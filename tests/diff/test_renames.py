"""Matching a product the manufacturer has renamed to the row FMLV still holds.

**Most renames never reach this**, and the first test here pins that so nobody reaches for
a rename when the threshold already covers them. Token overlap carries a range whose name
was merely shortened, because the layout code still agrees and the code is most of a short
name:

| rename | score | |
|---|---|---|
| Pilote `Van Vega V540G` -> `Van V540G` | 0.667 | matches already |
| Sunlight `Van Adventure Edition V60` -> `Van Adventure V60` | 0.750 | matches already |
| Auto-Sleepers `Active FG635` vs `Active FG365` | 0.000 | needs a rename |
| McLouis `Fusion 330` against FMLV's `Baron 530` | 0.000 | needs a rename |
| a one-word range swapped outright, code kept | 0.333 | needs a rename |

The two that need it are real. Auto-Sleepers' `FG365` had its digits transposed in an older
export (`docs/adapters/auto-sleepers.md`), since corrected in FMLV — which is why it also
serves as the staleness case. McLouis renamed and renumbered the whole range at once when
the Baron moved to Elnagh, `Baron 530/560/573/579` becoming `Fusion 330/360/373/379`
(`docs/adapters/mclouis.md`); FMLV still holds the Baron rows under McLouis as 2025, so the
two only miss each other because the model-year filter drops them.

No network here.
"""

from __future__ import annotations

from src.adapters.base import ExtractedMotorhome
from src.diff.matching import (
    NO_RENAMES,
    Renames,
    match_products,
    stale_renames,
    token_similarity,
)
from src.product_model.model import Motorhome


def baseline(manufacturer_range: str, model: str, product_id: int = 100) -> Motorhome:
    return Motorhome(
        manufacturer="Trigano S A McLouis",
        manufacturer_range=manufacturer_range,
        model=model,
        product_id=product_id,
    )


def scraped(manufacturer_range: str, model: str) -> ExtractedMotorhome:
    return ExtractedMotorhome(
        motorhome=Motorhome(
            manufacturer="Trigano S A McLouis",
            manufacturer_range=manufacturer_range,
            model=model,
            product_id=None,
        )
    )


# --------------------------------------------------------------------------- #
# What does not need a rename at all
# --------------------------------------------------------------------------- #


def test_a_shortened_range_matches_without_any_rename() -> None:
    """Pilote's and Sunlight's renames both clear the default threshold on their own.

    Pinned because declaring a rename for one of these would be dead config from the day
    it was written, and `stale_renames` would then be the only thing saying so.
    """
    shortened = token_similarity(
        scraped("Van Vega", "V540G").motorhome, baseline("Van", "V540G")
    )
    sunlight = token_similarity(
        scraped("Van Adventure Edition", "V60").motorhome,
        baseline("Van Adventure", "V60"),
    )

    assert shortened > 0.5
    assert sunlight > 0.5
    assert match_products(
        [scraped("Van Vega", "V540G")], [baseline("Van", "V540G")]
    )[0].baseline is not None


# --------------------------------------------------------------------------- #
# A layout code that moved, which no threshold can recover
# --------------------------------------------------------------------------- #


def test_a_moved_code_scores_zero_however_low_the_threshold() -> None:
    """Deliberate: a code is the one part of a name meant to be unique in its range."""
    old, new = baseline("Active", "FG365"), scraped("Active", "FG635")

    assert token_similarity(new.motorhome, old) == 0.0
    assert match_products([new], [old], threshold=0.0)[0].baseline is None


def test_a_moved_code_matches_once_the_rename_names_it() -> None:
    old, new = baseline("Active", "FG365"), scraped("Active", "FG635")
    renames = Renames(models={("Active", "FG635"): ("Active", "FG365")})

    assert token_similarity(new.motorhome, old, renames=renames) == 1.0

    result = match_products([new], [old], renames=renames)[0]
    assert result.baseline is old
    assert result.method == "exact"


def test_a_range_and_code_renamed_together_matches() -> None:
    """McLouis's `Baron 530` became `Fusion 330` — both halves moved at once."""
    renames = Renames(
        models={
            ("Fusion", "330"): ("Baron", "530"),
            ("Fusion", "360"): ("Baron", "560"),
        }
    )
    rows = [baseline("Baron", "530", 1), baseline("Baron", "560", 2)]
    found = [scraped("Fusion", "330"), scraped("Fusion", "360")]

    results = match_products(found, rows, renames=renames)

    assert [result.baseline for result in results] == rows


def test_each_renamed_layout_lands_on_its_own_row() -> None:
    """The renumbering is not an offset to be inferred — 530->330 but 573->373."""
    renames = Renames(models={("Fusion", "373"): ("Baron", "573")})
    rows = [baseline("Baron", "530", 1), baseline("Baron", "573", 2)]

    result = match_products([scraped("Fusion", "373")], rows, renames=renames)[0]

    assert result.baseline is rows[1]


# --------------------------------------------------------------------------- #
# A range replaced outright, where lowering the threshold would be reckless
# --------------------------------------------------------------------------- #


def test_a_range_swapped_outright_falls_below_the_threshold() -> None:
    assert token_similarity(
        scraped("Galaxy", "630").motorhome, baseline("Sport", "630")
    ) < 0.5


def test_a_renamed_range_carries_every_layout_in_it() -> None:
    """One entry, not one per layout — the point of a range-level rename."""
    renames = Renames(ranges={"Galaxy": "Sport"})
    rows = [baseline("Sport", code, i) for i, code in enumerate(("630", "650", "690"))]
    found = [scraped("Galaxy", code) for code in ("630", "650", "690")]

    results = match_products(found, rows, renames=renames)

    assert [result.baseline for result in results] == rows


def test_a_rename_leaves_every_other_product_alone() -> None:
    """Narrower than lowering `MATCH_THRESHOLD`, which loosens every pair at once."""
    renames = Renames(ranges={"Galaxy": "Sport"})
    rows = [baseline("Sport", "630", 1), baseline("Cruiser", "690", 2)]

    assert match_products([scraped("Explorer", "100")], rows, renames=renames)[0].baseline is None


def test_a_model_rename_beats_a_range_rename_for_the_same_product() -> None:
    """So a range-wide rename can carry an exception for the one layout that also moved."""
    renames = Renames(
        ranges={"Fusion": "Baron"},
        models={("Fusion", "330"): ("Baron", "531")},
    )

    assert renames.applied_to("Fusion", "330") == ("Baron", "531")
    assert renames.applied_to("Fusion", "360") == ("Baron", "360")


def test_spelling_differences_that_a_person_would_ignore_still_match() -> None:
    """An adapter author copies the name out of an export; case and spacing drift."""
    assert Renames(ranges={"van  VEGA": "Van"}).applied_to("Van Vega", "V540G") == (
        "Van",
        "V540G",
    )


def test_an_unrenamed_product_is_returned_untouched() -> None:
    assert Renames().applied_to("Baron", "530") == ("Baron", "530")
    assert NO_RENAMES.applied_to("Baron", "530") == ("Baron", "530")


# --------------------------------------------------------------------------- #
# Renaming is for matching only, never for FMLV's own strings
# --------------------------------------------------------------------------- #


def test_the_scraped_product_keeps_its_own_name() -> None:
    """Rewriting is for scoring only.

    The settled rule is that the FMLV export decides these strings, and
    `store.changes._IDENTITY_FIELDS` never proposes a change to one.
    """
    renames = Renames(models={("Fusion", "330"): ("Baron", "530")})
    new = scraped("Fusion", "330")

    match_products([new], [baseline("Baron", "530")], renames=renames)

    assert (new.motorhome.manufacturer_range, new.motorhome.model) == ("Fusion", "330")


def test_the_baseline_side_is_never_rewritten() -> None:
    """A rename says what the *site* now calls a row, so only the scraped side moves.

    Rewriting both would score 1.0 on a pair that does not agree, hiding a real mismatch.
    """
    renames = Renames(ranges={"Baron": "Fusion"})

    assert token_similarity(
        scraped("Baron", "530").motorhome, baseline("Baron", "530"), renames=renames
    ) < 1.0


# --------------------------------------------------------------------------- #
# A rename is meant to stop being needed
# --------------------------------------------------------------------------- #


def test_a_rename_that_did_its_job_is_not_reported() -> None:
    renames = Renames(ranges={"Fusion": "Baron"})

    assert stale_renames([scraped("Fusion", "330")], [baseline("Baron", "330")], renames) == []


def test_a_rename_the_site_no_longer_needs_is_reported() -> None:
    """The manufacturer moved on again, or the entry never matched what the adapter emits."""
    renames = Renames(ranges={"Fusion": "Baron"})

    notes = stale_renames([scraped("Baron", "530")], [baseline("Baron", "530")], renames)

    assert len(notes) == 1
    assert "nothing collected this run is in a range called 'Fusion'" in notes[0]


def test_a_rename_fmlv_has_already_had_applied_is_reported() -> None:
    """Auto-Sleepers' transposed codes were fixed in FMLV, which is how these end.

    Left in place the entry claims a row is called something FMLV no longer calls it, and
    the next person reading the adapter believes it.
    """
    renames = Renames(models={("Active", "FG635"): ("Active", "FG365")})

    notes = stale_renames(
        [scraped("Active", "FG635")], [baseline("Active", "FG635")], renames
    )

    assert len(notes) == 1
    assert "FMLV has probably been corrected" in notes[0]


def test_nothing_is_deleted_or_corrected_automatically() -> None:
    """A stale entry is a note for a person; removing it belongs in a commit."""
    renames = Renames(models={("Active", "FG635"): ("Active", "FG365")})
    rows = [baseline("Active", "FG635")]

    stale_renames([scraped("Active", "FG635")], rows, renames)

    assert renames.models == {("Active", "FG635"): ("Active", "FG365")}


def test_no_renames_reports_nothing() -> None:
    assert stale_renames([scraped("Baron", "530")], [baseline("Baron", "530")], NO_RENAMES) == []


def test_renames_are_falsey_when_empty() -> None:
    """So an adapter that declares neither dict costs nothing to check."""
    assert not Renames()
    assert Renames(ranges={"a": "b"})
    assert Renames(models={("a", "b"): ("c", "d")})


# --------------------------------------------------------------------------- #
# The adapter opt-in, which fails silently if it is not wired
# --------------------------------------------------------------------------- #


def test_an_adapter_declaring_neither_dict_gets_no_renames() -> None:
    """Every manufacturer but the handful that have had one, so this is the common path."""
    from types import SimpleNamespace  # noqa: PLC0415

    from src.cli import renames as adapter_renames  # noqa: PLC0415

    assert not adapter_renames(SimpleNamespace())


def test_an_adapter_declaring_renames_has_them_read() -> None:
    """The `getattr` opt-in, same shape as `MATCH_THRESHOLD` and `DEFAULT_RANGES`.

    Wired wrongly this fails silently: the adapter's declaration is simply ignored and the
    run reports new products beside disappearance notices, which is what it exists to stop.
    """
    from types import SimpleNamespace  # noqa: PLC0415

    from src.cli import renames as adapter_renames  # noqa: PLC0415

    declared = adapter_renames(
        SimpleNamespace(
            RENAMED_RANGES={"Fusion": "Baron"},
            RENAMED_MODELS={("Fusion", "330"): ("Baron", "530")},
        )
    )

    assert declared.ranges == {"Fusion": "Baron"}
    assert declared.models == {("Fusion", "330"): ("Baron", "530")}
    assert declared.applied_to("Fusion", "330") == ("Baron", "530")


def test_a_declared_rename_reaches_the_diff() -> None:
    """End to end through `diff_products`, which is what the run actually calls."""
    from src.diff import diff_products  # noqa: PLC0415
    from src.diff.classify import ChangeKind  # noqa: PLC0415

    renames = Renames(models={("Fusion", "330"): ("Baron", "530")})
    rows = [baseline("Baron", "530", 1)]

    without = diff_products([scraped("Fusion", "330")], rows)
    with_rename = diff_products([scraped("Fusion", "330")], rows, renames=renames)

    assert {diff.kind for diff in without} == {
        ChangeKind.NEW_PRODUCT,
        ChangeKind.DISAPPEARED,
    }
    assert ChangeKind.NEW_PRODUCT not in {diff.kind for diff in with_rename}
    assert ChangeKind.DISAPPEARED not in {diff.kind for diff in with_rename}
    assert with_rename[0].fmlv_product_id == 1
