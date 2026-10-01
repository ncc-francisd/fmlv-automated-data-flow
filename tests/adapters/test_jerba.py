"""Jerba Campervans — parsing and derivation only, no network.

The adapter holds its figures as constants (the site publishes none), so most of what
there is to test is that the constants obey the project's rules and that the two supplied
documents are still being checked against each other.
"""

from __future__ import annotations

from dataclasses import replace

from src.adapters import ADAPTERS, adapter_for, jerba
from src.adapters.jerba import (
    EXPECTED_PRODUCTS,
    HIGH_TOP_ABOVE_MM,
    PRODUCTS,
    body_type_for,
    document_disagreements,
)
from src.product_model.enums import BodyType
from src.vehicle_class import VehicleClass


def _product(platform: str, model: str) -> jerba.JerbaProduct:
    return next(p for p in PRODUCTS if p.platform == platform and p.model == model)


# --- registry -------------------------------------------------------------------------


def test_the_adapter_is_wired_in() -> None:
    """Three edits in `adapters/__init__.py`, all of which fail silently: a brand with no
    adapter is a normal state, so a missing one just never appears in the dropdown."""
    assert jerba.MANUFACTURER == "Jerba Campervans"
    assert jerba.MANUFACTURER_DISPLAY_NAME == "Jerba"
    assert (
        adapter_for("Jerba Campervans", VehicleClass.MOTORHOME, display_name="Jerba")
        is jerba
    )
    assert ("Jerba Campervans", "Jerba", VehicleClass.MOTORHOME) in ADAPTERS


# --- the roster -----------------------------------------------------------------------


def test_fourteen_products_across_three_base_vehicles() -> None:
    assert len(PRODUCTS) == EXPECTED_PRODUCTS == 14
    by_platform: dict[str, int] = {}
    for product in PRODUCTS:
        by_platform[product.platform] = by_platform.get(product.platform, 0) + 1
    assert by_platform == {"VW T7": 5, "Ford Transit Custom": 5, "VW Crafter": 4}


def test_the_roster_is_the_union_of_two_incomplete_documents() -> None:
    """**The trap this exists for.** Each supplied document is missing something the other
    has: the Jura is drawn in the layout brochure but priced in neither list, and the MWB
    Harris is priced but never drawn. Building the roster from either one alone loses a
    product that is plainly on sale."""
    drawn_only = [p for p in PRODUCTS if p.brochure_roof and not p.price_list_roof]
    priced_only = [p for p in PRODUCTS if p.price_list_roof and not p.brochure_roof]

    assert {p.model for p in drawn_only} == {"Jura"}
    assert {p.model for p in priced_only} == {"Harris MWB"}


def test_every_product_names_a_base_vehicle_fmlv_spells_that_way() -> None:
    """`VW`, never `Volkswagen` — the base vehicle takes the abbreviated form."""
    assert {p.base_vehicle for p in PRODUCTS} == {"VW", "Ford"}


def test_the_same_layout_on_two_base_vehicles_is_two_products() -> None:
    """Five names are sold on both panel vans at different prices, and base vehicle is
    part of product identity, so each pair is two vehicles rather than one."""
    tiree = [p for p in PRODUCTS if p.model == "Tiree"]

    assert len(tiree) == 2
    assert {p.base_vehicle for p in tiree} == {"VW", "Ford"}
    assert tiree[0].price_pounds != tiree[1].price_pounds


# --- the rules the figures have to obey -----------------------------------------------


def test_berths_take_the_lower_figure_of_a_range() -> None:
    """`Sleeps 2 / 4` is 2 and `Sleeps 4 / 6` is 4 — the extra berths need options."""
    assert _product("VW T7", "Tiree").berths == 2
    assert _product("VW Crafter", "Harris").berths == 4


def test_the_width_recorded_excludes_the_mirrors() -> None:
    """The brochure prints both; FMLV holds the body width. 2062 against 2276 on the panel
    vans, 2040 against 2427 on the Crafter."""
    assert _product("VW T7", "Tiree").width_mm == 2062
    assert _product("VW Crafter", "Mull").width_mm == 2040


def test_an_unpublished_figure_is_none_rather_than_a_guess() -> None:
    """The MWB Harris has no layout column. Its length is *probably* 5986mm like the other
    mediums, but an inference is not a published figure and FMLV's own value should stand."""
    harris_mwb = _product("VW Crafter", "Harris MWB")

    assert harris_mwb.length_mm is None
    assert harris_mwb.berths is None
    assert harris_mwb.belted_travel_seats is None
    assert harris_mwb.price_pounds == 83500


def test_the_jura_is_collected_without_a_price_never_with_an_invented_one() -> None:
    juras = [p for p in PRODUCTS if p.model == "Jura"]

    assert len(juras) == 2
    assert all(p.price_pounds is None for p in juras)


# --- body type ------------------------------------------------------------------------


def test_an_elevating_roof_below_the_threshold_is_not_a_high_top() -> None:
    got, reason = body_type_for(_product("VW T7", "Tiree"))

    assert got is BodyType.CAMPERVAN_ELEVATING_ROOF
    assert "2300mm" in reason


def test_a_fixed_high_roof_over_the_threshold_is_a_high_top() -> None:
    assert body_type_for(_product("VW T7", "Jura"))[0] is BodyType.CAMPERVAN_HIGH_TOP
    assert body_type_for(_product("VW Crafter", "Mull"))[0] is BodyType.CAMPERVAN_HIGH_TOP


def test_the_optional_elevating_roof_does_not_change_what_a_crafter_is() -> None:
    """Every Crafter offers an optional ATEC elevating roof. An optional rising roof never
    changes what the vehicle is, so it stays a plain high top."""
    for model in ("Mull", "Barra", "Harris"):
        assert body_type_for(_product("VW Crafter", model))[0] is BodyType.CAMPERVAN_HIGH_TOP


def test_the_threshold_is_the_shared_one() -> None:
    assert HIGH_TOP_ABOVE_MM == 2300


def test_a_roof_nobody_describes_derives_nothing() -> None:
    nameless = replace(_product("VW T7", "Tiree"), brochure_roof=None, price_list_roof=None)

    got, reason = body_type_for(nameless)

    assert got is None
    assert "neither document" in reason


# --- the self-check -------------------------------------------------------------------


def test_the_documents_are_checked_against_each_other() -> None:
    """**The nearest thing this manufacturer has to a self-check**, since no mass is
    published and there is no arithmetic to reconcile. It already earns its place: the VW
    T7 list calls the Taransay a front elevating roof where the Ford list and the layout
    brochure both say rear."""
    found = document_disagreements()

    assert len(found) == 1
    assert "Taransay" in found[0]
    assert "rear elevating" in found[0] and "front elevating" in found[0]


def test_a_price_that_breaks_the_two_thousand_step_is_reported(monkeypatch) -> None:
    """Every VW T7 is exactly GBP2,000 above its Ford twin. A misread price, or a layout
    matched to the wrong row, would almost certainly break that."""
    broken = tuple(
        replace(p, price_pounds=99999) if (p.platform == "VW T7" and p.model == "Sanna") else p
        for p in PRODUCTS
    )
    monkeypatch.setattr(jerba, "PRODUCTS", broken)

    found = document_disagreements()

    assert any("Sanna" in message and "2,000" in message for message in found)


def test_an_unpriced_pair_does_not_trip_the_step_check() -> None:
    """Neither Jura has a price, so there is no step to compare and nothing to report."""
    assert not any("Jura" in message for message in document_disagreements())


# --- what reaches the pipeline --------------------------------------------------------


def test_no_mass_is_ever_emitted() -> None:
    """Jerba publish none and did not answer when asked. Emitting a blank would wipe what
    FMLV holds; emitting nothing leaves it standing."""
    for product in PRODUCTS:
        motorhome = jerba._build_extracted(product).motorhome
        assert motorhome.mtplm_kilograms is None
        assert motorhome.mro_kilograms is None
        assert motorhome.mh_payload_kilograms is None


def test_a_field_with_no_figure_gets_no_provenance() -> None:
    """A field with no provenance is a field the pipeline proposes nothing for."""
    jura = jerba._build_extracted(_product("VW T7", "Jura"))
    harris_mwb = jerba._build_extracted(_product("VW Crafter", "Harris MWB"))

    assert "rrp_pounds" not in jura.provenance
    assert "berths" in jura.provenance
    assert {"berths", "mh_passenger_seats_inc_driver", "mh_length_mm"}.isdisjoint(
        harris_mwb.provenance
    )


def test_the_seat_provenance_warns_that_the_belts_are_unconfirmed() -> None:
    """Only three-point belts count. The brochure says "BELTED TRAVEL SEATS" without
    saying what kind, so the reviewer is told that rather than it passing as settled."""
    tiree = jerba._build_extracted(_product("VW T7", "Tiree"))

    snippet = tiree.provenance["mh_passenger_seats_inc_driver"].snippet
    assert "three-point" in snippet


def test_the_range_and_model_are_the_platform_and_the_layout() -> None:
    tiree = jerba._build_extracted(_product("Ford Transit Custom", "Tiree")).motorhome

    assert tiree.manufacturer_range == "Ford Transit Custom"
    assert tiree.model == "Tiree"
    assert tiree.base_vehicle_manufacturer == "Ford"
