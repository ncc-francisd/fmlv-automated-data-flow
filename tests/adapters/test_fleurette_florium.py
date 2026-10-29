"""Fleurette and Florium: the shared catalogue reader and the two brands over it.

Pure parsing only — the fixtures are the catalogue's technical spread as
`fetch.pdf.extract_text` renders it, saved on 29 October 2026. Pages 38–41 are the
motorhome table and its equipment; 42–44 are the vans'.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.adapters import fleurette, fleurette_florium as shared, florium
from src.adapters import ADAPTERS
from src.product_model.enums import BodyType, Heating, Refrigeration
from src.vehicle_class import VehicleClass

FIXTURES = Path(__file__).parent / "fixtures"


def _pages() -> list[str]:
    """The catalogue's technical spread, page 38 first, as `collect_columns` sees it."""
    return [
        (FIXTURES / f"fleurette_catalogue_p{number}.txt").read_text(encoding="utf-8")
        for number in range(38, 45)
    ]


@pytest.fixture(scope="module")
def columns() -> tuple[tuple[shared.Column, ...], tuple[shared.Column, ...]]:
    pages = _pages()
    shared_at, shared_lengths = shared.find_table_page(pages, shared.SHARED_CODES)
    van_at, van_lengths = shared.find_table_page(pages, shared.BLACK_PEARL_CODES)
    coachbuilts = shared.read_table(
        pages[shared_at].splitlines(),
        shared.SHARED_CODES,
        shared_lengths,
        [line for page in pages[shared_at:van_at] for line in page.splitlines()],
        on_progress=lambda message: None,
        what="motorhome",
    )
    vans = shared.read_table(
        pages[van_at].splitlines(),
        shared.BLACK_PEARL_CODES,
        van_lengths,
        [line for page in pages[van_at:] for line in page.splitlines()],
        on_progress=lambda message: None,
        what="van",
    )
    placed = tuple(
        c.__class__(**{**c.__dict__, "body_type": shared.SHARED_RANGE_AT[i][2]})
        for i, c in enumerate(coachbuilts)
    )
    return placed, vans


def _by_code(columns: tuple[shared.Column, ...]) -> dict[str, shared.Column]:
    return {column.code: column for column in columns}


# --- Registry wiring -----------------------------------------------------------------


def test_both_brands_register_under_one_manufacturer():
    """The Swift arrangement: one manufacturer, two display names, two entries."""
    assert fleurette.MANUFACTURER == florium.MANUFACTURER == "Fleurette Constructeur"
    assert ("Fleurette Constructeur", "Fleurette", VehicleClass.MOTORHOME) in ADAPTERS
    assert ("Fleurette Constructeur", "Florium", VehicleClass.MOTORHOME) in ADAPTERS


def test_the_registry_row_names_the_manufacturer_the_export_holds():
    """`Fleurette Constructeur`, read off FMLV product 9214 on 28 October 2026.

    Getting this wrong finds an empty baseline and proposes every product as new — which
    on a brand new manufacturer looks exactly like a correct first run, so nothing would
    catch it until the duplicates appeared.
    """
    registry = (Path("config") / "manufacturers.csv").read_text(encoding="utf-8-sig")
    assert registry.count("9001,Fleurette Constructeur,Fleurette,Fleurette,") == 1
    assert registry.count("9002,Fleurette Constructeur,Florium,Florium,") == 1


# --- The roster ----------------------------------------------------------------------


def test_thirteen_shared_layouts_and_four_vans():
    assert len(shared.SHARED_CODES) == 13
    assert len(shared.BLACK_PEARL_CODES) == 4
    assert fleurette.EXPECTED_LAYOUTS == 13
    assert florium.EXPECTED_LAYOUTS == 17


def test_a_layout_code_is_unique_within_its_table():
    """`collect` looks a column's range up by `SHARED_CODES.index`, which needs this."""
    assert len(set(shared.SHARED_CODES)) == len(shared.SHARED_CODES)
    assert len(set(shared.BLACK_PEARL_CODES)) == len(shared.BLACK_PEARL_CODES)


def test_the_same_layout_code_serves_both_brands():
    """`70LMF` is a Magister *and* a Mayflower — the collision the survey warned about.

    Twelve of the thirteen codes are used twice. Keying on the code alone would collapse
    thirty products into seventeen, which is what halved the Malibu roster.
    """
    index = shared.SHARED_CODES.index("70LMF")
    assert shared.SHARED_RANGE_AT[index][:2] == ("Magister", "Mayflower")


def test_range_and_model_stay_unique_across_all_thirty():
    """What saves it: the range names differ even where the codes do not."""
    identities = {("Fleurette", r, c) for (r, c) in fleurette.PRICES}
    identities |= {("Florium", r, c) for (r, c) in florium.PRICES}
    assert len(identities) == 30


def test_every_layout_is_priced():
    """Thirteen and seventeen, with nothing relying on a lookup that quietly misses."""
    assert len(fleurette.PRICES) == 13
    assert len(florium.PRICES) == 17
    for code in shared.SHARED_CODES:
        index = shared.SHARED_CODES.index(code)
        assert (shared.SHARED_RANGE_AT[index][0], code) in fleurette.PRICES
        assert (shared.SHARED_RANGE_AT[index][1], code) in florium.PRICES


# --- `Wellness` ----------------------------------------------------------------------


def test_wellness_is_not_part_of_any_range_or_model_name():
    """The catalogue's contents page advertises it as a *gamme*; the data says otherwise.

    The technical table files every layout under the four paired names and the price list
    heads its blocks Migrateur / Magister / Discover, so the two documents that carry
    figures agree. A word that might later be dropped would churn the identity key.
    """
    names = [n for pair in shared.RANGE_PAIRS for n in pair[:2]] + ["Black Pearl"]
    assert not any("Wellness" in name for name in names)
    assert not any("Wellness" in code for code in shared.SHARED_CODES)


def test_wellness_is_what_makes_six_fleurette_layouts_dearer():
    """And where neither brand fits it, the twins are priced to the pound identically."""
    same = [("60LG", 68690), ("64LDF", 70990), ("67LO", 74390)]
    for code, price in same:
        index = shared.SHARED_CODES.index(code)
        left, right, _body = shared.SHARED_RANGE_AT[index]
        assert fleurette.PRICES[(left, code)] == price
        assert florium.PRICES[(right, code)] == price

    dearer = [("69LJG", 2000), ("70LMF", 3300), ("74LMF", 3800)]
    for code, gap in dearer:
        index = shared.SHARED_CODES.index(code)
        left, right, _body = shared.SHARED_RANGE_AT[index]
        assert fleurette.PRICES[(left, code)] - florium.PRICES[(right, code)] == gap


# --- Splitting a row -----------------------------------------------------------------


def test_the_length_row_reads_as_thirteen_values():
    line = (
        "Longueur hors tout* 5,99 6,47 6,99 6,77 6,97 6,97 7,38 7,30 7,30 "
        "7,19 7,19 7,49 7,49"
    )
    assert shared.split_row(line, "Longueur hors tout", 13, value=shared.METRES_VALUE) == (
        "5,99", "6,47", "6,99", "6,77", "6,97", "6,97", "7,38",
        "7,30", "7,30", "7,19", "7,19", "7,49", "7,49",
    )


def test_a_decimal_split_by_kerning_is_closed_before_counting():
    """`7,19` extracts as `7,1 9` — fifteen tokens for thirteen columns, left alone."""
    line = "Longueur hors tout* 5,99 6,47 6,99 6,77 6,97 6,97 7,38 7,30 7,30 7,1 9 7,1 9 7,4 9 7,4 9"
    values = shared.split_row(line, "Longueur hors tout", 13, value=shared.METRES_VALUE)
    assert values is not None
    assert values[-4:] == ("7,19", "7,19", "7,49", "7,49")


def test_a_label_qualifier_holding_numbers_is_not_read_as_a_value():
    """`(jantes 15'' … jantes 16'' …)` would otherwise supply the first two columns."""
    line = (
        "Hauteur hors tout (jantes 15'' Profil�s et jantes 16'' Int�graux de "
        "s�rie)* 2,70 2,70 2,70 2,82 2,82 2,82 2,82 2,92 2,92 2,88 2,88 2,88 2,88"
    )
    values = shared.split_row(line, "Hauteur hors tout", 13, value=shared.METRES_VALUE)
    assert values is not None
    assert values[0] == "2,70" and values[-1] == "2,88"


def test_a_row_that_lost_a_cell_is_rejected():
    line = "Longueur hors tout* 6,47 6,99 6,77 6,97 6,97 7,38 7,30 7,30 7,19 7,19 7,49 7,49"
    assert shared.split_row(line, "Longueur hors tout", 13, value=shared.METRES_VALUE) is None


def test_a_row_that_gained_a_cell_is_rejected():
    """The one taking from the end would otherwise shift every vehicle left a place."""
    line = (
        "Longueur hors tout* 9,99 5,99 6,47 6,99 6,77 6,97 6,97 7,38 7,30 7,30 "
        "7,19 7,19 7,49 7,49"
    )
    assert shared.split_row(line, "Longueur hors tout", 13, value=shared.METRES_VALUE) is None


def test_the_optional_berth_is_not_counted():
    """`3 (S) /4 (O)` is three berths standard — and four tokens for one column."""
    line = "Places couchage 3 3 3 4 4 4 3 (S) /4 (O) 4 4 4 4 4 4"
    values = shared.split_row(line, "Places couchage", 13, value=shared.BERTHS_VALUE)
    assert values is not None
    assert values[6] == "3"


def test_the_vans_optional_berth_is_written_differently_and_still_not_counted():
    line = "Places couchage 2/3 (O) 2/3 (O) 2/3 (O) 3/4 (O)"
    assert shared.split_row(line, "Places couchage", 4, value=shared.BERTHS_VALUE) == (
        "2", "2", "2", "3",
    )


# --- Seats ---------------------------------------------------------------------------


def test_the_whole_wrapped_seats_row_is_read_in_column_order():
    """Every cell, not just the run before the first band.

    The bands wrap onto lines of their own and the label's own `configuration` sits
    before any digit, so the region reads cleanly end to end. This is the real page 38
    row, rejoined.
    """
    region = (
        "Places carte grise et nombre de ceinture suivant la configuration * * * "
        "4 4 4 4 4 4 4 4/3 selon configuration 4/3 selon configuration 4 4 "
        "3/2/4 selon configuration 4/3 selon configuration"
    )
    assert shared.seat_counts(region, 13) == (
        4, 4, 4, 4, 4, 4, 4, None, None, 4, 4, None, None,
    )


def test_a_three_way_band_is_one_cell_and_is_never_recorded():
    """`3/2/4` must not read as three columns, and must not record its own 2."""
    region = "Places carte grise * * * 3/2/4 selon configuration 4"
    assert shared.seat_counts(region, 2) == (None, 4)


def test_a_band_that_lost_its_phrase_makes_the_row_refuse():
    """Falling back to bare integers splits `4/3` in two, so the count no longer fits."""
    region = "Places carte grise * * * 4 4/3 4"
    assert shared.seat_counts(region, 3) == (None, None, None)


def test_a_seats_row_of_the_wrong_width_is_refused_entirely():
    """A gained or lost cell would shift every vehicle along a place — so nothing is."""
    region = "Places carte grise * * * 4 4 4 4"
    assert shared.seat_counts(region, 13) == (None,) * 13
    assert shared.seat_counts(region, 3) == (None, None, None)


def test_neither_seats_label_contains_a_digit():
    """`seat_counts` scans the whole region, which relies on the label holding no cell."""
    for page in _pages():
        for line in page.splitlines():
            if line.startswith(shared.SEATS_ROW[0]):
                label = line[: line.index("*")] if "*" in line else line
                assert not re.search(r"\d", label), label


def test_the_seats_region_stops_before_the_footnote():
    """The page footnote's `3%` and `16''` are digits that would count as columns."""
    assert shared.SEATS_END_ROW == "Places repas"
    for page in _pages():
        lines = [line.strip() for line in page.splitlines()]
        if not any(line.startswith(shared.SEATS_ROW[0]) for line in lines):
            continue
        start = next(
            i for i, line in enumerate(lines) if line.startswith(shared.SEATS_ROW[0])
        )
        assert any(
            line.startswith(shared.SEATS_END_ROW) for line in lines[start:]
        ), "no terminator after the seats row"


def test_the_two_72s_are_read_from_the_catalogue_not_supplied(columns):
    """The catalogue states these plainly; the old parser simply never reached them."""
    coachbuilts, _vans = columns
    by_code = _by_code(coachbuilts)
    for code in ("72LMF", "72LJG"):
        assert by_code[code].seats == 4
        assert code not in shared.SUPPLIED_SEATS


def test_a_banded_seats_cell_is_never_recorded_by_the_parser():
    """The parse leaves all four bands unset. `read_table` then supplies them."""
    region = (
        "Places carte grise et nombre de ceinture suivant la configuration * * * "
        "4 4 4 4 4 4 4 4/3 selon configuration 4/3 selon configuration 4 4 "
        "3/2/4 selon configuration 4/3 selon configuration"
    )
    codes = shared.SHARED_CODES
    parsed = dict(zip(codes, shared.seat_counts(region, len(codes))))
    for code in ("73LMF", "73LJG", "74LJG", "75LMF"):
        assert parsed[code] is None
        assert code in shared.SUPPLIED_SEATS


def test_the_supplied_seats_reach_the_four_banded_columns(columns):
    coachbuilts, _vans = columns
    by_code = _by_code(coachbuilts)
    for code in ("73LMF", "73LJG", "74LJG", "75LMF"):
        assert by_code[code].seats == 3


def test_the_banded_seats_come_from_the_manufacturers_own_picto(columns):
    """Read off the model pages' travel-seats tile, whose figure is in the filename.

    `pictos-3-4-carte-grise-...png`, and `carte grise` is what the catalogue calls the
    same row. Checked across all seventeen columns on 29 October 2026: the picto agrees
    wherever the catalogue is plain, and bands exactly where the catalogue bands.
    """
    assert shared.SUPPLIED_SEATS == {"73LMF": 3, "73LJG": 3, "74LJG": 3, "75LMF": 3}


def test_every_van_seat_count_is_read_from_its_own_row(columns):
    _coachbuilts, vans = columns
    assert [column.seats for column in vans] == [4, 4, 4, 4]


# --- The checks ----------------------------------------------------------------------


def test_every_real_layout_agrees_with_the_length_its_code_implies(columns):
    coachbuilts, vans = columns
    for column in coachbuilts + vans:
        assert shared.reconciles(column.code, column.length_mm)


def test_the_length_check_is_corroboration_not_a_slip_detector(columns):
    """Stated as a test so nobody mistakes it for the column-alignment guard.

    Neighbouring layouts often share a length outright — `70LMF` and `70LJG` are both
    6,97 — so a simulated one-place shift is caught on well under half the columns. The
    guard is `split_row`'s exact count; this catches a roster read in the wrong order.
    """
    coachbuilts, _vans = columns
    real = [c.length_mm for c in coachbuilts]
    codes = [c.code for c in coachbuilts]
    caught = sum(
        1 for i in range(len(codes) - 1) if not shared.reconciles(codes[i], real[i + 1])
    )
    assert 0 < caught < len(codes) - 1


def test_the_two_fridge_rows_are_complementary(columns):
    """One `S` per column between them — an independent read of the same thirteen."""
    pages = _pages()
    lines = [line for page in pages[:4] for line in page.splitlines()]
    rows = shared._marker_row(lines, shared.FRIDGE_ROWS, 13)
    assert len(rows) == 2
    for index in range(13):
        assert sum(row[index] == "S" for row in rows) == 1


# --- The figures -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("code", "length", "width", "height", "mro", "berths"),
    [
        ("60LG", 5990, 2230, 2700, 2693, 3),
        ("74LMF", 7380, 2300, 2820, 3014, 3),
        ("73LJG", 7300, 2300, 2920, 3161, 4),
    ],
)
def test_a_coachbuilt_column_reads_as_the_catalogue_prints_it(
    columns, code, length, width, height, mro, berths
):
    column = _by_code(columns[0])[code]
    assert (column.length_mm, column.width_mm, column.height_mm) == (length, width, height)
    assert column.mro_kilograms == mro
    assert column.berths == berths


def test_the_vans_read_as_the_catalogue_prints_them(columns):
    vans = _by_code(columns[1])
    assert vans["59LT"].mro_kilograms == 2924
    assert vans["63LJ"].mro_kilograms == 3070
    assert vans["63KS"].mro_kilograms == 3081
    assert all(v.width_mm == 2050 and v.height_mm == 2590 for v in vans.values())


def test_a_mass_the_catalogue_does_not_publish_is_left_unset(columns):
    """`NC` is *non communiqué*. Nothing is emitted, and nothing is inferred."""
    coachbuilts, vans = columns
    for code in ("72LMF", "72LJG", "74LJG", "75LMF"):
        assert _by_code(coachbuilts)[code].mro_kilograms is None
    assert _by_code(vans)["63LD"].mro_kilograms is None


def test_the_width_excludes_mirrors(columns):
    """`Largeur hors tout (sans rétroviseurs)` — the settled rule, satisfied at source."""
    line = next(
        line
        for line in _pages()[0].splitlines()
        if line.startswith(shared.WIDTH_ROW[0])
    )
    assert "sans r" in line and "troviseurs" in line


# --- Body type and base vehicle ---------------------------------------------------------


def test_the_body_type_comes_from_the_catalogues_own_banners(columns):
    """Not from a height — the Elister is the tallest coachbuilt here and still a profile.

    `height-does-not-decide-coachbuilt-profile`: 2920mm with a drop-down bed would have
    argued for an over-cab bed. Page 38 banners these columns `PROFILÉS`.
    """
    coachbuilts, vans = columns
    by_code = _by_code(coachbuilts)
    for code in ("60LG", "67LO", "73LMF", "73LJG"):
        assert by_code[code].body_type is BodyType.COACH_BUILT_LOW_PROFILE
    for code in ("72LMF", "74LJG"):
        assert by_code[code].body_type is BodyType.A_CLASS
    assert all(v.body_type is BodyType.CAMPERVAN_HIGH_TOP for v in vans)


def test_a_black_pearl_clears_the_high_top_threshold(columns):
    _coachbuilts, vans = columns
    assert all(v.height_mm > shared.HIGH_TOP_ABOVE_MM for v in vans)


def test_only_the_elister_and_belixter_are_mercedes():
    mercedes = {r for r, make in shared.BASE_VEHICLES.items() if make == "Mercedes"}
    assert mercedes == {"Elister", "Belixter"}


# --- Habitation ------------------------------------------------------------------------


def test_every_layout_has_blown_air_heating_and_a_compressor_fridge(columns):
    coachbuilts, vans = columns
    for column in coachbuilts + vans:
        assert column.heating_note, column.code
        assert column.fridge_note, column.code


def test_alde_is_an_option_and_never_sets_the_heating():
    """It would be wet central, and the catalogue and site both make it prominent.

    Page 39 prices it as `OPTION INTEGRAUX FIAT : Pack Optimum : Chauffage Alde`, so no
    column takes it as standard — but a reader matching on the word alone would.
    """
    page = _pages()[1]
    assert "Chauffage Alde" in page
    assert "OPTION" in page[: page.index("Chauffage Alde")].rsplit("\n", 1)[-1].upper()


def test_the_electric_heating_options_are_not_matched():
    """`Combi 4 ED` and `Combi 6ED` are upgrades; an option never sets the base spec."""
    for _prefix, contains in shared.HEATING_ROWS:
        assert contains[0] in ("Combi 4 D (", "Combi 6 D (")


# --- The products ----------------------------------------------------------------------


def _product(column: shared.Column, brand: str, manufacturer_range: str):
    prices = fleurette.PRICES if brand == "Fleurette" else florium.PRICES
    source = fleurette.PRICE_SOURCE if brand == "Fleurette" else florium.PRICE_SOURCE
    return shared.build_product(
        column,
        manufacturer=fleurette.MANUFACTURER,
        display_name=brand,
        manufacturer_range=manufacturer_range,
        price=prices.get((manufacturer_range, column.code)),
        price_source=source,
    )


def test_a_product_carries_the_company_and_shows_the_brand(columns):
    built = _product(_by_code(columns[0])["60LG"], "Fleurette", "Migrateur").motorhome
    assert built.manufacturer == "Fleurette Constructeur"
    assert built.manufacturer_display_name == "Fleurette"
    assert built.manufacturer_range == "Migrateur"
    assert built.model == "60LG"


def test_the_payload_is_derived_and_says_so(columns):
    built = _product(_by_code(columns[0])["60LG"], "Fleurette", "Migrateur")
    assert built.motorhome.mh_payload_kilograms == 3500 - 2693
    assert "3500kg maximum authorised mass - 2693kg" in (
        built.provenance["mh_payload_kilograms"].snippet
    )


def test_no_payload_is_invented_where_there_is_no_mass(columns):
    built = _product(_by_code(columns[0])["72LMF"], "Fleurette", "Discover")
    assert built.motorhome.mro_kilograms is None
    assert built.motorhome.mh_payload_kilograms is None
    assert "mro_kilograms" not in built.provenance


def test_the_price_says_it_was_manually_sourced(columns):
    """It is on no website, so no run refreshes it and a reviewer has to know that."""
    built = _product(_by_code(columns[0])["60LG"], "Fleurette", "Migrateur")
    snippet = built.provenance["rrp_pounds"].snippet
    assert "MANUALLY SOURCED" in snippet
    assert "re-verify" in snippet
    assert "nothing is converted" in snippet


def test_the_mass_is_a_real_mass_in_running_order(columns):
    """Their footnote includes one driver, so no allowance is added back."""
    built = _product(_by_code(columns[0])["60LG"], "Fleurette", "Migrateur")
    assert "Avec 1 conducteur" in built.provenance["mro_kilograms"].snippet


def test_habitation_reaches_the_reviewer_set(columns):
    built = _product(_by_code(columns[0])["60LG"], "Fleurette", "Migrateur").motorhome
    assert built.heating is Heating.BLOWN_AIR
    assert built.refrigeration is Refrigeration.FRIDGE_FREEZER


@pytest.mark.parametrize(
    ("brand", "manufacturer_range", "code", "price"),
    [
        ("Fleurette", "Migrateur", "60LG", 68690),
        ("Fleurette", "Elister", "73LJG", 102990),
        ("Florium", "Mayflower", "70LMF", 74590),
        ("Florium", "Black Pearl", "63KS", 68690),
    ],
)
def test_the_price_is_the_base_vehicles(columns, brand, manufacturer_range, code, price):
    """The manual transmission, except where the list publishes automatic only."""
    pool = columns[1] if manufacturer_range == "Black Pearl" else columns[0]
    built = _product(_by_code(pool)[code], brand, manufacturer_range)
    assert built.motorhome.rrp_pounds == price


def test_the_discover_and_wincester_price_is_the_automatic_one():
    """They are published automatic-only, so the cheaper-of-two rule would misfire."""
    assert fleurette.PRICES[("Discover", "72LMF")] == 94990
    assert florium.PRICES[("Wincester", "72LMF")] == 93690


def test_the_two_contradicted_black_pearl_rows_are_not_used():
    """63LJ at £57,275 and 59LT at £55,300 undercut their own 140hp manual by £10-12k
    while the same sheet prices a 180hp engine at +£2,160. The arithmetic wins."""
    assert florium.PRICES[("Black Pearl", "63LJ")] == 66990
    assert florium.PRICES[("Black Pearl", "59LT")] == 64390
    assert 57275 not in florium.PRICES.values()
    assert 55300 not in florium.PRICES.values()


# --- Finding the tables ----------------------------------------------------------------


def test_the_tables_are_found_by_shape_not_by_page_number():
    pages = _pages()
    assert shared.find_table_page(pages, shared.SHARED_CODES)[0] == 0
    assert shared.find_table_page(pages, shared.BLACK_PEARL_CODES)[0] == 4


def test_the_vans_page_spells_its_first_layout_with_a_space():
    """`59 LT` on the catalogue, `59LT` everywhere else — why the match ignores spaces."""
    vans_page = _pages()[4]
    assert "59 LT" in vans_page
    assert "59LT" not in vans_page


def test_the_catalogue_url_prefers_the_newest_model_year():
    html = """
      <a href="https://x/uploads/2025/08/Catalogue_Fleurette_FR_297x210_2026-13_BD.pdf">old</a>
      <a href="https://x/uploads/2026/07/Catalogue_Fleurette_297x210_2027_FR_BD-17.pdf">new</a>
    """
    assert shared.catalogue_url(html).endswith("2027_FR_BD-17.pdf")


def test_the_year_is_found_despite_the_underscores():
    """`\\b(20\\d{2})\\b` never fires between `_` and `2027`, so every name read as yearless."""
    assert shared.catalogue_url(
        '<a href="https://x/Catalogue_Fleurette_297x210_2027_FR_BD-17.pdf">c</a>'
    ) is not None
