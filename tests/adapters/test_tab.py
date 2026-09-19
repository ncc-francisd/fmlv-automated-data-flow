"""T@B parsing, against the real pages captured in `fixtures/`.

Pure parsing only — no network and no HTML fetching. Every trap in the module docstring
that actually bit during the build has a test here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters import tab
from src.adapters.tab import (
    EUR_PER_GBP_RATE,
    EXPECTED_PRODUCTS,
    LAYOUTS,
    TabCaravan,
    _Layout,
    _reconciles,
    parse_headline_price,
    parse_load_increases,
    parse_styles,
    parse_technical_data,
    resolve_prices,
    standard_equipment,
    visible_lines,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _lines(name: str) -> list[str]:
    return (FIXTURES / name).read_text(encoding="utf-8").splitlines()


@pytest.fixture
def en_320() -> list[str]:
    return _lines("tab_320_en_text.txt")


@pytest.fixture
def en_400() -> list[str]:
    return _lines("tab_400_en_text.txt")


@pytest.fixture
def en_offroad() -> list[str]:
    return _lines("tab_320_offroad_en_text.txt")


# --- identity -----------------------------------------------------------------------


def test_the_manufacturer_is_the_export_spelling() -> None:
    """The join key back to FMLV's product ids. `T@B` alone is the display name and the
    NCC supplier name, but it is not what the export's `manufacturer` column holds."""
    assert tab.MANUFACTURER == "Knaus Tabbert AG T@B"
    assert tab.MANUFACTURER_DISPLAY_NAME == "T@B"


def test_five_products_across_three_pages() -> None:
    """Basic and Metropolis are styles sharing spec pages, not ranges of their own, so
    three specification tables serve five FMLV products."""
    assert sum(len(layout.styles) for layout in LAYOUTS) == EXPECTED_PRODUCTS
    assert len(LAYOUTS) == 3


def test_offroad_is_the_320_and_not_a_fourth_model() -> None:
    """FMLV holds it as range `Offroad`, model `320` — it has its own page only because
    the style carries the 1,000kg chassis, so its weights differ."""
    offroad = next(layout for layout in LAYOUTS if layout.slug == "320-offroad")

    assert offroad.model == "320"
    assert offroad.styles == ("Offroad",)


# --- the specification table --------------------------------------------------------


def test_the_320_table_reads_the_requesters_figures(en_320: list[str]) -> None:
    """The three weights the requester quoted on 2026-09-19, to the kilogram."""
    figures = parse_technical_data(en_320)

    assert figures.mro_kilograms == 653
    assert figures.mtplm_kilograms == 800
    assert figures.shipping_length_mm == 5170
    assert figures.overall_width_mm == 2010
    assert figures.height_mm == 2440
    assert figures.headroom_mm == 1820
    assert figures.berths == 2


def test_the_mro_is_the_middle_of_three_masses(en_320: list[str]) -> None:
    """`Mass of unladen vehicle` sits on the line directly above `Mass in ready to travel
    condition`. Reading the wrong one puts 620kg in `mro_kilograms` and everything still
    looks plausible."""
    figures = parse_technical_data(en_320)

    assert figures.unladen_kilograms == 620
    assert figures.mro_kilograms == 653
    assert figures.mro_kilograms != figures.unladen_kilograms


def test_the_summary_cards_mass_is_not_read(en_320: list[str]) -> None:
    """Above the table each page repeats length, width, beds and a bare `Mass`, and that
    `Mass` is the *unladen* figure. Scoping to `Technical data` is what excludes it — an
    unscoped read of the whole page takes 620."""
    assert "Mass" in en_320[: en_320.index("Technical data")]

    assert parse_technical_data(en_320).mro_kilograms == 653


def test_german_thousands_separators(en_400: list[str]) -> None:
    """The 400's MTPLM is published as `1.200`."""
    assert parse_technical_data(en_400).mtplm_kilograms == 1200


def test_the_offroad_is_taller_and_heavier(en_offroad: list[str]) -> None:
    """Same length as the 320 and 50mm taller, on the 1,000kg chassis."""
    figures = parse_technical_data(en_offroad)

    assert figures.shipping_length_mm == 5170
    assert figures.height_mm == 2490
    assert figures.mtplm_kilograms == 1000
    assert figures.mro_kilograms == 708


def test_a_paired_dimension_splits_into_overall_and_interior(en_320: list[str]) -> None:
    """`201 / 180` and `244 / 182` are overall then interior, in one cell each."""
    figures = parse_technical_data(en_320)

    assert (figures.overall_width_mm, figures.height_mm) == (2010, 2440)
    assert figures.headroom_mm == 1820


def test_berths_skip_the_up_to_line(en_320: list[str]) -> None:
    """`Number of beds` is followed by a bare `up to` before the figure, so a fixed
    offset of one reads the words instead of the number."""
    assert parse_technical_data(en_320).berths == 2


def test_a_page_without_a_table_yields_nothing() -> None:
    assert parse_technical_data(["Some marketing copy", "620"]).mro_kilograms is None


# --- payload ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("fixture", "published", "derived"),
    [
        ("tab_320_en_text.txt", 57, 147),
        ("tab_400_en_text.txt", 106, 214),
        ("tab_320_offroad_en_text.txt", 202, 292),
    ],
)
def test_the_published_payload_is_never_the_recorded_one(
    fixture: str, published: int, derived: int
) -> None:
    """The site's `Maximum payload` assumes full gas bottles and a full water tank, so it
    undershoots by 90kg on the 320. The recorded figure is MTPLM minus MRO — the requester
    gave 147 for the 320 directly, and the same trap is in `knaus.py` and `weinsberg.py`."""
    figures = parse_technical_data(_lines(fixture))
    product = TabCaravan(range_name="Basic", model="x", figures=figures)

    assert figures.published_payload_kilograms == published
    assert product.derived_payload_kilograms == derived


# --- the self-check -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("fixture", "mtplm", "optional"),
    [
        ("tab_320_en_text.txt", 800, [850, 1000]),
        ("tab_400_en_text.txt", 1200, [1500, 1300, 1400]),
        ("tab_320_offroad_en_text.txt", 1000, []),
    ],
)
def test_standard_load_increase_restates_the_mtplm(
    fixture: str, mtplm: int, optional: list[int]
) -> None:
    """The self-check, and it is real corroboration: the two figures sit in different
    sections of the page in different markup, hundreds of lines apart."""
    lines = _lines(fixture)
    standard, found_optional = parse_load_increases(lines)

    assert standard == [mtplm]
    assert found_optional == optional
    assert parse_technical_data(lines).mtplm_kilograms == mtplm


def test_the_optional_load_increases_are_not_the_vehicles_mass(en_320: list[str]) -> None:
    """The 320 can be ordered on an 850 or 1,000kg chassis. Both are paid options, so the
    base vehicle stays 800 — reading them would put an optioned figure in `mtplm`."""
    standard, optional = parse_load_increases(en_320)

    assert standard == [800]
    assert 1000 in optional


def test_mixed_separators_on_one_page(en_320: list[str]) -> None:
    """The table and standard equipment use German dots while the optional lines use
    English commas — `Load increase to 1,000 kg` on the same page as `1.200`."""
    _standard, optional = parse_load_increases(en_320)

    assert 1000 in optional


def test_a_disagreeing_load_increase_drops_the_product() -> None:
    """A page whose two MTPLM statements differ has been misread, so nothing is proposed."""
    figures = parse_technical_data(_lines("tab_320_en_text.txt"))
    product = TabCaravan(range_name="Basic", model="320", figures=figures)

    assert _reconciles(product, [800])[0] is True
    assert _reconciles(product, [850])[0] is False
    assert _reconciles(product, [])[0] is False


# --- prices -------------------------------------------------------------------------


def test_the_english_page_carries_no_headline_price(en_400: list[str]) -> None:
    """The whole reason the German page is fetched at all. The English edition has only
    the style panel, and on the 400 that panel is stale."""
    assert parse_headline_price(en_400) is None


def test_the_german_pages_carry_the_headline() -> None:
    assert parse_headline_price(_lines("tab_320_de_text.txt")) == 14990
    assert parse_headline_price(_lines("tab_400_de_text.txt")) == 24390
    assert parse_headline_price(_lines("tab_320_offroad_de_text.txt")) == 18490


def test_the_320_style_panel(en_320: list[str]) -> None:
    assert parse_styles(en_320) == [
        ("Basic", 14990),
        ("Metropolis", 16380),
        ("Offroad", 18490),
    ]


def test_the_offroad_page_has_no_style_panel(en_offroad: list[str]) -> None:
    assert parse_styles(en_offroad) == []


def test_an_agreeing_panel_prices_every_style(en_320: list[str]) -> None:
    """The 320's panel says BASIC 14.990 and so does its headline, so the panel is trusted
    and Metropolis gets its own price rather than the base one."""
    layout = _Layout("320", "320", ("Basic", "Metropolis"))

    prices = resolve_prices(layout, parse_styles(en_320), 14990)

    assert prices.by_style == {"Basic": 14990, "Metropolis": 16380}
    assert prices.note is None


def test_a_stale_panel_is_rejected_whole(en_400: list[str]) -> None:
    """The 400's panel prices BASIC at 13.990 against its own headline of 24.390 — 74%
    under, and under the *smaller* 320 at that. FMLV's GBP 24,970 sides with the headline.

    The panel is discarded entirely rather than half-trusted, so Metropolis 400 gets no
    price at all instead of a figure from a document already shown to be wrong."""
    layout = _Layout("400", "400", ("Basic", "Metropolis"))

    prices = resolve_prices(layout, parse_styles(en_400), 24390)

    assert prices.by_style == {"Basic": 24390}
    assert "Metropolis" not in prices.by_style
    assert prices.note is not None
    assert "REJECTED" in prices.note


def test_a_page_with_no_panel_prices_its_one_style(en_offroad: list[str]) -> None:
    layout = _Layout("320-offroad", "320", ("Offroad",))

    prices = resolve_prices(layout, parse_styles(en_offroad), 18490)

    assert prices.by_style == {"Offroad": 18490}
    assert prices.note is None


def test_offroads_price_is_corroborated_twice(en_320: list[str]) -> None:
    """The one product with two independent price statements: the 320 panel's OFFROAD
    entry, and the 320-offroad page's own headline."""
    panel = dict(parse_styles(en_320))

    assert panel["Offroad"] == parse_headline_price(_lines("tab_320_offroad_de_text.txt"))


def test_euros_are_divided_by_the_rate() -> None:
    """1.15 is euros per pound, so it divides. Multiplying gives GBP 17,239 for the 320,
    which is above its euro price and obviously wrong — the direction matters."""
    figures = parse_technical_data(_lines("tab_320_en_text.txt"))
    product = TabCaravan(range_name="Basic", model="320", figures=figures, price_eur=14990)

    assert EUR_PER_GBP_RATE == 1.15
    assert product.rrp_pounds == 13035


def test_no_price_means_no_price() -> None:
    figures = parse_technical_data(_lines("tab_400_en_text.txt"))

    assert TabCaravan(range_name="Metropolis", model="400", figures=figures).rrp_pounds is None


# --- equipment ----------------------------------------------------------------------


def test_standard_equipment_stops_before_the_optional_list(en_400: list[str]) -> None:
    """Scoped deliberately: the 400's optional list offers a Truma air conditioner and a
    larger refrigerator, and reading both sections as one reports kit it does not have."""
    equipment = standard_equipment(en_400)

    assert equipment
    assert any("Gas heating" in line for line in equipment)
    assert not any("Load increase to 1,500" in line for line in equipment)


def test_the_320_has_no_refrigerator_as_standard(en_320: list[str]) -> None:
    """Its standard equipment says `Storage cabinet instead of refrigerator` — the base
    320 genuinely ships without one, which is why nothing is asserted for it."""
    equipment = standard_equipment(en_320)

    assert any("instead of refrigerator" in line for line in equipment)


# --- the line split -----------------------------------------------------------------


def test_visible_lines_puts_each_value_on_its_own_line() -> None:
    """Every figure on this site sits below its label rather than beside it, which is what
    makes the label-then-value parse possible. The site builds its table from divs, so
    each cell becomes its own line."""
    html = "<div>Overall length in cm</div><div>517</div>"

    assert visible_lines(html) == ["Overall length in cm", "517"]


def test_a_real_table_row_keeps_its_cells_together() -> None:
    """The limit of the split, stated so nobody assumes otherwise: `td` is not a block tag
    here, so a genuine table cell pair stays on one line. Nothing on tabme.de is built
    that way, and `value_after` would not find the figure if it were."""
    html = "<table><tr><td>Overall length in cm</td><td>517</td></tr></table>"

    assert visible_lines(html) == ["Overall length in cm 517"]


def test_scripts_are_dropped() -> None:
    assert visible_lines("<script>var x = 620;</script><p>653</p>") == ["653"]
