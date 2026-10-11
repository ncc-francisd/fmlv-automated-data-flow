"""Volkswagen's California brochures and price list, captured 11 October 2026.

The fixtures are the extracted text of the pages that carry figures, not whole documents.
Every trap covered here is one the build actually hit: two brochures that weigh
differently, a length the dimensions page will not label, footnote digits glued onto a
weight, and a Dune trim that must not become a product.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters.volkswagen import (
    DRIVER_ALLOWANCE_KG,
    EXPECTED_PRODUCTS,
    MANUFACTURER,
    MANUFACTURER_DISPLAY_NAME,
    CaliforniaWeight,
    GrandWeight,
    Product,
    _reconciles_california,
    _reconciles_grand,
    base_variants,
    build_extracted,
    find_documents,
    parse_california_dimensions,
    parse_california_prices,
    parse_california_weights,
    parse_grand_prices,
    parse_grand_weights,
)
from src.product_model.enums import BodyType

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def brochure() -> str:
    return _fixture("volkswagen_california_brochure.txt")


@pytest.fixture(scope="module")
def grand() -> str:
    return _fixture("volkswagen_grand_california_brochure.txt")


# --- identity ------------------------------------------------------------------------


def test_the_manufacturer_is_volkswagen_and_the_base_vehicle_is_vw() -> None:
    """Both spellings are deliberate — one name per company per role, for the filters."""
    assert MANUFACTURER == "Volkswagen"
    assert MANUFACTURER_DISPLAY_NAME == "Volkswagen"
    built = build_extracted(
        Product("California", "Beach", 2850, 2383, 467, "http://x", "the arithmetic")
    )
    assert built.motorhome.manufacturer == "Volkswagen"
    assert built.motorhome.base_vehicle_manufacturer == "VW"


def test_the_three_documents_are_found_on_the_index() -> None:
    documents = find_documents(_fixture("volkswagen_brochure_index.html"))
    assert set(documents) == {"california_brochure", "california_prices", "grand_brochure"}
    assert documents["california_prices"].endswith("california-pl.pdf")


def test_a_grand_california_price_guide_is_not_expected() -> None:
    """Its prices live inside its brochure; the price-guide folder has no file for it."""
    documents = find_documents(_fixture("volkswagen_brochure_index.html"))
    assert "grand_california-pl.pdf" not in " ".join(documents.values())


# --- the California weights ------------------------------------------------------------


def test_every_engine_row_is_read_under_its_variant(brochure: str) -> None:
    rows = parse_california_weights(brochure)
    assert len(rows) == 8
    assert {row.variant for row in rows} == {"Beach", "Coast", "Ocean"}


def test_the_figures_match_what_fmlv_holds(brochure: str) -> None:
    """2,850 / 2,383 / 467 on the Beach — FMLV's figures to the kilogram."""
    beach = next(r for r in parse_california_weights(brochure) if r.model == "Beach")
    assert (beach.gross_kilograms, beach.mro_kilograms, beach.payload_kilograms) == (
        2850,
        2383,
        467,
    )


def test_an_ehybrid_row_becomes_its_own_model(brochure: str) -> None:
    models = {row.model for row in parse_california_weights(brochure)}
    assert "Beach eHybrid" in models
    assert "Ocean eHybrid" in models


def test_the_californias_unladen_weight_is_already_the_running_order(brochure: str) -> None:
    """Its footnote: "includes approximately 90% fuel load and 75kg for driver"."""
    for row in parse_california_weights(brochure):
        ok, basis = _reconciles_california(row)
        assert ok is True, f"{row.model}: {basis}"
        assert row.gross_kilograms - row.mro_kilograms == row.payload_kilograms


def test_a_payload_that_contradicts_the_masses_is_refused() -> None:
    ok, basis = _reconciles_california(CaliforniaWeight("Beach", "150PS", 2850, 2383, 999))
    assert ok is False
    assert "467kg" in basis


# --- the base variant --------------------------------------------------------------------


def test_the_lowest_powered_engine_is_the_base(brochure: str) -> None:
    """The Coast and Ocean each publish a 204PS TSI as well as the 150PS TDI."""
    rows = parse_california_weights(brochure)
    chosen = {row.model: row.power for row in base_variants(rows)}
    assert chosen["Coast"] == 150
    assert chosen["Ocean"] == 150
    assert 204 in {row.power for row in rows}


def test_the_base_variants_are_exactly_the_six_fmlv_holds(brochure: str) -> None:
    assert sorted(row.model for row in base_variants(parse_california_weights(brochure))) == [
        "Beach",
        "Beach eHybrid",
        "Coast",
        "Coast eHybrid",
        "Ocean",
        "Ocean eHybrid",
    ]


# --- prices --------------------------------------------------------------------------------


def test_the_price_is_the_column_the_website_headlines() -> None:
    """£64,432 for the Beach — the fifth money column, and what the model page shows."""
    prices = parse_california_prices(_fixture("volkswagen_california_prices.txt"))
    assert prices["Beach"] == (64432, 5)


def test_the_price_list_also_gives_the_seat_count() -> None:
    """Five for the Beach, four for everything else — which agrees with FMLV."""
    prices = parse_california_prices(_fixture("volkswagen_california_prices.txt"))
    assert prices["Beach"][1] == 5
    assert {model: seats for model, (_p, seats) in prices.items() if model != "Beach"} == {
        "Beach eHybrid": 4,
        "Coast": 4,
        "Coast eHybrid": 4,
        "Ocean": 4,
        "Ocean eHybrid": 4,
    }


def test_the_cheaper_engine_wins_where_a_model_has_two() -> None:
    """The Coast's 204PS TSI is £74,704 and must not displace the 150PS at £71,740."""
    prices = parse_california_prices(_fixture("volkswagen_california_prices.txt"))
    assert prices["Coast"][0] == 71740


# --- the Grand California ------------------------------------------------------------------


def test_the_dune_trims_never_become_products(grand: str) -> None:
    rows = parse_grand_weights(grand)
    assert {row.model for row in rows} == {"600", "680"}
    assert "Dune" in grand, "the fixture should still contain the rows being excluded"


def test_a_footnote_digit_glued_to_a_weight_is_discarded(grand: str) -> None:
    """The table prints `3,8803` — a 3.88 tonne class with footnote 3 stuck to it."""
    assert "3,8803" in grand
    assert {row.gross_kilograms for row in parse_grand_weights(grand)} == {3500, 3880}


def test_the_kerb_weight_is_not_the_mass_in_running_order(grand: str) -> None:
    """VW's kerb weight excludes the driver their payload accounts for.

    Gross minus kerb is 75kg more than the payload they print, on every row.
    """
    for row in parse_grand_weights(grand):
        assert row.gross_kilograms - row.kerb_kilograms - DRIVER_ALLOWANCE_KG == (
            row.payload_kilograms
        )
        assert row.mro_kilograms == row.kerb_kilograms + DRIVER_ALLOWANCE_KG


def test_the_running_order_reproduces_what_fmlv_holds(grand: str) -> None:
    """3,021 + 75 = 3,096 against FMLV's 3,098 — a slightly older brochure, not a misread."""
    row = next(r for r in parse_grand_weights(grand) if r.model == "600" and r.gross_kilograms == 3500)
    assert row.kerb_kilograms == 3021
    assert row.mro_kilograms == 3096


def test_the_grand_reconciles_on_the_corrected_mass(grand: str) -> None:
    for row in parse_grand_weights(grand):
        ok, basis = _reconciles_grand(row)
        assert ok is True, f"{row.model}: {basis}"


def test_the_naive_subtraction_is_refused() -> None:
    """Had VW's payload been gross minus kerb, as their own footnote claims, it would read
    479 on the 600 rather than 404. The check refuses that, which is what stops the kerb
    weight being recorded as a mass in running order."""
    naive = GrandWeight("600", "2.0TDI", 3500, 3021, 3500 - 3021)
    ok, basis = _reconciles_grand(naive)
    assert ok is False
    assert "404" in basis or "479" in basis


def test_the_grand_prices_join_on_the_weight_class(grand: str) -> None:
    """The price rows say `3.5T` where the weights table says `3,500`."""
    prices = parse_grand_prices(grand)
    assert prices[("600", 3500)] == 84208
    assert prices[("680", 3880)] == 86986


def test_four_motion_never_undercuts_front_wheel_drive(grand: str) -> None:
    """Both are 3.88T on the 680; the base is the cheaper front-wheel drive."""
    assert parse_grand_prices(grand)[("680", 3880)] == 86986
    assert "95,050" in grand


# --- dimensions ------------------------------------------------------------------------------


def test_the_california_dimensions_are_read(brochure: str) -> None:
    assert parse_california_dimensions(brochure) == {
        "mh_width_mm": 1941,
        "mh_height_mm": 1972,
        "mh_length_mm": 5173,
    }


def test_the_width_including_mirrors_is_ignored(brochure: str) -> None:
    """VW publish 2,252 beside the 1,941 body width, and FMLV holds the body."""
    assert "2,252" in brochure
    assert parse_california_dimensions(brochure)["mh_width_mm"] == 1941


def test_the_length_comes_from_the_prose_not_the_diagram(brochure: str) -> None:
    """The dimensions page labels the length *with* a trailing hitch (5,276) and leaves the
    real one as a bare figure beside a drawing, so the prose is the only labelled source."""
    assert "5,276" in brochure
    assert parse_california_dimensions(brochure)["mh_length_mm"] == 5173


# --- what is built -----------------------------------------------------------------------------


def test_a_california_is_an_elevating_roof_campervan() -> None:
    built = build_extracted(
        Product(
            "California", "Beach", 2850, 2383, 467, "http://x", "the arithmetic",
            body_type=BodyType.CAMPERVAN_ELEVATING_ROOF, body_type_reason="pop-up roof standard",
        )
    )
    assert built.motorhome.body_type is BodyType.CAMPERVAN_ELEVATING_ROOF


def test_nothing_is_proposed_for_a_field_that_was_not_read() -> None:
    """The California's berths and the Grand California's dimensions are left to FMLV."""
    built = build_extracted(
        Product("California", "Beach", 2850, 2383, 467, "http://x", "the arithmetic")
    )
    assert built.motorhome.berths is None
    assert "berths" not in built.provenance
    assert "mh_length_mm" not in built.provenance


def test_the_expected_count_is_what_fmlv_holds() -> None:
    assert EXPECTED_PRODUCTS == 8
