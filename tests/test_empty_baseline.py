"""`fmlv empty-baseline`, which lets a brand FMLV holds nothing for be run at all.

`cli.latest_export` raises rather than assuming an empty baseline, and rightly — that guard
is what stops a forgotten `fetch-export` turning every product of an established
manufacturer into a duplicate. A genuinely new brand has no export to forget, though, and
without a file there is nothing to diff against and no way to produce the first upload.

Atom is the case that needed it: launched September 2026 with no FMLV rows at all.

No network here.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest

from src.cli import DEFAULT_VEHICLE_CLASS, CommandError, empty_baseline, latest_export
from src.product_model import io
from src.registry.models import Manufacturer
from src.vehicle_class import VehicleClass
from tests.test_cli import make_manufacturer


def _manufacturer() -> Manufacturer:
    """Atom as the registry holds it — the case this command was written for."""
    return make_manufacturer(
        manufacturer_id=278,
        fmlv_manufacturer="Trigano",
        fmlv_display_name="Atom",
        ncc_supplier_name="Atom",
        website_url="https://atommotorhomes.com/",
    )


def test_it_writes_a_file_latest_export_will_accept(tmp_path: Path) -> None:
    """The whole point: the run can start where it otherwise refuses to."""
    with pytest.raises(CommandError, match="no .* export"):
        latest_export(
            root=tmp_path, manufacturer_id=278, manufacturer_name="Trigano"
        )

    written = empty_baseline(manufacturer=_manufacturer(), data_root=tmp_path)

    assert latest_export(
        root=tmp_path, manufacturer_id=278, manufacturer_name="Trigano"
    ) == written


def test_the_baseline_it_writes_is_empty_and_valid(tmp_path: Path) -> None:
    """Header row and nothing else — parsed, not merely written."""
    written = empty_baseline(manufacturer=_manufacturer(), data_root=tmp_path)

    result = io.read_export(written)

    assert list(result.motorhomes) == []
    assert result.issues == []


def test_it_lands_where_the_manufacturer_s_exports_go(tmp_path: Path) -> None:
    """Same `<id>_<name>` directory a real export would, so the two are interchangeable."""
    written = empty_baseline(
        manufacturer=_manufacturer(), data_root=tmp_path, today=date(2026, 9, 16)
    )

    assert written.parent.name == "278_Trigano"
    assert written.name == "2026-09-16_Trigano_motorhome-campervans.xlsx"


def test_a_real_export_supersedes_it(tmp_path: Path) -> None:
    """`latest_export` takes the newest file, so nothing has to be deleted afterwards.

    **It sorts on the modification time, not the date in the filename**, so the two are
    written a clear hour apart. Writing them back to back made this test flaky: the
    placeholder and the export it is meant to supersede landed within the same filesystem
    timestamp tick, `max` returned whichever it saw first, and the run failed perhaps one
    time in fifty. Real exports arrive days apart, so the race is the test's alone.
    """
    empty = empty_baseline(
        manufacturer=_manufacturer(), data_root=tmp_path, today=date(2026, 9, 16)
    )
    real = empty.with_name("2026-10-01_Trigano_motorhome-campervans.xlsx")
    real.write_bytes(empty.read_bytes())

    placeholder_written = empty.stat().st_mtime
    os.utime(real, (placeholder_written + 3600, placeholder_written + 3600))

    chosen = latest_export(root=tmp_path, manufacturer_id=278, manufacturer_name="Trigano")

    assert chosen == real


def test_a_caravan_baseline_uses_the_caravan_schema(tmp_path: Path) -> None:
    """The two schemas share a file format and almost no columns."""
    written = empty_baseline(
        manufacturer=_manufacturer(),
        data_root=tmp_path,
        vehicle_class=VehicleClass.CARAVAN,
    )

    assert "touring-caravans" in written.name
    assert DEFAULT_VEHICLE_CLASS is not VehicleClass.CARAVAN
