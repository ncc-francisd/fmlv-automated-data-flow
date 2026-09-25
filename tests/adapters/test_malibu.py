"""Malibu parsing, against real pages captured in `fixtures/`.

Pure parsing only — no network. Each fixture was chosen for what it breaks: the I 430 is
an ordinary motorhome, the **T 490** is a page whose table has slipped a row, the van
publishes no berth count at all, and the Genius writes `Max. numbers of seats` where
everything else is singular.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters import malibu
from src.adapters.malibu import (
    EXPECTED_PRODUCTS,
    hero_berths,
    RANGES,
    MalibuProduct,
    _mass,
    _reconciles,
    build_extracted,
    chassis_from,
    lap_belt_warning,
    model_name,
    parse_running_order,
    parse_technical_data,
    prices_from,
    range_for,
    roster_from,
    visible_lines,
)
from src.product_model.enums import BodyType

FIXTURES = Path(__file__).parent / "fixtures"


def _lines(name: str) -> list[str]:
    return (FIXTURES / f"malibu_{name}_text.txt").read_text(encoding="utf-8").splitlines()


def _range(name: str):
    return next(r for r in RANGES if r.fmlv_range == name)


def _product(
    fixture: str, range_name: str, chassis: str | None = "Fiat", hero: int | None = None
) -> MalibuProduct:
    lines = _lines(fixture)
    config = _range(range_name)
    return MalibuProduct(
        config=range_for(lines[0], config),
        url="https://www.malibu-carthago.com/x",
        model=model_name(lines[0], config),
        chassis=chassis,
        rrp_pounds=None,
        hero_berths=hero,
        fields=parse_technical_data(lines),
        lines=lines,
    )


# --- identity and roster --------------------------------------------------------------


def test_the_manufacturer_is_one_word_in_both_roles() -> None:
    assert malibu.MANUFACTURER == "Malibu"
    assert malibu.MANUFACTURER_DISPLAY_NAME == "Malibu"


def test_ten_ranges_and_the_expected_product_count() -> None:
    assert len(RANGES) == 10
    assert EXPECTED_PRODUCTS == 47


def test_the_roster_finds_products_at_the_site_root_too() -> None:
    """**About half the A-Class products sit under the range path and half at the site root.**
    A reader scoped to the range path finds only its half and reports the range as
    halved."""
    page = (FIXTURES / "malibu_a_class_range.html").read_text(encoding="utf-8")

    links = roster_from(page, _range("A-Class"))

    under = [x for x in links if x.startswith("/en/motorhome/")]
    at_root = [x for x in links if not x.startswith("/en/motorhome/")]
    # Nine of each in this capture; the live page carries nineteen.
    assert len(under) == 9
    assert len(at_root) == 9


def test_the_range_comes_from_the_name_not_the_page() -> None:
    """Every motorhome page lists the same 28 products, so the page proves nothing. Only
    two products are Edition +, and Malibu say so in their names."""
    a_class = _range("A-Class")

    assert range_for("Malibu I 430 KB-LE comfort 4.2 t", a_class).fmlv_range == "A-Class"
    assert range_for("Malibu T 430 KB-LE comfort 4.2 t", a_class).fmlv_range == "Coachbuilt"
    assert (
        range_for("Malibu Edition + I 490 RB-LE comfort", a_class).fmlv_range
        == "A-Class Edition +"
    )
    assert (
        range_for("Malibu Edition + T 490 RB-LE comfort", a_class).fmlv_range
        == "Coachbuilt Edition +"
    )


def test_a_van_range_is_never_reassigned() -> None:
    assert range_for("Malibu Van compact 540 DB", _range("Van Compact")).fmlv_range == (
        "Van Compact"
    )


# --- the model name -------------------------------------------------------------------


def test_the_model_is_written_the_way_fmlv_writes_it() -> None:
    """`I430`, not `I 430`; the trim word kept because lightweight and comfort are two
    models; the weight class dropped so the name still matches the row it extends."""
    config = _range("A-Class")

    assert model_name("Malibu I 430 KB-LE comfort 4.2 t - Malibu Vans", config) == (
        "I430 KB-LE comfort"
    )
    assert model_name("Malibu I 470 RB-LE “K” lightweight 3.5 t", config) == (
        "I470 RB-LE K lightweight"
    )


def test_the_edition_prefix_is_not_part_of_the_model() -> None:
    """It is the range. `Malibu Edition + T 490 RB-LE comfort` is `T490 RB-LE comfort`."""
    assert model_name("Malibu Edition + T 490 RB-LE comfort 4.2 t", _range("Coachbuilt")) == (
        "T490 RB-LE comfort"
    )


def test_a_van_model_is_just_its_code() -> None:
    title = "Malibu Van compact 540 DB - Malibu Wohnmobile & Vans"

    assert model_name(title, _range("Van Compact")) == "540 DB"


def test_the_chassis_survives_malibus_own_typo() -> None:
    """One slug reads `fiat-duacto`. Matching `ducato` alone loses that product's chassis
    and leaves it indistinguishable from its Mercedes sibling."""
    assert chassis_from("malibu-i-441-le-lightweight-fiat-duacto") == "Fiat"
    assert chassis_from("malibu-i-430-kb-le-comfort-fiat-ducato") == "Fiat"
    assert chassis_from("malibu-i-430-kb-le-comfort-mercedes-benz") == "Mercedes"


# --- the technical block ---------------------------------------------------------------


def test_the_labels_are_matched_as_patterns() -> None:
    """Malibu write the gross weight as `Tech. permissible…` on most pages and
    `Technically permissible…` on others. Exact-matching one dropped 30 of 47 products."""
    fields = parse_technical_data(_lines("i430_fiat"))

    assert fields["base_vehicle"] == "Fiat Ducato"
    assert fields["length"] == "6850"
    assert fields["mtplm"] == "4250"
    assert fields["mro"].startswith("3.013")


def test_a_product_reads_every_field() -> None:
    product = _product("i430_fiat", "A-Class")

    assert product.model == "I430 KB-LE comfort"
    assert product.mtplm_kilograms == 4250
    assert product.mro_kilograms == 3013
    assert product.derived_payload_kilograms == 4250 - 3013
    assert product.berths == 4
    assert product.travel_seats == 4


def test_the_published_tolerance_band_is_the_self_check() -> None:
    assert parse_running_order("3.013 (2.862 - 3.164)") == (3013, (2862, 3164))

    ok, reason = _reconciles(_product("i430_fiat", "A-Class"))

    assert ok is True
    assert "brackets it exactly" in reason


# --- the page whose table slipped a row -------------------------------------------------


def test_a_door_opening_is_not_a_mass() -> None:
    """**Two Coachbuilt Edition + pages print `1050 x 1140` under the gross-weight
    label** — a rear-garage door, because their table has slipped a row."""
    assert _mass("1050 x 1140") is None
    assert _mass("4250") == 4250
    assert _mass("999") is None
    assert _mass(None) is None


def test_the_slipped_page_keeps_its_product_and_loses_only_that_mass() -> None:
    """Dropping it would have made two live FMLV rows look discontinued. Everything else
    on the page reads normally, so the product is kept and the mass withheld."""
    product = _product("t490_slipped", "Coachbuilt")

    assert product.mtplm_kilograms is None
    assert product.mro_kilograms == 3113
    assert product.derived_payload_kilograms is None

    ok, reason = _reconciles(product)
    assert ok is True
    assert "NO GROSS WEIGHT IS PROPOSED" in reason

    extracted = build_extracted(product, mass_basis=reason)
    assert "mtplm_kilograms" not in extracted.provenance
    assert "mh_payload_kilograms" not in extracted.provenance
    assert extracted.motorhome.mh_length_mm == 7345


def test_a_gross_weight_below_the_running_order_is_refused() -> None:
    """The check the first pass lacked: it only tested the band, which was self-consistent
    while the gross weight was a door opening."""
    product = _product("i430_fiat", "A-Class")
    broken = MalibuProduct(
        config=product.config,
        url=product.url,
        model=product.model,
        chassis=product.chassis,
        rrp_pounds=None,
        hero_berths=None,
        fields={**product.fields, "mtplm": "2000"},
        lines=product.lines,
    )

    ok, reason = _reconciles(broken)

    assert ok is False
    assert "impossible" in reason


# --- vans and the Genius -----------------------------------------------------------------


def test_a_van_states_no_berth_count_of_its_own() -> None:
    """A van's vehicle-data table has no sleeping-places row at all. Its range hero says
    `up to 4`, which is an upper bound needing the optional pop-up roof, so nothing is
    recorded and FMLV's 2 stands."""
    van = _product("van_compact_540", "Van Compact")

    assert van.model == "540 DB"
    assert van.berths is None
    assert van.travel_seats == 4
    assert van.mro_kilograms == 2735


def test_the_genius_writes_seats_in_the_plural() -> None:
    """`Max. numbers of seats` on that page alone; everything else is singular."""
    genius = _product("genius_641", "Genius", chassis="Mercedes")

    assert genius.travel_seats == 4
    assert genius.model == "641 LE"


def test_a_van_is_a_high_top_campervan() -> None:
    extracted = build_extracted(_product("van_compact_540", "Van Compact"), mass_basis="")

    assert extracted.motorhome.body_type is BodyType.CAMPERVAN_HIGH_TOP


def test_a_motorhome_takes_its_range_body_type() -> None:
    assert (
        build_extracted(_product("i430_fiat", "A-Class"), mass_basis="").motorhome.body_type
        is BodyType.A_CLASS
    )


# --- the seat label ----------------------------------------------------------------------


def test_the_two_point_label_alone_raises_no_warning() -> None:
    """It is boilerplate on every motorhome page. Warning on it would warn on everything."""
    assert lap_belt_warning(_lines("i430_fiat")) is None


def test_a_page_that_really_names_a_lap_belt_does() -> None:
    """The guard that keeps the reading honest: the day Malibu fit one and say so, the run
    says so rather than counting it as a travel seat."""
    warning = lap_belt_warning(
        ["Rear bench with a 2-point lap belt for the centre seat", "Heating system"]
    )

    assert warning is not None
    assert "lap belt" in warning


# --- prices -------------------------------------------------------------------------------


def test_prices_are_read_from_the_range_card() -> None:
    """`ab` / `92.170` / `GBP` across three runs of text — a dot for thousands and the
    currency as a word, so searching for a pound sign finds only the range's headline."""
    page = (FIXTURES / "malibu_a_class_range.html").read_text(encoding="utf-8")

    found = prices_from(visible_lines(page))

    assert found["Malibu I 430 KB-LE lightweight 3.5 t"] == 92_170
    assert found["Malibu I 430 KB-LE comfort 4.2 t"] == 101_480


# --- the range hero, which is where a van's berth figure lives ---------------------------


def test_an_upper_bound_is_not_a_berth_count() -> None:
    """`up to 4` on every van range, beside `Optional: Pop-up roof family-for-4`. The
    settled rule takes the lower figure of a range, and these pages never state it."""
    berths, raw = hero_berths(["up to 4", "sleeping berths"])

    assert berths is None
    assert raw == "up to 4"


def test_a_definite_hero_figure_is_recorded() -> None:
    """The Genius states a bare `2` and mentions no pop-up roof anywhere."""
    assert hero_berths(["2", "Lengthways single beds"]) == (2, "2")


def test_a_page_with_no_hero_figure_yields_nothing() -> None:
    assert hero_berths(["Gross vehicle weight", "from 3.5 t"]) == (None, None)
