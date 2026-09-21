"""Adria caravan parsing, against real PDFs and Livewire bodies captured in `fixtures/`.

Pure parsing only — no network. Every trap in the module docstring has a test, and so
does each of the two the first live run exposed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters import adria, adria_caravan
from src.adapters.adria import parse_livewire_products
from src.adapters.adria_caravan import (
    EXPECTED_LAYOUTS,
    RANGES,
    RENAMED_MODELS,
    AdriaCaravan,
    _reconciles,
    body_type_for,
    model_name,
    parse_caravan_pdf,
    range_config,
)
from src.product_model.enums import CaravanBodyType
from src.vehicle_class import VehicleClass

FIXTURES = Path(__file__).parent / "fixtures"


def _pdf(name: str) -> str:
    return (FIXTURES / f"adria_caravan_{name}_pdf.txt").read_text(encoding="utf-8")


def _livewire(name: str):
    body = (FIXTURES / f"adria_caravan_livewire_{name}.json").read_bytes()
    return parse_livewire_products(body)


@pytest.fixture
def rio_grande() -> str:
    return _pdf("alpina_rio_grande")


@pytest.fixture
def colorado() -> str:
    return _pdf("alpina_colorado")


@pytest.fixture
def tyne() -> str:
    return _pdf("altea_tyne")


@pytest.fixture
def action() -> str:
    return _pdf("action_tba")


# --- identity -----------------------------------------------------------------------


def test_it_registers_as_the_caravan_adapter() -> None:
    """Without `VEHICLE_CLASS` this module would replace `adria.py` in the registry."""
    assert adria_caravan.VEHICLE_CLASS is VehicleClass.CARAVAN
    assert adria_caravan.MANUFACTURER == "Adria Mobil"
    assert adria_caravan.MANUFACTURER == adria.MANUFACTURER


def test_the_four_caravan_ranges() -> None:
    assert [config.fmlv_range for config in RANGES] == [
        "Alpina",
        "Adora",
        "Altea",
        "Action",
    ]
    assert EXPECTED_LAYOUTS == 10


def test_no_caravan_range_takes_its_model_from_the_trim() -> None:
    """The opposite of the motorhome ranges, and for a reason — see the trim test."""
    assert all(config.model_includes_trim is False for config in RANGES)


def test_an_unknown_range_selector_still_works() -> None:
    config = range_config("caravans/newthing", "NewThing")

    assert config.fmlv_range == "NewThing"
    assert config.model_includes_trim is False


# --- the mass that matters ----------------------------------------------------------


def test_the_minimum_permissible_mass_is_recorded_not_the_maximum(tyne: str) -> None:
    """The single most important field mapping. The Altea Tyne states a maximum of 1800
    and a minimum of 1650, and FMLV holds 1650 — the base vehicle. Reading the maximum
    would record an uprated chassis on five of the eight readable layouts."""
    figures = parse_caravan_pdf(tyne)

    assert figures.maximum_laden_kilograms == 1800
    assert figures.get("mtplm_kilograms") == 1650


def test_the_two_masses_agree_where_there_is_no_uprating(rio_grande: str) -> None:
    figures = parse_caravan_pdf(rio_grande)

    assert figures.maximum_laden_kilograms == 2000
    assert figures.get("mtplm_kilograms") == 2000
    assert figures.get("mro_kilograms") == 1785


def test_the_payload_is_derived_not_read(rio_grande: str) -> None:
    """Adria's own `Max loading weight` deducts a 48kg option pack: 161 where FMLV holds
    215. The same trap as Knaus, Weinsberg, T@B and Frankia."""
    figures = parse_caravan_pdf(rio_grande)
    live = next(p for p in _livewire("alpina") if p.layout_label == "623 HT RIO GRANDE")
    product = AdriaCaravan(config=RANGES[0], product=live, figures=figures, pdf_url="x")

    assert figures.published_max_loading == 161
    assert product.derived_payload_kilograms == 215


# --- length -------------------------------------------------------------------------


def test_length_is_the_total_including_the_tow_bar(rio_grande: str) -> None:
    """The motorhome adapter's own reader takes the body length, which for a caravan is
    1.3m short and looks entirely plausible in a review queue."""
    figures = parse_caravan_pdf(rio_grande)

    assert figures.get("shipping_length_mm") == 8190
    assert figures.get("exterior_body_length_mm") == 6890
    assert figures.get("internal_length_mm") == 6193


def test_the_motorhome_reader_would_take_the_wrong_one(rio_grande: str) -> None:
    """Stated as a test because it is the reason this module has its own patterns."""
    assert adria.parse_technical_data_pdf(rio_grande)["mh_length_mm"].value == 6890


def test_the_awning_is_the_body_figure_not_the_chassis(rio_grande: str) -> None:
    """`Awning perimeter dimensions (body/chassis, cm) 1083/638` — the first, in cm."""
    assert parse_caravan_pdf(rio_grande).awning_length_mm == 10830


# --- everything else the PDF gives --------------------------------------------------


def test_the_remaining_dimensions(rio_grande: str) -> None:
    figures = parse_caravan_pdf(rio_grande)

    assert figures.get("overall_width_mm") == 2460
    assert figures.get("height_mm") == 2600
    assert figures.get("headroom_mm") == 1950
    assert figures.axles == 1


def test_a_single_axle_is_not_a_twin_axle(rio_grande: str) -> None:
    assert parse_caravan_pdf(rio_grande).axles == 1


# --- the two cases the first live run exposed ---------------------------------------


def test_a_missing_minimum_mass_does_not_drop_the_caravan(colorado: str) -> None:
    """The Alpina Colorado publishes a maximum and no minimum, alone among the ten.
    Dropping it reported a live FMLV row as disappeared when it is plainly on the site,
    so it is collected with no mass and no payload instead."""
    figures = parse_caravan_pdf(colorado)
    live = next(p for p in _livewire("alpina") if p.layout_label == "623 UL COLORADO")
    product = AdriaCaravan(
        config=RANGES[0], product=live, figures=figures, pdf_url="x"
    )

    assert figures.maximum_laden_kilograms == 2500
    assert figures.get("mtplm_kilograms") is None
    assert product.derived_payload_kilograms is None

    ok, reason = _reconciles(product, colorado)
    assert ok is True
    assert "NO PERMISSIBLE MASS PROPOSED" in reason


def test_an_unspecified_layout_is_dropped(action: str) -> None:
    """Both Action configurations are announced but have no figures at all: their
    `Dimensions and weights` section holds only an option-pack weight."""
    figures = parse_caravan_pdf(action)

    assert figures.technical_data_is_tba is True
    assert figures.get("shipping_length_mm") is None

    product = AdriaCaravan(
        config=RANGES[3], product=_livewire("action")[0], figures=figures, pdf_url="x"
    )
    ok, reason = _reconciles(product, action)
    assert ok is False
    assert "TBA" in reason


# --- naming -------------------------------------------------------------------------


def test_the_model_comes_from_the_layout_not_the_trim() -> None:
    """Altea's `622 DK AVON` carries its sibling's trim, `Altea 622 DP Dart`. Taking the
    trim would file two different caravans under one name."""
    altea = {p.layout_label: p.trim_label for p in _livewire("altea")}

    assert altea["622 DK AVON"] == "Altea 622 DP Dart"
    assert altea["622 DP DART"] == "Altea 622 DP Dart"

    avon = next(p for p in _livewire("altea") if p.layout_label == "622 DK AVON")
    assert model_name(avon) == "622 DK AVON"


def test_the_market_suffix_is_stripped() -> None:
    """`391 LH GB` — FMLV's own Action rows carry no market code."""
    action = _livewire("action")[0]

    assert action.layout_label == "391 LH GB"
    assert model_name(action) == "391 LH"


def test_the_colorado_rename_targets_a_real_fmlv_identity() -> None:
    """Evidenced on the mass: both hold a running order of 1837kg and a length of
    8260mm. The name alone would not have been enough."""
    assert RENAMED_MODELS[("Alpina", "623 UL COLORADO")] == ("Alpina", "623 UC COLORADO")


def test_every_rename_is_for_a_layout_this_adapter_emits() -> None:
    emitted = {config.fmlv_range for config in RANGES}

    assert all(rng in emitted for rng, _model in RENAMED_MODELS)


# --- body type ----------------------------------------------------------------------


def test_adria_caravans_are_rigid() -> None:
    """Applied as the two-part rule rather than asserted, because `wingamm_caravan.py`
    found the brand that breaks the usual answer by asserting it."""
    body_type, reason = body_type_for("", 1650)

    assert body_type is CaravanBodyType.RIGID
    assert "micro" in reason


def test_weight_alone_does_not_make_a_micro() -> None:
    """The Action 361 LT was 1150kg — light enough, but Adria never call it a micro."""
    body_type, reason = body_type_for("A lovely caravan", 1150)

    assert body_type is CaravanBodyType.RIGID
    assert "never call it one" in reason


def test_both_halves_together_do() -> None:
    body_type, _reason = body_type_for("the Adria micro-caravan", 1150)

    assert body_type is CaravanBodyType.MICRO


def test_naming_without_the_weight_does_not() -> None:
    body_type, reason = body_type_for("the Adria micro-caravan", 1650)

    assert body_type is CaravanBodyType.RIGID
    assert "over the" in reason


# --- the self-check -----------------------------------------------------------------


def test_a_pdf_for_another_caravan_is_rejected(rio_grande: str, tyne: str) -> None:
    """This adapter *constructs* its PDF URL from an id, so the failure to defend against
    is a whole spec sheet belonging to the wrong caravan."""
    tyne_product = next(p for p in _livewire("altea") if p.layout_label == "612 DL TYNE")
    product = AdriaCaravan(
        config=RANGES[2],
        product=tyne_product,
        figures=parse_caravan_pdf(rio_grande),
        pdf_url="x",
    )

    ok, reason = _reconciles(product, rio_grande)
    assert ok is False
    assert "does not name" in reason

    product.figures = parse_caravan_pdf(tyne)
    assert _reconciles(product, tyne)[0] is True
