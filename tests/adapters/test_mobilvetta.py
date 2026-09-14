"""Tests for the Mobilvetta adapter's pure parsing functions, against real pages.

Fixtures are real importer range pages fetched 14 September 2026 with `<script>` and
`<style>` removed — see `docs/adapters/mobilvetta.md`. All four current ones, because a
page here is a *range* rather than a product and the four between them carry all eight
layouts:

* **K-Yacht** — four layouts on one page, and four prices, two of which a fixed-width
  extraction lost.
* **KEA** — two layouts.
* **Admiral** — one, and the only campervan.
* **KEA Kompakt** — one, and the only range whose prefix is a superset of another's.

No network here.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.adapters import adapter_for, mobilvetta
from src.adapters.mobilvetta import (
    BASE_VEHICLE,
    EXCLUDED_PAGES,
    EXPECTED_LAYOUTS,
    RANGE_PREFIXES,
    MobilvettaProduct,
    _build_extracted_motorhome,
    _range_and_model,
    _reconciles,
    find_range_urls,
    layout_blocks,
    plain_text,
)
from src.product_model.enums import BodyType

FIXTURES = Path(__file__).parent / "fixtures"

PAGES: dict[str, str] = {
    "mobilvetta_k_yacht.html": "https://www.marquisleisure.co.uk/mobilvetta-k-yacht-2026-motorhome-range",
    "mobilvetta_kea.html": "https://www.marquisleisure.co.uk/mobilvetta-kea-2026-motorhome-range",
    "mobilvetta_admiral.html": "https://www.marquisleisure.co.uk/mobilvetta-admiral-2026-campervan-range",
    "mobilvetta_kea_kompakt.html": "https://www.marquisleisure.co.uk/mobilvetta-kea-kompakt-2026-motorhome-range",
}

ALL_KEYS = tuple(key for key, _label in mobilvetta.DEFAULT_RANGES)


def _page(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _layouts(name: str) -> list[MobilvettaProduct]:
    return layout_blocks(_page(name), PAGES[name])


def _by_model(name: str) -> dict[str, MobilvettaProduct]:
    return {p.model: p for p in _layouts(name)}


# --------------------------------------------------------------------------- #
# The roster
# --------------------------------------------------------------------------- #


def _index(*slugs: str) -> str:
    return "".join(f'<a href="/{s}">x</a>' for s in slugs)


def test_only_range_pages_are_taken() -> None:
    """The requester's warning was to avoid the used-stock pages."""
    html_ = _index(
        "mobilvetta-kea-2026-motorhome-range",
        "used-mobilvetta-kea-for-sale",
        "new-motorhomes/mobilvetta",
    )

    urls = find_range_urls(html_, ALL_KEYS)

    assert urls == ["https://www.marquisleisure.co.uk/mobilvetta-kea-2026-motorhome-range"]


def test_the_eighties_page_is_excluded() -> None:
    """The requester ruled it stock rather than range, 14 September 2026.

    FMLV's current Mobilvetta range is exactly eight and neither 80 is among them.
    """
    html_ = _index(
        "mobilvetta-k-yacht-80-and-kea-80-2026-motorhome-range",
        "mobilvetta-kea-2026-motorhome-range",
    )

    urls = find_range_urls(html_, ALL_KEYS)

    assert len(urls) == 1
    assert "80" not in urls[0]
    assert "mobilvetta-k-yacht-80-and-kea-80-2026-motorhome-range" in EXCLUDED_PAGES


def test_a_single_range_reads_only_its_own_page() -> None:
    html_ = _index(
        "mobilvetta-kea-2026-motorhome-range",
        "mobilvetta-admiral-2026-campervan-range",
    )

    assert find_range_urls(html_, ("admiral",)) == [
        "https://www.marquisleisure.co.uk/mobilvetta-admiral-2026-campervan-range"
    ]


def test_the_four_pages_carry_eight_layouts_between_them() -> None:
    """A page is a range, not a product — the roster count is this source's only check."""
    total = sum(len(_layouts(name)) for name in PAGES)

    assert total == EXPECTED_LAYOUTS == 8
    assert len(_layouts("mobilvetta_k_yacht.html")) == 4
    assert len(_layouts("mobilvetta_kea.html")) == 2


# --------------------------------------------------------------------------- #
# The heading, whose first block carries the page's banner
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("heading", "expected"),
    [
        ("K.YACHT 86", ("K-YACHT TEKNO LINE", "86")),
        ("MOBILVETTA K.YACHT A CLASS MOTORHOME RANGE K.YACHT 59", ("K-YACHT TEKNO LINE", "59")),
        ("MOBILVETTA ADMIRAL ADMIRAL K 6.3", ("ADMIRAL", "K 6.3")),
        ("MOBILVETTA KEA COACHBUILT MOTORHOME RANGE KEA 86", ("KEA", "86")),
        ("MOBILVETTA KEA KOMPAKT KEA KOMPAKT 55", ("KEA Kompakt", "55")),
    ],
)
def test_the_last_occurrence_of_the_prefix_wins(
    heading: str, expected: tuple[str, str]
) -> None:
    """The first block on every page has the page's banner welded to its front.

    Taking the first match gave models like `A CLASS MOTORHOME RANGE K.YACHT 59`, which
    still matched their FMLV rows on token overlap — so the run looked almost right, with
    one product orphaned and three carrying nonsense as their model.
    """
    assert _range_and_model(heading) == expected


def test_kea_kompakt_is_not_read_as_kea() -> None:
    """The prefixes are ordered longest-first for exactly this."""
    assert RANGE_PREFIXES[0][0] == "KEA KOMPAKT"
    assert _range_and_model("KEA KOMPAKT 55") == ("KEA Kompakt", "55")
    assert _range_and_model("KEA 90") == ("KEA", "90")


def test_a_heading_with_no_known_range_yields_nothing() -> None:
    assert _range_and_model("KROSSER 12") is None


def test_every_model_is_the_bare_layout_code() -> None:
    models = {p.model for name in PAGES for p in _layouts(name)}

    assert models == {"59", "86", "90", "95", "K 6.3", "55"}


# --------------------------------------------------------------------------- #
# Everything one block yields
# --------------------------------------------------------------------------- #


def test_a_layout_yields_every_field() -> None:
    product = _by_model("mobilvetta_k_yacht.html")["59"]

    assert product.manufacturer_range == "K-YACHT TEKNO LINE"
    assert product.berths == 3
    assert product.mh_passenger_seats_inc_driver == 4
    assert product.mh_length_mm == 5990
    assert product.mh_width_mm == 2350
    assert product.mh_height_mm == 2950
    assert product.mtplm_kilograms == 4400
    assert product.mh_payload_kilograms == 1502
    assert product.rrp_pounds == 109_995


def test_belts_is_the_seat_count_and_berths_the_sleeping_count() -> None:
    """Named unambiguously here — unlike Pilote, where "Berth" meant a seat."""
    product = _by_model("mobilvetta_k_yacht.html")["59"]

    assert (product.berths, product.mh_passenger_seats_inc_driver) == (3, 4)


def test_every_layout_on_the_k_yacht_page_is_priced() -> None:
    """A fixed 700-character window after each heading lost two of these four.

    The price sits at the end of a block rather than beside the dimensions, so a block
    has to run to the next heading.
    """
    prices = {m: p.rrp_pounds for m, p in _by_model("mobilvetta_k_yacht.html").items()}

    assert prices == {"59": 109_995, "86": 119_995, "90": 119_995, "95": 118_995}


def test_the_offer_is_not_mistaken_for_a_price() -> None:
    """Three pages carry a stray £4,000, which is a discount rather than a vehicle."""
    assert "£4,000" in plain_text(_page("mobilvetta_k_yacht.html"))
    assert all(
        p.rrp_pounds is None or p.rrp_pounds > 50_000
        for name in PAGES
        for p in _layouts(name)
    )


def test_the_width_is_the_mirrors_folded_figure() -> None:
    assert "MIRRORS FOLDED" in plain_text(_page("mobilvetta_kea.html")).upper()
    assert _by_model("mobilvetta_kea.html")["90"].mh_width_mm == 2350


def test_the_mass_in_running_order_is_derived_and_says_so() -> None:
    """Marquis publish MTPLM and payload but no MIRO."""
    product = _by_model("mobilvetta_kea.html")["90"]

    assert product.mro_kilograms == product.mtplm_kilograms - product.mh_payload_kilograms
    snippet = _build_extracted_motorhome(product).provenance["mro_kilograms"].snippet
    assert "nothing on the page corroborates this" in snippet


def test_no_payload_means_no_derived_mass() -> None:
    product = replace(_by_model("mobilvetta_kea.html")["90"], mh_payload_kilograms=None)

    assert product.mro_kilograms is None


# --------------------------------------------------------------------------- #
# The check this source does not offer
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", sorted(PAGES))
def test_every_real_block_passes_the_completeness_check(name: str) -> None:
    for product in _layouts(name):
        reconciles, why_not = _reconciles(product)
        assert reconciles is True, f"{product.label}: {why_not}"


def test_a_block_with_a_heading_and_no_figures_is_dropped() -> None:
    """That means the page's shape changed under the parse, not that a vehicle is empty."""
    product = MobilvettaProduct(
        source_url="x", manufacturer_range="KEA", model="90"
    )

    reconciles, why_not = _reconciles(product)

    assert reconciles is False
    assert "shape has probably changed" in why_not


def test_the_expected_roster_size_is_pinned() -> None:
    """With no arithmetic check, a change in the count is the main warning available."""
    assert EXPECTED_LAYOUTS == 8


# --------------------------------------------------------------------------- #
# What reaches the reviewer
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("name", "model", "expected"),
    [
        ("mobilvetta_k_yacht.html", "59", BodyType.A_CLASS),
        ("mobilvetta_kea.html", "90", BodyType.COACH_BUILT_LOW_PROFILE),
        ("mobilvetta_kea_kompakt.html", "55", BodyType.COACH_BUILT_LOW_PROFILE),
        ("mobilvetta_admiral.html", "K 6.3", BodyType.CAMPERVAN_HIGH_TOP),
    ],
)
def test_the_body_type_follows_the_range(name: str, model: str, expected: BodyType) -> None:
    assert _by_model(name)[model].body_type is expected


def test_every_layout_is_a_fiat() -> None:
    extracted = _build_extracted_motorhome(_by_model("mobilvetta_admiral.html")["K 6.3"])

    assert extracted.motorhome.base_vehicle_manufacturer == BASE_VEHICLE == "Fiat"


def test_the_seat_provenance_explains_the_pages_own_word() -> None:
    snippet = _build_extracted_motorhome(
        _by_model("mobilvetta_k_yacht.html")["59"]
    ).provenance["mh_passenger_seats_inc_driver"].snippet

    assert "BELTS" in snippet
    assert "belted travel seat" in snippet


def test_the_price_names_marquis_as_the_seller_that_sets_it() -> None:
    snippet = _build_extracted_motorhome(
        _by_model("mobilvetta_k_yacht.html")["59"]
    ).provenance["rrp_pounds"].snippet

    assert "Marquis Leisure" in snippet


# --------------------------------------------------------------------------- #
# Wiring
# --------------------------------------------------------------------------- #


def test_the_adapter_is_registered_under_its_fmlv_name() -> None:
    assert adapter_for("Mobilvetta") is mobilvetta
