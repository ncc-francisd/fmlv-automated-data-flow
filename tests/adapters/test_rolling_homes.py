"""Rolling Homes' model pages, captured 9 October 2026.

The traps these cover are all real and all hit while building: a Conversion Only price
that is the lowest number on the page, a second Key Features list under it stating
different berths, an Extras tab whose contents are not equipment the vehicle has, two
pages that are empty shells, and slugs that name the wrong vehicle.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters import habitation
from src.adapters import rolling_homes as rh
from src.product_model.enums import BodyType

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def columbus_s() -> str:
    return _fixture("rolling_homes_columbus_s.html")


# --- The roster ------------------------------------------------------------------------


def test_every_vehicle_page_is_found_on_the_home_page() -> None:
    """The site publishes no roster, so these links are the only list there is."""
    paths = rh.find_van_paths(_fixture("rolling_homes_home.html"))
    assert len(paths) == 11
    assert "/van/weekender/" in paths
    assert "/van/vw-columbus-campervan/" in paths


def test_a_vehicle_is_named_by_its_heading_not_its_slug() -> None:
    """`/van/darwin-rl/` is the Darwin **EL** — the slug would mislabel it."""
    assert rh.vehicle_name(_fixture("rolling_homes_darwin_el.html")) == "Darwin EL"


# --- Identity --------------------------------------------------------------------------


def test_fmlv_files_the_base_vehicle_as_the_model() -> None:
    """FMLV holds `Columbus S` / `T7`, and the site never prints `T7` anywhere."""
    assert rh.identity_for("Columbus S") == ("Columbus S", "T7")
    assert rh.identity_for("Expedition") == ("Expedition", "SWB")


def test_the_darwin_carries_its_variant_as_the_model() -> None:
    assert rh.identity_for("Darwin EL") == ("Darwin", "EL")
    assert rh.identity_for("Darwin FL 6.0") == ("Darwin", "FL 6.0")


def test_an_unseen_variant_of_a_known_range_still_splits() -> None:
    """A new Darwin would be filed under Darwin rather than becoming its own range."""
    assert rh.identity_for("Darwin XL") == ("Darwin", "XL")


def test_a_one_name_vehicle_carries_that_name_twice() -> None:
    """Nova will not take a blank, and FMLV already files 7329 this way."""
    assert rh.identity_for("Weekender") == ("Weekender", "Weekender")
    assert rh.identity_for("Something New") == ("Something New", "Something New")


# --- The trap --------------------------------------------------------------------------


def test_the_new_vehicle_section_stops_at_the_conversion_heading(columbus_s: str) -> None:
    section = rh.new_vehicle_section(columbus_s)
    assert section is not None
    assert "Conversion Only" not in section


def test_the_price_is_the_cheapest_finished_vehicle(columbus_s: str) -> None:
    """£64,495, the entry trim — not £80,001, and emphatically not £20,495."""
    section = rh.new_vehicle_section(columbus_s)
    assert section is not None
    assert rh.base_price(section) == 64495


def test_the_conversion_price_is_the_lowest_number_on_the_page(columbus_s: str) -> None:
    """Which is why 'take the lowest price' takes the wrong one every time."""
    every_price = {int(p.replace(",", "")) for p in __import__("re").findall(r"£\s?([\d,]{5,})", columbus_s)}
    assert min(every_price) == 20495
    assert rh._conversion_price(columbus_s) == 20495


def test_a_price_read_from_the_conversion_block_is_refused() -> None:
    """The structural half of the self-check, since there is no arithmetic one."""
    vehicle = rh.Vehicle(name="Columbus S", url="x", rrp_pounds=20495, conversion_only_price=20495)
    reconciles, basis = rh._reconciles(vehicle)
    assert reconciles is False
    assert "Conversion Only" in basis


def test_an_implausibly_cheap_price_is_refused() -> None:
    vehicle = rh.Vehicle(name="Columbus S", url="x", rrp_pounds=9_995)
    assert rh._reconciles(vehicle)[0] is False


def test_no_price_at_all_is_not_a_failure() -> None:
    """The Expedition publishes none; dropping it would report a live vehicle as gone."""
    reconciles, basis = rh._reconciles(rh.Vehicle(name="Expedition", url="x"))
    assert reconciles is True
    assert "FMLV's own figure stands" in basis


# --- Berths, seats and equipment come from Key Features only -----------------------------


def test_berths_and_seats_come_from_the_new_vehicle_block(columbus_s: str) -> None:
    """`4 berths and 4 seats` — the Conversion block says `2- 4 berths and 4-5 seats`."""
    section = rh.new_vehicle_section(columbus_s)
    assert section is not None
    assert rh.berths_and_seats(section) == (4, 4)


def test_the_lower_figure_of_a_range_is_taken() -> None:
    assert rh.berths_and_seats("<p>Key Features</p><p>layout with 2- 4 berths and 4-6 seats</p>") == (2, 4)


def test_the_extras_tab_is_not_read_as_equipment(columbus_s: str) -> None:
    """The first run reported the Columbus's heating as `Diesel blown air heating*`.

    That is an item from the Extras list — something to add to the vehicle, not something
    it has. `docs/adapters/README.md`: never read a paid option as standard equipment.
    """
    section = rh.new_vehicle_section(columbus_s)
    assert section is not None
    assert "Diesel blown air heating" in section, "the fixture should still contain the extra"
    features = rh.key_features(section)
    assert any("50L fridge freezer" in line for line in features)
    assert not any("Diesel blown air heating" in line for line in features)


def test_the_key_features_stop_at_the_next_tab(columbus_s: str) -> None:
    section = rh.new_vehicle_section(columbus_s)
    assert section is not None
    assert "Vehicle Upgrades" not in rh.key_features(section)


# --- Body type ---------------------------------------------------------------------------


def test_a_stated_elevating_roof_gives_the_elevating_roof_body_type(columbus_s: str) -> None:
    section = rh.new_vehicle_section(columbus_s)
    assert section is not None
    body_type, reason = rh.body_type_for(section)
    assert body_type is BodyType.CAMPERVAN_ELEVATING_ROOF
    assert "no height is published" in reason


def test_without_a_stated_roof_the_body_type_is_left_blank() -> None:
    """The Crafter Darwins are high tops, and nothing here could know that."""
    body_type, reason = rh.body_type_for("<p>Key Features</p><p>A luxury motorhome</p>")
    assert body_type is None
    assert "needs a height" in reason


# --- The empty shells ---------------------------------------------------------------------


def test_the_expeditions_new_vehicle_tab_is_empty() -> None:
    """Rolling Homes have simply not filled it in — worth telling them."""
    section = rh.new_vehicle_section(_fixture("rolling_homes_expedition.html"))
    assert section is not None
    assert rh.base_price(section) is None
    assert rh.berths_and_seats(section) == (None, None)


def test_the_expeditions_berths_live_only_in_the_conversion_block() -> None:
    """So not reading them is correct: they describe converting a customer's own van."""
    page = _fixture("rolling_homes_expedition.html")
    assert "2- 4 berths and 4-6 seats" in page
    section = rh.new_vehicle_section(page)
    assert section is not None
    assert "berths" not in " ".join(rh.key_features(section)).lower()


def test_an_empty_shell_is_still_emitted_for_its_identity() -> None:
    """The Weekender is a live FMLV product; collecting nothing reads as withdrawn."""
    vehicle = rh.parse_vehicle(_fixture("rolling_homes_expedition.html"), "x")
    assert vehicle is not None
    assert vehicle.publishes_nothing is True
    assert rh._reconciles(vehicle)[0] is True


def test_an_empty_shell_proposes_nothing_but_its_range() -> None:
    vehicle = rh.parse_vehicle(_fixture("rolling_homes_expedition.html"), "x")
    assert vehicle is not None
    built = rh.build_extracted(vehicle, basis="no price is published")
    assert set(built.provenance) == {"manufacturer_range"}
    assert built.motorhome.rrp_pounds is None


# --- What is deliberately never proposed --------------------------------------------------


def test_no_mass_or_dimension_is_ever_proposed(columbus_s: str) -> None:
    """Rolling Homes publish none, so FMLV's carry through untouched."""
    vehicle = rh.parse_vehicle(columbus_s, "x")
    assert vehicle is not None
    built = rh.build_extracted(vehicle, basis="£64,495")
    for name in (
        "mtplm_kilograms",
        "mro_kilograms",
        "mh_payload_kilograms",
        "mh_length_mm",
        "mh_width_mm",
        "mh_height_mm",
    ):
        assert getattr(built.motorhome, name) is None
        assert name not in built.provenance


def test_the_model_is_never_proposed(columbus_s: str) -> None:
    """FMLV's model is the base-vehicle generation and the site never prints it."""
    vehicle = rh.parse_vehicle(columbus_s, "x")
    assert vehicle is not None
    built = rh.build_extracted(vehicle, basis="£64,495")
    assert built.motorhome.model == "T7"
    assert "model" not in built.provenance


def test_ability_is_not_a_product() -> None:
    assert "Ability" in rh.NOT_A_PRODUCT


def test_the_columbus_s_builds_whole(columbus_s: str) -> None:
    vehicle = rh.parse_vehicle(columbus_s, "x")
    assert vehicle is not None
    built = rh.build_extracted(vehicle, basis="£64,495, the cheapest trim")
    assert built.motorhome.manufacturer == "Rolling Homes"
    assert built.motorhome.manufacturer_range == "Columbus S"
    assert built.motorhome.rrp_pounds == 64495
    assert built.motorhome.berths == 4
    assert built.motorhome.mh_passenger_seats_inc_driver == 4
    assert built.motorhome.base_vehicle_manufacturer == "VW"
    assert built.motorhome.body_type is BodyType.CAMPERVAN_ELEVATING_ROOF


def test_the_fridge_freezer_is_found_as_a_habitation_finding(columbus_s: str) -> None:
    section = rh.new_vehicle_section(columbus_s)
    assert section is not None
    features = habitation.features_from(habitation.usable_lines(rh.key_features(section)))
    assert "refrigeration" in features
    assert "fridge freezer" in features["refrigeration"].snippet.lower()
