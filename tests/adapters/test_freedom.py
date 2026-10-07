"""Freedom Caravans — parsing and derivation only, no network.

Fixtures are the real pages of 7 October 2026, with the inline CSS and scripts stripped.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters import ADAPTERS, adapter_for, freedom
from src.adapters.freedom import (
    EXPECTED_MODELS,
    MODELS,
    Specification,
    _reconciles,
    build_extracted,
    parse_berths,
    parse_price,
    parse_specification,
    roster_slugs,
)
from src.product_model.enums import CaravanBodyType
from src.vehicle_class import VehicleClass

FIXTURES = Path(__file__).parent / "fixtures"


def _page(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def microlite_sport() -> str:
    """A pop-top: its labels are `Height (Roof Down)` and `Headroom (Roof Up)`."""
    return _page("freedom-microlite-sport.html")


@pytest.fixture
def carpento_360() -> str:
    """A fixed roof: plain `Height` and `Headroom`."""
    return _page("freedom-carpento-360.html")


@pytest.fixture
def models_index() -> str:
    return _page("freedom-models-index.html")


def _model(fmlv_model: str):
    return next(m for m in MODELS if m.fmlv_model == fmlv_model)


# --- registry -------------------------------------------------------------------------


def test_the_adapter_is_wired_in_as_a_caravan_adapter() -> None:
    assert freedom.MANUFACTURER == "Freedom Caravans"
    assert freedom.MANUFACTURER_DISPLAY_NAME == "Freedom"
    assert freedom.VEHICLE_CLASS is VehicleClass.CARAVAN
    assert (
        adapter_for("Freedom Caravans", VehicleClass.CARAVAN, display_name="Freedom")
        is freedom
    )
    assert ("Freedom Caravans", "Freedom", VehicleClass.CARAVAN) in ADAPTERS


# --- the price, which is the whole reason this adapter exists in this shape ------------


def test_the_price_comes_from_the_model_page(microlite_sport: str, carpento_360: str) -> None:
    assert parse_price(microlite_sport) == 14995
    assert parse_price(carpento_360) == 23995


def test_the_index_price_disagrees_and_is_never_used(models_index: str) -> None:
    """**The trap this adapter is shaped around.** `/models/` carries a `from` price
    beside every model and disagrees with the model pages on six of the eight — it says
    GBP13,995 for the Microlite Sport where the model page and FMLV both say GBP14,995.
    An adapter reading the index would proposes five wrong prices on its first run.

    So `parse_price` is never given the index, and this test pins the discrepancy rather
    than the behaviour: if Freedom ever fix the index, this is what will tell us."""
    assert "13,995" in models_index, "the index's stale Microlite Sport price"
    assert parse_price(models_index) != 14995, "the index does not agree with the pages"


# --- the roster -----------------------------------------------------------------------


def test_the_roster_is_read_from_the_index(models_index: str) -> None:
    slugs = roster_slugs(models_index)

    assert len(slugs) == EXPECTED_MODELS == 8
    assert slugs == sorted(set(slugs), key=slugs.index), "no duplicates"
    assert {m.slug for m in MODELS} == set(slugs)


def test_fmlv_files_by_model_family_not_the_sites_classic_range() -> None:
    """The site groups five models under a `Classic Range` heading. FMLV does not use it —
    its range is the family, and the Sunseeker is the one no slug would give you."""
    assert {m.fmlv_range for m in MODELS} == {
        "Jetstream", "Microlite", "Sunseeker", "Carpento", "Wayfarer",
    }
    assert _model("Classic").slug == "sunseeker"
    assert _model("Classic").fmlv_range == "Sunseeker"
    assert not any(m.fmlv_range == "Classic" for m in MODELS)


# --- the specification ----------------------------------------------------------------


def test_the_weights_and_dimensions_of_a_pop_top(microlite_sport: str) -> None:
    spec = parse_specification(microlite_sport)

    assert spec.mtplm_kilograms == 750
    assert spec.mro_kilograms == 580
    assert spec.published_payload_kilograms == 170
    assert spec.shipping_length_mm == 4000
    assert spec.exterior_body_length_mm == 2820
    assert spec.overall_width_mm == 1940
    assert spec.height_mm == 2210
    assert spec.headroom_mm == 1880


def test_the_roof_qualified_labels_are_read_too(microlite_sport: str, carpento_360: str) -> None:
    """**The trap this exists for.** The two Microlites are pop-tops and head their rows
    `Height (Roof Down)` and `Headroom (Roof Up)`; the other six say plain `Height` and
    `Headroom`. Matching only the plain spelling loses both dimensions on a quarter of the
    range, and loses them silently."""
    assert "Height (Roof Down)" in microlite_sport
    assert "Height (Roof Down)" not in carpento_360

    assert parse_specification(microlite_sport).height_mm == 2210
    assert parse_specification(carpento_360).height_mm == 2350


def test_the_two_lengths_are_not_interchangeable(carpento_360: str) -> None:
    """`Overall Length` includes the hitch; `Body Length` is the body. FMLV holds 4800 and
    3600 for this model, which is how the mapping was confirmed rather than assumed."""
    spec = parse_specification(carpento_360)

    assert spec.shipping_length_mm == 4800
    assert spec.exterior_body_length_mm == 3600
    assert spec.shipping_length_mm > spec.exterior_body_length_mm


def test_a_whole_number_of_metres_parses(microlite_sport: str) -> None:
    """`Overall Length: 4m` has no decimal point where every other dimension does."""
    assert parse_specification(microlite_sport).shipping_length_mm == 4000


def test_a_page_with_no_spec_block_yields_nothing_rather_than_guessing() -> None:
    assert parse_specification("<html><body>no numbers here</body></html>") == Specification()


# --- berths ---------------------------------------------------------------------------


def test_berths_come_from_the_title(microlite_sport: str, carpento_360: str) -> None:
    assert parse_berths(microlite_sport) == 3
    assert parse_berths(carpento_360) == 3


def test_a_page_that_states_no_berths_proposes_none() -> None:
    """**Three of the eight pages say nothing about berths**, and FMLV's own figure has to
    stand for those. Guessing from the bed sizes is the invention the guide warns against:
    the Jetstream Twin Sport lists a double *and* a single where FMLV holds two berths."""
    assert parse_berths("<html><head><title>Freedom Jetstream Twin Sport</title></head></html>") is None


# --- the self-check -------------------------------------------------------------------


def test_the_published_payload_checks_the_two_masses() -> None:
    ok, reason = _reconciles(
        Specification(mtplm_kilograms=750, mro_kilograms=580, published_payload_kilograms=170)
    )

    assert ok
    assert "750" in reason and "580" in reason


def test_a_payload_that_does_not_reconcile_is_refused() -> None:
    """**Dropped, not proposed.** Without this a misread column reaches a reviewer as a
    plausible caravan carrying another model's weights."""
    ok, reason = _reconciles(
        Specification(mtplm_kilograms=750, mro_kilograms=580, published_payload_kilograms=150)
    )

    assert not ok
    assert "170kg against a published payload of 150kg" in reason


def test_a_page_missing_a_mass_is_refused() -> None:
    assert _reconciles(Specification(mtplm_kilograms=750))[0] is False
    assert _reconciles(Specification(mtplm_kilograms=750, mro_kilograms=580))[0] is False


# --- what reaches the pipeline --------------------------------------------------------


def _built(page: str, fmlv_model: str):
    spec = parse_specification(page)
    ok, basis = _reconciles(spec)
    assert ok
    return build_extracted(
        _model(fmlv_model), spec, price_pounds=parse_price(page),
        berths=parse_berths(page), basis=basis,
    )


def test_the_derived_payload_goes_in_personal_effects(microlite_sport: str) -> None:
    """Per `docs/adapters/README.md`: the whole of a single published payload figure is
    the personal-effects total, and the optional column gets provenance with no value so a
    stale figure can be cleared rather than silently blanked."""
    extracted = _built(microlite_sport, "Sport")

    assert extracted.caravan.personal_effects_payload_kilograms == 170
    assert extracted.caravan.optional_equipment_payload_kilograms is None
    assert "optional_equipment_payload_kilograms" in extracted.provenance


def test_no_internal_length_is_ever_proposed(microlite_sport: str) -> None:
    """No Freedom model publishes one, so FMLV's column is left alone."""
    extracted = _built(microlite_sport, "Sport")

    assert extracted.caravan.internal_length_mm is None
    assert "internal_length_mm" not in extracted.provenance


def test_every_model_is_a_micro(microlite_sport: str, carpento_360: str) -> None:
    """The two-part test: Freedom build small lightweight caravans and the heaviest in the
    range is 1000kg. All nine FMLV rows already read `type_micro`."""
    for page, model in ((microlite_sport, "Sport"), (carpento_360, "360")):
        assert _built(page, model).caravan.body_type is CaravanBodyType.MICRO


def test_the_pop_top_is_still_filed_as_a_micro(microlite_sport: str) -> None:
    """**Not an oversight.** The Microlite is a pop-top, but the caravan type columns are
    single-select and FMLV has settled on micro for all nine rows. The roof is read for
    its dimensions, not for the body type."""
    extracted = _built(microlite_sport, "Sport")

    assert extracted.caravan.body_type is CaravanBodyType.MICRO
    assert extracted.caravan.height_mm == 2210, "roof down"
    assert extracted.caravan.headroom_mm == 1880, "roof up"


def test_provenance_names_the_page_it_came_from(carpento_360: str) -> None:
    extracted = _built(carpento_360, "360")

    for field in ("rrp_pounds", "mtplm_kilograms", "shipping_length_mm", "body_type"):
        assert field in extracted.provenance, field
        assert extracted.provenance[field].source_url.endswith("/models/carpento-360/")
        assert extracted.provenance[field].snippet.startswith("Carpento 360 — ")


def test_the_price_provenance_warns_about_the_index(microlite_sport: str) -> None:
    """Whoever reads this proposal in six months should be told why the number on the
    index page is different."""
    snippet = _built(microlite_sport, "Sport").provenance["rrp_pounds"].snippet

    assert "/models/" in snippet
    assert "stale" in snippet
