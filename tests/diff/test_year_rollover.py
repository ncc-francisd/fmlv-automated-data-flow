"""Unit tests for model-year rollover — DESIGN.md §9 open question 1."""

from __future__ import annotations

from datetime import date

from src.diff.year_rollover import bump_year, can_bump_year, in_rollover_window
from src.product_model.model import Motorhome


def test_bump_year_advances_by_one() -> None:
    motorhome = Motorhome(year=2026)
    bumped = bump_year(motorhome)
    assert bumped.year == 2027


def test_bump_year_does_not_mutate_the_original() -> None:
    motorhome = Motorhome(year=2026)
    bump_year(motorhome)
    assert motorhome.year == 2026


def test_bump_year_is_a_no_op_when_year_is_unset() -> None:
    motorhome = Motorhome(year=None)
    assert bump_year(motorhome).year is None


def test_bump_year_leaves_every_other_field_untouched() -> None:
    motorhome = Motorhome(year=2026, model="Supreme 670 DC", rrp_pounds=93950)
    bumped = bump_year(motorhome)
    assert bumped.model == "Supreme 670 DC"
    assert bumped.rrp_pounds == 93950


def test_in_rollover_window_true_in_july() -> None:
    assert in_rollover_window(date(2026, 7, 15)) is True


def test_in_rollover_window_true_on_boundaries() -> None:
    assert in_rollover_window(date(2026, 6, 1)) is True
    assert in_rollover_window(date(2026, 12, 31)) is True


def test_in_rollover_window_runs_past_the_autumn_shows() -> None:
    """Widened from 30 September on 1 October 2026, when Carthago and Adria were both
    still publishing 2027 vehicles. October is squarely rollover season."""
    assert in_rollover_window(date(2026, 10, 1)) is True
    assert in_rollover_window(date(2026, 11, 20)) is True


def test_in_rollover_window_false_outside_the_window() -> None:
    assert in_rollover_window(date(2026, 5, 31)) is False
    assert in_rollover_window(date(2026, 1, 15)) is False


def test_the_window_stops_where_can_bump_year_does() -> None:
    """On 1 January a 2026 product is no longer bumpable by either route, so there is
    nothing for a wider window to offer."""
    assert in_rollover_window(date(2026, 12, 31)) is True
    assert can_bump_year(2026, today=date(2026, 12, 31)) is True
    assert can_bump_year(2026, today=date(2027, 1, 1)) is False


def test_can_bump_year_true_when_the_year_is_the_current_year() -> None:
    assert can_bump_year(2026, today=date(2026, 7, 15)) is True


def test_can_bump_year_false_when_already_at_current_year_plus_one() -> None:
    assert can_bump_year(2027, today=date(2026, 7, 15)) is False


def test_can_bump_year_false_when_beyond_the_cap() -> None:
    assert can_bump_year(2028, today=date(2026, 7, 15)) is False


def test_can_bump_year_false_when_the_year_is_stale() -> None:
    assert can_bump_year(2025, today=date(2026, 7, 15)) is False
