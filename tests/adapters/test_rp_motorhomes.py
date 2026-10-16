"""RP Motorhomes' 2027 brochures, captured 16 October 2026.

The fixtures are the Technical Data spread of each brochure plus the pages naming the
special edition, and one slice of a range page for the brochure link.

The spread publishes every dimension twice — rounded in a tile and dimensioned on a
drawing — and the tiles are demonstrably wrong, so most of these tests are about reading
the drawing and ignoring the tile beside it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters.rp_motorhomes import (
    DRIVETRAINS,
    EXPECTED_PRODUCTS,
    HIGH_TOP_ABOVE_MM,
    MANUFACTURER,
    MANUFACTURER_DISPLAY_NAME,
    MINIMUM_CREDIBLE_PRICE,
    RANGE_PATHS,
    SPECIAL_EDITION,
    Product,
    RangeBrochure,
    _products,
    _reconciles,
    body_type_for,
    build_extracted,
    find_brochure_url,
    parse_drawing,
    parse_gross_weights,
    parse_prices,
    parse_range_brochure,
)
from src.product_model.enums import BodyType

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _brochure(name: str, manufacturer_range: str) -> RangeBrochure:
    return parse_range_brochure(
        _fixture(f"rp_{name}_technical_data.txt"),
        manufacturer_range=manufacturer_range,
        url="http://x/b.pdf",
    )


@pytest.fixture(scope="module")
def rebel() -> RangeBrochure:
    return _brochure("rebel", "Rebel")


@pytest.fixture(scope="module")
def rebellion() -> RangeBrochure:
    return _brochure("rebellion", "Rebellion")


# --- identity --------------------------------------------------------------------------------


def test_the_manufacturer_and_its_two_ranges() -> None:
    assert MANUFACTURER == "RP Motorhomes"
    assert MANUFACTURER_DISPLAY_NAME == "RP Motorhomes"
    assert set(RANGE_PATHS) == {"Rebel", "Rebellion"}
    assert EXPECTED_PRODUCTS == len(RANGE_PATHS) * len(DRIVETRAINS)


def test_the_2027_pages_are_the_ones_read() -> None:
    """The site keeps `/rebel` and `/rebellion` alongside them, and those are last
    season's."""
    assert all(path.endswith("-2027") for path in RANGE_PATHS.values())


def test_the_brochure_link_is_found_on_the_range_page() -> None:
    url = find_brochure_url(_fixture("rp_rebel_2027_page.html"))
    assert url is not None
    assert url.endswith(".pdf")
    assert "brochure" in url.lower()


# --- the prices, which are in the brochure and nowhere else -------------------------------------


def test_both_prices_are_read(rebel: RangeBrochure, rebellion: RangeBrochure) -> None:
    assert rebel.prices == {"RWD": 147000, "AWD": 155000}
    assert rebellion.prices == {"RWD": 157000, "AWD": 170000}


def test_an_option_price_is_never_taken_for_a_vehicle(rebel: RangeBrochure) -> None:
    """The spread prices a 9G Auto at £2,607 and a 190bhp engine at £4,051 beside the
    vehicles."""
    assert "2,607" in _fixture("rp_rebel_technical_data.txt")
    assert all(price >= MINIMUM_CREDIBLE_PRICE for price in rebel.prices.values())


# --- the gross weights ------------------------------------------------------------------------------


def test_the_gross_weights_come_from_the_tile_row(rebel: RangeBrochure) -> None:
    assert rebel.gross_weights == {"RWD": 3500, "AWD": 4100}


def test_the_heavier_plates_are_options_and_are_not_taken() -> None:
    """`3,880kg GVW £505` and `4,400kg GVW £505` sit beside the row. The base-vehicle rule
    records the base, which is what FMLV holds."""
    text = _fixture("rp_rebel_technical_data.txt")
    assert "3,880kg GVW" in text
    assert parse_gross_weights(text)["RWD"] == 3500


def test_a_row_that_is_not_a_pair_is_not_read() -> None:
    assert parse_gross_weights("3,500 is the weight") == {}


# --- the drawing, and the tiles that disagree with it --------------------------------------------------


def test_the_six_drawing_figures_are_assigned(rebel: RangeBrochure) -> None:
    drawing = rebel.drawing
    assert drawing is not None
    assert drawing.width_mm == 2020
    assert drawing.width_including_mirrors_mm == 2345
    assert drawing.length_mm == 5932
    assert drawing.heights_mm == (2780, 2900)


def test_the_tile_contradicts_the_drawing_on_the_rebel_awd(rebel: RangeBrochure) -> None:
    """The tiles read `5.9m` and `7.0m` while both drawings say 5932mm — the AWD's tile is
    an error, almost certainly copied from the Rebellion page. FMLV holds 5932 for both,
    so taking the tile would stretch the vehicle by a metre."""
    text = _fixture("rp_rebel_technical_data.txt")
    assert "7.0m" in text
    assert rebel.drawing is not None
    assert rebel.drawing.length_mm == 5932


def test_the_width_pair_is_told_apart_by_size(rebel: RangeBrochure) -> None:
    """2020mm across the body and 2345mm across the mirrors; FMLV records the body."""
    drawing = rebel.drawing
    assert drawing is not None
    assert drawing.width_mm < drawing.width_including_mirrors_mm


def test_the_taller_height_is_the_all_wheel_drive(rebellion: RangeBrochure) -> None:
    """Assigned by magnitude, not position: the captions beneath the drawings run AWD
    first and then RWD, the reverse of the figures above them."""
    drawing = rebellion.drawing
    assert drawing is not None
    assert drawing.height_for("RWD") == 3050
    assert drawing.height_for("AWD") == 3180


def test_a_drawing_block_of_the_wrong_size_is_refused() -> None:
    """Anything but six figures means the spread has been redrawn."""
    assert parse_drawing("2020 mm 2345 mm 5932 mm") is None


def test_two_different_lengths_drop_the_length() -> None:
    """Nothing could say which belonged to which model — the tiles cannot arbitrate,
    having already been shown wrong."""
    drawing = parse_drawing("2020 mm 2345 mm 5932 mm 6967 mm 2780 mm 2900 mm")
    assert drawing is not None
    assert drawing.length_mm is None
    assert drawing.width_mm == 2020


# --- what is built -------------------------------------------------------------------------------------


def test_the_four_products_are_range_by_drivetrain(
    rebel: RangeBrochure, rebellion: RangeBrochure
) -> None:
    built = [
        (p.manufacturer_range, p.drivetrain)
        for brochure in (rebel, rebellion)
        for p in _products(brochure)
    ]
    assert built == [
        ("Rebel", "RWD"), ("Rebel", "AWD"),
        ("Rebellion", "RWD"), ("Rebellion", "AWD"),
    ]


def test_an_rp_is_a_high_top_campervan_on_a_mercedes(rebel: RangeBrochure) -> None:
    product = _products(rebel)[0]
    built = build_extracted(product, basis="b")
    assert built.motorhome.body_type is BodyType.CAMPERVAN_HIGH_TOP
    assert built.motorhome.base_vehicle_manufacturer == "Mercedes"
    assert str(HIGH_TOP_ABOVE_MM) in built.provenance["body_type"].snippet


def test_no_mass_in_running_order_or_payload_is_proposed(rebel: RangeBrochure) -> None:
    """Every payload reads `TBC` and no running-order mass is published at all."""
    built = build_extracted(_products(rebel)[0], basis="b")
    assert built.motorhome.mro_kilograms is None
    assert built.motorhome.mh_payload_kilograms is None
    assert "mro_kilograms" not in built.provenance
    assert "mh_payload_kilograms" not in built.provenance


def test_no_berths_or_seats_are_proposed(rebel: RangeBrochure) -> None:
    """The tiles give them as bare digits that run into the figure beside them in the
    extracted text — `2.9m2 2`."""
    built = build_extracted(_products(rebel)[0], basis="b")
    assert built.motorhome.berths is None
    assert built.motorhome.mh_passenger_seats_inc_driver is None
    assert "berths" not in built.provenance


def test_the_length_provenance_warns_about_the_tile(rebel: RangeBrochure) -> None:
    built = build_extracted(_products(rebel)[0], basis="b")
    assert "NOT the summary tile" in built.provenance["mh_length_mm"].snippet


# --- the self-check ---------------------------------------------------------------------------------------


def test_a_sound_product_reconciles(rebel: RangeBrochure) -> None:
    for product in _products(rebel):
        ok, basis = _reconciles(product)
        assert ok is True, basis


def test_a_gross_weight_outside_the_sprinters_band_is_refused() -> None:
    ok, basis = _reconciles(
        Product("Rebel", "RWD", "http://x", rrp_pounds=147000, mtplm_kilograms=246)
    )
    assert ok is False
    assert "plated" in basis


def test_the_widths_taken_the_wrong_way_round_are_refused() -> None:
    ok, basis = _reconciles(
        Product(
            "Rebel", "RWD", "http://x", rrp_pounds=147000, mtplm_kilograms=3500,
            mh_width_mm=2345, width_including_mirrors_mm=2020,
        )
    )
    assert ok is False
    assert "across the mirrors" in basis


# --- the special edition -------------------------------------------------------------------------------------


def test_the_rebel_raid_is_found_and_priced(rebel: RangeBrochure) -> None:
    assert rebel.special_editions.get("Rebel Raid") == 199995


def test_the_rebel_raid_is_not_collected(rebel: RangeBrochure) -> None:
    """A named edition is a product under the settled rule, but the brochure gives it no
    technical data at all — every required field would be inferred from the Rebel AWD."""
    assert "Rebel Raid" in SPECIAL_EDITION
    assert "NO technical figures" in SPECIAL_EDITION["Rebel Raid"]
    assert all(p.drivetrain in DRIVETRAINS for p in _products(rebel))


def test_the_rebellion_has_no_special_edition(rebellion: RangeBrochure) -> None:
    assert rebellion.special_editions == {}


def test_a_low_height_would_not_be_a_high_top() -> None:
    body_type, reason = body_type_for(2200)
    assert body_type is BodyType.CAMPERVAN
    assert "at or below" in reason
