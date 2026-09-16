"""Tests for the Ace adapter's pure parsing functions, against the real pages.

Fixtures are the three real range pages from `acemotorhomes.com`, fetched 16 September 2026
with `<script>` and `<style>` removed **except the JSON block**, which is the whole source.
All three, because each carries something the others do not:

* **1200** — nine layouts, the pop-top roofs, and the one arithmetic slip.
* **1500** — the same layout code as a 2-berth and a 4-berth, which is the case FMLV
  could not previously tell apart.
* **Supreme** — seven layouts with no price published yet.

No network here.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.adapters import ace, adapter_for, habitation, swift
from src.adapters.ace import (
    EXPECTED_LAYOUTS,
    LAYOUT_CODES,
    MANUFACTURER,
    MANUFACTURER_DISPLAY_NAME,
    RANGES,
    _body_type,
    _build_extracted_motorhome,
    _discrepancies,
    _identity,
    _reconciles,
    layout_data,
    read_range,
)
from src.product_model.enums import BodyType
from src.vehicle_class import VehicleClass

FIXTURES = Path(__file__).parent / "fixtures"

PAGES = {"1200": "ace_1200.html", "1500": "ace_1500.html", "Supreme": "ace_supreme.html"}


def _page(name: str) -> str:
    return (FIXTURES / PAGES[name]).read_text(encoding="utf-8")


def _range(name: str) -> ace.Range:
    return next(entry for entry in RANGES if entry.name == name)


def _products(name: str) -> list[ace.AceProduct]:
    page = _page(name)
    return read_range(page, _range(name), habitation.list_items(page))


def _by_model(name: str) -> dict[str, ace.AceProduct]:
    return {product.model: product for product in _products(name)}


def _all() -> list[ace.AceProduct]:
    return [product for name in PAGES for product in _products(name)]


# --------------------------------------------------------------------------- #
# The second brand under one manufacturer
# --------------------------------------------------------------------------- #


def test_ace_and_swift_share_a_manufacturer_and_are_told_apart_by_the_brand() -> None:
    """The case `ADAPTERS`' display-name key exists for.

    `Swift Group Ltd` names three FMLV manufacturers — Swift, Bessacarr and Ace Motorhomes.
    Keyed on the manufacturer alone, one of these two modules would have answered for both.
    """
    assert MANUFACTURER == swift.MANUFACTURER == "Swift Group Ltd"
    assert MANUFACTURER_DISPLAY_NAME == "Ace Motorhomes"

    assert adapter_for(MANUFACTURER, display_name="Ace Motorhomes") is ace
    assert adapter_for(MANUFACTURER, display_name="Swift") is swift


def test_the_manufacturer_alone_is_now_ambiguous_and_answers_nothing() -> None:
    """Better than an arbitrary pick: the wrong adapter would write a full set of
    plausible, wrong proposals against the other brand's real product ids."""
    assert adapter_for(MANUFACTURER, VehicleClass.MOTORHOME) is None


# --------------------------------------------------------------------------- #
# The source: the site's own JSON
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(("name", "count"), [("1200", 9), ("1500", 6), ("Supreme", 7)])
def test_each_range_publishes_its_whole_dataset(name: str, count: int) -> None:
    assert len(layout_data(_page(name))) == count
    assert len(_products(name)) == count


def test_the_roster_is_twenty_two() -> None:
    """Ace publish no count of their own, so this is the only guard against a lost layout."""
    assert len(_all()) == EXPECTED_LAYOUTS == 22


def test_the_dataset_is_found_by_content_not_position() -> None:
    """A range page carries more than one JSON block."""
    blocks = ace._JSON_BLOCK.findall(_page("1500"))

    assert len(blocks) > 1
    assert all("weightMtplm" in entry for entry in layout_data(_page("1500")))


def test_a_page_without_the_dataset_yields_nothing() -> None:
    assert layout_data("<html><body>Ace</body></html>") == []
    assert read_range("<html></html>", _range("1500"), []) == []


# --------------------------------------------------------------------------- #
# The berth count, which is half the identity
# --------------------------------------------------------------------------- #


def test_one_floorplan_sold_two_ways_gets_two_models() -> None:
    """FMLV held `1500 SL` twice; matching keys on range plus model and could not tell
    them apart, and `cli._dedupe_baseline` drops duplicates outright."""
    models = _by_model("1500")

    assert set(models) == {"GL", "ET", "DB2", "DB4", "SL2", "SL4"}
    assert models["SL2"].berths == 2
    assert models["SL4"].berths == 4


def test_the_two_halves_of_a_pair_differ_only_in_mass_and_beds() -> None:
    """Which is why the title is load-bearing — nothing else separates them."""
    two, four = _by_model("1500")["SL2"], _by_model("1500")["SL4"]

    assert two.mh_length_mm == four.mh_length_mm
    assert two.mh_width_mm == four.mh_width_mm
    assert two.mtplm_kilograms == four.mtplm_kilograms
    assert two.mro_kilograms != four.mro_kilograms


def test_a_layout_with_no_berth_count_keeps_its_bare_code() -> None:
    """The 1200 already separates its 4-berths with a `T`, and `1500 GL` is 2-berth only."""
    assert set(_by_model("1200")) == {
        "GS", "GST", "RB", "RL", "RLT", "GL", "GLT", "SL", "SLT",
    }
    assert _identity("1500 GL", "1500") == ("GL", "GL")


def test_the_berth_is_joined_with_no_separator() -> None:
    """`SL 2` against `SL 4` scores exactly 0.500 — the matching threshold itself — and
    `SL (2 berth)` scores 0.600. Only the joined form is safely distinct."""
    from src.diff.matching import DEFAULT_THRESHOLD, token_similarity  # noqa: PLC0415
    from src.product_model.model import Motorhome  # noqa: PLC0415

    def pair(left: str, right: str) -> float:
        return token_similarity(
            Motorhome(manufacturer=MANUFACTURER, manufacturer_range="1500", model=left),
            Motorhome(manufacturer=MANUFACTURER, manufacturer_range="1500", model=right),
        )

    assert _identity("1500 SL (2 berth)", "1500") == ("SL2", "SL")
    assert pair("SL2", "SL4") < DEFAULT_THRESHOLD
    assert pair("SL 2", "SL 4") >= DEFAULT_THRESHOLD


def test_a_layout_from_another_range_is_not_claimed() -> None:
    assert _identity("Supreme SL (2 berth)", "1500") is None


# --------------------------------------------------------------------------- #
# The figures
# --------------------------------------------------------------------------- #


def test_a_layout_yields_every_field() -> None:
    product = _by_model("1500")["DB4"]

    assert product.berths == 4
    assert product.mh_passenger_seats_inc_driver == 4
    assert product.mh_length_mm == 7810
    assert product.mh_width_mm == 2370
    assert product.mh_height_mm == 2880
    assert product.mtplm_kilograms == 3500
    assert product.mro_kilograms == 3045
    assert product.mh_payload_kilograms == 455
    assert product.rrp_pounds == 71_490


def test_dimensions_are_converted_from_metres() -> None:
    """Ace publish `7.81m`, not `7810mm`."""
    assert layout_data(_page("1500"))[2]["length"] == "7.81m"
    assert _by_model("1500")["DB2"].mh_length_mm == 7810


def test_an_unpublished_price_is_nothing_rather_than_zero() -> None:
    """The whole Supreme range reads `startingPrice: 0`, which is not a price."""
    assert all(entry["startingPrice"] == 0 for entry in layout_data(_page("Supreme")))
    assert all(product.rrp_pounds is None for product in _products("Supreme"))
    assert "rrp_pounds" not in _build_extracted_motorhome(
        _by_model("Supreme")["EW2"]
    ).provenance


def test_the_priced_ranges_are_all_priced() -> None:
    assert all(p.rrp_pounds is not None for p in _products("1200") + _products("1500"))


# --------------------------------------------------------------------------- #
# The self-check, which is a real one
# --------------------------------------------------------------------------- #


def test_the_masses_close_on_every_layout_but_one() -> None:
    """`payload == MTPLM - MRO`, which several other adapters have no equivalent of."""
    off = [p.label for p in _all() if _discrepancies(p)]

    assert off == ["1200 RLT"]


def test_the_one_that_does_not_close_is_reported_and_kept() -> None:
    """Out by exactly the 30kg Ace's own automatic option says it moves — their slip."""
    product = _by_model("1200")["RLT"]

    assert _reconciles(product)[0] is True
    notes = _discrepancies(product)
    assert len(notes) == 1
    assert "30kg" in notes[0]
    assert product.mtplm_kilograms - product.mro_kilograms != product.mh_payload_kilograms


def test_an_entry_missing_its_masses_is_dropped() -> None:
    """What a change to the dataset's shape would produce."""
    product = replace(_by_model("1500")["GL"], mtplm_kilograms=None)

    reconciles, why_not = _reconciles(product)

    assert reconciles is False
    assert "MTPLM" in why_not


# --------------------------------------------------------------------------- #
# What reaches the reviewer
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("range_name", "model", "expected"),
    [
        ("1200", "RL", BodyType.CAMPERVAN_HIGH_TOP),
        ("1200", "RLT", BodyType.CAMPERVAN_HIGH_TOP_ELEVATING_ROOF),
        ("1500", "DB2", BodyType.COACH_BUILT_LOW_PROFILE),
        ("Supreme", "EW2", BodyType.COACH_BUILT_LOW_PROFILE),
    ],
)
def test_the_body_type_follows_the_range_and_the_pop_top(
    range_name: str, model: str, expected: BodyType
) -> None:
    assert _by_model(range_name)[model].body_type is expected


def test_the_pop_top_flag_marks_exactly_the_t_layouts() -> None:
    """Read from the data rather than inferred from the letter."""
    popped = {p.model for p in _products("1200") if "ELEVATING" in p.body_type.name}

    assert popped == {"GST", "RLT", "GLT", "SLT"}


def test_a_range_carries_one_chassis() -> None:
    assert _range("1200").base_vehicle == "Fiat"
    assert _range("1500").base_vehicle == _range("Supreme").base_vehicle == "Ford"
    assert _build_extracted_motorhome(
        _by_model("1200")["RL"]
    ).motorhome.base_vehicle_manufacturer == "Fiat"


# --------------------------------------------------------------------------- #
# Habitation, qualified by letter rather than by number
# --------------------------------------------------------------------------- #


def test_a_feature_qualified_by_letter_reaches_only_those_layouts() -> None:
    """`Separate shower cubicle (DB, ET & SL)` — the 1500 GL does not have one."""
    lines = ["Separate shower cubicle (DB, ET & SL)"]

    assert habitation.lines_for_layout(lines, "DB", codes=LAYOUT_CODES) == lines
    assert habitation.lines_for_layout(lines, "GL", codes=LAYOUT_CODES) == []


def test_a_parenthesis_that_is_not_a_layout_list_is_left_alone() -> None:
    """`(LED)` and `(5G ready)` are the same shape and must not restrict anything."""
    lines = ["LED lighting (LED)", "Motorhome WiFi (5G ready)"]

    assert habitation.lines_for_layout(lines, "GL", codes=LAYOUT_CODES) == lines


def test_the_beds_come_from_the_layouts_own_entry() -> None:
    """Per layout and properly named, rather than scraped from the range's prose."""
    beds = ace._bed_lines(layout_data(_page("1500"))[0])

    assert beds
    assert all(line.endswith(" bed") for line in beds)


def test_a_habitation_finding_quotes_the_page() -> None:
    extracted = _build_extracted_motorhome(_by_model("1500")["DB2"])

    for field_name in ("heating", "refrigeration", "bed_types"):
        if field_name in extracted.provenance:
            assert extracted.provenance[field_name].snippet


# --------------------------------------------------------------------------- #
# Wiring
# --------------------------------------------------------------------------- #


def test_the_adapter_is_registered_under_its_own_brand() -> None:
    assert adapter_for("Swift Group Ltd", display_name="Ace Motorhomes") is ace
