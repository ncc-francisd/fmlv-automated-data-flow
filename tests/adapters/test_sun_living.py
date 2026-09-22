"""SUN LIVING parsing, against real Livewire bodies and PDFs captured in `fixtures/`.

Pure parsing only — no network. Most of the machinery is Adria's and tested there; what
is tested here is the two things that differ, the PDF host and the model naming, plus
that Adria's readers really do read a Sun Living document.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.adapters import sun_living
from src.adapters.adria import (
    parse_base_vehicle_manufacturer,
    parse_livewire_products,
    parse_technical_data_pdf,
    pdf_describes_layout,
    pdf_title,
    technical_data_pdf_url,
)
from src.adapters.sun_living import (
    EXPECTED_LAYOUTS,
    RANGES,
    SunLivingMotorhome,
    _reconciles,
    model_name,
    range_config,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _livewire(name: str):
    return parse_livewire_products(
        (FIXTURES / f"sun_living_livewire_{name}.json").read_bytes()
    )


def _pdf(name: str) -> str:
    return (FIXTURES / f"sun_living_{name}_pdf.txt").read_text(encoding="utf-8")


@pytest.fixture
def v_series():
    return _livewire("v_series")


@pytest.fixture
def s_series():
    return _livewire("s_series")


@pytest.fixture
def s72dc() -> str:
    return _pdf("s72dc")


@pytest.fixture
def c70dl() -> str:
    return _pdf("c70dl")


# --- identity and roster ------------------------------------------------------------


def test_the_manufacturer_is_capitals_in_both() -> None:
    assert sun_living.MANUFACTURER == "SUN LIVING"
    assert sun_living.MANUFACTURER_DISPLAY_NAME == "SUN LIVING"


def test_four_ranges_ten_configurations() -> None:
    assert [c.fmlv_range for c in RANGES] == [
        "A Series",
        "C Series",
        "S Series",
        "V Series",
    ]
    assert EXPECTED_LAYOUTS == 10


def test_an_unknown_range_selector_still_works() -> None:
    assert range_config("motorhomes/x-series", "X Series").fmlv_range == "X Series"


# --- the PDF host, which is the one change Adria needed -----------------------------


def test_the_pdf_host_comes_from_the_configurator_url(v_series) -> None:
    """The helper used to hardcode `configure.adria-mobil.com`, so every Sun Living PDF
    returned 404 — and the C 70DL, which also has no price, looked convincingly like a
    model with no technical data published at all."""
    url = technical_data_pdf_url(v_series[0])

    assert url is not None
    assert url.startswith("https://configure.sun-living.com/")
    assert "adria-mobil" not in url


def test_the_market_and_period_still_come_from_it_too(v_series) -> None:
    url = technical_data_pdf_url(v_series[0])

    assert "/gb/25-26/" in url
    assert url.endswith(f"/{v_series[0].product_id}/pdf")


# --- the model name -----------------------------------------------------------------


def test_the_v55sp_is_two_configurations(v_series) -> None:
    """One layout, two trims — and the second is an elevating tent roof that adds two
    berths and GBP4,000. Dropping the trim files two campervans under one name."""
    v55 = [p for p in v_series if p.layout_label == "V 55SP"]

    assert len(v55) == 2
    assert sorted(p.trim_label for p in v55) == ["StdF RHD", "StdF RHD TentTop"]
    assert sorted(p.berths for p in v55) == [2, 4]


def test_the_trim_is_kept_only_when_it_says_something(v_series) -> None:
    """`StdF RHD` is market boilerplate; `TentTop` is the vehicle."""
    by_trim = {p.trim_label: model_name(p) for p in v_series if p.layout_label == "V 55SP"}

    assert by_trim["StdF RHD"] == "V 55SP"
    assert by_trim["StdF RHD TentTop"] == "V 55SP TentTop"


def test_the_motorhome_trims_add_nothing(s_series) -> None:
    """`SL_Ford_RHD` is entirely boilerplate, so the model is the layout alone."""
    assert {model_name(p) for p in s_series} == {"S 72DC", "S 72DL", "S 75SL"}


def test_an_unknown_trim_word_would_carry_across() -> None:
    """The boilerplate is subtracted rather than the interesting words listed, so a
    future `Sport` or `Elevating Roof` needs no code change."""
    product = replace(
        _livewire("v_series")[0], layout_label="V 60SP", trim_label="StdF RHD Sport"
    )

    assert model_name(product) == "V 60SP Sport"


def test_a_configuration_with_no_layout_label_has_no_model() -> None:
    product = replace(_livewire("v_series")[0], layout_label=None)

    assert model_name(product) is None


# --- Adria's readers on a Sun Living document ---------------------------------------


def test_adrias_spec_reader_reads_a_sun_living_pdf(s72dc: str) -> None:
    """All seven fields, and every one matches what FMLV holds for the S 72DC."""
    specs = parse_technical_data_pdf(s72dc)

    assert {name: match.value for name, match in specs.items()} == {
        "mh_length_mm": 7295,
        "mh_width_mm": 2295,
        "mh_height_mm": 2870,
        "mro_kilograms": 3002,
        "mtplm_kilograms": 3500,
        "berths": 4,
        "mh_passenger_seats_inc_driver": 4,
    }


def test_the_mass_is_the_without_pack_figure(s72dc: str) -> None:
    """The requester's ruling: the all-inclusive pack is the customer's conversation and
    FMLV holds the base level. The snippet carries the qualifier to the reviewer."""
    snippet = parse_technical_data_pdf(s72dc)["mro_kilograms"].snippet

    assert "WITHOUT ALL INC' PACK" in snippet


def test_the_document_names_its_own_vehicle(s72dc: str, c70dl: str) -> None:
    """The identity self-check, which matters because the URL is *constructed* from an
    id: the risk is a whole spec sheet belonging to the wrong vehicle."""
    assert pdf_title(s72dc) == "SUN LIVING S 72DC"
    assert pdf_describes_layout(s72dc, "S 72DC") is True
    assert pdf_describes_layout(s72dc, "C 70DL") is False
    assert pdf_title(c70dl) == "SUN LIVING C 70DL"


def test_the_base_vehicle_is_read(s72dc: str) -> None:
    assert parse_base_vehicle_manufacturer(s72dc) == "Ford"


def test_the_c70dl_has_a_full_pdf(c70dl: str) -> None:
    """It publishes GBP0.00, which made it look like a model still in transition with no
    technical data. It has all of it."""
    specs = parse_technical_data_pdf(c70dl)

    assert specs["mh_length_mm"].value == 6970
    assert specs["mro_kilograms"].value == 2763
    assert specs["berths"].value == 2


# --- price and the self-check -------------------------------------------------------


def _product(live, specs) -> SunLivingMotorhome:
    return SunLivingMotorhome(
        config=RANGES[3], product=live, model="x", pdf_url="u", specs=specs
    )


def test_a_zero_price_is_no_price(v_series, s72dc: str) -> None:
    """The C 70DL publishes GBP0.00. Recording a zero would wipe a real figure."""
    live = replace(v_series[0], price_pounds=0)

    assert _product(live, parse_technical_data_pdf(s72dc)).rrp_pounds is None


def test_a_real_price_is_kept(v_series, s72dc: str) -> None:
    live = replace(v_series[0], price_pounds=57_995)

    assert _product(live, parse_technical_data_pdf(s72dc)).rrp_pounds == 57_995


def test_the_payload_is_derived(v_series, s72dc: str) -> None:
    """Max authorised weight minus the mass in running order, the requester's formula."""
    assert _product(v_series[0], parse_technical_data_pdf(s72dc)).derived_payload_kilograms == 498


def test_a_pdf_for_another_vehicle_is_rejected(v_series, c70dl: str) -> None:
    live = next(p for p in v_series if p.layout_label == "V 55SP")
    product = _product(live, parse_technical_data_pdf(c70dl))

    ok, reason = _reconciles(product, c70dl)

    assert ok is False
    assert "does not name" in reason


def test_a_coherent_document_reconciles(s_series, s72dc: str) -> None:
    live = next(p for p in s_series if p.layout_label == "S 72DC")
    product = SunLivingMotorhome(
        config=RANGES[2],
        product=live,
        model="S 72DC",
        pdf_url="u",
        specs=parse_technical_data_pdf(s72dc),
    )

    assert _reconciles(product, s72dc)[0] is True


# --- body type, derived per range ----------------------------------------------------


def test_each_range_has_its_own_body_style() -> None:
    """Derived, not asserted as one constant — the `wingamm_caravan.py` lesson. Every
    range is internally consistent in FMLV across live and archived rows alike."""
    from src.product_model.enums import BodyType

    assert sun_living.body_type_for("A Series", "A 70DK")[0] is (
        BodyType.COACH_BUILT_OVER_CAB_BED
    )
    assert sun_living.body_type_for("C Series", "C 70DL")[0] is (
        BodyType.COACH_BUILT_LOW_PROFILE
    )
    assert sun_living.body_type_for("S Series", "S 72DC")[0] is (
        BodyType.COACH_BUILT_LOW_PROFILE
    )
    assert sun_living.body_type_for("V Series", "V 60SP")[0] is (
        BodyType.CAMPERVAN_HIGH_TOP
    )


def test_the_tenttop_is_the_one_with_the_roof_bed() -> None:
    """Its own name says so and it sleeps four where the base sleeps two. FMLV holds the
    pair the other way round, which is what happens when two rows share a model name and
    an edit lands on whichever the editor opened."""
    from src.product_model.enums import BodyType

    body_type, reason = sun_living.body_type_for("V Series", "V 55SP TentTop")

    assert body_type is BodyType.CAMPERVAN_HIGH_TOP_ELEVATING_ROOF
    assert "other way round" in reason


def test_a_roof_bed_only_applies_to_campervans() -> None:
    """A coach-built keeps its own style whatever its trim says."""
    from src.product_model.enums import BodyType

    assert sun_living.body_type_for("S Series", "S 72DC TentTop")[0] is (
        BodyType.COACH_BUILT_LOW_PROFILE
    )


def test_an_unknown_range_proposes_no_body_type() -> None:
    """Better blank than guessed, across eight mutually exclusive columns."""
    assert sun_living.body_type_for("X Series", "X 10AB")[0] is None
