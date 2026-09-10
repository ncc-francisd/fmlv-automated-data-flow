"""Bürstner (buerstner.com) — the eleventh adapter, motorhomes and campervans.

See `docs/adapters/burstner.md` for the full write-up. Bürstner is an Erwin Hymer Group
brand — like Etrusco, non-core to the UK market — but unlike Etrusco the UK-relevant data
is not on a `/gb/en/` path of the manufacturer's own catalogue pages. It is on the parent
site's **GB market edition**, `buerstner.com/gb`, and lives in five per-range "Prices &
Technical Data" PDFs rather than in HTML:

    594 TD 644 TD 684 TD 690 TD
    Price                                     80,795.-  82,495.-  80,995.-  79,995.-
    Overall length (approx. cm)               599       699       689       699
    Technically permissible maximum
      laden mass (kg)*                        3500      3650      3650      3500
    Mass in running order (kg) (+/-5%)*    3056 (2903 to 3209)*  3196 (3036 to 3356)* ...
    Permitted number of seats
      (including driver)*                     4         4         4         4
    Sleeping berths standard / max.           2 - 4     2 - 4     2 - 4     2 - 5

Two things this shape needs that Auto-Trail's whole-page-per-model documents do not:

* **Column attribution.** Every layout in a range sits in its own column of one shared
  table, so a label's value-run has to be sliced to the right column count and matched to
  the right layout — the risk `morelo.py` and `sunlight.py` exist to manage. Checked here:
  `extract_positioned_text` on this document's tables shows real pypdf reading order
  already matches left-to-right column order (nearly every value run reports `(0, 0)`,
  meaning pypdf could not place it at all — but the handful of runs it *could* place, e.g.
  the header names and the wrapped mass-tolerance bands, confirm reading order is correct
  where it can be checked). So this adapter reads columns in plain reading order rather
  than sorting by x, and instead defends itself the way `auto_trail.py` and `morelo.py`
  both do: **a row whose column count does not match the header's is dropped for the
  whole table** rather than guessed at.
* **Discovering three of the five PDFs at all.** Only the two B66 documents are linked
  from their family pages; Signature (both chassis) and Habiton are not linked from
  anywhere found on the site. Their URLs are the same predictable shape as the two linked
  ones, differing only in the trailing slug, so the dated folder segment is read out of a
  linked B66 URL and reused to build the other three — see `_discover_document_urls`.

**`body_type` is derived from the published width**, which is the one measurement here
that separates a converted panel van (2040-2080mm) from a coachbuilt body (2300-2350mm);
see `body_type_for`. It was deliberately left unset until 27 August 2026, because FMLV's
baseline holds two Bürstner classifications that no rule derivable from the source
reproduces, and proposing a "correction" to a record that was actually right is worse than
an honest gap. The requester then confirmed both are FMLV's own errors — B66 TD 744 is a
low profile, not an `a_class`, and B66 C 644 is a plain high top with no elevating roof as
standard — so the field is now filled and those two are proposed rather than left for a
manual edit. Against the real baseline the rule confirms 11 of 13 and proposes exactly
those 2.

One thing this adapter deliberately does **not** attempt:

* **The overview page's range-level "from" price.** It is not read at all — see the
  module-level `_PRICE_SOURCE_NOTE`.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..fetch.http import Fetcher
from ..fetch.pdf import extract_text
from ..product_model.enums import BodyType, Refrigeration
from ..product_model.model import Motorhome
from . import ehg_configurator
from . import habitation
from .base import (
    ExtractedMotorhome,
    Provenance,
    floorplan_provenance,
    fmlv_base_vehicle,
)

BASE_URL = "https://www.buerstner.com"
MANUFACTURER = "Bürstner"
MANUFACTURER_DISPLAY_NAME = "Bürstner"

#: The two documents that are actually linked in HTML, and where to find the link.
#: Their own `href` supplies the dated folder segment (e.g. `26-08-17-uk`) that the
#: other three documents share but never state anywhere themselves.
_B66_MOTORHOMES_PAGE = f"{BASE_URL}/gb/b66/motorhomes"
_B66_CAMPERVANS_PAGE = f"{BASE_URL}/gb/b66/vans"

#: `(page URL, document key)` for the two pages whose own PDF link is read directly.
_LINKED_DOCUMENT_PAGES: tuple[tuple[str, str], ...] = (
    (_B66_MOTORHOMES_PAGE, "b66-td"),
    (_B66_CAMPERVANS_PAGE, "b66-c"),
)

#: One `Prices & Technical Data` PDF's own link, e.g.
#: `/buerstner/01-relaunch-2025/technische-daten/26-08-17-uk/buerstner-technical-data-2027-b66-td-gb.pdf`.
#: The middle group is the dated folder; the last is the document's own slug, read so the
#: link can be told apart from any other PDF a future redesign might add to the page.
_DOCUMENT_HREF = re.compile(
    r'href="(/buerstner/01-relaunch-2025/technische-daten/([^/"]+)'
    r'/buerstner-technical-data-2027-([a-z0-9-]+)-gb\.pdf)"'
)

#: Bürstner's own range/model naming, read from a real FMLV export for id 65 (26 active
#: products, `fmlv fetch-export` against `ncc_supplier_name` "Bürstner", confirmed the
#: same string as `fmlv_manufacturer` including the umlaut). FMLV holds B66 Motorhomes and
#: B66 Campervans as ONE range, `B66`, distinguished only by the model's `TD`/`C` prefix —
#: matching the site's own single B66 branding rather than its two separate URLs — and
#: Habiton and Habiton X collapse the same way into one range, `Habiton`, distinguished by
#: `HM`/`HMX`. Signature is assumed to follow the same pattern for `SFT`/`SMT`, though no
#: SMT row exists in the baseline yet to confirm it directly.
#:
#: `token_order` says which way the document prints a layout code: B66's tables print
#: `594 TD` (number first), but FMLV holds `TD 594` — Signature and Habiton already print
#: `SFT 7.0` / `HM 6.0`, which is FMLV's order already, so only B66 needs its two tokens
#: reversed. See `_canonical_model`.
@dataclass(frozen=True)
class _DocumentConfig:
    key: str
    range_label: str
    token_order: str  # "number_first" | "letter_first"
    base_vehicle_manufacturer: str
    #: Whether this document's seats row is a type-approval ceiling that overstates the
    #: belted seats actually fitted as standard. See `_SEATS_ARE_A_CEILING_NOTE`.
    seats_overstate_standard: bool = False


DOCUMENTS: tuple[_DocumentConfig, ...] = (
    _DocumentConfig("b66-td", "B66", "number_first", "Fiat"),
    _DocumentConfig("b66-c", "B66", "number_first", "Fiat"),
    _DocumentConfig(
        "signature-sft", "Signature", "letter_first", "Fiat", seats_overstate_standard=True
    ),
    _DocumentConfig(
        "signature-smt", "Signature", "letter_first", "Mercedes", seats_overstate_standard=True
    ),
    _DocumentConfig(
        "habiton", "Habiton", "letter_first", "Mercedes", seats_overstate_standard=True
    ),
)

#: Why `mh_passenger_seats_inc_driver` is **not** filled for Signature or Habiton.
#:
#: "Permitted number of seats (including driver)" is a **type-approval ceiling**, not a
#: count of belted seats fitted as standard — footnote 3 of every document says it is
#: "determined by the manufacturer in what is referred to as the type-approval
#: procedure". Reading its lower bound as the standard figure works for B66 and fails
#: for these two ranges, and the FMLV baseline is what shows it failing:
#:
#:     range              published   FMLV holds
#:     B66 TD / C         4           4  (all seven)  <- agree
#:     Signature SFT      4 - 5       2  (7.0, 7.4, 7.5), 4 (7.1)
#:     Habiton HM / HMX   4           2  (both 6.0)
#:
#: The Signature ranges have a face-to-face lounge with no belted rear seats as
#: standard; the belted seats come from an equipment item, "Sofa convertible to L-shaped
#: bench (4 belted seats in total)". That item appears in the SFT document's own
#: per-layout standard-equipment table — but the table marks availability with glyphs
#: that `extract_text` drops, leaving only the legend ("Standard equipment / Not
#: possible"), so **the document cannot say which layouts have it**. FMLV holding 4 for
#: SFT 7.1 alone is consistent with it being standard on that layout only. The SMT
#: document does not mention the bench at all, yet still publishes `4 - 5`.
#:
#: So the field is left unset for both ranges rather than proposed: an existing record
#: keeps its own value, and a new layout surfaces as a `missing_required` gap for a
#: reviewer to fill from the equipment list or from EHG. The published figure is still
#: narrated on every run so the gap is visible and not silent.
#:
#: Found 27 August 2026 when the requester challenged the figure and a colleague's
#: source independently said two belted seats as standard, "up to 4 or 5 by adding
#: Bürstner's rotating/convertible bench" — which is the same equipment item, from an
#: unrelated source. Run #11 had proposed 2 -> 4 on all five affected products.
_SEATS_ARE_A_CEILING_NOTE = (
    "Bürstner publish a type-approval ceiling ('permitted number of seats'), not the "
    "belted seats fitted as standard, and this range's belted rear seats come from an "
    "equipment item whose per-layout availability the document does not state in "
    "extractable form"
)

#: A layout code as each document order prints it. Letters are 2-4 chars (`C`, `TD`,
#: `HM`, `HMX`, `SFT`, `SMT`); the number carries an optional one-decimal-place suffix
#: (`7.0`, `6.1`).
_TOKEN = {
    "number_first": re.compile(r"\d+(?:\.\d+)?\s+[A-Z]{1,4}"),
    "letter_first": re.compile(r"[A-Z]{2,4}\s+\d+(?:\.\d+)?"),
}

#: A header *line* — the whole line is one or more layout codes and nothing else, which
#: is what lets this be told apart from a labelled row: no labelled row in these
#: documents is all-caps-and-digits with no lowercase letters anywhere.
_HEADER_LINE = {
    order: re.compile(rf"^(?:{token.pattern}\s*)+$", re.MULTILINE)
    for order, token in _TOKEN.items()
}

#: The overview page's range-level "from" price is deliberately never read. It is not a
#: price for any specific layout — Signature and Habiton publish no per-layout price
#: anywhere else in HTML, so there is nothing for it to conflict with in the way B66's
#: page-level floorplan price list does — and against the real FMLV baseline it tracks
#: neither an ordinary annual increase (B66's ~5%) nor the larger Signature/Habiton one
#: (~20-30%). Requester's decision, 2026-08-19: the per-layout PDF price is the only
#: price that means anything for a specific model, so it is what this adapter uses.
_PRICE_SOURCE_NOTE = (
    "the per-layout price from Bürstner's own 'Prices & Technical Data' PDF, not the "
    "model-overview page's range-level 'from' price, which is not a per-model figure"
)

#: One label this adapter reads, and how to read it. `field` is `None` for a label that
#: exists only to mark where the *previous* label's value-run ends — `docs/adapters/
#: README.md`'s rule of stopping at the next row's label, generalised to N columns
#: instead of one. `kind` selects the extractor in `_extract`.
_LABELS: tuple[tuple[str, str | None, str], ...] = (
    ("Price", "rrp_pounds", "price"),
    ("Overall length (approx. cm)", "mh_length_mm", "cm"),
    ("Overall width (approx. cm)", "mh_width_mm", "cm"),
    ("Overall height (approx. cm)", "mh_height_mm", "cm"),
    ("Headroom (approx. cm)", None, "boundary"),
    ("Technically permissible maximum laden mass (kg)", "mtplm_kilograms", "int"),
    ("Mass in running order (kg) (+/-5%)", "mro_kilograms", "mro_band"),
    ("Manufacturer-specified mass for optional equipment (approx. kg)", None, "boundary"),
    ("Technically permissible maximum towable mass (kg)", None, "boundary"),
    ("Total weight gross vehicle (approx. kg)", None, "boundary"),
    ("Wheelbase (approx. mm)", None, "boundary"),
    ("Drive", None, "boundary"),  # Habiton only
    ("Permitted number of seats (including driver)", "mh_passenger_seats_inc_driver", "range_or_int"),
    ("Sleeping berths standard / max.", "berths", "range_or_int"),
    ("Bed size centre (approx. cm)", None, "boundary"),
    ("Fold down bed (approx. cm)", None, "boundary"),
    ("Bed size rear (approx. cm)", None, "boundary"),
    ("Fold down bed rear (approx. cm)", None, "boundary"),
    ("Sleeping roof (approx. cm)", None, "boundary"),
    ("Refrigerator volume incl. freezer (approx. l)", None, "boundary"),
    ("Fresh water supply (approx. l)", None, "boundary"),
)

#: Slack allowed on the printed mass-in-running-order tolerance band, in kg, for rounding
#: — the same allowance `etrusco.py` uses for the identical device.
_MRO_BAND_SLACK_KG = 3

#: The priced accessory that buys the *upper* figure in a `4 - 5` seats row: an extra
#: belted seat. Present in both Signature documents (part 793011, in the `Accessories`
#: table beside a price and an added weight), absent from B66's and Habiton's.
#:
#: This is what settles a question the row's own label cannot: "Permitted number of
#: seats (including driver)" is a **type-approval maximum** — footnote 3 says it is
#: "determined by the manufacturer in what is referred to as the type-approval
#: procedure" and is what the 75kg-per-passenger mass calculation uses — so `4 - 5`
#: could in principle mean five seats are fitted as standard. It does not: the fifth is
#: an option, and the document warns that "increasing the number of seatbelt-secured
#: seats" deducts a further 85kg per seat from the special-equipment allowance.
#: Recording the lower figure is therefore the base-vehicle figure, per
#: `docs/adapters/README.md`, and this pattern is what lets the snippet say so.
_EXTRA_BELTED_SEAT = re.compile(
    r"Additional\s+seat\s+secured\s+with\s+a\s+seatbelt", re.IGNORECASE
)

#: A campervan taller than this is a high top. The same threshold as
#: `auto_trail.HIGH_TOP_ABOVE_MM`, set by the NCC side on 16 August 2026.
HIGH_TOP_ABOVE_MM = 2300

#: A body no wider than this is a converted panel van; anything wider is a coachbuilt
#: body. **Width, not height, is what separates the two here** — and it is the one
#: measurement in these documents that does the job cleanly:
#:
#:     2040-2080mm   Habiton HM/HMX, B66 C     panel van
#:     2300-2350mm   B66 TD, Signature SFT/SMT coachbuilt body
#:
#: Checked against the real FMLV baseline export 27 August 2026: this rule reproduces
#: FMLV's own classification on **11 of the 13** products it holds, and the two it
#: contradicts are both confirmed FMLV errors (see the `body_type` section of
#: `docs/adapters/burstner.md`). Height cannot be used for this: FMLV's own stored
#: heights are unusable (Habiton 1900mm, Signature 1980mm — headroom, not overall) and
#: the documents' real heights overlap heavily between the two families (campervans
#: 2650-2850mm against coachbuilts 2800-2990mm).
_CAMPERVAN_WIDTH_AT_MOST_MM = 2100

#: The base vehicle as each document's own engine list names it, e.g.
#: `Fiat Ducato Multijet 3 - 2.2l - 140 hp - Euro 6E` or
#: `Mercedes Benz Sprinter 4,5 t - 417 CDI`. Anchored to the base vehicle's own model
#: name rather than just the make, because the make alone appears all over these
#: documents on things that are not chassis — the Habiton document carries `Mercedes
#: Comfort Seats` and `Mercedes emergency call system` in its equipment lists, and the
#: first of those sits only 34 lines from the real chassis line.
_CHASSIS_LINE = re.compile(
    r"^(?:Fiat\s+Ducato|Mercedes[\s-]+Benz\s+(?:4wd\s+)?Sprinter)[^\n]*", re.MULTILINE
)

#: The chassis line's own opening word -> the make as the document itself names it.
#: `fmlv_base_vehicle` then maps that onto FMLV's spelling, so `Mercedes Benz` becomes
#: `Mercedes` in one place shared with every other adapter rather than here.
_CHASSIS_MAKES: tuple[tuple[str, str], ...] = (
    ("fiat", "Fiat"),
    ("mercedes", "Mercedes Benz"),
)


def _label_pattern(label: str) -> re.Pattern[str]:
    """A label as printed, tolerant of the mid-label line wrap these PDFs use.

    `extract_text` renders `Technically permissible maximum laden\\nmass (kg)*` with a
    real newline where the PDF wrapped the row header, so every space in the label
    becomes `\\s+` rather than a literal space.
    """
    words = label.split()
    return re.compile(r"\s+".join(re.escape(word) for word in words))


def _canonical_model(token: str, order: str) -> str:
    """A layout code in FMLV's order: letters first, e.g. `594 TD` -> `TD 594`.

    Signature's and Habiton's documents already print letters first (`SFT 7.0`,
    `HM 6.0`), so this is a no-op for them beyond whitespace normalisation.
    """
    parts = token.split()
    if order == "number_first":
        number, letters = parts
    else:
        letters, number = parts
    return f"{letters} {number}"


def _find_blocks(text: str, order: str) -> list[tuple[tuple[str, ...], str]]:
    """`(layout codes, block text)` for every distinct table in one document.

    A table can repeat its header across a page break to continue with rows this adapter
    does not need (bed sizes, water capacities) — only the **first** occurrence of a
    given set of layout codes is kept, so a continuation page never overwrites the block
    that actually carries price and weight.
    """
    headers = list(_HEADER_LINE[order].finditer(text))
    seen: set[tuple[str, ...]] = set()
    blocks: list[tuple[tuple[str, ...], str]] = []
    for index, header in enumerate(headers):
        tokens = _TOKEN[order].findall(header.group(0))
        codes = tuple(_canonical_model(token, order) for token in tokens)
        if codes in seen:
            continue
        seen.add(codes)
        block_end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        blocks.append((codes, text[header.end() : block_end]))
    return blocks


def _extract(kind: str, value_run: str, count: int) -> list[object | None]:
    """One label's values across `count` columns, or `count` `None`s if they don't line up.

    Never guesses at a partial match — a value-run yielding the wrong number of figures
    means a row wrapped unexpectedly or a footnote mark was swept in with the numbers,
    and the whole row is safer left blank than attributed to the wrong column. This is
    the same defence `morelo.py`'s `_row_values` and `auto_trail.py`'s block-count check
    both use, generalised to however many columns a table has.
    """
    empty: list[object | None] = [None] * count
    if kind in ("price", "int", "cm"):
        # Where a manufacturer publishes two figures for one column — Bürstner does
        # this for a dual roof height, `265 / 275` — the base-vehicle rule in
        # `docs/adapters/README.md` takes the first (base) figure and drops the second,
        # the same way `auto_trail.py`'s `_millimetres` does for `3030/3106mm`.
        collapsed = re.sub(r"(\d[\d,]*)\s*/\s*\d[\d,]*", r"\1", value_run)
        numbers = re.findall(r"\d[\d,]*", collapsed)
        if len(numbers) != count:
            return empty
        values = [int(number.replace(",", "")) for number in numbers]
        return [value * 10 for value in values] if kind == "cm" else values
    if kind == "mro_band":
        triples = re.findall(r"(\d[\d,]*)\s*\(\s*(\d[\d,]*)\s*to\s*(\d[\d,]*)\)", value_run)
        if len(triples) != count:
            return empty
        return [
            (int(mass.replace(",", "")), int(lo.replace(",", "")), int(hi.replace(",", "")))
            for mass, lo, hi in triples
        ]
    if kind == "range_or_int":
        # A row can mix a plain figure in one column with a range in another —
        # Habiton's seats row is `4   3 - 4` for its two columns — so each token is
        # matched as "a number, optionally followed by '- a number'" rather than
        # requiring every column in the row to be the same shape.
        tokens = re.findall(r"\d+(?:\s*-\s*\d+)?", value_run)
        if len(tokens) != count:
            return empty
        parsed: list[object | None] = []
        for token in tokens:
            if "-" in token:
                lo, _hi = re.split(r"\s*-\s*", token)
                parsed.append((int(lo), re.sub(r"\s+", " ", token)))
            else:
                parsed.append((int(token), token))
        return parsed
    return empty


def published_chassis(text: str) -> tuple[str, str] | None:
    """`(make, the line as printed)` for the base vehicle one document names, or `None`.

    Every one of the five documents names its chassis in an engine/`Chassis Equipment`
    list rather than in the layout table, so this is a **document-level** fact, not a
    per-column one — which is why it is read once per document and shared by every
    layout in it, unlike everything `_extract` handles.

    `None` when no line matches, which is not a failure: the per-range make in
    `DOCUMENTS` then stands on its own, as it did before this was read at all.
    """
    match = _CHASSIS_LINE.search(text)
    if match is None:
        return None
    line = re.sub(r"\s+", " ", match.group(0)).strip(" -–")
    lowered = line.lower()
    for prefix, make in _CHASSIS_MAKES:
        if lowered.startswith(prefix):
            return fmlv_base_vehicle(make), line
    return None


def body_type_for(width_mm: int | None, height_mm: int | None) -> BodyType | None:
    """FMLV's body type for one layout, from its own published width and height.

    `None` when the width is missing — the family cannot be told apart without it, and a
    guess here would propose a wrong classification onto an existing product, which is
    what kept this field unset until 27 August 2026.

    **Campervans are `campervan_high_top`, never the elevating-roof variant.** Bürstner's
    own B66 van page prices the pop-up roof as an accessory — "Pop-up roof in Lanzarote
    Grey £420" — and describes it as "optionally available", so it is not standard on any
    layout. FMLV holding `campervan_high_top_elevating_roof` for `C 644` was confirmed by
    the requester on 27 August 2026 to be an error; the roof is optional across the range.

    **Coachbuilts are `coach_built_low_profile`, never A-class or over-cab.** Bürstner's
    B66 range nav offers exactly two categories, `Semi-integrated` and `Camper Vans`, and
    "A class" appears nowhere in either page's visible text; TD 744, which FMLV held as
    `a_class`, is listed on the Semi-integrated page beside its four siblings and is the
    same 2300mm width as all of them. Also confirmed an FMLV error by the requester. The
    beds these documents publish are `Fold down bed` rows — a drop-down over the lounge,
    not an over-cab bed, which is the other classification this could have been.
    """
    if width_mm is None:
        return None
    if width_mm <= _CAMPERVAN_WIDTH_AT_MOST_MM:
        if height_mm is None:
            return None  # a van whose roof height is unknown could be either
        return (
            BodyType.CAMPERVAN_HIGH_TOP
            if height_mm > HIGH_TOP_ABOVE_MM
            else BodyType.CAMPERVAN
        )
    return BodyType.COACH_BUILT_LOW_PROFILE


def _band_reconciles(band: tuple[int, int, int] | None) -> bool:
    """Whether a mass-in-running-order figure agrees with its own printed ±5% band.

    The same device Etrusco and Sunlight publish: `2903 = round(3056 x 0.95)` and
    `3209 = round(3056 x 1.05)`. A slipped column pairs one layout's mass with another's
    band, which this catches; `_MRO_BAND_SLACK_KG` allows for Bürstner's own rounding.
    """
    if band is None:
        return True
    mass, lo, hi = band
    return (
        abs(lo - mass * 0.95) <= _MRO_BAND_SLACK_KG
        and abs(hi - mass * 1.05) <= _MRO_BAND_SLACK_KG
    )


@dataclass(frozen=True)
class BurstnerProduct:
    """One layout, read from one column of one range's technical-data table."""

    range_label: str
    model: str
    base_vehicle_manufacturer: str
    rrp_pounds: int | None = None
    mh_length_mm: int | None = None
    mh_width_mm: int | None = None
    mh_height_mm: int | None = None
    mtplm_kilograms: int | None = None
    mro_kilograms: int | None = None
    #: The published `standard - max` string, e.g. `'2 - 4'`, kept for the provenance
    #: snippet — `berths` and `mh_passenger_seats_inc_driver` record the standard
    #: (lower) figure per `docs/adapters/README.md`, and a reviewer needs to see what
    #: that number was read out of.
    berths: int | None = None
    berths_published: str | None = None
    mh_passenger_seats_inc_driver: int | None = None
    seats_published: str | None = None
    #: The base vehicle line as this layout's document prints it, e.g. `Fiat Ducato
    #: Multijet 3 - 2.2l - 140 hp - Euro 6E`. `None` when the document names none, in
    #: which case `base_vehicle_manufacturer` is the per-range make from `DOCUMENTS`
    #: alone and the provenance snippet says so.
    base_vehicle_published: str | None = None
    #: Set only when the document's own chassis line contradicts the per-range make in
    #: `DOCUMENTS` — carries the make that was expected, for the snippet to flag.
    base_vehicle_expected: str | None = None
    #: Whether this layout's seats row is a type-approval ceiling rather than the belted
    #: seats fitted as standard. When set, `mh_passenger_seats_inc_driver` is deliberately
    #: `None` even though `seats_published` has a figure — see `_SEATS_ARE_A_CEILING_NOTE`.
    seats_overstate_standard: bool = False
    #: Whether this layout's document sells an extra belted seat as a priced accessory,
    #: which is what the upper figure of a `4 - 5` seats row costs. `False` does not mean
    #: the upper figure is standard — only that this document does not price it.
    extra_belted_seat_optional: bool = False
    #: The whole document's lines, for the habitation findings. **Document-wide, not
    #: per column**, which is the whole reason so little is reported from them — see
    #: `_habitation_findings`.
    document_lines: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        return f"{self.range_label} {self.model}"

    @property
    def mh_payload_kilograms(self) -> int | None:
        if self.mtplm_kilograms is None or self.mro_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mro_kilograms

    @property
    def body_type(self) -> BodyType | None:
        return body_type_for(self.mh_width_mm, self.mh_height_mm)


def parse_document(text: str, config: _DocumentConfig) -> tuple[list[BurstnerProduct], int]:
    """Every layout in one document, and how many candidate tables were found.

    Returns the count of tables found (before any self-check drops) alongside the
    products, so `collect` can narrate a table that yielded zero usable layouts
    separately from a document with no tables at all.
    """
    blocks = _find_blocks(text, config.token_order)

    # The chassis is named once per document, not per column, so it is read here and
    # shared by every layout below. The document over-rules the per-range make in
    # `DOCUMENTS` when the two disagree — `docs/adapters/README.md`'s rule that the
    # manufacturer's own current publication wins — and the make it displaced is kept
    # so the snippet can tell a reviewer the two did not agree.
    document_lines = tuple(
        stripped for line in text.splitlines() if (stripped := line.strip())
    )
    extra_seat_optional = _EXTRA_BELTED_SEAT.search(text) is not None
    chassis = published_chassis(text)
    base_vehicle = chassis[0] if chassis else config.base_vehicle_manufacturer
    published_line = chassis[1] if chassis else None
    expected = (
        config.base_vehicle_manufacturer
        if chassis and chassis[0] != config.base_vehicle_manufacturer
        else None
    )

    products: list[BurstnerProduct] = []
    for codes, block in blocks:
        count = len(codes)
        matches = []
        for label, field, kind in _LABELS:
            match = _label_pattern(label).search(block)
            if match:
                matches.append((match.start(), match.end(), field, kind))
        matches.sort(key=lambda item: item[0])

        values: dict[str, list[object | None]] = {}
        for index, (_start, end, field, kind) in enumerate(matches):
            if field is None:
                continue
            next_start = matches[index + 1][0] if index + 1 < len(matches) else len(block)
            values[field] = _extract(kind, block[end:next_start], count)

        # A layout-code line can appear more than once for reasons other than
        # continuing this table — Bürstner's own equipment-comparison chart repeats
        # every code in one row with no Price or weight anywhere near it. A block
        # where every tracked field came back empty is that, not a second copy of the
        # real table, so it contributes no products rather than N empty ones.
        if not any(value is not None for column in values.values() for value in column):
            continue

        for column, model in enumerate(codes):
            band = values.get("mro_kilograms", [None] * count)[column]
            if not _band_reconciles(band):
                # mro_kilograms=-1 is a sentinel, never a real value: collect() checks
                # for it and narrates + drops the product rather than proposing it.
                products.append(
                    BurstnerProduct(
                        range_label=config.range_label,
                        model=model,
                        base_vehicle_manufacturer=base_vehicle,
                        mro_kilograms=-1,
                    )
                )
                continue
            seats_pair = values.get("mh_passenger_seats_inc_driver", [None] * count)[column]
            berths_pair = values.get("berths", [None] * count)[column]
            products.append(
                BurstnerProduct(
                    range_label=config.range_label,
                    model=model,
                    base_vehicle_manufacturer=base_vehicle,
                    base_vehicle_published=published_line,
                    base_vehicle_expected=expected,
                    extra_belted_seat_optional=extra_seat_optional,
                    rrp_pounds=values.get("rrp_pounds", [None] * count)[column],
                    mh_length_mm=values.get("mh_length_mm", [None] * count)[column],
                    mh_width_mm=values.get("mh_width_mm", [None] * count)[column],
                    mh_height_mm=values.get("mh_height_mm", [None] * count)[column],
                    mtplm_kilograms=values.get("mtplm_kilograms", [None] * count)[column],
                    mro_kilograms=band[0] if band is not None else None,
                    mh_passenger_seats_inc_driver=(
                        seats_pair[0]
                        if seats_pair and not config.seats_overstate_standard
                        else None
                    ),
                    seats_published=seats_pair[1] if seats_pair else None,
                    seats_overstate_standard=config.seats_overstate_standard,
                    berths=berths_pair[0] if berths_pair else None,
                    berths_published=berths_pair[1] if berths_pair else None,
                    document_lines=document_lines,
                )
            )
    return products, len(blocks)


#: Bürstner's configurator, which is the Erwin Hymer Group platform every EHG brand runs —
#: see `ehg_configurator`. It is the only source of floorplans that covers the whole UK
#: range: the range pages carry drawings for B66 only, and Signature none at all.
#:
#: The requester found it on 9 September 2026, having opened the configurator by hand:
#: *"you have to click on configurator […] you then get a floor plan and also some more
#: specifications."*
_CONFIGURATOR_PAGE = "/gb/configurator/signature"


def _model_tokens(name: str) -> frozenset[str]:
    """A layout's identity as alphanumeric tokens — `'TD 644'` -> `{'td', '644'}`."""
    return frozenset(token for token in re.split(r"[^a-z0-9]+", name.lower()) if token)


def floorplan_for(model: str, plans: dict[str, str]) -> str | None:
    """One layout's drawing, matched on the **model** alone, or `None`.

    **The range is deliberately not part of the key.** The configurator is the German
    product structure and the UK site renames freely: `B66 644 TD` is filed under a series
    called `Lyseo TD` and published as `Lyseo TD 644 G`, while `B66 644 C` comes from one
    called `Eliseo C`. Matching on the range would fail on five of eight B66 layouts.
    The model's own tokens survive the renaming — `TD 644` is in `Lyseo TD 644 G`, and
    `C 644` is in `B66 644 C` — and they still separate every pair that matters:
    `HM 6.0` does not match `Habiton HMX 6.0`, because `hmx` is not `hm`.
    Verified against all 20 layouts on 9 September 2026: 20 matched, each uniquely.

    An ambiguous match yields `None` rather than a guess. A wrong drawing is worse than
    none — a reviewer reads a layout off it and records it as fact.
    """
    wanted = _model_tokens(model)
    if not wanted:
        return None
    matched = [
        url for name, url in plans.items() if wanted <= _model_tokens(name)
    ]
    return matched[0] if len(matched) == 1 else None


def _fetch_floorplans(
    http: Fetcher, on_progress: Callable[[str], None]
) -> dict[str, str]:
    """`{marketing name: drawing URL}` for the current model year, or `{}`.

    Three requests plus one per series. Everything is discovered rather than hardcoded —
    the brand key and series id come off the configurator page, and the model year is the
    newest the brand publishes — so a renumbered or renamed series cannot silently serve
    last season's layouts. Failures are narrated and never fatal: this supplies pointers a
    reviewer can do without, not values.
    """
    page = http.fetch(f"{BASE_URL}{_CONFIGURATOR_PAGE}")
    if page.status_code != 200:
        on_progress(f"configurator page returned {page.status_code} — no floorplans")
        return {}
    brand_key = ehg_configurator.parse_brand_key(
        page.file_path.read_text(encoding="utf-8", errors="replace")
    )
    if brand_key is None:
        on_progress("no brand key on the configurator page — no floorplans")
        return {}

    index_url = (
        f"{BASE_URL}{ehg_configurator.BRAND_SERIES_PATH.format(brand_key=brand_key)}"
        f"?{ehg_configurator.UK_QUERY}"
    )
    index = http.fetch(index_url)
    if index.status_code != 200:
        on_progress(f"series index returned {index.status_code} — no floorplans")
        return {}
    payload = index.file_path.read_text(encoding="utf-8")

    # The list is cumulative — 44 series back to 2023, names reused across years — so
    # without this the run collects last season's roster. See `ehg_configurator`.
    year = ehg_configurator.latest_model_year(payload)
    series = ehg_configurator.parse_series_index(payload, model_year=year)
    on_progress(f"configurator: {len(series)} series for model year {year}")

    plans: dict[str, str] = {}
    for entry in series:
        models_url = (
            f"{BASE_URL}{ehg_configurator.SERIES_MODELS_PATH.format(series_id=entry.id)}"
            f"?{ehg_configurator.UK_QUERY}"
        )
        response = http.fetch(models_url)
        if response.status_code != 200:
            on_progress(f"series {entry.name} returned {response.status_code}, skipped")
            continue
        for model in ehg_configurator.parse_models(
            response.file_path.read_text(encoding="utf-8")
        ):
            if model.floorplan_url:
                plans[model.marketing_name] = model.floorplan_url
    on_progress(f"configurator: {len(plans)} floorplan(s) found")
    return plans


# --- The habitation findings ---------------------------------------------------------

#: Why so little is reported from a Bürstner document. The standard-equipment pages list
#: a range's whole menu with a tick per column, and **the ticks do not survive the text
#: extraction** — the Habiton page offers both a "90L compressor refrigerator (7L freezer
#: compartment)" and a "Compressor refrigerator, 69 l" with nothing left in the text to
#: say which of HM 6.0 and HM 6.1 gets which. That is the unattributable-spans problem
#: `docs/adapters/README.md` warns about, and the honest response is to report only what
#: is true of every layout in the document.
_UNATTRIBUTABLE_NOTE = (
    "read from the document as a whole rather than from this layout's column: "
    "Bürstner's standard-equipment pages mark each layout with a tick, and the ticks do "
    "not survive extraction from the PDF"
)

#: The specification row that settles the fridge, and the one habitation fact this
#: document does attribute per column. Its label states the answer on its own — a
#: refrigerator whose volume is quoted *including* a freezer has a freezer — so the row's
#: presence is the finding and the figures in it are the evidence.
_FRIDGE_ROW = re.compile(
    r"^Refrigerator volume incl\. freezer.*$", re.IGNORECASE | re.MULTILINE
)


#: Where a document's standard equipment ends. Everything past it is priced — the
#: `Optional equipment` table and the `Accessories` table that follows it — and reading
#: it as fitted got the Signature's heating exactly backwards: its standard `Heating`
#: section names `Truma Combi 6E gas / electrical`, blown air, and its options table
#: sells `Hot water heating (Diesel) with integrated 10-litre boiler`, wet, under part
#: number 711045. Neither line marks itself; the table heading is the only signal.
_END_OF_STANDARD = re.compile(r"^\s*(?:Optional equipment|Accessories)\s*$")


def standard_lines(lines: tuple[str, ...]) -> tuple[str, ...]:
    """`lines` up to the first priced table, which is where the fitted equipment ends."""
    for index, line in enumerate(lines):
        if _END_OF_STANDARD.match(line):
            return lines[:index]
    return lines


def _habitation_findings(
    lines: tuple[str, ...],
) -> tuple[dict[str, habitation.Feature], str | None]:
    """`({field: Feature}, the unclear-heating line)` for one document.

    Only `heating` and `refrigeration` are taken, and both because they are **range-wide
    facts**: one document is one range built on one chassis with one heater, and the
    fridge row states a freezer whatever the litres. Everything else the equipment pages
    name — the beds above all — varies layout by layout and cannot be attributed, so it
    is left to the drawing.
    """
    found: dict[str, habitation.Feature] = {}
    lines = standard_lines(lines)
    if heater := habitation.heating_from(lines):
        found["heating"] = habitation.Feature(
            heater[0],
            heater[1],
            note=(
                "the heater this document names. One document is one range on one "
                "chassis, and Bürstner fit it one heating system"
            ),
        )
    if row := _FRIDGE_ROW.search("\n".join(lines)):
        found["refrigeration"] = habitation.Feature(
            Refrigeration.FRIDGE_FREEZER,
            row.group(0).strip(),
            note=(
                "the specification's own row, whose label states the answer — a "
                "refrigerator volume quoted *including* the freezer has one. The "
                "litres are per layout, in the table's column order"
            ),
        )
    return found, habitation.heating_is_unclear(lines)


def _build_extracted_motorhome(
    product: BurstnerProduct, source_url: str, floorplan_url: str | None = None
) -> ExtractedMotorhome:
    features, heating_unclear = _habitation_findings(product.document_lines)
    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.range_label,
        model=product.model,
        base_vehicle_manufacturer=product.base_vehicle_manufacturer,
        rrp_pounds=product.rrp_pounds,
        mro_kilograms=product.mro_kilograms,
        mtplm_kilograms=product.mtplm_kilograms,
        mh_payload_kilograms=product.mh_payload_kilograms,
        mh_length_mm=product.mh_length_mm,
        mh_width_mm=product.mh_width_mm,
        mh_height_mm=product.mh_height_mm,
        mh_passenger_seats_inc_driver=product.mh_passenger_seats_inc_driver,
        berths=product.berths,
        body_type=product.body_type,
        # Habitation, from the document as a whole — reported as findings rather than
        # proposed, so the pipeline never writes them. See `_habitation_findings` for
        # why only these two are taken.
        heating=features["heating"].value if "heating" in features else None,
        refrigeration=(
            features["refrigeration"].value if "refrigeration" in features else None
        ),
    )

    provenance: dict[str, Provenance] = {}
    if product.rrp_pounds is not None:
        provenance["rrp_pounds"] = Provenance(
            source_url=source_url,
            snippet=f"{product.label} — Price: £{product.rrp_pounds:,}. Read from {_PRICE_SOURCE_NOTE}.",
        )
    if product.body_type is not None:
        family = (
            "a converted panel van"
            if product.mh_width_mm and product.mh_width_mm <= _CAMPERVAN_WIDTH_AT_MOST_MM
            else "a coachbuilt body"
        )
        if product.body_type in (BodyType.CAMPERVAN_HIGH_TOP, BodyType.CAMPERVAN):
            detail = (
                f"roof {product.mh_height_mm}mm, above the {HIGH_TOP_ABOVE_MM}mm "
                f"high-top threshold. Bürstner price the pop-up roof as an optional "
                f"accessory rather than fitting it as standard, so this is a plain high "
                f"top"
            )
        elif product.range_label == "B66":
            detail = (
                "Bürstner's own B66 range nav offers exactly two categories, "
                "'Semi-integrated' and 'Camper Vans', and 'A class' appears nowhere in "
                "either page - so a B66 coachbuilt is a low profile"
            )
        else:
            detail = (
                f"this range's own page was not read, so the classification rests on the "
                f"width plus the document publishing a 'Fold down bed' (a drop-down over "
                f"the lounge) and no over-cab bed. The same rule reproduces FMLV's "
                f"existing classification for every {product.range_label} layout it "
                f"already holds"
            )
        provenance["body_type"] = Provenance(
            source_url=source_url,
            snippet=(
                f"{product.label} — {product.body_type.value}: Overall width (approx. cm) "
                f"{product.mh_width_mm // 10 if product.mh_width_mm else '?'} means "
                f"{family}; {detail}"
            ),
        )

    if product.base_vehicle_manufacturer is not None:
        if product.base_vehicle_published is None:
            basis = (
                f"the base vehicle every layout in the {product.range_label} range is "
                f"built on — this document names no chassis line of its own"
            )
        elif product.base_vehicle_expected is not None:
            basis = (
                f"read from this document's own chassis list, '"
                f"{product.base_vehicle_published}'. NOTE: the adapter expected "
                f"{product.base_vehicle_expected} for this range, so the range has "
                f"changed chassis or the document has changed shape — do not accept "
                f"this blind"
            )
        else:
            basis = (
                f"read from this document's own chassis list, '"
                f"{product.base_vehicle_published}'"
            )
        provenance["base_vehicle_manufacturer"] = Provenance(
            source_url=source_url,
            snippet=f"{product.label} — {product.base_vehicle_manufacturer}: {basis}",
        )

    numeric_snippets = {
        "mh_length_mm": ("Overall length (approx. cm)", product.mh_length_mm, 10),
        "mh_width_mm": ("Overall width (approx. cm)", product.mh_width_mm, 10),
        "mh_height_mm": ("Overall height (approx. cm)", product.mh_height_mm, 10),
        "mtplm_kilograms": ("Technically permissible maximum laden mass (kg)", product.mtplm_kilograms, 1),
        "mro_kilograms": ("Mass in running order (kg) (+/-5%)", product.mro_kilograms, 1),
    }
    for field, (row_label, value, divisor) in numeric_snippets.items():
        if value is not None:
            provenance[field] = Provenance(
                source_url=source_url,
                snippet=f"{product.label} — {row_label}: {value // divisor if divisor > 1 else value}",
            )
    if product.mh_payload_kilograms is not None:
        provenance["mh_payload_kilograms"] = Provenance(
            source_url=source_url,
            snippet=(
                f"{product.label} — derived: {product.mtplm_kilograms}kg technically "
                f"permissible maximum laden mass - {product.mro_kilograms}kg mass in "
                f"running order = {product.mh_payload_kilograms}kg (not published directly)"
            ),
        )
    if product.seats_overstate_standard:
        # Deliberately NOT registered: registering it with a None value would propose
        # clearing the figure FMLV already holds, which is the opposite of the intent.
        # The published figure reaches a reviewer through `collect`'s narration instead.
        pass
    elif product.seats_published is not None:
        # The label is a type-approval *maximum*, so a range needs explaining: the lower
        # figure is what the vehicle has without options, which is what FMLV records.
        if "-" not in product.seats_published:
            basis = "a single published figure, so standard and maximum are the same"
        elif product.extra_belted_seat_optional:
            basis = (
                f"a range, and the upper figure is optional: this document sells an "
                f"'Additional seat secured with a seatbelt and Isofix (Vario Seat)' as a "
                f"priced accessory, and warns that each added belted seat deducts a "
                f"further 85kg from the special-equipment allowance. "
                f"{product.mh_passenger_seats_inc_driver} is the base-vehicle figure"
            )
        else:
            basis = (
                f"a range, and {product.mh_passenger_seats_inc_driver} is recorded as the "
                f"standard figure per the lower-figure rule — but NOTE this document "
                f"prices no extra belted seat, so what the upper figure costs is not "
                f"stated here; worth confirming with the manufacturer"
            )
        provenance["mh_passenger_seats_inc_driver"] = Provenance(
            source_url=source_url,
            snippet=(
                f"{product.label} — Permitted number of seats (including driver): "
                f"{product.seats_published}. That row is a type-approval maximum, not a "
                f"count of fitted seats ({basis})"
            ),
        )
    if product.berths_published is not None:
        provenance["berths"] = Provenance(
            source_url=source_url,
            snippet=f"{product.label} — Sleeping berths standard / max.: {product.berths_published}",
        )

    for name, feature in features.items():
        provenance[name] = Provenance(
            source_url=source_url,
            snippet=(
                f"{product.label} — {feature.note or _UNATTRIBUTABLE_NOTE}: "
                f"{feature.snippet}"
            ),
        )
    if product.document_lines and "heating" not in features and heating_unclear:
        provenance["heating"] = Provenance(
            source_url=source_url,
            snippet=(
                f"{product.label} — a heater is listed but its kind is not named: "
                f"{heating_unclear}"
            ),
        )
    if product.document_lines:
        # Left unset, so `findings.SILENCE_MEANS` supplies the recommendation and its
        # own wording. These documents price every accessory Bürstner sell, so a
        # microwave that appears in neither the standard nor the accessory tables is
        # not one they offer.
        provenance["microwave"] = Provenance(
            source_url=source_url,
            snippet=(
                f"{product.label} — the word 'microwave' appears nowhere in this "
                f"range's prices-and-technical-data document, which prices every "
                f"accessory Bürstner sell for it"
            ),
        )

    # The positional fields no technical-data table settles — and Bürstner's settle none:
    # every layout field lives in standard-equipment tables whose availability marks are
    # vector graphics rather than text. See docs/adapters/burstner.md.
    if floorplan_url:
        provenance.update(floorplan_provenance(motorhome, floorplan_url, product.label))

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


def find_document_href(html: str) -> tuple[str, str, str] | None:
    """One page's own technical-data PDF link, as `(path, dated folder, document key)`.

    `None` rather than a guess when the page carries no such link — this is what lets
    `build_document_urls` tell "the page changed shape" apart from "this page simply
    doesn't link its own document" (true of three of the five).
    """
    match = _DOCUMENT_HREF.search(html)
    return (match.group(1), match.group(2), match.group(3)) if match else None


def build_document_urls(date_folder: str, linked: dict[str, str]) -> dict[str, str]:
    """Every document's URL: `linked` verbatim, the rest built from `date_folder`.

    `linked` is keyed by document key (`"b66-td"`, `"b66-c"`) to an absolute URL already
    read from a page; any `DOCUMENTS` key missing from it is reconstructed using the
    shared dated-folder segment, which is never guessed — only ever read out of a linked
    document's own URL by `find_document_href`.
    """
    urls = dict(linked)
    for config in DOCUMENTS:
        if config.key not in urls:
            urls[config.key] = (
                f"{BASE_URL}/buerstner/01-relaunch-2025/technische-daten/{date_folder}/"
                f"buerstner-technical-data-2027-{config.key}-gb.pdf"
            )
    return urls


def _discover_document_urls(
    http: Fetcher, on_progress: Callable[[str], None]
) -> dict[str, str]:
    """The five documents' current URLs, three of them reconstructed from the other two.

    Only the B66 pages link their own PDF. Signature (both chassis) and Habiton are not
    linked from any page found on the site — the same unlinked-document risk
    `docs/adapters/README.md` describes for Rimor's catalogue — so their URLs are built
    from the dated folder segment a B66 page's own link reveals. That folder
    (`26-08-17-uk` as surveyed) is what will change between editions; nothing about it is
    guessed, only reused.
    """
    date_folder: str | None = None
    linked: dict[str, str] = {}

    for page_url, key in _LINKED_DOCUMENT_PAGES:
        page = http.fetch(page_url)
        if page.status_code != 200:
            on_progress(f"[{key}] SKIPPED: {page_url} returned {page.status_code}")
            continue
        html = page.file_path.read_text(encoding="utf-8", errors="replace")
        found = find_document_href(html)
        if found is None:
            on_progress(f"[{key}] SKIPPED: no technical-data PDF linked from {page_url}")
            continue
        path, folder, slug = found
        linked[slug] = f"{BASE_URL}{path}"
        date_folder = date_folder or folder

    if date_folder is None:
        msg = (
            f"no technical-data PDF linked from either {_B66_MOTORHOMES_PAGE} or "
            f"{_B66_CAMPERVANS_PAGE} — the site's link format has probably changed"
        )
        raise RuntimeError(msg)

    return build_document_urls(date_folder, linked)


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 — Bürstner needs no JS; see the module docstring
    snapshot_dir: Path,  # noqa: ARG001 — `http` already snapshots into it
    *,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Collect every Bürstner layout from the current per-range technical-data PDFs.

    A document that can't be fetched or parsed is narrated and skipped rather than
    raised, so one range's rebuilt or misnamed PDF doesn't cost the other four.
    """
    on_progress("finding the current technical-data documents...")
    urls = _discover_document_urls(http, on_progress)

    # Once for the manufacturer, not once per document: the configurator is keyed on the
    # brand, and its layouts span all five.
    plans = _fetch_floorplans(http, on_progress)

    results: list[ExtractedMotorhome] = []
    for config in DOCUMENTS:
        url = urls.get(config.key)
        if url is None:
            continue

        on_progress(f"[{config.key}] downloading {url} ...")
        pdf = http.fetch(url)
        if pdf.status_code != 200:
            on_progress(f"[{config.key}] SKIPPED: {url} returned {pdf.status_code}")
            continue

        document = extract_text(pdf.file_path)
        if document.is_empty():
            on_progress(f"[{config.key}] SKIPPED: no extractable text in {url}")
            continue

        products, table_count = parse_document(document.text, config)
        if table_count == 0:
            on_progress(f"[{config.key}] SKIPPED: no layout table recognised in {url}")
            continue

        kept = 0
        for product in products:
            if product.mro_kilograms == -1:
                on_progress(
                    f"[{config.key}] {product.range_label} {product.model} — SKIPPED: "
                    f"mass in running order does not reconcile with its own printed "
                    f"+/-5% band, so this table's columns may be misaligned"
                )
                continue
            if product.seats_overstate_standard and product.seats_published is not None:
                on_progress(
                    f"[{config.key}] {product.label} — mh_passenger_seats_inc_driver "
                    f"LEFT UNSET: the document publishes "
                    f"'{product.seats_published}' but {_SEATS_ARE_A_CEILING_NOTE}. "
                    f"Fill it from the range's equipment list or from EHG"
                )
            results.append(
                _build_extracted_motorhome(
                    product, url, floorplan_url=floorplan_for(product.model, plans)
                )
            )
            kept += 1
        on_progress(f"[{config.key}] {kept} layout(s) collected from {table_count} table(s)")

    on_progress(f"{len(results)} product(s) collected")
    return results
