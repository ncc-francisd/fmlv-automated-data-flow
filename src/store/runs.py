"""Run lifecycle: start, finish, fail — the `run` table.

Every fetch/diff/review phase attaches its records to a run via `run_id`, but this
module only covers the run record itself; snapshots, proposed changes, decisions and
verifications are scaffolded in `schema.sql` for the phases that populate them.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from ..vehicle_class import DEFAULT as DEFAULT_VEHICLE_CLASS
from ..vehicle_class import VehicleClass

Trigger = Literal["manual", "scheduled"]
RunStatus = Literal["running", "succeeded", "failed"]


@dataclass(frozen=True)
class Run:
    """A single run: one manufacturer, one trigger, one outcome."""

    id: int
    manufacturer_id: int
    fmlv_manufacturer: str
    trigger: Trigger
    status: RunStatus
    started_at: str
    finished_at: str | None
    error_message: str | None
    range_label: str | None = None
    #: Which FMLV product area this run swept. Defaulted for the same reason the column
    #: is (`store/schema.sql`) — every run recorded before caravans existed was a
    #: motorhome run, and reads back as one.
    vehicle_class: VehicleClass = DEFAULT_VEHICLE_CLASS

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Run:
        return cls(
            id=row["id"],
            manufacturer_id=row["manufacturer_id"],
            fmlv_manufacturer=row["fmlv_manufacturer"],
            trigger=row["trigger"],
            status=row["status"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            error_message=row["error_message"],
            range_label=row["range_label"],
            vehicle_class=VehicleClass(row["vehicle_class"]),
        )


def _now() -> str:
    return datetime.now(UTC).isoformat()


def start_run(
    connection: sqlite3.Connection,
    *,
    manufacturer_id: int,
    fmlv_manufacturer: str,
    trigger: Trigger,
    range_label: str | None = None,
    vehicle_class: VehicleClass = DEFAULT_VEHICLE_CLASS,
) -> Run:
    """Record the start of a run. Status is 'running' until `finish_run`/`fail_run`.

    `range_label` is the human label of any `--range`/range-box restriction (e.g.
    "Matrix", or "Supersonic, Sonic" for more than one) — `None` for an unrestricted
    full-manufacturer run, which is what most of DESIGN.md's scheduled sweeps will be.

    `vehicle_class` is what makes two runs over the same manufacturer distinguishable.
    Eight of the sixteen registered manufacturers build both motorhomes and caravans, and
    a full sweep of either carries no `range_label` — so without this a Bailey caravan run
    and a Bailey motorhome run were two identical rows on the runs page.
    """
    cursor = connection.execute(
        """
        INSERT INTO run
            (manufacturer_id, fmlv_manufacturer, trigger, status, started_at, range_label,
             vehicle_class)
        VALUES (?, ?, ?, 'running', ?, ?, ?)
        """,
        (
            manufacturer_id,
            fmlv_manufacturer,
            trigger,
            _now(),
            range_label,
            VehicleClass(vehicle_class).value,
        ),
    )
    connection.commit()
    assert cursor.lastrowid is not None
    return get_run(connection, cursor.lastrowid)


def finish_run(connection: sqlite3.Connection, run_id: int) -> Run:
    """Mark a run as succeeded."""
    connection.execute(
        "UPDATE run SET status = 'succeeded', finished_at = ? WHERE id = ?",
        (_now(), run_id),
    )
    connection.commit()
    return get_run(connection, run_id)


def fail_run(connection: sqlite3.Connection, run_id: int, error_message: str) -> Run:
    """Mark a run as failed, recording why."""
    connection.execute(
        "UPDATE run SET status = 'failed', finished_at = ?, error_message = ? WHERE id = ?",
        (_now(), error_message, run_id),
    )
    connection.commit()
    return get_run(connection, run_id)


def get_run(connection: sqlite3.Connection, run_id: int) -> Run:
    """Fetch a run by id. Raises `KeyError` if it doesn't exist."""
    row = connection.execute("SELECT * FROM run WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        msg = f"no run with id {run_id}"
        raise KeyError(msg)
    return Run.from_row(row)


def list_runs(
    connection: sqlite3.Connection,
    *,
    manufacturer_id: int | None = None,
    status: RunStatus | None = None,
    vehicle_class: VehicleClass | None = None,
) -> list[Run]:
    """List runs, most recent first, optionally scoped by manufacturer, status and/or class.

    Every filter defaults to `None` meaning "don't filter" — in particular `vehicle_class`,
    so the runs page keeps showing both product areas together unless a reviewer narrows it.
    """
    clauses: list[str] = []
    params: list[object] = []
    if manufacturer_id is not None:
        clauses.append("manufacturer_id = ?")
        params.append(manufacturer_id)
    if status is not None:
        clauses.append("status = ?")
        params.append(status)
    if vehicle_class is not None:
        clauses.append("vehicle_class = ?")
        params.append(VehicleClass(vehicle_class).value)

    query = "SELECT * FROM run"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY started_at DESC"

    rows = connection.execute(query, params).fetchall()
    return [Run.from_row(row) for row in rows]


def list_run_manufacturers(connection: sqlite3.Connection) -> list[tuple[int, str]]:
    """Distinct `(manufacturer_id, fmlv_manufacturer)` pairs that have at least one run.

    For the runs page's manufacturer filter — drawn from run history rather than the
    registry, so it only ever offers manufacturers there's actually something to filter
    to, and stays correct even if the registry changes later.
    """
    rows = connection.execute(
        "SELECT DISTINCT manufacturer_id, fmlv_manufacturer FROM run ORDER BY fmlv_manufacturer"
    ).fetchall()
    return [(row["manufacturer_id"], row["fmlv_manufacturer"]) for row in rows]


@dataclass(frozen=True)
class RunTotals:
    """What a run found, as counts — the numbers a reviewer sanity-checks before accepting.

    **Not derivable from the change queue**, which is why these exist. A product the run
    read and found entirely unchanged raises no proposed change at all, so counting the
    queue undercounts the roster; on a quiet run it would report nothing collected.
    """

    #: Products this run read off the manufacturer's site.
    collected: int
    #: Of those, the ones no earlier run had seen.
    new: int
    #: Baseline products the run did not find. See `disappearance_notice`.
    disappeared: int

    @property
    def unchanged(self) -> int:
        return self.collected - self.new


#: A product this run stamped but did not actually find. `changes.persist_diff` calls
#: `upsert_seen` for a `DISAPPEARED` product as well, because the disappearance notice
#: needs a product row to hang off — so `last_seen_run_id` alone over-counts the roster by
#: exactly the number of disappearances. Carado's run 175 read 33 products and reported
#: 39, which is 33 and the 6 it could not find.
_NOT_ACTUALLY_FOUND = (
    "id IN (SELECT product_id FROM disappearance_notice WHERE run_id = ?)"
)


def run_totals(connection: sqlite3.Connection, run_id: int) -> RunTotals:
    """`RunTotals` for one run.

    `last_seen_run_id` is stamped on every product a run touched and `first_seen_run_id`
    only by the run that introduced it, so both counts fall out of the product table
    without the run needing to record anything — **less the disappearances**, which are
    stamped too and were never found. See `_NOT_ACTUALLY_FOUND`.
    """
    collected = connection.execute(
        f"SELECT COUNT(*) FROM product WHERE last_seen_run_id = ? AND NOT {_NOT_ACTUALLY_FOUND}",
        (run_id, run_id),
    ).fetchone()[0]
    new = connection.execute(
        f"SELECT COUNT(*) FROM product WHERE first_seen_run_id = ? AND NOT {_NOT_ACTUALLY_FOUND}",
        (run_id, run_id),
    ).fetchone()[0]
    disappeared = connection.execute(
        "SELECT COUNT(*) FROM disappearance_notice WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    return RunTotals(collected=collected, new=new, disappeared=disappeared)
