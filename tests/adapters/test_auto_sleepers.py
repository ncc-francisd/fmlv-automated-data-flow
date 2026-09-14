"""Tests for the Auto-Sleepers adapter's pure parsing functions, against real pages.

Fixtures are real pages fetched 14 September 2026 with `<script>` and `<style>` removed —
see `docs/adapters/auto-sleepers.md`. Four of the eighteen, each carrying something the
others do not:

* **Bourton** — a Mercedes coachbuilt, and the page whose summary strip was blanked by the
  2027 changeover between two fetches on one day.
* **FG 635** — an Active campervan: the range that comes from the URL rather than the
  heading, and the only body type with a separate pop-top roof height.
* **Broadway EK TB LP** — the layout FMLV does not hold, so the one that arrives new.
* **M-Star** — a Mercedes campervan, the only one on a 3880kg chassis.

No network here.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.adapters import adapter_for, auto_sleepers
from src.adapters.auto_sleepers import (
    ACTIVE_RANGE,
    DEFAULT_RANGES,
    PAYLOAD_TOLERANCE_KG,
    AutoSleepersProduct,
    _build_extracted_motorhome,
    _range_and_model,
    _reconciles,
    detail_rows,
    find_model_urls,
    parse_model_page,
    plain_text,
)
from src.product_model.enums import BodyType, Heating, Refrigeration

FIXTURES = Path(__file__).parent / "fixtures"

#: Auto-Sleepers' own UK roster, and the requester confirms every model on the site is
#: current here — so this is the whole range, not an importer's subset.
EXPECTED_LAYOUTS = 18

PAGES: dict[str, str] = {
    "auto_sleepers_bourton.html": "https://auto-sleepers.com/motorhomes/mercedes/bourton",
    "auto_sleepers_fg635.html": "https://auto-sleepers.com/campervans/fiat-active/fg-635",
    "auto_sleepers_broadway_ek_tb_lp.html": "https://auto-sleepers.com/motorhomes/fiat/broadway-ek-tb-lp",
    "auto_sleepers_m_star.html": "https://auto-sleepers.com/campervans/mercedes/m-star",
}

ALL_KEYS = tuple(key for key, _label in DEFAULT_RANGES)


def _page(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _parse(name: str) -> AutoSleepersProduct:
    product = parse_model_page(_page(name), PAGES[name])
    assert product is not None, f"{name} did not parse"
    return product


# --------------------------------------------------------------------------- #
# The roster
# --------------------------------------------------------------------------- #


def _sitemap(*paths: str) -> str:
    return "".join(f"<url><loc>https://auto-sleepers.com{p}</loc></url>" for p in paths)


def test_a_model_url_is_found_inside_the_sitemap_not_only_at_a_string_end() -> None:
    """Every `<loc>` is followed by a closing tag, not by end-of-string.

    Anchoring the pattern on `$` matched nothing in the sitemap, and the first real run
    collected zero products against a 19-row baseline.
    """
    urls = find_model_urls(_sitemap("/motorhomes/mercedes/bourton"), ALL_KEYS)

    assert urls == ["https://auto-sleepers.com/motorhomes/mercedes/bourton"]


def test_only_model_pages_are_taken_from_the_sitemap() -> None:
    """325 URLs, of which 18 are vehicles."""
    xml = _sitemap(
        "/",
        "/campervans",
        "/campervans/fiat",
        "/campervans/fiat/symbol",
        "/find-your-perfect-motorhome",
    )

    assert find_model_urls(xml, ALL_KEYS) == ["https://auto-sleepers.com/campervans/fiat/symbol"]


def test_a_single_range_reads_only_its_own_pages() -> None:
    xml = _sitemap("/campervans/fiat/symbol", "/campervans/mercedes/m-star")

    urls = find_model_urls(xml, ("campervans/mercedes",))

    assert urls == ["https://auto-sleepers.com/campervans/mercedes/m-star"]


def test_the_roster_is_deduplicated() -> None:
    xml = _sitemap("/campervans/fiat/symbol", "/campervans/fiat/symbol/")

    assert len(find_model_urls(xml, ALL_KEYS)) == 1


def test_every_body_type_and_base_vehicle_pair_is_covered() -> None:
    assert len(DEFAULT_RANGES) == 5
    assert {key.split("/")[1] for key in ALL_KEYS} == {"fiat", "fiat-active", "mercedes"}


# --------------------------------------------------------------------------- #
# The range and model, which are not both in the heading
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("heading", "base", "expected"),
    [
        ("Bourton", "mercedes", ("Bourton", "Bourton")),
        ("Broadway EB", "fiat", ("Broadway", "EB")),
        ("Nuevo EK Plus", "fiat", ("Nuevo", "EK Plus")),
        ("Burford Duo", "mercedes", ("Burford", "Duo")),
        ("FG 635", "fiat-active", ("Active", "FG635")),
    ],
)
def test_the_range_and_model_follow_fmlvs_two_shapes(
    heading: str, base: str, expected: tuple[str, str]
) -> None:
    """A singleton repeats itself; a family splits on its first word."""
    assert _range_and_model(heading, base) == expected


def test_an_active_campervan_takes_its_range_from_the_url() -> None:
    """FMLV holds range `Active`, model `FG635` — and the heading says neither.

    The requester corrected these in Nova on 14 September 2026; before that FMLV had
    `FG365 Active` / `FG365`, with the digits transposed.
    """
    product = _parse("auto_sleepers_fg635.html")

    assert (product.manufacturer_range, product.model) == (ACTIVE_RANGE, "FG635")
    assert "FG 635" in _page("auto_sleepers_fg635.html")


# --------------------------------------------------------------------------- #
# Everything one page yields
# --------------------------------------------------------------------------- #


def test_a_coachbuilt_yields_every_field() -> None:
    product = _parse("auto_sleepers_bourton.html")

    assert (product.manufacturer_range, product.model) == ("Bourton", "Bourton")
    assert product.mh_passenger_seats_inc_driver == 2
    assert product.berths == 2
    assert product.mh_length_mm == 6445
    assert product.mh_width_mm == 2260
    assert product.mh_height_mm == 2865
    assert product.mtplm_kilograms == 3500
    assert product.mro_kilograms == 3043
    assert product.mh_payload_kilograms == 457


def test_a_campervan_yields_every_field() -> None:
    product = _parse("auto_sleepers_m_star.html")

    assert product.mh_length_mm == 7100
    assert product.mh_width_mm == 2020
    assert product.mh_height_mm == 2881
    assert product.mtplm_kilograms == 3880
    assert product.base_vehicle == "Mercedes"


def test_the_width_is_the_mirrors_folded_figure() -> None:
    """Both are published and both are labelled, so there is no way to take the wrong one."""
    rows = detail_rows(_page("auto_sleepers_bourton.html"))

    assert rows["Overall Width (mirrors folded)"].startswith("2260mm")
    assert rows["Overall Width (mirrors extended)"].startswith("2660mm")
    assert _parse("auto_sleepers_bourton.html").mh_width_mm == 2260


def test_the_imperial_half_of_a_dimension_is_ignored() -> None:
    assert "21'1" in detail_rows(_page("auto_sleepers_bourton.html"))["Overall Length"]
    assert _parse("auto_sleepers_bourton.html").mh_length_mm == 6445


def test_entities_are_resolved_rather_than_shown_to_a_reviewer() -> None:
    assert "&#39;" not in plain_text("<p>6445mm / 21&#39;1&quot;</p>")


def test_the_price_is_the_on_the_road_headline() -> None:
    assert _parse("auto_sleepers_broadway_ek_tb_lp.html").rrp_pounds == 82_850


# --------------------------------------------------------------------------- #
# The labels move, so they are matched on their stems
# --------------------------------------------------------------------------- #


def test_either_wording_of_the_laden_mass_row_is_read() -> None:
    """The same row was reworded *and* misspelled within one day.

    `Maximum Technically Permissible Laden Mass (a) (est)` in the morning,
    `Maximum Permissable Laden Mass (a) (est)` in the afternoon.
    """
    page = _page("auto_sleepers_bourton.html")
    reworded = page.replace("Maximum Permissable Laden Mass (a)", "Maximum Technically Permissible Laden Mass (a)")

    assert parse_model_page(page, PAGES["auto_sleepers_bourton.html"]).mtplm_kilograms == 3500
    assert parse_model_page(reworded, PAGES["auto_sleepers_bourton.html"]).mtplm_kilograms == 3500


def test_a_page_part_way_through_the_changeover_yields_nothing_rather_than_zero() -> None:
    """A blanked value must reach a reviewer as a field not found, preserving FMLV's."""
    page = _page("auto_sleepers_bourton.html").replace("3043kg", "")
    product = parse_model_page(page, PAGES["auto_sleepers_bourton.html"])

    assert product is not None
    assert product.mro_kilograms is None
    assert product.mh_length_mm == 6445, "the rest of the page still reads"


# --------------------------------------------------------------------------- #
# The self-check, which the page prints
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", sorted(PAGES))
def test_the_pages_own_subtraction_holds(name: str) -> None:
    reconciles, why_not = _reconciles(_parse(name))

    assert reconciles is True, why_not


def test_the_tolerance_is_zero_because_the_page_prints_the_arithmetic() -> None:
    """`Maximum User Payload (c) (c=a-b)` held exactly on all 18 at survey."""
    assert PAYLOAD_TOLERANCE_KG == 0

    reconciles, why_not = _reconciles(
        replace(_parse("auto_sleepers_bourton.html"), mh_payload_kilograms=458)
    )

    assert reconciles is False
    assert "1kg out" in why_not


def test_a_failed_check_drops_the_masses_and_keeps_the_rest() -> None:
    """One URL is one vehicle, so there is no reason to distrust the dimensions."""
    product = replace(
        _parse("auto_sleepers_bourton.html"),
        mtplm_kilograms=None,
        mro_kilograms=None,
        mh_payload_kilograms=None,
    )
    extracted = _build_extracted_motorhome(product)

    assert extracted.motorhome.mtplm_kilograms is None
    assert extracted.motorhome.mh_length_mm == 6445
    assert extracted.motorhome.rrp_pounds is not None


def test_a_product_missing_a_mass_has_nothing_to_contradict() -> None:
    reconciles, _why = _reconciles(
        replace(_parse("auto_sleepers_bourton.html"), mro_kilograms=None)
    )

    assert reconciles is True


# --------------------------------------------------------------------------- #
# Body type and base vehicle
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("auto_sleepers_bourton.html", BodyType.COACH_BUILT_LOW_PROFILE),
        ("auto_sleepers_broadway_ek_tb_lp.html", BodyType.COACH_BUILT_LOW_PROFILE),
        ("auto_sleepers_m_star.html", BodyType.CAMPERVAN_HIGH_TOP),
        ("auto_sleepers_fg635.html", BodyType.CAMPERVAN_HIGH_TOP_ELEVATING_ROOF),
    ],
)
def test_the_body_type_comes_from_the_path_and_the_roof_rows(
    name: str, expected: BodyType
) -> None:
    """Only the Active vans publish a pop-top height, and only they have one."""
    assert _parse(name).body_type is expected


def test_only_the_active_vans_publish_a_pop_top_height() -> None:
    assert _parse("auto_sleepers_fg635.html").has_pop_top is True
    assert _parse("auto_sleepers_m_star.html").has_pop_top is False


def test_an_active_van_is_still_a_fiat() -> None:
    """`fiat-active` is Auto-Sleepers' sub-brand, not a different base vehicle."""
    extracted = _build_extracted_motorhome(_parse("auto_sleepers_fg635.html"))

    assert extracted.motorhome.base_vehicle_manufacturer == "Fiat"


# --------------------------------------------------------------------------- #
# What reaches the reviewer
# --------------------------------------------------------------------------- #


def test_the_habitation_readings_are_findings_from_the_models_own_copy() -> None:
    extracted = _build_extracted_motorhome(_parse("auto_sleepers_bourton.html"))

    assert extracted.motorhome.heating is Heating.WET_CENTRAL
    assert extracted.motorhome.refrigeration is Refrigeration.FRIDGE_FREEZER
    assert extracted.motorhome.microwave is True
    assert extracted.motorhome.shower_toilet_separated is True


def test_the_misspelled_washroom_wording_is_still_read() -> None:
    """Auto-Sleepers write "Seperate" on every page."""
    page = _page("auto_sleepers_bourton.html")

    assert "Seperate" in page
    assert _build_extracted_motorhome(_parse("auto_sleepers_bourton.html")).motorhome.shower_toilet_separated is True


def test_the_height_provenance_explains_why_it_shrinks() -> None:
    """Every matched product loses 25-35mm, so a reviewer needs the reason beside it."""
    snippet = _build_extracted_motorhome(_parse("auto_sleepers_bourton.html")).provenance[
        "mh_height_mm"
    ].snippet

    assert "excl TV aerial" in snippet
    assert "one definition" in snippet


def test_the_weights_say_the_manufacturer_hedged_them() -> None:
    snippet = _build_extracted_motorhome(_parse("auto_sleepers_bourton.html")).provenance[
        "mtplm_kilograms"
    ].snippet

    assert "(est)" in snippet


def test_the_width_provenance_names_the_figure_not_taken() -> None:
    snippet = _build_extracted_motorhome(_parse("auto_sleepers_bourton.html")).provenance[
        "mh_width_mm"
    ].snippet

    assert "mirrors folded" in snippet
    assert "mirrors-extended" in snippet


# --------------------------------------------------------------------------- #
# Wiring
# --------------------------------------------------------------------------- #


def test_the_adapter_is_registered_under_its_fmlv_name() -> None:
    assert adapter_for("Auto-Sleepers Limited") is auto_sleepers
