"""Globecar parsing, against the real pages captured in `fixtures/`.

Pure parsing only — no network. Every trap in the module docstring has a test here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters import globecar
from src.adapters.globecar import (
    EXPECTED_LAYOUTS,
    LAYOUTS,
    GlobecarCampervan,
    _reconciles,
    parse_header_card,
    parse_seat_belts,
    parse_technical_data,
    resolve_roster,
    technical_block,
    visible_lines,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _lines(name: str) -> list[str]:
    return (FIXTURES / name).read_text(encoding="utf-8").splitlines()


@pytest.fixture
def summit_540() -> list[str]:
    return _lines("globecar_summit_540_text.txt")


@pytest.fixture
def summit_600l() -> list[str]:
    return _lines("globecar_summit_600l_text.txt")


@pytest.fixture
def shine_540() -> list[str]:
    return _lines("globecar_summit_shine_540_text.txt")


# --- identity and roster ------------------------------------------------------------


def test_the_manufacturer_matches_the_export() -> None:
    assert globecar.MANUFACTURER == "Globecar"
    assert globecar.MANUFACTURER_DISPLAY_NAME == "Globecar"


def test_eleven_layouts_across_three_ranges() -> None:
    assert len(LAYOUTS) == EXPECTED_LAYOUTS
    assert {layout.manufacturer_range for layout in LAYOUTS} == {
        "Summit",
        "Summit Prime",
        "Summit Shine",
    }


def test_two_slugs_are_misspelt_on_the_site() -> None:
    """`sumit-prime-540` and `sumit-shine-640` are both missing the second `m`. The roster
    cannot be built by joining the range and model names, which is why it is hardcoded."""
    misspelt = sorted(layout.slug for layout in LAYOUTS if not layout.slug.startswith("summit"))

    assert misspelt == ["sumit-prime-540", "sumit-shine-640"]


def test_the_index_links_exactly_the_expected_roster() -> None:
    """What catches a layout being added, or a misspelt slug being corrected."""
    index = (FIXTURES / "globecar_range_index.html").read_text(encoding="utf-8")

    published, expected = resolve_roster(index)

    assert published == expected


def test_fmlvs_range_model_split_is_followed() -> None:
    """`Summit Prime` / `540`, not `Summit` / `Prime 540` — which is how FMLV's own 2027
    rows are filed. Its 2022 rows use the older `H - Line` / `Summit 540` arrangement and
    are dropped by the year filter, so they cannot be matched either way."""
    prime = [layout for layout in LAYOUTS if layout.manufacturer_range == "Summit Prime"]

    assert sorted(layout.model for layout in prime) == ["540", "600", "640"]


# --- the technical data block -------------------------------------------------------


def test_the_table_is_read_not_the_header_card(summit_540: list[str]) -> None:
    """The whole point of scoping. On the Summit 540 the header card says 3300kg and the
    table says 3500kg, and the card comes first on the page — so an unscoped read takes
    the wrong one."""
    card = parse_header_card(summit_540)
    table = parse_technical_data(summit_540)

    assert card.mtplm_kilograms == 3300
    assert table.mtplm_kilograms == 3500


def test_the_card_is_wrong_on_the_shine_540_too(shine_540: list[str]) -> None:
    """3000kg is not a chassis Globecar offers, and FMLV holds 3300 for this layout."""
    assert parse_header_card(shine_540).mtplm_kilograms == 3000
    assert parse_technical_data(shine_540).mtplm_kilograms == 3300


def test_the_summit_540_figures(summit_540: list[str]) -> None:
    figures = parse_technical_data(summit_540)

    assert figures.mh_length_mm == 5413
    assert figures.mh_width_mm == 2050
    assert figures.mh_height_mm == 2580
    assert figures.mtplm_kilograms == 3500
    assert figures.mro_kilograms == 2680
    assert figures.payload_kilograms == 820
    assert figures.berths == 2


def test_exterior_height_is_not_interior_height(summit_540: list[str]) -> None:
    """`Height:` and `Interior height:` are both in the same block, so a substring match
    on the first would take whichever came first."""
    figures = parse_technical_data(summit_540)

    assert figures.mh_height_mm == 2580
    assert figures.interior_height_mm == 1905


def test_berths_take_the_base_not_the_option(summit_540: list[str]) -> None:
    """`Sleeping places: 2 (+1 optional)`. The extra berth is a factory-order seat, and an
    optional berth does not count."""
    figures = parse_technical_data(summit_540)

    assert figures.sleeping_raw == "2 (+1 optional)"
    assert figures.berths == 2


def test_the_header_card_inflates_its_counts(summit_540: list[str]) -> None:
    """It folds the options into the headline — `SEATS 4` against the table's `3/3
    (+1 optional)`, and `SLEEPS 2 (+3 opt.)` against `2 (+1 optional)`. Another reason
    nothing is ever recorded from it."""
    card = parse_header_card(summit_540)
    table = parse_technical_data(summit_540)

    assert card.seats_raw == "4"
    assert parse_seat_belts(table.seats_raw)[0] == 3


def test_a_page_without_the_block_yields_nothing() -> None:
    assert technical_block(["Some marketing copy", "3500kg"]) == []
    assert parse_technical_data(["Some marketing copy"]).mtplm_kilograms is None


def test_a_bed_size_is_never_read_as_a_dimension() -> None:
    """`Rear bed in mm (approx)` is `1.960 x 1.200/1.410`, which must not parse."""
    lines = ["TECHNICAL DATA", "Length", "1.960 x 1.200/1.410"]

    assert parse_technical_data(lines).mh_length_mm is None


# --- seats --------------------------------------------------------------------------


def test_the_belt_count_is_recorded_not_the_seat_count(summit_540: list[str]) -> None:
    """`3/3` is seats over belts, and only three-point belts count as travel seats."""
    seats, reason = parse_seat_belts(parse_technical_data(summit_540).seats_raw)

    assert seats == 3
    assert "three-point belts" in reason


def test_four_belts_where_the_page_says_four(summit_600l: list[str]) -> None:
    figures = parse_technical_data(summit_600l)

    assert figures.seats_raw == "4/4 (+1 optional)"
    assert parse_seat_belts(figures.seats_raw)[0] == 4


def test_two_configurations_in_one_cell_are_not_read(shine_540: list[str]) -> None:
    """The trap. Seven layouts state `3/3 (+1 optional)/4 (+1 optional)`, which is two
    seating configurations with nothing to say which this layout is built as — and FMLV
    holds 4 for two of them and 3 for the other five against that identical string. So it
    is genuinely both, and any guess would be wrong somewhere."""
    figures = parse_technical_data(shine_540)

    assert figures.seats_raw == "3/3 (+1 optional)/4 (+1 optional)"
    seats, reason = parse_seat_belts(figures.seats_raw)
    assert seats is None
    assert "NOT READ" in reason


def test_the_optional_seat_is_never_added() -> None:
    """`(+1 optional)` is a factory order, so 3 stays 3."""
    assert parse_seat_belts("3/3 (+1 optional)")[0] == 3


def test_an_absent_or_odd_seats_cell_reads_nothing() -> None:
    assert parse_seat_belts(None)[0] is None
    assert parse_seat_belts("on request")[0] is None


# --- the self-check -----------------------------------------------------------------


def test_the_published_payload_checks_the_parse(summit_540: list[str]) -> None:
    """Globecar publishes MPLM, MRO *and* payload, so the three check each other:
    3500 - 2680 = 820, which is the figure on the page."""
    product = GlobecarCampervan(layout=LAYOUTS[0], figures=parse_technical_data(summit_540))

    reconciles, reason = _reconciles(product)

    assert reconciles is True
    assert "820kg" in reason


def test_a_layout_whose_three_masses_disagree_is_dropped(summit_540: list[str]) -> None:
    """Had the header card's 3300 been read, this is what would have caught it:
    3300 - 2680 = 620, not the published 820."""
    figures = parse_technical_data(summit_540)
    figures.mtplm_kilograms = 3300
    product = GlobecarCampervan(layout=LAYOUTS[0], figures=figures)

    reconciles, reason = _reconciles(product)

    assert reconciles is False
    assert "620" in reason


def test_a_missing_mass_drops_the_layout(summit_540: list[str]) -> None:
    figures = parse_technical_data(summit_540)
    figures.payload_kilograms = None

    assert _reconciles(GlobecarCampervan(layout=LAYOUTS[0], figures=figures))[0] is False


# --- the line split -----------------------------------------------------------------


def test_each_value_lands_on_its_own_line() -> None:
    html = "<div>MPLM</div><div>3500kg</div>"

    assert visible_lines(html) == ["MPLM", "3500kg"]


def test_scripts_are_dropped() -> None:
    assert visible_lines("<script>var kg = 9999;</script><p>3500kg</p>") == ["3500kg"]
