"""What a run found, as counts, for the reviewer to sanity-check a roster against.

Added 2 October 2026: the run page showed `Pending (84)` and nothing else, so there was
no way to tell from it whether Carado's 33 products had all arrived.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from src import store


def _run(connection: sqlite3.Connection, manufacturer_id: int = 60) -> int:
    run = store.start_run(
        connection,
        manufacturer_id=manufacturer_id,
        fmlv_manufacturer="Carado",
        trigger="manual",
    )
    return run.id


def _product(
    connection: sqlite3.Connection,
    run_id: int,
    model: str,
    *,
    first: int | None = None,
    fmlv_product_id: int | None = None,
) -> None:
    """One product row. `fmlv_product_id=None` is a product FMLV does not hold — which is
    what makes it *new*, and is deliberately the default here."""
    connection.execute(
        "INSERT INTO product (manufacturer_id, manufacturer_range, model,"
        " fmlv_product_id, first_seen_run_id, last_seen_run_id, vehicle_class)"
        " VALUES (60, 'Van', ?, ?, ?, ?, 'motorhome')",
        (model, fmlv_product_id, first if first is not None else run_id, run_id),
    )
    connection.commit()


def test_a_run_that_found_nothing_counts_nothing(tmp_path) -> None:
    connection = store.connect(tmp_path / "runs.db")
    run_id = _run(connection)

    totals = store.run_totals(connection, run_id)

    assert (totals.collected, totals.new, totals.disappeared) == (0, 0, 0)
    connection.close()


def test_every_product_the_run_read_is_counted(tmp_path) -> None:
    connection = store.connect(tmp_path / "runs.db")
    run_id = _run(connection)
    for model in ("V132", "V337", "V347"):
        _product(connection, run_id, model, fmlv_product_id=None)

    totals = store.run_totals(connection, run_id)

    assert totals.collected == 3
    assert totals.new == 3
    assert totals.matched == 0
    connection.close()


def test_a_product_that_matched_an_fmlv_row_is_not_new(tmp_path) -> None:
    """**The trap this exists for.** `new` used to mean "no earlier run had seen it",
    which on a manufacturer's *first* run is every product — so Bespoke's run 190 said
    `9 products collected · 9 new` where eight had matched an FMLV row and only one was
    genuinely new. The reviewer reads "new" as "FMLV does not have this", and so does the
    card below it, which `run_detail.html` marks new on `not product.fmlv_product_id`."""
    connection = store.connect(tmp_path / "runs.db")
    run_id = _run(connection)
    for model, fmlv_id in (("V132", 7963), ("V337", 7964), ("V347", None)):
        _product(connection, run_id, model, fmlv_product_id=fmlv_id)

    totals = store.run_totals(connection, run_id)

    assert totals.collected == 3
    assert totals.new == 1, "only the one FMLV does not hold"
    assert totals.matched == 2
    connection.close()


def test_a_product_the_pipeline_has_seen_before_is_still_new_until_fmlv_holds_it(
    tmp_path,
) -> None:
    """Being proposed once does not put it in FMLV. Until it is uploaded and comes back in
    an export with an id, the run really is still proposing it — and the page still draws
    it as a new-product card — so the count has to agree."""
    connection = store.connect(tmp_path / "runs.db")
    first_run = _run(connection)
    second_run = _run(connection)
    _product(connection, second_run, "V132", first=first_run, fmlv_product_id=None)
    _product(connection, second_run, "V337", first=first_run, fmlv_product_id=7900)

    totals = store.run_totals(connection, second_run)

    assert totals.collected == 2
    assert totals.new == 1
    assert totals.matched == 1
    connection.close()


def test_the_count_survives_a_run_where_nothing_changed(tmp_path) -> None:
    """**The reason this is not counted off the change queue.** A product read and found
    entirely unchanged raises no proposed change, so a queue-based count would report a
    quiet run as having collected nothing — the opposite of the truth, and exactly the
    case where a reviewer most wants to know the roster was complete."""
    connection = store.connect(tmp_path / "runs.db")
    first_run = _run(connection)
    second_run = _run(connection)
    for index, model in enumerate(("V132", "V337", "V347")):
        _product(
            connection, second_run, model, first=first_run, fmlv_product_id=7900 + index
        )

    totals = store.run_totals(connection, second_run)

    assert store.list_change_queue(connection, second_run) == []
    assert totals.collected == 3
    assert totals.new == 0
    connection.close()


def test_products_from_another_run_are_not_counted(tmp_path) -> None:
    connection = store.connect(tmp_path / "runs.db")
    mine = _run(connection)
    theirs = _run(connection)
    _product(connection, mine, "V132")
    _product(connection, theirs, "V337")

    assert store.run_totals(connection, mine).collected == 1
    assert store.run_totals(connection, theirs).collected == 1
    connection.close()


def test_a_product_the_run_could_not_find_is_not_counted_as_collected() -> None:
    """**The trap this exists for.** `persist_diff` calls `upsert_seen` for a DISAPPEARED
    product too, because the notice needs a product row to hang off — so counting
    `last_seen_run_id` alone over-states the roster by exactly the disappearances. Carado's
    run 175 read 33 products and the page said 39, which was 33 plus the 6 it had lost."""
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        connection = store.connect(Path(folder) / "runs.db")
        run_id = _run(connection)
        for model in ("V132", "V337", "V347"):
            _product(connection, run_id, model)
        gone = connection.execute(
            "SELECT id FROM product WHERE model = 'V347'"
        ).fetchone()[0]
        store.record_disappearance_notice(
            connection, run_id=run_id, product_id=gone, note="not on the site"
        )
        connection.commit()

        totals = store.run_totals(connection, run_id)

        assert totals.collected == 2, "the one it could not find is not collected"
        assert totals.new == 2
        assert totals.disappeared == 1
        connection.close()
