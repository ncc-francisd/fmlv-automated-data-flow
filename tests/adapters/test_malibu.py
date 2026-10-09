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
    PERFORMANCE_4X4,
    hero_berths,
    RANGES,
    berths_from_beds,
    van_prices_from,
    MalibuProduct,
    _mass,
    _reconciles,
    build_extracted,
    chassis_from,
    lap_belt_warning,
    model_name,
    parse_running_order,
    parse_technical_data,
    normalised_title,
    price_for,
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


def test_eleven_ranges_and_the_expected_product_count() -> None:
    """Eleven since 9 October 2026: the Genius performance 4x4 has a page of its own.

    `/en/malibu-genius/` lists only the 641 LE, so the 4x4's product page was reachable
    from nowhere the adapter looked — and FMLV's 8573 was reported disappeared on every
    run from #135 on.
    """
    assert len(RANGES) == 11
    assert EXPECTED_PRODUCTS == 49
    assert any(PERFORMANCE_4X4 in config.path for config in RANGES)


def test_the_roster_finds_products_at_the_site_root_too() -> None:
    """**About half the A-Class products sit under the range path and half at the site root.**
    A reader scoped to the range path finds only its half and reports the range as
    halved."""
    page = (FIXTURES / "malibu_a_class_range.html").read_text(encoding="utf-8")

    links = roster_from(page, _range("A-Class"))

    under = [x for x in links if x.startswith("/en/motorhome/")]
    at_root = [x for x in links if not x.startswith("/en/motorhome/")]
    # Nine of each in this capture; the live page carries nineteen. The tenth under the
    # range path is a `-2` slug, which `roster_from` no longer drops — two pages for one
    # vehicle are now collapsed in `collect`, on the name read from the page.
    assert len(under) == 10
    assert len(at_root) == 9
    assert sum(1 for x in links if x.rstrip("/").endswith("-2")) == 1


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


def test_a_van_counts_its_berths_from_its_bed_rows() -> None:
    """A van's table has no sleeping-places row, but it does state its beds.

    It used to fall through to the range hero's `up to 4` and record nothing. The
    requester's rule of 9 October 2026 reads the beds instead: a fixed double is two
    berths, and a bed marked as needing special equipment is not counted at all.
    """
    van = _product("van_compact_540", "Van Compact")

    assert van.model == "540 DB"
    assert van.berths == 2
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


def test_prices_are_keyed_on_length_because_titles_collide() -> None:
    """**Malibu print the Fiat and the Mercedes build of a layout under one name.** Two
    cards both headed `I 470 RB-LE "K" lightweight 3.5 t`, one 717.5 cm at GBP97,300 and
    one 728 cm at GBP110,390. Keyed on the title alone the second is discarded, and three
    products came through with no price while two were given their sibling's."""
    page = (FIXTURES / "malibu_a_class_range.html").read_text(encoding="utf-8")

    found = prices_from(visible_lines(page))

    i470 = {
        length: value
        for (name, length), value in found.items()
        if "470" in name and "lightweight" in name
    }
    assert i470 == {7175: 97_300, 7280: 110_390}


def test_a_card_and_its_product_page_quote_and_dash_differently() -> None:
    """The cards use curly quotes and an en dash; the product titles use straight quotes
    and a hyphen. Either difference alone loses the price."""
    assert normalised_title('Malibu I 470 RB-LE “K” lightweight') == (
        normalised_title('Malibu I 470 RB-LE "K" lightweight')
    )
    assert normalised_title("Van first class – two rooms") == (
        normalised_title("Van first class - two rooms")
    )


def test_the_right_price_reaches_the_right_chassis() -> None:
    page = (FIXTURES / "malibu_a_class_range.html").read_text(encoding="utf-8")
    prices = prices_from(visible_lines(page))
    title = 'Malibu I 470 RB-LE "K" lightweight 3.5 t'

    assert price_for(prices, title, 7175) == 97_300
    assert price_for(prices, title, 7280) == 110_390


def test_a_title_carried_once_needs_no_length() -> None:
    """The vans carry a name once each, so a product whose length could not be read still
    finds its price. Every motorhome name is a chassis pair, so none falls back."""
    assert price_for({("Malibu Van compact 540 DB", 5410): 59_100}, "Malibu Van compact 540 DB", None) == 59_100


def test_a_shared_title_with_no_length_finds_nothing() -> None:
    """Better none than the wrong chassis's price."""
    prices = {
        ("Malibu I 470 lightweight", 7175): 97_300,
        ("Malibu I 470 lightweight", 7280): 110_390,
    }

    assert price_for(prices, "Malibu I 470 lightweight", None) is None


# --- the two vans that were being missed -------------------------------------------------
#
# Both found by the requester on 9 October 2026, who noticed two Genius vans and two Relax
# vans on the site where the run produced one of each.


def test_the_van_pattern_allows_a_digit_in_the_slug() -> None:
    """`4x4` has a digit in the middle, and the pattern used to allow only letters there.

    So `/en/camper-vans/malibu-genius-performance-4x4-641-le/` never matched, and FMLV's
    8573 was reported disappeared on every run.
    """
    page = (
        '<a href="/en/camper-vans/malibu-genius-performance-4x4-641-le/">4x4</a>'
        '<a href="/en/camper-van/genius-641-le/">standard</a>'
    )
    links = roster_from(page, _range("Genius"))
    assert "/en/camper-vans/malibu-genius-performance-4x4-641-le/" in links
    assert "/en/camper-van/genius-641-le/" in links


def test_a_dash_two_slug_is_no_longer_dropped_by_the_roster() -> None:
    """It was, as a duplicate — and `relax-640-le-r-2` is now the 640 LE **XR**."""
    page = (
        '<a href="/en/camper-vans/crelax-camper-van/relax-640-le-r/">R</a>'
        '<a href="/en/camper-vans/crelax-camper-van/relax-640-le-r-2/">XR</a>'
    )
    assert len(roster_from(page, _range("Van Relax"))) == 2


# --- the van price card, and the berths it does not state ---------------------------------
#
# Both found by the requester on 9 October 2026, reading the page himself after the run
# reported no price and no berths for every van.


_VAN_CARD = (
    '<h3>Malibu relax 640 LE XR</h3>'
    '<div class="elementor-widget-container" data-widget_type="fahrzeug_eigenschaften.default">'
    '<div class="wrapper"><div class="eigenschaft">Total length</div>'
    '<div class="wert">6,355 m</div></div>'
    '<div class="wrapper"><div class="eigenschaft">Gross weight</div>'
    '<div class="wert">3,5 - 4 t</div></div>'
    '<div class="wrapper"><div class="eigenschaft">Price</div>'
    '<div class="wert">58.930 £</div></div></div>'
)


def test_a_van_card_is_read_from_its_own_widget() -> None:
    """The van pages price in `58.930 £`, not `GBP`, and in markup the text reader never
    reaches — 497 visible lines come back from a 979KB page, so every van had no price."""
    prices = van_prices_from(_VAN_CARD)
    assert ("Malibu relax 640 LE XR", 6355) in prices
    assert prices[("Malibu relax 640 LE XR", 6355)] == 58930


def test_a_dot_is_a_thousands_separator_not_a_decimal() -> None:
    """`58.930 £` is fifty-eight thousand, not fifty-eight."""
    assert next(iter(van_prices_from(_VAN_CARD).values())) == 58930


def test_a_multiplication_sign_does_not_lose_a_price() -> None:
    """The 4x4's card reads `4×4` and its product page `4x4`."""
    assert normalised_title("Malibu genius performance 4\u00d74 641 LE") == (
        "Malibu genius performance 4x4 641 LE"
    )


def test_the_same_words_in_a_different_order_still_match() -> None:
    """`genius performance 4x4 641 LE` on the card, `genius 641 LE performance 4x4` built."""
    prices = {("Malibu genius performance 4x4 641 LE", None): 133630}
    assert price_for(prices, "Malibu genius 641 LE performance 4x4", None) == 133630


def test_an_ambiguous_token_match_returns_nothing() -> None:
    """The fallback only fires where exactly one card matches on its words."""
    prices = {("B A", None): 1, ("A B  ", None): 2}
    assert price_for(prices, "A B C", None) is None
    assert price_for(prices, "A  B", None) is None


def test_an_asterisked_bed_is_not_a_berth() -> None:
    """The requester's rule: a bed needing special equipment is not standard.

    Relax 640 LE XR — a fixed rear double at `2020 x 900 / 1890 x 1020`, and a seating
    conversion at `1600 x 1145***` whose footnote reads "in conjunction with special
    equipment". Two berths, not four.
    """
    berths, reason = berths_from_beds(
        {"bed_fixed": "2020 x 900 / 1890 x 1020", "bed_conversion": "1600 x 1145***"}
    )
    assert berths == 2
    assert "special equipment" in reason


def test_two_unmarked_beds_are_four_berths() -> None:
    berths, _ = berths_from_beds(
        {"bed_fixed": "2020 x 900", "bed_conversion": "1600 x 1145"}
    )
    assert berths == 4


def test_no_bed_at_all_proposes_nothing() -> None:
    """Silence stays silence — FMLV's own figure is left alone."""
    assert berths_from_beds({})[0] is None
    assert berths_from_beds({"bed_conversion": "1600 x 1145**"})[0] is None
