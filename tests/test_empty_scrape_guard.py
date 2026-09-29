"""A run that scrapes nothing must refuse to compare.

Added 29 September 2026, after Adria restructured their site and both adapters started
returning zero. The diff would have compared nothing against the live baseline and proposed
every Adria product for deactivation — the whole brand — from a review screen that looked
entirely ordinary.
"""

from __future__ import annotations

import pytest

from src import cli


def test_a_scrape_that_found_nothing_refuses_to_compare() -> None:
    """The guard, stated as the message a reviewer would see."""
    with pytest.raises(RuntimeError) as raised:
        cli._refuse_empty_scrape(scraped=[], baseline=[object(), object()], name="Adria Mobil")

    assert "NO products" in str(raised.value)
    assert "every Adria Mobil product" in str(raised.value)


def test_an_empty_baseline_is_not_the_same_thing() -> None:
    """A brand FMLV holds nothing for yet is a legitimate first run, not a broken one."""
    cli._refuse_empty_scrape(scraped=[], baseline=[], name="New Brand")


def test_a_scrape_that_found_something_passes() -> None:
    cli._refuse_empty_scrape(scraped=[object()], baseline=[object()], name="Adria Mobil")


def test_a_range_scoped_run_may_still_come_back_empty() -> None:
    """The pipeline has always allowed this, and its blast radius is one range the
    operator named rather than the whole brand."""
    cli._refuse_empty_scrape(
        scraped=[],
        baseline=[object()],
        name="Adria Mobil",
        whole_manufacturer=False,
    )
