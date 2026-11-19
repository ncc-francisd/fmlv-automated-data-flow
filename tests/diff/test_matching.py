"""Unit tests for token-based product matching."""

from __future__ import annotations

import pytest

from src.adapters.base import ExtractedMotorhome
from src.diff.matching import match_products, token_similarity
from src.product_model.model import Motorhome


def make_motorhome(**overrides: object) -> Motorhome:
    fields: dict[str, object] = {
        "manufacturer": "Adria Mobil",
        "manufacturer_range": "Matrix",
        "model": "Supreme 670 DC",
        "product_id": 12345,
    }
    fields.update(overrides)
    return Motorhome(**fields)


def make_extracted(**overrides: object) -> ExtractedMotorhome:
    return ExtractedMotorhome(motorhome=make_motorhome(product_id=None, **overrides))


def test_exact_range_and_model_match_scores_one() -> None:
    baseline = make_motorhome()
    scraped = make_extracted(manufacturer_range="Matrix", model="Supreme 670 DC")
    assert token_similarity(baseline, scraped.motorhome) == 1.0


def test_word_order_difference_still_matches() -> None:
    # Adria's site: "670 DC" (layout) + "Supreme Alde RHD" (trim) vs baseline's
    # "Supreme 670 DC" — same words, different order/extra trim words (see
    # docs/adapters/adria.md).
    baseline = make_motorhome(manufacturer_range="Matrix", model="Supreme 670 DC")
    scraped = make_extracted(manufacturer_range="Matrix", model="670 DC Supreme Alde RHD")
    results = match_products([scraped], [baseline])
    assert len(results) == 1
    assert results[0].baseline is baseline
    assert results[0].method == "fuzzy"
    assert 0.5 <= results[0].score < 1.0


def test_unrelated_product_does_not_match() -> None:
    baseline = make_motorhome(manufacturer_range="Matrix", model="Supreme 670 DC")
    scraped = make_extracted(manufacturer_range="Coral", model="Axess 600 SP")
    results = match_products([scraped], [baseline])
    assert results[0].baseline is None
    assert results[0].method is None
    assert results[0].score == 0.0


def test_one_to_one_assignment_does_not_double_match_a_baseline_row() -> None:
    baseline = make_motorhome(manufacturer_range="Matrix", model="Supreme 670 DC")
    best = make_extracted(manufacturer_range="Matrix", model="Supreme 670 DC")
    worse = make_extracted(manufacturer_range="Matrix", model="670 DC Supreme Alde RHD")

    results = match_products([worse, best], [baseline])

    matched = [r for r in results if r.baseline is not None]
    assert len(matched) == 1
    # The exact match wins the shared baseline row even though it was scored second.
    assert matched[0].extracted is best
    assert matched[0].method == "exact"


def test_new_product_with_no_baseline_candidates_is_unmatched() -> None:
    scraped = make_extracted(manufacturer_range="Coral", model="Axess 600 SP")
    results = match_products([scraped], [])
    assert results[0].baseline is None
    assert results[0].baseline_index is None


def test_threshold_can_be_tightened() -> None:
    baseline = make_motorhome(manufacturer_range="Matrix", model="Supreme 670 DC")
    scraped = make_extracted(manufacturer_range="Matrix", model="670 DC Supreme Alde RHD")
    results = match_products([scraped], [baseline], threshold=0.9)
    assert results[0].baseline is None


# --- Model codes spaced one way and closed up the other (docs/adapters/sunlight.md) ---


def test_spaced_model_code_matches_the_closed_up_baseline() -> None:
    # Sunlight's MY27 price list prints "V 60" and renamed the range at the same time;
    # FMLV holds the layout as "Van Adventure Edition" / "V60".
    baseline = make_motorhome(manufacturer_range="Van Adventure Edition", model="V60")
    scraped = make_extracted(manufacturer_range="Van Adventure", model="V 60")
    results = match_products([scraped], [baseline])
    assert results[0].baseline is baseline
    assert results[0].method == "fuzzy"


def test_code_with_a_trailing_letter_matches_however_it_is_spaced() -> None:
    # "V 67 S" (baseline) and "V 67S" (price list) are one layout, not two.
    baseline = make_motorhome(manufacturer_range="Van Adventure Edition", model="V 67 S")
    scraped = make_extracted(manufacturer_range="Van Adventure", model="V 67S")
    results = match_products([scraped], [baseline])
    assert results[0].baseline is baseline


def test_a_trailing_letter_still_distinguishes_two_real_layouts() -> None:
    # Sunlight sells both a CLIFF 540 and a CLIFF 540 V. Gluing the code back together
    # must not glue these two into one (sunlight.py's parser exists to keep them apart).
    baseline = make_motorhome(manufacturer_range="CLIFF Adventure", model="CLIFF 540")
    scraped = make_extracted(manufacturer_range="CLIFF Vanlife", model="CLIFF 540 V")
    results = match_products([scraped], [baseline])
    assert results[0].baseline is None


def test_siblings_sharing_a_range_but_not_a_code_do_not_match() -> None:
    # A two-word range name is half the token bag, which was enough on its own to drag
    # two different layouts up to the threshold.
    baseline = make_motorhome(manufacturer_range="Low Profiles", model="T65")
    scraped = make_extracted(manufacturer_range="Low Profiles", model="T 66S")
    results = match_products([scraped], [baseline])
    assert results[0].baseline is None
    assert token_similarity(baseline, scraped.motorhome) == 0.0


def test_a_code_on_only_one_side_does_not_block_a_match() -> None:
    # The code gate applies only when *both* names carry one; a trim-only name is not
    # disqualified for having no digits to agree about.
    baseline = make_motorhome(manufacturer_range="Matrix", model="Supreme Plus")
    scraped = make_extracted(manufacturer_range="Matrix", model="Supreme Plus 670")
    results = match_products([scraped], [baseline])
    assert results[0].baseline is baseline


def test_adria_layout_code_plus_trim_is_unaffected_by_code_joining() -> None:
    # "DC" is two letters, so it is left alone rather than glued to "670" — the case
    # DEFAULT_THRESHOLD was calibrated against must not move.
    baseline = make_motorhome(manufacturer_range="Matrix", model="Supreme 670 DC")
    scraped = make_extracted(manufacturer_range="Matrix", model="670 DC Supreme Alde RHD")
    # 2/3 — the score the old word-bag tokeniser gave this pair, unchanged.
    assert token_similarity(baseline, scraped.motorhome) == pytest.approx(2 / 3)


# --- Which duplicate baseline row an update lands on ---


def test_live_baseline_row_wins_over_an_archived_duplicate() -> None:
    # FMLV's export is a history: Sunlight's "Coachbuilts A60" is in it twice, archived
    # 2022 and live 2026. An update belongs on the live row.
    archived = make_motorhome(
        manufacturer_range="Coachbuilts", model="A60", product_id=3524, year=2022, archived=True
    )
    live = make_motorhome(
        manufacturer_range="Coachbuilts", model="A60", product_id=6562, year=2026, archived=False
    )
    scraped = make_extracted(manufacturer_range="Coachbuilts Root", model="A 60")

    results = match_products([scraped], [archived, live])

    assert results[0].baseline is live


def test_newest_year_wins_between_two_live_duplicates() -> None:
    older = make_motorhome(
        manufacturer_range="Low Profiles", model="T58", product_id=3536, year=2022
    )
    newer = make_motorhome(
        manufacturer_range="Low Profiles", model="T58", product_id=7982, year=2026
    )
    scraped = make_extracted(manufacturer_range="Low Profiles", model="T 58")

    results = match_products([scraped], [older, newer])

    assert results[0].baseline is newer


def test_a_layout_code_matches_whether_or_not_it_is_spaced() -> None:
    """**The trap this exists for.** FMLV holds Carado's van as `CV 640` where the site
    writes `CV640`. With `cv` and `640` left as separate tokens the two shared no layout
    code at all, so `_jaccard` zeroed the pair and Carado's run 175 reported a van still
    on sale at GBP53,090 as missing from the site. Two more went the same way."""
    from src.diff.matching import DEFAULT_THRESHOLD, token_similarity
    from src.product_model.model import Motorhome

    def product(manufacturer_range: str, model: str) -> Motorhome:
        return Motorhome(
            manufacturer="Carado", manufacturer_range=manufacturer_range, model=model
        )

    assert (
        token_similarity(product("Campervan", "CV640"), product("Campervan", "CV 640"))
        == 1.0
    )
    assert (
        token_similarity(
            product("Campervan PRO", "CV541"), product("Campervan PRO", "CV 541 PRO")
        )
        >= DEFAULT_THRESHOLD
    )


def test_a_multi_letter_run_after_the_digits_is_still_left_alone() -> None:
    """The reason `_is_code_fragment` excluded multi-letter runs in the first place:
    joining `670` to `DC` would make Adria's `670 DC` and `670 DL` one token each and
    lose the layout entirely. The prefix rule only ever looks forwards."""
    from src.diff.matching import _tokenize

    assert _tokenize("670 DC") == frozenset({"670", "dc"})
    assert _tokenize("A Class") == frozenset({"a", "class"})
    assert _tokenize("MWB Harris") == frozenset({"mwb", "harris"})


def test_a_long_word_never_swallows_a_number() -> None:
    """`PRO` is three letters and could open a code; `Campervan` cannot."""
    from src.diff.matching import _tokenize

    assert _tokenize("Campervan 640") == frozenset({"campervan", "640"})


def test_a_plus_suffix_keeps_its_own_baseline_row() -> None:
    r"""**Panama, 19 November 2026.** `_tokenize` keeps letters and digits only, so `P\50`
    and `P\50+` reduce to the same bag and both score 1.000 against FMLV's `P\50+`. For a
    year that cost nothing, because only the `+` existed. The day Panama published the
    plain `P\50`, the greedy assignment had two perfect candidates for one row, fell
    through to collection order, and gave the row to the new model — so a product FMLV
    held and was actively selling came back as new.

    The exact name now outranks an equal score, so the row goes to the product that
    carries its name verbatim and the genuinely new one is left over.
    """
    baseline = make_motorhome(manufacturer_range="P", model=r"\50+")
    newcomer = make_extracted(manufacturer_range="P", model=r"\50")
    incumbent = make_extracted(manufacturer_range="P", model=r"\50+")

    # The newcomer first, which is the order the roster gives and the order that failed.
    results = match_products([newcomer, incumbent], [baseline])

    assert results[0].baseline is None, "the new P\50 is new"
    assert results[1].baseline is baseline, "the P\50+ keeps its own row"


def test_the_same_name_rank_ignores_case_and_spacing() -> None:
    """An export that holds `P \\50 +` is holding the same name, not a different product.
    Separation has to come from the characters that differ, not from how they are typed.
    """
    from src.diff.matching import _same_name_rank

    baseline = make_motorhome(manufacturer_range="P", model=r"\50+")

    assert _same_name_rank(make_motorhome(manufacturer_range="p", model=r"\50+"), baseline) == 0
    assert _same_name_rank(make_motorhome(manufacturer_range="P", model=r"\50+ "), baseline) == 0
    assert _same_name_rank(make_motorhome(manufacturer_range="P", model=r"\50"), baseline) == 1


def test_a_suffix_spaced_one_way_in_fmlv_still_claims_its_own_row() -> None:
    """**Etrusco's spelling, in Panama's situation.**

    FMLV holds `CV` / `640 SB +`, with a space before the plus, where Etrusco's own site
    writes `640 SB+`. Today that pair matches correctly only because FMLV happens to hold
    the plain `640 SB` as well, so the plain scraped name finds an exact row and the
    plussed one is left the right row by elimination. Take the plain row away — which is
    exactly the position Panama was in, one baseline row and two perfect candidates — and
    the spacing is all that separates them.

    With the exact name compared as typed, `640 SB+` does not match `640 SB +`, neither
    candidate ranks ahead of the other, and the tie falls through to collection order: the
    plain `640 SB` takes the row and the `640 SB+` FMLV is selling is proposed as new.
    """
    plussed = make_motorhome(manufacturer_range="CV", model="640 SB +", product_id=7969)
    scraped_plain = make_extracted(manufacturer_range="CV", model="640 SB")
    scraped_plussed = make_extracted(manufacturer_range="CV", model="640 SB+")

    # The plain one first, which is the order that loses the row.
    results = match_products([scraped_plain, scraped_plussed], [plussed])

    assert results[0].baseline is None, "the plain 640 SB is the new one"
    assert results[1].baseline is plussed, "640 SB+ belongs on the 640 SB + row"


def test_both_spellings_present_in_fmlv_keep_their_own_rows() -> None:
    """The case Etrusco is actually in today, which must not move: FMLV holds both the
    plain row and the spaced-suffix one, and each scraped name goes to its own."""
    plain = make_motorhome(manufacturer_range="CV", model="640 SB", product_id=6533)
    plussed = make_motorhome(manufacturer_range="CV", model="640 SB +", product_id=7969)
    scraped_plain = make_extracted(manufacturer_range="CV", model="640 SB")
    scraped_plussed = make_extracted(manufacturer_range="CV", model="640 SB+")

    results = match_products([scraped_plussed, scraped_plain], [plain, plussed])

    assert results[0].baseline is plussed
    assert results[1].baseline is plain


def test_the_same_name_rank_ignores_every_space_not_just_repeated_ones() -> None:
    """Carthago writes a weight both ways — `4.2 t` and `4.2t` — and FMLV holds one of
    them. Collapsing runs of whitespace is not enough; the spaces have to go."""
    from src.diff.matching import _same_name_rank

    baseline = make_motorhome(manufacturer_range="C2-tourer", model='I 147 RB-LE "K" comfort 4.2t')

    same = make_motorhome(
        manufacturer_range="C2-tourer", model='I 147 RB-LE "K" comfort 4.2 t'
    )
    assert _same_name_rank(same, baseline) == 0

    # A real difference still separates them: 4.2t and 3.5t are two vehicles.
    other = make_motorhome(
        manufacturer_range="C2-tourer", model='I 147 RB-LE "K" lightweight 3.5 t'
    )
    assert _same_name_rank(other, baseline) == 1


def test_dropping_spaces_does_not_merge_two_real_layouts() -> None:
    """Sunlight sells both a `CLIFF 540` and a `CLIFF 540 V`. Removing spaces must not
    make the trailing letter disappear along with them."""
    from src.diff.matching import _same_name_rank

    plain = make_motorhome(manufacturer_range="CLIFF Adventure", model="CLIFF 540")
    with_v = make_motorhome(manufacturer_range="CLIFF Adventure", model="CLIFF 540 V")
    assert _same_name_rank(plain, with_v) == 1
