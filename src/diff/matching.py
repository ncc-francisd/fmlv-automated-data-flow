"""Matching scraped products to existing FMLV `product_id`s.

Per DESIGN.md §4.1, `product_id` is minted by the NCC website, not this application —
matching is how a freshly scraped product finds its way to the *right* existing
`product_id` (so a 2027 model update lands on the same row as its 2026 predecessor)
or is correctly recognised as new.

Exact string matching on `manufacturer_range`/`model` does not work. A manufacturer's
site names a configuration differently to the baseline export — Adria's site names a
configuration by layout code + trim (`"670 DC"` + `"Supreme Alde RHD"`), the baseline
export has `"Supreme 670 DC"` for the same product: same words, different order (see
docs/adapters/adria.md and the TODO.md note it links to). So matching is token-based:
normalise range+model text into a bag of words and score candidates by overlap, rather
than requiring an exact match.

A bag of words alone is not enough, because a model *code* is not a word. Sunlight's
price list prints `V 60`, the baseline export holds `V60` — the same layout, but
tokenised as `{v, 60}` and `{v60}`, which share nothing at all. The overlap then rests
entirely on the range name, and when the range has *also* been renamed (Sunlight's MY27
`Van Adventure Edition` → `Van Adventure`) the score collapses far enough that eleven
products FMLV already held were proposed as new, while the same run raised disappearance
notices against the rows they duplicated. See docs/adapters/sunlight.md.

So code fragments are glued back together before scoring: a run of adjacent tokens that
can only be parts of a code — single letters and digit-leading tokens — is joined into
one, so `V 60`, `V60`, `I 67S`/`I67S` and `V 67 S`/`V 67S` all tokenise alike. The rule
is deliberately narrow. It leaves a multi-letter token such as Adria's `DC` alone, so
`"670 DC"` still scores as before, and it keeps `CLIFF 540 V` (`{cliff, 540v}`) distinct
from `CLIFF 540` (`{cliff, 540}`) — the collision sunlight.py's run-based parser exists
to avoid, which a blanket "strip the spaces" normalisation would have reintroduced here.

Callers are expected to have already scoped both `scraped` and `baseline` to a single
manufacturer — a run is always per-manufacturer (DESIGN.md §5), so matching does not
check manufacturer identity itself.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from ..adapters.base import ExtractedProduct
from ..product_model.product import Product

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

#: Only whitespace may sit between two tokens for them to count as one code. A comma or
#: a slash separates *fields*, so "Matrix, 670" must not glue into "matrix670".
_WHITESPACE_ONLY = re.compile(r"\s*\Z")

#: Below this score a candidate isn't a match at all — the scraped product is treated
#: as new instead. Chosen against the Adria "670 DC Supreme Alde RHD" vs baseline
#: "Supreme 670 DC" case (see docs/adapters/adria.md), which scores well above this;
#: revisit once a second manufacturer's naming has been checked against it.
DEFAULT_THRESHOLD = 0.5


def _key(text: str | None) -> str:
    """A name reduced to what two people spelling it would still agree on.

    Lower-cased and inner whitespace collapsed, so an adapter author copying `Van Vega`
    out of an FMLV export matches `van  vega` in the scraped product. Nothing stronger:
    a rename declares two *specific* names are one product, and quietly matching more
    than was written down is the opposite of what it is for.
    """
    return " ".join((text or "").lower().split())


@dataclass(frozen=True)
class Renames:
    """What a manufacturer has renamed since FMLV recorded it, for matching only.

    **Most renames do not need this**, and reaching for it first would be a mistake.
    Token overlap already carries a range whose name was shortened, because the layout
    code still agrees and the code is most of a short name:

    | rename | score | |
    |---|---|---|
    | Pilote `Van Vega V540G` -> `Van V540G` | 0.667 | matches already |
    | Sunlight `Van Adventure Edition V60` -> `Van Adventure V60` | 0.750 | matches already |
    | Auto-Sleepers `Active FG635` vs `Active FG365` | **0.000** | needs this |
    | McLouis `Fusion 330` <- FMLV's `Baron 530` | **0.000** | needs this |
    | a one-word range swapped, code kept | **0.333** | needs this |

    So there are two cases that genuinely need naming, and the first is the important one:

    * **the layout code moved.** `token_similarity` returns 0 when both sides name a code
      and none agree — deliberately, because a code is the one part of a name meant to be
      unique within its range. No threshold recovers that, and none should.
    * **the range was replaced outright** rather than shortened, leaving only the code in
      common. Reaching 0.333 by lowering `MATCH_THRESHOLD` would match almost anything.

    Lowering the threshold is the blunt alternative in both: it loosens *every* pair in
    the manufacturer, and `docs/adapters/README.md` records that Adria's good match at
    0.667 scores lower than Etrusco's worst bad match at 0.750, so there is not always a
    value that separates them. A rename names one pair and leaves the rest alone.

    **Matching is all this does; whether FMLV is corrected is a separate question, and the
    answer is the adapter's.** A rename is proposed like any other field change when the
    adapter records provenance for `manufacturer_range`/`model`, and suppressed when it
    records none — `store.changes._IDENTITY_FIELDS` only keeps those columns out of the
    *needs-a-choice* prompt for a new product, it does not stop them being compared.

    Those two levers together are what makes an otherwise undeliverable correction
    deliverable. Wingamm's Brownie is the worked example: FMLV files it under range
    `Coach Built low profile`, a body type in the range column, and emitting the right name
    scored 0.200 and orphaned `product_id` 5855. Naming the rename here matches it at 1.000
    *and* lets the adapter propose the correction through review, instead of emitting
    FMLV's own wrong value and waiting on a manual edit.

    Propose **both halves of the identity or neither** — `docs/adapters/README.md` records
    that accepting a range rename alone left Bailey's `Adamo XL` + `I` as `Adamo I`.

    Once the correction is accepted the entry here is dead, and `stale_renames` says so.

    Both maps are keyed on **what the site now says** and give **what FMLV still holds**,
    which is the direction an adapter author reads them in: the scraped name is the one
    they have in front of them.
    """

    #: Site's range name -> FMLV's, for every layout in it. The common case: a range is
    #: renamed and its layout codes are untouched.
    ranges: Mapping[str, str] = field(default_factory=dict)

    #: Site's `(range, model)` -> FMLV's, for one layout. Needed when the **code** moves,
    #: which forces the score to 0 however alike the rest reads.
    models: Mapping[tuple[str, str], tuple[str, str]] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return bool(self.ranges or self.models)

    def applied_to(
        self, manufacturer_range: str | None, model: str | None
    ) -> tuple[str | None, str | None]:
        """One scraped identity rewritten to the name FMLV still holds, if it is renamed.

        `models` is consulted first and wins outright, so a range-wide rename can carry
        an exception for the one layout that was also renumbered.
        """
        whole = {
            (_key(scraped_range), _key(scraped_model)): target
            for (scraped_range, scraped_model), target in self.models.items()
        }
        renamed = whole.get((_key(manufacturer_range), _key(model)))
        if renamed is not None:
            return renamed

        ranges = {_key(scraped): target for scraped, target in self.ranges.items()}
        moved = ranges.get(_key(manufacturer_range))
        if moved is not None:
            return moved, model
        return manufacturer_range, model


#: No renames, which is every manufacturer but the handful that have had one.
NO_RENAMES = Renames()


def _is_code_fragment(token: str) -> bool:
    """True for a token that can only be part of a model code, never a word.

    A lone letter (`V`, `T`, the `S` of `V 67 S`) or anything starting with a digit
    (`60`, `67S`, `7433Q`). A multi-letter run like `DC` or `RHD` is deliberately
    excluded: it is just as likely to be a trim name, and gluing it to its neighbour
    would break Adria's `"670 DC"` (docs/adapters/adria.md).
    """
    return (len(token) == 1 and token.isalpha()) or token[0].isdigit()


def _tokenize(text: str | None) -> frozenset[str]:
    """Word-bag of `text`, with adjacent model-code fragments joined into one token.

    Runs of code fragments separated by nothing but whitespace are joined, so `V 60`
    and `V60` — and `V 67 S` and `V 67S` — all yield the same token. A run is only
    joined when it carries a digit somewhere: `A Class` stays two tokens, since `A` on
    its own would otherwise swallow the word after it.
    """
    if not text:
        return frozenset()
    lowered = text.lower()
    matches = list(_TOKEN_PATTERN.finditer(lowered))

    tokens: list[str] = []
    run: list[re.Match[str]] = []

    def flush() -> None:
        if len(run) > 1 and any(match.group()[0].isdigit() for match in run):
            tokens.append("".join(match.group() for match in run))
        else:
            tokens.extend(match.group() for match in run)
        run.clear()

    for match in matches:
        adjacent = bool(run) and bool(
            _WHITESPACE_ONLY.match(lowered, run[-1].end(), match.start())
        )
        if not _is_code_fragment(match.group()):
            flush()
            tokens.append(match.group())
            continue
        if not adjacent:
            flush()
        run.append(match)
    flush()

    return frozenset(tokens)


def _identity_tokens(manufacturer_range: str | None, model: str | None) -> frozenset[str]:
    return _tokenize(manufacturer_range) | _tokenize(model)


def _codes(tokens: frozenset[str]) -> frozenset[str]:
    """The layout codes in a token bag — the tokens carrying a digit."""
    return frozenset(token for token in tokens if any(char.isdigit() for char in token))


def token_similarity(
    left: Product, right: Product, *, renames: Renames = NO_RENAMES
) -> float:
    """Jaccard similarity of the two products' range+model word bags, in [0, 1].

    `renames` is applied to **`left`**, which `match_products` always calls with the
    scraped product — a rename says what the site now calls a row FMLV still holds under
    the old name, so it is the scraped side that gets rewritten. Rewriting is for scoring
    only; the product keeps its own name everywhere else.

    **The better of the two scores wins, so a rename can only ever raise one.** That is
    what makes an entry safe to leave in place across the correction it is waiting for:
    while FMLV holds the old name the rewritten identity matches, and the moment FMLV is
    corrected the product's own name matches instead. Scoring *only* the rewritten
    identity meant an accepted correction orphaned the very product the rename existed to
    protect — Wingamm's Brownie went from 1.000 to 0.200 the day its rename was accepted,
    and `stale_renames` would only have said so alongside the broken run.

    Zero when both sides name a layout code and none of the codes agree. Word overlap
    alone is too generous here: `Low Profiles T65` and `Low Profiles T 66S` share their
    whole range name, which on a two-word range is already half the bag — enough to
    reach the threshold on the strength of being siblings. But a layout code is the one
    part of a product's name that is *meant* to be unique within its range, so two
    products whose codes disagree are two products, however alike the rest reads.
    """
    right_tokens = _identity_tokens(right.manufacturer_range, right.model)
    identities = {
        (left.manufacturer_range, left.model),
        renames.applied_to(left.manufacturer_range, left.model),
    }
    return max(
        _jaccard(_identity_tokens(*identity), right_tokens) for identity in identities
    )


def _jaccard(left_tokens: frozenset[str], right_tokens: frozenset[str]) -> float:
    """The score for one pair of token bags, before any renaming."""
    union = left_tokens | right_tokens
    if not union:
        return 0.0

    left_codes, right_codes = _codes(left_tokens), _codes(right_tokens)
    if left_codes and right_codes and not (left_codes & right_codes):
        return 0.0

    return len(left_tokens & right_tokens) / len(union)


def _tie_break(baseline: Product) -> tuple[int, int]:
    """Sort key preferring the *live, current* row when several score identically.

    An FMLV export holds a manufacturer's history, not just its current line-up: the
    Sunlight baseline carries `Coachbuilts A60` twice, as archived 2022 product 3524 and
    live 2026 product 6562. Both are the same layout and both score identically against
    a scraped `Coachbuilts Root A 60`, so without a tie-break the winner is whichever
    the export happened to list first — and a model-year update would land on the dead
    row while the live one drifted out of date.

    Sorted ascending, so lower is better: not-archived before archived, then the newest
    year first.
    """
    return (1 if baseline.archived else 0, -(baseline.year or 0))


@dataclass(frozen=True)
class MatchResult:
    """The outcome of matching one scraped product against the baseline.

    `baseline is None` means no candidate reached the threshold — treat as new
    (DESIGN.md §4.1: a genuinely new product is submitted with `product_id` blank).
    """

    extracted: ExtractedProduct
    baseline: Product | None
    baseline_index: int | None
    score: float
    method: str | None  # "exact" | "fuzzy" | None


def match_products(
    scraped: Iterable[ExtractedProduct],
    baseline: Iterable[Product],
    *,
    threshold: float = DEFAULT_THRESHOLD,
    renames: Renames = NO_RENAMES,
) -> list[MatchResult]:
    """Match every scraped product to at most one baseline product, and vice versa.

    A greedy highest-score-first assignment: candidate (scraped, baseline) pairs are
    scored, sorted best-first, and each is accepted only if neither side has already
    been claimed by a better-scoring pair. This is a one-to-one matching, not a
    threshold-only lookup — it stops two similarly-named scraped products both
    claiming the same baseline row.

    Equal scores are broken by `_tie_break`: an export routinely holds the same layout
    more than once, and the live row is the one an update belongs on.
    """
    scraped_list = list(scraped)
    baseline_list = list(baseline)

    candidates: list[tuple[float, tuple[int, int], int, int]] = []
    for s_idx, extracted in enumerate(scraped_list):
        for b_idx, baseline_motorhome in enumerate(baseline_list):
            score = token_similarity(
                extracted.product, baseline_motorhome, renames=renames
            )
            if score > 0:
                candidates.append((score, _tie_break(baseline_motorhome), s_idx, b_idx))

    # Best score first, then the tie-break, then insertion order (scraped-index then
    # baseline-index ascending) so results are deterministic run to run.
    candidates.sort(
        key=lambda candidate: (-candidate[0], candidate[1], candidate[2], candidate[3])
    )

    matched_scraped: dict[int, tuple[int, float]] = {}
    used_baseline: set[int] = set()
    for score, _tie, s_idx, b_idx in candidates:
        if score < threshold:
            break
        if s_idx in matched_scraped or b_idx in used_baseline:
            continue
        matched_scraped[s_idx] = (b_idx, score)
        used_baseline.add(b_idx)

    results: list[MatchResult] = []
    for s_idx, extracted in enumerate(scraped_list):
        match = matched_scraped.get(s_idx)
        if match is None:
            results.append(
                MatchResult(
                    extracted=extracted,
                    baseline=None,
                    baseline_index=None,
                    score=0.0,
                    method=None,
                )
            )
            continue
        b_idx, score = match
        method = "exact" if score == 1.0 else "fuzzy"
        results.append(
            MatchResult(
                extracted=extracted,
                baseline=baseline_list[b_idx],
                baseline_index=b_idx,
                score=score,
                method=method,
            )
        )
    return results


def stale_renames(
    scraped: Iterable[ExtractedProduct],
    baseline: Iterable[Product],
    renames: Renames,
) -> list[str]:
    """Rename entries that did nothing this run, worded for `on_progress`.

    **A rename is meant to stop being needed.** The usual end of one is that the name is
    corrected in FMLV, at which point the entry is not merely useless but actively
    misleading: it claims a row is called something FMLV no longer calls it, and the next
    person reading the adapter believes it. Auto-Sleepers' transposed `FG365`/`FG635`
    codes were a live example that FMLV has since fixed.

    Two ways to be dead, and both are reported rather than assumed harmless:

    * **the site no longer publishes the name being renamed** — the manufacturer moved on
      again, or the entry was written against a spelling the adapter does not produce;
    * **FMLV no longer holds the old name** — the row has been corrected, which is the
      outcome the rename was buying time for.

    Nothing is dropped or corrected automatically. A stale entry is a note for a person,
    not a fault: deleting it is a code change and belongs in a commit, not in a run.
    """
    scraped_names = {
        (_key(item.product.manufacturer_range), _key(item.product.model))
        for item in scraped
    }
    scraped_ranges = {manufacturer_range for manufacturer_range, _model in scraped_names}
    baseline_names = {
        (_key(product.manufacturer_range), _key(product.model)) for product in baseline
    }
    baseline_ranges = {manufacturer_range for manufacturer_range, _model in baseline_names}

    notes: list[str] = []
    for scraped_range, fmlv_range in renames.ranges.items():
        if _key(scraped_range) not in scraped_ranges:
            notes.append(
                f"the rename of range '{scraped_range}' to '{fmlv_range}' did nothing: "
                f"nothing collected this run is in a range called '{scraped_range}'"
            )
        elif _key(fmlv_range) not in baseline_ranges:
            notes.append(
                f"the rename of range '{scraped_range}' to '{fmlv_range}' did nothing: "
                f"the baseline holds no range called '{fmlv_range}', so FMLV has probably "
                f"been corrected and this entry can be deleted"
            )
    for (scraped_range, scraped_model), (fmlv_range, fmlv_model) in renames.models.items():
        if (_key(scraped_range), _key(scraped_model)) not in scraped_names:
            notes.append(
                f"the rename of '{scraped_range} {scraped_model}' to '{fmlv_range} "
                f"{fmlv_model}' did nothing: nothing collected this run is called "
                f"'{scraped_range} {scraped_model}'"
            )
        elif (_key(fmlv_range), _key(fmlv_model)) not in baseline_names:
            notes.append(
                f"the rename of '{scraped_range} {scraped_model}' to '{fmlv_range} "
                f"{fmlv_model}' did nothing: the baseline holds no '{fmlv_range} "
                f"{fmlv_model}', so FMLV has probably been corrected and this entry can "
                f"be deleted"
            )
    return notes
