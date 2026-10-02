"""`fmlv show-baseline` — what a run on this machine would actually diff against.

Added 2 October 2026. A stale baseline is invisible: a run matching against an export
taken hours earlier looks exactly like one matching against the current data, and reports
products as missing from the manufacturer's site that FMLV no longer holds. Telling the
two apart took four rounds of exporting by hand and comparing by eye.
"""

from __future__ import annotations

from pathlib import Path

from src.cli import main
from src.product_model.io import write_csv
from src.product_model.model import Motorhome


def _carado_export(root: Path) -> Path:
    export = root / "exports" / "92_Carado" / "2026-10-02_Carado_motorhome-campervans.csv"
    export.parent.mkdir(parents=True, exist_ok=True)
    write_csv(
        [
            Motorhome(
                product_id=9017,
                year=2027,
                manufacturer="Carado",
                manufacturer_range="Campervan",
                model="CV640",
                base_vehicle_manufacturer="Peugeot",
            ),
            # The NCC export filters supplier by substring, so Bodans' `Caradon XL`
            # arrives inside Carado's export — twice. A run drops it; so must this.
            Motorhome(
                product_id=8892,
                year=2027,
                manufacturer="Bodans",
                manufacturer_range="Boxer",
                model="Caradon XL",
            ),
        ],
        export,
    )
    return export


def test_it_prints_the_file_and_when_it_was_written(tmp_path, capsys) -> None:
    """**The question the command exists to answer.** Without the timestamp there is no
    way to tell a fresh baseline from one downloaded hours earlier."""
    _carado_export(tmp_path)

    exit_code = main(["show-baseline", "Carado", "--data-dir", str(tmp_path)])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "2026-10-02_Carado_motorhome-campervans" in out
    assert "written" in out
    assert "whatever was on disk" in out


def test_it_applies_the_same_filters_a_run_does(tmp_path, capsys) -> None:
    """It is only trustworthy if what it prints is what a run would see, so it reports the
    baseline after the manufacturer, archived and model-year filters — not the row count
    of the file."""
    _carado_export(tmp_path)

    main(["show-baseline", "Carado", "--data-dir", str(tmp_path)])

    out = capsys.readouterr().out
    assert "rows in the file              2" in out
    assert "BASELINE A RUN WOULD USE      1" in out


def test_another_manufacturer_in_the_export_is_named_not_just_counted(tmp_path, capsys) -> None:
    """Carado's export carries Bodans' `Caradon XL`, because the NCC site matches the
    supplier name as a substring. Saying whose it is turns a puzzling number into an
    explanation."""
    _carado_export(tmp_path)

    main(["show-baseline", "Carado", "--data-dir", str(tmp_path)])

    out = capsys.readouterr().out
    assert "not Carado, dropped" in out
    assert "Bodans" in out


def test_the_rows_themselves_are_printed(tmp_path, capsys) -> None:
    _carado_export(tmp_path)

    main(["show-baseline", "Carado", "--data-dir", str(tmp_path)])

    out = capsys.readouterr().out
    assert "9017" in out
    assert "CV640" in out
    assert "Caradon XL" not in out.split("BASELINE A RUN WOULD USE")[1]


def test_an_unknown_manufacturer_is_an_error_not_a_traceback(tmp_path, capsys) -> None:
    """It names the manufacturers it does know, so a typo is self-correcting."""
    exit_code = main(["show-baseline", "Nobody At All", "--data-dir", str(tmp_path)])

    assert exit_code != 0
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert "Carado" in err
