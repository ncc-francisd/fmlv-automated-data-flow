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
    #: The NCC supplier label this run's baseline was exported under, the file it came
    #: back in, and how many rows of it survived the baseline filter. All three are
    #: `None` on a run recorded before `record_baseline` existed, and on one that failed
    #: before it got that far. See `record_baseline`.
    baseline_supplier: str | None = None
    baseline_export: str | None = None
    baseline_count: int | None = None

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
            baseline_supplier=row["baseline_supplier"],
            baseline_export=row["baseline_export"],
            baseline_count=row["baseline_count"],
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


def record_baseline(
    connection: sqlite3.Connection,
    run_id: int,
    *,
    supplier_name: str | None,
    export_path: str,
    product_count: int,
) -> Run:
    """Record what this run compared against, before it compares anything.

    **The gap this closes.** A run says what it collected and what it proposes, and said
    nothing at all about the other half of the comparison. So when Panama's `P\12+` and
    `P\50+` arrived as new products on 19 November 2026 while FMLV held both live and
    active, there was no way to see from the run that its baseline held three Panama rows
    rather than five — the two were missing because the registry named the importer's NCC
    supplier entry, which returns a different set of products from the brand's own. The
    run succeeded, the counts looked plausible, and accepting the two "new" products would
    have duplicated two live ones.

    An incomplete baseline never announces itself: it proposes live products as new, which
    is indistinguishable from a manufacturer that has genuinely grown. Naming the supplier,
    the file and the row count is what lets a reviewer tell the two apart in a glance
    instead of a download.

    Written as soon as the baseline is built rather than at the end, so a run that fails
    later still says what it was working from.
    """
    connection.execute(
        """
        UPDATE run
           SET baseline_supplier = ?, baseline_export = ?, baseline_count = ?
         WHERE id = ?
        """,
        (supplier_name, export_path, product_count, run_id),
    )
    connection.commit()
    return get_run(connection, run_id)


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
class SilentProduct:
    """A product this run read and matched that produced no review row of any kind.

    **The gap this closes.** A reviewer counts the products on a manufacturer's site,
    counts the ones on the run page, and finds fewer — which looks exactly like the
    adapter having missed some. It is usually the opposite: the product was read, every
    field agreed with FMLV, and a run only writes a row where it has something to say.

    The requester, 15 November 2026, on Coachman's VIP range: *"the site has 5 VIPs […]
    and the review run only had 3 […] I'm just going to check if the adapter was also
    picking up the other 2"*. It was. Both publish `TBC` for every mass including the
    nose weight, so there was nothing to propose and nothing to find, and they vanished
    from the page. Naming them is the whole fix.

    `verified_fields` is how many fields were checked and matched — the evidence that
    silence here means agreement rather than an adapter that never looked.
    """

    product_id: int
    fmlv_product_id: int | None
    key: str
    verified_fields: int


def silent_products(connection: sqlite3.Connection, run_id: int) -> list[SilentProduct]:
    """Every product this run read that raised no row — ordered as a reviewer reads them.

    **Not the same as "unchanged".** A product whose fields all matched can still raise a
    finding (a nose weight, a habitation reading on a new product), and then it does appear
    on the page. What matters to a reviewer scanning for a missing model is whether the
    product produced *anything*, so the test is on the rows themselves rather than on the
    diff's classification.

    Disappearances are excluded: they were not read, they were looked for and not found,
    and they have their own notices.

    Like `run_totals`, this reads `last_seen_run_id`, which only ever holds the newest
    run that touched a product. So a **superseded** run reports nothing silent, the same
    way its page already reports nothing collected. That is the existing meaning of the
    column rather than a limitation introduced here, and the two stay consistent.
    """
    rows = connection.execute(
        """
        SELECT p.id,
               p.fmlv_product_id,
               p.manufacturer_range,
               p.model,
               (SELECT COUNT(*) FROM verification v
                 WHERE v.run_id = ? AND v.product_id = p.id) AS verified
          FROM product p
         WHERE p.last_seen_run_id = ?
           AND NOT EXISTS (SELECT 1 FROM proposed_change c
                            WHERE c.run_id = ? AND c.product_id = p.id)
           AND NOT EXISTS (SELECT 1 FROM disappearance_notice d
                            WHERE d.run_id = ? AND d.product_id = p.id)
         ORDER BY p.manufacturer_range, p.model
        """,
        (run_id, run_id, run_id, run_id),
    ).fetchall()
    return [
        SilentProduct(
            product_id=row["id"],
            fmlv_product_id=row["fmlv_product_id"],
            key=" ".join(
                part for part in (row["manufacturer_range"], row["model"]) if part
            ),
            verified_fields=row["verified"],
        )
        for row in rows
    ]


@dataclass(frozen=True)
class RunTotals:
    """What a run found, as counts — the numbers a reviewer sanity-checks before accepting.

    **Not derivable from the change queue**, which is why these exist. A product the run
    read and found entirely unchanged raises no proposed change at all, so counting the
    queue undercounts the roster; on a quiet run it would report nothing collected.
    """

    #: Products this run read off the manufacturer's site.
    collected: int
    #: Of those, the ones **FMLV does not hold** — no `fmlv_product_id`, so they matched
    #: no baseline row. See `run_totals` for why it is not "first seen by this pipeline".
    new: int
    #: Baseline products the run did not find. See `disappearance_notice`.
    disappeared: int

    @property
    def matched(self) -> int:
        """Collected products that found an FMLV row. Not *unchanged* — they may well
        carry proposed corrections; what they are is already in FMLV."""
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

    `last_seen_run_id` is stamped on every product a run touched, so `collected` falls out
    of the product table without the run needing to record anything — **less the
    disappearances**, which are stamped too and were never found. See `_NOT_ACTUALLY_FOUND`.

    **`new` means absent from FMLV, not absent from this pipeline.** It was
    `first_seen_run_id = run_id`, which is a different question and reads right only after
    a manufacturer's first run: on that run every product is first-seen, so the page said
    `9 products collected · 9 new` for Bespoke's run 190 where eight of the nine had
    matched an FMLV row and the upload CSV correctly carried one new product. The reviewer
    reads "new" as "FMLV does not have this", which is also what the run page means by it
    one line further down — `run_detail.html` marks a card new on `not
    product.fmlv_product_id`. This counts the same thing, so the header and the cards
    below it can no longer disagree.

    A product stays new until it is uploaded and comes back in an export with an id. That
    is correct: for as long as FMLV does not hold it, the run really is proposing it.
    """
    collected = connection.execute(
        f"SELECT COUNT(*) FROM product WHERE last_seen_run_id = ? AND NOT {_NOT_ACTUALLY_FOUND}",
        (run_id, run_id),
    ).fetchone()[0]
    new = connection.execute(
        "SELECT COUNT(*) FROM product WHERE last_seen_run_id = ?"
        f" AND fmlv_product_id IS NULL AND NOT {_NOT_ACTUALLY_FOUND}",
        (run_id, run_id),
    ).fetchone()[0]
    disappeared = connection.execute(
        "SELECT COUNT(*) FROM disappearance_notice WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    return RunTotals(collected=collected, new=new, disappeared=disappeared)
