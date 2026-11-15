"""Products a run read and matched that raised no review row at all.

Added 15 November 2026. A reviewer counted five VIPs on Coachman's site, found three on
the run page, and reasonably suspected the adapter of missing two. It had read all five:
the other two agreed with FMLV on every field and publish `TBC` for every mass including
the nose weight, so there was nothing to propose and nothing to find. Silence was the
right answer and it was indistinguishable from a gap.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from src import store


def _run(connection: sqlite3.Connection) -> int:
    run = store.start_run(
        connection,
        manufacturer_id=25,
        fmlv_manufacturer="Coachman",
        trigger="manual",
        vehicle_class="caravan",
    )
    return run.id


def _product(
    connection: sqlite3.Connection,
    run_id: int,
    model: str,
    *,
    fmlv_product_id: int | None = 6681,
    manufacturer_range: str = "VIP",
) -> int:
    cursor = connection.execute(
        "INSERT INTO product (manufacturer_id, manufacturer_range, model,"
        " fmlv_product_id, first_seen_run_id, last_seen_run_id, vehicle_class)"
        " VALUES (25, ?, ?, ?, ?, ?, 'caravan')",
        (manufacturer_range, model, fmlv_product_id, run_id, run_id),
    )
    connection.commit()
    return int(cursor.lastrowid)


def _proposal(connection: sqlite3.Connection, run_id: int, product_id: int) -> None:
    connection.execute(
        "INSERT INTO proposed_change (run_id, product_id, field, old_value, new_value,"
        " created_at) VALUES (?, ?, 'mtplm_kilograms', NULL, '1452', '2026-11-15T00:00:00Z')",
        (run_id, product_id),
    )
    connection.commit()


def _verification(
    connection: sqlite3.Connection, run_id: int, product_id: int, field: str
) -> None:
    store.record_verification(
        connection, run_id=run_id, product_id=product_id, field=field
    )


def _disappearance(connection: sqlite3.Connection, run_id: int, product_id: int) -> None:
    connection.execute(
        "INSERT INTO disappearance_notice (run_id, product_id, note, created_at)"
        " VALUES (?, ?, 'not found', '2026-11-15T00:00:00Z')",
        (run_id, product_id),
    )
    connection.commit()


def test_a_product_that_raised_no_row_is_reported(tmp_path: Path) -> None:
    connection = store.connect(tmp_path / "runs.db")
    run_id = _run(connection)
    product_id = _product(connection, run_id, "520")
    for field in ("rrp_pounds", "berths", "shipping_length_mm"):
        _verification(connection, run_id, product_id, field)

    silent = store.silent_products(connection, run_id)

    assert [p.key for p in silent] == ["VIP 520"]
    assert silent[0].fmlv_product_id == 6681
    assert silent[0].verified_fields == 3
    connection.close()


def test_a_product_with_a_proposal_is_not_silent(tmp_path: Path) -> None:
    connection = store.connect(tmp_path / "runs.db")
    run_id = _run(connection)
    product_id = _product(connection, run_id, "460")
    _proposal(connection, run_id, product_id)

    assert store.silent_products(connection, run_id) == []
    connection.close()


def test_a_product_whose_only_row_is_a_finding_is_not_silent(tmp_path: Path) -> None:
    """**Not the same as "unchanged".**

    A product can agree with FMLV on every field and still raise a nose-weight finding,
    and then it does appear on the page. The test is on the rows, not the classification.
    """
    connection = store.connect(tmp_path / "runs.db")
    run_id = _run(connection)
    product_id = _product(connection, run_id, "575")
    connection.execute(
        "INSERT INTO proposed_change (run_id, product_id, field, old_value, new_value,"
        " created_at, is_finding) VALUES (?, ?, 'max_nose_weight_kilograms', NULL, '100',"
        " '2026-11-15T00:00:00Z', 1)",
        (run_id, product_id),
    )
    connection.commit()

    assert store.silent_products(connection, run_id) == []
    connection.close()


def test_a_disappeared_product_is_not_silent(tmp_path: Path) -> None:
    """It was not read and found identical — it was looked for and not found, and it has
    its own notice."""
    connection = store.connect(tmp_path / "runs.db")
    run_id = _run(connection)
    product_id = _product(connection, run_id, "675")
    _disappearance(connection, run_id, product_id)

    assert store.silent_products(connection, run_id) == []
    connection.close()


def test_a_product_last_seen_by_an_earlier_run_is_not_reported(tmp_path: Path) -> None:
    connection = store.connect(tmp_path / "runs.db")
    first = _run(connection)
    _product(connection, first, "520")
    second = _run(connection)

    assert store.silent_products(connection, second) == []
    connection.close()


def test_silent_products_read_in_range_and_model_order(tmp_path: Path) -> None:
    connection = store.connect(tmp_path / "runs.db")
    run_id = _run(connection)
    _product(connection, run_id, "565", manufacturer_range="VIP")
    _product(connection, run_id, "545 Xtra", manufacturer_range="Acadia")
    _product(connection, run_id, "520", manufacturer_range="VIP")

    assert [p.key for p in store.silent_products(connection, run_id)] == [
        "Acadia 545 Xtra",
        "VIP 520",
        "VIP 565",
    ]
    connection.close()


def test_a_product_with_no_verification_says_so_rather_than_claiming_a_match(
    tmp_path: Path,
) -> None:
    """Zero checked fields is a different situation from zero differing fields, and the
    summary wording depends on telling them apart."""
    connection = store.connect(tmp_path / "runs.db")
    run_id = _run(connection)
    _product(connection, run_id, "520")

    assert store.silent_products(connection, run_id)[0].verified_fields == 0
    connection.close()
