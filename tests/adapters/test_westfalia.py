"""Tests for the Westfalia adapter's pure parsing functions, against the real documents.

Fixtures are the Columbus price list and brochure as extracted text, plus the range page
that links both, captured 18 September 2026. No PDF is committed and no network is used.

The two documents hold different halves of what FMLV needs: the price list has dimensions,
permissible weight and prices; the brochure has the mass in running order.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.adapters import adapter_for, westfalia
from src.adapters.westfalia import (
    EXPECTED_LAYOUTS,
    MANUFACTURER,
    MANUFACTURER_DISPLAY_NAME,
    MINIMUM_VEHICLE_PRICE,
    RANGES,
    _reconciles,
    build_extracted,
    find_brochure_url,
    find_price_list_url,
    parse_base_prices,
    parse_brochure_masses,
    parse_dimensions,
    parse_weights,
    read_price_list,
)
from src.vehicle_class import VehicleClass

FIXTURES = Path(__file__).parent / "fixtures"

URL = "https://www.campersales.co.uk/guides/westfalia/pricelist.pdf"


def _price_list() -> str:
    return (FIXTURES / "westfalia_columbus_pricelist.txt").read_text(encoding="utf-8")


def _brochure() -> str:
    return (FIXTURES / "westfalia_columbus_brochure.txt").read_text(encoding="utf-8")


def _page() -> str:
    return (FIXTURES / "westfalia_columbus_page.html").read_text(encoding="utf-8")


def _columbus() -> westfalia.Range:
    return RANGES[0]


def _products() -> dict[str, westfalia.WestfaliaProduct]:
    masses = parse_brochure_masses(_brochure())
    return {p.model: p for p in read_price_list(_price_list(), _columbus(), masses)}


# --------------------------------------------------------------------------- #
# Identity, including FMLV's typo
# --------------------------------------------------------------------------- #


def test_the_manufacturer_carries_fmlvs_misspelling() -> None:
    """`Westfailia` is a typo in FMLV and it is the join key. Correcting it here would
    find an empty baseline and propose all eight products as new. The requester confirmed
    on 18 September 2026 that it cannot be changed on the FMLV side."""
    assert MANUFACTURER == "Westfailia"
    assert MANUFACTURER_DISPLAY_NAME == "Westfalia"
    assert adapter_for(MANUFACTURER, VehicleClass.MOTORHOME) is westfalia


# --------------------------------------------------------------------------- #
# The documents
# --------------------------------------------------------------------------- #


def test_both_documents_are_found_on_the_range_page() -> None:
    """Filenames follow no pattern between ranges, so both are discovered, not built."""
    assert find_price_list_url(_page()).endswith("Columbus-Pricelist-MY26-UK-March-2026.pdf")
    assert "CATALOGUE" in find_brochure_url(_page())


def test_a_page_with_neither_document_yields_nothing() -> None:
    assert find_price_list_url("<html></html>") is None
    assert find_brochure_url("<html></html>") is None


# --------------------------------------------------------------------------- #
# The price list
# --------------------------------------------------------------------------- #


def test_the_dimensions_are_one_row_and_one_label() -> None:
    """`L/W/H 5.413/2.050/2.600 …` — three fields under one label, in metres with a dot
    as the thousands separator."""
    assert parse_dimensions(_price_list(), 4) == [
        (5413, 2050, 2600),
        (5998, 2050, 2600),
        (5998, 2050, 2600),
        (6363, 2050, 2600),
    ]


def test_a_dimension_row_of_the_wrong_width_yields_nothing() -> None:
    """A short row puts each layout on its neighbour's dimensions."""
    assert parse_dimensions(_price_list(), 5) == []


def test_the_permissible_weight_is_read_per_column() -> None:
    assert parse_weights(_price_list(), 4) == [3500, 3500, 3500, 3500]


def test_the_base_price_is_the_cheapest_engine_on_the_base_chassis() -> None:
    """Each layout is priced on a different engine and a dash means not offered, so there
    is no single row to read. These four are exactly what FMLV holds."""
    assert parse_base_prices(_price_list(), 4) == [70475, 68919, 68473, 70856]


def test_a_row_running_into_the_next_is_still_read() -> None:
    """The 140 HP Automatic row comes out with seven cells — its own four plus three from
    the Maxi Chassis row below. Demanding exactly four discarded it and the 540 D fell
    back to the 180 HP price, £73,634 against the correct £70,475."""
    assert parse_base_prices(_price_list(), 4)[0] == 70475
    assert "£73.634" in _price_list()


def test_the_maxi_chassis_prices_are_never_taken() -> None:
    """A heavier chassis sold as an upgrade, about £9,000 dearer, and it sits immediately
    below the base rows."""
    assert "£77.133" in _price_list()

    assert all(price < 77_000 for price in parse_base_prices(_price_list(), 4))


def test_an_option_price_is_never_taken_as_a_vehicle() -> None:
    """The same document prices a £141 seat cover and a £12,818 roof package."""
    assert all(price >= MINIMUM_VEHICLE_PRICE for price in parse_base_prices(_price_list(), 4))


# --------------------------------------------------------------------------- #
# The brochure, which is where the mass lives
# --------------------------------------------------------------------------- #


def test_the_mass_panel_is_read_despite_its_broken_label() -> None:
    """The label comes out as `Mass in running` newline `order`, so a literal search finds
    nothing and a single-line window captures the label and no figures. Both read exactly
    like a brochure with no masses in it — which is what this survey first concluded."""
    masses = parse_brochure_masses(_brochure())

    assert masses == {
        "540 D": (2865, 3500),
        "600 D": (2935, 3500),
        "600 E": (2975, 3500),
        "640 E": (3030, 3500),
    }


def test_the_first_entry_is_not_lost_to_the_preceding_word() -> None:
    """The name capture can run back into the text before it — the first entry came out as
    "order  COLUMBUS 540 D" and keyed itself wrongly, so the 540 D silently lost its mass
    while the other three kept theirs."""
    assert "540 D" in parse_brochure_masses(_brochure())


def test_a_brochure_with_no_panel_yields_nothing() -> None:
    assert parse_brochure_masses("no masses here") == {}


def test_the_mass_is_keyed_by_name_not_by_position() -> None:
    """Which is the point: FMLV's stored Columbus masses hold exactly the error that
    position-based reading causes — the 600 D and 600 E carry each other's figure."""
    masses = parse_brochure_masses(_brochure())

    assert masses["600 D"][0] == 2935
    assert masses["600 E"][0] == 2975


# --------------------------------------------------------------------------- #
# The products
# --------------------------------------------------------------------------- #


def test_a_layout_yields_every_field() -> None:
    product = _products()["600 D"]

    assert product.mh_length_mm == 5998
    assert product.mtplm_kilograms == 3500
    assert product.mro_kilograms == 2935
    assert product.payload_kilograms == 565
    assert product.rrp_pounds == 68_919


def test_the_payload_is_derivable_only_because_of_the_brochure() -> None:
    without = read_price_list(_price_list(), _columbus(), {})[0]

    assert without.mro_kilograms is None
    assert without.payload_kilograms is None


# --------------------------------------------------------------------------- #
# The self-check
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("model", ["540 D", "600 D", "600 E", "640 E"])
def test_the_two_documents_agree_on_the_permissible_weight(model: str) -> None:
    """The one genuinely independent check here: the price list and the brochure are
    written separately and both state it."""
    assert _reconciles(_products()[model])[0] is True


def test_documents_disagreeing_on_the_weight_drops_the_layout() -> None:
    product = replace(_products()["600 D"], brochure_mtplm_kilograms=4250)

    reconciles, why_not = _reconciles(product)

    assert reconciles is False
    assert "4250kg" in why_not


def test_a_mass_above_the_permissible_weight_is_refused() -> None:
    product = replace(_products()["600 D"], mro_kilograms=3600)

    assert _reconciles(product)[0] is False


# --------------------------------------------------------------------------- #
# The four ranges collected by name
# --------------------------------------------------------------------------- #


def test_every_range_fmlv_holds_is_collected() -> None:
    """Collecting only Columbus would report the other four as discontinued — four live
    vehicles. `vantage.py` did exactly that before it was caught."""
    assert {entry.fmlv_range for entry in RANGES} == {
        "Columbus", "James Cook", "Jules Verne", "Sven Hedin", "Club Joker Urban",
    }
    assert sum(len(entry.models) for entry in RANGES) == EXPECTED_LAYOUTS == 8


def test_a_name_only_range_proposes_no_figure() -> None:
    """Its identity keeps it alive; every stored figure is left untouched."""
    sven = next(entry for entry in RANGES if entry.fmlv_range == "Sven Hedin")
    product = read_price_list("", sven)[0]
    extracted = build_extracted(product, URL, basis="identity only")

    assert _reconciles(product)[0] is True
    assert extracted.motorhome.mtplm_kilograms is None
    assert extracted.motorhome.rrp_pounds is None
    assert "mro_kilograms" not in extracted.provenance
    assert "manufacturer_range" in extracted.provenance


def test_only_columbus_is_read_for_figures() -> None:
    assert [entry.fmlv_range for entry in RANGES if entry.figures] == ["Columbus"]


# --------------------------------------------------------------------------- #
# What reaches the reviewer
# --------------------------------------------------------------------------- #


def test_the_price_provenance_explains_which_engine_it_is() -> None:
    snippet = build_extracted(_products()["600 D"], URL, basis="x").provenance[
        "rrp_pounds"
    ].snippet

    assert "cheapest engine" in snippet
    assert "Maxi Chassis" in snippet


def test_the_mass_provenance_says_it_came_from_the_brochure() -> None:
    snippet = build_extracted(_products()["600 D"], URL, basis="x").provenance[
        "mro_kilograms"
    ].snippet

    assert "brochure" in snippet
    assert "price list does not state it" in snippet


def test_both_halves_of_the_identity_carry_provenance() -> None:
    provenance = build_extracted(_products()["540 D"], URL, basis="x").provenance

    assert "manufacturer_range" in provenance
    assert "model" in provenance
