"""Tests for the Vantage adapter's pure parsing functions, against the real pages.

Fixtures are four real pages from `vantagemotorhomes.co.uk`, fetched 17 September 2026
with `<script>` and `<style>` removed. Four, because each carries something the others do
not:

* **the 5.99m index** — six models, and the trap that both Ford F-Lines are linked from a
  *panel van* index.
* **cub** — an ordinary Fiat layout, and the marketing line "upgrade from a pop-top" that
  must not be read as an elevating roof.
* **ora-f-line** — the Ford, and the mixed-case heading (`ORA F Line`) that an
  upper-case-only pattern silently dropped.
* **vantage-r** — a **stock** page, which must be rejected. This is the negative test the
  whole roster design exists for.

No network here.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.adapters import adapter_for, vantage
from src.adapters.vantage import (
    DEFAULT_RANGES,
    EXPECTED_LAYOUTS,
    MANUFACTURER,
    _KNOWN_NON_MODELS,
    _reconciles,
    build_extracted,
    elevating_roof_in,
    find_model_slugs,
    parse_model_page,
)
from src.adapters import habitation
from src.product_model.enums import BodyType
from src.vehicle_class import VehicleClass

FIXTURES = Path(__file__).parent / "fixtures"

URL = "https://www.vantagemotorhomes.co.uk/cub"

PAGES = {
    "index": "vantage_index_599.html",
    "cub": "vantage_cub.html",
    "ora-f-line": "vantage_ora_f_line.html",
    "stock": "vantage_stock.html",
}


def _page(name: str) -> str:
    return (FIXTURES / PAGES[name]).read_text(encoding="utf-8")


def _product(slug: str, *, index_range: str | None = "5.99m"):
    parsed = parse_model_page(_page(slug), slug, index_range=index_range)
    assert parsed is not None
    return parsed


# --------------------------------------------------------------------------- #
# Registration
# --------------------------------------------------------------------------- #


def test_the_adapter_is_registered_for_campervans() -> None:
    assert adapter_for(MANUFACTURER, VehicleClass.MOTORHOME) is vantage
    assert vantage.VEHICLE_CLASS is VehicleClass.MOTORHOME
    assert MANUFACTURER == "Vantage"


def test_there_are_three_length_ranges() -> None:
    assert [label for _path, label in DEFAULT_RANGES] == ["5.41m", "5.99m", "6.36m"]


# --------------------------------------------------------------------------- #
# The range is the length — the inverted identity
# --------------------------------------------------------------------------- #


def test_the_range_is_the_length_and_the_model_is_the_name() -> None:
    """Inverted from every other brand, and confirmed against FMLV's own export."""
    cub = _product("cub", index_range="5.41m")

    assert cub.manufacturer_range == "5.41m"
    assert cub.model == "CUB"


def test_the_range_comes_from_the_page_not_from_the_index() -> None:
    """The index is used to check the range, never to supply it."""
    assert _product("cub", index_range=None).manufacturer_range == "5.41m"


def test_the_f_line_heading_is_not_upper_case() -> None:
    """The bug that silently collected 11 of 13: eleven pages head themselves `CUB`, and
    the other two head themselves `ORA F Line`. Only `EXPECTED_LAYOUTS` disagreed."""
    f_line = _product("ora-f-line")

    assert f_line.model == "ORA F-Line"
    assert f_line.manufacturer_range == "5.99m"


def test_the_f_line_name_is_hyphenated_as_vantage_write_it_elsewhere() -> None:
    """The heading says `ORA F Line`; the page title and its own prose say `ORA F-Line`.
    These two are new products, so the name proposed here becomes the name FMLV holds."""
    assert "ORA F Line" in _page("ora-f-line")
    assert _product("ora-f-line").model == "ORA F-Line"


# --------------------------------------------------------------------------- #
# The roster, and everything that is not a Vantage
# --------------------------------------------------------------------------- #


def test_the_index_links_both_fords_from_a_panel_van_page() -> None:
    """Which is why the make cannot come from the section — see the module docstring."""
    slugs = find_model_slugs(_page("index"))

    assert {"ora", "sol", "max", "teo", "ora-f-line", "sol-f-line-13"} <= set(slugs)


def test_the_stock_page_is_not_a_model_and_is_rejected() -> None:
    """The negative test the roster design exists for. `/vantage-r` lists used and ex-demo
    vehicles with their own prices, and reading one would propose a second-hand van as a
    current model."""
    assert "Stock Bonus" in _page("stock")

    assert parse_model_page(_page("stock"), "vantage-r") is None


def test_the_navigation_is_not_mistaken_for_models() -> None:
    """Pilote's pages are on every index, and Pilote are a different FMLV manufacturer."""
    slugs = set(find_model_slugs(_page("index")))

    assert not slugs & {"pilote", "pilote-atlas", "pilote-pacific", "galaxy"}
    assert {"pilote", "galaxy", "motorhome-stock", "vantage-r"} <= _KNOWN_NON_MODELS


def test_a_page_that_is_not_a_model_yields_nothing() -> None:
    assert parse_model_page("<html><body>Vantage</body></html>", "x") is None


def test_the_roster_is_thirteen() -> None:
    """Vantage publish no count, so this is the only guard against a lost card — and it
    is what caught the mixed-case heading bug."""
    assert EXPECTED_LAYOUTS == 13


# --------------------------------------------------------------------------- #
# The figures
# --------------------------------------------------------------------------- #


def test_a_model_yields_every_field() -> None:
    cub = _product("cub", index_range="5.41m")

    assert cub.berths == 2
    assert cub.travel_seats == 2
    assert cub.base_vehicle_manufacturer == "Fiat"
    assert cub.mtplm_kilograms == 3500
    assert cub.payload_kilograms == 600
    assert cub.rrp_pounds == 74_995


def test_the_mass_in_running_order_is_derived() -> None:
    """Vantage publish no MRO. The derivation reproduces FMLV's stored figure exactly on
    all eleven existing models — 3500 - 600 = 2900 is what FMLV holds for the CUB."""
    assert _product("cub", index_range="5.41m").mro_kilograms == 2900


def test_the_base_vehicle_is_the_make_alone() -> None:
    """One name per company, not the trim — and read per page, so the Ford is a Ford."""
    assert _product("ora-f-line").base_vehicle_manufacturer == "Ford"
    assert _product("cub", index_range="5.41m").base_vehicle_manufacturer == "Fiat"
    assert "Transit" in _product("ora-f-line").base_vehicle_evidence


def test_the_price_is_the_otr_headline_and_not_an_option() -> None:
    """The same page lists `8 Speed Automatic Transmission £2520` and `CAT 1 Alarm £525`
    in a quotation calculator. The first bare £ on the page is not the price."""
    assert "£2520" in _page("cub") or "2520" in _page("cub")

    assert _product("cub", index_range="5.41m").rrp_pounds == 74_995


def test_a_page_with_no_otr_line_yields_no_price() -> None:
    """Better than a £525 campervan."""
    page = _page("cub").replace("(OTR)", "(each)")

    parsed = parse_model_page(page, "cub")
    assert parsed is not None
    assert parsed.rrp_pounds is None


# --------------------------------------------------------------------------- #
# The self-check
# --------------------------------------------------------------------------- #


def test_a_model_reconciles() -> None:
    assert _reconciles(_product("cub", index_range="5.41m"))[0] is True


def test_a_page_linked_from_the_wrong_length_index_is_dropped() -> None:
    """The only genuinely independent check this source offers: the index states the
    range and the page states its own."""
    reconciles, why_not = _reconciles(_product("cub", index_range="6.36m"))

    assert reconciles is False
    assert "6.36m" in why_not and "5.41m" in why_not


def test_a_payload_that_exceeds_the_vehicle_is_dropped() -> None:
    product = _product("cub", index_range="5.41m")

    reconciles, why_not = _reconciles(replace(product, payload_kilograms=4000))

    assert reconciles is False
    assert "no vehicle" in why_not


def test_a_model_missing_a_mass_is_dropped() -> None:
    product = _product("cub", index_range="5.41m")

    reconciles, why_not = _reconciles(replace(product, mtplm_kilograms=None))

    assert reconciles is False
    assert "gross vehicle weight" in why_not


# --------------------------------------------------------------------------- #
# What reaches the reviewer
# --------------------------------------------------------------------------- #


def test_every_model_is_a_high_top_campervan() -> None:
    """Asserted, because the roof rule needs a height and Vantage publish none. FMLV
    already holds this on all eleven existing models."""
    extracted = build_extracted(_product("cub", index_range="5.41m"), URL, basis="x")

    assert extracted.motorhome.body_type is BodyType.CAMPERVAN_HIGH_TOP
    assert "high top" in extracted.provenance["body_type"].snippet


def test_marketing_copy_is_not_read_as_an_elevating_roof() -> None:
    """The CUB is sold as "the ideal upgrade from a pop-top", which is a sentence about a
    different kind of van. Scanning the page turned that into a warning every run."""
    assert "pop-top" in _page("cub")

    assert elevating_roof_in(tuple(habitation.list_items(_page("cub")))) is None


def test_a_real_elevating_roof_in_the_equipment_is_reported() -> None:
    assert elevating_roof_in(("Elevating roof with stitched lining",)) is not None
    assert elevating_roof_in(("Rear parking sensors",)) is None


@pytest.mark.parametrize("field_name", ["mh_length_mm", "mh_width_mm", "mh_height_mm"])
def test_no_dimension_is_emitted(field_name: str) -> None:
    """The site's only length is the rounded range name — 5.41m against FMLV's 5413mm —
    and no width or height is published at all. FMLV's own figures stand."""
    extracted = build_extracted(_product("cub", index_range="5.41m"), URL, basis="x")

    assert getattr(extracted.motorhome, field_name) is None
    assert field_name not in extracted.provenance


def test_both_halves_of_the_identity_carry_provenance() -> None:
    provenance = build_extracted(_product("cub", index_range="5.41m"), URL, basis="x").provenance

    assert "manufacturer_range" in provenance
    assert "model" in provenance
    # The range is a measurement, so the snippet has to say why.
    assert "length" in provenance["manufacturer_range"].snippet


def test_the_base_vehicle_snippet_says_where_it_was_read() -> None:
    """Because the obvious wrong source — the index section — gives Fiat for a Ford."""
    extracted = build_extracted(_product("ora-f-line"), URL, basis="x")

    assert "own page" in extracted.provenance["base_vehicle_manufacturer"].snippet
