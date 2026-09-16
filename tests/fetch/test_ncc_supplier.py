"""Picking a supplier from the NCC export drop-down, and saying so when it is absent.

Playwright's own failure here is 30 seconds of silence and then a locator dump — *"did not
find some options"* beside the `<select>`'s markup, naming neither the supplier nor the
reason. Atom failed exactly that way on 16 September 2026, triggered from the review app,
because a triggered run refreshes the export first and `Atom` was not yet an NCC supplier.

No network or browser here: the page is a stub with the options a real one would report.
"""

from __future__ import annotations

import pytest

from src.fetch.ncc import SupplierNotListed, _select_supplier

SELECTOR = "select#exhibitor"


class _Locator:
    def __init__(self, options: list[str]) -> None:
        self._options = options

    def all_text_contents(self) -> list[str]:
        return self._options


class _Page:
    """Enough of a Playwright page for the one call under test."""

    def __init__(self, options: list[str]) -> None:
        self._options = options
        self.selected: str | None = None

    def locator(self, selector: str) -> _Locator:
        assert selector == f"{SELECTOR} option"
        return _Locator(self._options)

    def select_option(self, selector: str, *, label: str) -> None:
        assert selector == SELECTOR
        self.selected = label


def test_a_listed_supplier_is_selected() -> None:
    page = _Page(["", "Adria Caravans & Motorhomes", "Marquis Leisure", "Swift"])

    _select_supplier(page, SELECTOR, "Marquis Leisure")

    assert page.selected == "Marquis Leisure"


def test_whitespace_around_an_option_does_not_hide_it() -> None:
    """Nova pads its option text, which would otherwise look like a missing supplier."""
    page = _Page(["  Marquis Leisure  "])

    _select_supplier(page, SELECTOR, "Marquis Leisure")

    assert page.selected == "Marquis Leisure"


def test_a_brand_new_to_fmlv_fails_at_once_and_says_why() -> None:
    """The Atom case: no products yet, so no supplier, so nothing to export."""
    page = _Page(["", "Adria Caravans & Motorhomes", "Swift"])

    with pytest.raises(SupplierNotListed) as excinfo:
        _select_supplier(page, SELECTOR, "Atom")

    message = str(excinfo.value)
    assert "'Atom' is not in the NCC supplier list" in message
    assert "empty-baseline" in message
    assert page.selected is None


def test_a_near_miss_is_offered_because_the_registry_is_the_likelier_fault() -> None:
    """Once a manufacturer exists, a mismatch is usually the registry's spelling."""
    page = _Page(["Marquis Leisure Ltd", "Swift"])

    with pytest.raises(SupplierNotListed) as excinfo:
        _select_supplier(page, SELECTOR, "Marquis Leisure")

    assert "'Marquis Leisure Ltd'" in str(excinfo.value)


def test_no_near_miss_offers_nothing_rather_than_noise() -> None:
    page = _Page(["Swift", "Bailey"])

    with pytest.raises(SupplierNotListed) as excinfo:
        _select_supplier(page, SELECTOR, "Atom")

    assert "closest" not in str(excinfo.value)
