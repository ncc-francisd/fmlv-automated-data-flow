"""ITINEO's parsing, against the pages and the guide page the sites served on 11 Nov 2026.

Pure parsing only: no network, no browser. `itineo-guide-page1.svg` is one captured
Calaméo page, already decompressed — the same artefact `rapido._svg_of` hands the parser
at run time.

The negative tests are the traps this guide actually laid: a column order that the page's
own reading order gets wrong, an equipment checklist laid out in the same ten columns, a
gross weight that is a choice rather than a figure, and one length written in private-use
glyphs that no parser can read.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters import itineo, rapido

FIXTURES = Path(__file__).parent / "fixtures"

#: The order the guide's ten columns are actually in, established in the survey and
#: confirmed against every model page's own published height.
EXPECTED_ORDER = (
    "CM660", "CJ660", "SBD700", "JC740", "MC740",
    "SB740", "PF600", "PJ700", "PS740", "PM740",
)


def _text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def guide_rows_page1() -> tuple[rapido._Row, ...]:
    return rapido.page_cells(_text("itineo-guide-page1.svg"))


@pytest.fixture
def index() -> str:
    return _text("itineo-index.html")


@pytest.fixture
def documents() -> str:
    return _text("itineo-documents.html")


@pytest.fixture
def pf600() -> str:
    return _text("itineo-model-pf600.html")


@pytest.fixture
def sbd700() -> str:
    return _text("itineo-model-sbd700.html")


# --------------------------------------------------------------------------- #
# The site
# --------------------------------------------------------------------------- #


def test_the_index_lists_the_ten_models(index: str) -> None:
    roster = itineo.parse_roster(index)

    assert set(roster) == set(EXPECTED_ORDER)
    assert len(roster) == itineo.EXPECTED_PRODUCTS


def test_the_specifications_book_is_told_from_the_catalogue(documents: str) -> None:
    """Two Calaméo books sit side by side and only one holds figures.

    The specifications anchor carries `id="itineo-dl-gt-*"` — `gt` for *guide technique* —
    and the catalogue beside it is `itineo-dl-catalogue-*`, 88 pages of photographs.
    """
    url = itineo.technical_guide_url(documents)

    assert url is not None
    assert "calameo.com" in url
    assert "007692732cc45a1d22052" in url
    assert "itineo-dl-catalogue" in documents, "the catalogue should still be there to confuse"


def test_rapidos_own_guide_finder_does_not_match_this_one(documents: str) -> None:
    """Which is why this module has its own. Rapido keys on a `TECHNICAL GUIDE` heading."""
    assert rapido.technical_guide_url(documents) is None


def test_a_page_without_the_anchor_yields_nothing() -> None:
    assert itineo.technical_guide_url("<html>no documents here</html>") is None
    assert itineo.technical_guide_url('<a id="itineo-dl-gt-x" href="/local.pdf">x</a>') is None


# --------------------------------------------------------------------------- #
# The guide's columns
# --------------------------------------------------------------------------- #


def test_the_column_order_comes_from_the_headings_x(
    guide_rows_page1: tuple[rapido._Row, ...],
) -> None:
    assert itineo.column_order(guide_rows_page1) == EXPECTED_ORDER


def test_the_pages_reading_order_would_get_it_wrong(
    guide_rows_page1: tuple[rapido._Row, ...],
) -> None:
    """The reason `column_order` sorts elements by x rather than trusting `page_cells`.

    The ten codes are staggered across two lines and some share one `<text>` element, so
    the `(y, x)` sort interleaves them. If this ever stops differing, the x sort has
    become unnecessary — but it has not.
    """
    reading_order = tuple(
        cell.strip().upper().replace(" ", "")
        for row in guide_rows_page1
        if row.cells and all(itineo._CODE.match(c.strip()) for c in row.cells)
        for cell in row.cells
    )

    assert set(reading_order) == set(EXPECTED_ORDER)
    assert reading_order != EXPECTED_ORDER


def test_rapidos_heading_partition_does_not_transfer(
    guide_rows_page1: tuple[rapido._Row, ...],
) -> None:
    """Rapido glues the heading line above its first section; Itineo's codes are not there.

    `rapido.heading_key` anchors on `VEHICLE DIMENSIONS`, and this guide spells it
    `VEHICULE DIMENSIONS`, the French way — so it finds no heading line at all.
    """
    assert rapido.heading_key(guide_rows_page1) is None


# --------------------------------------------------------------------------- #
# The guide's rows
# --------------------------------------------------------------------------- #


def _table(rows: tuple[rapido._Row, ...]) -> dict[str, tuple[str, ...]]:
    return {
        row.label.lower().rstrip(" :"): row.values
        for row in itineo.guide_rows(rows, len(EXPECTED_ORDER))
    }


def test_the_masses_are_read_for_all_ten(guide_rows_page1: tuple[rapido._Row, ...]) -> None:
    table = _table(guide_rows_page1)

    assert table["mass in running order (miro) (kg)"] == (
        "2900", "2935", "2995", "3070", "3085", "3075", "2780", "2975", "3070", "3125",
    )
    assert table["payload (kg)"] == (
        "600", "565", "505", "430", "415", "425", "720", "525", "430", "375",
    )


def test_every_published_pair_sums_to_the_light_gross_weight(
    guide_rows_page1: tuple[rapido._Row, ...],
) -> None:
    """The self-check, and it is unusually strong: ten for ten, exactly.

    It also settles that the light chassis is the base vehicle, because the payloads are
    computed against 3,500 kg and not against the 4.4-tonne option.
    """
    table = _table(guide_rows_page1)
    miro = [int(v) for v in table["mass in running order (miro) (kg)"]]
    payload = [int(v) for v in table["payload (kg)"]]

    assert [a + b for a, b in zip(miro, payload, strict=True)] == [3500] * 10


def test_the_width_taken_is_the_one_without_mirrors(
    guide_rows_page1: tuple[rapido._Row, ...],
) -> None:
    """Itineo publish both, adjacent, and the cross-manufacturer rule wants the body."""
    table = _table(guide_rows_page1)

    assert table["overall width (excluding wing mirrors)"][0] == "2.19"
    assert table["overall width with wing mirrors open"][0] == "2.56"
    assert "overall width (excluding wing mirrors)" in itineo._METRES_ROWS
    assert "overall width with wing mirrors open" not in itineo._METRES_ROWS


def test_the_gross_weight_is_a_choice_and_is_read_as_a_set(
    guide_rows_page1: tuple[rapido._Row, ...],
) -> None:
    """`LIGHT: 3.5 T` and `HEAVY: 4.4 T`, spread across a dozen fragments.

    There is no column to attribute them to, which is why `guide_rows` falls back to
    gathering fragments and `_apply_guide` offers the set to every model.
    """
    rows = itineo.guide_rows(guide_rows_page1, len(EXPECTED_ORDER))
    gross = next(r for r in rows if "gross vehicle weight" in r.label.lower())

    assert any("3.5" in value for value in gross.values)
    assert len(gross.values) != len(EXPECTED_ORDER)


def test_one_length_is_written_in_private_use_glyphs_and_is_refused(
    guide_rows_page1: tuple[rapido._Row, ...],
) -> None:
    """Column nine's length is `.` — font substitution, not a number.

    Nothing can read it, so it must convert to `None` rather than to a plausible figure.
    """
    table = _table(guide_rows_page1)
    lengths = table["overall length"]

    assert len(lengths) == len(EXPECTED_ORDER)
    unreadable = lengths[EXPECTED_ORDER.index("PS740")]
    assert itineo._metres_to_mm(unreadable) is None
    assert itineo._metres_to_mm(lengths[EXPECTED_ORDER.index("PF600")]) == 5990


# --------------------------------------------------------------------------- #
# The model pages
# --------------------------------------------------------------------------- #


def test_berths_take_the_standard_figure_not_the_span(pf600: str) -> None:
    """`Number of possible sleeping spaces  2(+1+1 opt)`, and the prose agrees.

    Itineo split the options out themselves, which is what makes this easy where Robeta's
    spans were not.
    """
    product = itineo.parse_model_page(pf600, "PF600", "https://example.invalid")

    assert product.berths == 2
    assert product.berths_note is not None and "opt" in product.berths_note


def test_the_prose_and_the_headline_agree_on_the_standard(pf600: str) -> None:
    """*"Up to 4 berths (including 2 as an option)"* is the same 2, said twice."""
    assert "including 2 as an option" in " ".join(pf600.split())

    product = itineo.parse_model_page(pf600, "PF600", "https://example.invalid")
    assert product.berths_note is not None
    assert "but the prose says" not in product.berths_note


def test_a_model_with_no_optional_berths_reads_straight_through(sbd700: str) -> None:
    product = itineo.parse_model_page(sbd700, "SBD700", "https://example.invalid")

    assert product.berths == 6


def test_the_model_page_height_is_kept_for_the_alignment_check(pf600: str) -> None:
    product = itineo.parse_model_page(pf600, "PF600", "https://example.invalid")

    assert product.page_height_mm == 2880


def test_a_misaligned_column_is_caught_by_the_model_pages_own_height(pf600: str) -> None:
    """The guard that makes the column order trustworthy.

    A wrong order would still give every model a plausible Itineo height, and nothing
    downstream would notice. The model pages publish a height each, independently.
    """
    product = itineo.parse_model_page(pf600, "PF600", "https://example.invalid")
    product.mh_height_mm = 2980  # as if the column order had slipped by one

    messages: list[str] = []
    assert not itineo._check_alignment(product, messages.append)
    assert messages and "columns are not where" in messages[0]

    product.mh_height_mm = 2880
    assert itineo._check_alignment(product, messages.append)


# --------------------------------------------------------------------------- #
# Ranges, price and wiring
# --------------------------------------------------------------------------- #


def test_the_three_ranges_match_what_fmlv_holds() -> None:
    """COZI for the P models, FAMILI COMPACT for the 660s, FAMILI for the rest.

    Getting this wrong proposes a rename on every product at once, because the range is
    part of how a scraped product is matched to its row.
    """
    assert itineo.range_of("PF600") == "COZI"
    assert itineo.range_of("PM740") == "COZI"
    assert itineo.range_of("CJ660") == "FAMILI COMPACT"
    assert itineo.range_of("CM660") == "FAMILI COMPACT"
    assert itineo.range_of("SBD700") == "FAMILI"
    assert itineo.range_of("JC740") == "FAMILI"


def test_no_price_is_ever_proposed(pf600: str) -> None:
    """Itineo publish none, and FMLV's rows carry dealer-sourced figures.

    A field with no provenance is not proposed, which is what keeps those alive. Emitting
    an empty one would propose deleting them.
    """
    product = itineo.parse_model_page(pf600, "PF600", "https://example.invalid")
    product.mro_kilograms, product.mh_payload_kilograms = 2780, 720
    extracted = itineo._build_extracted_motorhome(product)

    assert extracted.motorhome.rrp_pounds is None
    assert "rrp_pounds" not in extracted.provenance
    assert "£" not in pf600


def test_no_mtplm_is_proposed_either(pf600: str) -> None:
    """The guide gives a choice of chassis, not this model's own gross weight."""
    product = itineo.parse_model_page(pf600, "PF600", "https://example.invalid")
    product.gross_weights = {3500, 3650}
    extracted = itineo._build_extracted_motorhome(product)

    assert extracted.motorhome.mtplm_kilograms is None
    assert "mtplm_kilograms" not in extracted.provenance


def test_the_manufacturer_is_the_exports_capitals() -> None:
    """FMLV's export spells both columns `ITINEO`, and so does the NCC list at id 128."""
    assert itineo.MANUFACTURER == "ITINEO"
    assert itineo.MANUFACTURER_DISPLAY_NAME == "ITINEO"


def test_every_model_is_offered_to_the_range_flag() -> None:
    assert {label for _, label in itineo.DEFAULT_RANGES} == set(EXPECTED_ORDER)
    assert len(itineo.DEFAULT_RANGES) == itineo.EXPECTED_PRODUCTS
