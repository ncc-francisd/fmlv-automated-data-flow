"""The upload CSV has to survive Excel, or an accent becomes a second manufacturer.

`Citroën` written as UTF-8 with no byte-order mark opens in Excel on a UK Windows machine
as `CitroÃ«n`. Save from there and the damage is real; upload it and FMLV gains a base
vehicle manufacturer that no filter ever joins back to the first. That is what happened to
Carado, reported 2 October 2026.
"""

from __future__ import annotations

import csv
from pathlib import Path

from src.adapters.base import fmlv_base_vehicle, repair_mojibake
from src.product_model.caravan import Caravan
from src.product_model.io import write_csv
from src.product_model.model import Motorhome
from src.product_model.caravan_io import write_csv as write_caravan_csv

CITROEN = "Citroën"
#: The same string after a UTF-8 file has been read as Windows-1252.
MANGLED = "CitroÃ«n"


def _motorhome() -> Motorhome:
    return Motorhome(
        manufacturer="Carado",
        manufacturer_display_name="Carado",
        manufacturer_range="Alcoves PRO",
        model="A132",
        base_vehicle_manufacturer=CITROEN,
    )


# --- the writer -----------------------------------------------------------------------


def test_the_upload_csv_opens_in_excel_with_its_accents_intact(tmp_path: Path) -> None:
    """**The trap this exists for.** Three bytes at the front of the file are what tells
    Excel the thing is UTF-8."""
    path = tmp_path / "upload.csv"

    write_csv([_motorhome()], path, leading_blank_rows=2)

    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), "no byte-order mark: Excel will read this as 1252"
    assert CITROEN.encode("utf-8") in raw


def test_the_caravan_upload_is_written_the_same_way(tmp_path: Path) -> None:
    path = tmp_path / "caravans.csv"

    write_caravan_csv(
        [
            Caravan(
                manufacturer="Adria Mobil",
                manufacturer_display_name="Adria",
                manufacturer_range="Altea",
                model="622 DK",
            )
        ],
        path,
        leading_blank_rows=2,
    )

    assert path.read_bytes().startswith(b"\xef\xbb\xbf")


def test_the_mark_does_not_reach_the_first_cell(tmp_path: Path) -> None:
    """The FMLV upload site reads row 1 as a single `-`. A reader that knows about the
    mark strips it; this pins that ours does, so the rows are what they look like."""
    path = tmp_path / "upload.csv"

    write_csv([_motorhome()], path, leading_blank_rows=2)

    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))

    assert rows[0] == ["-"]
    assert rows[1] == ["-"]
    assert rows[2][0] == "product_id"


def test_excel_round_trip_is_what_breaks_it() -> None:
    """Not a test of our code — a test of the claim the fix rests on, so nobody has to
    re-derive it. This is exactly the string the requester saw in his spreadsheet."""
    assert CITROEN.encode("utf-8").decode("cp1252") == MANGLED


# --- the repair -----------------------------------------------------------------------


def test_a_mangled_make_is_repaired_rather_than_recorded() -> None:
    """A manufacturer's own page can be served with the wrong charset, and a spreadsheet
    round-tripped through Excel carries the damage in its cells."""
    assert repair_mojibake(MANGLED) == CITROEN
    assert fmlv_base_vehicle(MANGLED) == CITROEN


def test_other_accented_makes_repair_too() -> None:
    assert repair_mojibake("BÃ¼rstner") == "Bürstner"


def test_an_undamaged_value_is_left_exactly_alone() -> None:
    for value in (CITROEN, "Citroen", "Fiat", "Peugeot", "Mercedes-Benz", "VW", ""):
        assert repair_mojibake(value) == value


def test_a_string_that_does_not_reverse_cleanly_is_not_mangled_further() -> None:
    """Only reversed where it round-trips exactly, so a real name carrying one of these
    letters survives rather than being broken the other way."""
    assert repair_mojibake("Ã") == "Ã"
    assert repair_mojibake("AÃZ") == "AÃZ"
