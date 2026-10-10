"""Elddis on the EHG configurator API, captured 10 October 2026.

The adapter was rebuilt that day because Elddis replaced their website and their range at
once: `sitemap.xml` went, every page moved under `/en/`, and not one model name carried
over. These fixtures are the brand's own API responses, which is the source the rebuild
reads.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.adapters import ehg_configurator as ehg
from src.adapters.elddis import (
    BRAND_KEY,
    DEFAULT_RANGES,
    EXPECTED_LAYOUTS,
    HIGH_TOP_ABOVE_MM,
    MANUFACTURER,
    MANUFACTURER_DISPLAY_NAME,
    ElddisLayout,
    _reconciles,
    body_type_for,
    build_extracted,
    model_name,
    parse_layouts,
)
from src.product_model.enums import BodyType

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def autoquest_gt() -> list[ElddisLayout]:
    return parse_layouts(_fixture("elddis_autoquest_gt_models.json"), "Autoquest GT")


@pytest.fixture(scope="module")
def autoquest_gtv() -> list[ElddisLayout]:
    return parse_layouts(_fixture("elddis_autoquest_gtv_models.json"), "Autoquest GTV")


# --- identity ---------------------------------------------------------------------------


def test_the_manufacturer_is_the_name_fmlv_holds() -> None:
    """`Elddis (EHG UK)` is the join key back to 29 existing product ids."""
    assert MANUFACTURER == "Elddis (EHG UK)"
    assert MANUFACTURER_DISPLAY_NAME == "Elddis"
    assert BRAND_KEY == "elddis"


def test_the_series_name_is_stripped_from_the_model() -> None:
    assert model_name("Elddis Autoquest GT 70 DS", "Autoquest GT") == "70 DS"
    assert model_name("Whirlwind GTV 554", "Whirlwind GTV") == "554"


def test_a_series_that_prefixes_another_does_not_steal_its_layouts() -> None:
    """`Autoquest GT` is a prefix of `Autoquest GTS`.

    Stripping against a list of names rather than this layout's own series would file
    every GTS layout under GT, leaving `S 66 DS` as the model.
    """
    assert model_name("Elddis Autoquest GTS 66 DS", "Autoquest GTS") == "66 DS"
    assert model_name("Elddis Autoquest GTS 66 DS", "Autoquest GT") == "S 66 DS"


def test_a_name_that_is_only_the_series_yields_nothing() -> None:
    assert model_name("Elddis Autoquest GT", "Autoquest GT") is None


# --- the layouts -------------------------------------------------------------------------


def test_every_layout_in_a_series_is_read(autoquest_gt: list[ElddisLayout]) -> None:
    assert [layout.model for layout in autoquest_gt] == ["70 DS", "74 DS", "74 DI"]


def test_the_figures_match_the_published_page(autoquest_gt: list[ElddisLayout]) -> None:
    """Autoquest GT 74 DS, checked by hand against elddis.co.uk on 10 October 2026."""
    layout = next(x for x in autoquest_gt if x.model == "74 DS")
    assert layout.rrp_pounds == 75027
    assert layout.mtplm_kilograms == 3499
    assert layout.mro_kilograms == 3020
    assert layout.payload_kilograms == 479
    assert layout.berths == 5
    assert layout.seats == 4
    assert layout.base_vehicle_manufacturer == "Fiat"


def test_dimensions_are_centimetres_and_are_converted(autoquest_gt: list[ElddisLayout]) -> None:
    """`741` is 7410mm. Taken as millimetres it would be a 74cm motorhome."""
    layout = next(x for x in autoquest_gt if x.model == "74 DS")
    assert layout.mh_length_mm == 7410
    assert layout.mh_width_mm == 2350
    assert layout.mh_height_mm == 2940


def test_the_width_is_the_body_not_the_mirrors(autoquest_gt: list[ElddisLayout]) -> None:
    """`widthOverall` is empty on every layout; `widthOverallwithoutMirrors` is the figure."""
    entries = json.loads(_fixture("elddis_autoquest_gt_models.json"))
    technical = entries[0]["technicalData"]
    assert ehg.technical_value(technical, "widthOverall") is None
    assert ehg.technical_value(technical, "widthOverallwithoutMirrors") == "235"
    assert autoquest_gt[0].mh_width_mm == 2350


def test_the_standard_seat_count_is_recorded(autoquest_gt: list[ElddisLayout]) -> None:
    """`maxPersons` 4 with `extraMaxPersons` 5 — the fifth seat is an option."""
    layout = autoquest_gt[0]
    assert layout.seats == 4
    assert layout.optional_seats == 5


def test_an_absent_count_reads_as_nothing(autoquest_gtv: list[ElddisLayout]) -> None:
    """The API writes an absent optional count as the string `None`, not as null."""
    assert all(x.optional_seats is None for x in autoquest_gtv)


# --- body type ---------------------------------------------------------------------------


def test_partially_integrated_is_a_low_profile_coachbuilt() -> None:
    """The German term for what FMLV holds on every Elddis motorhome."""
    body_type, reason = body_type_for("partially-integrated", 2940)
    assert body_type is BodyType.COACH_BUILT_LOW_PROFILE
    assert "partially-integrated" in reason


def test_a_tall_campervan_is_a_high_top() -> None:
    body_type, _ = body_type_for("campervan", 2580)
    assert body_type is BodyType.CAMPERVAN_HIGH_TOP


def test_an_optional_pop_top_does_not_change_the_body_type(
    autoquest_gtv: list[ElddisLayout],
) -> None:
    """Elddis mark theirs `(○) Optional` and print `258 / 280 (○)` for the height.

    The base-vehicle rule records the vehicle as standard, so the roof is ignored and the
    height recorded is the closed one.
    """
    for layout in autoquest_gtv:
        assert layout.mh_height_mm == 2580
        assert layout.body_type is BodyType.CAMPERVAN_HIGH_TOP


def test_a_short_campervan_is_not_a_high_top() -> None:
    body_type, _ = body_type_for("campervan", HIGH_TOP_ABOVE_MM)
    assert body_type is BodyType.CAMPERVAN


def test_an_unknown_body_type_is_left_blank_rather_than_guessed() -> None:
    body_type, reason = body_type_for("integrated", 2940)
    assert body_type is None
    assert "not a value this adapter has been taught" in reason


# --- the self-check -----------------------------------------------------------------------


def test_the_two_masses_reconcile_on_every_layout(
    autoquest_gt: list[ElddisLayout], autoquest_gtv: list[ElddisLayout]
) -> None:
    for layout in [*autoquest_gt, *autoquest_gtv]:
        ok, basis = _reconciles(layout)
        assert ok is True, f"{layout.label}: {basis}"


def test_a_running_order_above_the_maximum_is_refused() -> None:
    """Which is what reading a mass out of the wrong field looks like."""
    ok, basis = _reconciles(
        ElddisLayout("Autoquest GT", "70 DS", mtplm_kilograms=3499, mro_kilograms=3600)
    )
    assert ok is False
    assert "zero or negative" in basis


def test_an_implausible_payload_is_refused() -> None:
    ok, _ = _reconciles(
        ElddisLayout("Autoquest GT", "70 DS", mtplm_kilograms=3499, mro_kilograms=500)
    )
    assert ok is False


def test_a_missing_mass_is_refused_rather_than_assumed() -> None:
    """Elddis publish no payload row, so two masses are the whole of the evidence."""
    ok, _ = _reconciles(ElddisLayout("Autoquest GT", "70 DS", mtplm_kilograms=3499))
    assert ok is False


# --- the roster ---------------------------------------------------------------------------


def test_the_series_index_is_filtered_to_one_model_year() -> None:
    """A brand's list is cumulative, and taking it whole collects last season's roster."""
    payload = _fixture("elddis_series.json")
    assert ehg.latest_model_year(payload) == 2027
    series = ehg.parse_series_index(payload, model_year=2027)
    assert sorted(s.name for s in series) == [
        "Autoquest GT",
        "Autoquest GTS",
        "Autoquest GTV",
        "Whirlwind GT",
        "Whirlwind GTS",
        "Whirlwind GTV",
    ]


def test_the_adapters_range_list_matches_the_catalogue() -> None:
    """Six ranges, eighteen layouts — and the list is reconciled against the API each run."""
    series = ehg.parse_series_index(_fixture("elddis_series.json"), model_year=2027)
    assert {s.name for s in series} == {label for _key, label in DEFAULT_RANGES}
    assert EXPECTED_LAYOUTS == 18


def test_a_trailing_space_in_a_series_name_is_cleaned() -> None:
    """The API sends `Autoquest GT ` and `Whirlwind GT `, which would not match otherwise."""
    raw = json.loads(_fixture("elddis_series.json"))
    assert any(entry["name"] != entry["name"].strip() for entry in raw)
    series = ehg.parse_series_index(_fixture("elddis_series.json"), model_year=2027)
    assert all(s.name == s.name.strip() for s in series)


# --- the built product ---------------------------------------------------------------------


def test_a_product_carries_provenance_for_everything_it_proposes(
    autoquest_gt: list[ElddisLayout],
) -> None:
    built = build_extracted(autoquest_gt[0], basis="the two masses", source_url="http://x")
    assert built.motorhome.manufacturer == "Elddis (EHG UK)"
    assert built.motorhome.manufacturer_range == "Autoquest GT"
    assert built.motorhome.model == "70 DS"
    for field in (
        "rrp_pounds",
        "berths",
        "mh_passenger_seats_inc_driver",
        "mtplm_kilograms",
        "mro_kilograms",
        "mh_payload_kilograms",
        "mh_length_mm",
        "mh_width_mm",
        "mh_height_mm",
        "body_type",
    ):
        assert field in built.provenance, field


def test_the_price_provenance_states_the_german_footnote(
    autoquest_gt: list[ElddisLayout],
) -> None:
    """A reviewer should see what Elddis say about their own figure."""
    built = build_extracted(autoquest_gt[0], basis="the two masses", source_url="http://x")
    assert "German retail prices" in built.provenance["rrp_pounds"].snippet


def test_the_optional_fifth_seat_is_explained(autoquest_gt: list[ElddisLayout]) -> None:
    built = build_extracted(autoquest_gt[0], basis="the two masses", source_url="http://x")
    snippet = built.provenance["mh_passenger_seats_inc_driver"].snippet
    assert "4 seats" in snippet
    assert "5 available as an option" in snippet
