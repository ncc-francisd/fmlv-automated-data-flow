"""Tests for the Benimar adapter's pure parsing functions, against real pages.

Fixtures are the four real importer range pages fetched 14 September 2026 with `<script>`
and `<style>` removed — see `docs/adapters/benimar.md`. All four, because a Marquis page is
a *range* rather than a product and because **the four do not share one template**:

* **Primero** — the older template, which shouts `OVERALL LENGTH`, heads its table
  `Weights and Dimensions`, prints no MIRO and gives a payload per chassis.
* **Mileo** — the newer one: title-case labels, a bare `Dimensions` heading, and MIRO
  printed beside MTPLM and payload.
* **Tessoro** — six layouts, the most on any page, and the only Ford.
* **Benivan** — the campervan, whose `Optional` pop-top bed and mirrors-folded width are
  both traps.

No network here.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.adapters import adapter_for, benimar, marquis
from src.adapters.benimar import (
    BASE_VEHICLES,
    BODY_TYPES,
    EXPECTED_LAYOUTS,
    BenimarProduct,
    _bed_lines,
    _build_extracted_motorhome,
    _discrepancies,
    _equipment_lines,
    _reconciles,
    find_range_urls,
    layout_blocks,
    plain_text,
)
from src.product_model.enums import BodyType

FIXTURES = Path(__file__).parent / "fixtures"

PAGES: dict[str, str] = {
    "benimar_primero.html": "https://www.marquisleisure.co.uk/benimar-primero-2026-motorhome-range",
    "benimar_mileo.html": "https://www.marquisleisure.co.uk/benimar-mileo-2026-motorhome-range",
    "benimar_tessoro.html": "https://www.marquisleisure.co.uk/benimar-tessoro-2026-motorhome-range",
    "benimar_benivan.html": "https://www.marquisleisure.co.uk/benimar-benivan-2026-campervan-range",
}

ALL_KEYS = tuple(key for key, _label in benimar.DEFAULT_RANGES)


def _page(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _layouts(name: str) -> list[BenimarProduct]:
    return layout_blocks(_page(name), PAGES[name])


def _by_model(name: str) -> dict[str, BenimarProduct]:
    return {p.model: p for p in _layouts(name)}


def _every_layout() -> list[BenimarProduct]:
    return [p for name in PAGES for p in _layouts(name)]


# --------------------------------------------------------------------------- #
# The roster
# --------------------------------------------------------------------------- #


def _index(*slugs: str) -> str:
    return "".join(f'<a href="/{s}">x</a>' for s in slugs)


def test_only_range_pages_are_taken() -> None:
    """The requester's standing warning about this site is to avoid the used-stock pages."""
    html_ = _index(
        "benimar-mileo-2026-motorhome-range",
        "used-benimar-mileo-for-sale",
        "new-motorhomes/benimar",
    )

    assert find_range_urls(html_, ALL_KEYS) == [
        "https://www.marquisleisure.co.uk/benimar-mileo-2026-motorhome-range"
    ]


def test_a_single_range_reads_only_its_own_page() -> None:
    html_ = _index(
        "benimar-mileo-2026-motorhome-range",
        "benimar-benivan-2026-campervan-range",
    )

    assert find_range_urls(html_, ("benivan",)) == [
        "https://www.marquisleisure.co.uk/benimar-benivan-2026-campervan-range"
    ]


def test_the_four_pages_carry_sixteen_layouts_between_them() -> None:
    """A page is a range, not a product, and the count is the main structural defence."""
    counts = {name: len(_layouts(name)) for name in PAGES}

    assert sum(counts.values()) == EXPECTED_LAYOUTS == 16
    assert counts["benimar_primero.html"] == 4
    assert counts["benimar_mileo.html"] == 4
    assert counts["benimar_tessoro.html"] == 6
    assert counts["benimar_benivan.html"] == 2


# --------------------------------------------------------------------------- #
# Two templates, which is what the first build got wrong
# --------------------------------------------------------------------------- #


def test_a_title_case_heading_is_read() -> None:
    """The first build required an upper-case heading and collected **zero** of sixteen.

    Mobilvetta shouts `K.YACHT 59`; Benimar writes `Primero 201`. The block reader now
    anchors on the marker instead of on the shape of the name.
    """
    assert "Primero 201 Weights and Dimensions" in plain_text(_page("benimar_primero.html"))
    assert "201" in _by_model("benimar_primero.html")


def test_both_templates_are_read() -> None:
    """Marquis are mid-redesign: `Weights and Dimensions` on one page, `Dimensions` on
    another, with the labels shouted on the first and title-case on the second."""
    primero, mileo = plain_text(_page("benimar_primero.html")), plain_text(
        _page("benimar_mileo.html")
    )

    assert "OVERALL LENGTH" in primero
    assert "OVERALL LENGTH" not in mileo
    assert _by_model("benimar_primero.html")["201"].mh_length_mm == 5950
    assert _by_model("benimar_mileo.html")["243"].mh_length_mm == 6990


def test_the_garage_aperture_does_not_open_a_block() -> None:
    """The older template also says `GARAGE APERTURE DIMENSIONS (mm)`.

    A bare `Dimensions` marker without its lookahead matched that too, doubling every
    Primero layout into a second, empty block.
    """
    assert "GARAGE APERTURE DIMENSIONS" in plain_text(_page("benimar_primero.html")).upper()
    assert len(_layouts("benimar_primero.html")) == 4


def test_every_layout_is_priced() -> None:
    """The price is the last thing in a block, so a body must run to the next marker.

    Stopping a lookback short of it lost three of the four Primero prices.
    """
    assert all(p.rrp_pounds is not None for p in _every_layout())
    assert _by_model("benimar_primero.html")["201"].rrp_pounds == 63_090
    assert _by_model("benimar_benivan.html")["122"].rrp_pounds == 61_995


def test_every_model_is_the_bare_layout_code() -> None:
    assert {p.model for p in _every_layout()} == {
        "201", "202", "282", "286",
        "243", "294",
        "413", "463", "481", "487", "840", "861",
        "122", "144",
    }


def test_the_page_banner_is_not_read_as_the_model() -> None:
    """The first block on every page has the page's own banner welded to its front."""
    assert (
        marquis.range_and_model(
            "2026 MILEO COACHBUILT MOTORHOME RANGE Mileo 243", benimar.RANGE_PREFIXES
        )
        == ("Mileo", "243")
    )


# --------------------------------------------------------------------------- #
# Everything one block yields
# --------------------------------------------------------------------------- #


def test_a_layout_on_the_newer_template_yields_every_field() -> None:
    product = _by_model("benimar_mileo.html")["243"]

    assert product.manufacturer_range == "Mileo"
    assert product.berths == 4
    assert product.mh_passenger_seats_inc_driver == 4
    assert product.mh_length_mm == 6990
    assert product.mh_width_mm == 2300
    assert product.mh_height_mm == 2890
    assert product.mtplm_kilograms == 3650
    assert product.published_mro_kilograms == 3149
    assert product.mh_payload_kilograms == 501
    assert product.rrp_pounds == 82_995


def test_a_layout_on_the_older_template_yields_every_field() -> None:
    """The Primero page prints no MIRO and no `(EXC TV AERIAL)` beside its height."""
    product = _by_model("benimar_primero.html")["201"]

    assert product.berths == 2
    assert product.mh_passenger_seats_inc_driver == 4
    assert product.mh_length_mm == 5950
    assert product.mh_width_mm == 2300
    assert product.mh_height_mm == 2890
    assert product.mtplm_kilograms == 3500
    assert product.published_mro_kilograms is None
    assert product.mh_payload_kilograms == 764


def test_the_manual_column_is_taken_not_the_automatic() -> None:
    """`MTPLM 3650kg 4400kg` and `MIRO 3149kg 3189kg` — the first is the base vehicle."""
    product = _by_model("benimar_mileo.html")["243"]

    assert "MTPLM 3650kg 4400kg" in plain_text(_page("benimar_mileo.html"))
    assert (product.mtplm_kilograms, product.published_mro_kilograms) == (3650, 3149)


def test_the_lighter_chassis_is_taken_not_the_heavier() -> None:
    """`MTPLM 3500kg / 3650kg` — the 3500 is what the quoted OTR price buys."""
    product = _by_model("benimar_primero.html")["201"]

    assert "MTPLM 3500kg / 3650kg" in plain_text(_page("benimar_primero.html"))
    assert (product.mtplm_kilograms, product.mh_payload_kilograms) == (3500, 764)


def test_a_berth_range_takes_the_lower_figure() -> None:
    """`Berths 2 | Optional 4 Berth Pop Top` — the extra two need an option bought."""
    assert "Optional 4 Berth Pop Top" in plain_text(_page("benimar_benivan.html"))
    assert _by_model("benimar_benivan.html")["144"].berths == 2


def test_the_pop_top_masses_are_not_taken() -> None:
    """Benivan prints `MIRO` then `MIRO (Pop Top)`; only the first is the base vehicle."""
    product = _by_model("benimar_benivan.html")["144"]

    assert "MIRO (Pop Top)" in plain_text(_page("benimar_benivan.html"))
    assert (product.published_mro_kilograms, product.mh_payload_kilograms) == (2834, 666)


def test_the_published_mass_wins_over_the_derived_one() -> None:
    product = _by_model("benimar_mileo.html")["243"]

    assert product.mro_kilograms == product.published_mro_kilograms == 3149
    snippet = _build_extracted_motorhome(product).provenance["mro_kilograms"].snippet
    assert "agrees with it" in snippet


def test_no_published_mass_is_derived_and_says_so() -> None:
    product = _by_model("benimar_primero.html")["201"]

    assert product.mro_kilograms == 3500 - 764 == 2736
    snippet = _build_extracted_motorhome(product).provenance["mro_kilograms"].snippet
    assert "prints no MIRO" in snippet


def test_no_payload_and_no_published_mass_means_no_mass() -> None:
    product = replace(
        _by_model("benimar_primero.html")["201"], mh_payload_kilograms=None
    )

    assert product.mro_kilograms is None


# --------------------------------------------------------------------------- #
# The self-check the Mobilvetta survey said did not exist
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", sorted(PAGES))
def test_every_real_layout_reconciles(name: str) -> None:
    for product in _layouts(name):
        reconciles, why_not = _reconciles(product)
        assert reconciles is True, f"{product.label}: {why_not}"


def test_the_newer_template_really_does_check_itself() -> None:
    """Twelve of the sixteen print MIRO, MTPLM and payload, and those must close."""
    checked = [p for p in _every_layout() if len(p.base_mro_routes) > 1]

    assert len(checked) == 12
    assert all(p.published_mro_kilograms is not None for p in checked)


def test_a_mass_from_the_wrong_column_is_caught() -> None:
    """The automatic column sits 40kg away, which is what this exists to catch."""
    product = replace(_by_model("benimar_mileo.html")["243"], base_mro_routes=(3189, 3149))

    reconciles, why_not = _reconciles(product)

    assert reconciles is False
    assert "wrong column" in why_not


def test_benimars_own_four_kilo_rounding_is_kept_and_narrated() -> None:
    """Mileo 294 prints MTPLM 3650, MIRO 3254 and payload 400, which miss by 4kg.

    Too small to be a misread and no reason to withhold a vehicle Marquis really sell, so
    it goes forward with the discrepancy said out loud.
    """
    product = _by_model("benimar_mileo.html")["294"]

    assert _reconciles(product)[0] is True
    assert product.base_mro_routes == (3254, 3250)
    assert any("rounding" in note for note in _discrepancies(product))


def test_benimars_own_chassis_disagreement_is_kept_and_narrated() -> None:
    """Primero 282 gives the heavier chassis 100kg more payload where it gains 150kg.

    The wrong figure is in a row this pipeline does not record, so it cannot drop the
    vehicle — but it is reported.
    """
    product = _by_model("benimar_primero.html")["282"]

    assert _reconciles(product)[0] is True
    assert sorted(set(product.chassis_mro_routes)) == [3026, 3076]
    assert any("chassis options imply" in note for note in _discrepancies(product))


def test_a_layout_that_agrees_with_itself_is_not_narrated() -> None:
    assert _discrepancies(_by_model("benimar_mileo.html")["243"]) == []


def test_a_block_with_a_heading_and_no_figures_is_dropped() -> None:
    """That means the page's shape changed under the parse, not that a vehicle is empty."""
    product = BenimarProduct(source_url="x", manufacturer_range="Mileo", model="243")

    reconciles, why_not = _reconciles(product)

    assert reconciles is False
    assert "shape has probably changed" in why_not


# --------------------------------------------------------------------------- #
# The width, which is the mirrors on a van and the body on a coachbuilt
# --------------------------------------------------------------------------- #


def test_a_coachbuilt_records_the_mirrors_folded_width() -> None:
    """At 2300mm the habitation body overhangs a Ducato's folded mirrors."""
    product = _by_model("benimar_mileo.html")["243"]

    assert product.recorded_width_mm == product.mh_width_mm == 2300


def test_a_campervan_records_no_width_at_all() -> None:
    """2260mm is a Ducato's folded mirrors, not its 2050mm body.

    The requester's ruling: leave it blank rather than record a figure that includes the
    mirrors. FMLV already holds 2050 for both of these, and emitting nothing keeps it.
    """
    for product in _layouts("benimar_benivan.html"):
        assert product.mh_width_mm == 2260
        assert product.recorded_width_mm is None
        assert _build_extracted_motorhome(product).motorhome.mh_width_mm is None


def test_no_width_provenance_is_recorded_for_a_campervan() -> None:
    extracted = _build_extracted_motorhome(_by_model("benimar_benivan.html")["144"])

    assert "mh_width_mm" not in extracted.provenance


# --------------------------------------------------------------------------- #
# Habitation, which is findings rather than proposals
# --------------------------------------------------------------------------- #


def test_the_beds_come_from_the_layouts_own_list() -> None:
    """A page is a range, so a bed named in the equipment list could be another layout's."""
    assert _bed_lines(
        "Bed Sizes Double Drop Down Bed 1400mm x 1900mm | 4'6'' x 6'2'' "
        "Double Rear Bed 1390mm x 2000mm | 4'6'' x 6'6'' # Garage dimensions"
    ) == ["Double Drop Down Bed", "Double Rear Bed"]


def test_a_bed_name_containing_an_x_survives() -> None:
    """Excluding `x` from a bed's name turned `FIXED REAR BED` into `ED REAR BED`."""
    assert _bed_lines("Bed Sizes FIXED REAR BED 1390mm X 2000mm | 4'6'' X 6'6''") == [
        "FIXED REAR BED"
    ]


def test_an_optional_bed_is_not_read_as_standard() -> None:
    """Both Benivan layouts offer an elevating roof bed the buyer may not have bought."""
    beds = _bed_lines(
        "Bed Sizes Double Rear Bed 1860mm x 1490mm | 6'1'' x 4'8'' "
        "Optional Elevating Roof Bed 2000mm x 1300mm | 6'5'' x 4'2''"
    )

    assert beds == ["Double Rear Bed"]


def test_the_equipment_list_never_contributes_a_bed() -> None:
    assert not any(
        "bed" in line.lower() for line in _equipment_lines(_page("benimar_primero.html"))
    )


def test_the_range_equipment_settles_the_habitation_fields() -> None:
    motorhome = _build_extracted_motorhome(_by_model("benimar_primero.html")["201"]).motorhome

    assert motorhome.refrigeration is not None
    assert motorhome.heating is not None
    assert motorhome.shower_toilet_separated is True


def test_a_habitation_finding_quotes_the_page() -> None:
    """A reviewer types these in by hand, so the snippet has to be Benimar's own words."""
    snippet = (
        _build_extracted_motorhome(_by_model("benimar_primero.html")["201"])
        .provenance["shower_toilet_separated"]
        .snippet
    )

    assert "Fully separate shower" in snippet


def test_the_microwave_is_not_asserted_where_the_copy_is_silent() -> None:
    """Silence is not a negative — the Primero list never mentions one."""
    motorhome = _build_extracted_motorhome(_by_model("benimar_primero.html")["201"]).motorhome

    assert motorhome.microwave is None


# --------------------------------------------------------------------------- #
# What else reaches the reviewer
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("name", "model", "expected"),
    [
        ("benimar_primero.html", "201", BodyType.COACH_BUILT_LOW_PROFILE),
        ("benimar_mileo.html", "243", BodyType.COACH_BUILT_LOW_PROFILE),
        ("benimar_tessoro.html", "413", BodyType.COACH_BUILT_LOW_PROFILE),
        ("benimar_benivan.html", "144", BodyType.CAMPERVAN_HIGH_TOP),
    ],
)
def test_the_body_type_follows_the_range(name: str, model: str, expected: BodyType) -> None:
    assert _by_model(name)[model].body_type is expected


def test_the_benivan_clears_the_high_top_threshold() -> None:
    """A campervan is a high top above 2300mm, and both Benivans are 2650mm."""
    assert all(p.mh_height_mm == 2650 for p in _layouts("benimar_benivan.html"))


def test_the_tessoro_is_a_ford_and_the_rest_are_fiats() -> None:
    """The base vehicle is per range here, unlike Mobilvetta and Panama."""
    assert BASE_VEHICLES["Tessoro"] == "Ford"
    assert {r: v for r, v in BASE_VEHICLES.items() if r != "Tessoro"} == {
        "Primero": "Fiat",
        "Mileo": "Fiat",
        "Benivan": "Fiat",
    }
    extracted = _build_extracted_motorhome(_by_model("benimar_tessoro.html")["413"])
    assert extracted.motorhome.base_vehicle_manufacturer == "Ford"


def test_every_range_has_a_body_type_and_a_base_vehicle() -> None:
    ranges = {p.manufacturer_range for p in _every_layout()}

    assert ranges == set(BODY_TYPES) == set(BASE_VEHICLES)


def test_the_seat_provenance_explains_the_pages_own_word() -> None:
    snippet = (
        _build_extracted_motorhome(_by_model("benimar_mileo.html")["243"])
        .provenance["mh_passenger_seats_inc_driver"]
        .snippet
    )

    assert "BELTS" in snippet
    assert "belted travel seat" in snippet


def test_the_price_names_marquis_as_the_seller_that_sets_it() -> None:
    snippet = (
        _build_extracted_motorhome(_by_model("benimar_primero.html")["201"])
        .provenance["rrp_pounds"]
        .snippet
    )

    assert "exclusive UK distributor" in snippet


# --------------------------------------------------------------------------- #
# Wiring
# --------------------------------------------------------------------------- #


def test_the_adapter_is_registered_under_its_fmlv_name() -> None:
    assert adapter_for("Benimar Ocarsa S.A.U.") is benimar
