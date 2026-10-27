"""Bespoke's own WordPress API, captured 27 October 2026.

The fixtures are the `bl_model` and `bl_range` responses with the fields this adapter does
not read stripped out; the trim was checked at capture time to parse identically.

Rebuilt that day because Bespoke replaced their website and their range at once. Several
of these tests exist to stop the **previous** failure recurring: that adapter read three
pages which now 404, fell back on hardcoded variant names, and reported a passing count
check over a roster that no longer existed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.adapters.bespoke import (
    EXPECTED_PRODUCTS,
    IDENTITY,
    MANUFACTURER,
    MANUFACTURER_DISPLAY_NAME,
    MODELS_URL,
    RANGES_URL,
    BespokeModel,
    _notes,
    _reconciles,
    build_extracted,
    equipment_lines,
    identity_for,
    parse_models,
    parse_ranges,
    seats_from,
)
from src.product_model.enums import Refrigeration

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def ranges() -> dict[int, str]:
    return parse_ranges(_fixture("bespoke_ranges.json"))


@pytest.fixture(scope="module")
def models(ranges: dict[int, str]) -> list[BespokeModel]:
    return parse_models(_fixture("bespoke_models.json"), ranges)


def _named(models: list[BespokeModel], name: str) -> BespokeModel:
    return next(model for model in models if model.name == name)


# --- identity ------------------------------------------------------------------------------


def test_the_manufacturer_keeps_its_two_names() -> None:
    """Both lists say `Bespoke NI`; the site brands itself `Bespoke`."""
    assert MANUFACTURER == "Bespoke NI"
    assert MANUFACTURER_DISPLAY_NAME == "Bespoke"


def test_the_api_is_the_source() -> None:
    assert MODELS_URL.endswith("/wp-json/wp/v2/bl_model?per_page=100")
    assert RANGES_URL.endswith("/wp-json/wp/v2/bl_range?per_page=100")


def test_the_five_current_models_are_read(models: list[BespokeModel]) -> None:
    assert sorted(model.name for model in models) == [
        "Crafter Edition",
        "Explore 4",
        "Explore 4 Hybrid",
        "Explore 5",
        "Explore 5 Hybrid",
    ]
    assert EXPECTED_PRODUCTS == 5


def test_the_roster_is_never_hardcoded(models: list[BespokeModel]) -> None:
    """The previous adapter fell back on hardcoded variant names when its pages went, and
    reported nine products that no longer existed. `IDENTITY` only splits a name the API
    returned; it cannot invent one."""
    assert set(IDENTITY) == {model.name for model in models}


def test_an_unknown_model_still_gets_an_identity() -> None:
    """A sixth model must come through with a usable name so the count check flags it,
    rather than being dropped and so never noticed."""
    assert identity_for("Explore 6") == ("Explore 6", "Explore 6")


def test_the_identity_split_follows_bespokes_naming() -> None:
    assert identity_for("Explore 4 Hybrid") == ("Explore", "4 Hybrid")
    assert identity_for("Crafter Edition") == ("Crafter Edition", "Crafter Edition")


# --- the ranges name the base vehicle, not an FMLV range -------------------------------------


def test_both_ranges_are_volkswagen(ranges: dict[int, str]) -> None:
    """The Ford Transit Custom that three of FMLV's rows are built on is gone."""
    assert sorted(ranges.values()) == ["VW Crafter", "VW Transporter"]


def test_the_base_vehicle_comes_from_the_range(models: list[BespokeModel]) -> None:
    built = build_extracted(_named(models, "Explore 4"), basis="b")
    assert built.motorhome.base_vehicle_manufacturer == "VW"
    assert "VW Transporter" in built.provenance["base_vehicle_manufacturer"].snippet


def test_a_model_with_no_range_is_dropped() -> None:
    """Its base vehicle could not be derived and nothing says which van it is."""
    ok, basis = _reconciles(BespokeModel(name="Explore 9", slug="x", url="http://x"))
    assert ok is False
    assert "names no range" in basis


# --- berths and seats ---------------------------------------------------------------------------


def test_berths_are_read(models: list[BespokeModel]) -> None:
    assert _named(models, "Explore 5").berths == 4
    assert _named(models, "Crafter Edition").berths == 2


def test_the_explore_number_is_the_seat_count_not_the_berths(models: list[BespokeModel]) -> None:
    """An Explore 5 is four berths and five seats — the name counts seats."""
    explore_5 = _named(models, "Explore 5")
    assert explore_5.berths == 4
    assert explore_5.seats_raw == "5"


def test_a_plain_seat_count_is_recorded(models: list[BespokeModel]) -> None:
    built = build_extracted(_named(models, "Explore 4"), basis="b")
    assert built.motorhome.mh_passenger_seats_inc_driver == 4


def test_up_to_four_is_a_ceiling_and_is_refused(models: list[BespokeModel]) -> None:
    """The Bürstner rule: a "permitted" or "up to" count is a type-approval maximum, not
    the belts fitted as standard."""
    crafter = _named(models, "Crafter Edition")
    assert crafter.seats_raw == "Up to 4"
    seats, basis = seats_from(crafter.seats_raw)
    assert seats is None
    assert "ceiling" in basis
    built = build_extracted(crafter, basis="b")
    assert built.motorhome.mh_passenger_seats_inc_driver is None
    assert "mh_passenger_seats_inc_driver" not in built.provenance


def test_the_refused_seat_count_is_reported(models: list[BespokeModel]) -> None:
    assert any("SEATS NOT PROPOSED" in note for note in _notes(_named(models, "Crafter Edition")))


# --- the four fields published nowhere ----------------------------------------------------------


def test_no_price_no_mass_and_no_dimension_is_proposed(models: list[BespokeModel]) -> None:
    built = build_extracted(_named(models, "Explore 4"), basis="b")
    motorhome = built.motorhome
    for value in (
        motorhome.rrp_pounds,
        motorhome.mro_kilograms,
        motorhome.mtplm_kilograms,
        motorhome.mh_payload_kilograms,
        motorhome.mh_length_mm,
        motorhome.mh_width_mm,
        motorhome.mh_height_mm,
    ):
        assert value is None
    for refused in ("rrp_pounds", "mro_kilograms", "mh_length_mm", "mh_height_mm"):
        assert refused not in built.provenance


def test_the_body_type_points_at_the_photograph(models: list[BespokeModel]) -> None:
    """Bespoke publish no height, so the high-top rule cannot be applied and the requester
    reads it off the picture instead."""
    built = build_extracted(_named(models, "Explore 4"), basis="b")
    assert built.motorhome.body_type is None
    pointer = built.provenance["body_type"]
    assert pointer.source_url.endswith((".png", ".jpg", ".jpeg"))
    assert "exterior photograph" in pointer.snippet


def test_the_floorplan_answers_the_positional_fields(models: list[BespokeModel]) -> None:
    built = build_extracted(_named(models, "Explore 4"), basis="b")
    layout = {
        name: p for name, p in built.provenance.items() if "layout" in p.source_url.lower()
    }
    assert layout
    assert all("floorplan" in p.snippet for p in layout.values())


# --- habitation ---------------------------------------------------------------------------------


def test_the_equipment_prose_is_gathered(models: list[BespokeModel]) -> None:
    lines = _named(models, "Explore 4").equipment
    assert any("Fridge" in line or "fridge" in line for line in lines)
    assert any("Hot Water" in line for line in lines)


def test_a_bare_fridge_is_a_fridge_freezer(models: list[BespokeModel]) -> None:
    built = build_extracted(_named(models, "Explore 4"), basis="b")
    assert built.motorhome.refrigeration is Refrigeration.FRIDGE_FREEZER


def test_the_washroom_values_are_reported_not_mapped(models: list[BespokeModel]) -> None:
    """`portable` and `external` are Bespoke's own words for a toilet and a shower that
    FMLV has no column shaped for, so they are stated for a person rather than forced into
    an enum."""
    notes = " ".join(_notes(_named(models, "Explore 4")))
    assert "portable" in notes
    assert "external" in notes


def test_bed_types_are_not_read_from_the_prose(models: list[BespokeModel]) -> None:
    """Dropped as on every other adapter: the copy names beds without saying which are
    built in and which are made up from the seating.

    It still carries a **floorplan pointer**, which is the right outcome — the drawing is
    where that question gets answered, so the entry is a reviewer reference rather than a
    value this adapter is proposing.
    """
    built = build_extracted(_named(models, "Explore 4"), basis="b")
    assert built.motorhome.bed_types == []
    pointer = built.provenance["bed_types"]
    assert pointer.reviewer_reference is True
    assert "floorplan" in pointer.snippet


# --- the parse refuses rubbish rather than inventing --------------------------------------------------


def test_an_empty_response_yields_nothing() -> None:
    assert parse_models("[]", {}) == []
    assert parse_ranges("[]") == {}


def test_unparseable_json_yields_nothing() -> None:
    assert parse_models("<html>404</html>", {}) == []
    assert parse_ranges("<html>404</html>") == {}


def test_equipment_lines_cope_with_an_empty_block() -> None:
    assert equipment_lines({}) == []


def test_a_model_without_a_title_is_skipped() -> None:
    payload = json.dumps([{"slug": "x", "acf": {}}])
    assert parse_models(payload, {}) == []
