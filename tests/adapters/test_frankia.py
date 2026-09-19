"""Frankia parsing, against the real pages captured in `fixtures/`.

Pure parsing only — no network. Every trap in the module docstring has a test here, and
each of the two that actually dropped a layout on the first live run has its own.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters import frankia
from src.adapters.frankia import (
    EUR_PER_GBP_RATE,
    EXPECTED_LAYOUTS,
    LAYOUTS,
    RENAMED_MODELS,
    ROSTER_WITHOUT_A_PAGE,
    FrankiaMotorhome,
    _match_heading,
    _reconciles,
    body_type_from,
    check_roster,
    columns_in,
    parse_layout_blocks,
    spec_blocks,
    visible_lines,
)
from src.product_model.enums import BodyType

FIXTURES = Path(__file__).parent / "fixtures"


def _lines(name: str) -> list[str]:
    return (FIXTURES / name).read_text(encoding="utf-8").splitlines()


@pytest.fixture
def noctra_cruiser() -> list[str]:
    return _lines("frankia_noctra_cruiser_text.txt")


@pytest.fixture
def now() -> list[str]:
    return _lines("frankia_now_text.txt")


@pytest.fixture
def neo_liner() -> list[str]:
    return _lines("frankia_neo_liner_text.txt")


@pytest.fixture
def final_edition() -> list[str]:
    return _lines("frankia_final_edition_text.txt")


@pytest.fixture
def overcab() -> list[str]:
    return _lines("frankia_together_overcab_text.txt")


# --- identity and roster ------------------------------------------------------------


def test_the_manufacturer_matches_the_export() -> None:
    assert frankia.MANUFACTURER == "Frankia"
    assert frankia.MANUFACTURER_DISPLAY_NAME == "Frankia"


def test_the_roster_is_twenty_of_which_sixteen_are_readable() -> None:
    """Twenty layouts in the Highlights spread; the three Mercedes Final Editions have no
    page, and the Noctra Cruiser's two platform variants share one FMLV name."""
    assert EXPECTED_LAYOUTS == 20
    assert len(LAYOUTS) == 16
    assert len(ROSTER_WITHOUT_A_PAGE) == 3


def test_the_transcribed_roster_still_matches_the_published_spread() -> None:
    """`LAYOUTS` is transcribed from pages 42-43, so it has to answer for itself. This is
    what turns next year's re-organisation into a loud failure rather than a quiet one."""
    spread = (FIXTURES / "frankia_highlights_2027_roster.txt").read_text(encoding="utf-8")

    missing, _unexpected = check_roster(spread)

    assert missing == []


def test_the_spread_names_the_ranges_that_are_gone() -> None:
    """Titan, Platin, F-Line and M-Line are not MY2027 ranges — which is the finding that
    turns 24 rows into disappearances."""
    spread = (FIXTURES / "frankia_highlights_2027_roster.txt").read_text(encoding="utf-8").upper()

    assert "NOCTRA" in spread
    assert "TITAN" not in spread
    assert "PLATIN" not in spread
    assert "M-LINE" not in spread


def test_every_rename_moves_a_layout_rather_than_inventing_one() -> None:
    """A rename says what the site now calls a row FMLV still holds. Each target must be
    a real FMLV identity, and each source must be a layout this adapter actually emits."""
    emitted = {(layout.range_name, layout.model) for layout in LAYOUTS}

    for source in RENAMED_MODELS:
        assert source in emitted, f"{source} is renamed but never collected"


# --- the two traps that dropped a layout on the first live run ----------------------


def test_a_heading_with_a_tagline_still_matches(now: list[str]) -> None:
    """The NOW page heads its only block `FRANKIA NOW 7.0 L – A NOW AGE OF SPACE`. An
    exact match dropped the layout entirely on the first run."""
    blocks = parse_layout_blocks(now)

    assert "FRANKIA NOW 7.0 L" not in blocks
    assert _match_heading(blocks, "FRANKIA NOW 7.0 L") is not None


def test_an_ambiguous_prefix_matches_nothing() -> None:
    """What keeps the prefix match safe: two siblings sharing a prefix return neither."""
    blocks = {"FRANKIA NEO Liner 7.0 L": object(), "FRANKIA NEO Liner 7.0 LX": object()}

    assert _match_heading(blocks, "FRANKIA NEO Liner 7.0 L") is blocks[
        "FRANKIA NEO Liner 7.0 L"
    ]
    assert _match_heading(blocks, "FRANKIA NEO Liner 7.0") is None


def test_the_noctra_cruiser_states_two_platforms_in_one_block(
    noctra_cruiser: list[str],
) -> None:
    """The other first-run drop. Mercedes and Fiat sit side by side, so every label has
    two values and `lines[i + 1]` reads a bare `314` where the unit is on the next line."""
    (_heading, values), = spec_blocks(noctra_cruiser)

    assert columns_in(values) == 2
    assert values["Total height"] == ["314", "312 cm"]


def test_both_noctra_columns_read(noctra_cruiser: list[str]) -> None:
    """Column 0 is the Mercedes, column 1 the Fiat, and the bare figure still parses."""
    mercedes = parse_layout_blocks(noctra_cruiser, column=0)["FRANKIA NOCTRA CRUISER 7.6 L"]
    fiat = parse_layout_blocks(noctra_cruiser, column=1)["FRANKIA NOCTRA CRUISER 7.6 L"]

    assert (mercedes.mh_height_mm, fiat.mh_height_mm) == (3140, 3120)
    assert mercedes.base_vehicle == "Mercedes"
    assert fiat.base_vehicle == "Fiat"


# --- the spec block -----------------------------------------------------------------


def test_five_spellings_of_one_heading_are_all_found(
    noctra_cruiser: list[str], now: list[str], final_edition: list[str], overcab: list[str]
) -> None:
    """`Technical Overview`, `Technology Overview`, `Technology overview`, `Technical
    overview`. Matching one of them finds half the pages and silently loses the rest."""
    assert len(spec_blocks(noctra_cruiser)) == 1
    assert len(spec_blocks(now)) == 1
    assert len(spec_blocks(final_edition)) == 3
    assert len(spec_blocks(overcab)) == 2


def test_the_heading_is_the_last_frankia_line_not_the_line_above(
    final_edition: list[str],
) -> None:
    """The line directly above every block is marketing copy. Scanning back for the last
    `FRANKIA …` line is what made the Final Edition, Titan, Platin and NOW pages read."""
    headings = [heading for heading, _ in spec_blocks(final_edition)]

    assert headings == [
        "FRANKIA FINAL EDITION I 640 SD",
        "FRANKIA FINAL EDITION I 740 GD",
        "FRANKIA FINAL EDITION I 790 GDW",
    ]


def test_three_layouts_on_one_page_keep_their_own_figures(
    final_edition: list[str],
) -> None:
    blocks = parse_layout_blocks(final_edition)

    assert blocks["FRANKIA FINAL EDITION I 640 SD"].mh_length_mm == 6450
    assert blocks["FRANKIA FINAL EDITION I 740 GD"].mh_length_mm == 7540
    assert blocks["FRANKIA FINAL EDITION I 790 GDW"].mh_length_mm == 7860


def test_both_thousands_separators_on_one_page(neo_liner: list[str]) -> None:
    """The NEO Liner 6.6 H states `4.500 kg` and `124.900 €` where its siblings on the
    same page state `4,500 kg` and `119,900 €`."""
    blocks = parse_layout_blocks(neo_liner)

    assert blocks["FRANKIA NEO Liner 6.6 H"].mtplm_kilograms == 4500
    assert blocks["FRANKIA NEO Liner 6.6 H"].price_eur == 124_900
    assert blocks["FRANKIA NEO Liner 7.0 L"].price_eur == 119_900


def test_the_lower_permissible_mass_is_recorded() -> None:
    """`3,500 | 4,500 kg` offers a paid uprating. The base vehicle is the lower figure,
    and FMLV holds 3500 for exactly these layouts."""
    lines = _lines("frankia_now_text.txt")
    figures = parse_layout_blocks(lines)["FRANKIA NOW 7.0 L – A NOW AGE OF SPACE"]

    assert figures.mtplm_kilograms == 3500


def test_the_overcab_page_is_reached_despite_its_german_path(overcab: list[str]) -> None:
    """Its URL is `/en/wohnmobile-reisemobile/...`, so a roster built by matching
    `/en/motorhomes-recreational-vehicles/` loses both Together Alcove layouts."""
    assert "/wohnmobile-reisemobile/" in frankia._TOGETHER_A

    blocks = parse_layout_blocks(overcab)
    assert blocks["FRANKIA TOGETHER A 680"].mh_length_mm == 7060
    assert blocks["FRANKIA TOGETHER A 740"].mh_length_mm == 7520


# --- body type ----------------------------------------------------------------------


def test_body_type_comes_from_the_pages_own_words(
    noctra_cruiser: list[str], overcab: list[str], neo_liner: list[str]
) -> None:
    """Not from the layout code, which does not settle it: FMLV holds `I 7400 GD` as an
    over-cab bed under M-Line and `Pure I 7400 GD` as an A-class under Platin."""
    assert body_type_from(noctra_cruiser, "")[0] is BodyType.COACH_BUILT_LOW_PROFILE
    assert body_type_from(overcab, "")[0] is BodyType.COACH_BUILT_OVER_CAB_BED
    assert body_type_from(neo_liner, "")[0] is BodyType.A_CLASS


def test_semi_integrated_is_not_read_as_integrated() -> None:
    """"semi-integrated" contains "integrated", and the pages use both words freely."""
    assert body_type_from(["A semi-integrated motorhome"], "")[0] is (
        BodyType.COACH_BUILT_LOW_PROFILE
    )


def test_a_page_that_says_nothing_proposes_no_body_type() -> None:
    assert body_type_from(["Some copy about kitchens"], "")[0] is None


# --- price and the weak self-check --------------------------------------------------


def test_euros_are_divided_by_the_rate(neo_liner: list[str]) -> None:
    figures = parse_layout_blocks(neo_liner)["FRANKIA NEO Liner 7.0 L"]
    product = FrankiaMotorhome(layout=LAYOUTS[5], figures=figures)

    assert EUR_PER_GBP_RATE == 1.15
    assert product.rrp_pounds == round(119_900 / 1.15)


def test_an_implausible_figure_drops_the_layout(neo_liner: list[str]) -> None:
    """There is no arithmetic self-check here — Frankia publishes no usable payload and
    no MY2027 MRO — so the guard is that the block is coherent and in range."""
    figures = parse_layout_blocks(neo_liner)["FRANKIA NEO Liner 7.0 L"]
    assert _reconciles(FrankiaMotorhome(layout=LAYOUTS[5], figures=figures))[0] is True

    figures.mh_length_mm = 706
    assert _reconciles(FrankiaMotorhome(layout=LAYOUTS[5], figures=figures))[0] is False


def test_a_block_missing_a_dimension_is_dropped(neo_liner: list[str]) -> None:
    figures = parse_layout_blocks(neo_liner)["FRANKIA NEO Liner 7.0 L"]
    figures.mtplm_kilograms = None

    ok, reason = _reconciles(FrankiaMotorhome(layout=LAYOUTS[5], figures=figures))
    assert ok is False
    assert "permissible mass" in reason


# --- the line split -----------------------------------------------------------------


def test_each_value_lands_on_its_own_line() -> None:
    assert visible_lines("<div>Total length</div><div>699 cm</div>") == [
        "Total length",
        "699 cm",
    ]
