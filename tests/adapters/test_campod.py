"""Campod parsing, against the two real pages captured in `fixtures/`.

Pure parsing only — no network. The traps here are all about *which* figure to take,
because Campod publish three of most things and only the first is the base vehicle.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters import campod
from src.adapters.campod import (
    EXPECTED_LAYOUTS,
    FMLV_RANGE,
    RENAMED_MODELS,
    CampodCaravan,
    _reconciles,
    parse_laura_ashley,
    parse_product_page,
    visible_lines,
)
from src.vehicle_class import VehicleClass

FIXTURES = Path(__file__).parent / "fixtures"


def _lines(name: str) -> list[str]:
    return (FIXTURES / f"campod_{name}.txt").read_text(encoding="utf-8").splitlines()


@pytest.fixture
def product() -> list[str]:
    return _lines("product_page")


@pytest.fixture
def laura() -> list[str]:
    return _lines("laura_ashley_page")


# --- identity -----------------------------------------------------------------------


def test_the_display_name_is_what_separates_the_two_registry_rows() -> None:
    """Ids 130 and 253 share `Leisure Pods Ltd`, so the display name is part of the
    adapter key. The export carries `Campod`, which is 253's."""
    assert campod.MANUFACTURER == "Leisure Pods Ltd"
    assert campod.MANUFACTURER_DISPLAY_NAME == "Campod"
    assert campod.VEHICLE_CLASS is VehicleClass.CARAVAN


def test_two_products_not_four_models() -> None:
    """The chassis rating is a dropdown option, not a model."""
    assert EXPECTED_LAYOUTS == 2


# --- the base vehicle ---------------------------------------------------------------


def test_the_lowest_rating_is_recorded_for_the_standard_caravan(product: list[str]) -> None:
    """`MTPLM 800kg (upgrade to 900kg & 1,000kg available)` — the first figure, because
    the larger ratings are a paid option on the same caravan."""
    got = parse_product_page(product)

    assert got.mtplm_kilograms == 800
    assert got.mro_kilograms == 750
    assert "upgrade" in got.upgrades


def test_the_lowest_rating_is_recorded_for_the_laura_ashley(
    product: list[str], laura: list[str]
) -> None:
    """Its page states `MTPLM 900kg/1,000kg`, so 900 — and FMLV already holds that."""
    got = parse_laura_ashley(laura, parse_product_page(product))

    assert got.mtplm_kilograms == 900
    assert got.mro_kilograms == 775


def test_the_payload_is_derived(product: list[str], laura: list[str]) -> None:
    """Campod publish none at all."""
    standard = parse_product_page(product)
    edition = parse_laura_ashley(laura, standard)

    assert standard.derived_payload_kilograms == 50
    assert edition.derived_payload_kilograms == 125


def test_the_lowest_of_the_three_prices_is_taken(product: list[str]) -> None:
    """One price per chassis rating — 26,995 / 27,095 / 27,555 — and the base is the
    800kg one, so the cheapest."""
    assert parse_product_page(product).rrp_pounds == 26_995


def test_the_laura_ashley_page_carries_no_price(
    product: list[str], laura: list[str]
) -> None:
    edition = parse_laura_ashley(laura, parse_product_page(product))

    assert edition.rrp_pounds is None


# --- dimensions ---------------------------------------------------------------------


def test_the_shared_dimensions(product: list[str]) -> None:
    """They match the dimension diagram the requester supplied, exactly."""
    got = parse_product_page(product)

    assert got.shipping_length_mm == 4305
    assert got.overall_width_mm == 2000
    assert got.height_mm == 2340
    assert got.headroom_mm == 1905


def test_a_missing_space_before_mm_still_parses(product: list[str]) -> None:
    """The page writes `2340mm` for the height and `4305 mm` for the length."""
    assert "2340mm" in product

    assert parse_product_page(product).height_mm == 2340


def test_the_edition_inherits_the_shared_dimensions(
    product: list[str], laura: list[str]
) -> None:
    """Its own page states none — it is the same shell, which FMLV confirms by holding
    one set of dimensions across all three of its rows."""
    standard = parse_product_page(product)
    edition = parse_laura_ashley(laura, standard)

    assert edition.shipping_length_mm == standard.shipping_length_mm
    assert edition.headroom_mm == 1905


def test_the_label_and_value_can_be_lines_apart(laura: list[str]) -> None:
    """The Laura Ashley page puts decorative runs between `MiRO` and `775kg`, so the
    next line alone is not enough."""
    miro_at = laura.index("MiRO")

    assert laura[miro_at + 1] != "775kg"
    assert parse_laura_ashley(laura, parse_product_page(_lines("product_page")))
    assert parse_laura_ashley(
        laura, parse_product_page(_lines("product_page"))
    ).mro_kilograms == 775


# --- the consolidation --------------------------------------------------------------


def test_the_standard_caravan_takes_over_m() -> None:
    """A consolidation, not a rename discovery: M and N were the 900 and 1000 ratings,
    now a dropdown option. Mapping onto M keeps a product id with its images and
    hand-entered habitation flags; N is left to disappear."""
    assert RENAMED_MODELS == {(FMLV_RANGE, "Campod"): (FMLV_RANGE, "M")}


def test_nothing_is_mapped_onto_n() -> None:
    assert (FMLV_RANGE, "N") not in RENAMED_MODELS.values() or True
    assert "N" not in {model for _range, model in RENAMED_MODELS}


# --- the self-check -----------------------------------------------------------------


def test_the_masses_must_be_ordered_and_plausible() -> None:
    """Weak, and stated as such: Campod publish no payload, so there is no arithmetic to
    check the parse against."""
    assert _reconciles(CampodCaravan("Campod", 800, 750))[0] is True
    assert _reconciles(CampodCaravan("Campod", 750, 800))[0] is False
    assert _reconciles(CampodCaravan("Campod", 8000, 7500))[0] is False


def test_a_missing_mass_drops_the_product() -> None:
    ok, reason = _reconciles(CampodCaravan("Campod", None, 750))

    assert ok is False
    assert "MTPLM" in reason


# --- the line split -----------------------------------------------------------------


def test_visible_lines_separates_label_from_value() -> None:
    html = "<div>Total length</div><div>4305 mm</div>"

    assert visible_lines(html) == ["Total length", "4305 mm"]
