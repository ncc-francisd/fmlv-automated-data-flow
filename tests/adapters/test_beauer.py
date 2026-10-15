"""River Motorhomes' Beauer pages, captured 15 October 2026.

The fixtures are each page's own markup with scripts, styles and SVGs removed; each was
checked at capture time to parse identically to the whole page.

The tests that matter here are the ones about what is *not* recorded. Every model
publishes two widths because the body telescopes, and every model's heating is an option.
Both read exactly like ordinary data.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters.beauer import (
    EXPECTED_MODELS,
    FACTORY_WEIGHTS,
    MANUFACTURER,
    MANUFACTURER_DISPLAY_NAME,
    OPTIONS_HEADING,
    VEHICLE_CLASS,
    Model,
    _notes,
    _reconciles,
    berths_from_prose,
    body_type_for,
    build_extracted,
    extended_dimensions,
    find_model_paths,
    model_name,
    parse_model,
    parse_price,
    parse_sections,
    price_note,
    standard_equipment,
    technical_data,
)
from src.product_model.enums import CaravanBodyType, Refrigeration
from src.vehicle_class import VehicleClass

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def index() -> str:
    return _fixture("beauer_index.html")


@pytest.fixture(scope="module")
def x4() -> str:
    return _fixture("beauer_x4.html")


@pytest.fixture(scope="module")
def x6() -> str:
    return _fixture("beauer_x6.html")


@pytest.fixture(scope="module")
def x8() -> str:
    return _fixture("beauer_x8.html")


def _model(html: str) -> Model:
    parsed = parse_model(html, "https://www.rivermotorhomes.co.uk/beauer-new/x/")
    assert parsed is not None
    return parsed


# --- identity ----------------------------------------------------------------------------


def test_beauer_is_a_caravan_brand() -> None:
    assert MANUFACTURER == "Beauer"
    assert MANUFACTURER_DISPLAY_NAME == "Beauer"
    assert VEHICLE_CLASS is VehicleClass.CARAVAN


def test_the_index_links_every_model(index: str) -> None:
    assert find_model_paths(index) == [
        "/beauer-new/beauer-x4/",
        "/beauer-new/beauer-x6/",
        "/beauer-new/beauer-x8/",
    ]
    assert EXPECTED_MODELS == 3


def test_the_name_comes_from_the_heading(x4: str, x8: str) -> None:
    assert model_name(x4) == "X4"
    assert model_name(x8) == "X8"


def test_the_model_name_is_carried_twice(x4: str) -> None:
    """Beauer give these no range, and Nova will not take a blank."""
    built = build_extracted(_model(x4), basis="test")
    assert built.caravan.manufacturer_range == "X4"
    assert built.caravan.model == "X4"


# --- the telescoping body, which is the whole risk ------------------------------------------


def test_the_travelling_dimensions_are_the_ones_recorded(x4: str) -> None:
    model = _model(x4)
    assert (model.length_mm, model.width_mm, model.height_mm) == (3850, 1950, 2650)


def test_the_extended_width_is_read_only_so_it_can_be_refused(x4: str, x8: str) -> None:
    """4600mm is wider than a motorway lane and would look like an ordinary figure."""
    assert extended_dimensions(x4)["width"] == 4600
    assert extended_dimensions(x8)["width"] == 4800
    built = build_extracted(_model(x4), basis="test")
    assert built.caravan.overall_width_mm == 1950


def test_neither_the_larger_nor_the_smaller_figure_is_the_rule(x4: str) -> None:
    """The extended WIDTH is larger than the travelling one and the extended HEIGHT is
    smaller, so any rule based on magnitude is wrong on one of the two. The split has to
    be on the heading."""
    model = _model(x4)
    extended = extended_dimensions(x4)
    assert extended["width"] > model.width_mm
    assert extended["height"] < model.height_mm


def test_the_two_dimension_blocks_use_the_same_labels(x4: str) -> None:
    """Which is why they are keyed by sub-heading — merging them overwrites the width."""
    technical = technical_data(x4)
    assert "Width" in technical["Dimensions"]
    assert "Width" in technical["Dimensions when extended"]
    assert technical["Dimensions"]["Width"] != technical["Dimensions when extended"]["Width"]


# --- the self-check -------------------------------------------------------------------------


def test_beauers_own_arithmetic_closes_on_every_model(x4: str, x6: str, x8: str) -> None:
    for html in (x4, x6, x8):
        model = _model(html)
        assert model.fully_equipped_kilograms + model.payload_kilograms == model.gross_kilograms
        ok, _ = _reconciles(model)
        assert ok is True


def test_the_dealers_figures_are_checked_against_the_manufacturers(x4: str) -> None:
    """The justification for reading specifications off a dealer at all."""
    model = _model(x4)
    published = FACTORY_WEIGHTS["X4"]
    assert model.gross_kilograms == published.gross_kilograms
    assert model.fully_equipped_kilograms == published.fully_equipped_kilograms


def test_a_page_that_has_drifted_from_beauers_own_figures_is_dropped() -> None:
    drifted = Model(
        url="http://x", name="X4",
        fully_equipped_kilograms=1250, payload_kilograms=150, gross_kilograms=1400,
    )
    ok, basis = _reconciles(drifted)
    assert ok is False
    assert "Beauer themselves publish" in basis


def test_masses_that_do_not_add_up_are_dropped() -> None:
    ok, basis = _reconciles(
        Model(url="http://x", name="X4",
              fully_equipped_kilograms=1200, payload_kilograms=150, gross_kilograms=1999)
    )
    assert ok is False
    assert "does not close" in basis


def test_an_unknown_model_still_passes_but_says_so() -> None:
    """A fourth Beauer must not be dropped merely for being new."""
    ok, basis = _reconciles(
        Model(url="http://x", name="X10",
              fully_equipped_kilograms=3000, payload_kilograms=200, gross_kilograms=3200)
    )
    assert ok is True
    assert "not a model this adapter has seen before" in basis


# --- equipment, read by section ----------------------------------------------------------------


def test_the_options_accordion_exists_on_every_model(x4: str, x6: str, x8: str) -> None:
    for html in (x4, x6, x8):
        assert OPTIONS_HEADING in parse_sections(html)


def test_the_heating_is_an_option_and_is_not_recorded(x4: str) -> None:
    """`Heating + 2,000 W Webasto gas or electric underfloor water heater` reads exactly
    like standard equipment and sits in Options. Read whole, every Beauer would get wet
    underfloor heating it has not got."""
    sections = parse_sections(x4)
    assert any("Webasto" in line for line in sections[OPTIONS_HEADING])
    assert not any("Webasto" in line for line in standard_equipment(sections))
    assert build_extracted(_model(x4), basis="test").caravan.heating is None


def test_the_microwave_is_an_option_too(x4: str) -> None:
    sections = parse_sections(x4)
    assert any("Microwave" in line for line in sections[OPTIONS_HEADING])
    assert build_extracted(_model(x4), basis="test").caravan.microwave is None


def test_the_cookie_banner_is_not_read_as_a_section(x4: str) -> None:
    """Its container reuses `accordion-header`, so its "heading" is hundreds of words of
    consent copy and branch opening hours."""
    assert all(len(heading) <= 60 for heading in parse_sections(x4))
    assert not any("cookie" in heading.lower() for heading in parse_sections(x4))


def test_a_bare_refrigerator_is_a_fridge_freezer(x4: str) -> None:
    """The settled rule: very few leisure vehicles lack the freezer compartment."""
    built = build_extracted(_model(x4), basis="test")
    assert built.caravan.refrigeration is Refrigeration.FRIDGE_FREEZER


def test_a_water_heater_is_not_reported_as_unclear_heating(x4: str) -> None:
    """Saying "the kind is unclear" about a 6-litre water heater sends a reviewer looking
    for a space-heating system that is not there."""
    notes = " ".join(_notes(_model(x4)))
    assert "NO HEATING IS STANDARD" in notes
    assert "heats water, not the caravan" in notes


# --- berths ---------------------------------------------------------------------------------------


def test_the_berths_are_corroborated_by_the_models_name(x4: str, x6: str, x8: str) -> None:
    assert _model(x4).berths == 4
    assert _model(x6).berths == 6
    assert _model(x8).berths == 8


def test_a_berth_count_that_contradicts_the_name_is_refused() -> None:
    berths, basis = berths_from_prose("<p>Sleeps up to 6 people</p>", "X4")
    assert berths is None
    assert "disagree" in basis


def test_a_page_stating_no_capacity_proposes_no_berths() -> None:
    berths, basis = berths_from_prose("<p>A lovely caravan</p>", "X4")
    assert berths is None
    assert "no sleeping capacity" in basis


# --- price ------------------------------------------------------------------------------------------


def test_the_single_price_is_read(x4: str, x6: str, x8: str) -> None:
    assert parse_price(x4) == 39990
    assert parse_price(x6) == 74990
    assert parse_price(x8) == 109990


def test_the_price_matching_the_euro_figure_is_flagged_not_refused(x4: str) -> None:
    """River ask £39,990 and Beauer 39,990 euros — the same digits with the symbol
    changed. It is recorded, because they are the UK seller, and reported every run."""
    model = _model(x4)
    note = price_note(model)
    assert note is not None
    assert "£34,774" in note
    assert build_extracted(model, basis="test").caravan.rrp_pounds == 39990


def test_a_price_that_differs_from_the_euro_figure_is_not_flagged() -> None:
    quiet = Model(url="http://x", name="X4", rrp_pounds=34_995)
    assert price_note(quiet) is None


# --- what is built -------------------------------------------------------------------------------------


def test_the_payload_is_never_recorded(x4: str) -> None:
    """Beauer publish one payload and it is the total, not the personal-effects half."""
    built = build_extracted(_model(x4), basis="test")
    assert built.caravan.personal_effects_payload_kilograms is None
    assert built.caravan.optional_equipment_payload_kilograms is None
    assert "personal_effects_payload_kilograms" not in built.provenance


def test_no_body_length_is_proposed(x4: str) -> None:
    """One length is published and it does not say whether it includes the drawbar."""
    built = build_extracted(_model(x4), basis="test")
    assert built.caravan.shipping_length_mm == 3850
    assert built.caravan.exterior_body_length_mm is None
    assert "exterior_body_length_mm" not in built.provenance


def test_only_the_x8_is_a_twin_axle(x4: str, x6: str, x8: str) -> None:
    """`AL-KO dual-axle chassis`, which only the X8's chassis section names."""
    assert _model(x4).twin_axle is False
    assert _model(x6).twin_axle is False
    assert _model(x8).twin_axle is True


def test_an_expanding_caravan_is_still_rigid() -> None:
    body_type, reason = body_type_for("X4", 1350)
    assert body_type is CaravanBodyType.RIGID
    assert "no canvas" in reason
    assert "1250kg" in reason
