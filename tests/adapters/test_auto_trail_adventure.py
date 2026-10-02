"""Auto-Trail's Adventure Coachbuilt range — the one range with no range page.

Everything here is pure parsing and joining; `collect` is not exercised.
"""

from __future__ import annotations

from src.adapters import auto_trail
from src.adapters.auto_trail import (
    ADVENTURE_RANGE_LABEL,
    ADVENTURE_SPECS,
    adventure_price_list_section,
    adventure_products,
    parse_adventure_price_list,
)
from src.product_model.enums import BodyType

#: The Adventure page of Auto-Trail's 2027 price list, as `fetch.pdf` extracts it, plus
#: the campervan Expedition rows that follow it in the same document.
PRICE_LIST = """\
ADVENTURE PRICE LIST
Applicable to Adventure 64, 74, 76, 76G
MODEL BASE VEHICLE  GROSS VEHICLE
WEIGHT
OVERALL
LENGTH
EX WORKS PRICE
Excl. VAT
VAT
20%
EX WORKS PRICE
Incl. VAT
ADVENTURE
64* Peugeot Boxer 140bhp (manual) 3,500/3,650kg 6.37m (20'9")  £57,083.00 £11,417.00 £68,500.00
74 Peugeot Boxer 140bhp (manual) 3,500/3,650/4,400kg 7.29m (23'9")  £59,167.00 £11,833.00 £71,000.00
76 Peugeot Boxer 140bhp (manual) 3,500/3,650/4,400kg 7.29m (23'9") £59,167.00 £11,833.00 £71,000.00
76G Peugeot Boxer 140bhp (manual) 3,500/3,650/4,400kg 7.29m (23'9") £59,167.00 £11,833.00 £71,000.00
*Adventure 64 is not available with a 180bhp 8-speed automatic gearbox

EXPEDITION VAN PRICE LIST
54 Fiat Ducato 140bhp (manual) 3,500kg 5.41m (17'9") £45,270.00 £9,054.00 £54,324.00
68 Fiat Ducato 140bhp (manual) 3,500kg 6.36m (20'10") £49,598.00 £9,920.00 £59,518.00
"""


def _spec(model: str):
    return next(s for s in ADVENTURE_SPECS if s.model == model)


# --- the range label ------------------------------------------------------------------


def test_the_label_keeps_the_two_adventures_apart() -> None:
    """**Ours, not Auto-Trail's.** They call it simply "Adventure", but they already sell
    an Adventure campervan range and FMLV files both under one manufacturer. The suffix
    copies the shape Auto-Trail themselves use for `Expedition Coachbuilt`."""
    assert ADVENTURE_RANGE_LABEL == "Adventure Coachbuilt"
    campervan_labels = {label for _path, label in auto_trail.DEFAULT_RANGES}
    assert "Adventure" in campervan_labels
    assert ADVENTURE_RANGE_LABEL not in campervan_labels


# --- reading the price list -----------------------------------------------------------


def test_the_price_list_is_read_for_price_length_weight_and_chassis() -> None:
    rows = parse_adventure_price_list(PRICE_LIST)

    assert sorted(rows) == ["64", "74", "76", "76G"]
    assert rows["64"].ex_works_incl_vat_pounds == 68500
    assert rows["64"].length_mm == 6370
    assert rows["64"].base_vehicle_manufacturer == "Peugeot"
    assert rows["76G"].length_mm == 7290


def test_only_the_adventure_page_is_read() -> None:
    """**The trap this exists for.** Every range in the document prints rows of the same
    shape, so an unscoped read also returns the campervan Expedition's 54 and 68. Neither
    collides with an Adventure model today, which is exactly why it would go unnoticed
    until one did."""
    section = adventure_price_list_section(PRICE_LIST)

    assert "64*" in section
    assert "EXPEDITION VAN" not in section
    assert "54" not in parse_adventure_price_list(PRICE_LIST)


def test_a_document_with_no_adventure_page_yields_nothing() -> None:
    assert adventure_price_list_section("EXPEDITION VAN PRICE LIST\n54 Fiat ...") == ""
    assert parse_adventure_price_list("nothing here") == {}


def test_the_base_gross_weight_is_recorded_not_the_upgrade() -> None:
    """`3,500/3,650/4,400kg` is one vehicle with two paid upgrades. FMLV holds the base."""
    rows = parse_adventure_price_list(PRICE_LIST)

    assert rows["74"].gross_weights_kg == (3500, 3650, 4400)
    assert rows["74"].mtplm_kilograms == 3500


def test_the_on_the_road_price_adds_the_verified_uplift() -> None:
    """Auto-Trail's website card sits exactly GBP635 above the price list's ex-works
    including VAT, checked across 25 models. The Adventure range has no card yet."""
    rows = parse_adventure_price_list(PRICE_LIST)

    assert rows["64"].on_the_road_pounds == 68500 + 635
    assert rows["74"].on_the_road_pounds == 71000 + 635


# --- joining the two documents --------------------------------------------------------


def test_four_products_are_built() -> None:
    products = adventure_products(PRICE_LIST)

    assert [p.model for p in products] == ["64", "74", "76", "76G"]
    assert {p.range_label for p in products} == {ADVENTURE_RANGE_LABEL}
    assert {p.body_type for p in products} == {BodyType.COACH_BUILT_OVER_CAB_BED}


def test_the_price_list_overrules_a_spreadsheet_length_that_disagrees() -> None:
    """**The trap this exists for.** The spreadsheet repeats 7288mm down all four rows,
    but Auto-Trail's price list gives the 64 as 6.37m and their news post says the range
    comes in two lengths. The spreadsheet is describing one model's length four times."""
    assert _spec("64").spreadsheet_length_mm == 7288

    sixty_four = next(p for p in adventure_products(PRICE_LIST) if p.model == "64")

    assert sixty_four.mh_length_mm == 6370
    assert any("918mm apart" in w for w in sixty_four.parse_warnings)


def test_a_length_that_agrees_to_the_rounded_metre_is_kept() -> None:
    """The price list prints 7.29m and the spreadsheet 7288mm — 2mm apart, so the more
    precise figure stands and nothing is warned about."""
    seventy_four = next(p for p in adventure_products(PRICE_LIST) if p.model == "74")

    assert seventy_four.mh_length_mm == 7288
    assert seventy_four.parse_warnings == ()


def test_the_standard_berths_and_belts_are_recorded_not_the_optioned_ones() -> None:
    """Auto-Trail's news post: "every Adventure model sleeps four people and comes with
    four seatbelts as standard, with the option to upgrade". The spreadsheet states 6
    berths on three of the four, and the price list sells six belts as a GBP995 option
    needing a GVW upgrade — so the extra capacity is an option and is not recorded."""
    products = adventure_products(PRICE_LIST)

    assert {p.berths for p in products} == {4}
    assert {p.mh_passenger_seats_inc_driver for p in products} == {4}


def test_the_payload_still_reconciles() -> None:
    for product in adventure_products(PRICE_LIST):
        assert product.mh_payload_kilograms == (
            product.mtplm_kilograms - product.mro_kilograms
        )


def test_the_provenance_does_not_claim_a_technical_specification() -> None:
    """There is no spec document for this range. Saying there is would send a reviewer
    looking for one that does not exist."""
    product = adventure_products(PRICE_LIST)[0]

    assert "Technical Specification" not in product.source_description
    assert "spreadsheet" in product.source_description
    assert "price list" in product.source_description


def test_an_empty_price_list_collects_nothing_rather_than_guessing() -> None:
    notes: list[str] = []

    assert adventure_products("", notes.append) == []
    assert any("No Adventure is collected" in n for n in notes)
