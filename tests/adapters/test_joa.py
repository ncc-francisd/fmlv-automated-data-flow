"""Tests for the Joa by Pilote adapter's pure parsing functions, against real pages.

Fixtures are real pages fetched 10 September 2026 with `<script>` and `<style>` removed
— see `docs/adapters/joa.md`. Four of the ten, chosen because each carries something the
others do not:

* **75TB** — a twin-bed motorhome, so it has the `Bed insert between twin beds` row that
  is the only bed statement anywhere on this brand.
* **60F** — the one motorhome with no drop-down bed available at all.
* **54G** — a panel van: no price on the page, and the other set of dimensions.
* **63T** — the page whose stated length is its neighbour's, which is what the
  model-code self-check exists to catch.

No network here.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.adapters import adapter_for, joa
from src.adapters.joa import (
    HIGH_TOP_ABOVE_MM,
    LENGTH_TOLERANCE_MM,
    MTPLM_KILOGRAMS,
    PRICES_NOT_ON_THE_SITE,
    JoaProduct,
    _build_extracted_motorhome,
    _reconciles,
    _text,
    find_model_urls,
    floorplan_for,
    parse_equipment,
    parse_model_page,
    width_disagreement,
)
from src.product_model.enums import BedType, BodyType, Heating, Refrigeration
from src.vehicle_class import VehicleClass

FIXTURES = Path(__file__).parent / "fixtures"

#: Joa's own roster: seven motorhomes and three panel vans, agreed by the site's
#: `vehicle-sitemap.xml` and by Pilote's 2027 Technical Book.
EXPECTED_MOTORHOMES = 7
EXPECTED_PANEL_VANS = 3

#: (fixture, slug) for the four pages captured.
PAGES: dict[str, str] = {
    "joa_motorhome_75tb.html": "motorhome-75tb",
    "joa_motorhome_60f.html": "motorhome-60f",
    "joa_panel_van_54g.html": "panel-van-54g",
    "joa_panel_van_63t.html": "panel-van-63t",
}


def _page(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _parse(name: str) -> JoaProduct:
    product = parse_model_page(_page(name), PAGES[name])
    assert product is not None, f"{name} did not parse"
    return product


# --------------------------------------------------------------------------- #
# The roster
# --------------------------------------------------------------------------- #


def test_the_sitemap_yields_exactly_ten_vehicles() -> None:
    urls = find_model_urls(_page("joa_vehicle_sitemap.xml"))

    assert len(urls) == EXPECTED_MOTORHOMES + EXPECTED_PANEL_VANS
    assert sum("/motorhome-" in url for url in urls) == EXPECTED_MOTORHOMES
    assert sum("/panel-van-" in url for url in urls) == EXPECTED_PANEL_VANS


def test_the_roster_excludes_the_index_and_the_french_pages() -> None:
    urls = find_model_urls(_page("joa_vehicle_sitemap.xml"))

    assert "https://www.joabypilote.fr/en/vehicle/" not in urls
    assert all("/en/vehicle/" in url for url in urls)


def test_the_alias_slugs_are_not_in_the_sitemap() -> None:
    """In-page links give fifteen URLs for ten vehicles; the sitemap gives ten.

    `60f`, `motorhome70t`, `van-54g`, `panel-van-60g-en` and `panel-van-63t-en` all
    redirect to a canonical page, and reading them would collect five vehicles twice.
    """
    urls = find_model_urls(_page("joa_vehicle_sitemap.xml"))
    tails = {url.rstrip("/").rsplit("/", 1)[-1] for url in urls}

    assert not tails & {"60f", "motorhome70t", "van-54g", "panel-van-60g-en", "panel-van-63t-en"}


# --------------------------------------------------------------------------- #
# Flattening the page
# --------------------------------------------------------------------------- #


def test_a_tag_becomes_a_space_so_a_figure_keeps_its_unit() -> None:
    """Joa split a figure from its unit across two elements.

    Replacing a tag with any marker rather than a space breaks `7,45 m long` in half,
    and four of the ten pages then look as though they carry no summary strip at all.
    """
    assert _text("<p>7,45</p><p>m long</p>") == "7,45 m long"


def test_scripts_and_styles_are_not_read_as_text() -> None:
    assert "var" not in _text("<script>var x = 1</script><p>4 seats</p>")


# --------------------------------------------------------------------------- #
# The mislabelled panel
# --------------------------------------------------------------------------- #


def test_the_width_length_row_gives_the_width_and_the_height() -> None:
    """The label says Length and the value is the height — on all ten pages."""
    product = _parse("joa_motorhome_75tb.html")

    assert product.mh_width_mm == 2300
    assert product.mh_height_mm == 2850
    # And the real length, which is nowhere near 2850mm, comes from the summary strip.
    assert product.mh_length_mm == 7450


def test_the_van_panel_gives_the_vans_own_dimensions() -> None:
    product = _parse("joa_panel_van_54g.html")

    assert (product.mh_width_mm, product.mh_height_mm) == (2050, 2670)
    assert product.mh_length_mm == 5410


# --------------------------------------------------------------------------- #
# Everything one page yields
# --------------------------------------------------------------------------- #


def test_a_motorhome_page_yields_every_field() -> None:
    product = _parse("joa_motorhome_75tb.html")

    assert (product.manufacturer_range, product.model) == ("Motorhome", "75TB")
    assert product.mh_passenger_seats_inc_driver == 4
    assert product.berths == 2
    assert product.mh_payload_kilograms == 470
    assert product.rrp_pounds == 68400
    assert product.price_manually_sourced is False


def test_a_van_page_yields_every_field_but_the_price() -> None:
    product = _parse("joa_panel_van_54g.html")

    assert (product.manufacturer_range, product.model) == ("Van", "54G")
    assert product.mh_payload_kilograms == 610
    assert product.rrp_pounds == PRICES_NOT_ON_THE_SITE["54G"] == 58900
    assert product.price_manually_sourced is True


def test_seats_and_berths_are_the_standard_figures_on_every_page() -> None:
    """The fifth seatbelt is a £1,240 option and the drop-down bed a £1,760 one."""
    for name in PAGES:
        product = _parse(name)
        assert product.mh_passenger_seats_inc_driver == 4, name
        assert product.berths == 2, name


def test_the_mass_in_running_order_is_derived_from_the_payload() -> None:
    """Joa publish no MRO; their own note defines the payload as MAM minus MRO."""
    product = _parse("joa_motorhome_75tb.html")

    assert product.mtplm_kilograms == MTPLM_KILOGRAMS == 3500
    assert product.mro_kilograms == 3500 - 470 == 3030


def test_no_payload_means_no_derived_mass_rather_than_a_wrong_one() -> None:
    product = replace(_parse("joa_motorhome_75tb.html"), mh_payload_kilograms=None)

    assert product.mro_kilograms is None


# --------------------------------------------------------------------------- #
# The self-check
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "name", ["joa_motorhome_75tb.html", "joa_motorhome_60f.html", "joa_panel_van_54g.html"]
)
def test_a_length_matching_its_model_code_reconciles(name: str) -> None:
    reconciles, why_not = _reconciles(_parse(name))

    assert reconciles is True, why_not


def test_the_63t_states_its_neighbours_length_and_is_caught() -> None:
    """The page says 5,99 m, which is the 60G's. The Book says 6,36 m; FMLV holds 6360."""
    product = _parse("joa_panel_van_63t.html")
    assert product.mh_length_mm == 5990
    assert product.implied_length_mm == 6300

    reconciles, why_not = _reconciles(product)

    assert reconciles is False
    assert "310mm gap" in why_not


def test_the_tolerance_admits_every_real_vehicle() -> None:
    """The worst real miss is the 75Qs at 110mm — 75 implies 7500, they are 7390."""
    assert LENGTH_TOLERANCE_MM >= 110

    ok, _why = _reconciles(
        replace(_parse("joa_motorhome_75tb.html"), model="75Q", mh_length_mm=7390)
    )
    assert ok is True


def test_a_missing_length_has_nothing_to_contradict() -> None:
    reconciles, _why = _reconciles(
        replace(_parse("joa_motorhome_75tb.html"), mh_length_mm=None)
    )

    assert reconciles is True


def test_a_failed_length_check_does_not_cost_the_other_fields() -> None:
    """`collect` blanks the length and keeps the product — see `_reconciles`.

    The 63T's width, height and payload are all right and all disagree with what FMLV
    holds, so dropping it would lose two real corrections and make a live vehicle look
    discontinued.
    """
    product = replace(_parse("joa_panel_van_63t.html"), mh_length_mm=None)
    extracted = _build_extracted_motorhome(product, "https://example.test/")

    assert extracted.motorhome.mh_length_mm is None
    assert extracted.motorhome.mh_width_mm == 2050
    assert extracted.motorhome.mh_height_mm == 2670
    assert extracted.motorhome.mh_payload_kilograms == 500
    assert "mh_length_mm" not in extracted.provenance


def test_a_width_that_disagrees_with_the_panel_is_narrated() -> None:
    product = replace(_parse("joa_motorhome_75tb.html"), width_strip_mm=2050)

    assert "2050mm wide and the technical panel says 2300mm" in (
        width_disagreement(product) or ""
    )


def test_the_widths_agree_on_a_real_page() -> None:
    assert width_disagreement(_parse("joa_motorhome_75tb.html")) is None


# --------------------------------------------------------------------------- #
# Body type
# --------------------------------------------------------------------------- #


def test_every_motorhome_is_a_low_profile() -> None:
    """Joa build no A-class, and their only elevated bed is optional and over the lounge."""
    assert _parse("joa_motorhome_75tb.html").body_type is BodyType.COACH_BUILT_LOW_PROFILE
    assert _parse("joa_motorhome_60f.html").body_type is BodyType.COACH_BUILT_LOW_PROFILE


def test_every_van_is_a_high_top_and_the_pop_up_roof_does_not_change_that() -> None:
    product = _parse("joa_panel_van_54g.html")

    assert product.mh_height_mm > HIGH_TOP_ABOVE_MM
    assert product.body_type is BodyType.CAMPERVAN_HIGH_TOP


# --------------------------------------------------------------------------- #
# The equipment overlay
# --------------------------------------------------------------------------- #


def test_the_equipment_overlay_is_read_not_the_navigation_one() -> None:
    """Every page has two overlays and the first is the site's nav menu.

    Taking the first gave every model the nav strip — "Panel van 63T / L6,36m - Twin
    beds / Panel van 60G / L5,99m - Double bed" — which put twin beds on all ten,
    including the two whose own nav entry says double.
    """
    equipment = parse_equipment(_page("joa_panel_van_54g.html"))

    assert "95-litre low compression refrigerator with drawer" in equipment
    assert not [line for line in equipment if line.startswith("L6,36m")]
    assert "Our Panel vans" not in equipment


def test_a_page_with_no_equipment_overlay_yields_nothing() -> None:
    assert parse_equipment("<html><body><p>nothing here</p></body></html>") == ()


# --------------------------------------------------------------------------- #
# Habitation findings
# --------------------------------------------------------------------------- #


def _built(name: str):
    page = _page(name)
    product = _parse(name)
    return _build_extracted_motorhome(
        product, "https://example.test/", parse_equipment(page), floorplan_for(page, product.model)
    )


@pytest.mark.parametrize("name", list(PAGES))
def test_every_model_reads_as_blown_air_from_its_own_labelled_row(name: str) -> None:
    extracted = _built(name)

    assert extracted.motorhome.heating is Heating.BLOWN_AIR
    assert "Truma" in extracted.provenance["heating"].snippet


def test_the_fridge_comes_from_the_labelled_row_not_the_overlay() -> None:
    """The motorhome overlay's chassis section carries a stray fridge line.

    Pilote's Book has "90-litre diesel tank" where the site says "90-litre high
    compression refrigerator"; the labelled row says 133 litres and agrees with the Book.
    """
    extracted = _built("joa_motorhome_75tb.html")

    assert extracted.motorhome.refrigeration is Refrigeration.FRIDGE_FREEZER
    assert "133-litres" in extracted.provenance["refrigeration"].snippet
    assert "90-litre" not in extracted.provenance["refrigeration"].snippet


def test_the_twin_bed_layouts_are_the_only_ones_that_name_a_bed() -> None:
    """"Bed insert between twin beds" is standard on 70T, 75T and 75TB alone."""
    assert _built("joa_motorhome_75tb.html").motorhome.bed_types == [BedType.FIXED_SEPARATE]
    assert _built("joa_motorhome_60f.html").motorhome.bed_types == []
    assert _built("joa_panel_van_54g.html").motorhome.bed_types == []


@pytest.mark.parametrize("name", list(PAGES))
def test_no_model_names_a_microwave(name: str) -> None:
    extracted = _built(name)

    assert extracted.motorhome.microwave is None
    assert "no microwave" in extracted.provenance["microwave"].snippet


def test_habitation_is_left_alone_when_no_equipment_is_supplied() -> None:
    extracted = _build_extracted_motorhome(
        _parse("joa_motorhome_75tb.html"), "https://example.test/"
    )

    assert extracted.motorhome.bed_types == []
    assert extracted.motorhome.microwave is None
    assert "microwave" not in extracted.provenance
    # The two labelled rows are on the product itself, so these still read.
    assert extracted.motorhome.heating is Heating.BLOWN_AIR


# --------------------------------------------------------------------------- #
# Floorplans
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", list(PAGES))
def test_every_page_carries_its_own_layout_drawing(name: str) -> None:
    product = _parse(name)

    url = floorplan_for(_page(name), product.model)

    assert url is not None
    assert url.endswith(f"joa-site-implant-{product.model.lower()}.jpg")


def test_a_neighbours_drawing_is_never_returned() -> None:
    """Every page carries the whole set in its nav strip, so the code has to match."""
    assert floorplan_for(_page("joa_panel_van_54g.html"), "60G").endswith("-60g.jpg")
    assert floorplan_for(_page("joa_panel_van_54g.html"), "99Z") is None


# --------------------------------------------------------------------------- #
# What reaches the reviewer
# --------------------------------------------------------------------------- #


def test_the_manually_sourced_figures_say_so_in_their_provenance() -> None:
    extracted = _built("joa_panel_van_54g.html")

    assert "MANUALLY SOURCED" in extracted.provenance["mtplm_kilograms"].snippet
    assert "MANUALLY SOURCED" in extracted.provenance["rrp_pounds"].snippet


def test_a_page_price_is_not_labelled_manually_sourced() -> None:
    extracted = _built("joa_motorhome_75tb.html")

    assert "MANUALLY SOURCED" not in extracted.provenance["rrp_pounds"].snippet
    assert "starting from £68,400" in extracted.provenance["rrp_pounds"].snippet


def test_both_halves_of_the_identity_carry_provenance() -> None:
    """`compare_fields` only walks fields that have it, so a bare model is invisible."""
    extracted = _built("joa_motorhome_75tb.html")

    assert "manufacturer_range" in extracted.provenance
    assert "model" in extracted.provenance


def test_the_asserted_fields_carry_provenance_too() -> None:
    """Bürstner's lesson: a value set without provenance is silent in both directions."""
    extracted = _built("joa_panel_van_54g.html")

    assert "Fiat" in extracted.provenance["base_vehicle_manufacturer"].snippet
    assert "body_type" in extracted.provenance
    assert extracted.motorhome.base_vehicle_manufacturer == "Fiat"


# --------------------------------------------------------------------------- #
# Registration
# --------------------------------------------------------------------------- #


def test_the_adapter_is_registered_under_the_name_fmlv_holds() -> None:
    assert joa.MANUFACTURER == "Joa by Pilote"
    assert adapter_for("Joa by Pilote", VehicleClass.MOTORHOME) is joa
