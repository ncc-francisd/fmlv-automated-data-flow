"""Tests for the Marquis Leisure page reader, shared by four Trigano brands.

Marquis are the sole UK importer for Benimar, Elnagh, Mobilvetta and Panama and publish one
range page per range, so what is common lives here rather than in any one adapter. These
cover the parts every brand leans on; the brand-specific readings are in each adapter's own
test file.

Fixtures are real importer pages — see `docs/adapters/benimar.md` and `elnagh.md`.

No network here.
"""

from __future__ import annotations

from pathlib import Path

from src.adapters.marquis import (
    bed_lines,
    equipment_lines,
    lines_for_layout,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _page(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# The bed list, which each brand writes differently
# --------------------------------------------------------------------------- #


def test_the_beds_come_from_the_layouts_own_list() -> None:
    """A page is a range, so a bed named in the equipment list could be another layout's."""
    assert bed_lines(
        "Bed Sizes Double Drop Down Bed 1400mm x 1900mm | 4'6'' x 6'2'' "
        "Double Rear Bed 1390mm x 2000mm | 4'6'' x 6'6'' # Garage dimensions"
    ) == ["Double Drop Down Bed", "Double Rear Bed"]


def test_a_bed_name_containing_an_x_survives() -> None:
    """Excluding `x` from a bed's name turned `FIXED REAR BED` into `ED REAR BED`."""
    assert bed_lines("Bed Sizes FIXED REAR BED 1390mm X 2000mm | 4'6'' X 6'6''") == [
        "FIXED REAR BED"
    ]


def test_an_optional_bed_is_not_read_as_standard() -> None:
    """Both Benivan layouts offer an elevating roof bed the buyer may not have bought."""
    beds = bed_lines(
        "Bed Sizes Double Rear Bed 1860mm x 1490mm | 6'1'' x 4'8'' "
        "Optional Elevating Roof Bed 2000mm x 1300mm | 6'5'' x 4'2''"
    )

    assert beds == ["Double Rear Bed"]


def test_the_equipment_list_never_contributes_a_bed() -> None:
    assert not any(
        "bed" in line.lower() for line in equipment_lines(_page("benimar_primero.html"))
    )


def test_a_size_suffixed_only_on_the_last_figure_is_read() -> None:
    """Elnagh write `1900 x 810mm` where Benimar write `1400mm × 1900mm`.

    Requiring the suffix on the first figure found none of Elnagh's four drop-down beds.
    """
    assert bed_lines("Bed Sizes DROP DOWN BED 1900 x 810mm / 6'2\" x 2'6\"") == [
        "DROP DOWN BED"
    ]


def test_a_three_dimensional_size_is_read() -> None:
    assert bed_lines("Bed Sizes DOUBLE REAR BED 1300 x 1100 x 1900mm / 4'3'' x 3'6''") == [
        "DOUBLE REAR BED"
    ]


def test_a_count_in_front_of_the_size_is_read() -> None:
    """Benimar's `Single Rear Bed 2 x 800mm × 2100mm` — two singles, one entry."""
    assert bed_lines("Bed Sizes Single Rear Bed 2 x 800mm × 2100mm") == ["Single Rear Bed"]


def test_a_block_with_no_bed_list_yields_nothing() -> None:
    assert bed_lines("BERTHS 4 BELTS 4 OVERALL LENGTH 6590mm") == []


# --------------------------------------------------------------------------- #
# The equipment list, which qualifies itself per layout
# --------------------------------------------------------------------------- #


def test_an_unqualified_line_reaches_every_layout() -> None:
    lines = ["Truma CP Plus with LCD control panel"]

    assert lines_for_layout(lines, "530") == lines
    assert lines_for_layout(lines, "286") == lines


def test_a_named_layout_list_restricts_the_line() -> None:
    """Elnagh's form, and the one place it changes an answer rather than shading it."""
    lines = ["Separate shower and toilet compartment (579 and 573 only)"]

    assert lines_for_layout(lines, "573") == lines
    assert lines_for_layout(lines, "530") == []


def test_an_exclusion_qualifier_is_honoured() -> None:
    """Benimar's form: `(excl 286)` means every layout but that one."""
    lines = ["145 litre fridge/freezer with automatic energy selection (excl 286)"]

    assert lines_for_layout(lines, "201") == lines
    assert lines_for_layout(lines, "286") == []


def test_a_parenthesis_that_is_not_a_layout_list_is_left_alone() -> None:
    """A qualifier must be nothing but layout codes and the words joining them."""
    lines = [
        "Large external garage with lighting, heating & 230v socket",
        "OVERALL WIDTH (MIRRORS FOLDED) 2350mm",
        "MAX USER PAYLOAD (3500KG CHASSIS) Manual 590kg",
        "Thetford cassette toilet with electric flush & 18 litre wheeled holding tank",
    ]

    assert lines_for_layout(lines, "530") == lines
