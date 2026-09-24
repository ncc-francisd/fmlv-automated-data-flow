"""One layout on two chassis is two vehicles, end to end.

The requester settled this on 23 September 2026 — *"if the base vehicle is different then
it's a different vehicle"* — after Carthago turned out to hold 22 such pairs in 53 live
rows, and after Frankia was found to have been quietly dropping one of `Noctra /
Cruiser 7.6 L` on every run since its adapter shipped.

Three things had to change together and each is covered here: the baseline dedupe must
stop collapsing the pair, the matcher must send each scraped product to the row on its own
chassis, and the store must keep them as two rows with two histories.
"""

from __future__ import annotations

import sqlite3

import pytest

from src import store
from src.adapters.base import ExtractedMotorhome
from src.cli import _dedupe_baseline
from src.diff.matching import match_products
from src.product_model.model import Motorhome
from src.store import products as products_store


def _motorhome(
    model: str, base: str | None, *, product_id: int | None = None, **fields
) -> Motorhome:
    return Motorhome(
        manufacturer="Frankia",
        manufacturer_range="Noctra",
        model=model,
        base_vehicle_manufacturer=base,
        product_id=product_id,
        year=2027,
        **fields,
    )


# --- the baseline dedupe --------------------------------------------------------------


def test_the_frankia_pair_both_survive_the_baseline() -> None:
    """8888 Mercedes and 8889 Fiat, both live, both named `Noctra / Cruiser 7.6 L`. One of
    them was being discarded before matching started — with no disappearance notice,
    because a discarded row never reaches the diff."""
    baseline = [
        _motorhome("Cruiser 7.6 L", "Mercedes", product_id=8888, mro_kilograms=3788),
        _motorhome("Cruiser 7.6 L", "Fiat", product_id=8889, mro_kilograms=3837),
    ]
    discarded: list[Motorhome] = []

    kept = _dedupe_baseline(baseline, on_discard=lambda _k, d: discarded.append(d))

    assert len(kept) == 2
    assert discarded == []


def test_a_genuine_duplicate_is_still_collapsed() -> None:
    """The dedupe's original job, unchanged: Swift's export really did hold one name
    twice on one chassis, and the newer row is the one an update belongs on."""
    baseline = [
        _motorhome("Cruiser 7.6 L", "Fiat", product_id=1),
        _motorhome("Cruiser 7.6 L", "Fiat", product_id=2),
    ]
    discarded: list[Motorhome] = []

    kept = _dedupe_baseline(baseline, on_discard=lambda _k, d: discarded.append(d))

    assert len(kept) == 1
    assert len(discarded) == 1


def test_two_chassis_less_products_still_collapse() -> None:
    """A manufacturer that publishes no chassis is exactly as it was before."""
    baseline = [
        _motorhome("Cruiser 7.6 L", None, product_id=1),
        _motorhome("Cruiser 7.6 L", None, product_id=2),
    ]

    assert len(_dedupe_baseline(baseline)) == 1


# --- the matcher ----------------------------------------------------------------------


def _extracted(model: str, base: str | None) -> ExtractedMotorhome:
    return ExtractedMotorhome(motorhome=_motorhome(model, base))


def test_each_scraped_product_claims_the_row_on_its_own_chassis() -> None:
    """**The failure this prevents is worse than a missed match.** Both pairs score 1.0 on
    name, so a greedy assignment pairs them in list order — and the first Carthago run
    would have written the Fiat's masses and price onto the Mercedes row."""
    scraped = [
        _extracted("Cruiser 7.6 L", "Fiat"),
        _extracted("Cruiser 7.6 L", "Mercedes"),
    ]
    baseline = [
        _motorhome("Cruiser 7.6 L", "Mercedes", product_id=8888),
        _motorhome("Cruiser 7.6 L", "Fiat", product_id=8889),
    ]

    results = match_products(scraped, baseline)

    by_chassis = {
        r.extracted.product.base_vehicle_manufacturer: r.baseline.product_id
        for r in results
        if r.baseline is not None
    }
    assert by_chassis == {"Fiat": 8889, "Mercedes": 8888}


def test_a_product_with_no_chassis_still_matches_one_that_has_one() -> None:
    """Unknown ranks as agreement, so this never demotes a manufacturer that publishes no
    chassis, nor a caravan, which has none."""
    results = match_products(
        [_extracted("Cruiser 7.6 L", None)],
        [_motorhome("Cruiser 7.6 L", "Fiat", product_id=8889)],
    )

    assert results[0].baseline is not None
    assert results[0].score == 1.0


def test_the_chassis_never_moves_a_score() -> None:
    """It sorts candidates that already tie; it is not folded into the similarity. Folding
    it in would push short names under the threshold — a one-token bag like
    `Pulsar / Pulsar` goes from 1.0 to 0.5 on one unmatched chassis token."""
    same = match_products(
        [_extracted("Cruiser 7.6 L", "Fiat")],
        [_motorhome("Cruiser 7.6 L", "Fiat", product_id=1)],
    )
    differing = match_products(
        [_extracted("Cruiser 7.6 L", "Fiat")],
        [_motorhome("Cruiser 7.6 L", "Mercedes", product_id=2)],
    )

    assert same[0].score == differing[0].score == 1.0
    assert differing[0].baseline is not None


# --- the store ------------------------------------------------------------------------


@pytest.fixture
def connection(tmp_path):
    conn = store.connect(tmp_path / "run_store.sqlite3")
    conn.execute(
        """
        INSERT INTO run (id, manufacturer_id, fmlv_manufacturer, trigger, status, started_at)
        VALUES (1, 111, 'Frankia', 'manual', 'running', '2026-09-23T00:00:00')
        """
    )
    conn.commit()
    yield conn
    conn.close()


def _seen(connection, *, model: str, base: str | None, fmlv_id: int | None):
    return products_store.upsert_seen(
        connection,
        manufacturer_id=111,
        fmlv_product_id=fmlv_id,
        manufacturer_range="Noctra",
        model=model,
        run_id=1,
        base_vehicle_manufacturer=base,
    )


def test_two_chassis_are_two_rows_with_two_histories(connection) -> None:
    fiat = _seen(connection, model="Cruiser 7.6 L", base="Fiat", fmlv_id=8889)
    mercedes = _seen(connection, model="Cruiser 7.6 L", base="Mercedes", fmlv_id=8888)

    assert fiat.id != mercedes.id
    assert fiat.base_vehicle_manufacturer == "Fiat"
    assert mercedes.base_vehicle_manufacturer == "Mercedes"


def test_the_same_vehicle_twice_is_one_row(connection) -> None:
    first = _seen(connection, model="Cruiser 7.6 L", base="Fiat", fmlv_id=8889)
    again = _seen(connection, model="Cruiser 7.6 L", base="Fiat", fmlv_id=8889)

    assert first.id == again.id


def test_a_new_product_with_no_fmlv_id_is_found_by_name_and_chassis(connection) -> None:
    """The fallback path. Without the chassis in it, Carthago's Fiat and Mercedes builds
    of one layout are one row."""
    fiat = _seen(connection, model="Cruiser 7.6 L", base="Fiat", fmlv_id=None)
    mercedes = _seen(connection, model="Cruiser 7.6 L", base="Mercedes", fmlv_id=None)
    fiat_again = _seen(connection, model="Cruiser 7.6 L", base="Fiat", fmlv_id=None)

    assert fiat.id != mercedes.id
    assert fiat_again.id == fiat.id


def test_two_live_products_taking_one_name_still_conflict(connection) -> None:
    """**The check this must not loosen.** Two FMLV products, both seen this run, both
    claiming one name on the same chassis: no local surgery can resolve that, so it is
    raised rather than silently merged.

    It is also why unknown is stored as '' and not NULL. NULL is not equal to NULL in a
    SQLite unique index, so a nullable column would let two chassis-less products hold one
    name and this would stop firing on exactly the FMLV duplicate Chausson hit.
    """
    _seen(connection, model="Cruiser 7.6 L", base=None, fmlv_id=8889)
    _seen(connection, model="Liner 8.3 L", base=None, fmlv_id=8888)

    with pytest.raises(products_store.ProductIdentityConflict):
        _seen(connection, model="Cruiser 7.6 L", base=None, fmlv_id=8888)


def test_the_same_name_on_two_chassis_is_not_a_conflict(connection) -> None:
    """The whole point: what used to be an unresolvable clash is now simply two vehicles."""
    _seen(connection, model="Cruiser 7.6 L", base="Fiat", fmlv_id=8889)
    _seen(connection, model="Liner 8.3 L", base="Mercedes", fmlv_id=8888)

    moved = _seen(connection, model="Cruiser 7.6 L", base="Mercedes", fmlv_id=8888)

    assert moved.base_vehicle_manufacturer == "Mercedes"
    assert connection.execute("SELECT COUNT(*) FROM product").fetchone()[0] == 2


def test_a_row_stored_before_the_column_existed_is_filled_in(connection) -> None:
    """It is found by its `fmlv_product_id` before the name is consulted, so the first run
    after the migration backfills its chassis rather than inserting a second row."""
    connection.execute(
        """
        INSERT INTO product (manufacturer_id, fmlv_product_id, manufacturer_range, model)
        VALUES (111, 8889, 'Noctra', 'Cruiser 7.6 L')
        """
    )
    connection.commit()
    before = connection.execute("SELECT COUNT(*) FROM product").fetchone()[0]

    filled = _seen(connection, model="Cruiser 7.6 L", base="Fiat", fmlv_id=8889)

    assert connection.execute("SELECT COUNT(*) FROM product").fetchone()[0] == before
    assert filled.base_vehicle_manufacturer == "Fiat"


# --- the trapdoor: a model that CHANGES chassis is still the same model ----------------
#
# The requester's check, 24 September 2026: *"it's quite common for manufacturers to keep
# the same model but change the base vehicle. I don't want that to appear as a new model
# when it's literally the same model. The only circumstance where we need to use the base
# as a differentiator is when there are actually two models live, one with one base and
# one with the other."*
#
# That is the behaviour these four lock in. The chassis **disambiguates between
# candidates**; it never gates a match, so with one live product a changed chassis is a
# field change on the row FMLV already has.


def test_a_model_that_changes_chassis_is_matched_not_new() -> None:
    """One live product, rebased from Fiat to Mercedes. It must match its own row."""
    results = match_products(
        [_extracted("Cruiser 7.6 L", "Mercedes")],
        [_motorhome("Cruiser 7.6 L", "Fiat", product_id=8889)],
    )

    assert results[0].baseline is not None, "a rebased model must not come through as new"
    assert results[0].baseline.product_id == 8889
    assert results[0].score == 1.0
    assert results[0].method == "exact"


def test_a_rebased_model_keeps_its_row_in_the_store(connection) -> None:
    """And the store updates that row rather than inserting beside it — the lookup finds
    it by `fmlv_product_id` before the name or the chassis is ever consulted."""
    before = _seen(connection, model="Cruiser 7.6 L", base="Fiat", fmlv_id=8889)

    after = _seen(connection, model="Cruiser 7.6 L", base="Mercedes", fmlv_id=8889)

    assert after.id == before.id
    assert after.base_vehicle_manufacturer == "Mercedes"
    assert connection.execute("SELECT COUNT(*) FROM product").fetchone()[0] == 1


def test_a_rebased_model_is_not_reported_as_disappeared() -> None:
    """The other half of the same worry: the Fiat row must not fall out unmatched and be
    proposed for deactivation."""
    results = match_products(
        [_extracted("Cruiser 7.6 L", "Mercedes")],
        [_motorhome("Cruiser 7.6 L", "Fiat", product_id=8889)],
    )

    claimed = {r.baseline.product_id for r in results if r.baseline is not None}

    assert claimed == {8889}


def test_the_chassis_only_decides_when_there_really_are_two() -> None:
    """The contrast, side by side. With one baseline row a Mercedes claims the Fiat's row;
    with two, each claims its own and neither is new."""
    one = match_products(
        [_extracted("Cruiser 7.6 L", "Mercedes")],
        [_motorhome("Cruiser 7.6 L", "Fiat", product_id=8889)],
    )
    two = match_products(
        [_extracted("Cruiser 7.6 L", "Mercedes"), _extracted("Cruiser 7.6 L", "Fiat")],
        [
            _motorhome("Cruiser 7.6 L", "Fiat", product_id=8889),
            _motorhome("Cruiser 7.6 L", "Mercedes", product_id=8888),
        ],
    )

    assert [r.baseline.product_id for r in one] == [8889]
    assert {
        r.extracted.product.base_vehicle_manufacturer: r.baseline.product_id for r in two
    } == {"Mercedes": 8888, "Fiat": 8889}
