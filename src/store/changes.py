"""Turning a run's diff (Phase 5's `diff.diff_products`) into durable rows.

`diff_products` is a pure, in-memory function — this module is where its output
becomes something a reviewer can act on: `proposed_change` rows for anything that
changed or is new, `verification` rows for anything checked and confirmed unchanged
(DESIGN.md §6.5). `ChangeKind.DISAPPEARED` is deliberately not persisted here — there's
no actionable proposal for it yet (proposing `archived = Yes` is still [F], see
TODO.md Phase 5).

DESIGN.md §6.8 ("rejections are remembered") is enforced in `was_previously_rejected`:
a proposed change is skipped if the exact same (product, field, new_value) was
rejected last time. A manufacturer later publishing a *different* corrected figure for
that field is a new proposal and is still shown — only the literal rejected value is
suppressed.

A `year_rollover_eligible` product (DESIGN.md §6.9) gets one more proposal beyond
what `diff.compare` found: a `field="year"` change from the baseline's year to
`year_rollover.bump_year`'s result. This is deliberately routed through the exact
same `proposed_change`/`decision` machinery as every other field — accepting it *is*
the "checkbox" TODO.md's Phase 5 entry described, rather than a separate mechanism.
Its `source_url` is `None` and its snippet says so: the suggestion comes from the
pipeline noticing the season, not from anything read off the manufacturer's site.

`bump_year_all` is §6.9's *other* route, the one the CLI's `--bump-year` passes:
the same proposal, for every product of the manufacturer rather than only the
seasonally plausible ones. Both routes converge here deliberately — a globally
requested rollover is still reviewed and accepted per product, and the pipeline
still never writes `year` on its own. Neither route proposes a bump unless the
baseline's `year` is exactly today's year — `year_rollover.can_bump_year` gates it,
so a product already sitting at `current_year + 1` (bumped and accepted earlier) or
still showing some older, stale year is never offered one.

`ChangeKind.DISAPPEARED` **is** persisted here, as a `disappearance_notice` row rather
than being dropped: a product missing from a manufacturer's latest sweep is exactly
the kind of thing a reviewer needs put in front of them, not silence. It is
deliberately *not* a `proposed_change` — there is no CSV field to change, since the
product hasn't been archived, only found missing from the site this sweep — so it
carries no accept/reject/correct affordance. It is a prompt for a reviewer to go and
consider manually deactivating the product on the FMLV Nova site themselves.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from ..diff.classify import ChangeKind, ProductDiff
from ..diff.compare import MissingField, field_value, profile_for
from ..diff.year_rollover import bump_year, can_bump_year
from ..product_model import caravan_schema, schema
from ..product_model.caravan import Caravan
from ..product_model.findings import (
    FINDING_FIELDS,
    FLOORPLAN_FIELD,
    FLOORPLAN_SNIPPET,
    SILENCE_MEANS,
)
from ..product_model.validation import (
    CARAVAN_LAYOUT_GROUP_FIELDS,
    LAYOUT_GROUP_FIELDS,
)
from ..vehicle_class import DEFAULT as DEFAULT_VEHICLE_CLASS
from ..vehicle_class import VehicleClass
from . import products as products_store
from .decisions import Decision
from .products import Product

#: `source_snippet` for the year-rollover suggestion — explains its provenance is the
#: pipeline's own seasonal heuristic, not a fact read off the manufacturer's site.
YEAR_ROLLOVER_SNIPPET = (
    "Suggested by the pipeline: this product is still on the manufacturer's site during "
    "the June-September model-year rollover window (DESIGN.md §6.9). Offered whether or "
    "not anything else changed, since a model carried over unrevised is still a current "
    "one. The model year is not published on the site, so this is a prompt to confirm, "
    "not a reading."
)

#: `note` for a `disappearance_notice` row — a `DISAPPEARED` product.
DISAPPEARANCE_NOTE = (
    "Not found on the manufacturer's site during this run's latest sweep. This is not "
    "a proposed CSV change — consider manually deactivating this product on the FMLV "
    "Nova site."
)

#: `source_snippet` for a `diff.MissingField` proposal — an in-scope field
#: (its area's `IN_SCOPE`) the adapter couldn't find this run. Reviewer templates match
#: on this exact text (`webapp.app`'s `is_missing_field` global) the same way
#: `ARCHIVE_SNIPPET`/`YEAR_ROLLOVER_SNIPPET` are matched on, since `proposed_change`
#: has no column of its own for "why was this proposed".
MISSING_FIELD_SNIPPET = (
    "This field is marked in-scope for automated collection, but was not found on "
    "the manufacturer's site this run. Confirm the existing figure is still "
    "correct, or enter a replacement."
)

#: The same offer for a field that is *not* in scope, but which the adapter attempted and
#: could not fill — it identified the family but not the value. Separate from
#: `MISSING_FIELD_SNIPPET` only so neither piece of wording has to lie; the reviewer is
#: offered exactly the same two actions, and `webapp.app`'s `is_missing_field` matches
#: both. Kept distinct rather than replacing the original, because rows already stored in
#: a deployed run store carry the original text and are matched on it exactly.
UNDETERMINED_FIELD_SNIPPET = (
    "The adapter identified what kind of product this is but could not determine this "
    "field from the manufacturer's site. Confirm the existing value is still correct, "
    "or choose a replacement."
)

#: `source_snippet` for a field a new product would otherwise reach FMLV blank on.
#: Nothing was read off the site — the adapter could not determine it and there is no
#: baseline to keep — so the reviewer has to choose, and `choices.needs_selection` marks
#: the row accordingly.
NEEDS_A_CHOICE_SNIPPET = (
    "Nothing was found for this field and there is no existing value to keep, so it "
    "needs one. Left unset, FMLV receives the product with this column blank."
)


def fields_needing_a_choice(product: Product) -> tuple[str, ...]:
    """Fields a **new** product must not reach FMLV blank, in the order to show them.

    Two kinds, and both were shipping blank without the reviewer ever seeing a row:

    * **Required columns** the adapter could not fill. `Kilig 55 Plus` went out with no
      MRO, MTPLM or payload, and the only sign was `required field 'mro_kilograms' is
      missing` in the issues file after the upload was generated.
    * **The body type**, where the adapter could not derive one. It is a choice across
      eight mutually exclusive columns, so a blank leaves the product uncategorised in
      every FMLV filter — the `Rimor Van 238` has no factory page at all and went out
      with nothing in any of them.

    The identity strings are excluded: `manufacturer`, `model` and their kin are always
    set on a product that exists at all, and a reviewer cannot usefully be asked to
    choose one. So are the habitation fields — bed types, the washroom, the kitchen and
    lounge locations, heating: those are **findings**, reported for a person to type in
    rather than asked about here. `product_model.findings` records why. `body_type`
    survives that exclusion and is the only member of either layout group left, because
    it is derived from a published height and segment rather than read off a drawing.
    """
    layout = (
        CARAVAN_LAYOUT_GROUP_FIELDS
        if isinstance(product, Caravan)
        else LAYOUT_GROUP_FIELDS
    )
    required = caravan_schema.REQUIRED if isinstance(product, Caravan) else schema.REQUIRED
    return (
        *(f for f in sorted(required) if f not in _IDENTITY_FIELDS),
        *(f for f in layout if f not in FINDING_FIELDS),
    )


#: Never asked about: a product with no manufacturer or model does not exist, and these
#: are what `diff.matching` keys on.
_IDENTITY_FIELDS: frozenset[str] = frozenset(
    {"manufacturer", "manufacturer_display_name", "manufacturer_range", "model"}
)


#: How `_serialize` joins a multi-valued field (e.g. `bed_types`) into one TEXT column.
#: `output.build.apply_field` is `_serialize`'s inverse and splits on this same
#: constant — keep them in sync.
LIST_SEPARATOR = ", "


#: `source_snippet` for a payload the pipeline derived rather than read. Says where the
#: two masses came from, because "no source found this run" and "here is a corrected
#: payload" look contradictory side by side unless the arithmetic is spelled out.
PAYLOAD_ARITHMETIC_SNIPPET = (
    "Derived {label}, not read from the site: {mtplm}kg MTPLM - {mro}kg MRO = "
    "{derived}kg, against the {held}kg on record. {basis}. Accepting this makes the "
    "three figures agree; rejecting it leaves FMLV as it is."
)


#: The payloads that are MTPLM minus an MRO, as `(payload path, MRO path, label)`. The
#: automatic variant has no MTPLM of its own — it is the same chassis with a different
#: gearbox — so both derive from the one `mtplm_kilograms`, which is what
#: `validation._validate_automatic` checks too.
_DERIVED_PAYLOADS: tuple[tuple[str, str, str], ...] = (
    ("mh_payload_kilograms", "mro_kilograms", "payload"),
    ("automatic.payload_kilograms", "automatic.mro_kilograms", "automatic payload"),
)


def _derived_payload_proposals(
    diff: ProductDiff,
) -> list[tuple[str, int, int, str]]:
    """`(field path, derived, held, explanation)` for each payload the masses contradict.

    Payload is arithmetic — MTPLM minus MRO — so it is checkable whether or not the
    manufacturer published anything this run. Until now a disagreement only surfaced as a
    `payload_mismatch` warning in the issues file, after the upload had been generated.

    The requester, 7 September 2026, on Horus 38: *"that figure for the payload should be
    876. So should be presenting a correction to the payload figure of 676, because if the
    MRO and MTPLM are correct, the figure should be 876. Even though you have no source to
    prove what the actual MRO and MTPLM are, you've simply carried it over from FMLV."*
    Extended to the automatic variant the same day, on the same reasoning — Horus 38 and
    40, Kilig 77 Plus, Sailer 69 and Sarus 66 Plus all disagree there too.

    Each mass is taken from the site where the adapter found one and from FMLV where it
    did not, which is what the upload row will hold, and the explanation says which.
    Skipped where the adapter is already proposing that payload — it does the same
    arithmetic, with a real source behind it — and skipped for caravans, whose
    `personal_effects_payload_kilograms` is *not* MTPLM minus MRO but the personal-effects
    half of a split.
    """
    baseline, extracted = diff.baseline, diff.extracted
    if baseline is None or extracted is None:
        return []
    if isinstance(baseline, Caravan) or isinstance(extracted.product, Caravan):
        return []

    def effective(field_path: str) -> tuple[int | None, bool]:
        scraped = field_value(extracted.product, field_path)
        if scraped is not None:
            return scraped, True
        return field_value(baseline, field_path), False

    mtplm, mtplm_scraped = effective("mtplm_kilograms")
    if mtplm is None:
        return []

    found: list[tuple[str, int, int, str]] = []
    for payload_path, mro_path, label in _DERIVED_PAYLOADS:
        if any(change.field == payload_path for change in diff.changes):
            continue
        mro, mro_scraped = effective(mro_path)
        held = field_value(baseline, payload_path)
        if mro is None or held is None:
            continue
        derived = mtplm - mro
        if derived == held:
            continue
        found.append(
            (
                payload_path,
                derived,
                held,
                PAYLOAD_ARITHMETIC_SNIPPET.format(
                    label=label,
                    mtplm=mtplm,
                    mro=mro,
                    derived=derived,
                    held=held,
                    basis=_mass_basis(mtplm_scraped, mro_scraped, label),
                ),
            )
        )
    return found


def _mass_basis(mtplm_scraped: bool, mro_scraped: bool, label: str) -> str:
    """Where each of the two masses came from, in words."""
    mro_name = "MRO" if label == "payload" else "automatic MRO"
    if mtplm_scraped and mro_scraped:
        return "Both masses come from the manufacturer's site this run"
    if not mtplm_scraped and not mro_scraped:
        return (
            "Neither mass was published this run, so both are FMLV's own figures "
            "carried over"
        )
    if mtplm_scraped:
        return (
            f"The MTPLM comes from the site this run; the {mro_name} is FMLV's own, "
            f"carried over"
        )
    return (
        f"The {mro_name} comes from the site this run; the MTPLM is FMLV's own, "
        f"carried over"
    )


def _missing_field_snippet(missing: MissingField) -> str:
    """The confirm-or-replace offer, plus whatever evidence the adapter recorded.

    Both constants stay **prefixes** of what is stored, because `webapp.app`'s
    `is_missing_field` identifies these rows by their opening text — there is no DB column
    for "why was this proposed" — and rows already written to a deployed run store carry
    the bare constant.

    Appending the adapter's own snippet is what gives a reviewer something to act on: for
    a field the adapter attempted and could not fill, that snippet quotes the page wording
    identifying what kind of product this is, and `source_url` links to the page it came
    from. Requested 2026-08-29.
    """
    if missing.old_value is None:
        # Nothing on either side, so "keep the existing value" is not one of the answers —
        # there is no existing value. Same wording, and so the same red flag and the same
        # set-or-leave-blank buttons, as a new product's empty column.
        base = NEEDS_A_CHOICE_SNIPPET
    else:
        base = (
            MISSING_FIELD_SNIPPET
            if missing.in_scope
            else UNDETERMINED_FIELD_SNIPPET
        )
    if missing.provenance and missing.provenance.snippet:
        return f"{base} {missing.provenance.snippet}"
    return base


@dataclass(frozen=True)
class ProposedChange:
    """One field-level proposal, persisted from a `diff.FieldChange` or a new field."""

    id: int
    run_id: int
    product_id: int
    field: str
    old_value: str | None
    new_value: str | None
    source_url: str | None
    source_snippet: str | None
    confidence: float | None
    created_at: str
    #: True when this row exists to hand the reviewer a source — the floorplan for a
    #: field no wording settles — rather than to propose a value.
    reviewer_reference: bool = False
    #: True when this row **states what the adapter found** for a person to type into
    #: FMLV by hand, rather than proposing anything. Findings are kept out of
    #: `list_change_queue` entirely, so nothing can decide one and nothing can carry one
    #: into an upload — see `product_model.findings`.
    is_finding: bool = False

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> ProposedChange:
        return cls(
            id=row["id"],
            run_id=row["run_id"],
            product_id=row["product_id"],
            field=row["field"],
            old_value=row["old_value"],
            new_value=row["new_value"],
            source_url=row["source_url"],
            source_snippet=row["source_snippet"],
            confidence=row["confidence"],
            created_at=row["created_at"],
            reviewer_reference=bool(row["reviewer_reference"]),
            is_finding=bool(row["is_finding"]),
        )


@dataclass(frozen=True)
class ChangeQueueEntry:
    """One row for the review UI: a proposed change, its product, and its decision."""

    change: ProposedChange
    product: Product
    decision: Decision | None


@dataclass(frozen=True)
class DisappearanceNotice:
    """One note that a baseline product wasn't found on the manufacturer's site."""

    id: int
    run_id: int
    product_id: int
    note: str
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> DisappearanceNotice:
        return cls(
            id=row["id"],
            run_id=row["run_id"],
            product_id=row["product_id"],
            note=row["note"],
            created_at=row["created_at"],
        )


@dataclass(frozen=True)
class DisappearanceNoticeEntry:
    """One row for the review UI: a disappearance notice with its product."""

    notice: DisappearanceNotice
    product: Product


@dataclass(frozen=True)
class RunReviewSummary:
    """Review status of one run's change queue, for the runs overview page."""

    pending_count: int
    primary_reviewer: str | None


@dataclass(frozen=True)
class PersistResult:
    """A summary of what persisting one run's diff did — for a run-completion message."""

    proposed: int = 0
    verified: int = 0
    suppressed_rejections: int = 0
    year_rollover_proposed: int = 0
    archive_proposed: int = 0
    missing_field_proposed: int = 0
    disappeared_noted: int = 0
    #: Read-only statements of what the adapter found, for a person to type into FMLV by
    #: hand. Counted separately from `proposed` because nothing decides one, so they are
    #: not work waiting on a reviewer — see `product_model.findings`.
    findings_recorded: int = 0


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _serialize(value: Any) -> str | None:
    """Stringify a diff value for storage — every `proposed_change` column is TEXT."""
    if value is None:
        return None
    if isinstance(value, list):
        return LIST_SEPARATOR.join(item for item in (_serialize(entry) for entry in value) if item)
    if hasattr(value, "value"):  # enum member, e.g. BodyType.A_CLASS
        return str(value.value)
    return str(value)


def get_proposed_change(connection: sqlite3.Connection, change_id: int) -> ProposedChange:
    """Fetch a proposed change by id. Raises `KeyError` if it doesn't exist."""
    row = connection.execute(
        "SELECT * FROM proposed_change WHERE id = ?", (change_id,)
    ).fetchone()
    if row is None:
        msg = f"no proposed_change with id {change_id}"
        raise KeyError(msg)
    return ProposedChange.from_row(row)


def was_previously_rejected(
    connection: sqlite3.Connection, *, product_id: int, field: str, new_value: str | None
) -> bool:
    """Whether the exact (product, field, new_value) triple was rejected last time.

    Only the most recent decision for a matching proposal counts — an earlier
    rejection later overridden (accept/correct) must not keep suppressing it.
    """
    row = connection.execute(
        """
        SELECT decision.action
        FROM proposed_change
        JOIN decision ON decision.proposed_change_id = proposed_change.id
        WHERE proposed_change.product_id = ?
          AND proposed_change.field = ?
          AND proposed_change.new_value IS ?
        ORDER BY decision.decided_at DESC, decision.id DESC
        LIMIT 1
        """,
        (product_id, field, new_value),
    ).fetchone()
    return row is not None and row["action"] == "reject"


def record_proposed_change(
    connection: sqlite3.Connection,
    *,
    run_id: int,
    product_id: int,
    field: str,
    old_value: str | None,
    new_value: str | None,
    source_url: str | None = None,
    source_snippet: str | None = None,
    confidence: float | None = None,
    reviewer_reference: bool = False,
    is_finding: bool = False,
) -> ProposedChange:
    cursor = connection.execute(
        """
        INSERT INTO proposed_change
            (run_id, product_id, field, old_value, new_value, source_url, source_snippet,
             confidence, created_at, reviewer_reference, is_finding)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (run_id, product_id, field, old_value, new_value, source_url, source_snippet,
         confidence, _now(), int(reviewer_reference), int(is_finding)),
    )
    connection.commit()
    assert cursor.lastrowid is not None
    return get_proposed_change(connection, cursor.lastrowid)


def verified_fields_by_product(
    connection: sqlite3.Connection, run_id: int
) -> dict[int, list[str]]:
    """Which fields were checked and found unchanged, per product, for one run.

    A field with no proposal is ambiguous to a reviewer — it may have been checked and
    matched, or never looked at, or withheld because the same value was rejected before.
    The requester, 8 September 2026, on Kilig 77 Plus: *"I noticed that there's no
    proposal on bed types. Is this because there is no change in the bed types?"* This is
    what lets the review page answer that, from the `verification` rows `persist_diff`
    already writes.
    """
    rows = connection.execute(
        "SELECT product_id, field FROM verification WHERE run_id = ? ORDER BY field",
        (run_id,),
    ).fetchall()
    verified: dict[int, list[str]] = {}
    for row in rows:
        verified.setdefault(row["product_id"], []).append(row["field"])
    return verified


def record_verification(
    connection: sqlite3.Connection, *, run_id: int, product_id: int, field: str
) -> None:
    connection.execute(
        "INSERT INTO verification (run_id, product_id, field, verified_at) VALUES (?, ?, ?, ?)",
        (run_id, product_id, field, _now()),
    )
    connection.commit()


def record_disappearance_notice(
    connection: sqlite3.Connection, *, run_id: int, product_id: int, note: str
) -> DisappearanceNotice:
    cursor = connection.execute(
        "INSERT INTO disappearance_notice (run_id, product_id, note, created_at) "
        "VALUES (?, ?, ?, ?)",
        (run_id, product_id, note, _now()),
    )
    connection.commit()
    row = connection.execute(
        "SELECT * FROM disappearance_notice WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return DisappearanceNotice.from_row(row)


def run_review_summary(connection: sqlite3.Connection, run_id: int) -> RunReviewSummary:
    """How much of a run's change queue is left to review, and who's reviewed most of it.

    `primary_reviewer` is whichever named reviewer has the most decisions recorded on
    this run (ties broken alphabetically) — a simple "who's mainly been through this"
    signal for the runs overview page, not a permissions concept. `None` if nothing on
    the run has been decided yet.
    """
    pending_row = connection.execute(
        """
        SELECT COUNT(*) AS pending
        FROM proposed_change
        LEFT JOIN decision ON decision.id = (
            SELECT id FROM decision AS latest
            WHERE latest.proposed_change_id = proposed_change.id
            ORDER BY latest.decided_at DESC, latest.id DESC
            LIMIT 1
        )
        WHERE proposed_change.run_id = ? AND decision.id IS NULL
        """,
        (run_id,),
    ).fetchone()

    reviewer_row = connection.execute(
        """
        SELECT decision.decided_by AS reviewer, COUNT(*) AS n
        FROM proposed_change
        JOIN decision ON decision.id = (
            SELECT id FROM decision AS latest
            WHERE latest.proposed_change_id = proposed_change.id
            ORDER BY latest.decided_at DESC, latest.id DESC
            LIMIT 1
        )
        WHERE proposed_change.run_id = ? AND decision.decided_by IS NOT NULL
        GROUP BY decision.decided_by
        ORDER BY n DESC, reviewer ASC
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()

    return RunReviewSummary(
        pending_count=pending_row["pending"],
        primary_reviewer=reviewer_row["reviewer"] if reviewer_row is not None else None,
    )


def _record_findings(
    connection: sqlite3.Connection,
    *,
    run_id: int,
    product_id: int,
    extracted: Any,
    is_new: bool,
) -> int:
    """Store what the adapter *found* about the habitation fields, for a person to type in.

    Not proposals — `list_change_queue` never returns these, so nothing can decide one
    and nothing can carry one into an upload CSV. `product_model.findings` records the
    ruling behind that and which fields it covers.

    Two kinds of row, with different scopes:

    * **The floorplan**, for every product. One row per product rather than one per
      positional field: a reviewer opens the drawing once and reads the whole layout off
      it, and five rows pointing at the same image were five clicks for one glance.
    * **Everything the copy settles** — the fridge, the heating, the microwave, the beds,
      the washroom — for a **new** product only. A model FMLV already holds carries its
      own values across untouched, so there would be nothing to type.
    """
    recorded = 0
    floorplan_url = next(
        (
            provenance.source_url
            for name, provenance in extracted.provenance.items()
            if name in FINDING_FIELDS and provenance.reviewer_reference and provenance.source_url
        ),
        None,
    )
    if floorplan_url is not None:
        record_proposed_change(
            connection,
            run_id=run_id,
            product_id=product_id,
            field=FLOORPLAN_FIELD,
            old_value=None,
            new_value=None,
            source_url=floorplan_url,
            source_snippet=FLOORPLAN_SNIPPET,
            is_finding=True,
        )
        recorded += 1

    if not is_new:
        return recorded

    for name in FINDING_FIELDS:
        provenance = extracted.provenance.get(name)
        if provenance is None or provenance.reviewer_reference:
            # Nothing was read for this field, or all the adapter offered was the drawing
            # — which the one row above already hands over.
            continue
        value = _serialize(field_value(extracted.product, name))
        snippet = provenance.snippet
        if value is None and name in SILENCE_MEANS:
            # The adapter read the copy and the copy did not say. For the microwave that
            # is itself the answer; see `findings.SILENCE_MEANS`.
            value, note = SILENCE_MEANS[name]
            snippet = f"{snippet} {note}"
        record_proposed_change(
            connection,
            run_id=run_id,
            product_id=product_id,
            field=name,
            old_value=None,
            new_value=value,
            source_url=provenance.source_url,
            source_snippet=snippet,
            is_finding=True,
        )
        recorded += 1
    return recorded


def persist_diff(
    connection: sqlite3.Connection,
    *,
    run_id: int,
    manufacturer_id: int,
    diffs: list[ProductDiff],
    bump_year_all: bool = False,
    today: date | None = None,
    vehicle_class: VehicleClass = DEFAULT_VEHICLE_CLASS,
) -> PersistResult:
    """Persist one run's worth of `diff_products` output.

    Upserts the product identity mapping (`store.products.upsert_seen`) for every
    matched, new or disappeared product, then records `proposed_change`/`verification`
    rows. `DISAPPEARED` products get a `disappearance_notice` — see the module
    docstring — rather than being skipped.

    `bump_year_all` proposes a `year` bump for every existing product, not just the
    seasonally eligible ones — DESIGN.md §6.9 route 1, requested explicitly by a human
    when triggering the run. A genuinely new product is never given one: it has no
    baseline year to bump. Either route is capped by `year_rollover.can_bump_year`
    (`today`, injectable for tests, defaults to the real today).

    `vehicle_class` is carried into every `upsert_seen` so a product's identity is scoped
    to the FMLV export it came from. It does not affect the `proposed_change` rows
    themselves — those are keyed on the product, and `field` is free text, which is why
    the whole review and decision path needed no changes for caravans.
    """
    proposed = 0
    verified = 0
    suppressed = 0
    year_rollover_proposed = 0
    archive_proposed = 0
    missing_field_proposed = 0
    disappeared_noted = 0
    findings_recorded = 0

    for diff in diffs:
        if diff.kind == ChangeKind.DISAPPEARED:
            assert diff.baseline is not None
            product = products_store.upsert_seen(
                connection,
                manufacturer_id=manufacturer_id,
                fmlv_product_id=diff.fmlv_product_id,
                manufacturer_range=diff.baseline.manufacturer_range,
                model=diff.baseline.model,
                run_id=run_id,
                vehicle_class=vehicle_class,
            )
            record_disappearance_notice(
                connection, run_id=run_id, product_id=product.id, note=DISAPPEARANCE_NOTE
            )
            disappeared_noted += 1
            continue

        assert diff.extracted is not None
        product = products_store.upsert_seen(
            connection,
            manufacturer_id=manufacturer_id,
            fmlv_product_id=diff.fmlv_product_id,
            manufacturer_range=diff.extracted.product.manufacturer_range,
            model=diff.extracted.product.model,
            run_id=run_id,
            vehicle_class=vehicle_class,
        )

        findings_recorded += _record_findings(
            connection,
            run_id=run_id,
            product_id=product.id,
            extracted=diff.extracted,
            is_new=diff.kind == ChangeKind.NEW_PRODUCT,
        )

        if diff.kind == ChangeKind.NEW_PRODUCT:
            profile = profile_for(diff.extracted.product)
            for field_name, provenance in diff.extracted.provenance.items():
                if field_name in FINDING_FIELDS:
                    continue  # reported above, never proposed
                value = field_value(diff.extracted.product, field_name)
                if (
                    value is None
                    and field_name not in profile.in_scope
                    and not provenance.reviewer_reference
                ):
                    # Nothing to say. A *new* product has no stored figure to confirm or
                    # clear, and an out-of-scope field carries no obligation to fill one,
                    # so this would be a `None -> None` row a reviewer has to decide for
                    # no reason. Swift's caravans hit it: they record
                    # `optional_equipment_payload_kilograms` with no value, to ask for a
                    # stale split to be cleared, and on the two genuinely new caravans
                    # there was never a split.
                    #
                    # **In-scope fields are deliberately still proposed when empty.** That
                    # is `swift._body_type_basis`'s feature — an adapter that knows the
                    # family but not the subtype records provenance with no value so the
                    # reviewer is offered the choice, rather than the field going blank
                    # forever on a product with no baseline to preserve.
                    #
                    # So is a `reviewer_reference`, for the same reason from the other
                    # direction: the adapter cannot know the value and is not pretending
                    # to, but it can say *where to look*. Dropping those would leave a new
                    # product's floorplan-only fields with nothing to click.
                    continue
                record_proposed_change(
                    connection,
                    run_id=run_id,
                    product_id=product.id,
                    field=field_name,
                    old_value=None,
                    new_value=_serialize(value),
                    source_url=provenance.source_url,
                    source_snippet=provenance.snippet,
                    reviewer_reference=provenance.reviewer_reference,
                )
                proposed += 1

            # Anything a new product would otherwise reach FMLV blank on gets a row,
            # whether the adapter mentioned it or not — see `fields_needing_a_choice`.
            # Without this the only sign was a line in the issues file, after the upload
            # had been generated.
            for field_name in fields_needing_a_choice(diff.extracted.product):
                if field_name in diff.extracted.provenance:
                    continue
                # `bed_types` is the schema's one list, so "nothing recorded" is `[]` and
                # not `None` — and that is precisely the case to ask about, since an empty
                # list writes `No` across all seven bed-type columns and so asserts the
                # vehicle has no beds.
                value = field_value(diff.extracted.product, field_name)
                if value is not None and value != []:
                    continue
                record_proposed_change(
                    connection,
                    run_id=run_id,
                    product_id=product.id,
                    field=field_name,
                    old_value=None,
                    new_value=None,
                    source_url=None,
                    source_snippet=NEEDS_A_CHOICE_SNIPPET,
                    reviewer_reference=True,
                )
                proposed += 1
            continue

        for change in diff.changes:
            new_value = _serialize(change.new_value)
            if was_previously_rejected(
                connection, product_id=product.id, field=change.field, new_value=new_value
            ):
                suppressed += 1
                continue
            record_proposed_change(
                connection,
                run_id=run_id,
                product_id=product.id,
                field=change.field,
                old_value=_serialize(change.old_value),
                new_value=new_value,
                source_url=change.provenance.source_url if change.provenance else None,
                source_snippet=change.provenance.snippet if change.provenance else None,
                reviewer_reference=(
                    change.provenance.reviewer_reference if change.provenance else False
                ),
                confidence=diff.match_score,
            )
            proposed += 1

        if (
            (bump_year_all or diff.year_rollover_eligible)
            and diff.baseline is not None
            and diff.baseline.year is not None
            and not any(change.field == "year" for change in diff.changes)
            and can_bump_year(diff.baseline.year, today=today)
        ):
            new_value = _serialize(bump_year(diff.baseline).year)
            if was_previously_rejected(
                connection, product_id=product.id, field="year", new_value=new_value
            ):
                suppressed += 1
            else:
                record_proposed_change(
                    connection,
                    run_id=run_id,
                    product_id=product.id,
                    field="year",
                    old_value=_serialize(diff.baseline.year),
                    new_value=new_value,
                    source_url=None,
                    source_snippet=YEAR_ROLLOVER_SNIPPET,
                )
                proposed += 1
                year_rollover_proposed += 1

        # Payload is arithmetic, so a disagreement is checkable even when nothing was
        # read this run — see `_derived_payload_proposal`.
        derived_payloads_offered: set[str] = set()
        for payload_path, derived, held, explanation in _derived_payload_proposals(diff):
            new_value = _serialize(derived)
            if was_previously_rejected(
                connection,
                product_id=product.id,
                field=payload_path,
                new_value=new_value,
            ):
                suppressed += 1
                continue
            record_proposed_change(
                connection,
                run_id=run_id,
                product_id=product.id,
                field=payload_path,
                old_value=_serialize(held),
                new_value=new_value,
                source_url=None,
                source_snippet=explanation,
            )
            proposed += 1
            derived_payloads_offered.add(payload_path)

        for field_name in diff.confirmed_fields:
            record_verification(connection, run_id=run_id, product_id=product.id, field=field_name)
            verified += 1

        for missing in diff.missing_fields:
            if missing.field in derived_payloads_offered:
                # The derived proposal above already offers this field, with the
                # arithmetic behind it. A second row saying "confirm the existing figure"
                # would sit right beneath one saying the existing figure is wrong.
                continue
            # No `was_previously_rejected` gate here, unlike an ordinary proposal:
            # "reject" isn't a coherent action for a field that's simply missing —
            # the review UI only offers "keep existing" (accept) or "replace"
            # (correct) for these — so a still-missing field keeps being asked
            # about every run until a reviewer resolves it one way or the other.
            old_serialized = _serialize(missing.old_value)
            record_proposed_change(
                connection,
                run_id=run_id,
                product_id=product.id,
                field=missing.field,
                old_value=old_serialized,
                new_value=old_serialized,
                source_url=missing.provenance.source_url if missing.provenance else None,
                reviewer_reference=(
                    missing.provenance.reviewer_reference if missing.provenance else False
                ),
                source_snippet=_missing_field_snippet(missing),
            )
            proposed += 1
            missing_field_proposed += 1

    return PersistResult(
        proposed=proposed,
        verified=verified,
        suppressed_rejections=suppressed,
        year_rollover_proposed=year_rollover_proposed,
        archive_proposed=archive_proposed,
        missing_field_proposed=missing_field_proposed,
        disappeared_noted=disappeared_noted,
        findings_recorded=findings_recorded,
    )


def list_change_queue(connection: sqlite3.Connection, run_id: int) -> list[ChangeQueueEntry]:
    """Every proposed change for a run, with its product and latest decision (if any).

    Ordered by product identity then field, so a reviewer sees every proposal for one
    product together — matches DESIGN.md §6.3's "beside each change" framing.

    A change whose latest decision is "undo" comes back with `decision=None` — the
    undo row itself stays in the database for the audit trail, but as far as this
    queue is concerned the change is pending again.

    **Findings are excluded**, and this one `WHERE` clause is what makes them safe: a row
    that never reaches the queue can never be decided (`webapp` renders its forms from
    it) and can never reach an upload (`output.build.build_upload_products` reads it for
    every field it writes). See `product_model.findings`, and `findings_by_product` for
    reading them back.
    """
    rows = connection.execute(
        """
        SELECT
            proposed_change.*,
            product.manufacturer_id AS product_manufacturer_id,
            product.fmlv_product_id AS product_fmlv_product_id,
            product.manufacturer_range AS product_manufacturer_range,
            product.model AS product_model,
            product.first_seen_run_id AS product_first_seen_run_id,
            product.last_seen_run_id AS product_last_seen_run_id,
            decision.id AS decision_id,
            decision.action AS decision_action,
            decision.corrected_value AS decision_corrected_value,
            decision.decided_by AS decision_decided_by,
            decision.decided_at AS decision_decided_at
        FROM proposed_change
        JOIN product ON product.id = proposed_change.product_id
        LEFT JOIN decision ON decision.id = (
            SELECT id FROM decision AS latest
            WHERE latest.proposed_change_id = proposed_change.id
            ORDER BY latest.decided_at DESC, latest.id DESC
            LIMIT 1
        )
        WHERE proposed_change.run_id = ? AND proposed_change.is_finding = 0
        ORDER BY product.manufacturer_range, product.model, proposed_change.field
        """,
        (run_id,),
    ).fetchall()

    entries: list[ChangeQueueEntry] = []
    for row in rows:
        change = ProposedChange.from_row(row)
        product = Product(
            id=row["product_id"],
            manufacturer_id=row["product_manufacturer_id"],
            fmlv_product_id=row["product_fmlv_product_id"],
            manufacturer_range=row["product_manufacturer_range"],
            model=row["product_model"],
            first_seen_run_id=row["product_first_seen_run_id"],
            last_seen_run_id=row["product_last_seen_run_id"],
        )
        decision = None
        if row["decision_id"] is not None and row["decision_action"] != "undo":
            decision = Decision(
                id=row["decision_id"],
                proposed_change_id=change.id,
                action=row["decision_action"],
                corrected_value=row["decision_corrected_value"],
                decided_by=row["decision_decided_by"],
                decided_at=row["decision_decided_at"],
            )
        entries.append(ChangeQueueEntry(change=change, product=product, decision=decision))
    return entries


def findings_by_product(
    connection: sqlite3.Connection, run_id: int
) -> dict[int, list[ProposedChange]]:
    """One run's findings, keyed by product id and ordered as the review shows them.

    Read-only by construction: findings carry no decision to join against, the same way
    a disappearance notice does not. The order is `FINDING_FIELDS`' own — the floorplan
    first, then the beds and washroom, then the equipment — rather than alphabetical,
    because it is a list a person reads down while typing a row into FMLV.
    """
    order = {field: index for index, field in enumerate((FLOORPLAN_FIELD, *FINDING_FIELDS))}
    rows = connection.execute(
        "SELECT * FROM proposed_change WHERE run_id = ? AND is_finding = 1",
        (run_id,),
    ).fetchall()

    by_product: dict[int, list[ProposedChange]] = {}
    for row in rows:
        by_product.setdefault(row["product_id"], []).append(ProposedChange.from_row(row))
    for findings in by_product.values():
        findings.sort(key=lambda finding: (order.get(finding.field, len(order)), finding.field))
    return by_product


def list_disappearance_notices(
    connection: sqlite3.Connection, run_id: int
) -> list[DisappearanceNoticeEntry]:
    """Every disappearance notice for a run, with its product — for the review UI.

    Purely informational: unlike `list_change_queue`, there is no decision to join
    against, since a disappearance notice has nothing to accept, reject or correct.
    """
    rows = connection.execute(
        """
        SELECT
            disappearance_notice.*,
            product.manufacturer_id AS product_manufacturer_id,
            product.fmlv_product_id AS product_fmlv_product_id,
            product.manufacturer_range AS product_manufacturer_range,
            product.model AS product_model,
            product.first_seen_run_id AS product_first_seen_run_id,
            product.last_seen_run_id AS product_last_seen_run_id
        FROM disappearance_notice
        JOIN product ON product.id = disappearance_notice.product_id
        WHERE disappearance_notice.run_id = ?
        ORDER BY product.manufacturer_range, product.model
        """,
        (run_id,),
    ).fetchall()

    entries: list[DisappearanceNoticeEntry] = []
    for row in rows:
        notice = DisappearanceNotice.from_row(row)
        product = Product(
            id=row["product_id"],
            manufacturer_id=row["product_manufacturer_id"],
            fmlv_product_id=row["product_fmlv_product_id"],
            manufacturer_range=row["product_manufacturer_range"],
            model=row["product_model"],
            first_seen_run_id=row["product_first_seen_run_id"],
            last_seen_run_id=row["product_last_seen_run_id"],
        )
        entries.append(DisappearanceNoticeEntry(notice=notice, product=product))
    return entries
