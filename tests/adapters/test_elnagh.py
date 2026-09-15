"""Tests for the Elnagh adapter's pure parsing functions, against the real page.

The fixture is the real importer range page fetched 14 September 2026 with `<script>` and
`<style>` removed — see `docs/adapters/elnagh.md`. One page, because Marquis sell one Elnagh
range and it carries all four layouts.

**Every figure this page publishes already agrees with FMLV**, which is why the numbers
below are asserted as literals: they are an independent check on the parse rather than a
record of whatever it happened to produce.

No network here.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.adapters import adapter_for, elnagh, marquis
from src.adapters.elnagh import (
    BASE_VEHICLE,
    BODY_TYPE,
    EXPECTED_LAYOUTS,
    RANGE_PREFIXES,
    ElnaghProduct,
    _build_extracted_motorhome,
    _discrepancies,
    _reconciles,
    find_range_urls,
    layout_blocks,
    plain_text,
)
from src.product_model.enums import BedType, BodyType

FIXTURES = Path(__file__).parent / "fixtures"

PAGE = "elnagh_baron.html"
PAGE_URL = "https://www.marquisleisure.co.uk/elnagh-baron-2026-motorhome-range"

ALL_KEYS = tuple(key for key, _label in elnagh.DEFAULT_RANGES)


def _page() -> str:
    return (FIXTURES / PAGE).read_text(encoding="utf-8")


def _layouts() -> list[ElnaghProduct]:
    return layout_blocks(_page(), PAGE_URL)


def _by_model() -> dict[str, ElnaghProduct]:
    return {p.model: p for p in _layouts()}


# --------------------------------------------------------------------------- #
# The roster
# --------------------------------------------------------------------------- #


def _index(*slugs: str) -> str:
    return "".join(f'<a href="/{s}">x</a>' for s in slugs)


def test_only_range_pages_are_taken() -> None:
    """The requester's standing warning about this site is to avoid the used-stock pages."""
    html_ = _index(
        "elnagh-baron-2026-motorhome-range",
        "used-elnagh-baron-for-sale",
        "new-motorhomes/elnagh",
    )

    assert find_range_urls(html_, ALL_KEYS) == [PAGE_URL]


def test_the_one_page_carries_four_layouts() -> None:
    """Marquis sell one Elnagh range; elnagh.com sells many more, and is not the roster."""
    assert len(_layouts()) == EXPECTED_LAYOUTS == 4


def test_the_models_are_the_four_baron_codes() -> None:
    assert {p.model for p in _layouts()} == {"530", "560", "573", "579"}
    assert {p.manufacturer_range for p in _layouts()} == {"Baron"}


def test_the_page_banner_is_not_read_as_the_model() -> None:
    """The first block has `2026 2026 ELNAGH BARON COACHBUILT MOTORHOME RANGE` in front."""
    assert marquis.range_and_model(
        "2026 2026 ELNAGH BARON COACHBUILT MOTORHOME RANGE Baron 530", RANGE_PREFIXES
    ) == ("Baron", "530")


# --------------------------------------------------------------------------- #
# The figures, every one of which FMLV already agrees with
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("model", "length", "payload", "mro", "price"),
    [
        ("530", 6590, 590, 2910, 67_995),
        ("560", 6990, 590, 2910, 67_995),
        ("573", 7410, 550, 2950, 69_995),
        ("579", 7410, 560, 2940, 69_995),
    ],
)
def test_each_layout_matches_what_fmlv_holds(
    model: str, length: int, payload: int, mro: int, price: int
) -> None:
    product = _by_model()[model]

    assert product.mh_length_mm == length
    assert product.mh_payload_kilograms == payload
    assert product.mro_kilograms == mro
    assert product.rrp_pounds == price


def test_every_layout_shares_its_width_height_and_masses() -> None:
    for product in _layouts():
        assert product.mh_width_mm == 2350
        assert product.mh_height_mm == 2950
        assert product.mtplm_kilograms == 3500
        assert product.berths == 4
        assert product.mh_passenger_seats_inc_driver == 4


def test_the_lighter_chassis_is_taken_not_the_heavier() -> None:
    """`MTPLM 3500kg / 3650kg` — the 3500 is what the quoted OTR price buys."""
    assert "MTPLM 3500kg / 3650kg" in plain_text(_page())
    assert _by_model()["530"].mtplm_kilograms == 3500


def test_the_manual_payload_is_taken_not_the_automatic() -> None:
    """`(3500KG CHASSIS) Manual 590kg / Auto 550kg` — the price line names a manual."""
    assert "Manual 590kg / Auto 550kg" in plain_text(_page())
    assert _by_model()["530"].mh_payload_kilograms == 590


def test_the_mass_in_running_order_is_derived_and_says_so() -> None:
    """The older Marquis template prints no MIRO figure."""
    product = _by_model()["530"]

    snippet = _build_extracted_motorhome(product).provenance["mro_kilograms"].snippet
    assert "prints no MIRO" in snippet
    assert "both imply 2910kg" in snippet


def test_the_glossarys_definition_of_miro_is_not_read_as_a_figure() -> None:
    """The page explains the term in prose at its foot — `MASS IN RUNNING ORDER (MIRO) -`.

    That matters because the **last** block's body runs to the end of the page, so the
    glossary is inside it. Only `MIRO <n>kg` is a figure.
    """
    text = plain_text(_page())

    assert "MASS IN RUNNING ORDER (MIRO)" in text.upper()
    for product in _layouts():
        assert product.mro_kilograms == product.mtplm_kilograms - (
            product.mh_payload_kilograms or 0
        )


def test_no_payload_means_no_derived_mass() -> None:
    assert replace(_by_model()["530"], mh_payload_kilograms=None).mro_kilograms is None


# --------------------------------------------------------------------------- #
# The check: two chassis rows, one mass in running order
# --------------------------------------------------------------------------- #


def test_every_layout_agrees_with_itself_across_both_chassis() -> None:
    """3500-590 and 3650-740 both give 2910. Unlike Benimar's Primero 282, all four hold."""
    for product in _layouts():
        assert len(set(product.chassis_mro_routes)) == 1
        assert _discrepancies(product) == []


def test_a_chassis_disagreement_is_narrated_not_fatal() -> None:
    """The wrong figure would be in the heavier chassis row, which is never recorded."""
    product = replace(_by_model()["530"], chassis_mro_routes=(2910, 2960))

    assert _reconciles(product)[0] is True
    assert any("chassis options imply" in note for note in _discrepancies(product))


@pytest.mark.parametrize("model", ["530", "560", "573", "579"])
def test_every_real_layout_reconciles(model: str) -> None:
    reconciles, why_not = _reconciles(_by_model()[model])

    assert reconciles is True, why_not


def test_a_block_with_a_heading_and_no_figures_is_dropped() -> None:
    """That means the page's shape changed under the parse, not that a vehicle is empty."""
    reconciles, why_not = _reconciles(
        ElnaghProduct(source_url="x", manufacturer_range="Baron", model="530")
    )

    assert reconciles is False
    assert "shape has probably changed" in why_not


# --------------------------------------------------------------------------- #
# The equipment list, which qualifies itself per layout
# --------------------------------------------------------------------------- #


def test_the_washroom_differs_by_layout_and_the_page_says_so() -> None:
    """The one field where reading the list range-wide would be wrong rather than vague.

    FMLV holds `separate_shower_toilet` as No, No, Yes, Yes across 530/560/573/579, which
    is exactly what these two lines say.
    """
    text = plain_text(_page())

    assert "Separate shower and toilet compartment (579 and 573 only)" in text
    assert "Combined shower and toilet compartment (530 and 560 only)" in text


def test_only_the_two_long_layouts_have_a_separate_washroom() -> None:
    separated = {
        model: _build_extracted_motorhome(product).motorhome.shower_toilet_separated
        for model, product in _by_model().items()
    }

    assert separated["573"] is True
    assert separated["579"] is True
    # Silence is not a negative: "Combined" is not read as a denial, so these stay open
    # for a reviewer rather than being asserted as False.
    assert separated["530"] is None
    assert separated["560"] is None


# --------------------------------------------------------------------------- #
# Habitation, which is findings rather than proposals
# --------------------------------------------------------------------------- #


def test_every_layout_has_a_drop_down_bed() -> None:
    """FMLV holds `drop_down_bed` for all four, and each block's bed list names one.

    Elnagh write the size as `DROP DOWN BED 1900 x 810mm`, suffixing only the last figure,
    where Benimar write `1400mm × 1900mm`. Requiring a suffix on the first found none.
    """
    for product in _layouts():
        motorhome = _build_extracted_motorhome(product).motorhome
        assert BedType.DROP_DOWN in motorhome.bed_types


def test_the_heating_and_fridge_come_from_the_range_list() -> None:
    motorhome = _build_extracted_motorhome(_by_model()["530"]).motorhome

    assert motorhome.heating is not None
    assert motorhome.refrigeration is not None


def test_the_microwave_is_not_asserted_where_the_copy_is_silent() -> None:
    """Silence is not a negative, and FMLV holds `microwave = No` for all four anyway."""
    assert _build_extracted_motorhome(_by_model()["530"]).motorhome.microwave is None


def test_a_habitation_finding_quotes_the_page() -> None:
    snippet = (
        _build_extracted_motorhome(_by_model()["573"])
        .provenance["shower_toilet_separated"]
        .snippet
    )

    assert "Separate shower and toilet compartment" in snippet


# --------------------------------------------------------------------------- #
# What else reaches the reviewer
# --------------------------------------------------------------------------- #


def test_every_layout_is_a_low_profile_coachbuilt() -> None:
    """Marquis head the page `COACHBUILT`, each bed list names a drop-down rather than an
    over-cab bed, and FMLV holds `type_coach_built_low_profile` for all four."""
    assert BODY_TYPE is BodyType.COACH_BUILT_LOW_PROFILE
    extracted = _build_extracted_motorhome(_by_model()["530"])
    assert extracted.motorhome.body_type is BodyType.COACH_BUILT_LOW_PROFILE


def test_every_layout_is_a_fiat() -> None:
    extracted = _build_extracted_motorhome(_by_model()["530"])

    assert extracted.motorhome.base_vehicle_manufacturer == BASE_VEHICLE == "Fiat"


def test_the_width_is_recorded_because_a_coachbuilt_body_overhangs_its_mirrors() -> None:
    """Unlike Benimar's Benivan, where the same label means the mirrors."""
    snippet = _build_extracted_motorhome(_by_model()["530"]).provenance["mh_width_mm"].snippet

    assert "MIRRORS FOLDED" in snippet
    assert "measures the body" in snippet


def test_the_seat_provenance_explains_the_pages_own_word() -> None:
    snippet = (
        _build_extracted_motorhome(_by_model()["530"])
        .provenance["mh_passenger_seats_inc_driver"]
        .snippet
    )

    assert "BELTS" in snippet
    assert "belted travel seat" in snippet


def test_the_price_names_marquis_as_the_importer_that_sets_it() -> None:
    snippet = _build_extracted_motorhome(_by_model()["530"]).provenance["rrp_pounds"].snippet

    assert "sole UK importer" in snippet


# --------------------------------------------------------------------------- #
# Wiring
# --------------------------------------------------------------------------- #


def test_the_adapter_is_registered_under_its_fmlv_name() -> None:
    assert adapter_for("Elnagh") is elnagh
