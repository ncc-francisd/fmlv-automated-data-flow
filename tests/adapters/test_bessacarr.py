"""Tests for the Bessacarr adapter's pure parsing functions, against the real pages.

Fixtures are four real pages from `bessacarrcaravan.co.uk`, fetched 17 September 2026 with
`<script>` and `<style>` removed. Four, because each carries something the others do not:

* **model-range** — the roster, and the reason it cannot be read from the navigation:
  the nav links all five model pages and only four have cards.
* **835** — a clean layout, and a card that omits the `kg` its siblings print.
* **850** — the page that prints the 845's personal-effects figure, higher than its own
  total payload.
* **780** — the withdrawn model, which fails both self-checks and must never be collected.

No network here.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.adapters import adapter_for, bessacarr, swift_caravan
from src.adapters.bessacarr import (
    EXPECTED_LAYOUTS,
    MANUFACTURER,
    MANUFACTURER_DISPLAY_NAME,
    MANUFACTURER_RANGE,
    BessacarrCaravan,
    _discrepancies,
    _reconciles,
    build_extracted,
    model_range_roster,
    parse_model_page,
)
from src.product_model.enums import CaravanBodyType
from src.vehicle_class import VehicleClass

FIXTURES = Path(__file__).parent / "fixtures"

URL = "https://www.bessacarrcaravan.co.uk/bessacarr835"


def _page(name: str) -> str:
    return (FIXTURES / f"bessacarr_{name}.html").read_text(encoding="utf-8")


def _roster() -> list[tuple[str, int]]:
    return model_range_roster(_page("model_range"))


def _product(model: str, *, card_mtplm: int | None = 2250) -> BessacarrCaravan:
    parsed = parse_model_page(_page(model), model, card_mtplm=card_mtplm)
    assert parsed is not None
    return parsed


# --------------------------------------------------------------------------- #
# The third brand under one manufacturer
# --------------------------------------------------------------------------- #


def test_bessacarr_is_the_third_brand_under_swift_group() -> None:
    """`ADAPTERS`' display-name key, which the Ace build introduced, earning its keep a
    second time — this time with two adapters in the *same* product area."""
    assert MANUFACTURER == swift_caravan.MANUFACTURER == "Swift Group Ltd"
    assert MANUFACTURER_DISPLAY_NAME == "Bessacarr"

    # The product area has to be named too: `adapter_for` defaults to motorhomes, where
    # `Swift Group Ltd` means Swift or Ace and "Bessacarr" matches neither.
    caravans = VehicleClass.CARAVAN
    assert adapter_for(MANUFACTURER, caravans, display_name="Bessacarr") is bessacarr
    assert adapter_for(MANUFACTURER, caravans, display_name="Swift") is swift_caravan
    assert adapter_for(MANUFACTURER, display_name="Bessacarr") is None


def test_swift_group_caravans_no_longer_resolve_without_a_brand() -> None:
    """Better than an arbitrary pick: the wrong adapter would propose four Bessacarrs
    against Swift's 26 caravans, or 26 Swift caravans against Bessacarr's four."""
    assert adapter_for(MANUFACTURER, VehicleClass.CARAVAN) is None


def test_this_adapter_declares_its_product_area() -> None:
    assert bessacarr.VEHICLE_CLASS is VehicleClass.CARAVAN


# --------------------------------------------------------------------------- #
# The roster, and the model that must not be in it
# --------------------------------------------------------------------------- #


def test_the_roster_is_four_and_comes_from_the_cards() -> None:
    assert [model for model, _mtplm in _roster()] == ["835", "845", "850", "860"]
    assert len(_roster()) == EXPECTED_LAYOUTS == 4


def test_the_withdrawn_780_is_linked_but_has_no_card() -> None:
    """The trap this roster reader exists for. `/model-range` links all five model pages
    from its navigation dropdown, so taking the hrefs would collect a 2025 model that is
    sold out, inactive in FMLV and contradicts itself."""
    page = _page("model_range")

    assert "/bessacarr780" in page
    assert "780" not in [model for model, _mtplm in _roster()]


def test_the_cards_carry_the_mtplm_with_or_without_its_unit() -> None:
    """`835 4 berth 2250 MTPLM` against `850 4 berth 2250kg MTPLM` — requiring the `kg`
    would silently halve the roster."""
    assert dict(_roster()) == {"835": 2250, "845": 2250, "850": 2250, "860": 2250}


def test_a_page_without_cards_yields_nothing() -> None:
    assert model_range_roster("<html><body>Bessacarr</body></html>") == []


# --------------------------------------------------------------------------- #
# The spec table
# --------------------------------------------------------------------------- #


def test_a_model_yields_every_field() -> None:
    product = _product("835")

    assert product.berths == 4
    assert product.twin_axle is True
    assert product.mtplm_kilograms == 2250
    assert product.mro_kilograms == 1965
    assert product.total_payload_kilograms == 285
    assert product.rrp_pounds == 54_995
    assert product.internal_length_mm == 6360
    assert product.shipping_length_mm == 7980
    assert product.awning_length_mm == 10_490
    assert product.overall_width_mm == 2450
    assert product.height_mm == 2590
    assert product.headroom_mm == 1950


def test_the_four_lengths_are_not_confused_with_each_other() -> None:
    """The way `docs/adapters/README.md` says a caravan adapter is most likely to go
    wrong. `Overall Length` is the shipping figure; reading it as the internal one would
    overstate the habitable space by 1.6m and look entirely plausible."""
    product = _product("835")

    assert product.internal_length_mm < product.shipping_length_mm
    assert product.awning_length_mm > product.shipping_length_mm


def test_a_two_part_label_is_read_past_its_parenthetical() -> None:
    """`Internal Length` and `(at bed box height)` are separate elements, as are
    `Overall Height` and `(inc. TV Aerial)#`."""
    assert "at bed box height" in _page("835")
    assert _product("835").internal_length_mm == 6360
    assert _product("835").height_mm == 2590


def test_the_misspelt_mtplm_label_is_matched() -> None:
    """The site writes `Permissable`. The pattern is loose across the word so it would
    survive them fixing the spelling."""
    assert "Permissable" in _page("835")
    assert _product("835").mtplm_kilograms == 2250


def test_the_single_axle_780_is_read_as_such() -> None:
    assert _product("780", card_mtplm=None).twin_axle is False
    assert _product("835").axle_evidence == "Numbers of Axles: 2"


def test_a_page_with_no_spec_table_yields_nothing() -> None:
    assert parse_model_page("<html><body>Bessacarr</body></html>", "835") is None


# --------------------------------------------------------------------------- #
# The self-checks, and the page that proves they are not vacuous
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("model", ["835", "850"])
def test_the_masses_close_on_every_model_in_the_roster(model: str) -> None:
    """`Total User Payload == MTPLM - MRO`, published independently of each other."""
    product = _product(model)

    assert _reconciles(product)[0] is True
    assert product.derived_payload_kilograms == product.total_payload_kilograms


def test_the_withdrawn_780_fails_the_arithmetic_and_is_dropped() -> None:
    """MRO 1774 + payload 215 = 1989 against a stated MTPLM of 1900. One published
    figure is wrong and nothing on the site says which."""
    product = _product("780", card_mtplm=None)

    assert product.mro_kilograms == 1774
    assert product.mtplm_kilograms == 1900
    assert product.total_payload_kilograms == 215

    reconciles, why_not = _reconciles(product)
    assert reconciles is False
    assert "215kg" in why_not


def test_the_780s_own_header_contradicts_its_own_table() -> None:
    """A third MTPLM on one page — the badge says 1800kg."""
    product = _product("780", card_mtplm=None)

    assert product.badge_mtplm_kilograms == 1800
    assert any("1800kg MTPLM" in note for note in _discrepancies(product))


def test_a_card_disagreeing_with_the_spec_table_drops_the_model() -> None:
    """The cross-document half of the check: two pages, written separately."""
    reconciles, why_not = _reconciles(replace(_product("835"), card_mtplm_kilograms=2125))

    assert reconciles is False
    assert "2125kg" in why_not and "2250kg" in why_not


def test_a_model_missing_a_mass_is_dropped() -> None:
    reconciles, why_not = _reconciles(replace(_product("835"), mro_kilograms=None))

    assert reconciles is False
    assert "MRO" in why_not


# --------------------------------------------------------------------------- #
# Payload: the total, not the row labelled personal effects
# --------------------------------------------------------------------------- #


def test_the_850_prints_the_845s_personal_effects_figure() -> None:
    """306kg against its own Total User Payload of 299kg — higher than the whole
    payload, so it cannot be a subdivision of it."""
    product = _product("850")

    assert product.total_payload_kilograms == 299
    assert product.stated_personal_effects_kilograms == 306

    notes = _discrepancies(product)
    assert len(notes) == 1
    assert "306kg" in notes[0] and "299kg" in notes[0]


def test_the_total_is_what_reaches_the_payload_column() -> None:
    """Not the figure whose label matches the column — see the module docstring."""
    caravan = build_extracted(_product("850"), URL).caravan

    assert caravan.personal_effects_payload_kilograms == 299


def test_the_optional_equipment_column_is_asked_to_stay_blank() -> None:
    """Recorded with no value, so the two payload columns sum to the published total."""
    extracted = build_extracted(_product("835"), URL)

    assert "optional_equipment_payload_kilograms" in extracted.provenance
    assert extracted.caravan.optional_equipment_payload_kilograms is None


def test_a_model_whose_two_payload_figures_agree_reports_nothing() -> None:
    assert _discrepancies(_product("835")) == []


# --------------------------------------------------------------------------- #
# What reaches the reviewer
# --------------------------------------------------------------------------- #


def test_the_identity_is_the_range_fmlv_already_holds() -> None:
    caravan = build_extracted(_product("835"), URL).caravan

    assert caravan.manufacturer == "Swift Group Ltd"
    assert caravan.manufacturer_display_name == "Bessacarr"
    assert caravan.manufacturer_range == MANUFACTURER_RANGE == "Bessacarr By Design"
    assert caravan.model == "835"


def test_both_halves_of_the_identity_carry_provenance() -> None:
    """`compare_fields` walks only fields that have provenance, and accepting a range
    change without its model corrupts the name."""
    provenance = build_extracted(_product("835"), URL).provenance

    assert "manufacturer_range" in provenance
    assert "model" in provenance


def test_the_dealer_columns_are_written_by_nothing() -> None:
    """Ruled on 17 September 2026: Bessacarr is a brand in its own right, not a dealer
    special, and FMLV's own four rows hold all three blank."""
    caravan = build_extracted(_product("835"), URL).caravan
    provenance = build_extracted(_product("835"), URL).provenance

    assert caravan.dealer is None
    assert caravan.dealer_specials_range is None
    assert caravan.dealer_model_variant is None
    assert not {"dealer", "dealer_specials_range", "dealer_model_variant"} & set(provenance)


def test_the_body_type_is_rigid_and_says_why() -> None:
    extracted = build_extracted(_product("835"), URL)

    assert extracted.caravan.body_type is CaravanBodyType.RIGID
    assert "walls fold or rise" in extracted.provenance["body_type"].snippet


def test_the_exterior_body_length_is_never_emitted() -> None:
    """Out of automated scope globally — see `docs/adapters/README.md`."""
    extracted = build_extracted(_product("835"), URL)

    assert extracted.caravan.exterior_body_length_mm is None
    assert "exterior_body_length_mm" not in extracted.provenance


def test_the_year_is_never_emitted() -> None:
    """A carry-through field only a person bumps, and the pages say 2025 where FMLV
    holds 2026."""
    extracted = build_extracted(_product("835"), URL)

    assert extracted.caravan.year is None
    assert "year" not in extracted.provenance


# --------------------------------------------------------------------------- #
# Habitation, which is thin and is the wrong equipment list
# --------------------------------------------------------------------------- #


def test_bed_types_are_not_emitted() -> None:
    """The `Bed Sizes` block names positions without saying whether a bed is built in or
    made up from the seating, which is what `BedType` has to distinguish."""
    assert "Bed Sizes" in _page("835")

    extracted = build_extracted(_product("835"), URL)

    assert extracted.caravan.bed_types == []
    assert "bed_types" not in extracted.provenance


def test_a_habitation_finding_quotes_the_page() -> None:
    from src.adapters import habitation  # noqa: PLC0415

    equipment = tuple(habitation.list_items(_page("835")))
    extracted = build_extracted(_product("835"), URL, equipment=equipment)

    for field_name in ("heating", "refrigeration", "microwave"):
        if field_name in extracted.provenance:
            assert extracted.provenance[field_name].snippet


def test_no_equipment_list_means_no_habitation_findings() -> None:
    extracted = build_extracted(_product("835"), URL, equipment=())

    assert extracted.caravan.heating is None
    assert extracted.caravan.refrigeration is None
