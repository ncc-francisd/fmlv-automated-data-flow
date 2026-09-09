"""Findings: what the site said about the habitation fields, stated rather than proposed.

The requester's ruling, 9 September 2026, after the habitation group cost two reviewers
their answers: *"an additional line, not to accept or reject, but simply to state a
finding […] you could put the source, and it could take you to that copy, but we could
leave it to humans to add those elements to the CSV."* And, on scope: *"your findings
about those areas like heating, microwave and fridges only need to apply to what are
identified as new models. We will keep and retain the existing values for existing
models."*

`src/product_model/findings.py` carries the reasoning. What is tested here is that the
promise holds at both ends: a finding reaches the reviewer with its evidence, and it can
reach neither a decision nor an upload CSV.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src import store
from src.adapters.base import ExtractedMotorhome, Provenance
from src.diff.classify import diff_products
from src.product_model.enums import BathroomLayout, BedType, Heating, Refrigeration
from src.product_model.findings import FLOORPLAN_FIELD
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
        connection, manufacturer_id=75, fmlv_manufacturer="Rimor", trigger="manual"
    ).id


PRODUCT = {
    "manufacturer": "Rimor",
    "manufacturer_range": "Kilig",
    "model": "66 Plus",
}


def a_scan_that_found_things(**overrides: object) -> ExtractedMotorhome:
    """One product whose copy settles the fridge, the heating and the beds."""
    fields: dict[str, object] = {
        **PRODUCT,
        "rrp_pounds": 61995,
        "refrigeration": Refrigeration.FRIDGE_FREEZER,
        "heating": Heating.BLOWN_AIR,
        "bed_types": [BedType.FIXED, BedType.DROP_DOWN],
        "bathroom_layout": [],
    }
    fields.update(overrides)
    return ExtractedMotorhome(
        motorhome=Motorhome(**fields),
        provenance={
            "rrp_pounds": Provenance("https://mnc.test/kilig-66", "£61,995"),
            "refrigeration": Provenance(
                "https://mnc.test/kilig-66", "141L fridge with freezer compartment"
            ),
            "heating": Provenance(
                "https://mnc.test/kilig-66", "Truma Combi 4 blown air heating"
            ),
            "bed_types": Provenance(
                "https://mnc.test/kilig-66",
                "Rear fixed double bed / Electric drop-down double bed",
            ),
            "bathroom_layout": Provenance(
                "https://www.rimor.it/plan.png",
                "read the washroom off the floorplan",
                reviewer_reference=True,
            ),
        },
    )


def findings_for_one_product(
    connection: sqlite3.Connection, run_id: int
) -> dict[str, store.ProposedChange]:
    by_product = store.findings_by_product(connection, run_id)
    assert len(by_product) <= 1, "these tests persist one product"
    findings = next(iter(by_product.values()), [])
    return {finding.field: finding for finding in findings}


# --------------------------------------------------------------------------- #
# A new product: everything the copy settled, with its evidence
# --------------------------------------------------------------------------- #


def test_a_new_products_habitation_readings_are_recorded_as_findings(
    connection: sqlite3.Connection, run_id: int
) -> None:
    """The value and the manufacturer's own line, for a person to type into FMLV."""
    store.persist_diff(
        connection,
        run_id=run_id,
        manufacturer_id=75,
        diffs=diff_products([a_scan_that_found_things()], []),
    )

    findings = findings_for_one_product(connection, run_id)

    assert findings["refrigeration"].new_value == "fridge_freezer"
    assert "freezer compartment" in findings["refrigeration"].source_snippet
    assert findings["refrigeration"].source_url == "https://mnc.test/kilig-66"
    assert findings["heating"].new_value == "blown_air_heating"
    assert findings["bed_types"].new_value == "fixed_bed, drop_down_bed"
    assert all(finding.is_finding for finding in findings.values())


def test_a_finding_is_kept_out_of_the_reviewers_queue(
    connection: sqlite3.Connection, run_id: int
) -> None:
    """The one guard that makes the rest safe.

    `list_change_queue` is what the review renders its forms from *and* what
    `output.build.build_upload_products` reads for every field it writes, so a row it
    never returns can neither be decided nor reach FMLV.
    """
    store.persist_diff(
        connection,
        run_id=run_id,
        manufacturer_id=75,
        diffs=diff_products([a_scan_that_found_things()], []),
    )

    queued = {entry.change.field for entry in store.list_change_queue(connection, run_id)}

    assert "rrp_pounds" in queued  # an ordinary proposal is untouched
    assert not {"refrigeration", "heating", "bed_types", "bathroom_layout"} & queued
    assert FLOORPLAN_FIELD not in queued


def test_findings_are_counted_apart_from_proposals(
    connection: sqlite3.Connection, run_id: int
) -> None:
    """A run's completion message says how much work is waiting; a finding is none."""
    result = store.persist_diff(
        connection,
        run_id=run_id,
        manufacturer_id=75,
        diffs=diff_products([a_scan_that_found_things()], []),
    )

    # The floorplan, plus the three the copy settled.
    assert result.findings_recorded == 4


def test_the_findings_read_in_the_order_a_person_works_down_them(
    connection: sqlite3.Connection, run_id: int
) -> None:
    """The drawing first, then the beds and washroom, then the equipment — not A to Z."""
    store.persist_diff(
        connection,
        run_id=run_id,
        manufacturer_id=75,
        diffs=diff_products([a_scan_that_found_things()], []),
    )

    fields = [finding.field for finding in findings_for_one_product(connection, run_id).values()]

    assert fields[0] == FLOORPLAN_FIELD
    assert fields.index("bed_types") < fields.index("heating")


# --------------------------------------------------------------------------- #
# The microwave, where silence is itself the answer
# --------------------------------------------------------------------------- #


def test_a_microwave_nobody_mentions_is_reported_as_no(
    connection: sqlite3.Connection, run_id: int
) -> None:
    """The requester, 9 September 2026: *"it should probably just recommend no, and say we
    couldn't find any evidence or mention of a microwave, and I would just default to
    accepting a no."*

    Safe as a finding in a way it would not be as a proposal: nothing is written, and the
    snippet says the recommendation rests on silence.
    """
    scan = a_scan_that_found_things()
    scan.provenance["microwave"] = Provenance(
        "https://mnc.test/kilig-66", "The specification lists no microwave."
    )
    store.persist_diff(
        connection, run_id=run_id, manufacturer_id=75, diffs=diff_products([scan], [])
    )

    microwave = findings_for_one_product(connection, run_id)["microwave"]

    assert microwave.new_value == "False"
    assert "no mention of a microwave" in microwave.source_snippet.lower()


def test_a_microwave_the_copy_states_is_reported_as_found(
    connection: sqlite3.Connection, run_id: int
) -> None:
    """The default only fills a silence — a stated microwave is reported as stated."""
    scan = a_scan_that_found_things(microwave=True)
    scan.provenance["microwave"] = Provenance(
        "https://mnc.test/kilig-66", "Microwave oven fitted as standard"
    )
    store.persist_diff(
        connection, run_id=run_id, manufacturer_id=75, diffs=diff_products([scan], [])
    )

    microwave = findings_for_one_product(connection, run_id)["microwave"]

    assert microwave.new_value == "True"
    assert microwave.source_snippet == "Microwave oven fitted as standard"


# --------------------------------------------------------------------------- #
# A matched product keeps what FMLV holds
# --------------------------------------------------------------------------- #


def test_a_matched_product_gets_the_floorplan_but_no_habitation_findings(
    connection: sqlite3.Connection, run_id: int
) -> None:
    """Nothing for a person to type in: FMLV's own values carry across untouched.

    The drawing is still offered, because a reviewer working any product may want to see
    the layout — it is the *statements* that are new-product-only.
    """
    baseline = Motorhome(**PRODUCT, product_id=7940, rrp_pounds=59995)
    store.persist_diff(
        connection,
        run_id=run_id,
        manufacturer_id=75,
        diffs=diff_products([a_scan_that_found_things()], [baseline]),
    )

    findings = findings_for_one_product(connection, run_id)

    assert set(findings) == {FLOORPLAN_FIELD}
    assert findings[FLOORPLAN_FIELD].source_url == "https://www.rimor.it/plan.png"
    assert "which end the beds are at" in findings[FLOORPLAN_FIELD].source_snippet


def test_a_matched_products_habitation_values_are_never_touched(
    connection: sqlite3.Connection, run_id: int
) -> None:
    """The Eriba Touring 430 and Dethleffs Alpa A 6820-2 losses, made impossible.

    The site says one thing, FMLV holds another, and there is no row either way — so no
    Accept can wipe a washroom location and no reviewer is asked to arbitrate.
    """
    baseline = Motorhome(
        **PRODUCT,
        product_id=7940,
        rrp_pounds=61995,
        refrigeration=Refrigeration.FRIDGE,
        heating=Heating.WET_CENTRAL,
        bed_types=[BedType.FIXED_SEPARATE],
        bathroom_layout=[BathroomLayout.SIDE_SHOWER_TOILET],
    )
    store.persist_diff(
        connection,
        run_id=run_id,
        manufacturer_id=75,
        diffs=diff_products([a_scan_that_found_things()], [baseline]),
    )

    queued = {entry.change.field for entry in store.list_change_queue(connection, run_id)}
    verified = store.verified_fields_by_product(connection, run_id)

    assert not {"refrigeration", "heating", "bed_types", "bathroom_layout"} & queued
    # Nor claimed as checked-and-unchanged, which they are not.
    assert all(
        "refrigeration" not in fields and "bed_types" not in fields
        for fields in verified.values()
    )
