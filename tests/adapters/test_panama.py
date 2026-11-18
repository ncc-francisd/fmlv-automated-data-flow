"""Tests for the Panama adapter's pure parsing functions, against real pages.

Fixtures are real pages fetched 14 September 2026 with `<script>` and `<style>` removed —
see `docs/adapters/panama.md`. Four of the five, each carrying something the others do not:

* **P\\12** — the only page with **two columns**, five belted seats against seven. The
  requester ruled the five-seat column is the base vehicle and the seventh seat an option.
* **P\\12+** — one column, and one of the two layouts FMLV does not yet hold.
* **P\\57** — one column and **no printed payload row**, so its payload is derived.
* **P\\10E Hybrid** — the page that misspells `sleeping potitions` and leaves its HTML
  entities unescaped where its siblings do not.

No network here.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.adapters import adapter_for, panama
from src.adapters.panama import (
    BASE_VEHICLE,
    EXPECTED_LAYOUTS,
    FMLV_RANGE,
    HIGH_TOP_ABOVE_MM,
    PanamaProduct,
    _build_extracted_motorhome,
    _first_millimetres,
    _reconciles,
    find_model_urls,
    parse_model_page,
    plain_text,
    sitemap_model_urls,
)
from src.product_model.enums import BodyType, Heating, Refrigeration

FIXTURES = Path(__file__).parent / "fixtures"

#: A real backslash, built rather than written, because a literal one in a fixture name or
#: a heredoc is too easy to lose to an escaping layer.
B = chr(92)

PAGES: dict[str, str] = {
    "panama_p12.html": "https://www.panamauk.co.uk/p12",
    "panama_p12_plus.html": "https://www.panamauk.co.uk/p12-plus",
    "panama_p57.html": "https://www.panamauk.co.uk/p57",
    "panama_p10e.html": "https://www.panamauk.co.uk/p10-e",
    "panama_p12_se_awd.html": "https://www.panamauk.co.uk/p12-se-awd",
}

#: `pages-sitemap.xml` as Wix served it on 18 November 2026, whole.
SITEMAP = "panama_pages_sitemap.xml"

#: **The SE fixture has had its `<style>` and `<script>` blocks removed and nothing else.**
#: The page is 2.5MB as served and 1.6MB of that is CSS; `plain_text` discards both tags
#: before reading a word, and the trimmed copy was checked to parse to the identical
#: `PanamaProduct` before it was saved.


def _page(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _parse(name: str) -> PanamaProduct:
    product = parse_model_page(_page(name), PAGES[name])
    assert product is not None, f"{name} did not parse"
    return product


# --------------------------------------------------------------------------- #
# The roster: the pages sitemap, with the homepage as a second opinion
# --------------------------------------------------------------------------- #


def test_the_pages_sitemap_lists_every_layout() -> None:
    """**The roster, as of 18 November 2026.** The homepage links four of these nine."""
    urls = sitemap_model_urls(_page(SITEMAP), ("p",))

    assert len(urls) == EXPECTED_LAYOUTS
    assert sorted(url.rsplit("/", 1)[-1] for url in urls) == [
        "p10-e",
        "p12",
        "p12-plus",
        "p12-se",
        "p12-se-awd",
        "p50",
        "p50-plus",
        "p57",
        "p57-se",
    ]


def test_the_sitemaps_other_pages_are_not_mistaken_for_models() -> None:
    """It lists thirty-odd pages and only nine of them are vehicles."""
    urls = sitemap_model_urls(_page(SITEMAP), ("p",))

    for junk in ("panama-media", "panama-owners", "privacy-policy", "panama-se-range"):
        assert not any(url.endswith(junk) for url in urls), junk


def test_the_homepage_is_still_read_as_a_roster() -> None:
    """Kept as the fallback and the cross-check: Wix could drop the sitemap tomorrow."""
    html_ = (
        '<a href="/p12">a</a><a href="/p12-plus">b</a><a href="/p57">c</a>'
        '<a href="/p50-plus">d</a><a href="/p10-e">e</a>'
    )

    urls = find_model_urls(html_, ("p",))

    assert len(urls) == 5
    assert urls[0] == "https://www.panamauk.co.uk/p12"


def test_a_slug_of_several_words_is_read() -> None:
    """**The bug this fix exists for.** The path pattern allowed one hyphenated word, so
    `/p12-se-awd` matched nothing — and `/p57-se` and `/p12-se` with it. Three live models
    went uncollected and nothing said so, because an unlinked page and a withdrawn model
    look the same from here."""
    html_ = '<a href="/p12-se-awd">a</a><a href="/p57-se">b</a><a href="/p12-se">c</a>'

    assert find_model_urls(html_, ("p",)) == [
        "https://www.panamauk.co.uk/p12-se-awd",
        "https://www.panamauk.co.uk/p57-se",
        "https://www.panamauk.co.uk/p12-se",
    ]


def test_the_sites_other_pages_are_not_mistaken_for_models() -> None:
    html_ = (
        '<a href="/panama-media">x</a><a href="/panama-owners">y</a>'
        '<a href="/pages-sitemap.xml">z</a><a href="/privacy-policy">w</a>'
        '<a href="/p57">real</a>'
    )

    assert find_model_urls(html_, ("p",)) == ["https://www.panamauk.co.uk/p57"]


def test_the_roster_is_deduplicated() -> None:
    html_ = '<a href="/p12">a</a><a href="https://www.panamauk.co.uk/p12">a</a>'

    assert len(find_model_urls(html_, ("p",))) == 1


# --------------------------------------------------------------------------- #
# The model name, backslash and all
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("panama_p12.html", f"{B}12"),
        ("panama_p12_plus.html", f"{B}12+"),
        ("panama_p57.html", f"{B}57"),
        ("panama_p10e.html", f"{B}10E Hybrid"),
    ],
)
def test_the_model_keeps_panamas_own_backslash(name: str, expected: str) -> None:
    """A real `U+005C`, confirmed in the page title, not a rendering artefact.

    FMLV holds two of the three with a forward slash instead; the requester is correcting
    that at upload. It costs nothing in matching, because the identity tokeniser splits on
    non-alphanumerics and both spellings reduce to the same bag.
    """
    product = _parse(name)

    assert product.model == expected
    assert product.manufacturer_range == FMLV_RANGE == "P"


def test_the_range_is_separate_from_the_model() -> None:
    """The page says `P\\12`; FMLV splits it into range `P` and model `\\12`."""
    assert _parse("panama_p12.html").label == f"P{B}12"


# --------------------------------------------------------------------------- #
# The two-column page
# --------------------------------------------------------------------------- #


def test_the_two_column_page_takes_the_base_vehicle_column() -> None:
    """The P\\12 publishes five belted seats and seven, and the seventh is an option.

    The requester's ruling, 14 September 2026. The run confirmed it independently: every
    one of the P\\12's spec fields then verified *unchanged* against FMLV, which the
    seven-seat column's 2630kg would not have done.
    """
    product = _parse("panama_p12.html")

    assert product.mh_passenger_seats_inc_driver == 5
    assert product.mro_kilograms == 2558
    assert "7" in plain_text(_page("panama_p12.html")), "the second column is really there"


def test_a_single_column_page_is_unaffected_by_the_rule() -> None:
    product = _parse("panama_p57.html")

    assert product.mh_passenger_seats_inc_driver == 4
    assert product.mro_kilograms == 2875


# --------------------------------------------------------------------------- #
# Everything one page yields
# --------------------------------------------------------------------------- #


def test_a_page_yields_every_field() -> None:
    product = _parse("panama_p12_plus.html")

    assert product.mh_passenger_seats_inc_driver == 5
    assert product.berths == 4
    assert product.mh_length_mm == 5440
    assert product.mh_width_mm == 2150
    assert product.mh_height_mm == 2000
    assert product.mtplm_kilograms == 3225
    assert product.mro_kilograms == 2655
    assert product.mh_payload_kilograms == 570
    assert product.rrp_pounds == 63_995


def test_the_width_is_the_mirrors_folded_figure() -> None:
    """`Overall Width (inc mirrors) 2275mm` sits directly above it, named."""
    text = plain_text(_page("panama_p12_plus.html"))

    assert "2275mm" in text
    assert _parse("panama_p12_plus.html").mh_width_mm == 2150


def test_the_misspelled_berth_label_is_still_read() -> None:
    """The P\\10E Hybrid says `Berths (sleeping potitions)`."""
    assert "potitions" in plain_text(_page("panama_p10e.html"))
    assert _parse("panama_p10e.html").berths == 4


def test_the_page_that_leaves_its_entities_escaped_is_still_read() -> None:
    """Its siblings give real characters; this one reaches the reader with `&#x27;`."""
    product = _parse("panama_p10e.html")

    assert product.mh_length_mm == 5040
    assert product.mh_width_mm == 2150


def test_either_wording_of_the_laden_mass_label_is_read() -> None:
    """`MTPLM (A) kg` on the P\\12 and `MTPLM (A)` on the other four."""
    assert _parse("panama_p12.html").mtplm_kilograms == 3175
    assert _parse("panama_p57.html").mtplm_kilograms == 3225


# --------------------------------------------------------------------------- #
# The self-check, which only three pages print
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", sorted(PAGES))
def test_a_printed_payload_agrees_with_the_masses_beside_it(name: str) -> None:
    reconciles, why_not = _reconciles(_parse(name))

    assert reconciles is True, why_not


def test_a_page_without_a_payload_row_derives_it_and_says_so() -> None:
    """Two of the five print no payload, so there is nothing to check against."""
    product = _parse("panama_p57.html")

    assert product.published_payload_kilograms is None
    assert product.mh_payload_kilograms == 3225 - 2875 == 350
    reconciles, _why = _reconciles(product)
    assert reconciles is True, "nothing printed means nothing to contradict"


def test_a_printed_payload_that_disagrees_is_caught() -> None:
    product = replace(_parse("panama_p12_plus.html"), published_payload_kilograms=999)

    reconciles, why_not = _reconciles(product)

    assert reconciles is False
    assert "570kg" in why_not


def test_a_failed_check_drops_the_masses_and_keeps_the_rest() -> None:
    product = replace(
        _parse("panama_p12_plus.html"),
        mtplm_kilograms=None,
        mro_kilograms=None,
        published_payload_kilograms=None,
    )
    extracted = _build_extracted_motorhome(product)

    assert extracted.motorhome.mtplm_kilograms is None
    assert extracted.motorhome.mh_payload_kilograms is None
    assert extracted.motorhome.mh_length_mm == 5440
    assert extracted.motorhome.rrp_pounds == 63_995


# --------------------------------------------------------------------------- #
# What reaches the reviewer
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", sorted(PAGES))
def test_every_layout_is_an_elevating_roof_campervan(name: str) -> None:
    """All five are 2000-2070mm with a pop-up roof, which is what FMLV holds."""
    assert _parse(name).body_type is BodyType.CAMPERVAN_ELEVATING_ROOF
    assert _parse(name).mh_height_mm < HIGH_TOP_ABOVE_MM


def test_the_base_vehicle_is_the_ford_every_page_states() -> None:
    extracted = _build_extracted_motorhome(_parse("panama_p12.html"))

    assert extracted.motorhome.base_vehicle_manufacturer == BASE_VEHICLE == "Ford"


def test_the_fridge_reading_comes_through_as_a_finding() -> None:
    extracted = _build_extracted_motorhome(_parse("panama_p12.html"))

    assert extracted.motorhome.refrigeration is Refrigeration.FRIDGE_FREEZER


def test_the_heating_is_read_from_the_named_unit_not_the_marketing_line() -> None:
    """The prose says only "diesel fuelled heating", which settles nothing on its own.

    A diesel heater may be blown air or a wet boiler. What decides it is the equipment
    list naming a **Webasto Air Top**, which is an air heater — so the reading is the
    page's own statement rather than an inference from the fuel.
    """
    text = plain_text(_page("panama_p12.html"))
    assert "diesel fuelled heating" in text.lower()
    assert "Air Top" in text

    extracted = _build_extracted_motorhome(_parse("panama_p12.html"))

    assert extracted.motorhome.heating is Heating.BLOWN_AIR
    assert "Air Top" in extracted.provenance["heating"].snippet


def test_a_layout_that_names_no_heater_reports_no_heating() -> None:
    """The hybrid lists no Webasto, and silence stays silence."""
    extracted = _build_extracted_motorhome(_parse("panama_p10e.html"))

    assert extracted.motorhome.heating is None
    assert "heating" not in extracted.provenance


def test_the_seat_provenance_explains_the_column_choice() -> None:
    snippet = _build_extracted_motorhome(_parse("panama_p12.html")).provenance[
        "mh_passenger_seats_inc_driver"
    ].snippet

    assert "first column" in snippet
    assert "option" in snippet


def test_the_derived_payload_says_nothing_corroborates_it() -> None:
    snippet = _build_extracted_motorhome(_parse("panama_p57.html")).provenance[
        "mh_payload_kilograms"
    ].snippet

    assert "derived" in snippet


def test_the_price_names_marquis_as_the_seller_that_sets_it() -> None:
    snippet = _build_extracted_motorhome(_parse("panama_p12.html")).provenance[
        "rrp_pounds"
    ].snippet

    assert "Marquis" in snippet


# --------------------------------------------------------------------------- #
# Wiring
# --------------------------------------------------------------------------- #


def test_the_adapter_is_registered_under_its_fmlv_name() -> None:
    assert adapter_for("Panama") is panama


def test_every_layout_records_the_mirrors_folded_width() -> None:
    """The folded figure, never the `(inc mirrors)` one printed above it.

    Panama are the only brand in the group that print both, so they are where a column
    mixing folded and extended mirrors would come from.
    """
    for name in PAGES:
        product = _parse(name)
        extracted = _build_extracted_motorhome(product)

        assert product.mh_width_mm == 2150
        assert extracted.motorhome.mh_width_mm == 2150
        snippet = extracted.provenance["mh_width_mm"].snippet
        assert "mirrors folded" in snippet
        assert "never recorded" in snippet


def test_the_page_publishes_both_mirror_figures() -> None:
    """2275mm with the mirrors out, 2150mm folded. Only the folded one is recorded."""
    text = plain_text(_page("panama_p57.html"))

    assert "Overall Width (inc mirrors)" in text
    assert "2275mm" in text
    assert "Overall Width (mirrors folded)" in text


# --------------------------------------------------------------------------- #
# The SE pages, which broke two readers at once
# --------------------------------------------------------------------------- #


def test_a_multi_word_model_name_is_read_from_the_title() -> None:
    """`<title>P\\12 SE  AWD| Panama MPV Campervan</title>` — two spaces inside the name
    and none before the pipe. The old pattern took one word plus an optional `Hybrid`, so
    this page returned `None` and was narrated as carrying no model name at all."""
    assert _parse("panama_p12_se_awd.html").model == f"{B}12 SE AWD"


def test_the_se_page_yields_every_field() -> None:
    """Nothing else about these pages is unusual: same template, same labels."""
    product = _parse("panama_p12_se_awd.html")

    assert product.rrp_pounds == 74995
    assert product.mtplm_kilograms == 3170
    assert product.mro_kilograms == 2715
    assert product.mh_length_mm == 5050
    assert product.mh_height_mm == 2020
    assert product.berths == 4
    assert product.mh_passenger_seats_inc_driver == 5


def test_the_payload_label_missing_its_bracket_is_still_read() -> None:
    """The three SE pages print `Maximum User Payload (A-B` with no closing bracket.
    Read, the figure corroborates the two masses; unread, the payload is derived and
    nothing checks it."""
    text_ = plain_text(_page("panama_p12_se_awd.html"))
    assert "Maximum User Payload (A-B 455kg" in text_, "the bracket is really missing"

    product = _parse("panama_p12_se_awd.html")

    assert product.published_payload_kilograms == 455
    assert product.mtplm_kilograms - product.mro_kilograms == 455


def test_the_se_page_still_takes_the_mirrors_folded_width() -> None:
    """It publishes both, `(inc mirrors) 2275mm` first and `(mirrors folded) 2150mm`
    second. FMLV wants the folded one — the settled rule — and the label is what picks it,
    not the order or the size."""
    text_ = plain_text(_page("panama_p12_se_awd.html"))
    assert "Overall Width (inc mirrors)" in text_
    assert "2275mm" in text_

    assert _parse("panama_p12_se_awd.html").mh_width_mm == 2150


def test_a_dimension_that_lost_its_unit_is_still_read() -> None:
    r"""Quoted from the live `P\12+` page on 18 November 2026, which prints `Overall Height
    6'7" | 2000` where every sibling prints `2000mm` and where it printed `2000mm` itself
    in September. 6'7" is 2007mm, so the figure is millimetres."""
    assert _first_millimetres("6'7\" | 2000 Ford Tourneo Custom 2.0 EcoBlue 136") == 2000


def test_a_bare_number_outside_the_metric_column_is_not_a_dimension() -> None:
    """The window after a label runs into the next row. Without the pipe anchor, the
    height on that same page would have read the `215` of the tyre size."""
    assert _first_millimetres("Tyre size 215/60 R17 C") is None
