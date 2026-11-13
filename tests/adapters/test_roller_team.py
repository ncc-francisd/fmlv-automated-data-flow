"""Roller Team's parsing, against captures of the real roster and the two 2027 PDFs.

Every fixture here is an unmodified capture taken 13 November 2026: the REST roster's
JSON, the extracted text of the UK price list, the extracted text of the brochure's
twelve specification pages, and two model pages — one ordinary, one served under the
wrong slug.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.adapters import roller_team
from src.adapters.roller_team import (
    PriceRow,
    RollerTeamProduct,
    RosterEntry,
    SpecColumn,
    _cells,
    _column_names,
    _COUNT_CELL,
    _KILOGRAMS_CELL,
    _reconciles,
    _tiles,
    find_document,
    parse_brochure,
    parse_price_list,
    parse_roster,
    split_range_and_model,
)
from src.product_model.enums import BodyType, Heating, Refrigeration

FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def roster() -> list[RosterEntry]:
    entries, _notes = parse_roster(_read("roller-team-roster.json"))
    return entries


@pytest.fixture(scope="module")
def roster_notes() -> list[str]:
    _entries, notes = parse_roster(_read("roller-team-roster.json"))
    return notes


@pytest.fixture(scope="module")
def prices() -> list[PriceRow]:
    return parse_price_list(_read("roller-team-price-list-2027.txt"))


@pytest.fixture(scope="module")
def specs(prices: list[PriceRow]) -> dict[str, SpecColumn]:
    by_range: dict[str, list[str]] = {}
    for row in prices:
        split = split_range_and_model(row.full_name)
        assert split is not None, row.full_name
        by_range.setdefault(split[0], []).append(split[1])
    pages = json.loads(_read("roller-team-brochure-2027-spec-pages.json"))
    columns, _notes = parse_brochure(pages, by_range)
    return columns


# --- The roster ----------------------------------------------------------------------


def test_the_roster_lists_every_current_model(roster: list[RosterEntry]) -> None:
    assert len(roster) == roller_team.EXPECTED_PRODUCTS == 20


def test_the_model_is_named_by_its_title_not_its_slug(roster: list[RosterEntry]) -> None:
    """The one trap that would invent a product and retire a real one on the same run."""
    mislabelled = next(entry for entry in roster if entry.slug == "zefiro-647")
    assert mislabelled.model_name == "Zefiro 747"
    assert not any(entry.model_name == "Zefiro 647" for entry in roster)


def test_a_slug_that_disagrees_with_its_title_is_narrated(roster_notes: list[str]) -> None:
    assert any("zefiro-647" in note and "Zefiro 747" in note for note in roster_notes)


def test_the_range_comes_from_the_gamma_taxonomy(roster: list[RosterEntry]) -> None:
    ranges = {entry.model_name: entry.manufacturer_range for entry in roster}
    assert ranges["Kronos Compact 665"] == "Kronos Compact"
    assert ranges["T-Line 590"] == "T-Line"
    assert ranges["Livingstone DUO"] == "Livingstone"


def test_the_body_type_comes_from_the_tipologia_taxonomy(roster: list[RosterEntry]) -> None:
    bodies = {entry.model_name: entry.tipologia for entry in roster}
    assert bodies["Pegaso 740"] == "a-class"
    assert bodies["Zefiro 675"] == "over-cab"
    assert bodies["Livingstone 2"] == "campervan"
    assert bodies["T-Line 750"] == "low-profile"


def test_the_bed_taxonomy_is_not_mistaken_for_the_body_taxonomy(
    roster: list[RosterEntry],
) -> None:
    """`tipologia-letto-single-beds` sits beside `tipologia-low-profile` on the same record."""
    zefiro = next(entry for entry in roster if entry.model_name == "Zefiro 707")
    assert zefiro.tipologia == "low-profile"


def test_the_stale_berth_taxonomy_is_not_read_at_all(roster: list[RosterEntry]) -> None:
    """Zefiro 746 is tagged `posti-letto-4-berths`; its tile and the brochure both say 6."""
    assert not hasattr(RosterEntry, "berths")
    payload = json.loads(_read("roller-team-roster.json"))
    tagged = next(r for r in payload if r["title"]["rendered"] == "Zefiro 746")
    assert "posti-letto-4-berths" in tagged["class_list"]


# --- Range and model -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("full_name", "expected"),
    [
        ("Kronos Compact 665", ("Kronos Compact", "665")),
        ("Livingstone Duo", ("Livingstone", "Duo")),
        ("Zefiro Sport", ("Zefiro", "Sport")),
        ("T-Line 590", ("T-Line", "590")),
        ("Pegaso 750", ("Pegaso", "750")),
    ],
)
def test_the_range_prefix_is_split_off_the_model(
    full_name: str, expected: tuple[str, str]
) -> None:
    assert split_range_and_model(full_name) == expected


def test_a_name_with_no_known_range_is_refused_rather_than_guessed() -> None:
    assert split_range_and_model("Granduca 7000") is None


def test_the_longest_range_prefix_wins() -> None:
    """`Kronos Compact 590` must not become range `Kronos` with model `Compact 590`."""
    assert split_range_and_model("Kronos Compact 590") == ("Kronos Compact", "590")


# --- The price list ------------------------------------------------------------------


def test_every_model_is_priced(prices: list[PriceRow]) -> None:
    assert len(prices) == roller_team.EXPECTED_PRODUCTS


def test_the_extractors_split_after_a_capital_t_is_repaired(prices: list[PriceRow]) -> None:
    """The PDF yields `T - Line 590` and `Ford T ransit`; both would miss every match."""
    names = {row.full_name for row in prices}
    assert "T-Line 590" in names
    assert {row.chassis for row in prices} == {"Fiat Ducato", "Ford Transit"}


def test_the_body_type_restated_in_the_name_is_stripped(prices: list[PriceRow]) -> None:
    names = {row.full_name for row in prices}
    assert "Zefiro 675" in names  # listed as `Zefiro 675 Hi-Line (over cab bed)`
    assert "Pegaso 590" in names  # listed as `Pegaso 590 A-Class (drop down bed)`
    assert "Zefiro Sport" in names
    assert not any("Hi-Line" in name or "A-Class" in name for name in names)


def test_the_on_the_road_price_is_the_one_recorded(prices: list[PriceRow]) -> None:
    zefiro = next(row for row in prices if row.full_name == "Zefiro 707")
    assert zefiro.ex_works_pounds == 70_560
    assert zefiro.on_the_road_pounds == 70_995


def test_on_the_road_is_ex_works_plus_the_charges_the_list_names(
    prices: list[PriceRow],
) -> None:
    """The price parse's own arithmetic check: £435 on every row, as the list states."""
    assert [row.full_name for row in prices if not row.charges_reconcile] == []


# --- The brochure's columnar tables --------------------------------------------------


def test_a_header_that_repeats_the_range_before_every_number_is_read() -> None:
    header = " Kronos Compact 590 Kronos Compact 665 Kronos Compact 670"
    assert _column_names(header, ["590", "665", "670"]) == ["590", "665", "670"]


def test_a_header_of_bare_numbers_and_a_word_is_read() -> None:
    assert _column_names(" 675 685 696 Sport", ["675", "685", "696", "Sport"]) == [
        "675",
        "685",
        "696",
        "Sport",
    ]


def test_columns_are_ordered_by_where_the_header_puts_them() -> None:
    assert _column_names(" 747 707 746", ["707", "746", "747"]) == ["747", "707", "746"]


def test_a_header_naming_none_of_the_candidates_is_refused() -> None:
    assert _column_names(" 100 200", ["590", "665"]) is None


def test_a_row_with_the_wrong_number_of_cells_is_discarded_not_guessed_at() -> None:
    """`Rear bed (cm) 190 x 135` gives one value for the Kronos's three columns."""
    page = "Rear bed (cm) 190 x 135\nGross vehicle weight 3,500kg 3,500kg 3,500kg"
    assert _cells(page, "Gross vehicle weight", _KILOGRAMS_CELL, 3) == ["3,500"] * 3
    assert _cells(page, "Rear bed (cm)", _KILOGRAMS_CELL, 3) is None


def test_a_row_that_is_absent_entirely_is_none() -> None:
    assert _cells("Berths 2 4", "Mass in running order", _KILOGRAMS_CELL, 2) is None


def test_every_model_gets_a_specification_column(specs: dict[str, SpecColumn]) -> None:
    assert len(specs) == roller_team.EXPECTED_PRODUCTS


def test_the_weights_are_read_off_the_table(specs: dict[str, SpecColumn]) -> None:
    pegaso = specs["PEGASO 750"]
    assert pegaso.gross_vehicle_weight_kg == 3500
    assert pegaso.mass_in_running_order_kg == 3060
    assert pegaso.length_m == 7.43
    assert pegaso.width_m == 2.35
    assert pegaso.height_m == 2.85


def test_the_kronos_665_is_four_berths(specs: dict[str, SpecColumn]) -> None:
    """Settled from the floorplan: a fixed double plus a front drop-down double."""
    assert specs["KRONOS COMPACT 665"].berths == 4
    assert specs["KRONOS COMPACT 665"].belted_seats == 4


def test_a_parenthesised_extra_berth_is_an_option_not_a_berth(
    specs: dict[str, SpecColumn],
) -> None:
    """`2 (+2 optional)` is two; the extras are the £290 fifth berth."""
    assert specs["KRONOS COMPACT 590"].berths == 2
    assert specs["KRONOS COMPACT 670"].berths == 2
    assert specs["T-LINE 700"].berths == 4  # written `4 (5 optional)`


def test_a_berth_written_as_a_sum_takes_the_base_figure(
    specs: dict[str, SpecColumn],
) -> None:
    """The Livingstone 2's `2 + 1` is two berths."""
    assert specs["LIVINGSTONE 2"].berths == 2


def test_the_two_masses_differ_between_sibling_columns(
    specs: dict[str, SpecColumn],
) -> None:
    """A column read off by one would give neighbours each other's weights."""
    assert specs["ZEFIRO 707"].mass_in_running_order_kg == 2915
    assert specs["ZEFIRO 746"].mass_in_running_order_kg == 2935
    assert specs["ZEFIRO 747"].mass_in_running_order_kg == 2925


def test_heating_is_counted_per_column_not_split_on_whitespace(
    specs: dict[str, SpecColumn],
) -> None:
    """Every range but the Livingstone wraps each column's appliance onto two lines."""
    for key in ("KRONOS COMPACT 590", "KRONOS COMPACT 665", "KRONOS COMPACT 670"):
        assert specs[key].heating is not None
        assert specs[key].heating[0] is Heating.BLOWN_AIR


def test_a_column_whose_heater_differs_from_its_siblings_keeps_its_own(
    specs: dict[str, SpecColumn],
) -> None:
    assert "Diesel" in specs["KRONOS COMPACT 670"].heating[1]
    assert "Gas" in specs["KRONOS COMPACT 590"].heating[1]


def test_the_livingstones_webasto_is_read_as_heating(specs: dict[str, SpecColumn]) -> None:
    assert specs["LIVINGSTONE 2"].heating[0] is Heating.BLOWN_AIR
    assert "Webasto" in specs["LIVINGSTONE 2"].heating[1]


def test_the_fridge_is_read_from_the_equipment_page(specs: dict[str, SpecColumn]) -> None:
    assert specs["ZEFIRO 707"].refrigeration[0] is Refrigeration.FRIDGE_FREEZER
    assert specs["KRONOS COMPACT 590"].refrigeration[0] is Refrigeration.FRIDGE_FREEZER


def test_no_bed_type_is_assigned_from_the_ragged_bed_rows(
    specs: dict[str, SpecColumn],
) -> None:
    assert not hasattr(SpecColumn, "bed_types")


# --- Joining, and the self-check -----------------------------------------------------


def _product(
    model_name: str,
    specs: dict[str, SpecColumn],
    prices: list[PriceRow],
    *,
    tile_length_m: float | None = None,
    tipologia: str = "low-profile",
    title: str | None = None,
) -> RollerTeamProduct:
    price = next(row for row in prices if row.key == model_name.upper())
    entry = RosterEntry(
        model_name=title or model_name,
        slug="x",
        link="https://example.invalid/x/",
        manufacturer_range=split_range_and_model(model_name)[0],
        tipologia=tipologia,
    )
    return RollerTeamProduct(
        roster=entry,
        price=price,
        spec=specs[model_name.upper()],
        tile_length_m=tile_length_m,
    )


def test_every_model_passes_the_length_self_check(
    specs: dict[str, SpecColumn], prices: list[PriceRow]
) -> None:
    """All twenty lengths agree between the brochure and the price list."""
    failures = [
        row.full_name
        for row in prices
        if not _reconciles(_product(row.full_name, specs, prices))[0]
    ]
    assert failures == []


def test_a_length_the_price_list_contradicts_drops_the_product(
    specs: dict[str, SpecColumn], prices: list[PriceRow]
) -> None:
    product = _product("Zefiro 707", specs, prices)
    product.spec = SpecColumn(**{**product.spec.__dict__, "length_m": 9.99})
    reconciles, note = _reconciles(product)
    assert not reconciles
    assert "9.99" in note and "7.12" in note


def test_a_model_page_tile_that_contradicts_both_documents_drops_the_product(
    specs: dict[str, SpecColumn], prices: list[PriceRow]
) -> None:
    product = _product("Zefiro 707", specs, prices, tile_length_m=8.5)
    assert not _reconciles(product)[0]


def test_the_check_says_how_many_sources_agreed(
    specs: dict[str, SpecColumn], prices: list[PriceRow]
) -> None:
    with_tile = _reconciles(_product("Zefiro 707", specs, prices, tile_length_m=7.12))[1]
    without = _reconciles(_product("Zefiro 707", specs, prices))[1]
    assert "all three sources" in with_tile
    assert "both documents" in without


# --- The product -----------------------------------------------------------------


def test_the_payload_is_derived_and_says_so(
    specs: dict[str, SpecColumn], prices: list[PriceRow]
) -> None:
    product = _product("Pegaso 750", specs, prices, tipologia="a-class")
    assert product.payload_kilograms == 3500 - 3060
    extracted = roller_team._build_extracted_motorhome(product)
    assert extracted.motorhome.mh_payload_kilograms == 440
    assert "DERIVED" in extracted.provenance["mh_payload_kilograms"].snippet


def test_the_base_gross_weight_is_recorded_not_the_free_upgrade(
    specs: dict[str, SpecColumn], prices: list[PriceRow]
) -> None:
    extracted = roller_team._build_extracted_motorhome(
        _product("Kronos Compact 590", specs, prices)
    )
    assert extracted.motorhome.mtplm_kilograms == 3500
    assert "3,550kg" in extracted.provenance["mtplm_kilograms"].snippet


@pytest.mark.parametrize(
    ("model_name", "tipologia", "expected"),
    [
        ("Pegaso 740", "a-class", BodyType.A_CLASS),
        ("Zefiro 675", "over-cab", BodyType.COACH_BUILT_OVER_CAB_BED),
        ("T-Line 750", "low-profile", BodyType.COACH_BUILT_LOW_PROFILE),
        ("Livingstone 2", "campervan", BodyType.CAMPERVAN_HIGH_TOP),
    ],
)
def test_the_body_type_is_published_not_derived(
    model_name: str,
    tipologia: str,
    expected: BodyType,
    specs: dict[str, SpecColumn],
    prices: list[PriceRow],
) -> None:
    product = _product(model_name, specs, prices, tipologia=tipologia)
    assert product.body_type is expected


def test_a_campervan_below_the_high_top_line_is_a_plain_campervan(
    specs: dict[str, SpecColumn], prices: list[PriceRow]
) -> None:
    product = _product("Livingstone 2", specs, prices, tipologia="campervan")
    product.spec = SpecColumn(**{**product.spec.__dict__, "height_m": 2.1})
    assert product.body_type is BodyType.CAMPERVAN


def test_an_unknown_body_taxonomy_leaves_the_field_blank(
    specs: dict[str, SpecColumn], prices: list[PriceRow]
) -> None:
    product = _product("Zefiro 707", specs, prices, tipologia="semintegrale")
    assert product.body_type is None


def test_the_automatic_is_available_but_its_price_columns_stay_blank(
    specs: dict[str, SpecColumn], prices: list[PriceRow]
) -> None:
    """Roller Team price the automatic as an uplift, not as a price of its own."""
    extracted = roller_team._build_extracted_motorhome(_product("Zefiro 707", specs, prices))
    assert extracted.motorhome.automatic is None


def test_the_chassis_is_spelled_fmlvs_way(
    specs: dict[str, SpecColumn], prices: list[PriceRow]
) -> None:
    fiat = roller_team._build_extracted_motorhome(_product("Pegaso 740", specs, prices))
    ford = roller_team._build_extracted_motorhome(_product("Zefiro 707", specs, prices))
    assert fiat.motorhome.base_vehicle_manufacturer == "Fiat"
    assert ford.motorhome.base_vehicle_manufacturer == "Ford"


def test_the_known_tile_fault_is_named_in_the_berth_provenance(
    specs: dict[str, SpecColumn], prices: list[PriceRow]
) -> None:
    """A typo is reported as a fault, not put to a reviewer as a question every run."""
    extracted = roller_team._build_extracted_motorhome(
        _product("Kronos Compact 665", specs, prices)
    )
    snippet = extracted.provenance["berths"].snippet
    assert extracted.motorhome.berths == 4
    assert "typo" in snippet and "floorplan" in snippet


def test_an_ordinary_model_carries_no_fault_note(
    specs: dict[str, SpecColumn], prices: list[PriceRow]
) -> None:
    extracted = roller_team._build_extracted_motorhome(_product("Zefiro 707", specs, prices))
    assert "typo" not in extracted.provenance["berths"].snippet


def test_the_model_string_takes_the_titles_spelling_not_the_price_lists(
    specs: dict[str, SpecColumn], prices: list[PriceRow]
) -> None:
    """FMLV holds `SPORT`; the price list writes `Sport`. The export decides."""
    product = _product("Zefiro Sport", specs, prices, title="Zefiro SPORT")
    assert product.model == "SPORT"
    extracted = roller_team._build_extracted_motorhome(product)
    assert extracted.motorhome.model == "SPORT"


def test_the_two_documents_still_join_whatever_the_casing(
    specs: dict[str, SpecColumn], prices: list[PriceRow]
) -> None:
    """The join is case-insensitive, so only the recorded spelling is in question."""
    assert "ZEFIRO SPORT" in specs
    assert any(row.key == "ZEFIRO SPORT" for row in prices)


def test_a_renamed_range_is_declared_in_the_direction_the_site_speaks() -> None:
    """Keyed on what the site now says, giving what FMLV still holds."""
    assert roller_team.RENAMED_MODELS[("Zefiro", "707")] == ("Auto-Roller", "707")
    assert ("Auto-Roller", "707") not in roller_team.RENAMED_MODELS


def test_the_rename_is_a_model_entry_not_a_range_wide_one() -> None:
    """A range-wide `Zefiro -> Auto-Roller` would orphan the four Zefiros FMLV has right."""
    assert not hasattr(roller_team, "RENAMED_RANGES")
    assert set(roller_team.RENAMED_MODELS) == {
        ("Zefiro", "707"),
        ("Zefiro", "746"),
        ("Zefiro", "747"),
    }


def test_a_renamed_product_says_in_its_provenance_what_fmlv_holds(
    specs: dict[str, SpecColumn], prices: list[PriceRow]
) -> None:
    extracted = roller_team._build_extracted_motorhome(_product("Zefiro 707", specs, prices))
    snippet = extracted.provenance["manufacturer_range"].snippet
    assert "Auto-Roller 707" in snippet
    assert "mass in running order" in snippet


def test_both_halves_of_the_identity_are_proposed_together(
    specs: dict[str, SpecColumn], prices: list[PriceRow]
) -> None:
    """Moving a range without its model is what wrote back Bailey's `Adamo I`."""
    extracted = roller_team._build_extracted_motorhome(_product("Zefiro 707", specs, prices))
    assert {"manufacturer_range", "model"} <= set(extracted.provenance)
    for field_name in ("manufacturer_range", "model"):
        assert "they are one name" in extracted.provenance[field_name].snippet


def test_an_unrenamed_product_carries_no_rename_note(
    specs: dict[str, SpecColumn], prices: list[PriceRow]
) -> None:
    extracted = roller_team._build_extracted_motorhome(_product("Zefiro 685", specs, prices))
    assert "Auto-Roller" not in extracted.provenance["manufacturer_range"].snippet


def test_the_length_provenance_names_the_check_that_licenses_it(
    specs: dict[str, SpecColumn], prices: list[PriceRow]
) -> None:
    extracted = roller_team._build_extracted_motorhome(_product("Zefiro 707", specs, prices))
    assert "right column" in extracted.provenance["mh_length_mm"].snippet


def test_no_floorplan_field_is_ever_proposed(
    specs: dict[str, SpecColumn], prices: list[PriceRow]
) -> None:
    extracted = roller_team._build_extracted_motorhome(_product("Zefiro 707", specs, prices))
    for field_name in ("sleeping_area", "kitchen_location", "lounge_location", "bed_types"):
        assert field_name not in extracted.provenance


# --- The pages -----------------------------------------------------------------------


def test_the_headline_tiles_are_read_by_label(roster: list[RosterEntry]) -> None:
    tiles = _tiles(_read("roller-team-zefiro-707.html"))
    assert tiles["Berths"] == "6"
    assert tiles["Passengers"] == "6"
    assert tiles["Length"] == "7,12"
    assert tiles["Width"] == "2,35"


def test_an_italian_decimal_comma_is_read_as_a_decimal_point() -> None:
    assert roller_team._tile_metres("7,12") == 7.12
    assert roller_team._tile_metres("") is None
    assert roller_team._tile_metres("n/a") is None


def test_the_mislabelled_page_still_carries_the_right_tiles() -> None:
    tiles = _tiles(_read("roller-team-zefiro-647.html"))
    assert tiles["Berths"] == "6"


def test_the_document_page_links_exactly_one_pdf() -> None:
    url = find_document(_read("roller-team-price-list-page.html"))
    assert url is not None
    assert url.endswith("Roller-Team-Price-List-2027.pdf")


def test_a_page_linking_two_pdfs_is_refused() -> None:
    """Which edition is current cannot be established, so nothing is guessed."""
    html = 'href="https://x/a.pdf" href="https://x/b.pdf"'
    assert find_document(html) is None


def test_a_page_linking_no_pdf_is_refused() -> None:
    assert find_document("<html><body>no documents here</body></html>") is None


def test_a_count_cell_takes_the_base_figure() -> None:
    assert _COUNT_CELL.match("4 (+1 optional)").group(1) == "4"
    assert _COUNT_CELL.match("2 + 1").group(1) == "2"
    assert _COUNT_CELL.match("8").group(1) == "8"
