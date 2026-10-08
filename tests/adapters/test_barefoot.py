"""Barefoot's catalogue table, its prices page, and the two pages beside them.

Every fixture is a real capture of 8 October 2026. The figures asserted here are the ones
FMLV already holds on all four of its live Barefoots, which is what makes them worth
asserting: a parse that drifts off the columns stops matching them immediately.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters import barefoot, habitation
from src.product_model.enums import CaravanBodyType

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def page_text() -> str:
    return _fixture("barefoot-catalogue-page10.txt")


@pytest.fixture(scope="module")
def specs(page_text: str) -> list[barefoot.Specification]:
    found = barefoot.parse_specifications(page_text)
    dimensions = barefoot.parse_dimensions(page_text, [spec.model for spec in found])
    for spec in found:
        for name, value in dimensions.get(spec.model, {}).items():
            setattr(spec, name, value)
    return found


def _by_model(specs: list[barefoot.Specification]) -> dict[str, barefoot.Specification]:
    return {spec.model: spec for spec in specs}


# --- The specification block -----------------------------------------------------------


def test_every_model_in_the_catalogue_is_found(specs: list[barefoot.Specification]) -> None:
    """Six, which is what the site's own navigation lists."""
    assert [spec.model for spec in specs] == [
        "Bothy",
        "Lite",
        "Classic",
        "Forward",
        "Eclipse",
        "Country Living",
    ]
    assert len(specs) == barefoot.EXPECTED_MODELS


def test_the_three_models_sharing_a_column_get_that_column(
    specs: list[barefoot.Specification],
) -> None:
    """Classic, Forward and Eclipse are one column of the table and three products."""
    models = _by_model(specs)
    for name in ("Classic", "Forward", "Eclipse"):
        assert models[name].mtplm_kilograms == 1100
        assert models[name].mro_kilograms == 960
        assert models[name].published_payload_kilograms == 140
        assert models[name].berths == 2


def test_figures_match_what_fmlv_already_holds(specs: list[barefoot.Specification]) -> None:
    """4129 Classic, to the millimetre and the kilogram."""
    classic = _by_model(specs)["Classic"]
    assert classic.shipping_length_mm == 5080
    assert classic.exterior_body_length_mm == 3780
    assert classic.overall_width_mm == 1920
    assert classic.height_mm == 2360
    assert classic.headroom_mm == 1870
    assert classic.derived_payload_kilograms == 140


def test_the_bothy_is_the_only_three_berth_and_has_its_own_dimension_column(
    specs: list[barefoot.Specification],
) -> None:
    """Its shell is the others' but its internal height is not — 1910 against 1870."""
    bothy = _by_model(specs)["Bothy"]
    assert bothy.berths == 3
    assert bothy.headroom_mm == 1910
    assert bothy.shipping_length_mm == 5080
    assert bothy.exterior_body_length_mm == 3780


def test_the_lower_of_each_published_pair_is_taken(specs: list[barefoot.Specification]) -> None:
    """`750/850` is specified at the time of order, so the base caravan is 750."""
    bothy = _by_model(specs)["Bothy"]
    assert bothy.mtplm_kilograms == 750
    assert bothy.mro_kilograms == 706
    assert bothy.published_payload_kilograms == 44


def test_every_model_is_a_single_axle(specs: list[barefoot.Specification]) -> None:
    assert all(spec.twin_axle is False for spec in specs)


# --- The erratum ------------------------------------------------------------------------


def test_the_lites_mtplm_is_corrected_and_the_correction_is_visible(
    specs: list[barefoot.Specification],
) -> None:
    """The catalogue prints `1100/1200`; only `1000/1100` reconciles with its own payload."""
    lite = _by_model(specs)["Lite"]
    assert lite.published_mtplm_cell == "1100/1200"
    assert lite.corrected_mtplm_cell == "1000/1100"
    assert lite.mtplm_kilograms == 1000
    assert lite.derived_payload_kilograms == lite.published_payload_kilograms == 100


def test_the_catalogue_as_published_fails_the_self_check(page_text: str) -> None:
    """Without the erratum the Lite is dropped rather than proposed — which is the point."""
    lite = next(
        spec for spec in barefoot.parse_specifications(page_text) if spec.model == "Lite"
    )
    lite.mtplm_kilograms = barefoot._lower(lite.published_mtplm_cell or "")
    reconciles, basis = barefoot._reconciles(lite)
    assert reconciles is False
    assert "200kg" in basis and "100kg" in basis


def test_the_erratum_lapses_once_barefoot_fix_it(page_text: str) -> None:
    """It is keyed on the wrong value, so a corrected catalogue is passed straight through."""
    fixed = page_text.replace("1100/1200 1100/1200 1100/1200", "1000/1100 1100/1200 1100/1200")
    lite = next(spec for spec in barefoot.parse_specifications(fixed) if spec.model == "Lite")
    assert lite.published_mtplm_cell == "1000/1100"
    assert lite.corrected_mtplm_cell == "1000/1100"
    assert lite.mtplm_kilograms == 1000


# --- The self-check ---------------------------------------------------------------------


def test_every_model_reconciles_once_the_erratum_is_applied(
    specs: list[barefoot.Specification],
) -> None:
    for spec in specs:
        reconciles, basis = barefoot._reconciles(spec)
        assert reconciles is True, f"{spec.model}: {basis}"


def test_a_column_read_one_place_off_is_caught(specs: list[barefoot.Specification]) -> None:
    """The Bothy's masses on the Classic is the failure the check exists for."""
    models = _by_model(specs)
    misaligned = barefoot.Specification(
        model="Classic",
        mtplm_kilograms=models["Bothy"].mtplm_kilograms,
        mro_kilograms=models["Bothy"].mro_kilograms,
        published_payload_kilograms=models["Classic"].published_payload_kilograms,
    )
    assert barefoot._reconciles(misaligned)[0] is False


# --- The column headings ----------------------------------------------------------------


def test_a_changed_specification_heading_yields_nothing_rather_than_a_guess(
    page_text: str,
) -> None:
    """No heading means no way to tell which model owns which column, so no products."""
    assert barefoot.parse_specifications(page_text.replace("Specification Barefoot", "Spec")) == []


def test_a_row_with_the_wrong_number_of_cells_is_dropped(page_text: str) -> None:
    """Four columns and three figures: the row is skipped, the rest of the model survives."""
    damaged = page_text.replace("Weight (MRO**), kg 706 900 960 960", "Weight (MRO**), kg 706 900 960")
    classic = next(spec for spec in barefoot.parse_specifications(damaged) if spec.model == "Classic")
    assert classic.mro_kilograms is None
    assert classic.mtplm_kilograms == 1100


def test_the_dimension_columns_are_split_on_punctuation_not_position(page_text: str) -> None:
    """`... Forward, Lite Bothy` — the missing comma is the whole of the boundary."""
    roster = [spec.model for spec in barefoot.parse_specifications(page_text)]
    columns = barefoot._dimension_columns(page_text, roster)
    assert columns is not None
    assert sorted(columns[0]) == ["Classic", "Country Living", "Eclipse", "Forward", "Lite"]
    assert columns[1] == ["Bothy"]


# --- The pages beside the catalogue -----------------------------------------------------


def test_the_catalogue_is_rediscovered_from_the_home_page() -> None:
    url = barefoot.catalogue_url(_fixture("barefoot_home.html"))
    assert url == "https://www.go-barefoot.co.uk/wp-content/uploads/2025/10/Go-Barefoot-cat.pdf"


def test_the_internal_length_comes_off_vital_statistics() -> None:
    """3560 — the one figure the catalogue omits and FMLV holds."""
    assert barefoot.internal_length_from(_fixture("barefoot_vital_statistics.html")) == 3560


def test_the_prices_page_gives_one_price_per_model() -> None:
    roster = ["Bothy", "Lite", "Classic", "Forward", "Eclipse", "Country Living"]
    assert barefoot.prices_from(_fixture("barefoot_prices.html"), roster) == {
        "Bothy": 25950,
        "Lite": 34950,
        "Classic": 39950,
        "Forward": 39950,
        "Eclipse": 39950,
        "Country Living": 40500,
    }


def test_the_accessory_bundle_is_not_read_as_a_price() -> None:
    """`'Barefoot and Go' – £41,500` names its models *after* the price, so it is skipped."""
    prices = barefoot.prices_from(
        _fixture("barefoot_prices.html"), ["Classic", "Forward", "Eclipse"]
    )
    assert set(prices.values()) == {39950}


def test_the_payment_terms_do_not_price_the_bothy() -> None:
    """`£15,000 (£10,000 for Bothy) payment required...` would otherwise beat the real one."""
    assert barefoot.prices_from(_fixture("barefoot_prices.html"), ["Bothy"]) == {"Bothy": 25950}


# --- Habitation findings ----------------------------------------------------------------


def test_the_fittings_list_stops_before_the_site_navigation() -> None:
    lines = barefoot.spec_lines(_fixture("barefoot_bothy.html"))
    assert any("Thetford Porta Potti" in line for line in lines)
    assert not any(line.strip() in {"Home", "Contact", "Gallery"} for line in lines)


def test_a_model_page_without_a_fittings_list_yields_nothing() -> None:
    """The four older pages carry prose and navigation alone, which must read as silence."""
    assert barefoot.spec_lines(_fixture("barefoot_classic.html")) == []


def test_barefoots_fittings_settle_nothing_the_shared_vocabulary_can_state() -> None:
    """Both new models read as silence on every habitation field, and that is the answer.

    It is worth asserting rather than assuming, because it is a real finding about this
    manufacturer: Barefoot describe a washroom in their own words (*"Beautiful curved
    bathroom with basin and shower"*, *"Dometic cassette toilet"*) without ever using the
    industry phrasing `habitation` reads, and the Bothy and the Lite carry a **cool box**
    rather than a fridge. Per `docs/adapters/README.md`, silence is not a negative — so
    nothing is asserted, and the run says so instead of inventing a value.
    """
    for name in ("barefoot_bothy.html", "barefoot_lite.html"):
        lines = habitation.usable_lines(barefoot.spec_lines(_fixture(name)))
        assert lines, f"{name} should still yield a fittings list"
        stated = set(habitation.features_from(lines)) - {"bed_types"}
        assert stated == set(), f"{name} unexpectedly stated {stated}"


# --- Judgement --------------------------------------------------------------------------


def test_barefoot_are_rigid_despite_being_light_enough_for_a_micro() -> None:
    """Both halves of the test are needed and only one is met — the naming half fails."""
    body_type, reason = barefoot.body_type_for("the perfect small caravan", 750)
    assert body_type is CaravanBodyType.RIGID
    assert "small caravan" in reason


def test_the_micro_test_is_applied_rather_than_its_answer_asserted() -> None:
    body_type, _ = barefoot.body_type_for("Luxury Mini Caravan in fibreglass", 750)
    assert body_type is CaravanBodyType.MICRO


def test_a_named_micro_over_the_weight_stays_rigid() -> None:
    body_type, _ = barefoot.body_type_for("Luxury Mini Caravan in fibreglass", 1400)
    assert body_type is CaravanBodyType.RIGID


# --- The built product ------------------------------------------------------------------


def test_the_range_repeats_the_model(specs: list[barefoot.Specification]) -> None:
    """One name, and Nova will not take a blank range."""
    built = barefoot.build_extracted(
        _by_model(specs)["Classic"], basis="the arithmetic", catalogue="http://example/cat.pdf"
    )
    assert built.caravan.manufacturer_range == "Classic"
    assert built.caravan.model == "Classic"
    assert built.caravan.manufacturer == "Barefoot Caravans"
    assert built.caravan.manufacturer_display_name == "Barefoot"


def test_the_whole_payload_is_recorded_as_personal_effects(
    specs: list[barefoot.Specification],
) -> None:
    built = barefoot.build_extracted(
        _by_model(specs)["Classic"], basis="the arithmetic", catalogue="http://example/cat.pdf"
    )
    assert built.caravan.personal_effects_payload_kilograms == 140
    assert built.caravan.optional_equipment_payload_kilograms is None


def test_no_awning_length_is_ever_proposed(specs: list[barefoot.Specification]) -> None:
    """Barefoot publish none, so FMLV's own 3000mm must stand untouched."""
    built = barefoot.build_extracted(
        _by_model(specs)["Classic"], basis="the arithmetic", catalogue="http://example/cat.pdf"
    )
    assert built.caravan.awning_length_mm is None
    assert "awning_length_mm" not in built.provenance


def test_a_cool_box_is_never_recorded_as_a_fridge(specs: list[barefoot.Specification]) -> None:
    """The Bothy carries a 24L cool box and no fridge, and the product must say neither.

    `habitation` reads only the words fridge, refrigerator and refrigeration, so a cool box
    reaches a reviewer as nothing said rather than as a fridge Barefoot never claimed.
    """
    bothy = _by_model(specs)["Bothy"]
    bothy.equipment = habitation.usable_lines(barefoot.spec_lines(_fixture("barefoot_bothy.html")))
    assert any("cool box" in line.lower() for line in bothy.equipment)
    built = barefoot.build_extracted(
        bothy, basis="the arithmetic", catalogue="http://example/cat.pdf"
    )
    assert built.caravan.refrigeration is None
    assert "refrigeration" not in built.provenance


def test_the_bothy_is_built_whole_from_its_three_sources(
    specs: list[barefoot.Specification],
) -> None:
    """Catalogue figures, Vital Statistics for the one it omits, prices page for the price."""
    bothy = _by_model(specs)["Bothy"]
    bothy.internal_length_mm = 3560
    bothy.rrp_pounds = 25950
    built = barefoot.build_extracted(
        bothy, basis="the arithmetic", catalogue="http://example/cat.pdf"
    )
    assert built.caravan.berths == 3
    assert built.caravan.mtplm_kilograms == 750
    assert built.caravan.personal_effects_payload_kilograms == 44
    assert built.caravan.body_type is CaravanBodyType.RIGID
    assert built.caravan.twin_axle is False
    assert built.caravan.rrp_pounds == built.caravan.price_min_range_pounds == 25950
    assert built.provenance["internal_length_mm"].source_url == barefoot.VITAL_STATISTICS_URL
    assert built.provenance["rrp_pounds"].source_url == barefoot.PRICES_URL
    assert built.provenance["mtplm_kilograms"].source_url == "http://example/cat.pdf"


def test_the_lites_corrected_mtplm_says_so_in_its_provenance(
    specs: list[barefoot.Specification],
) -> None:
    """A reviewer must be able to see that the published figure was not taken at face value."""
    built = barefoot.build_extracted(
        _by_model(specs)["Lite"], basis="the arithmetic", catalogue="http://example/cat.pdf"
    )
    snippet = built.provenance["mtplm_kilograms"].snippet
    assert "1100/1200" in snippet
    assert "1,000kg" in snippet
