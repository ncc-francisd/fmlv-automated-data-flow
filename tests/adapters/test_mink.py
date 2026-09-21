"""Mink parsing, against the real index, model page and catalogue page in `fixtures/`.

Pure parsing only — no network. Every trap in the module docstring has a test, including
the one the first live run exposed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters import mink
from src.adapters.mink import (
    DRAWING_DIMENSIONS_MM,
    EXPECTED_LAYOUTS,
    FMLV_RANGE,
    MinkCaravan,
    _reconciles,
    find_catalogue_url,
    model_pages,
    parse_specification_page,
    specification_page,
)
from src.vehicle_class import VehicleClass

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def index() -> str:
    return (FIXTURES / "mink_models_index.html").read_text(encoding="utf-8")


@pytest.fixture
def model_page() -> str:
    return (FIXTURES / "mink_model_page_s.html").read_text(encoding="utf-8")


@pytest.fixture
def spec() -> str:
    return (FIXTURES / "mink_catalogue_specification_page.txt").read_text(encoding="utf-8")


# --- identity -----------------------------------------------------------------------


def test_a_mink_is_a_caravan() -> None:
    """Towed, no engine. The brand name is the only thing suggesting otherwise, and
    FMLV already files all four in the touring-caravan export."""
    assert mink.VEHICLE_CLASS is VehicleClass.CARAVAN


def test_the_manufacturer_is_the_row_that_has_the_rows() -> None:
    """Two ids could be this brand; id 168's `Mink Camppers EHF` carries none."""
    assert mink.MANUFACTURER == "Mink Campers"
    assert mink.MANUFACTURER_DISPLAY_NAME == "Mink"
    assert FMLV_RANGE == "Campers"


# --- the roster ---------------------------------------------------------------------


def test_the_index_lists_three_models(index: str) -> None:
    assert model_pages(index) == [
        ("/mink-campers/mink-e/", "E"),
        ("/mink-campers/mink-s/", "S"),
        ("/mink-campers/mink-x/", "X"),
    ]
    assert EXPECTED_LAYOUTS == 3


def test_used_stock_is_not_a_model(index: str) -> None:
    """It lives under `/vehicles-for-sale/`, which cannot match the model pattern —
    which is what keeps the requester's warning about used stock automatic."""
    assert "/vehicles-for-sale/" in index

    assert not any("vehicles-for-sale" in path for path, _model in model_pages(index))


def test_the_index_has_no_z(index: str) -> None:
    """FMLV holds a `Z` at GBP 16,995 that appears in no source at all."""
    assert "Z" not in {model for _path, model in model_pages(index)}
    assert "mink-z" not in index.lower()


# --- finding the catalogue ----------------------------------------------------------


def test_the_catalogue_is_found_on_a_model_page(model_page: str) -> None:
    """Discovered per run rather than hardcoded, so next year's edition is picked up."""
    url = find_catalogue_url(model_page)

    assert url is not None
    assert url.endswith(".pdf")
    assert "brochure" in url.lower()


def test_the_model_page_carries_none_of_the_figures(model_page: str) -> None:
    """The reason the catalogue is the source at all. The brief expected the weights to
    be on each model page; they are not, in the static HTML or the rendered DOM."""
    for figure in ("4116", "2811", "2080", "1829", "750", "19995", "19,995"):
        assert figure not in model_page, f"{figure} unexpectedly present"


def test_a_page_without_a_catalogue_link_yields_none() -> None:
    assert find_catalogue_url("<a href='/about/'>About</a>") is None


# --- the specification page ---------------------------------------------------------


def test_the_specification_page_is_recognised(spec: str) -> None:
    assert specification_page(["a cover page", spec, "a photo page"]) == spec
    assert specification_page(["nothing here"]) is None


def test_gross_is_the_mtplm_and_net_is_the_running_order(spec: str) -> None:
    """Mink's own wording, and the thing most likely to mislead someone reading the
    document cold: it never uses the words MTPLM, MiRO or payload."""
    models, _drawing, warnings = parse_specification_page(spec)

    assert warnings == []
    assert [m.model for m in models] == ["S", "X", "E"]
    assert [m.mtplm_kilograms for m in models] == [750, 750, 750]
    assert [m.mro_kilograms for m in models] == [520, 530, 510]


def test_the_payload_is_derived(spec: str) -> None:
    """FMLV holds a flat 230 on all four, which only reconciles on two: 750 - 530 is 220
    for the X and 750 - 510 is 240 for the E."""
    models, _drawing, _warnings = parse_specification_page(spec)

    assert [m.derived_payload_kilograms for m in models] == [230, 220, 240]


def test_the_drawing_is_read_not_the_rounded_table(spec: str) -> None:
    """4116 against the table's 4120, 2811 against 2810, 2080 against 2100."""
    models, drawing, _warnings = parse_specification_page(spec)

    assert drawing == DRAWING_DIMENSIONS_MM
    assert drawing["shipping_length_mm"] == 4116
    assert models[0].table_length_mm == 4120
    assert models[0].table_width_mm == 2100


def test_the_glued_drawing_callouts_are_still_read(spec: str) -> None:
    """The trap the first live run exposed. The side view's two callouts extract as
    `2080 mm4116 mm` with no space, so a word boundary on either side fails and both
    figures — the length and the width — were lost."""
    assert "2080 mm4116 mm" in spec

    _models, drawing, warnings = parse_specification_page(spec)
    assert warnings == []
    assert drawing["overall_width_mm"] == 2080
    assert drawing["shipping_length_mm"] == 4116


def test_a_column_count_mismatch_reads_nothing(spec: str) -> None:
    """Columns are matched to headings by position, because the page ties them together
    no other way. A fourth heading must stop the parse, not shift every figure by one."""
    models, _drawing, warnings = parse_specification_page(spec + "\nMINK-Q\n")

    assert models == []
    assert warnings and "matched by position" in warnings[0]


def test_the_table_height_is_kept_but_not_recorded(spec: str) -> None:
    """Read so a reviewer can see it, and deliberately not emitted: three sources give
    three heights and the drawing does not say which model it depicts."""
    models, _drawing, _warnings = parse_specification_page(spec)

    assert [m.table_height_mm for m in models] == [1850, 1880, 1850]


# --- the self-check -----------------------------------------------------------------


def test_the_masses_must_be_ordered_and_plausible() -> None:
    """A weak check, stated as such: Mink publish no payload, so there is no arithmetic
    to test the parse against."""
    good = MinkCaravan("S", 750, 520, 1850, 4120, 2100)
    assert _reconciles(good)[0] is True

    inverted = MinkCaravan("S", 520, 750, 1850, 4120, 2100)
    assert _reconciles(inverted)[0] is False

    absurd = MinkCaravan("S", 7500, 5200, 1850, 4120, 2100)
    assert _reconciles(absurd)[0] is False
