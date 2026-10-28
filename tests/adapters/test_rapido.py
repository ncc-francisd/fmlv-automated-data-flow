"""Rapido — parsing and derivation only, no network.

Fixtures are the real pages of 28 October 2026. The five guide pages are the SVG text
layer exactly as Calaméo served it, with only the one `<image>` element carrying the page
artwork removed: it is a base64 bitmap, it is ninety per cent of the file, and nothing in
the adapter ever looks at it.

Those five were chosen because each broke the parser while it was being written:

* **page 2** — the GVW values do line up as a row here, and do not on page 12;
* **page 3** — `V65 XL` and `V68` share one `<text>` element as `XLV`, and the Webasto
  heading is the one the vocabulary cannot read;
* **page 9** — two heading letters are drawn as outlines rather than set as text, so the
  glued string is short of a full set;
* **page 12** — the GVW row is broken into free-standing `LIGHT:`/`HEAVY:` elements, and
  666F carries a drop-down berth option beside its standard berths;
* **page 24** — four columns, a footnoted `3*` registered-seat count, and the one series
  where ALDE is standard rather than an option.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters import ADAPTERS, adapter_for, rapido
from src.adapters.base import ExtractedMotorhome
from src.adapters.rapido import (
    BODY_TYPES,
    EXPECTED_MODELS,
    MANUFACTURER,
    MANUFACTURER_DISPLAY_NAME,
    RANGE_NAMES,
    RENAMED_MODELS,
    RENAMED_RANGES,
    _gross_weights,
    _is_subsequence,
    _read_columns,
    _series_of,
    heading_key,
    identity_key,
    model_columns,
    page_cells,
    parse_roster,
    reconciles,
    standard_heating,
    technical_guide_url,
)
from src.diff.matching import (
    DEFAULT_THRESHOLD,
    Renames,
    _identity_tokens,
    _jaccard,
    token_similarity,
)
from src.product_model.enums import BodyType, Heating, Refrigeration
from src.product_model.model import Motorhome
from src.vehicle_class import VehicleClass

FIXTURES = Path(__file__).parent / "fixtures"

#: Which page of the guide each layout's figures are on, from the 2027 edition.
_MIRO_LABEL = "Mass in Running Order (MIRO) (kg)"


def _page(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def comparator() -> str:
    return _page("rapido_comparator.html")


@pytest.fixture
def catalogues() -> str:
    return _page("rapido_catalogues.html")


def _guide(number: int) -> tuple:
    return page_cells(_page(f"rapido_guide_p{number}.svg"))


def _columns_of(number: int, keys: list[str]) -> tuple[tuple[str, ...], list]:
    """One page's heading and its columns, the way `collect` reads them."""
    rows = _guide(number)
    count = len(next(row for row in rows if row.label == _MIRO_LABEL).values)
    heading = model_columns(rows, keys, count)
    assert heading is not None
    return heading, _read_columns(rows, count, number)


# --- registry -------------------------------------------------------------------------


def test_the_adapter_is_wired_in() -> None:
    assert ADAPTERS[(MANUFACTURER, MANUFACTURER_DISPLAY_NAME, VehicleClass.MOTORHOME)] is rapido
    assert adapter_for(MANUFACTURER) is rapido


def test_the_registry_row_and_the_module_agree_on_the_manufacturer() -> None:
    """The join key back to FMLV's product ids. A trailing space empties the baseline."""
    row = next(
        line
        for line in Path("config/manufacturers.csv").read_text(encoding="utf-8").splitlines()
        if line.startswith("129,")
    )
    assert f",{MANUFACTURER}," in row


# --- the comparator, which is the roster ----------------------------------------------


def test_the_comparator_lists_every_layout(comparator: str) -> None:
    roster = parse_roster(comparator)
    assert len(roster) == EXPECTED_MODELS


def test_every_layout_lands_in_a_series_and_a_body_type_we_know(comparator: str) -> None:
    for entry in parse_roster(comparator):
        assert entry.series in RANGE_NAMES, entry.name
        assert entry.body in BODY_TYPES, entry.name


def test_the_range_is_fmlvs_own_spelling(comparator: str) -> None:
    """`SERIE 80dF`, not the nav's `SERIE 80DF`: the guide and the layout codes agree."""
    by_name = {entry.name: entry for entry in parse_roster(comparator)}
    assert by_name["8066dF"].range_name == "SERIE 80dF"
    assert by_name["V65 XL"].range_name == "SERIE VANS"
    assert by_name["C86i"].range_name == "SERIE C"


def test_serie_c_holds_both_a_body_types(comparator: str) -> None:
    """The reason body type is read per layout rather than per series."""
    by_name = {entry.name: entry for entry in parse_roster(comparator)}
    assert BODY_TYPES[by_name["C86"].body] is BodyType.COACH_BUILT_LOW_PROFILE
    assert BODY_TYPES[by_name["C86i"].body] is BodyType.A_CLASS


def test_696f_is_a_low_profile_not_an_over_cab_bed(comparator: str) -> None:
    """FMLV holds it as an over-cab bed; Rapido file it with the rest of Serie 6F."""
    entry = next(e for e in parse_roster(comparator) if e.name == "696F")
    assert BODY_TYPES[entry.body] is BodyType.COACH_BUILT_LOW_PROFILE


def test_the_technical_guide_is_found_by_its_heading(catalogues: str) -> None:
    found = technical_guide_url(catalogues)
    assert found is not None
    assert found.startswith("https://www.calameo.com/read/")
    # The catalogue sits beside it on the same page and must not be picked up instead.
    assert found != "https://www.calameo.com/read/0076927323f141e968aa0?authid=0zG0Yf8mXNtB"


def test_a_catalogues_page_with_no_guide_gives_nothing() -> None:
    assert technical_guide_url("<h2>CATALOG 2027</h2>") is None


# --- splitting cells on `dx` ----------------------------------------------------------


def test_a_row_splits_into_the_label_and_one_cell_per_column() -> None:
    rows = _guide(24)
    payload = next(row for row in rows if row.label == "Payload (kg)")
    assert payload.values == ("255", "1140", "270", "1150")


def test_a_two_column_page_splits_into_two() -> None:
    rows = _guide(2)
    assert next(row for row in rows if row.label == "Overall length").values == ("5,99", "6,36")


def test_the_series_title_is_read_off_the_page_that_carries_one() -> None:
    assert _series_of(_guide(2)) == "vans"
    assert _series_of(_guide(12)) == "serie-6f"
    assert _series_of(_guide(24)) == "serie-distinction"


def test_a_continuation_page_claims_no_series() -> None:
    """Pages 3 and 9 head themselves with the chassis, so the caller carries the last on."""
    assert _series_of(_guide(3)) is None
    assert _series_of(_guide(9)) is None


# --- binding columns to layouts -------------------------------------------------------


def test_a_heading_shared_between_two_vehicles_still_splits(comparator: str) -> None:
    """`V65 XL` and `V68` arrive as one element, `XLV`, and only `dx` separates them."""
    keys = [entry.key for entry in parse_roster(comparator) if entry.series == "vans"]
    heading, _columns = _columns_of(3, keys)
    assert heading == ("v64", "v65xl", "v68")


def test_an_outlined_heading_does_not_partition(comparator: str) -> None:
    """Page 9 loses the `i` of C66i and the `C` of C86i to outlined type."""
    keys = [entry.key for entry in parse_roster(comparator) if entry.series == "serie-c"]
    rows = _guide(9)
    assert heading_key(rows) == "c6686i"
    assert model_columns(rows, keys, 2) is None


def test_what_was_read_of_an_outlined_heading_fits_the_published_order() -> None:
    """The check that lets `collect` place page 9 on the order the series is listed in."""
    assert _is_subsequence("c6686i", "c66ic86i")
    assert not _is_subsequence("c6686i", "c86ic66i")


def test_a_heading_that_reads_two_ways_is_no_reading() -> None:
    rows = _guide(2)
    assert model_columns(rows, ["v5", "5", "v62"], 2) is None


# --- the self-check -------------------------------------------------------------------


def test_every_layout_on_a_page_reconciles(comparator: str) -> None:
    keys = [entry.key for entry in parse_roster(comparator)]
    for number in (2, 3, 12, 24):
        rows = _guide(number)
        gross = _gross_weights(rows)
        _heading, columns = _columns_of(number, keys)
        for column in columns:
            assert reconciles(column.miro, column.payload, gross), (number, column)


def test_a_gross_weight_broken_out_of_its_row_is_still_found() -> None:
    """Page 12 prints the GVW as free-standing `LIGHT:`/`HEAVY:` elements, not as a row."""
    assert 3500 in _gross_weights(_guide(12))


def test_a_column_slipped_by_one_fails_the_self_check() -> None:
    """V55's MIRO with V62's payload is 3520, and no Rapido is sold at 3520."""
    gross = _gross_weights(_guide(2))
    assert reconciles(3045, 455, gross)
    assert not reconciles(3045, 475, gross)


def test_a_layout_with_half_the_arithmetic_missing_is_not_reconciled() -> None:
    assert not reconciles(3045, None, {3500})
    assert not reconciles(None, 455, {3500})
    assert not reconciles(3045, 455, set())


# --- reading one column ---------------------------------------------------------------


def test_the_figures_of_one_layout(comparator: str) -> None:
    keys = [entry.key for entry in parse_roster(comparator)]
    heading, columns = _columns_of(24, keys)
    alde = columns[heading.index("i66malde")]
    assert alde.length_mm == 7540
    assert alde.width_mm == 2350
    assert alde.height_mm == 2950
    assert alde.miro == 3360
    assert alde.payload == 1140
    assert alde.miro + alde.payload == 4500
    assert alde.berths == 4
    assert alde.seats == 4
    assert alde.chassis == "MERCEDES AL-KO"


def test_a_footnoted_seat_count_keeps_its_figure(comparator: str) -> None:
    """The Distinction's 3.5-tonne variants are registered for three, with an asterisk."""
    keys = [entry.key for entry in parse_roster(comparator)]
    heading, columns = _columns_of(24, keys)
    assert columns[heading.index("i66mtruma")].seats == 3


def test_berths_are_the_standard_line_not_the_option(comparator: str) -> None:
    """666F prints `Berths 2+1` and `Berths (with drop-down bed option) 2+2`."""
    keys = [entry.key for entry in parse_roster(comparator)]
    heading, columns = _columns_of(12, keys)
    assert columns[heading.index("666f")].berths == 3
    assert columns[heading.index("606f")].berths == 4


def test_the_width_is_the_one_without_the_mirrors(comparator: str) -> None:
    """Three widths are printed; FMLV wants the narrowest of them."""
    keys = [entry.key for entry in parse_roster(comparator)]
    heading, columns = _columns_of(2, keys)
    assert columns[heading.index("v55")].width_mm == 2050


def test_the_garage_is_read_out_of_its_own_section(comparator: str) -> None:
    """`Width`/`Length`/`Height` mean nothing without the heading they sit under."""
    keys = [entry.key for entry in parse_roster(comparator)]
    heading, columns = _columns_of(2, keys)
    garage = columns[heading.index("v55")].garage
    assert "width 87 cm" in garage
    assert "length 128 cm" in garage


# --- habitation -----------------------------------------------------------------------


def test_an_optional_alde_is_not_the_heating_fitted() -> None:
    assert standard_heating("TRUMA Combi 6 INET X / ALDE as option") == "TRUMA Combi 6 INET X"


def test_a_single_system_is_left_alone() -> None:
    assert standard_heating("ALDE 3030+") == "ALDE 3030+"
    assert standard_heating("TRUMA Combi 4 DIESEL CP PLUS") == "TRUMA Combi 4 DIESEL CP PLUS"


def test_the_heating_read_off_each_series(comparator: str) -> None:
    roster = {entry.key: entry for entry in parse_roster(comparator)}
    heading, columns = _columns_of(24, [entry.key for entry in roster.values()])
    truma = rapido._build(
        roster["i66mtruma"], columns[heading.index("i66mtruma")], "https://x?a=b", lambda _m: None
    )
    alde = rapido._build(
        roster["i66malde"], columns[heading.index("i66malde")], "https://x?a=b", lambda _m: None
    )
    assert truma.motorhome.heating is Heating.BLOWN_AIR
    assert alde.motorhome.heating is Heating.WET_CENTRAL


def test_a_fridge_with_no_freezer_either_way_is_a_fridge_freezer(comparator: str) -> None:
    roster = {entry.key: entry for entry in parse_roster(comparator)}
    heading, columns = _columns_of(2, [entry.key for entry in roster.values()])
    built = rapido._build(
        roster["v55"], columns[heading.index("v55")], "https://x?a=b", lambda _m: None
    )
    assert built.motorhome.refrigeration is Refrigeration.FRIDGE_FREEZER


def test_an_unnamed_heating_system_is_left_unread_and_narrated(comparator: str) -> None:
    """`WEBASTO 4 kW DIESEL` says the fuel and the output, neither of which settles it."""
    roster = {entry.key: entry for entry in parse_roster(comparator)}
    heading, columns = _columns_of(3, [entry.key for entry in roster.values()])
    said: list[str] = []
    built = rapido._build(
        roster["v64"], columns[heading.index("v64")], "https://x?a=b", said.append
    )
    assert built.motorhome.heating is None
    assert "heating left unread" in built.provenance["heating"].snippet
    assert any("heating left unread" in line for line in said)


def test_the_positional_fields_are_reviewer_pointers(comparator: str) -> None:
    roster = {entry.key: entry for entry in parse_roster(comparator)}
    heading, columns = _columns_of(2, [entry.key for entry in roster.values()])
    built = rapido._build(
        roster["v55"], columns[heading.index("v55")], "https://x?a=b", lambda _m: None
    )
    for field in ("sleeping_area", "kitchen_location", "lounge_location", "bathroom_layout"):
        assert built.provenance[field].reviewer_reference
        assert built.provenance[field].source_url.endswith("v55.chtml")


def test_no_price_is_ever_emitted(comparator: str) -> None:
    """Rapido publish none, and no importer sets one; see the module docstring."""
    roster = {entry.key: entry for entry in parse_roster(comparator)}
    heading, columns = _columns_of(24, [entry.key for entry in roster.values()])
    built = rapido._build(
        roster["i96malde"], columns[heading.index("i96malde")], "https://x?a=b", lambda _m: None
    )
    assert built.motorhome.rrp_pounds is None
    assert built.motorhome.price_min_range_pounds is None
    assert built.motorhome.price_max_range_pounds is None
    assert "rrp_pounds" not in built.provenance


# --- matching -------------------------------------------------------------------------


def test_identity_is_blind_to_where_rapido_put_the_space() -> None:
    assert identity_key("V65 XL") == identity_key("V65XL") == "v65xl"
    assert identity_key("i96M TRUMA") == "i96mtruma"


#: What this adapter emits, against what FMLV held before the 28 October 2026 correction.
_AGAINST_THE_OLD_EXPORT = (
    (("SERIE C", "C03"), ("COMPACT", "C03")),
    (("SERIE C", "C86i"), ("COMPACT i", "C86i")),
    (("SERIE VANS", "V55"), ("VAN", "V55")),
    (("SERIE VANS", "V65 XL"), ("VAN", "V65XL")),
    (("SERIE 80dF", "8066dF"), ("SERIE 80dF", "8066dF ULTIMATE")),
    (("SERIE DISTINCTION", "i96M TRUMA"), ("SERIE DISTINCTION", "I96M")),
)

_RENAMES = Renames(ranges=RENAMED_RANGES, models=RENAMED_MODELS)


@pytest.mark.parametrize(("site", "old"), _AGAINST_THE_OLD_EXPORT)
def test_the_renames_rescue_what_the_old_export_would_have_orphaned(
    site: tuple[str, str], old: tuple[str, str]
) -> None:
    """Every one of these scored below the threshold before the rename was named.

    The review VM keeps its own export, so a run there against the uncorrected one is the
    case these entries exist for.
    """
    assert _jaccard(
        _identity_tokens(*_RENAMES.applied_to(*site)), _identity_tokens(*old)
    ) >= DEFAULT_THRESHOLD


def test_v65_xl_is_the_one_a_range_rename_could_not_rescue() -> None:
    """A disagreeing layout code is a hard zero, so the model had to be named too."""
    old = _identity_tokens("VAN", "V65XL")
    assert _jaccard(_identity_tokens("SERIE VANS", "V65 XL"), old) == pytest.approx(0.0)
    # Fixing only the range leaves the codes `v65` and `v65xl` still disagreeing.
    assert _jaccard(_identity_tokens("VAN", "V65 XL"), old) == pytest.approx(0.0)
    assert _jaccard(
        _identity_tokens(*RENAMED_MODELS[("SERIE VANS", "V65 XL")]), old
    ) == pytest.approx(1.0)


@pytest.mark.parametrize(("site", "_old"), _AGAINST_THE_OLD_EXPORT)
def test_a_rename_never_costs_anything_against_the_corrected_export(
    site: tuple[str, str], _old: tuple[str, str]
) -> None:
    """`token_similarity` takes the better of the two readings, so a stale entry is free.

    This is what the export has held since 28 October 2026, and why `cli.stale_renames`
    is expected to report every entry above as dead on the first run.
    """
    scraped = ExtractedMotorhome(
        motorhome=Motorhome(manufacturer_range=site[0], model=site[1])
    )
    held = Motorhome(manufacturer_range=site[0], model=site[1])
    assert token_similarity(
        scraped.motorhome, held, renames=_RENAMES
    ) == pytest.approx(1.0)
