"""Tests for the review app: run list, change queue, per-field decisions.

Uses `fastapi.testclient.TestClient` against a throwaway SQLite file — no real
server, no browser. `diff_products` + `store.persist_diff` populate the DB the same
way a real run would (Phase 5 + the persistence layer above), so these tests exercise
the same path a reviewer actually hits.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src import paths, store
from src.adapters.base import ExtractedMotorhome, Provenance
from src.diff.classify import diff_products
from src.product_model import io
from src.product_model.enums import BedType, BodyType, Refrigeration
from src.product_model.model import Motorhome
from src.vehicle_class import VehicleClass
from src.webapp import create_app


def make_baseline(**overrides: object) -> Motorhome:
    fields: dict[str, object] = {
        "product_id": 4147,
        "manufacturer": "Adria Mobil",
        "manufacturer_range": "Matrix",
        "model": "Supreme 670 DC",
        "rrp_pounds": 93950,
    }
    fields.update(overrides)
    return Motorhome(**fields)


def make_extracted(*, rrp_pounds: int, **overrides: object) -> ExtractedMotorhome:
    fields: dict[str, object] = {
        "manufacturer": "Adria Mobil",
        "manufacturer_range": "Matrix",
        "model": "Supreme 670 DC",
        "rrp_pounds": rrp_pounds,
    }
    fields.update(overrides)
    return ExtractedMotorhome(
        motorhome=Motorhome(**fields),
        provenance={
            "rrp_pounds": Provenance(
                source_url="https://www.adria.co.uk/motorhomes/matrix", snippet="RRP £93,920"
            )
        },
    )


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "runs.db"


@pytest.fixture
def client(db_path: Path) -> TestClient:
    # Explicit registry_path/reviewers_path keep this isolated from the real
    # project's config/ directory — create_app defaults there otherwise.
    return TestClient(
        create_app(
            db_path,
            registry_path=db_path.parent / "manufacturers.csv",
            reviewers_path=db_path.parent / "reviewers.csv",
        )
    )


@pytest.fixture
def run_with_one_change(db_path: Path) -> tuple[int, int]:
    """A run with a single pending `rrp_pounds` proposed change. Returns (run_id, change_id)."""
    connection = store.connect(db_path)
    try:
        run = store.start_run(
            connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
        )
        baseline = make_baseline()
        extracted = make_extracted(rrp_pounds=93920)
        diffs = diff_products([extracted], [baseline])
        store.persist_diff(connection, run_id=run.id, manufacturer_id=3, diffs=diffs)
        [entry] = store.list_change_queue(connection, run.id)
        store.finish_run(connection, run.id)
        return run.id, entry.change.id
    finally:
        connection.close()


@pytest.fixture
def run_ready_for_upload(db_path: Path) -> int:
    """A succeeded, fully-reviewed run, plus the registry/export files its manufacturer
    needs — everything `generate_upload_route` looks up besides the change queue
    itself. Returns the run id."""
    data_root = db_path.parent
    (data_root / "manufacturers.csv").write_text(
        "manufacturer_id,fmlv_manufacturer,website_url\n3,Adria Mobil,https://example.invalid/\n",
        encoding="utf-8",
    )
    connection = store.connect(db_path)
    try:
        run = store.start_run(
            connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
        )
        baseline = make_baseline()
        extracted = make_extracted(rrp_pounds=93920)
        diffs = diff_products([extracted], [baseline])
        store.persist_diff(connection, run_id=run.id, manufacturer_id=3, diffs=diffs)
        for entry in store.list_change_queue(connection, run.id):
            store.record_decision(
                connection, proposed_change_id=entry.change.id, action="accept", decided_by="ben"
            )
        store.finish_run(connection, run.id)
    finally:
        connection.close()

    export_dir = paths.manufacturer_exports_dir(3, "Adria Mobil", root=data_root)
    io.write_csv([baseline], export_dir / "2026-08-01_Adria-Mobil_motorhome-campervans.csv")
    return run.id


def test_home_page_links_to_trigger_and_runs(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert 'href="/trigger"' in response.text
    assert 'href="/runs"' in response.text


def _manufacturer_options(html: str) -> list[str]:
    """The labels in the trigger form's manufacturer dropdown, in rendered order."""
    block = re.search(r'<select id="manufacturer_name".*?</select>', html, re.DOTALL)
    assert block is not None, "the manufacturer dropdown is missing from /trigger"
    labels = re.findall(r"<option[^>]*>(.*?)</option>", block.group(0), re.DOTALL)
    return [label.strip() for label in labels if label.strip()]


def test_the_manufacturer_dropdown_is_alphabetical(db_path: Path) -> None:
    """Sorted by the name on screen, which is not the name in the registry.

    The five here are written to the CSV in deliberately wrong order, and three of them
    display as something other than their `fmlv_manufacturer`: sorting on the stored name
    would put Weinsberg under K and Chausson under T, which is exactly where nobody would
    look for them. `MOTO-TREK` is here for the case: an ASCII sort puts every capitalised
    name ahead of every lower-cased one, so it would land before Morelo.
    """
    (db_path.parent / "manufacturers.csv").write_text(
        "manufacturer_id,fmlv_manufacturer,fmlv_display_name,website_url\n"
        "252,Knaus Tabbert AG,Weinsberg,https://example.invalid/a\n"
        "76,MOTO-TREK LIMITED,MOTO-TREK,https://example.invalid/b\n"
        "3,Adria Mobil,Adria,https://example.invalid/c\n"
        "53,Trigano VDL Chausson,Chausson,https://example.invalid/d\n"
        "46,Morelo,Morelo,https://example.invalid/e\n",
        encoding="utf-8",
    )
    client = TestClient(
        create_app(
            db_path,
            registry_path=db_path.parent / "manufacturers.csv",
            reviewers_path=db_path.parent / "reviewers.csv",
        )
    )

    options = _manufacturer_options(client.get("/trigger").text)

    assert options == ["Adria", "Chausson", "Morelo", "MOTO-TREK", "Weinsberg"]


def test_a_manufacturer_with_no_display_name_sorts_on_the_name_shown_instead(
    db_path: Path,
) -> None:
    """The template falls back to `fmlv_manufacturer` when the display name is blank, so
    the sort has to make the same fallback or the two disagree."""
    (db_path.parent / "manufacturers.csv").write_text(
        "manufacturer_id,fmlv_manufacturer,fmlv_display_name,website_url\n"
        "144,Wingamm,,https://example.invalid/a\n"
        "46,Morelo,,https://example.invalid/b\n"
        "28,Bailey,,https://example.invalid/c\n",
        encoding="utf-8",
    )
    client = TestClient(
        create_app(
            db_path,
            registry_path=db_path.parent / "manufacturers.csv",
            reviewers_path=db_path.parent / "reviewers.csv",
        )
    )

    assert _manufacturer_options(client.get("/trigger").text) == [
        "Bailey",
        "Morelo",
        "Wingamm",
    ]


def _runs_filter_options(html: str) -> list[str]:
    """The labels in the runs page's manufacturer filter, minus the "All" entry."""
    block = re.search(r'<select name="manufacturer_id".*?</select>', html, re.DOTALL)
    assert block is not None, "the manufacturer filter is missing from /runs"
    labels = [
        label.strip()
        for label in re.findall(r"<option[^>]*>(.*?)</option>", block.group(0), re.DOTALL)
    ]
    return [label for label in labels if label and label != "All manufacturers"]


def test_the_runs_filter_uses_the_same_names_as_the_trigger_page(db_path: Path) -> None:
    """Runs are recorded under `fmlv_manufacturer`, which is not what the app displays.

    Left alone, the same brand reads as "Chausson" on the trigger page and "Trigano VDL
    Chausson" here — and sorts under C there and T here, so a reviewer looking under C
    would not find it. Sorting alone would not have fixed that.
    """
    (db_path.parent / "manufacturers.csv").write_text(
        "manufacturer_id,fmlv_manufacturer,fmlv_display_name,website_url\n"
        "53,Trigano VDL Chausson,Chausson,https://example.invalid/a\n"
        "252,Knaus Tabbert AG,Weinsberg,https://example.invalid/b\n"
        "3,Adria Mobil,Adria,https://example.invalid/c\n",
        encoding="utf-8",
    )
    connection = store.connect(db_path)
    try:
        for manufacturer_id, recorded in (
            (252, "Knaus Tabbert AG"),
            (3, "Adria Mobil"),
            (53, "Trigano VDL Chausson"),
        ):
            store.start_run(
                connection,
                manufacturer_id=manufacturer_id,
                fmlv_manufacturer=recorded,
                trigger="manual",
            )
    finally:
        connection.close()
    client = TestClient(
        create_app(
            db_path,
            registry_path=db_path.parent / "manufacturers.csv",
            reviewers_path=db_path.parent / "reviewers.csv",
        )
    )

    assert _runs_filter_options(client.get("/runs").text) == [
        "Adria",
        "Chausson",
        "Weinsberg",
    ]


def test_a_manufacturer_with_runs_but_no_registry_row_keeps_its_recorded_name(
    db_path: Path,
) -> None:
    """The filter is drawn from run history so it survives the registry changing. A brand
    dropped from the registry must still be selectable, or its old runs become unreachable.
    """
    (db_path.parent / "manufacturers.csv").write_text(
        "manufacturer_id,fmlv_manufacturer,fmlv_display_name,website_url\n"
        "3,Adria Mobil,Adria,https://example.invalid/a\n",
        encoding="utf-8",
    )
    connection = store.connect(db_path)
    try:
        store.start_run(
            connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
        )
        store.start_run(
            connection, manufacturer_id=999, fmlv_manufacturer="Zenith Vans", trigger="manual"
        )
    finally:
        connection.close()
    client = TestClient(
        create_app(
            db_path,
            registry_path=db_path.parent / "manufacturers.csv",
            reviewers_path=db_path.parent / "reviewers.csv",
        )
    )

    assert _runs_filter_options(client.get("/runs").text) == ["Adria", "Zenith Vans"]


def test_the_runs_list_still_works_with_no_registry_file(db_path: Path) -> None:
    """Labelling the filter must not make the whole page depend on the registry.

    This page listed runs long before it consulted the registry at all, so a missing or
    unreadable CSV costs the display names and nothing else. Regression test: adding the
    lookup without this guard broke fourteen existing tests, all of which reach `/runs`
    without writing a registry file.
    """
    connection = store.connect(db_path)
    try:
        store.start_run(
            connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
        )
    finally:
        connection.close()
    client = TestClient(
        create_app(
            db_path,
            registry_path=db_path.parent / "nonexistent.csv",
            reviewers_path=db_path.parent / "reviewers.csv",
        )
    )

    response = client.get("/runs")

    assert response.status_code == 200
    assert _runs_filter_options(response.text) == ["Adria Mobil"]


def test_run_list_is_empty_with_no_runs(client: TestClient) -> None:
    response = client.get("/runs")
    assert response.status_code == 200
    assert "No runs recorded yet" in response.text


def test_run_list_shows_recorded_runs(client: TestClient, db_path: Path) -> None:
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    store.finish_run(connection, run.id)
    connection.close()

    response = client.get("/runs")

    assert response.status_code == 200
    assert "Adria Mobil" in response.text
    assert f"#{run.id}" in response.text


def test_run_list_shows_a_running_run_without_a_review_link(
    client: TestClient, db_path: Path
) -> None:
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    connection.close()

    response = client.get("/runs")

    assert response.status_code == 200
    assert f'href="/runs/{run.id}"' not in response.text
    assert '<span class="badge running">running</span>' in response.text


def test_run_list_shows_pending_count_and_a_generate_upload_button(
    client: TestClient, run_with_one_change: tuple[int, int]
) -> None:
    run_id, _change_id = run_with_one_change

    response = client.get("/runs")

    assert response.status_code == 200
    assert "1 pending" in response.text
    assert f'action="/runs/{run_id}/generate-upload"' in response.text


def test_run_list_shows_the_primary_reviewer_once_something_is_decided(
    client: TestClient, run_with_one_change: tuple[int, int]
) -> None:
    run_id, change_id = run_with_one_change
    client.post(
        f"/runs/{run_id}/changes/{change_id}/decide",
        data={"action": "accept", "reviewer_name": "ben"},
    )

    response = client.get("/runs")

    assert response.status_code == 200
    assert "ben" in response.text
    assert "none" in response.text  # nothing left pending


def test_run_list_filters_by_manufacturer(client: TestClient, db_path: Path) -> None:
    connection = store.connect(db_path)
    adria = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    store.finish_run(connection, adria.id)
    swift = store.start_run(
        connection, manufacturer_id=26, fmlv_manufacturer="Swift Group Ltd", trigger="manual"
    )
    store.finish_run(connection, swift.id)
    connection.close()

    response = client.get("/runs", params={"manufacturer_id": 3})

    assert response.status_code == 200
    assert f">#{adria.id}<" in response.text
    assert f">#{swift.id}<" not in response.text
    assert "No runs match this filter" not in response.text


def test_run_list_filters_by_status(client: TestClient, db_path: Path) -> None:
    connection = store.connect(db_path)
    running = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    finished = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    store.finish_run(connection, finished.id)
    connection.close()

    response = client.get("/runs", params={"status": "running"})

    assert response.status_code == 200
    assert f">#{running.id}<" in response.text
    assert f">#{finished.id}<" not in response.text


def test_run_list_filters_by_start_date(client: TestClient, db_path: Path) -> None:
    # Fixed, midday-UTC timestamps rather than store.start_run's "now" -- keeps this
    # deterministic regardless of the test machine's timezone or time of day, and
    # avoids the local-date boundary the filter itself has to handle near midnight.
    connection = store.connect(db_path)
    connection.executemany(
        """
        INSERT INTO run (manufacturer_id, fmlv_manufacturer, trigger, status, started_at)
        VALUES (?, ?, 'manual', 'succeeded', ?)
        """,
        [
            (3, "Adria Mobil", "2026-03-15T12:00:00+00:00"),
            (3, "Adria Mobil", "2026-03-16T12:00:00+00:00"),
        ],
    )
    connection.commit()
    run_15 = connection.execute(
        "SELECT id FROM run WHERE started_at = '2026-03-15T12:00:00+00:00'"
    ).fetchone()["id"]
    run_16 = connection.execute(
        "SELECT id FROM run WHERE started_at = '2026-03-16T12:00:00+00:00'"
    ).fetchone()["id"]
    connection.close()

    response = client.get("/runs", params={"start_date": "2026-03-15"})

    assert response.status_code == 200
    assert f">#{run_15}<" in response.text
    assert f">#{run_16}<" not in response.text


def test_run_list_ignores_an_unparseable_start_date(client: TestClient, db_path: Path) -> None:
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    store.finish_run(connection, run.id)
    connection.close()

    response = client.get("/runs", params={"start_date": "not-a-date"})

    assert response.status_code == 200
    assert f">#{run.id}<" in response.text


def test_run_list_with_no_matches_says_so_without_claiming_no_runs_at_all(
    client: TestClient, db_path: Path
) -> None:
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    store.finish_run(connection, run.id)
    connection.close()

    response = client.get("/runs", params={"status": "failed"})

    assert response.status_code == 200
    assert "No runs match this filter" in response.text
    assert "No runs recorded yet" not in response.text


def test_run_list_ignores_an_unknown_status_value(client: TestClient, db_path: Path) -> None:
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    store.finish_run(connection, run.id)
    connection.close()

    response = client.get("/runs", params={"status": "bogus"})

    assert response.status_code == 200
    assert f"#{run.id}" in response.text


def test_generate_upload_route_writes_a_csv_and_reports_it_as_json(
    client: TestClient, run_ready_for_upload: int
) -> None:
    run_id = run_ready_for_upload

    response = client.post(f"/runs/{run_id}/generate-upload")

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["count"] == 1
    assert data["filename"].startswith(f"run{run_id}_")
    assert data["download_url"] == f"/runs/{run_id}/uploads/{data['filename']}"
    assert data["issues_download_url"] == f"/runs/{run_id}/uploads/{data['issues_filename']}"
    assert "folder_url" not in data


def test_generate_upload_route_refuses_a_run_that_has_not_succeeded(
    client: TestClient, db_path: Path
) -> None:
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    connection.close()

    response = client.post(f"/runs/{run.id}/generate-upload")

    assert response.status_code == 409
    assert response.json()["ok"] is False


def test_downloading_a_generated_upload_serves_the_file(
    client: TestClient, run_ready_for_upload: int
) -> None:
    run_id = run_ready_for_upload
    filename = client.post(f"/runs/{run_id}/generate-upload").json()["filename"]

    response = client.get(f"/runs/{run_id}/uploads/{filename}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")


def test_downloading_a_generated_upload_issues_file_serves_readable_text(
    client: TestClient, run_ready_for_upload: int
) -> None:
    run_id = run_ready_for_upload
    issues_filename = client.post(f"/runs/{run_id}/generate-upload").json()["issues_filename"]

    response = client.get(f"/runs/{run_id}/uploads/{issues_filename}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "[WARNING]" in response.text or "[ERROR]" in response.text


def test_downloading_an_upload_for_the_wrong_run_id_404s(
    client: TestClient, run_ready_for_upload: int
) -> None:
    run_id = run_ready_for_upload
    filename = client.post(f"/runs/{run_id}/generate-upload").json()["filename"]

    response = client.get(f"/runs/{run_id + 1}/uploads/{filename}")

    assert response.status_code == 404


def test_a_running_run_shows_the_in_progress_page_not_the_queue(
    client: TestClient, db_path: Path
) -> None:
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    connection.close()

    response = client.get(f"/runs/{run.id}")

    assert response.status_code == 200
    assert "still fetching and diffing" in response.text
    assert "Pending (" not in response.text


def test_run_detail_404s_for_an_unknown_run(client: TestClient) -> None:
    response = client.get("/runs/999999")
    assert response.status_code == 404


def test_run_detail_shows_pending_change_with_source_and_link(
    client: TestClient, run_with_one_change: tuple[int, int]
) -> None:
    run_id, _change_id = run_with_one_change

    response = client.get(f"/runs/{run_id}")

    assert response.status_code == 200
    assert "rrp_pounds" in response.text
    assert "93950" in response.text
    assert "93920" in response.text
    assert "https://www.adria.co.uk/motorhomes/matrix" in response.text
    assert "£93,920" in response.text
    assert "Pending (1)" in response.text
    assert 'class="product-group new-product"' not in response.text


def test_accept_records_a_decision_and_moves_the_change_to_decided(
    client: TestClient, db_path: Path, run_with_one_change: tuple[int, int]
) -> None:
    run_id, change_id = run_with_one_change

    response = client.post(
        f"/runs/{run_id}/changes/{change_id}/decide",
        data={"action": "accept", "reviewer_name": "ben"},
    )

    assert response.status_code == 200
    assert "decision-accept" in response.text
    assert "ben" in response.text

    connection = store.connect(db_path)
    decision = store.latest_decision(connection, change_id)
    connection.close()
    assert decision is not None
    assert decision.action == "accept"
    assert decision.decided_by == "ben"

    detail = client.get(f"/runs/{run_id}")
    assert "Pending (0)" in detail.text
    assert "Decided (1)" in detail.text


def test_undo_reopens_an_accepted_change_for_review(
    client: TestClient, db_path: Path, run_with_one_change: tuple[int, int]
) -> None:
    run_id, change_id = run_with_one_change

    client.post(
        f"/runs/{run_id}/changes/{change_id}/decide",
        data={"action": "accept", "reviewer_name": "ben"},
    )

    response = client.post(
        f"/runs/{run_id}/changes/{change_id}/decide",
        data={"action": "undo", "reviewer_name": "ben"},
    )

    assert response.status_code == 200
    assert "decision-accept" not in response.text
    assert "decision-form" in response.text

    connection = store.connect(db_path)
    queue = store.list_change_queue(connection, run_id)
    latest = store.latest_decision(connection, change_id)
    connection.close()
    [entry] = queue
    assert entry.decision is None
    assert latest is not None
    assert latest.action == "undo"

    detail = client.get(f"/runs/{run_id}")
    assert "Pending (1)" in detail.text
    assert "Decided (" not in detail.text


def test_reject_records_a_decision(
    client: TestClient, db_path: Path, run_with_one_change: tuple[int, int]
) -> None:
    run_id, change_id = run_with_one_change

    response = client.post(
        f"/runs/{run_id}/changes/{change_id}/decide",
        data={"action": "reject", "reviewer_name": "ben"},
    )

    assert response.status_code == 200
    assert "decision-reject" in response.text
    connection = store.connect(db_path)
    decision = store.latest_decision(connection, change_id)
    connection.close()
    assert decision is not None
    assert decision.action == "reject"


def test_correct_with_a_value_records_the_corrected_value(
    client: TestClient, db_path: Path, run_with_one_change: tuple[int, int]
) -> None:
    run_id, change_id = run_with_one_change

    response = client.post(
        f"/runs/{run_id}/changes/{change_id}/decide",
        data={"action": "correct", "corrected_value": "93900", "reviewer_name": "ben"},
    )

    assert response.status_code == 200
    assert "93900" in response.text
    connection = store.connect(db_path)
    decision = store.latest_decision(connection, change_id)
    connection.close()
    assert decision is not None
    assert decision.action == "correct"
    assert decision.corrected_value == "93900"


def test_correct_without_a_value_is_rejected_with_an_inline_error(
    client: TestClient, db_path: Path, run_with_one_change: tuple[int, int]
) -> None:
    run_id, change_id = run_with_one_change

    response = client.post(
        f"/runs/{run_id}/changes/{change_id}/decide",
        data={"action": "correct", "corrected_value": "", "reviewer_name": "ben"},
    )

    assert response.status_code == 200
    assert "Enter a corrected value" in response.text
    connection = store.connect(db_path)
    decision = store.latest_decision(connection, change_id)
    connection.close()
    assert decision is None


def test_decide_404s_for_an_unknown_change(
    client: TestClient, run_with_one_change: tuple[int, int]
) -> None:
    run_id, _change_id = run_with_one_change

    response = client.post(
        f"/runs/{run_id}/changes/999999/decide",
        data={"action": "accept"},
    )

    assert response.status_code == 404


def test_decide_rejects_an_action_outside_the_allowed_set(
    client: TestClient, run_with_one_change: tuple[int, int]
) -> None:
    run_id, change_id = run_with_one_change

    response = client.post(
        f"/runs/{run_id}/changes/{change_id}/decide",
        data={"action": "maybe"},
    )

    assert response.status_code == 422


def test_new_product_field_has_no_old_value_shown_as_an_em_dash(
    client: TestClient, db_path: Path
) -> None:
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    extracted = make_extracted(
        rrp_pounds=45000, manufacturer_range="Sonic", model="Axess 600 SL"
    )
    diffs = diff_products([extracted], [])
    store.persist_diff(connection, run_id=run.id, manufacturer_id=3, diffs=diffs)
    store.finish_run(connection, run.id)
    connection.close()

    response = client.get(f"/runs/{run.id}")

    assert response.status_code == 200
    assert "new product" in response.text
    assert "45000" in response.text
    assert 'class="product-group new-product"' in response.text


def test_layout_field_change_is_marked_unusual(
    client: TestClient, db_path: Path
) -> None:
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    baseline = make_baseline()
    extracted = ExtractedMotorhome(
        motorhome=Motorhome(
            manufacturer="Adria Mobil",
            manufacturer_range="Matrix",
            model="Supreme 670 DC",
            rear_garage=True,
        ),
        provenance={
            "rear_garage": Provenance(source_url="https://example.com", snippet="Garage: Yes")
        },
    )
    diffs = diff_products([extracted], [baseline])
    store.persist_diff(connection, run_id=run.id, manufacturer_id=3, diffs=diffs)
    store.finish_run(connection, run.id)
    connection.close()

    response = client.get(f"/runs/{run.id}")

    assert "unusual" in response.text


def test_year_rollover_proposal_is_marked_possible_rollover(
    client: TestClient, db_path: Path
) -> None:
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    baseline = make_baseline(year=2026)
    extracted = make_extracted(rrp_pounds=93920)
    diffs = diff_products([extracted], [baseline], today=date(2026, 7, 15))
    store.persist_diff(connection, run_id=run.id, manufacturer_id=3, diffs=diffs)
    store.finish_run(connection, run.id)
    connection.close()

    response = client.get(f"/runs/{run.id}")

    assert "possible rollover" in response.text
    assert "2027" in response.text


def test_disappeared_product_shows_a_disappearance_notice_with_no_decision_controls(
    client: TestClient, db_path: Path
) -> None:
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    baseline = make_baseline()
    diffs = diff_products([], [baseline])
    store.persist_diff(connection, run_id=run.id, manufacturer_id=3, diffs=diffs)
    store.finish_run(connection, run.id)
    connection.close()

    response = client.get(f"/runs/{run.id}")

    assert response.status_code == 200
    assert 'class="badge disappeared"' in response.text
    assert "missing from site" in response.text
    assert 'class="disappearance-notice"' in response.text
    # No accept/reject/correct affordance — it's not a proposed CSV change.
    assert 'class="decision-form"' not in response.text
    assert 'class="accept-all-form"' not in response.text


def test_accept_all_accepts_every_pending_change_for_one_product(
    client: TestClient, db_path: Path
) -> None:
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    baseline = make_baseline(mro_kilograms=3184)
    extracted = ExtractedMotorhome(
        motorhome=Motorhome(
            manufacturer="Adria Mobil",
            manufacturer_range="Matrix",
            model="Supreme 670 DC",
            rrp_pounds=93920,
            mro_kilograms=3228,
        ),
        provenance={
            "rrp_pounds": Provenance(source_url="https://a", snippet="a"),
            "mro_kilograms": Provenance(source_url="https://a", snippet="b"),
        },
    )
    diffs = diff_products([extracted], [baseline])
    store.persist_diff(connection, run_id=run.id, manufacturer_id=3, diffs=diffs)
    queue = store.list_change_queue(connection, run.id)
    product_id = queue[0].product.id
    assert len(queue) == 2
    store.finish_run(connection, run.id)
    connection.close()

    response = client.post(
        f"/runs/{run.id}/products/{product_id}/accept-all",
        data={"reviewer_name": "ben"},
    )

    assert response.status_code == 200
    assert response.text.count("decision-accept") == 2
    # A single click both decides everything and hides the "Accept all" button —
    # previously the button stayed put, wrongly implying a second click was needed.
    assert "accept-all-form" not in response.text

    connection = store.connect(db_path)
    decisions = [store.latest_decision(connection, e.change.id) for e in queue]
    connection.close()
    assert all(d is not None and d.action == "accept" for d in decisions)


def test_accept_all_404s_for_an_unknown_product(
    client: TestClient, run_with_one_change: tuple[int, int]
) -> None:
    run_id, _change_id = run_with_one_change

    response = client.post(
        f"/runs/{run_id}/products/999999/accept-all",
        data={"reviewer_name": "ben"},
    )

    assert response.status_code == 404


def test_run_detail_groups_changes_by_product_not_a_single_flat_list(
    client: TestClient, db_path: Path
) -> None:
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    first_baseline = make_baseline(product_id=4147, model="Supreme 670 DC", mro_kilograms=3184)
    second_baseline = make_baseline(product_id=8195, model="670 SL 60Y", mro_kilograms=3134)
    first_extracted = ExtractedMotorhome(
        motorhome=Motorhome(
            manufacturer="Adria Mobil",
            manufacturer_range="Matrix",
            model="Supreme 670 DC",
            rrp_pounds=93920,
        ),
        provenance={"rrp_pounds": Provenance(source_url="https://a", snippet="a")},
    )
    second_extracted = ExtractedMotorhome(
        motorhome=Motorhome(
            manufacturer="Adria Mobil",
            manufacturer_range="Matrix",
            model="670 SL 60Y",
            rrp_pounds=94000,
        ),
        provenance={"rrp_pounds": Provenance(source_url="https://b", snippet="b")},
    )
    diffs = diff_products(
        [first_extracted, second_extracted], [first_baseline, second_baseline]
    )
    store.persist_diff(connection, run_id=run.id, manufacturer_id=3, diffs=diffs)
    store.finish_run(connection, run.id)
    connection.close()

    response = client.get(f"/runs/{run.id}")

    assert response.status_code == 200
    assert "Supreme 670 DC" in response.text
    assert "670 SL 60Y" in response.text
    assert "93920" in response.text
    assert "94000" in response.text


def test_rejection_is_remembered_across_runs_end_to_end(
    client: TestClient, db_path: Path
) -> None:
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    baseline = make_baseline()
    extracted = make_extracted(rrp_pounds=93920)
    diffs = diff_products([extracted], [baseline])
    store.persist_diff(connection, run_id=run.id, manufacturer_id=3, diffs=diffs)
    [entry] = store.list_change_queue(connection, run.id)
    store.finish_run(connection, run.id)
    connection.close()

    client.post(
        f"/runs/{run.id}/changes/{entry.change.id}/decide",
        data={"action": "reject", "reviewer_name": "ben"},
    )

    connection = store.connect(db_path)
    second_run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    second_diffs = diff_products([extracted], [baseline])
    store.persist_diff(connection, run_id=second_run.id, manufacturer_id=3, diffs=second_diffs)
    store.finish_run(connection, second_run.id)
    connection.close()

    response = client.get(f"/runs/{second_run.id}")
    assert "Pending (0)" in response.text
    assert "rrp_pounds" not in response.text


# --------------------------------------------------------------------------- #
# Reviewer gating — decisions are only accepted from a name in reviewers.csv
# --------------------------------------------------------------------------- #


@pytest.fixture
def reviewers_path(tmp_path: Path) -> Path:
    path = tmp_path / "reviewers.csv"
    path.write_text(
        "reviewer_name,reviewer_email\nBen Molyneaux,ben.m@thencc.org.uk\nFran,\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def gated_client(db_path: Path, reviewers_path: Path) -> TestClient:
    return TestClient(
        create_app(
            db_path,
            reviewers_path=reviewers_path,
            registry_path=db_path.parent / "manufacturers.csv",
        )
    )


def test_decide_is_rejected_when_reviewer_is_not_in_the_known_list(
    gated_client: TestClient, db_path: Path
) -> None:
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    baseline = make_baseline()
    extracted = make_extracted(rrp_pounds=93920)
    diffs = diff_products([extracted], [baseline])
    store.persist_diff(connection, run_id=run.id, manufacturer_id=3, diffs=diffs)
    [entry] = store.list_change_queue(connection, run.id)
    connection.close()

    response = gated_client.post(
        f"/runs/{run.id}/changes/{entry.change.id}/decide",
        data={"action": "accept", "reviewer_name": "Someone Unlisted"},
    )

    assert response.status_code == 200
    assert "Select your name from the reviewer list" in response.text
    connection = store.connect(db_path)
    decision = store.latest_decision(connection, entry.change.id)
    connection.close()
    assert decision is None


def test_decide_succeeds_when_reviewer_is_in_the_known_list(
    gated_client: TestClient, db_path: Path
) -> None:
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    baseline = make_baseline()
    extracted = make_extracted(rrp_pounds=93920)
    diffs = diff_products([extracted], [baseline])
    store.persist_diff(connection, run_id=run.id, manufacturer_id=3, diffs=diffs)
    [entry] = store.list_change_queue(connection, run.id)
    connection.close()

    response = gated_client.post(
        f"/runs/{run.id}/changes/{entry.change.id}/decide",
        data={"action": "accept", "reviewer_name": "Fran"},
    )

    assert response.status_code == 200
    assert "decision-accept" in response.text
    connection = store.connect(db_path)
    decision = store.latest_decision(connection, entry.change.id)
    connection.close()
    assert decision is not None
    assert decision.decided_by == "Fran"


def test_run_detail_offers_a_reviewer_dropdown_when_reviewers_are_configured(
    gated_client: TestClient, db_path: Path
) -> None:
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    store.finish_run(connection, run.id)
    connection.close()

    response = gated_client.get(f"/runs/{run.id}")

    assert response.status_code == 200
    assert "<select" in response.text
    assert "Ben Molyneaux" in response.text
    assert "Fran" in response.text


def test_run_list_shows_a_product_area_badge(client: TestClient, db_path: Path) -> None:
    """The question this whole pass answers: two Bailey runs must be tellable apart.

    A full sweep of either area carries no `range_label`, so before the badge existed
    these two rendered as visually identical rows.
    """
    connection = store.connect(db_path)
    motorhome = store.start_run(
        connection,
        manufacturer_id=28,
        fmlv_manufacturer="Bailey",
        trigger="manual",
        vehicle_class=VehicleClass.MOTORHOME,
    )
    store.finish_run(connection, motorhome.id)
    caravan = store.start_run(
        connection,
        manufacturer_id=28,
        fmlv_manufacturer="Bailey",
        trigger="manual",
        vehicle_class=VehicleClass.CARAVAN,
    )
    store.finish_run(connection, caravan.id)
    connection.close()

    response = client.get("/runs")

    assert response.status_code == 200
    assert "badge vehicle-class motorhome" in response.text
    assert "badge vehicle-class caravan" in response.text


def test_run_list_filters_by_product_area(client: TestClient, db_path: Path) -> None:
    connection = store.connect(db_path)
    motorhome = store.start_run(
        connection,
        manufacturer_id=28,
        fmlv_manufacturer="Bailey",
        trigger="manual",
        vehicle_class=VehicleClass.MOTORHOME,
    )
    store.finish_run(connection, motorhome.id)
    caravan = store.start_run(
        connection,
        manufacturer_id=28,
        fmlv_manufacturer="Bailey",
        trigger="manual",
        vehicle_class=VehicleClass.CARAVAN,
    )
    store.finish_run(connection, caravan.id)
    connection.close()

    response = client.get("/runs", params={"vehicle_class": "caravan"})

    assert response.status_code == 200
    assert f">#{caravan.id}<" in response.text
    assert f">#{motorhome.id}<" not in response.text
    assert "No runs match this filter" not in response.text


def test_run_list_ignores_an_unknown_product_area_rather_than_erroring(
    client: TestClient, db_path: Path
) -> None:
    """Same "cleared means all" treatment the status filter gets."""
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=28, fmlv_manufacturer="Bailey", trigger="manual"
    )
    store.finish_run(connection, run.id)
    connection.close()

    response = client.get("/runs", params={"vehicle_class": "hovercraft"})

    assert response.status_code == 200
    assert f">#{run.id}<" in response.text


def test_run_detail_heading_names_the_product_area(client: TestClient, db_path: Path) -> None:
    connection = store.connect(db_path)
    run = store.start_run(
        connection,
        manufacturer_id=28,
        fmlv_manufacturer="Bailey",
        trigger="manual",
        vehicle_class=VehicleClass.CARAVAN,
    )
    store.finish_run(connection, run.id)
    connection.close()

    response = client.get(f"/runs/{run.id}")

    assert response.status_code == 200
    assert "Touring caravans" in response.text


# --------------------------------------------------------------------------- #
# "Leave blank" — the third answer to a field the adapter could not find
# --------------------------------------------------------------------------- #
#
# Requested 3 September 2026, while reviewing Swift's first caravan run. Their 2027
# site publishes no internal length, height or awning size at all, so each arrived as
# a flagged no-op on 24 products — and the only available answers were "keep the
# existing figure" or "type a replacement". Neither says "the manufacturer has
# withdrawn this, so stop showing a stale number".


@pytest.fixture
def run_with_a_missing_field(db_path: Path) -> tuple[int, int]:
    """A run whose one proposal is an in-scope field the adapter did not find.

    `mh_height_mm` is on the baseline and absent from the scrape, which is exactly
    what `diff.compare` turns into a `MissingField` rather than a change.
    """
    connection = store.connect(db_path)
    try:
        run = store.start_run(
            connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
        )
        baseline = make_baseline(mh_height_mm=2890)
        extracted = make_extracted(rrp_pounds=93950)  # same price, so the only row is the gap
        diffs = diff_products([extracted], [baseline])
        store.persist_diff(connection, run_id=run.id, manufacturer_id=3, diffs=diffs)
        [entry] = store.list_change_queue(connection, run.id)
        assert entry.change.field == "mh_height_mm"
        store.finish_run(connection, run.id)
        return run.id, entry.change.id
    finally:
        connection.close()


def test_a_missing_field_row_offers_leaving_it_blank(
    client: TestClient, run_with_a_missing_field: tuple[int, int]
) -> None:
    run_id, _change_id = run_with_a_missing_field
    body = client.get(f"/runs/{run_id}").text

    assert "Keep existing value" in body
    assert "Leave blank" in body
    assert 'value="blank"' in body


def test_leaving_a_field_blank_is_recorded_and_shown_as_cleared(
    client: TestClient, db_path: Path, run_with_a_missing_field: tuple[int, int]
) -> None:
    run_id, change_id = run_with_a_missing_field

    response = client.post(
        f"/runs/{run_id}/changes/{change_id}/decide",
        data={"action": "blank", "reviewer_name": "ben"},
    )

    assert response.status_code == 200
    assert "cleared the value" in response.text
    connection = store.connect(db_path)
    try:
        decision = store.latest_decision(connection, change_id)
    finally:
        connection.close()
    assert decision is not None
    assert decision.action == "blank"
    # Not a "correct" carrying an empty string: clearing the field *is* the value, so
    # `corrected_value` keeps meaning "what the reviewer typed".
    assert decision.corrected_value is None
    assert decision.decided_by == "ben"


def test_leaving_a_field_blank_needs_no_replacement_value(
    client: TestClient, run_with_a_missing_field: tuple[int, int]
) -> None:
    """The guard that blocks an empty "correct" must not also block a deliberate blank."""
    run_id, change_id = run_with_a_missing_field

    response = client.post(
        f"/runs/{run_id}/changes/{change_id}/decide",
        data={"action": "blank", "corrected_value": "", "reviewer_name": "ben"},
    )

    assert "Enter a corrected value" not in response.text
    assert "cleared the value" in response.text


def test_a_blanked_field_can_be_undone(
    client: TestClient, run_with_a_missing_field: tuple[int, int]
) -> None:
    run_id, change_id = run_with_a_missing_field
    client.post(
        f"/runs/{run_id}/changes/{change_id}/decide",
        data={"action": "blank", "reviewer_name": "ben"},
    )

    response = client.post(
        f"/runs/{run_id}/changes/{change_id}/decide",
        data={"action": "undo", "reviewer_name": "ben"},
    )

    assert "cleared the value" not in response.text
    assert "Leave blank" in response.text  # reopened for review


def test_a_field_that_cannot_hold_a_blank_is_refused_by_the_endpoint(
    client: TestClient, db_path: Path
) -> None:
    """The template offers no button for these, but the endpoint is a plain POST.

    Without this guard a hand-rolled request would reach `apply_field` and write `No`
    into a boolean — asserting *single axle* rather than *unknown*, which is a worse
    answer than the figure it replaced. The proposal is recorded directly rather than
    diffed into being, so the guard is exercised rather than depending on which rows a
    particular baseline happens to produce.
    """
    connection = store.connect(db_path)
    try:
        run = store.start_run(
            connection,
            manufacturer_id=26,
            fmlv_manufacturer="Swift Group Ltd",
            trigger="manual",
            vehicle_class=VehicleClass.CARAVAN,
        )
        product = store.upsert_seen(
            connection,
            manufacturer_id=26,
            fmlv_product_id=None,
            manufacturer_range="Challenger Grande",
            model="580",
            run_id=run.id,
            vehicle_class=VehicleClass.CARAVAN,
        )
        change = store.record_proposed_change(
            connection,
            run_id=run.id,
            product_id=product.id,
            field="twin_axle",
            old_value="True",
            new_value="False",
            source_url=None,
            source_snippet=store.MISSING_FIELD_SNIPPET,
        )
        store.finish_run(connection, run.id)
    finally:
        connection.close()

    response = client.post(
        f"/runs/{run.id}/changes/{change.id}/decide",
        data={"action": "blank", "reviewer_name": "ben"},
    )

    assert "cannot be left blank" in response.text
    connection = store.connect(db_path)
    try:
        assert store.latest_decision(connection, change.id) is None
    finally:
        connection.close()


def test_a_row_for_an_unblankable_field_offers_no_blank_button(
    client: TestClient, db_path: Path
) -> None:
    """The guard above is the backstop; this is the reviewer never being offered it."""
    connection = store.connect(db_path)
    try:
        run = store.start_run(
            connection,
            manufacturer_id=26,
            fmlv_manufacturer="Swift Group Ltd",
            trigger="manual",
            vehicle_class=VehicleClass.CARAVAN,
        )
        product = store.upsert_seen(
            connection,
            manufacturer_id=26,
            fmlv_product_id=None,
            manufacturer_range="Challenger Grande",
            model="580",
            run_id=run.id,
            vehicle_class=VehicleClass.CARAVAN,
        )
        store.record_proposed_change(
            connection,
            run_id=run.id,
            product_id=product.id,
            field="twin_axle",
            old_value="True",
            new_value="True",
            source_url=None,
            source_snippet=store.MISSING_FIELD_SNIPPET,
        )
        store.finish_run(connection, run.id)
    finally:
        connection.close()

    body = client.get(f"/runs/{run.id}").text

    assert "Keep existing value" in body
    assert "Leave blank" not in body


def test_blanking_a_required_column_is_flagged_on_the_button(
    client: TestClient, run_with_a_missing_field: tuple[int, int]
) -> None:
    """`mh_height_mm` is a required column, so the button warns before it is clicked.

    Blanking it is still allowed — the reviewer's judgement is the point — but the
    generated CSV will report the row as missing a required field, and that should not be
    a surprise discovered at upload.
    """
    run_id, _change_id = run_with_a_missing_field
    body = client.get(f"/runs/{run_id}").text

    assert "Leave blank" in body
    assert "blank-required-flag" in body
    assert "will report this row as missing it" in body


def test_a_floorplan_reference_is_lifted_into_the_product_header(
    client: TestClient, db_path: Path
) -> None:
    """Several fields point at the same drawing, so it belongs above the rows, not in them.

    The requester, 6 September 2026: *"a single floor plan link in the product header
    above all the rows would be very helpful."*
    """
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    extracted = make_extracted(rrp_pounds=45000)
    extracted.provenance["sleeping_area"] = Provenance(
        source_url="https://example.test/floorplan.jpg",
        snippet="read which end the beds are at off the floorplan",
        reviewer_reference=True,
    )
    diffs = diff_products([extracted], [])
    store.persist_diff(connection, run_id=run.id, manufacturer_id=3, diffs=diffs)
    store.finish_run(connection, run.id)
    connection.close()

    response = client.get(f"/runs/{run.id}")

    assert response.status_code == 200
    assert 'class="product-floorplan"' in response.text
    assert 'href="https://example.test/floorplan.jpg"' in response.text
    assert ">Floorplan</a>" in response.text


def test_a_product_with_no_floorplan_gets_no_header_link(
    client: TestClient, db_path: Path
) -> None:
    """Rimor's Van 238 and Horus 12 have no factory page, so there is no drawing."""
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    diffs = diff_products([make_extracted(rrp_pounds=45000)], [])
    store.persist_diff(connection, run_id=run.id, manufacturer_id=3, diffs=diffs)
    store.finish_run(connection, run.id)
    connection.close()

    response = client.get(f"/runs/{run.id}")

    assert response.status_code == 200
    assert 'class="product-floorplan"' not in response.text


def _run_with_a_bed_types_change(db_path: Path) -> tuple[int, int]:
    """A pending `bed_types` proposal on a matched product, for the multi-select tests.

    Recorded directly rather than through `persist_diff`, because since 9 September 2026
    the pipeline no longer *proposes* `bed_types` — it reports it as a finding, and
    `product_model.findings` says why. The multi-select review path still has to work:
    the deployed run store holds hundreds of `bed_types` and `bathroom_layout` proposals
    from earlier runs, and a reviewer opening one of those runs must still be able to
    tick the boxes and decide it. That is exactly what this fixture now stands for.
    """
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    product = store.upsert_seen(
        connection,
        manufacturer_id=3,
        fmlv_product_id=1,
        manufacturer_range="Matrix",
        model="Supreme 670 DC",
        run_id=run.id,
    )
    change = store.record_proposed_change(
        connection,
        run_id=run.id,
        product_id=product.id,
        field="bed_types",
        old_value="island_bed",
        new_value="drop_down_bed",
        source_url="https://example.test/p",
        source_snippet="Front electric drop-down double bed",
    )
    store.finish_run(connection, run.id)
    connection.close()
    return run.id, change.id


def test_bed_types_is_offered_as_tick_boxes_not_one_choice(
    client: TestClient, db_path: Path
) -> None:
    """The requester, 7 September 2026: *"we need the option to be able to select all the
    types that apply rather than correct the value with one other value."*
    """
    run_id, _change_id = _run_with_a_bed_types_change(db_path)

    response = client.get(f"/runs/{run_id}")

    assert response.status_code == 200
    assert 'class="choice-checks"' in response.text
    assert 'name="corrected_values"' in response.text
    assert 'value="island_bed"' in response.text
    assert 'value="drop_down_bed"' in response.text
    # And the labels, not the column names, since a reviewer reads these.
    assert "Drop-down bed" in response.text


def test_correcting_bed_types_records_every_type_ticked(
    client: TestClient, db_path: Path
) -> None:
    """A four-berth coachbuilt has a fixed bed at the back and a drop-down over the cab."""
    run_id, change_id = _run_with_a_bed_types_change(db_path)

    response = client.post(
        f"/runs/{run_id}/changes/{change_id}/decide",
        data={
            "action": "correct",
            "reviewer_name": "ben",
            "corrected_values": ["island_bed", "drop_down_bed"],
        },
    )

    assert response.status_code == 200
    connection = store.connect(db_path)
    decision = store.latest_decision(connection, change_id)
    connection.close()
    assert decision is not None
    assert decision.action == "correct"
    assert decision.corrected_value == "island_bed, drop_down_bed"


def test_a_corrected_bed_type_list_survives_into_the_upload(
    client: TestClient, db_path: Path
) -> None:
    """The whole point: `apply_field` has always split this, so the list has to reach it."""
    from src.output.build import apply_field

    run_id, change_id = _run_with_a_bed_types_change(db_path)
    client.post(
        f"/runs/{run_id}/changes/{change_id}/decide",
        data={
            "action": "correct",
            "reviewer_name": "ben",
            "corrected_values": ["fixed_bed", "drop_down_bed"],
        },
    )
    connection = store.connect(db_path)
    decision = store.latest_decision(connection, change_id)
    connection.close()

    product = apply_field(Motorhome(manufacturer="Adria Mobil"), "bed_types", decision.corrected_value)
    assert product.bed_types == [BedType.FIXED, BedType.DROP_DOWN]


def test_an_unrecognised_bed_type_is_refused_at_review_not_at_upload(
    client: TestClient, db_path: Path
) -> None:
    """One bad part would make `apply_field` raise for the whole row, hours later."""
    run_id, change_id = _run_with_a_bed_types_change(db_path)

    response = client.post(
        f"/runs/{run_id}/changes/{change_id}/decide",
        data={
            "action": "correct",
            "reviewer_name": "ben",
            "corrected_values": ["island_bed", "hammock"],
        },
    )

    assert response.status_code == 200
    assert "not one of the values" in response.text
    connection = store.connect(db_path)
    assert store.latest_decision(connection, change_id) is None
    connection.close()


def _run_with_an_unset_field(db_path: Path) -> tuple[int, int]:
    """A new product whose body type the adapter could not derive: no value either side.

    `body_type` rather than a positional field, because since 9 September 2026 the
    positional fields are findings and no longer ask the reviewer anything — see
    `product_model.findings`. The body type is the case left: eight mutually exclusive
    columns, nothing in the baseline to keep, and a blank leaves the product out of every
    FMLV filter.
    """
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    extracted = make_extracted(rrp_pounds=45000, body_type=None)
    diffs = diff_products([extracted], [])
    store.persist_diff(connection, run_id=run.id, manufacturer_id=3, diffs=diffs)
    store.finish_run(connection, run.id)
    product_id = next(
        entry.product.id
        for entry in store.list_change_queue(connection, run_id=run.id)
        if entry.change.field == "body_type"
    )
    connection.close()
    return run.id, product_id


def test_a_field_with_nothing_to_accept_is_flagged_in_red(
    client: TestClient, db_path: Path
) -> None:
    """The requester, 7 September 2026: *"we need a flag saying selection needed in red"*."""
    run_id, _product_id = _run_with_an_unset_field(db_path)

    response = client.get(f"/runs/{run_id}")

    assert response.status_code == 200
    assert "selection needed" in response.text
    assert "selection-needed-row" in response.text


def test_accept_all_leaves_a_field_that_needs_a_choice_pending(
    client: TestClient, db_path: Path
) -> None:
    """Accepting it would mark the field reviewed and leave it blank — how run 86 shipped
    with its layout columns unset. So it stays pending and the reviewer is told."""
    run_id, product_id = _run_with_an_unset_field(db_path)

    response = client.post(
        f"/runs/{run_id}/products/{product_id}/accept-all",
        data={"reviewer_name": "ben"},
    )

    assert response.status_code == 200
    assert "still need a choice" in response.text
    assert "body_type" in response.text

    connection = store.connect(db_path)
    pending = [
        entry
        for entry in store.list_change_queue(connection, run_id=run_id)
        if entry.decision is None
    ]
    connection.close()
    # The unanswerable field is still pending, along with every other column this new
    # product has nothing for — see `store.changes.fields_needing_a_choice`. Everything
    # with a real value was accepted.
    assert "body_type" in [entry.change.field for entry in pending]
    assert "rrp_pounds" not in [entry.change.field for entry in pending]


def test_accept_all_still_accepts_everything_when_nothing_needs_a_choice(
    client: TestClient, db_path: Path, run_with_one_change: tuple[int, int]
) -> None:
    """The ordinary case has to be untouched."""
    run_id, change_id = run_with_one_change
    connection = store.connect(db_path)
    product_id = next(
        entry.product.id for entry in store.list_change_queue(connection, run_id=run_id)
    )
    connection.close()

    response = client.post(
        f"/runs/{run_id}/products/{product_id}/accept-all",
        data={"reviewer_name": "ben"},
    )

    assert response.status_code == 200
    assert "still need a choice" not in response.text
    connection = store.connect(db_path)
    assert store.latest_decision(connection, change_id) is not None
    connection.close()


def test_a_yes_no_field_is_offered_as_a_choice_not_a_text_box() -> None:
    """A reviewer answering from the floorplan needs options, not free text.

    The requester, 9 September 2026: *"if bed types or indeed separated shower and toilet
    are not available in the copy, they should be available for a reviewer like myself to
    either leave the default as blank or input a value."* Before this the row fell back to
    the free-text box, where "yes" stored verbatim reads back as `False` in `apply_field`.
    """
    from src.webapp import choices
    from src.webapp.choices import VehicleClass

    for vehicle_class in (VehicleClass.MOTORHOME, VehicleClass.CARAVAN):
        options = choices.field_choices("shower_toilet_separated", vehicle_class)
        assert options == [("", [("True", "Yes"), ("False", "No")])], vehicle_class

    # The stored values are Python's own `str(bool)`, because that is what `apply_field`
    # parses back with `raw_value == "True"`.
    assert choices.is_valid_choice("shower_toilet_separated", "True") is True
    assert choices.is_valid_choice("shower_toilet_separated", "False") is True
    assert choices.is_valid_choice("shower_toilet_separated", "yes") is False


def test_a_reviewers_yes_reaches_the_upload_as_yes() -> None:
    """The whole point of the selector: what is chosen has to survive to the CSV."""
    from src.output.build import apply_field
    from src.product_model.caravan import Caravan
    from src.product_model.caravan_io import caravan_to_row

    caravan = Caravan(manufacturer="Eriba", model="Touring 310")
    assert caravan.shower_toilet_separated is None

    decided = apply_field(caravan, "shower_toilet_separated", "True")
    assert decided.shower_toilet_separated is True
    assert caravan_to_row(decided)["separate_shower_toilet"] == "Yes"


def test_a_reviewers_bed_types_reach_the_upload() -> None:
    """`bed_types` is multi-select, so several tick boxes come back as one joined value."""
    from src.output.build import apply_field
    from src.product_model.caravan import Caravan
    from src.product_model.caravan_io import caravan_to_row

    caravan = Caravan(manufacturer="Eriba", model="Novaline 515")
    assert caravan.bed_types == []

    decided = apply_field(caravan, "bed_types", "fixed_bunks, make_up_beds")
    row = caravan_to_row(decided)
    assert (row["fixed_bunks"], row["make_up_beds"]) == ("Yes", "Yes")
    assert row["island_bed"] == "No"


def test_needs_selection_only_fires_when_both_sides_are_empty() -> None:
    """On a matched product, accepting is a real answer: keep what FMLV holds."""
    from src.webapp import choices

    assert choices.needs_selection(None, None) is True
    assert choices.needs_selection("", "  ") is True
    assert choices.needs_selection("side_shower_toilet", None) is False
    assert choices.needs_selection(None, "island_bed") is False


def test_accept_all_does_accept_a_new_products_weights(
    client: TestClient, db_path: Path
) -> None:
    """Regression guard for run 87: MRO and payload must not be caught by the new skip.

    The `needs_selection` guard only skips rows with nothing on either side. A new
    product's MRO is a real proposed value, so Accept all has to take it — otherwise the
    upload reports `required field 'mro_kilograms' is missing`.
    """
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=75, fmlv_manufacturer="Rimor", trigger="manual"
    )
    extracted = make_extracted(
        rrp_pounds=61995,
        manufacturer_range="Kilig",
        model="55 Plus",
        mro_kilograms=3051,
        mtplm_kilograms=3500,
        mh_payload_kilograms=449,
    )
    for name, snippet in (
        ("mro_kilograms", "MRO: 3051 kg"),
        ("mtplm_kilograms", "Maximum overall weight: 3500"),
        ("mh_payload_kilograms", "3500 kg MTPLM - 3051 kg MRO"),
    ):
        extracted.provenance[name] = Provenance("https://www.rimor.it/x", snippet)
    store.persist_diff(
        connection, run_id=run.id, manufacturer_id=75, diffs=diff_products([extracted], [])
    )
    store.finish_run(connection, run.id)
    product_id = next(
        e.product.id for e in store.list_change_queue(connection, run_id=run.id)
    )
    connection.close()

    client.post(
        f"/runs/{run.id}/products/{product_id}/accept-all", data={"reviewer_name": "ben"}
    )

    connection = store.connect(db_path)
    decided = {
        e.change.field: e.decision.action
        for e in store.list_change_queue(connection, run_id=run.id)
        if e.decision is not None
    }
    pending = [
        e.change.field
        for e in store.list_change_queue(connection, run_id=run.id)
        if e.decision is None
    ]
    connection.close()

    assert decided.get("mro_kilograms") == "accept"
    assert decided.get("mh_payload_kilograms") == "accept"
    assert decided.get("mtplm_kilograms") == "accept"
    # Held back: the columns this new product has no value for at all. Nothing with a
    # real figure is.
    assert "body_type" in pending
    assert not {"mro_kilograms", "mtplm_kilograms", "mh_payload_kilograms"} & set(pending)


def _run_with_a_new_products_missing_weight(db_path: Path) -> tuple[int, int, int]:
    """A new product with no MRO from anywhere: `(run, product, mro change)`."""
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=75, fmlv_manufacturer="Rimor", trigger="manual"
    )
    extracted = make_extracted(
        rrp_pounds=69995, manufacturer_range="Super Brig", model="Suite"
    )
    store.persist_diff(
        connection, run_id=run.id, manufacturer_id=75, diffs=diff_products([extracted], [])
    )
    store.finish_run(connection, run.id)
    queue = store.list_change_queue(connection, run_id=run.id)
    mro = next(e for e in queue if e.change.field == "mro_kilograms")
    connection.close()
    return run.id, mro.product.id, mro.change.id


def test_a_new_products_missing_weight_offers_blank_or_a_value(
    client: TestClient, db_path: Path
) -> None:
    """There is no existing figure, so "keep it" is not one of the answers."""
    run_id, _product_id, _change_id = _run_with_a_new_products_missing_weight(db_path)

    response = client.get(f"/runs/{run_id}")

    assert response.status_code == 200
    assert "no value from the site, and none on record" in response.text
    assert 'value="blank"' in response.text
    assert "Leave blank" in response.text
    # Not offered: there is nothing on record to keep.
    assert "Keep existing value" not in response.text


def test_a_new_products_weight_can_be_left_blank(
    client: TestClient, db_path: Path
) -> None:
    """Francis, 7 September 2026: *"I can choose to leave it blank, I assume."*"""
    run_id, _product_id, change_id = _run_with_a_new_products_missing_weight(db_path)

    response = client.post(
        f"/runs/{run_id}/changes/{change_id}/decide",
        data={"action": "blank", "reviewer_name": "ben"},
    )

    assert response.status_code == 200
    connection = store.connect(db_path)
    decision = store.latest_decision(connection, change_id)
    connection.close()
    assert decision is not None
    assert decision.action == "blank"


def test_a_new_products_weight_can_be_typed_in_instead(
    client: TestClient, db_path: Path
) -> None:
    run_id, _product_id, change_id = _run_with_a_new_products_missing_weight(db_path)

    client.post(
        f"/runs/{run_id}/changes/{change_id}/decide",
        data={"action": "correct", "corrected_value": "3005", "reviewer_name": "ben"},
    )

    connection = store.connect(db_path)
    decision = store.latest_decision(connection, change_id)
    connection.close()
    assert decision is not None
    assert decision.action == "correct"
    assert decision.corrected_value == "3005"


def test_editing_the_bed_type_boxes_and_pressing_accept_saves_the_edit(
    client: TestClient, db_path: Path
) -> None:
    """Francis, 7 September 2026, on Kilig 66 Plus: *"if I go to change it and add one or
    remove one and click accept, it doesn't change. Surely I should be able to edit it."*

    The boxes sit beside Accept, pre-ticked from the proposal, so editing them and
    pressing Accept looked like it saved and did not — Accept recorded the proposal.
    """
    run_id, change_id = _run_with_a_bed_types_change(db_path)

    response = client.post(
        f"/runs/{run_id}/changes/{change_id}/decide",
        data={
            "action": "accept",
            "reviewer_name": "ben",
            # Proposed was drop_down_bed alone; the reviewer adds the island bed.
            "corrected_values": ["island_bed", "drop_down_bed"],
        },
    )

    assert response.status_code == 200
    connection = store.connect(db_path)
    decision = store.latest_decision(connection, change_id)
    connection.close()
    assert decision is not None
    assert decision.action == "correct"
    assert decision.corrected_value == "island_bed, drop_down_bed"


def test_pressing_accept_with_the_boxes_untouched_is_still_a_plain_accept(
    client: TestClient, db_path: Path
) -> None:
    """Nothing was edited, so nothing is reinterpreted."""
    run_id, change_id = _run_with_a_bed_types_change(db_path)

    client.post(
        f"/runs/{run_id}/changes/{change_id}/decide",
        data={
            "action": "accept",
            "reviewer_name": "ben",
            "corrected_values": ["drop_down_bed"],  # exactly what was proposed
        },
    )

    connection = store.connect(db_path)
    decision = store.latest_decision(connection, change_id)
    connection.close()
    assert decision.action == "accept"
    assert decision.corrected_value is None


def test_reordered_bed_types_are_not_treated_as_an_edit(
    client: TestClient, db_path: Path
) -> None:
    """The boxes submit in enum order; the adapter proposes in the order the copy named
    them. Same set, so pressing Accept must stay an accept rather than a correction.

    A stored proposal rather than a fresh diff — `bed_types` is a finding now, and this
    guards the path a run from before that still takes. See `_run_with_a_bed_types_change`.
    """
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=75, fmlv_manufacturer="Rimor", trigger="manual"
    )
    product = store.upsert_seen(
        connection,
        manufacturer_id=75,
        fmlv_product_id=7927,
        manufacturer_range="Sarus",
        model="66 Plus",
        run_id=run.id,
    )
    change_id = store.record_proposed_change(
        connection,
        run_id=run.id,
        product_id=product.id,
        field="bed_types",
        old_value="make_up_beds",
        new_value="island_bed, drop_down_bed",
        source_url="https://mnc.test/x",
        source_snippet="Rear double island bed / Electric drop-down double bed",
    ).id
    connection.close()

    client.post(
        f"/runs/{run.id}/changes/{change_id}/decide",
        data={
            "action": "accept",
            "reviewer_name": "ben",
            # Enum order puts island before drop-down; the proposal happens to agree here,
            # so submit them the other way round to prove the comparison is set-based.
            "corrected_values": ["drop_down_bed", "island_bed"],
        },
    )

    connection = store.connect(db_path)
    decision = store.latest_decision(connection, change_id)
    connection.close()
    assert decision.action == "accept"


def test_changing_a_single_select_and_pressing_accept_saves_the_change(
    client: TestClient, db_path: Path
) -> None:
    """The same trap on a dropdown, so the same answer."""
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=75, fmlv_manufacturer="Rimor", trigger="manual"
    )
    baseline = Motorhome(
        manufacturer="Rimor", manufacturer_range="Horus", model="38", product_id=5992,
        body_type=BodyType.CAMPERVAN,
    )
    extracted = make_extracted(
        rrp_pounds=59995, manufacturer_range="Horus", model="38",
        body_type=BodyType.CAMPERVAN_HIGH_TOP,
    )
    extracted.provenance["body_type"] = Provenance("https://rimor.it/x", "listed under /vans")
    store.persist_diff(
        connection, run_id=run.id, manufacturer_id=75, diffs=diff_products([extracted], [baseline])
    )
    change_id = next(
        e.change.id
        for e in store.list_change_queue(connection, run_id=run.id)
        if e.change.field == "body_type"
    )
    connection.close()

    client.post(
        f"/runs/{run.id}/changes/{change_id}/decide",
        data={
            "action": "accept",
            "reviewer_name": "ben",
            "corrected_value": "type_campervan_high_top_elevating_roof",
        },
    )

    connection = store.connect(db_path)
    decision = store.latest_decision(connection, change_id)
    connection.close()
    assert decision.action == "correct"
    assert decision.corrected_value == "type_campervan_high_top_elevating_roof"


def test_a_field_checked_and_unchanged_is_shown_so_a_missing_row_is_not_ambiguous(
    client: TestClient, db_path: Path
) -> None:
    """Kilig 77 Plus had no `bed_types` row, and no way to tell why.

    The requester, 8 September 2026: *"I noticed that there's no proposal on bed types. Is
    this because there is no change in the bed types?"* A field with no row may have
    matched, or never been looked at, and those mean opposite things.

    Shown here on the MTPLM rather than on `bed_types` itself, which is a finding now and
    so is neither proposed nor confirmed — see `product_model.findings`. The ambiguity the
    line answers is the same for every field that *is* still compared.
    """
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=75, fmlv_manufacturer="Rimor", trigger="manual"
    )
    baseline = Motorhome(
        manufacturer="Rimor",
        manufacturer_range="Kilig",
        model="77 Plus",
        product_id=7940,
        rrp_pounds=59995,
        mtplm_kilograms=3500,
    )
    # The same MTPLM, a changed price: the mass is checked and matches, the price does not.
    extracted = make_extracted(
        rrp_pounds=61995,
        manufacturer_range="Kilig",
        model="77 Plus",
        mtplm_kilograms=3500,
    )
    extracted.provenance["mtplm_kilograms"] = Provenance(
        "https://mnc.test/x", "Maximum overall weight: 3500 kg"
    )
    store.persist_diff(
        connection, run_id=run.id, manufacturer_id=75, diffs=diff_products([extracted], [baseline])
    )
    store.finish_run(connection, run.id)
    connection.close()

    response = client.get(f"/runs/{run.id}")

    assert response.status_code == 200
    assert "checked and unchanged" in response.text
    assert "mtplm_kilograms" in response.text
    # And the price, which did change, is still a row to decide.
    assert "61995" in response.text


def test_a_product_with_nothing_verified_shows_no_such_line(
    client: TestClient, db_path: Path
) -> None:
    """A new product has no baseline, so nothing can be confirmed unchanged."""
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    store.persist_diff(
        connection,
        run_id=run.id,
        manufacturer_id=3,
        diffs=diff_products([make_extracted(rrp_pounds=45000)], []),
    )
    store.finish_run(connection, run.id)
    connection.close()

    response = client.get(f"/runs/{run.id}")

    assert response.status_code == 200
    assert "checked and unchanged" not in response.text


# --------------------------------------------------------------------------- #
# Findings: stated for a person to act on, never decided
# --------------------------------------------------------------------------- #


def _run_with_findings(db_path: Path) -> tuple[int, int, int]:
    """A new product whose copy settles the fridge: `(run, product, finding change id)`."""
    connection = store.connect(db_path)
    run = store.start_run(
        connection, manufacturer_id=75, fmlv_manufacturer="Rimor", trigger="manual"
    )
    extracted = make_extracted(
        rrp_pounds=61995,
        manufacturer_range="Kilig",
        model="66 Plus",
        refrigeration=Refrigeration.FRIDGE_FREEZER,
    )
    extracted.provenance["refrigeration"] = Provenance(
        "https://mnc.test/kilig-66", "141L fridge with freezer compartment"
    )
    extracted.provenance["bathroom_layout"] = Provenance(
        "https://www.rimor.it/plan.png", "read the washroom off the floorplan", True
    )
    store.persist_diff(
        connection, run_id=run.id, manufacturer_id=75, diffs=diff_products([extracted], [])
    )
    store.finish_run(connection, run.id)
    findings = store.findings_by_product(connection, run.id)
    product_id, rows = next(iter(findings.items()))
    finding_id = next(row.id for row in rows if row.field == "refrigeration")
    connection.close()
    return run.id, product_id, finding_id


def test_a_finding_is_shown_with_its_source_and_no_buttons(
    client: TestClient, db_path: Path
) -> None:
    """The requester, 9 September 2026: *"not to accept or reject, but simply to state a
    finding […] you could put the source, and it could take you to that copy."*
    """
    run_id, _product_id, finding_id = _run_with_findings(db_path)

    response = client.get(f"/runs/{run_id}")

    assert response.status_code == 200
    assert "What we found on the site" in response.text
    assert "Refrigeration" in response.text
    assert "Fridge/freezer" in response.text
    assert "141L fridge with freezer compartment" in response.text
    # And no decision form for it, which is what keeps it out of the CSV.
    assert f"/changes/{finding_id}/decide" not in response.text


def test_the_floorplan_finding_is_the_products_header_link(
    client: TestClient, db_path: Path
) -> None:
    """One link per product rather than one per positional field — the drawing answers
    them all at once, and a reviewer opens it once."""
    run_id, _product_id, _finding_id = _run_with_findings(db_path)

    response = client.get(f"/runs/{run_id}")

    assert 'class="product-floorplan"' in response.text
    assert 'href="https://www.rimor.it/plan.png"' in response.text
    # Not repeated as a statement in the list below it.
    assert response.text.count("https://www.rimor.it/plan.png") == 1


def test_deciding_a_finding_is_refused(client: TestClient, db_path: Path) -> None:
    """Only reachable by a hand-rolled POST — the page renders no form for one — but a
    decision would be honoured by `build_upload_products` and write the very column the
    pipeline no longer writes."""
    run_id, _product_id, finding_id = _run_with_findings(db_path)

    response = client.post(
        f"/runs/{run_id}/changes/{finding_id}/decide",
        data={"action": "accept", "reviewer_name": "ben"},
    )

    assert response.status_code == 400
    connection = store.connect(db_path)
    assert store.latest_decision(connection, finding_id) is None
    connection.close()


def test_a_new_product_keeps_its_blue_after_being_decided(
    client: TestClient, db_path: Path
) -> None:
    """The colour is how a reviewer picks the products needing a row typed into FMLV out
    of a long Decided list, and the findings only become actionable once the decisions are
    made — so losing the blue on acceptance threw it away at exactly the wrong moment.

    Requested 10 September 2026.
    """
    run_id, _product_id, _finding_id = _run_with_findings(db_path)
    # Every row, not `accept-all`, which deliberately holds back the ones a new product
    # has nothing to accept on — see `choices.needs_selection`.
    connection = store.connect(db_path)
    for entry in store.list_change_queue(connection, run_id):
        store.record_decision(
            connection, proposed_change_id=entry.change.id, action="accept", decided_by="ben"
        )
    connection.close()

    response = client.get(f"/runs/{run_id}")

    assert response.status_code == 200
    assert "Pending (0)" in response.text, "the product must have left the pending group"
    decided = response.text.split("Decided")[1]
    assert "product-group new-product" in decided
    assert "new product</span>" in decided
    # And the findings are still there to act on.
    assert "What we found on the site" in decided
