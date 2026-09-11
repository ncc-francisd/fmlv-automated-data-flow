"""Tests for the Pilote adapter's pure parsing functions, against real pages.

Fixtures are real pages fetched 11 September 2026 **after the click**, with `<script>`
and `<style>` removed — so each one carries a filled technical popup, which is the only
state in which this source has any numbers at all. Four of the 43, one per body type:

* **V540G Pilote** — a panel van: the 23-row popup, the `Load capacity` payload row, and
  the row labelled literally `undefined`.
* **G690GJ Expression** — an A-class: the 57-row popup, and payload in the summary strip
  instead.
* **P720U Evidence** — a low profile, and the one sampled layout where the site's berth
  count disagrees with the brochure.
* **A630G Atlas** — the Ford-based compact low profile, whose length is the evidence that
  no Atlas exemption is needed.

No network here.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.adapters import adapter_for, pilote
from src.adapters.pilote import (
    CLICK_SELECTOR,
    DEFAULT_RANGES,
    HIGH_TOP_ABOVE_MM,
    LENGTH_TOLERANCE_MM,
    PRICES,
    PiloteProduct,
    _build_extracted_motorhome,
    _reconciles,
    find_model_urls,
    length_disagreement,
    parse_model_page,
    plain_text,
    popup_rows,
)
from src.product_model.enums import BodyType

FIXTURES = Path(__file__).parent / "fixtures"

#: Pilote's 2027 UK roster: 43 layouts, agreed by the sitemap, the price list and the
#: Options brochure's layout tables.
EXPECTED_LAYOUTS = 43

PAGES: dict[str, str] = {
    "pilote_v540g_pilote.html": "https://www.pilote-motorhome.uk/panel-van/v540g-pilote/",
    "pilote_g690gj_expression.html": "https://www.pilote-motorhome.uk/a-class/g690gj-expression/",
    "pilote_p720u_evidence.html": "https://www.pilote-motorhome.uk/low-profile/p720u-evidence/",
    "pilote_a630g_atlas.html": "https://www.pilote-motorhome.uk/compact-low-profile/a630g-atlas/",
}

ALL_KEYS = tuple(key for key, _label in DEFAULT_RANGES)


def _page(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _parse(name: str) -> PiloteProduct:
    product = parse_model_page(_page(name), PAGES[name])
    assert product is not None, f"{name} did not parse"
    return product


# --------------------------------------------------------------------------- #
# The roster, and the range name hidden in the slug
# --------------------------------------------------------------------------- #


def _sitemap(*paths: str) -> str:
    return "".join(f"<url><loc>https://www.pilote-motorhome.uk{p}</loc></url>" for p in paths)


def test_the_slug_pair_gives_every_fmlv_range() -> None:
    """Body type alone is not a range — the offer is the other half of the identity."""
    assert len(DEFAULT_RANGES) == 7
    assert dict(DEFAULT_RANGES)["a-class/expression"] == "Galaxy Expression"
    assert dict(DEFAULT_RANGES)["a-class/evidence"] == "Galaxy Evidence"
    # `Van`, not `Pilote Van`: FMLV prepends the manufacturer when it renders a listing,
    # so `Van` shows as "Pilote Van V630S Fiat" and `Pilote Van` would double it up.
    assert dict(DEFAULT_RANGES)["panel-van/pilote"] == "Van"


def test_one_layout_code_under_two_offers_is_two_products() -> None:
    """G740FC is £86,900 as Expression and £94,900 as Evidence, so model is not identity."""
    assert PRICES[("Galaxy Expression", "G740FC")] != PRICES[("Galaxy Evidence", "G740FC")]


def test_the_broken_placeholder_entry_is_dropped() -> None:
    """The sitemap carries a `%taxo%` URL that is not a vehicle."""
    urls = find_model_urls(_sitemap("/%taxo%/", "/a-class/g690gj-expression/"), ALL_KEYS)

    assert urls == ["https://www.pilote-motorhome.uk/a-class/g690gj-expression/"]


def test_a_single_range_reads_only_its_own_pages() -> None:
    xml = _sitemap(
        "/a-class/g690gj-expression/",
        "/a-class/g690gj-evidence/",
        "/panel-van/v540g-pilote/",
    )

    urls = find_model_urls(xml, ("a-class/evidence",))

    assert urls == ["https://www.pilote-motorhome.uk/a-class/g690gj-evidence/"]


def test_the_roster_is_deduplicated() -> None:
    xml = _sitemap("/a-class/g690gj-expression/", "/a-class/g690gj-expression/")

    assert len(find_model_urls(xml, ALL_KEYS)) == 1


def test_the_price_list_covers_the_whole_roster() -> None:
    assert len(PRICES) == EXPECTED_LAYOUTS


# --------------------------------------------------------------------------- #
# The popup, which is the only place the numbers live
# --------------------------------------------------------------------------- #


def test_the_van_and_the_coachbuilt_have_different_sized_tables() -> None:
    """23 rows against 50 — so nothing may be read by position."""
    assert len(popup_rows(_page("pilote_v540g_pilote.html"))) == 23
    assert len(popup_rows(_page("pilote_g690gj_expression.html"))) > 40


def test_a_page_without_the_click_yields_no_rows() -> None:
    """An empty popup means the click did not land, not that the vehicle has no data."""
    assert popup_rows("<html><body><p>no popup here</p></body></html>") == {}


def test_the_undefined_row_is_kept_under_its_own_key_and_never_read() -> None:
    """A label that failed to render is not a figure to record under a guess."""
    rows = popup_rows(_page("pilote_v540g_pilote.html"))

    assert rows.get("undefined") == "411"
    product = _parse("pilote_v540g_pilote.html")
    assert 411 not in {
        product.mh_payload_kilograms,
        product.mtplm_kilograms,
        product.mro_kilograms,
    }


def test_a_tag_becomes_a_space_so_a_value_keeps_its_unit() -> None:
    assert plain_text("<p>Length 7,07</p><p>m</p>") == "Length 7,07 m"


# --------------------------------------------------------------------------- #
# Everything one page yields
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("name", "expected_range", "expected_model"),
    [
        ("pilote_v540g_pilote.html", "Van", "V540G"),
        ("pilote_g690gj_expression.html", "Galaxy Expression", "G690GJ"),
        ("pilote_p720u_evidence.html", "Pacific Evidence", "P720U"),
        ("pilote_a630g_atlas.html", "ATLAS", "A630G"),
    ],
)
def test_the_range_and_model_come_from_the_slug(
    name: str, expected_range: str, expected_model: str
) -> None:
    product = _parse(name)

    assert (product.manufacturer_range, product.model) == (expected_range, expected_model)


def test_a_panel_van_yields_every_field() -> None:
    product = _parse("pilote_v540g_pilote.html")

    assert product.mh_length_mm == 5410
    assert product.mh_height_mm == 2670
    assert product.mh_passenger_seats_inc_driver == 4
    assert product.berths == 2
    assert product.mtplm_kilograms == 3500
    assert product.mh_payload_kilograms == 730
    assert product.mro_kilograms == 3500 - 730 == 2770


def test_a_coachbuilt_yields_every_field() -> None:
    product = _parse("pilote_g690gj_expression.html")

    assert product.mh_length_mm == 7070
    assert product.mh_height_mm == 2850
    assert product.mh_passenger_seats_inc_driver == 4
    assert product.berths == 4
    assert product.mtplm_kilograms == 3500
    assert product.mh_payload_kilograms == 485
    assert product.mro_kilograms == 3015


def test_the_payload_comes_from_the_popup_on_a_van_and_the_strip_on_a_coachbuilt() -> None:
    """The two body types publish the same quantity in different places."""
    van = _parse("pilote_v540g_pilote.html")
    coachbuilt = _parse("pilote_g690gj_expression.html")

    assert "Load capacity" in van.payload_source
    assert "summary strip" in coachbuilt.payload_source


def test_no_payload_means_no_derived_mass_rather_than_a_wrong_one() -> None:
    product = replace(_parse("pilote_v540g_pilote.html"), mh_payload_kilograms=None)

    assert product.mro_kilograms is None


@pytest.mark.parametrize("name", sorted(PAGES))
def test_the_seat_count_is_four_on_every_sampled_layout(name: str) -> None:
    """From the popup's `Seats with safety belts`, never the strip's `Berth`.

    The strip calls a belted seat a Berth, and the page also carries a filter sidebar
    reading `2 berths 3 berths 4 berths` — between them, a loose pattern gave all four
    layouts 2 seats and 2 berths in the first parse.
    """
    assert _parse(name).mh_passenger_seats_inc_driver == 4


def test_the_optional_fifth_belt_is_not_counted() -> None:
    """`Seats with safety belts - optional` sits directly below the row that is read."""
    rows = popup_rows(_page("pilote_g690gj_expression.html"))

    assert "Seats with safety belts - optional" in rows
    assert _parse("pilote_g690gj_expression.html").mh_passenger_seats_inc_driver == 4


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("pilote_v540g_pilote.html", 2),
        ("pilote_g690gj_expression.html", 4),
        ("pilote_p720u_evidence.html", 2),
        ("pilote_a630g_atlas.html", 2),
    ],
)
def test_berths_come_from_the_strips_sleeping_place_row(name: str, expected: int) -> None:
    """The P720U's 2 disagrees with the brochure's 4; the requester ruled the site wins."""
    assert _parse(name).berths == expected


# --------------------------------------------------------------------------- #
# Body type and base vehicle
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("pilote_g690gj_expression.html", BodyType.A_CLASS),
        ("pilote_p720u_evidence.html", BodyType.COACH_BUILT_LOW_PROFILE),
        ("pilote_a630g_atlas.html", BodyType.COACH_BUILT_LOW_PROFILE),
        ("pilote_v540g_pilote.html", BodyType.CAMPERVAN_HIGH_TOP),
    ],
)
def test_the_body_type_comes_from_the_sites_own_path(name: str, expected: BodyType) -> None:
    """`compact` describes the width, not a different body — Atlas is a low profile."""
    assert _parse(name).body_type is expected


def test_a_van_below_the_threshold_would_not_be_a_high_top() -> None:
    product = replace(_parse("pilote_v540g_pilote.html"), mh_height_mm=HIGH_TOP_ABOVE_MM - 10)

    assert product.body_type is BodyType.CAMPERVAN


def test_the_atlas_is_the_ford_and_the_rest_are_fiat() -> None:
    atlas = _build_extracted_motorhome(_parse("pilote_a630g_atlas.html"))
    galaxy = _build_extracted_motorhome(_parse("pilote_g690gj_expression.html"))

    assert atlas.motorhome.base_vehicle_manufacturer == "Ford"
    assert galaxy.motorhome.base_vehicle_manufacturer == "Fiat"


# --------------------------------------------------------------------------- #
# The self-check
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", sorted(PAGES))
def test_a_length_matching_its_model_code_reconciles(name: str) -> None:
    reconciles, why_not = _reconciles(_parse(name))

    assert reconciles is True, why_not


def test_the_atlas_needs_no_exemption() -> None:
    """The brochure gives the A630G as 6.99m; the site and FMLV both say 6.30m."""
    product = _parse("pilote_a630g_atlas.html")

    assert product.mh_length_mm == product.implied_length_mm == 6300


def test_a_length_from_a_neighbouring_layout_is_caught() -> None:
    product = replace(_parse("pilote_a630g_atlas.html"), mh_length_mm=7250)

    reconciles, why_not = _reconciles(product)

    assert reconciles is False
    assert "950mm gap" in why_not


def test_the_tolerance_admits_the_worst_real_layout() -> None:
    """The G690GJ is 170mm from its code, which is the widest gap sampled."""
    assert LENGTH_TOLERANCE_MM > 170

    product = _parse("pilote_g690gj_expression.html")
    assert abs(product.mh_length_mm - product.implied_length_mm) == 170


def test_a_missing_length_has_nothing_to_contradict() -> None:
    reconciles, _why = _reconciles(replace(_parse("pilote_v540g_pilote.html"), mh_length_mm=None))

    assert reconciles is True


def test_the_strip_and_the_popup_are_checked_against_each_other() -> None:
    product = _parse("pilote_p720u_evidence.html")

    assert length_disagreement(product) is None
    assert "7250mm" in str(length_disagreement(replace(product, strip_length_mm=6000)))


# --------------------------------------------------------------------------- #
# What reaches the reviewer
# --------------------------------------------------------------------------- #


def test_no_width_is_recorded_at_all() -> None:
    """Pilote publish an interior width and a mirrors-open width, and FMLV wants neither.

    Emitting nothing also preserves whatever FMLV holds on a matched product, which is
    the requester's same-outer-shell case.
    """
    extracted = _build_extracted_motorhome(_parse("pilote_g690gj_expression.html"))

    assert extracted.motorhome.mh_width_mm is None
    assert "mh_width_mm" not in extracted.provenance


def test_the_mam_provenance_says_it_is_the_same_figure_as_mtplm() -> None:
    extracted = _build_extracted_motorhome(_parse("pilote_v540g_pilote.html"))

    assert "MAM and MTPLM are the same figure" in extracted.provenance["mtplm_kilograms"].snippet


def test_the_seat_provenance_warns_about_the_word_berth() -> None:
    extracted = _build_extracted_motorhome(_parse("pilote_v540g_pilote.html"))

    assert "Berth for a seat" in extracted.provenance["mh_passenger_seats_inc_driver"].snippet


def test_the_price_names_the_document_it_could_not_have_fetched() -> None:
    extracted = _build_extracted_motorhome(_parse("pilote_v540g_pilote.html"))

    assert extracted.motorhome.rrp_pounds == 65_400
    assert "No Pilote page carries a price" in extracted.provenance["rrp_pounds"].snippet


def test_the_derived_mass_says_it_was_derived() -> None:
    extracted = _build_extracted_motorhome(_parse("pilote_v540g_pilote.html"))

    assert "derived as MAM" in extracted.provenance["mro_kilograms"].snippet


# --------------------------------------------------------------------------- #
# Wiring
# --------------------------------------------------------------------------- #


def test_the_click_selector_is_not_a_text_match() -> None:
    """A text selector hits the popup's own heading, and a wrong click is silent."""
    assert CLICK_SELECTOR == "button.btn-popup"


def test_the_adapter_is_registered_under_its_fmlv_name() -> None:
    assert adapter_for("Pilote") is pilote


# --------------------------------------------------------------------------- #
# Identity, where the 0.5 default is not safe
# --------------------------------------------------------------------------- #


def test_the_match_threshold_excludes_a_different_offer() -> None:
    """Run #79 proved this rather than predicting it.

    `Galaxy Expression G720FGJ` and `Galaxy Selection G720FGJ` score 0.500 against each
    other, as do `Galaxy Expression G740FC` and `Galaxy Evidence G740FC` — and both pairs
    are real vehicles that are not each other, because the offer is part of the identity.
    At the default, the newly-listed Expression G720FGJ claimed the Selection row.
    """
    from types import SimpleNamespace

    from src.diff.matching import token_similarity

    def score(left: tuple[str, str], right: tuple[str, str]) -> float:
        return token_similarity(
            SimpleNamespace(manufacturer_range=left[0], model=left[1]),
            SimpleNamespace(manufacturer_range=right[0], model=right[1]),
        )

    # Must match: the same vehicle, and the `Pilote Van` -> `Van` correction, which is
    # the whole reason the threshold sits at 0.6 rather than higher.
    assert score(("Galaxy Expression", "G720FGJ"), ("Galaxy Expression", "G720FGJ")) >= (
        pilote.MATCH_THRESHOLD
    )
    assert score(("Van", "V600G"), ("Pilote Van", "V600G")) >= pilote.MATCH_THRESHOLD

    # Must not: every one of these is two real vehicles, usually at two different prices.
    for left, right in [
        (("Galaxy Expression", "G720FGJ"), ("Galaxy Selection", "G720FGJ")),
        (("Galaxy Expression", "G740FC"), ("Galaxy Evidence", "G740FC")),
        (("Van", "V540G"), ("Van Vega Evidence", "V540G")),
        (("Pacific Expression", "P720U"), ("Pacific Evidence", "P720U")),
    ]:
        assert score(left, right) < pilote.MATCH_THRESHOLD, (left, right)


def test_the_click_timeout_is_longer_than_the_shared_default() -> None:
    """Two of the 43 lost their popup at 5000ms in run #79."""
    from src.fetch.browser import DEFAULT_CLICK_TIMEOUT_MS

    assert pilote.CLICK_TIMEOUT_MS > DEFAULT_CLICK_TIMEOUT_MS


def test_the_two_layouts_with_no_popup_are_known_rather_than_a_click_failure() -> None:
    """Their pages carry no `button.btn-popup` at all — checked over plain HTTP.

    Raising the click timeout from 5s to 15s changed nothing for these two, which is
    what proved the cause was the source rather than the timing.
    """
    from src.adapters.pilote import LAYOUTS_WITHOUT_A_POPUP

    assert LAYOUTS_WITHOUT_A_POPUP == {
        ("Pacific Expression", "P740GJ"),
        ("Pacific Expression", "P740C"),
    }
    # Every sampled layout does have one, so the gap is specific rather than general.
    for name in PAGES:
        product = _parse(name)
        assert (product.manufacturer_range, product.model) not in LAYOUTS_WITHOUT_A_POPUP
        assert popup_rows(_page(name)), name
