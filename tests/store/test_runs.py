"""Tests for the run store: schema creation and the run lifecycle."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src import store


@pytest.fixture
def connection(tmp_path: Path) -> sqlite3.Connection:
    conn = store.connect(tmp_path / "runs.db")
    try:
        yield conn
    finally:
        conn.close()


def test_connect_creates_every_table(connection: sqlite3.Connection) -> None:
    tables = {
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    assert tables >= {
        "run",
        "source_snapshot",
        "product",
        "proposed_change",
        "decision",
        "verification",
    }


def test_connect_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "runs.db"
    first = store.connect(db_path)
    store.start_run(first, manufacturer_id=1, fmlv_manufacturer="Adria Mobil", trigger="manual")
    first.close()

    # Reconnecting must not wipe or fail on the existing schema/data.
    second = store.connect(db_path)
    try:
        assert len(store.list_runs(second)) == 1
    finally:
        second.close()


def test_start_run_records_running_status(connection: sqlite3.Connection) -> None:
    run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    assert run.status == "running"
    assert run.finished_at is None
    assert run.error_message is None
    assert run.trigger == "manual"


def test_finish_run_marks_succeeded(connection: sqlite3.Connection) -> None:
    run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    finished = store.finish_run(connection, run.id)
    assert finished.status == "succeeded"
    assert finished.finished_at is not None


def test_fail_run_records_error_message(connection: sqlite3.Connection) -> None:
    run = store.start_run(
        connection, manufacturer_id=46, fmlv_manufacturer="Morelo", trigger="scheduled"
    )
    failed = store.fail_run(connection, run.id, "site returned 503")
    assert failed.status == "failed"
    assert failed.error_message == "site returned 503"
    assert failed.finished_at is not None


def test_get_run_raises_for_unknown_id(connection: sqlite3.Connection) -> None:
    with pytest.raises(KeyError):
        store.get_run(connection, 999)


def test_list_runs_orders_most_recent_first(connection: sqlite3.Connection) -> None:
    first = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    second = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="scheduled"
    )
    runs = store.list_runs(connection, manufacturer_id=3)
    assert [run.id for run in runs] == [second.id, first.id]


def test_list_runs_filters_by_manufacturer(connection: sqlite3.Connection) -> None:
    store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    store.start_run(connection, manufacturer_id=46, fmlv_manufacturer="Morelo", trigger="manual")

    adria_runs = store.list_runs(connection, manufacturer_id=3)
    assert len(adria_runs) == 1
    assert adria_runs[0].fmlv_manufacturer == "Adria Mobil"


def test_list_runs_filters_by_status(connection: sqlite3.Connection) -> None:
    running = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    finished = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    store.finish_run(connection, finished.id)

    running_only = store.list_runs(connection, status="running")
    assert [run.id for run in running_only] == [running.id]


def test_list_runs_combines_manufacturer_and_status_filters(
    connection: sqlite3.Connection,
) -> None:
    store.start_run(connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual")
    morelo = store.start_run(
        connection, manufacturer_id=46, fmlv_manufacturer="Morelo", trigger="manual"
    )
    store.finish_run(connection, morelo.id)

    matches = store.list_runs(connection, manufacturer_id=46, status="succeeded")
    assert [run.id for run in matches] == [morelo.id]
    assert store.list_runs(connection, manufacturer_id=3, status="succeeded") == []


def test_list_run_manufacturers_returns_distinct_pairs_alphabetically(
    connection: sqlite3.Connection,
) -> None:
    store.start_run(connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual")
    store.start_run(connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual")
    store.start_run(connection, manufacturer_id=46, fmlv_manufacturer="Morelo", trigger="manual")

    assert store.list_run_manufacturers(connection) == [
        (3, "Adria Mobil"),
        (46, "Morelo"),
    ]


def test_invalid_trigger_is_rejected_by_the_schema(connection: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            """
            INSERT INTO run (manufacturer_id, fmlv_manufacturer, trigger, status, started_at)
            VALUES (1, 'Adria Mobil', 'not_a_real_trigger', 'running', '2026-01-01T00:00:00')
            """
        )


# --- What the run compared against (store.record_baseline) ---


def test_a_new_run_has_no_baseline_recorded_yet(connection: sqlite3.Connection) -> None:
    """All three read back `None` until the baseline has actually been built, so a run
    that failed during the export fetch cannot claim a baseline it never had."""
    run = store.start_run(
        connection, manufacturer_id=221, fmlv_manufacturer="Panama", trigger="manual"
    )
    assert run.baseline_supplier is None
    assert run.baseline_export is None
    assert run.baseline_count is None


def test_record_baseline_names_the_supplier_file_and_count(
    connection: sqlite3.Connection,
) -> None:
    r"""**Panama, 19 November 2026.** The run proposed `P\12+` and `P\50+` as new while
    FMLV held both live, because the registry named the importer's NCC supplier entry and
    that entry returns three Panama products where the brand's own returns five. Nothing
    on the run said which export it had used or how big it was."""
    run = store.start_run(
        connection, manufacturer_id=221, fmlv_manufacturer="Panama", trigger="manual"
    )
    recorded = store.record_baseline(
        connection,
        run.id,
        supplier_name="Marquis Leisure",
        export_path=r"data\exports\221_Panama\2026-11-19_Panama_motorhome-campervans.xlsx",
        product_count=3,
    )
    assert recorded.baseline_supplier == "Marquis Leisure"
    assert recorded.baseline_export.endswith("2026-11-19_Panama_motorhome-campervans.xlsx")
    assert recorded.baseline_count == 3
    # And it survives a re-read, which is what the review page does.
    assert store.get_run(connection, run.id).baseline_count == 3


def test_a_baseline_of_nothing_is_recorded_as_nothing(
    connection: sqlite3.Connection,
) -> None:
    """Zero is a fact and must not read as "not recorded" — a brand new to FMLV really
    does have an empty baseline (`fmlv empty-baseline`), and the page says so."""
    run = store.start_run(
        connection, manufacturer_id=999, fmlv_manufacturer="Atom", trigger="manual"
    )
    recorded = store.record_baseline(
        connection, run.id, supplier_name=None, export_path="empty.xlsx", product_count=0
    )
    assert recorded.baseline_count == 0
    assert recorded.baseline_supplier is None


def test_recording_a_baseline_leaves_the_rest_of_the_run_alone(
    connection: sqlite3.Connection,
) -> None:
    run = store.start_run(
        connection,
        manufacturer_id=25,
        fmlv_manufacturer="Coachman",
        trigger="scheduled",
        range_label="VIP",
        vehicle_class="caravan",
    )
    recorded = store.record_baseline(
        connection, run.id, supplier_name="Coachman Caravans", export_path="x.xlsx",
        product_count=17,
    )
    assert recorded.status == "running"
    assert recorded.range_label == "VIP"
    assert recorded.vehicle_class.value == "caravan"
    assert store.finish_run(connection, run.id).baseline_count == 17
