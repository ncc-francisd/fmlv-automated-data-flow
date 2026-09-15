"""Tests for the McLouis adapter's pure parsing functions, against the real pages.

Fixtures are the four real model pages from `mclouisfusion.co.uk`, fetched 15 September
2026 with `<script>` and `<style>` removed — see `docs/adapters/mclouis.md`. All four,
because **one page is one layout** here, unlike every Marquis brand, and because the four
differ in ways that broke the parse:

* **330** — the only four-belt layout, and the only one excluded by `(exc 330)`.
* **360** — capitalises `Overall Length` where the others do not.
* **373** — the separate washroom, and a bed size written `2 x 800mm x 2000mm`.
* **379** — a bed size with a one-`m` typo, `1500mm x 1900m`.

No network here.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.adapters import adapter_for, mclouis
from src.adapters.mclouis import (
    BASE_URL,
    BASE_VEHICLE,
    BODY_TYPE,
    EXPECTED_LAYOUTS,
    RANGE,
    McLouisProduct,
    _bed_lines,
    _build_extracted_motorhome,
    _reconciles,
    find_model_urls,
    plain_text,
    read_model_page,
)
from src.product_model.enums import BedType, BodyType

FIXTURES = Path(__file__).parent / "fixtures"

MODELS = ("330", "360", "373", "379")


def _page(model: str) -> str:
    return (FIXTURES / f"mclouis_fusion_{model}.html").read_text(encoding="utf-8")


def _product(model: str) -> McLouisProduct:
    return read_model_page(
        _page(model), model, f"{BASE_URL}/explore-the-range/fusion-{model}"
    )


def _all() -> list[McLouisProduct]:
    return [_product(model) for model in MODELS]


# --------------------------------------------------------------------------- #
# The roster
# --------------------------------------------------------------------------- #


def test_the_range_page_yields_four_layouts_in_order() -> None:
    """The slug carries the model code, so the roster needs no parsing of prose."""
    index = "".join(
        f'<a href="/explore-the-range/fusion-{m}">Explore {m}</a>' for m in MODELS
    )

    assert find_model_urls(index, ()) == [
        (m, f"{BASE_URL}/explore-the-range/fusion-{m}") for m in MODELS
    ]
    assert len(MODELS) == EXPECTED_LAYOUTS == 4


def test_a_layout_is_linked_more_than_once_and_counted_once() -> None:
    """Every model page links its three siblings at the foot, and so does the footer."""
    index = '<a href="/explore-the-range/fusion-330">a</a>' * 3

    assert find_model_urls(index, ()) == [
        ("330", f"{BASE_URL}/explore-the-range/fusion-330")
    ]


def test_a_single_model_reads_only_its_own_page() -> None:
    index = "".join(
        f'<a href="/explore-the-range/fusion-{m}">x</a>' for m in MODELS
    )

    assert find_model_urls(index, ("373",)) == [
        ("373", f"{BASE_URL}/explore-the-range/fusion-373")
    ]


def test_nothing_but_a_fusion_model_page_is_taken() -> None:
    index = (
        '<a href="/explore-the-range">x</a>'
        '<a href="/brochures">x</a>'
        '<a href="/explore-the-range/fusion-330">x</a>'
    )

    assert [model for model, _url in find_model_urls(index, ())] == ["330"]


# --------------------------------------------------------------------------- #
# The figures
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("model", "seats", "length", "mtplm", "mro", "payload", "price"),
    [
        ("330", 4, 6590, 3500, 2910, 590, 74_995),
        ("360", 5, 6990, 3500, 2910, 590, 77_495),
        ("373", 5, 7410, 3500, 2950, 550, 79_495),
        ("379", 5, 7410, 3500, 2940, 560, 79_495),
    ],
)
def test_each_layout_yields_every_field(
    model: str, seats: int, length: int, mtplm: int, mro: int, payload: int, price: int
) -> None:
    product = _product(model)

    assert product.manufacturer_range == RANGE == "Fusion"
    assert product.berths == 4
    assert product.mh_passenger_seats_inc_driver == seats
    assert product.mh_length_mm == length
    assert product.mtplm_kilograms == mtplm
    assert product.mro_kilograms == mro
    assert product.mh_payload_kilograms == payload
    assert product.rrp_pounds == price


def test_the_dimensions_are_converted_from_metres() -> None:
    """The site publishes `6.59m`, not `6590mm`, unlike every Marquis brand."""
    assert "Overall length 6.59m" in plain_text(_page("330"))
    assert _product("330").mh_length_mm == 6590


def test_a_capitalised_label_is_still_read() -> None:
    """The 360 page writes `Overall Length` where the other three write `Overall length`."""
    assert "Overall Length 6.99m" in plain_text(_page("360"))
    assert _product("360").mh_length_mm == 6990


def test_every_layout_shares_its_width_and_height() -> None:
    for product in _all():
        assert product.mh_width_mm == 2350
        assert product.mh_height_mm == 2770


def test_the_height_is_the_one_the_brochure_prints_too() -> None:
    """FMLV holds 2950; the site and the 2026 brochure both say 2770.

    The site adds that heights are measured with the aerial in its lowest position.
    """
    snippet = _build_extracted_motorhome(_product("330")).provenance["mh_height_mm"].snippet

    assert "2.77m" in snippet
    assert "brochure prints the same figure" in snippet


def test_the_base_chassis_is_taken_not_the_uprated_ones() -> None:
    """`3500kg | 3650kg | 4400kg` — the first is what the quoted price buys."""
    product = _product("330")

    assert product.mtplm_figures == (3500, 3650, 4400)
    assert product.mro_figures == (2910, 2910, 2970)
    assert product.payload_figures == (590, 740, 1430)
    assert (product.mtplm_kilograms, product.mro_kilograms) == (3500, 2910)


def test_the_site_price_is_taken_over_the_brochures() -> None:
    """The brochure says £76,995 for the 373 where the site says £79,495.

    The settled rule is that the website over-rules a document unless the site can be
    shown wrong, and FMLV's own figures match the site.
    """
    snippet = _build_extracted_motorhome(_product("373")).provenance["rrp_pounds"].snippet

    assert "79,495" in snippet
    assert "brochure's price list disagrees" in snippet


# --------------------------------------------------------------------------- #
# The self-check, which is the strongest of the six Trigano brands
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("model", MODELS)
def test_every_chassis_column_closes(model: str) -> None:
    """`(a-b)` is the page's own label for the payload row, on all three columns."""
    product = _product(model)
    reconciles, why_not = _reconciles(product)

    assert reconciles is True, why_not
    for mtplm, mro, payload in zip(
        product.mtplm_figures, product.mro_figures, product.payload_figures, strict=True
    ):
        assert mtplm - mro == payload


def test_a_column_out_of_step_is_caught() -> None:
    """The fault this exists to catch: one row read against another's chassis."""
    product = replace(_product("330"), mro_figures=(2910, 2970, 2910))

    reconciles, why_not = _reconciles(product)

    assert reconciles is False
    assert "its own (a-b) gives" in why_not


def test_rows_of_different_lengths_cannot_be_paired() -> None:
    """A short row means the columns no longer line up, not that a figure is missing."""
    product = replace(_product("330"), payload_figures=(590, 740))

    reconciles, why_not = _reconciles(product)

    assert reconciles is False
    assert "cannot be paired up" in why_not


def test_a_page_yielding_no_weights_is_dropped() -> None:
    product = McLouisProduct(source_url="x", model="330")

    reconciles, why_not = _reconciles(product)

    assert reconciles is False
    assert "shape has probably changed" in why_not


# --------------------------------------------------------------------------- #
# Habitation, which is findings rather than proposals
# --------------------------------------------------------------------------- #


def test_the_washroom_differs_by_layout_and_the_page_says_so() -> None:
    """The same house style as Elnagh, and the same four-way split."""
    text = plain_text(_page("330"))

    assert "Separate shower and toilet compartment (373 and 379 only)" in text
    assert "Combined shower and toilet compartment (330 and 360 only)" in text


def test_only_the_two_long_layouts_have_a_separate_washroom() -> None:
    separated = {
        p.model: _build_extracted_motorhome(p).motorhome.shower_toilet_separated
        for p in _all()
    }

    assert separated["373"] is True
    assert separated["379"] is True
    # Silence is not a negative: "Combined" is not read as a denial.
    assert separated["330"] is None
    assert separated["360"] is None


def test_the_fifth_seat_line_is_kept_off_the_330() -> None:
    """McLouis spell the exclusion `(exc 330)`, not `(excl 330)`."""
    assert "5th Homologated seat in running order (exc 330)" in plain_text(_page("330"))
    assert _product("330").mh_passenger_seats_inc_driver == 4
    assert not any("5th Homologated" in line for line in _product("330").copy_lines)
    assert any("5th Homologated" in line for line in _product("360").copy_lines)


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("330", ["Rear Drop Down Double bed", "Front Single bed"]),
        ("360", ["Rear Fixed Double bed", "Front Double bed"]),
        ("373", ["Fixed Rear Singles bed", "Front Double bed"]),
        ("379", ["Rear Fixed Double bed", "Front Double bed"]),
    ],
)
def test_the_bed_list_splits_cleanly(model: str, expected: list[str]) -> None:
    """The names carry no `Bed`, so the split keys on the size and appends the word.

    Stopping the size at the first `mm` left `x 2070mm` behind, which the next iteration
    read as a bed named `x`.
    """
    assert _bed_lines(plain_text(_page(model))) == expected


def test_a_size_suffixed_on_every_figure_is_swallowed_whole() -> None:
    assert _bed_lines("Bed Sizes Rear Fixed Double 1300mm x 2070mm") == [
        "Rear Fixed Double bed"
    ]


def test_a_size_with_a_one_m_typo_is_swallowed_whole() -> None:
    """The 379 page ends its rear bed `1500mm x 1900m`."""
    assert _bed_lines("Bed Sizes Rear Fixed Double 1500mm x 1900m") == [
        "Rear Fixed Double bed"
    ]


def test_every_layout_has_a_drop_down_bed() -> None:
    for product in _all():
        motorhome = _build_extracted_motorhome(product).motorhome
        assert BedType.DROP_DOWN in motorhome.bed_types


def test_the_heating_and_fridge_come_from_the_equipment_list() -> None:
    motorhome = _build_extracted_motorhome(_product("330")).motorhome

    assert motorhome.heating is not None
    assert motorhome.refrigeration is not None


def test_the_microwave_is_not_asserted_where_the_copy_is_silent() -> None:
    assert _build_extracted_motorhome(_product("330")).motorhome.microwave is None


# --------------------------------------------------------------------------- #
# What else reaches the reviewer
# --------------------------------------------------------------------------- #


def test_every_layout_is_a_low_profile_coachbuilt_fiat() -> None:
    motorhome = _build_extracted_motorhome(_product("330")).motorhome

    assert BODY_TYPE is BodyType.COACH_BUILT_LOW_PROFILE
    assert motorhome.body_type is BodyType.COACH_BUILT_LOW_PROFILE
    assert motorhome.base_vehicle_manufacturer == BASE_VEHICLE == "Fiat"


def test_every_layout_has_a_rear_garage() -> None:
    """Each page prints the aperture and a maximum load capacity."""
    for product in _all():
        assert product.rear_garage is True
        assert _build_extracted_motorhome(product).motorhome.rear_garage is True


def test_the_seat_provenance_explains_why_five_is_a_belt_count() -> None:
    snippet = (
        _build_extracted_motorhome(_product("360"))
        .provenance["mh_passenger_seats_inc_driver"]
        .snippet
    )

    assert "SEATBELTS" in snippet
    assert "5th Homologated seat" in snippet


def test_the_payload_provenance_shows_the_subtraction() -> None:
    snippet = (
        _build_extracted_motorhome(_product("330"))
        .provenance["mh_payload_kilograms"]
        .snippet
    )

    assert "3500kg minus 2910kg agrees" in snippet


# --------------------------------------------------------------------------- #
# Wiring
# --------------------------------------------------------------------------- #


def test_the_adapter_is_registered_under_its_fmlv_name() -> None:
    assert adapter_for("Trigano S A McLouis") is mclouis
