"""Tests for the VANTourer adapter's pure parsing functions, against the real documents.

Fixtures are the real UK price list's extracted text and the downloads page that links it,
both captured 18 September 2026. No PDF is committed — `tests/fetch/test_pdf.py` covers
extraction — and no network is used here.

The price list is the whole source: technical data and prices in one UK market edition.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.adapters import adapter_for, vantourer
from src.adapters.vantourer import (
    EXPECTED_LAYOUTS,
    GO_EDITION_SUFFIX,
    MANUFACTURER,
    PASSENGER_ALLOWANCE_KG,
    _reconciles,
    _values,
    build_extracted,
    find_price_list_url,
    parse_berths,
    parse_columns,
    parse_masses_in_running_order,
    read_price_list,
    technical_block,
)
from src.vehicle_class import VehicleClass

FIXTURES = Path(__file__).parent / "fixtures"

URL = "https://www.vantourer.de/pricelist.pdf"


def _text() -> str:
    return (FIXTURES / "vantourer_pricelist_uk_2027.txt").read_text(encoding="utf-8")


def _downloads() -> str:
    return (FIXTURES / "vantourer_downloads.html").read_text(encoding="utf-8")


def _products() -> dict[str, vantourer.VantourerProduct]:
    return {f"{p.manufacturer_range} {p.model}": p for p in read_price_list(_text())}


# --------------------------------------------------------------------------- #
# Registration and the document
# --------------------------------------------------------------------------- #


def test_the_adapter_is_registered_for_campervans() -> None:
    assert adapter_for(MANUFACTURER, VehicleClass.MOTORHOME) is vantourer
    assert MANUFACTURER == "VANTourer"
    assert vantourer.VEHICLE_CLASS is VehicleClass.MOTORHOME


def test_the_uk_edition_is_the_one_chosen() -> None:
    """The same page offers `-de-`, `-at-`, `-ch-de-`, `-en-`, `-it-` and `-se-`. The
    `-en-` edition is English too and quotes euro, so taking it would fill `rrp_pounds`
    with the wrong currency while looking entirely right."""
    found = find_price_list_url(_downloads())

    assert found is not None
    url, year = found
    assert url.endswith("pricelist-01-2027-uk-web.pdf")
    assert year == "2027"
    assert "-en-web" not in url


def test_no_uk_edition_yields_nothing_rather_than_a_fallback() -> None:
    assert find_price_list_url("<html>no price lists here</html>") is None


# --------------------------------------------------------------------------- #
# The table, and the prose that looks like it
# --------------------------------------------------------------------------- #


def test_the_columns_are_the_four_floorplans() -> None:
    assert [c.heading for c in parse_columns(_text())] == ["540 D", "600 D", "600 L", "630 L"]


def test_the_range_is_the_number_and_the_model_the_letters() -> None:
    first = parse_columns(_text())[0]

    assert first.manufacturer_range == "540"
    assert first.model == "D"


def test_rows_are_read_from_the_table_and_not_from_the_prose() -> None:
    """The document explains itself in the same words the rows use — page 2's footnote
    says *"The stated weight is the maximum authorised laden mass"* — so an unscoped
    search finds the sentence, returns no figures and drops every vehicle. It did."""
    assert "the maximum authorised laden mass" in _text()

    assert _values(_text(), "Maximum authorised laden mass", count=4) == []
    assert _values(technical_block(_text()), "Maximum authorised laden mass", count=4) == [
        3500.0,
        3500.0,
        3500.0,
        3500.0,
    ]


def test_a_row_with_no_bracketed_unit_still_yields_its_values() -> None:
    """`Length in cm 541 599 599 636` has no bracket, and a pattern that assumed one
    swallowed the whole row."""
    assert _values(technical_block(_text()), "Length in cm", count=4) == [541, 599, 599, 636]


def test_a_footnote_marker_is_not_read_as_a_figure() -> None:
    """`Maximum authorised laden mass (kg) 1/2 3,500` — the `1/2` is a footnote, and
    `Minimum payload (kg) 1 94.1` likewise."""
    block = technical_block(_text())

    assert _values(block, "Minimum payload", count=4) == [94.1, 99.9, 99.9, 103.6]


def test_a_row_of_the_wrong_length_yields_nothing() -> None:
    """A short row silently shifts every column, which is this source's characteristic
    failure — so it is refused rather than zipped."""
    assert _values(technical_block(_text()), "Length in cm", count=5) == []


def test_the_masses_interleave_the_two_trims() -> None:
    """Eight figures, standard and GO! alternating per column, each carrying a tolerance
    band that distinguishes it from the band's own contents."""
    masses = parse_masses_in_running_order(technical_block(_text()))

    assert masses == [2660, 2738, 2815, 2893, 2810, 2885, 2995, 3073]


# --------------------------------------------------------------------------- #
# The berth block, which is not laid out as a row
# --------------------------------------------------------------------------- #


def test_the_berth_count_is_the_first_of_each_column_group() -> None:
    assert parse_berths(technical_block(_text()), 4) == [2, 2, 2, 2]


def test_the_berth_run_stops_at_the_chassis_description() -> None:
    """A fixed character window ran straight past it and collected sixty tokens."""
    assert "Fiat Ducato" in technical_block(_text())

    assert len(parse_berths(technical_block(_text()), 4)) == 4


def test_a_berth_run_of_the_wrong_length_yields_nothing() -> None:
    """There is no label beside these figures to check them against, so the count is the
    only guard — and a wrong berth count is not what a reviewer spots."""
    assert parse_berths(technical_block(_text()), 5) == []
    assert parse_berths("no berth block here", 4) == []


# --------------------------------------------------------------------------- #
# The products
# --------------------------------------------------------------------------- #


def test_every_floorplan_is_sold_two_ways() -> None:
    products = _products()

    assert len(products) == EXPECTED_LAYOUTS == 8
    assert "540 D" in products
    assert f"540 D{GO_EDITION_SUFFIX}" in products


def test_the_go_edition_is_named_as_fmlv_names_it() -> None:
    """No VANTourer document writes it this way: the technical table heads the column
    `540 D` and the price table `GO! 540 D`."""
    assert "540 D GO! Edition" in _products()
    assert "GO! 540 D" in _text()


def test_a_product_yields_every_field() -> None:
    product = _products()["600 D"]

    assert product.mh_length_mm == 5990
    assert product.mh_width_mm == 2050
    assert product.mh_height_mm == 2580
    assert product.berths == 2
    assert product.travel_seats == 4
    assert product.mtplm_kilograms == 3500
    assert product.mro_kilograms == 2815
    assert product.rrp_pounds == 68_790


def test_the_exterior_dimension_is_taken_not_the_interior() -> None:
    """Width and height print as `exterior/interior` — 205/187 and 258/190."""
    product = _products()["600 D"]

    assert product.mh_width_mm == 2050
    assert product.mh_height_mm == 2580


def test_the_two_trims_differ_only_where_they_should() -> None:
    standard, go = _products()["600 D"], _products()["600 D GO! Edition"]

    assert standard.mh_length_mm == go.mh_length_mm
    assert standard.berths == go.berths
    assert go.mro_kilograms > standard.mro_kilograms
    assert go.rrp_pounds > standard.rrp_pounds


def test_the_price_is_the_vehicle_and_not_the_engine_upgrade() -> None:
    """`Surcharges for motorization` sits immediately below the price row and is a row of
    2,750s. Anchoring on `Right Hand Drive` is what separates them."""
    assert _products()["600 D"].rrp_pounds == 68_790
    assert _products()["600 D GO! Edition"].rrp_pounds == 71_627
    assert all(p.rrp_pounds != 2750 for p in _products().values())


# --------------------------------------------------------------------------- #
# The self-check
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("name", "expected"),
    [("540 D", 840), ("600 D", 685), ("600 L", 690), ("630 L GO! Edition", 427)],
)
def test_the_masses_reconcile_four_ways(name: str, expected: int) -> None:
    """`MTPLM - MRO == 3 passengers x 75kg + additional equipment + minimum payload`.
    Exact on all eight, to the tenth of a kilogram."""
    product = _products()[name]

    assert _reconciles(product)[0] is True
    assert product.payload_kilograms == expected


def test_every_product_reconciles() -> None:
    assert all(_reconciles(p)[0] for p in _products().values())


def test_a_column_shift_breaks_the_check() -> None:
    """The failure this source is most exposed to: read one value out of step and every
    vehicle carries its neighbour's weights, plausibly and consistently."""
    product = _products()["540 D"]
    shifted = replace(product, additional_equipment_kg=_products()["600 D"].additional_equipment_kg)

    reconciles, why_not = _reconciles(shifted)

    assert reconciles is False
    assert "out of step" in why_not


def test_the_driver_is_not_counted_twice() -> None:
    """The driver's 75kg is already inside the mass in running order, so only the other
    three passengers are added."""
    product = _products()["540 D"]

    assert product.travel_seats == 4
    assert (product.travel_seats - 1) * PASSENGER_ALLOWANCE_KG == 225


# --------------------------------------------------------------------------- #
# What reaches the reviewer
# --------------------------------------------------------------------------- #


def test_the_payload_is_derived_and_not_the_legal_minimum() -> None:
    """`Minimum payload` is 94.1kg on a van that carries 840. An adapter matching on the
    word "payload" records a tenth of the real figure."""
    extracted = build_extracted(_products()["540 D"], URL, basis="x")

    assert extracted.motorhome.mh_payload_kilograms == 840
    assert "94.1" in extracted.provenance["mh_payload_kilograms"].snippet


def test_the_seat_count_is_stated_as_three_point_belts() -> None:
    """Rare and worth using: the price list names the belt type, so nothing is inferred."""
    extracted = build_extracted(_products()["600 D"], URL, basis="x")

    assert extracted.motorhome.mh_passenger_seats_inc_driver == 4
    assert "3-point" in extracted.provenance["mh_passenger_seats_inc_driver"].snippet


def test_no_body_type_is_proposed() -> None:
    """FMLV holds the eight inconsistently and VANTourer call the roof optional; that is a
    decision for a person, and a body type asserted from partial evidence has already been
    wrong twice this month on `vantage.py`."""
    extracted = build_extracted(_products()["600 L"], URL, basis="x")

    assert extracted.motorhome.body_type is None
    assert "body_type" not in extracted.provenance


def test_the_price_provenance_says_it_is_already_sterling() -> None:
    """So nobody later adds a conversion to a figure VANTourer have already converted."""
    snippet = build_extracted(_products()["600 D"], URL, basis="x").provenance[
        "rrp_pounds"
    ].snippet

    assert "UK VAT" in snippet
    assert "£68,790" in snippet


def test_both_halves_of_the_identity_carry_provenance() -> None:
    provenance = build_extracted(_products()["540 D"], URL, basis="x").provenance

    assert "manufacturer_range" in provenance
    assert "model" in provenance


def test_the_base_vehicle_is_the_make_alone() -> None:
    extracted = build_extracted(_products()["540 D"], URL, basis="x")

    assert extracted.motorhome.base_vehicle_manufacturer == "Fiat"
