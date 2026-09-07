"""Tests for persisting a run's diff into `proposed_change`/`verification` rows."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import pytest

from src import store
from src.adapters.base import ExtractedMotorhome, Provenance
from src.diff.classify import diff_products
from src.product_model.model import Motorhome


@pytest.fixture
def connection(tmp_path: Path) -> sqlite3.Connection:
    conn = store.connect(tmp_path / "runs.db")
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def run_id(connection: sqlite3.Connection) -> int:
    return store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    ).id


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
                source_url="https://www.adria.co.uk/motorhomes/matrix", snippet="£93,920"
            )
        },
    )


def test_changed_field_is_persisted_as_a_proposed_change(
    connection: sqlite3.Connection, run_id: int
) -> None:
    baseline = make_baseline()
    extracted = make_extracted(rrp_pounds=93920)
    diffs = diff_products([extracted], [baseline])

    result = store.persist_diff(
        connection, run_id=run_id, manufacturer_id=3, diffs=diffs
    )

    assert result.proposed == 1
    assert result.verified == 0
    queue = store.list_change_queue(connection, run_id)
    assert len(queue) == 1
    entry = queue[0]
    assert entry.change.field == "rrp_pounds"
    assert entry.change.old_value == "93950"
    assert entry.change.new_value == "93920"
    assert entry.change.source_url == "https://www.adria.co.uk/motorhomes/matrix"
    assert entry.product.fmlv_product_id == 4147
    assert entry.decision is None


def test_missing_in_scope_field_is_persisted_as_a_confirm_or_replace_proposal(
    connection: sqlite3.Connection, run_id: int
) -> None:
    # mro_kilograms is in_scope (schema.IN_SCOPE) and has a baseline figure, but
    # this run's adapter never found it — must be surfaced for review, not skipped.
    baseline = make_baseline(rrp_pounds=93920, mro_kilograms=2944)
    extracted = make_extracted(rrp_pounds=93920)
    diffs = diff_products([extracted], [baseline])

    result = store.persist_diff(connection, run_id=run_id, manufacturer_id=3, diffs=diffs)

    assert result.proposed == 1
    assert result.missing_field_proposed == 1
    queue = store.list_change_queue(connection, run_id)
    assert len(queue) == 1
    entry = queue[0]
    assert entry.change.field == "mro_kilograms"
    assert entry.change.old_value == "2944"
    assert entry.change.new_value == "2944"
    assert entry.change.source_snippet == store.MISSING_FIELD_SNIPPET
    assert entry.change.source_url is None


def test_unchanged_confirmed_is_persisted_as_a_verification_not_a_change(
    connection: sqlite3.Connection, run_id: int
) -> None:
    baseline = make_baseline(rrp_pounds=93920)
    extracted = make_extracted(rrp_pounds=93920)
    diffs = diff_products([extracted], [baseline])

    result = store.persist_diff(
        connection, run_id=run_id, manufacturer_id=3, diffs=diffs
    )

    assert result.proposed == 0
    assert result.verified == 1
    assert store.list_change_queue(connection, run_id) == []


def test_new_product_persists_every_extracted_field_with_no_old_value(
    connection: sqlite3.Connection, run_id: int
) -> None:
    extracted = make_extracted(
        rrp_pounds=45000, manufacturer_range="Sonic", model="Axess 600 SL"
    )
    diffs = diff_products([extracted], [])

    result = store.persist_diff(
        connection, run_id=run_id, manufacturer_id=3, diffs=diffs
    )

    # The extracted field, plus one row per single-select layout group the product has no
    # value for — a new product needs a choice from each, and without a row the reviewer
    # never sees it. See `LAYOUT_GROUP_UNSET_SNIPPET`.
    unset_count = sum(
        1
        for f in store.changes.fields_needing_a_choice(extracted.product)
        if f not in extracted.provenance
        and getattr(extracted.product, f, None) is None
    )
    assert result.proposed == 1 + unset_count
    queue = store.list_change_queue(connection, run_id)
    rrp = next(e for e in queue if e.change.field == "rrp_pounds")
    assert rrp.change.old_value is None
    assert rrp.change.new_value == "45000"
    assert rrp.product.fmlv_product_id is None

    unset = {e.change.field for e in queue if e.change.reviewer_reference}
    assert "mro_kilograms" in unset
    assert "sleeping_area" in unset
    assert all(
        e.change.new_value is None for e in queue if e.change.reviewer_reference
    )


def test_disappeared_product_gets_a_disappearance_notice_not_a_proposed_change(
    connection: sqlite3.Connection, run_id: int
) -> None:
    baseline = make_baseline()
    diffs = diff_products([], [baseline])

    result = store.persist_diff(
        connection, run_id=run_id, manufacturer_id=3, diffs=diffs
    )

    assert result.proposed == 0
    assert result.disappeared_noted == 1
    assert result.verified == 0
    assert store.list_change_queue(connection, run_id) == []
    [entry] = store.list_disappearance_notices(connection, run_id)
    assert entry.product.fmlv_product_id == 4147
    assert "not found" in entry.notice.note.lower()


def test_disappearance_notice_is_recorded_again_every_run_it_recurs(
    connection: sqlite3.Connection, run_id: int
) -> None:
    """Unlike a proposed change, there's no accept/reject to remember — a still-missing
    product gets a fresh notice on the run detail page each run it stays missing."""
    baseline = make_baseline()
    first_diffs = diff_products([], [baseline])
    store.persist_diff(connection, run_id=run_id, manufacturer_id=3, diffs=first_diffs)

    second_run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    second_diffs = diff_products([], [baseline])
    result = store.persist_diff(
        connection, run_id=second_run.id, manufacturer_id=3, diffs=second_diffs
    )

    assert result.disappeared_noted == 1
    assert len(store.list_disappearance_notices(connection, second_run.id)) == 1


def test_rejected_change_is_not_re_proposed_next_run(
    connection: sqlite3.Connection, run_id: int
) -> None:
    baseline = make_baseline()
    extracted = make_extracted(rrp_pounds=93920)
    first_diffs = diff_products([extracted], [baseline])
    store.persist_diff(connection, run_id=run_id, manufacturer_id=3, diffs=first_diffs)

    [entry] = store.list_change_queue(connection, run_id)
    store.record_decision(
        connection, proposed_change_id=entry.change.id, action="reject", decided_by="ben"
    )

    second_run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    # Same baseline, same scraped value again — the manufacturer's site hasn't changed.
    second_diffs = diff_products([extracted], [baseline])
    result = store.persist_diff(
        connection, run_id=second_run.id, manufacturer_id=3, diffs=second_diffs
    )

    assert result.proposed == 0
    assert result.suppressed_rejections == 1
    assert store.list_change_queue(connection, second_run.id) == []


def test_a_different_new_value_is_still_proposed_after_a_rejection(
    connection: sqlite3.Connection, run_id: int
) -> None:
    baseline = make_baseline()
    first_extracted = make_extracted(rrp_pounds=93920)
    first_diffs = diff_products([first_extracted], [baseline])
    store.persist_diff(connection, run_id=run_id, manufacturer_id=3, diffs=first_diffs)

    [entry] = store.list_change_queue(connection, run_id)
    store.record_decision(
        connection, proposed_change_id=entry.change.id, action="reject", decided_by="ben"
    )

    second_run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    # The manufacturer corrected their site to a different figure — must still surface.
    second_extracted = make_extracted(rrp_pounds=94500)
    second_diffs = diff_products([second_extracted], [baseline])
    result = store.persist_diff(
        connection, run_id=second_run.id, manufacturer_id=3, diffs=second_diffs
    )

    assert result.proposed == 1
    assert result.suppressed_rejections == 0


def test_year_rollover_eligible_product_gets_a_year_proposed_change(
    connection: sqlite3.Connection, run_id: int
) -> None:
    baseline = make_baseline(year=2026)
    extracted = make_extracted(rrp_pounds=93920)
    diffs = diff_products([extracted], [baseline], today=date(2026, 7, 15))
    assert diffs[0].year_rollover_eligible is True

    result = store.persist_diff(connection, run_id=run_id, manufacturer_id=3, diffs=diffs)

    assert result.year_rollover_proposed == 1
    queue = store.list_change_queue(connection, run_id)
    year_change = next(entry for entry in queue if entry.change.field == "year")
    assert year_change.change.old_value == "2026"
    assert year_change.change.new_value == "2027"
    assert year_change.change.source_url is None
    assert year_change.change.source_snippet is not None


def test_year_rollover_not_proposed_outside_the_window(
    connection: sqlite3.Connection, run_id: int
) -> None:
    baseline = make_baseline(year=2026)
    extracted = make_extracted(rrp_pounds=93920)
    diffs = diff_products([extracted], [baseline], today=date(2026, 1, 15))

    result = store.persist_diff(connection, run_id=run_id, manufacturer_id=3, diffs=diffs)

    assert result.year_rollover_proposed == 0
    queue = store.list_change_queue(connection, run_id)
    assert not any(entry.change.field == "year" for entry in queue)


def test_year_rollover_not_proposed_when_baseline_is_already_at_the_cap(
    connection: sqlite3.Connection, run_id: int
) -> None:
    # Already one year ahead of "today" — bumping again would overshoot the cap.
    baseline = make_baseline(year=2027)
    extracted = make_extracted(rrp_pounds=93920)
    diffs = diff_products([extracted], [baseline], today=date(2026, 7, 15))

    result = store.persist_diff(
        connection, run_id=run_id, manufacturer_id=3, diffs=diffs, today=date(2026, 7, 15)
    )

    assert result.year_rollover_proposed == 0
    queue = store.list_change_queue(connection, run_id)
    assert not any(entry.change.field == "year" for entry in queue)


def test_year_rollover_not_proposed_when_baseline_year_is_stale(
    connection: sqlite3.Connection, run_id: int
) -> None:
    # Baseline is two years behind "today" — not a plausible rollover, just stale data.
    baseline = make_baseline(year=2024)
    extracted = make_extracted(rrp_pounds=93920)
    diffs = diff_products([extracted], [baseline], today=date(2026, 7, 15))

    result = store.persist_diff(
        connection, run_id=run_id, manufacturer_id=3, diffs=diffs, today=date(2026, 7, 15)
    )

    assert result.year_rollover_proposed == 0
    queue = store.list_change_queue(connection, run_id)
    assert not any(entry.change.field == "year" for entry in queue)


def test_bump_year_all_also_respects_the_cap(
    connection: sqlite3.Connection, run_id: int
) -> None:
    baseline = make_baseline(year=2027)
    extracted = make_extracted(rrp_pounds=93950)  # identical to baseline, no other change
    diffs = diff_products([extracted], [baseline], today=date(2026, 1, 15))

    result = store.persist_diff(
        connection,
        run_id=run_id,
        manufacturer_id=3,
        diffs=diffs,
        bump_year_all=True,
        today=date(2026, 1, 15),
    )

    assert result.year_rollover_proposed == 0
    assert result.proposed == 0


def test_rejected_year_rollover_is_not_re_proposed(
    connection: sqlite3.Connection, run_id: int
) -> None:
    baseline = make_baseline(year=2026)
    extracted = make_extracted(rrp_pounds=93920)
    diffs = diff_products([extracted], [baseline], today=date(2026, 7, 15))
    store.persist_diff(connection, run_id=run_id, manufacturer_id=3, diffs=diffs)

    queue = store.list_change_queue(connection, run_id)
    year_change = next(entry for entry in queue if entry.change.field == "year")
    store.record_decision(
        connection, proposed_change_id=year_change.change.id, action="reject", decided_by="ben"
    )

    second_run = store.start_run(
        connection, manufacturer_id=3, fmlv_manufacturer="Adria Mobil", trigger="manual"
    )
    second_diffs = diff_products([extracted], [baseline], today=date(2026, 8, 1))
    result = store.persist_diff(
        connection, run_id=second_run.id, manufacturer_id=3, diffs=second_diffs
    )

    assert result.year_rollover_proposed == 0
    assert result.suppressed_rejections == 1


def test_change_queue_reflects_a_decision_once_made(
    connection: sqlite3.Connection, run_id: int
) -> None:
    baseline = make_baseline()
    extracted = make_extracted(rrp_pounds=93920)
    diffs = diff_products([extracted], [baseline])
    store.persist_diff(connection, run_id=run_id, manufacturer_id=3, diffs=diffs)

    [entry] = store.list_change_queue(connection, run_id)
    store.record_decision(
        connection, proposed_change_id=entry.change.id, action="accept", decided_by="ben"
    )

    [updated] = store.list_change_queue(connection, run_id)
    assert updated.decision is not None
    assert updated.decision.action == "accept"


def test_run_review_summary_before_anything_is_decided(
    connection: sqlite3.Connection, run_id: int
) -> None:
    baseline = make_baseline()
    extracted = make_extracted(rrp_pounds=93920)
    diffs = diff_products([extracted], [baseline])
    store.persist_diff(connection, run_id=run_id, manufacturer_id=3, diffs=diffs)

    summary = store.run_review_summary(connection, run_id)

    assert summary.pending_count == 1
    assert summary.primary_reviewer is None


def test_run_review_summary_counts_pending_and_finds_the_busiest_reviewer(
    connection: sqlite3.Connection, run_id: int
) -> None:
    first_baseline = make_baseline(product_id=4147, model="Supreme 670 DC")
    second_baseline = make_baseline(product_id=8195, model="670 SL 60Y")
    first_extracted = make_extracted(rrp_pounds=93920, model="Supreme 670 DC")
    second_extracted = make_extracted(rrp_pounds=81000, model="670 SL 60Y")
    diffs = diff_products(
        [first_extracted, second_extracted], [first_baseline, second_baseline]
    )
    store.persist_diff(connection, run_id=run_id, manufacturer_id=3, diffs=diffs)

    [first_entry, second_entry] = store.list_change_queue(connection, run_id)
    store.record_decision(
        connection, proposed_change_id=first_entry.change.id, action="accept", decided_by="ben"
    )
    store.record_decision(
        connection, proposed_change_id=second_entry.change.id, action="accept", decided_by="ben"
    )

    summary = store.run_review_summary(connection, run_id)

    assert summary.pending_count == 0
    assert summary.primary_reviewer == "ben"


def test_an_in_scope_gap_is_described_as_one_the_adapter_was_required_to_fill(
    connection: sqlite3.Connection, run_id: int
) -> None:
    """The wording depends on `MissingField.in_scope`, not on the motorhome schema.

    Until 4 September 2026 `_missing_field_snippet` tested every field against
    `schema.IN_SCOPE` — the *motorhome* set. Caravans name their fields differently
    (`height_mm`, not `mh_height_mm`), so every one of a caravan run's in-scope gaps fell
    through to the out-of-scope wording and told the reviewer the adapter "could not
    determine" a field it was in fact required to find. 72 rows on Swift's first run.
    """
    from src.diff.compare import MissingField

    in_scope = MissingField(field="height_mm", old_value=2590, in_scope=True)
    out_of_scope = MissingField(
        field="optional_equipment_payload_kilograms", old_value=41, in_scope=False
    )

    assert store.changes._missing_field_snippet(in_scope) == store.MISSING_FIELD_SNIPPET
    assert (
        store.changes._missing_field_snippet(out_of_scope) == store.UNDETERMINED_FIELD_SNIPPET
    )


def test_a_caravan_in_scope_gap_gets_the_in_scope_wording(
    connection: sqlite3.Connection,
) -> None:
    """End to end, through the diff, on the fields that were actually mis-described."""
    from src.adapters.base import ExtractedCaravan, Provenance
    from src.diff.classify import diff_products
    from src.product_model.caravan import Caravan
    from src.vehicle_class import VehicleClass

    baseline = Caravan(
        product_id=9001,
        manufacturer="Swift Group Ltd",
        manufacturer_display_name="Swift",
        manufacturer_range="Sprite",
        model="Alpine 4",
        height_mm=2590,
        mtplm_kilograms=1247,
    )
    scraped = ExtractedCaravan(
        caravan=baseline.model_copy(update={"height_mm": None, "product_id": None}),
        provenance={"mtplm_kilograms": Provenance(source_url="https://x.test", snippet="1247kg")},
    )
    run = store.start_run(
        connection,
        manufacturer_id=26,
        fmlv_manufacturer="Swift Group Ltd",
        trigger="manual",
        vehicle_class=VehicleClass.CARAVAN,
    )
    diffs = diff_products([scraped], [baseline])
    store.persist_diff(connection, run_id=run.id, manufacturer_id=26, diffs=diffs)

    row = next(
        e for e in store.list_change_queue(connection, run.id) if e.change.field == "height_mm"
    )

    assert row.change.source_snippet is not None
    assert row.change.source_snippet.startswith(store.MISSING_FIELD_SNIPPET)


def test_a_new_product_is_not_asked_about_an_empty_out_of_scope_field(
    connection: sqlite3.Connection,
) -> None:
    """A `None -> None` row on a brand-new product is a decision for no reason.

    Swift's caravans record `optional_equipment_payload_kilograms` with no value, to ask
    for a stale split to be cleared where FMLV holds one. On the two genuinely new
    caravans there was never a split, so the row said nothing and still had to be decided.
    """
    from src.adapters.base import ExtractedCaravan, Provenance
    from src.diff.classify import diff_products
    from src.product_model.caravan import Caravan
    from src.vehicle_class import VehicleClass

    scraped = ExtractedCaravan(
        caravan=Caravan(
            manufacturer="Swift Group Ltd",
            manufacturer_display_name="Swift",
            manufacturer_range="Conqueror",
            model="565",
            mtplm_kilograms=1700,
        ),
        provenance={
            "mtplm_kilograms": Provenance(source_url="https://x.test", snippet="1700kg"),
            "optional_equipment_payload_kilograms": Provenance(
                source_url="https://x.test", snippet="Swift publish no split"
            ),
        },
    )
    run = store.start_run(
        connection,
        manufacturer_id=26,
        fmlv_manufacturer="Swift Group Ltd",
        trigger="manual",
        vehicle_class=VehicleClass.CARAVAN,
    )
    store.persist_diff(
        connection, run_id=run.id, manufacturer_id=26, diffs=diff_products([scraped], [])
    )

    fields = {e.change.field for e in store.list_change_queue(connection, run.id)}

    assert "mtplm_kilograms" in fields
    assert "optional_equipment_payload_kilograms" not in fields


def test_a_new_product_is_still_asked_about_an_empty_in_scope_field(
    connection: sqlite3.Connection,
) -> None:
    """The other side of that rule, and the reason it is scoped rather than blanket.

    `swift._body_type_basis` records provenance with *no value* on purpose: the adapter
    knows the family but not the subtype, so the reviewer is offered the choice. A new
    product has no baseline to preserve, so suppressing this would leave the field blank
    forever.
    """
    from src.adapters.base import ExtractedCaravan, Provenance
    from src.diff.classify import diff_products
    from src.product_model.caravan import Caravan
    from src.vehicle_class import VehicleClass

    scraped = ExtractedCaravan(
        caravan=Caravan(
            manufacturer="Swift Group Ltd",
            manufacturer_display_name="Swift",
            manufacturer_range="Conqueror",
            model="565",
            body_type=None,
        ),
        provenance={
            "body_type": Provenance(
                source_url="https://x.test", snippet="a touring caravan, subtype unstated"
            )
        },
    )
    run = store.start_run(
        connection,
        manufacturer_id=26,
        fmlv_manufacturer="Swift Group Ltd",
        trigger="manual",
        vehicle_class=VehicleClass.CARAVAN,
    )
    store.persist_diff(
        connection, run_id=run.id, manufacturer_id=26, diffs=diff_products([scraped], [])
    )

    queue = store.list_change_queue(connection, run.id)
    entry = next(e for e in queue if e.change.field == "body_type")

    assert entry.change.new_value is None
    # The adapter's own row, carrying the evidence it did find — not one of the
    # "nothing here at all" rows a new product also gets for its blank columns.
    assert entry.change.source_snippet is not None
    assert "subtype unstated" in entry.change.source_snippet


def test_a_new_product_is_asked_about_every_column_it_has_nothing_for(
    connection: sqlite3.Connection, run_id: int
) -> None:
    """The Rimor Van 238, which shipped blank in run 87 with no row to warn anyone.

    It has no factory page, so the adapter found no weights and nothing positional — not
    even a floorplan to point at. Before this the only sign was `required field
    'mro_kilograms' is missing` in the issues file, after the upload was generated.
    """
    scraped = ExtractedMotorhome(
        motorhome=Motorhome(
            manufacturer="Rimor",
            manufacturer_range="Horus",
            model="Van 238",
            rrp_pounds=56995,
            mh_length_mm=5980,
        ),
        provenance={
            "rrp_pounds": Provenance(source_url="https://mnc.test/x", snippet="£56,995"),
            "mh_length_mm": Provenance(source_url="https://mnc.test/x", snippet="Length: 5.98m"),
        },
    )
    store.persist_diff(
        connection, run_id=run_id, manufacturer_id=75, diffs=diff_products([scraped], [])
    )

    rows = {e.change.field: e.change for e in store.list_change_queue(connection, run_id)}

    # The weights it could not find, each needing a figure typed in.
    for field_name in ("mro_kilograms", "mtplm_kilograms", "mh_payload_kilograms"):
        assert field_name in rows, field_name
        assert rows[field_name].new_value is None
        assert rows[field_name].reviewer_reference is True

    # And the positional groups, which no wording could ever settle.
    for field_name in ("sleeping_area", "kitchen_location", "lounge_location"):
        assert field_name in rows, field_name
        assert rows[field_name].new_value is None

    # What it did find is a normal proposal, not one of these.
    assert rows["rrp_pounds"].new_value == "56995"
    assert rows["rrp_pounds"].reviewer_reference is False
    # And nothing is invented for a column it already has.
    assert rows["mh_length_mm"].new_value == "5980"


def test_an_existing_product_is_not_asked_about_columns_it_already_holds(
    connection: sqlite3.Connection, run_id: int
) -> None:
    """Only new products get these rows: a matched one has a baseline value to keep."""
    baseline = make_baseline()
    scraped = make_extracted(rrp_pounds=93920)
    store.persist_diff(
        connection, run_id=run_id, manufacturer_id=3, diffs=diff_products([scraped], [baseline])
    )

    fields = [e.change.field for e in store.list_change_queue(connection, run_id)]
    assert fields == ["rrp_pounds"]
