"""Rapido (rapido-motorhome.co.uk) — French campervans, low-profiles and A-classes.

See `docs/adapters/rapido.md` for the survey. Twenty-nine layouts across six series, and
two documents between them hold every figure FMLV wants:

* the **2027 Technical Guide**, a 32-page Calaméo flipbook, for dimensions, masses,
  registered seats, berths, garage, heating and refrigeration;
* the **comparator** (`comparateur-camping-cars.php`), one plain HTML page whose 29 cards
  carry the roster, the series, the body type and a published length.

The model pages carry equipment prose and a floorplan but **not one weight or dimension**,
so they are read for neither.

**There is no price, and that is a finding rather than a gap.** Rapido publish none — not
in the Technical Guide, not in the 88-page Catalogue, not on any UK page — and unlike every
other brand here there is no exclusive UK importer to set one: Rapido run the UK site
themselves and sell direct to independent dealers whose asking prices for the same vehicle
differ by thousands. So this adapter **emits no price at all**, which leaves the figures
FMLV already holds untouched and surfaces them as a no-op rather than inheriting them
silently. A UK price list is an outstanding ask.

**The guide is a flipbook, and its pages are SVG with real text.** The assets are
token-signed — a bare fetch of `p1.svgz` is 403 — so the reader has to be loaded in a
browser and its responses captured, which is the whole reason the registry row says
`needs_javascript=yes`. The site itself is plain HTML and needs nothing.

**Cells come from `dx`, not from `x`.** Each table row is a *single* `<text>` element whose
content is the label and every value run together — `Payload (kg)615580` — so the element's
x is the label's x and says nothing about where the columns are. The per-character `dx`
attribute is 0 to -0.6 inside a word and jumps by several hundred at a cell boundary, which
splits the row exactly rather than by guessing at digit counts. `_CELL_GAP` is the
threshold. A row whose cell count does not match the page's column count is **dropped with
a warning**, never realigned — `docs/adapters/README.md` on cardinality failures.

**The same rule reads the column headings**, which is the one place it is indispensable:
page 3 renders `V65 XL` and `V68` with the `XL` and the `V` inside one element, as `XLV`,
and only the 86.75 jump between them says they belong to different vehicles. The heading
fragments are then glued into one string and partitioned against the comparator's roster,
so the adapter never has to decide where a space belongs — `V` + `65` + `XL` and Rapido's
own `V65 XL` normalise alike. A page whose heading does not read exactly one way is dropped.

**The self-check is arithmetic Rapido print against themselves**: MIRO + payload must equal
a gross weight stated somewhere on the same page. It holds on all 29, on both the 3.5-tonne
and the 4.5-tonne chassis, and a column slipped by one fails it — V55's MIRO with V62's
payload is 3520, which is no chassis Rapido sell. A layout that fails is dropped, never
proposed.

**Two things the guide prints that must not be read as the answer:**

* `Berths (with drop-down bed option)` is an option, and the standard `Berths` line stands.
  666F prints 2+1 and 2+2; the figure is 3.
* `Type of heating` reads `TRUMA Combi 6 INET X / ALDE as option` on four layouts. The
  standard system is the one before the slash, and recording ALDE there would call a
  blown-air motorhome wet-central off an extra the buyer may not have bought.

**Seats are the registered ones, not the belted ones.** Every layout shows
`Seats with seatbelts 2+2`, but the Distinction's 3.5-tonne variants are registered for
three and FMLV already holds `i66M TRUMA` at 3, so `Registered (driving) seats` is the
column FMLV has been using.
"""

from __future__ import annotations

import gzip
import html as htmllib
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from src.adapters.base import (
    ExtractedMotorhome,
    Provenance,
    floorplan_provenance,
    fmlv_base_vehicle,
)
from src.adapters.habitation import Feature, features_from, heating_is_unclear
from src.fetch.browser import BrowserFetcher
from src.fetch.http import Fetcher
from src.product_model.enums import BodyType
from src.product_model.model import Motorhome

__all__ = [
    "BASE_URL",
    "BODY_TYPES",
    "CATALOGUES_URL",
    "COMPARATOR_URL",
    "DEFAULT_RANGES",
    "EXPECTED_MODELS",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "RANGE_NAMES",
    "RENAMED_MODELS",
    "RENAMED_RANGES",
    "RosterEntry",
    "UNCONFIRMED_FEATURES",
    "collect",
    "heading_key",
    "identity_key",
    "model_columns",
    "page_cells",
    "parse_roster",
    "reconciles",
    "standard_heating",
    "technical_guide_url",
]

BASE_URL = "https://www.rapido-motorhome.co.uk"
MANUFACTURER = "Rapido"
MANUFACTURER_DISPLAY_NAME = "Rapido"

#: The 29 cards, each with the roster name, the series, the body type and a length.
COMPARATOR_URL = f"{BASE_URL}/comparateur-camping-cars.php"

#: Where the Calaméo link to the Technical Guide is published. The book code is opaque and
#: will change for 2028, so it is rediscovered here every run rather than hardcoded.
CATALOGUES_URL = f"{BASE_URL}/catalogue-camping-cars-rapido.php"

#: How many layouts the site claims, for the count assertion. The comparator, the homepage
#: nav and the Technical Guide all agree on 29 for 2027.
EXPECTED_MODELS = 29


#: Rapido's series slug (out of a model page's path) against the range name FMLV holds.
#:
#: **These are Rapido's own words, not a normalisation of them.** Their nav writes
#: `SERIE VANS`, `SERIE C`, `SERIE 6F`, `SERIE 8F` and `SERIE DISTINCTION` in capitals, and
#: the Technical Guide's section headings say the same. `SERIE 80dF` keeps the lower-case
#: `d` that the guide and every layout code in the series use — the nav is the only place
#: it reads `80DF`, and FMLV holds the guide's spelling.
#:
#: An unlisted slug is not fatal: it becomes `SERIE <SLUG>` and is narrated, so a series
#: added for 2028 arrives as a readable proposal instead of being dropped.
RANGE_NAMES: dict[str, str] = {
    "vans": "SERIE VANS",
    "serie-c": "SERIE C",
    "serie-6f": "SERIE 6F",
    "serie-8f": "SERIE 8F",
    "serie-80df": "SERIE 80dF",
    "serie-distinction": "SERIE DISTINCTION",
}

#: The body type, from the segment Rapido put in each model page's own path.
#:
#: **Stated, not derived.** The Technical Guide heads each series with it in words —
#: "CAMPERVANS WITH FIAT CHASSIS", "COMPACT **LOW-PROFILE** MODELS", "**A-CLASS** MODELS
#: WITH MERCEDES AL-KO CHASSIS" — and the path segment says the same thing per layout,
#: which the headings cannot because they only appear on a series' second page. Nothing
#: here is read off a height; `docs/adapters/README.md` and `auto-trail.md` record why a
#: dimension cannot decide a coachbuilt's profile.
#:
#: Serie C is the reason this is per-layout rather than per-series: C03 to C86 are
#: low-profiles and C55i, C66i and C86i are A-classes, in one range.
#:
#: **This makes FMLV's 696F wrong.** It is held as an over-cab bed; Rapido file it under
#: low-profile with the rest of Serie 6F, and the drop-down bed the 6F offers is an option,
#: not an over-cab.
BODY_TYPES: dict[str, BodyType] = {
    "vans": BodyType.CAMPERVAN_HIGH_TOP,
    "low-profile": BodyType.COACH_BUILT_LOW_PROFILE,
    "a-class": BodyType.A_CLASS,
}

#: `--range` support. The first element is the series slug the comparator publishes, the
#: last the label `cli.resolve_ranges` matches on.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = tuple(RANGE_NAMES.items())

#: What Rapido now call a range against what FMLV held before 28 October 2026 — for
#: **matching only**; nothing here renames anything in FMLV.
#:
#: FMLV used eight range strings for six ranges, and emitting Rapido's own names against
#: that baseline orphaned nine products: `COMPACT` scored 0.250, `COMPACT i` 0.200 and
#: `VAN` 0.333, all below the 0.5 threshold. `COMPACT i` is the Wingamm Brownie defect —
#: a body type in the range column splitting one Rapido range in two.
#:
#: The export was corrected before the first run, so these are expected to be stale from
#: the start and `cli.stale_renames` will say so. They are kept until a run against the
#: current export reports them dead, because the review VM keeps its own export and a run
#: there against the old one would otherwise duplicate nine live products.
#: `token_similarity` takes the better of the renamed and un-renamed scores, so an entry
#: that no longer applies cannot cost anything — `SERIE VANS`/`V62` was already right under
#: the old names and still scores 1.000.
RENAMED_RANGES: dict[str, str] = {
    "SERIE C": "COMPACT",
    "SERIE VANS": "VAN",
}

#: The same, for a layout whose **code** moved, which forces the score to zero however
#: alike the rest reads.
#:
#: `V65 XL` is the one that could not be rescued by the range alone: Rapido write it with a
#: space, which tokenises as `v65` against the baseline's `v65xl`, and a disagreeing layout
#: code is a hard zero by design. The other three retire names FMLV carried for layouts
#: Rapido have since renamed — the ULTIMATE special edition was replaced for 2027 by
#: OPTIMUM LINE, which is a trim marked on the same spec column rather than a layout, and
#: every Distinction is now suffixed with its heating.
RENAMED_MODELS: dict[tuple[str, str], tuple[str, str]] = {
    ("SERIE VANS", "V65 XL"): ("VAN", "V65XL"),
    ("SERIE 80dF", "8066dF"): ("SERIE 80dF", "8066dF ULTIMATE"),
    ("SERIE 80dF", "8096dF"): ("SERIE 80dF", "8096dF ULTIMATE"),
    ("SERIE DISTINCTION", "i96M TRUMA"): ("SERIE DISTINCTION", "I96M"),
}

#: Checked for, and the source is silent — recorded with no value so a reviewer can tell
#: "looked, and Rapido do not say" from "never looked". `diff.compare` renders these as
#: confirm-or-replace rather than as a proposed `No`.
#:
#: The guide's equipment pages do carry an oven and washroom grid, but there the label and
#: its ●/○ marks sit on separate lines and the mark count does not always equal the column
#: count, so reading them would mean realigning by assumption — exactly what the cell rule
#: above exists to refuse.
UNCONFIRMED_FEATURES: dict[str, str] = {
    "microwave": "no microwave is named in the technical data; the guide's equipment "
    "grid cannot be aligned to its columns safely, so this is unread rather than absent",
    "shower_toilet_separated": "the technical data pages give no washroom description at "
    "all — only bed sizes, tank volumes and the garage",
}


# --------------------------------------------------------------------------- #
# The comparator: the roster, the series, the body type
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RosterEntry:
    """One layout as the comparator publishes it."""

    #: Rapido's own spelling, from the card's visible heading: `V65 XL`, `i96M TRUMA`.
    name: str
    #: The series segment of the model page's path — `vans`, `serie-c`, `serie-80df`.
    series: str
    #: The body-type segment of that same path — `vans`, `low-profile`, `a-class`.
    body: str
    #: The model page, which carries the floorplan a reviewer needs for the positional
    #: fields. It holds no weights or dimensions.
    url: str
    #: `data-long`, in centimetres, for cross-checking the guide's metres.
    length_mm: int | None = None
    #: `data-couchage` — the beds a layout can be had with, quoted but never parsed.
    beds: str = ""

    @property
    def key(self) -> str:
        return identity_key(self.name)

    @property
    def range_name(self) -> str:
        return RANGE_NAMES.get(self.series, f"SERIE {self.series.upper()}")

    @property
    def label(self) -> str:
        return f"{self.range_name} {self.name}"


_CARD = re.compile(
    r'(?s)<a\b(?P<attrs>[^>]*class="[^"]*cell-modele[^"]*"[^>]*)>(?P<inner>.*?)</a>'
)
_ATTR = re.compile(r'([a-zA-Z-]+)="([^"]*)"')
#: `motorhome_<body>_<series>_<slug>.chtml`. Four segments, always.
_MODEL_PATH = re.compile(
    r"motorhome_(?P<body>[^_]+)_(?P<series>[^_]+)_(?P<slug>[^.]+)\.chtml"
)


def _text(fragment: str) -> str:
    return " ".join(htmllib.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def identity_key(name: str) -> str:
    """A layout name reduced to what two renderings of it still agree on.

    `V65 XL`, `V 65 XL` and the guide's `V` + `65` + `XL` fragments all give `v65xl`, which
    is what lets a column heading be matched to the roster without the adapter ever having
    to decide where Rapido put a space.
    """
    return re.sub(r"[^a-z0-9]", "", name.lower())


def parse_roster(page: str) -> tuple[RosterEntry, ...]:
    """Every layout the comparator lists, in the order it lists them."""
    entries: list[RosterEntry] = []
    for card in _CARD.finditer(page):
        attrs = dict(_ATTR.findall(card.group("attrs")))
        path = _MODEL_PATH.search(attrs.get("href", ""))
        if path is None:
            continue
        # The heading is everything before the length, which the card renders inside
        # guillemets: "V65 XL ‹ 6.36 m ›".
        name = _text(card.group("inner")).split("‹")[0].strip()
        if not name:
            continue
        length = attrs.get("data-long", "")
        entries.append(
            RosterEntry(
                name=name,
                series=path.group("series"),
                body=path.group("body"),
                url=f"{BASE_URL}/{attrs['href'].lstrip('/')}",
                length_mm=int(length) * 10 if length.isdigit() else None,
                beds=attrs.get("data-couchage", ""),
            )
        )
    return tuple(entries)


#: The catalogues page gives each document a `<h2>` and a stable anchor id. Either will do,
#: and both are checked because the id is the kind of thing a site redesign drops.
_GUIDE_ANCHOR = re.compile(r'<a\b[^>]*\bid="[^"]*-dl-gt-[^"]*"[^>]*\bhref="([^"]+)"')
_GUIDE_BLOCK = re.compile(
    r"(?is)<h2[^>]*>\s*TECHNICAL GUIDE.*?"
    r"<a\b[^>]*\bhref=\"(https://www\.calameo\.com/[^\"]+)\""
)


def technical_guide_url(page: str) -> str | None:
    """The Calaméo reader URL for the current Technical Guide, or `None` if it has moved."""
    for pattern in (_GUIDE_ANCHOR, _GUIDE_BLOCK):
        found = pattern.search(page)
        if found and "calameo.com" in found.group(1):
            return htmllib.unescape(found.group(1))
    return None


# --------------------------------------------------------------------------- #
# The Technical Guide: SVG pages, split on `dx`
# --------------------------------------------------------------------------- #

#: A `dx` advance above this marks a cell boundary. Inside a word the values run from 0 to
#: about -0.6; between cells they are in the hundreds, so nothing sits near the threshold.
_CELL_GAP = 5.0

_TEXT_ELEMENT = re.compile(r"(?s)<text[^>]*>.*?</text>")
_DX = re.compile(r'dx="([^"]*)"')
_MATRIX = re.compile(r"matrix\(([^)]*)\)")
#: `/p12.svgz` out of a captured asset URL.
_PAGE_NUMBER = re.compile(r"/p(\d+)\.svgz?\b")


@dataclass(frozen=True)
class _Row:
    """One `<text>` element: where it sits, and the cells `dx` splits it into."""

    y: float
    x: float
    cells: tuple[str, ...]

    @property
    def label(self) -> str:
        return self.cells[0].strip() if self.cells else ""

    @property
    def values(self) -> tuple[str, ...]:
        return tuple(cell.strip() for cell in self.cells[1:])


def _split_element(element: str) -> _Row:
    attrs = element[: element.index(">")]
    inner = element[element.index(">") + 1 : element.rindex("</text>")]
    text = htmllib.unescape(re.sub(r"<[^>]+>", "", inner))

    x = y = 0.0
    matrix = _MATRIX.search(attrs)
    if matrix:
        parts = [float(value) for value in re.split(r"[,\s]+", matrix.group(1).strip())]
        if len(parts) == 6:
            x, y = parts[4], parts[5]

    advances = _DX.search(attrs)
    if not advances:
        return _Row(y=y, x=x, cells=(text,))

    jumps = [float(value) for value in advances.group(1).split()]
    cells: list[str] = []
    current: list[str] = []
    for index, character in enumerate(text):
        if index < len(jumps) and jumps[index] > _CELL_GAP and current:
            cells.append("".join(current))
            current = []
        current.append(character)
    if current:
        cells.append("".join(current))
    return _Row(y=y, x=x, cells=tuple(cells))


def page_cells(svg: str) -> tuple[_Row, ...]:
    """Every row of one guide page, in reading order, each already split into cells."""
    rows = [_split_element(element.group(0)) for element in _TEXT_ELEMENT.finditer(svg)]
    rows.sort(key=lambda row: (round(row.y, 1), row.x))
    return tuple(rows)


def _svg_of(path: Path) -> str:
    """A captured page, whether or not Calaméo gzipped it — both have been seen."""
    raw = path.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw.decode("utf-8", errors="replace")


# --------------------------------------------------------------------------- #
# Binding a page's columns to layouts
# --------------------------------------------------------------------------- #

#: The first section of every specification table, and the line the column headings sit
#: immediately above.
_FIRST_SECTION = "VEHICLE DIMENSIONS"

#: The row that says how many columns a page has, and half of the self-check.
_MIRO_LABEL = "Mass in Running Order (MIRO) (kg)"

#: Two rows are the same line of type when their baselines agree this closely.
_SAME_LINE = 1.5

#: More than one reading of a heading is no reading at all; stop looking after the second.
_ENOUGH_PARTITIONS = 2


def _partitions(key: str, candidates: Sequence[str], count: int) -> list[tuple[str, ...]]:
    """Every way `key` splits into exactly `count` roster keys, laid end to end."""
    found: list[tuple[str, ...]] = []

    def walk(rest: str, taken: list[str]) -> None:
        if len(found) >= _ENOUGH_PARTITIONS or len(taken) > count:
            return
        if not rest:
            if len(taken) == count:
                found.append(tuple(taken))
            return
        for candidate in candidates:
            if rest.startswith(candidate):
                walk(rest[len(candidate) :], [*taken, candidate])

    walk(key, [])
    return found


def heading_key(rows: Sequence[_Row]) -> str | None:
    """Every fragment of a page's column headings, glued into one normalised string.

    The headings are display type sitting on the line immediately above the table's first
    section, one `<text>` element per fragment, and the fragments of two neighbouring
    vehicles sometimes share an element (`XLV`, for `V65 XL` beside `V68`). Gluing and
    normalising sidesteps both the spacing and the element boundaries, so `V` + `65` + `XL`
    and Rapido's own `V65 XL` come out alike.
    """
    baseline = next(
        (row.y for row in rows if row.label.upper().startswith(_FIRST_SECTION)), None
    )
    if baseline is None:
        return None
    above = [row.y for row in rows if row.y < baseline - 0.1]
    if not above:
        return None
    heading_y = max(above)
    glued = "".join(
        identity_key(cell)
        for row in rows
        if abs(row.y - heading_y) <= _SAME_LINE
        for cell in row.cells
    )
    return glued or None


def model_columns(
    rows: Sequence[_Row], roster_keys: Sequence[str], count: int
) -> tuple[str, ...] | None:
    """The layouts this page's `count` columns belong to, left to right.

    The glued heading is partitioned against the roster. `None` means it did not partition
    exactly one way, and the caller falls back or drops the page rather than guessing at
    the alignment.
    """
    glued = heading_key(rows)
    if glued is None:
        return None
    # Longest first so the search settles on `c66i` before `c66`, which keeps the common
    # case cheap; a second reading is still looked for before one is accepted.
    candidates = sorted(set(roster_keys), key=len, reverse=True)
    found = _partitions(glued, candidates, count)
    return found[0] if len(found) == 1 else None


def _is_subsequence(part: str, whole: str) -> bool:
    """Every character of `part` appears in `whole`, in order."""
    remaining = iter(whole)
    return all(character in remaining for character in part)


#: What the guide shouts across the top of a series' **first** page, normalised, against
#: the comparator's series slug. Five of the six already read alike once case and spacing
#: are gone — `SERIE C`, `SERIE 6F`, `SERIE 8F`, `SERIE 80dF`, `SERIE DISTINCTION` — so
#: only the campervans need naming here, Rapido heading theirs `CAMPERVAN SERIES`.
_SERIES_HEADINGS: dict[str, str] = {"campervanseries": "vans"}


def _series_of(rows: Sequence[_Row]) -> str | None:
    """The series this page belongs to, where it shouts one across the top.

    Only a series' first page carries its title; the pages after it head themselves with
    the chassis instead ("CAMPERVANS WITH FIAT CHASSIS"), so the caller carries the last
    title it saw forward through the book.
    """
    if not rows:
        return None
    top = min(row.y for row in rows)
    glued = "".join(
        identity_key(cell)
        for row in rows
        if abs(row.y - top) <= _SAME_LINE
        for cell in row.cells
    )
    if glued in _SERIES_HEADINGS:
        return _SERIES_HEADINGS[glued]
    return next((slug for slug in RANGE_NAMES if identity_key(slug) == glued), None)


# --------------------------------------------------------------------------- #
# Reading one column
# --------------------------------------------------------------------------- #

#: A section heading inside the table: one cell, shouted, opening with a letter. The
#: opening letter matters — `20/130` is a fresh-water capacity, not a heading.
_SECTION = re.compile(r"^[A-Z][A-Z0-9 ()/,.&'’\-]{2,}$")

#: `3,5 T`, `4,25 T` — a chassis weight as the guide prints it.
_TONNES = re.compile(r"(\d+(?:,\d+)?)\s*T\b")
#: `GVW 3500/3650 kg`, `GVW = 4400 kg` — the same thing where the guide prints kilograms.
_GVW_KG = re.compile(r"GVW[^A-Za-z]{0,6}(\d{4})(?:\s*/\s*(\d{4}))?\s*kg", re.I)

#: The garage dimensions sit under this heading. `Width`, `Length` and `Height` are far too
#: common to be looked up by label alone.
_GARAGE_SECTION = "STORAGE AREA/GARAGE"
_GARAGE_LABELS = ("Width", "Length", "Height")
_BED_SECTION = "BED SIZE"

#: A cell the guide uses for "this layout does not have one".
_ABSENT = {"", "-"}


def _metres_to_mm(value: str) -> int | None:
    try:
        return round(float(value.replace(",", ".").strip()) * 1000)
    except ValueError:
        return None


def _count(value: str) -> int | None:
    """`2+1` -> 3, `4*` -> 4, `-` -> None. Rapido print both halves of a berth count."""
    cleaned = re.sub(r"[*\s]", "", value)
    if cleaned in _ABSENT:
        return None
    try:
        return sum(int(part) for part in cleaned.split("+"))
    except ValueError:
        return None


def _gross_weights(rows: Iterable[_Row]) -> set[int]:
    """Every gross weight printed anywhere on the page, in kilograms.

    The GVW row is not reliably a row: on some pages its values sit in free-standing
    `LIGHT:`/`HEAVY:` elements that no cell split lines up with. What the self-check needs
    is only that the figure appears on the page at all, so the whole page is read rather
    than one line of it.
    """
    weights: set[int] = set()
    for row in rows:
        text = " ".join(row.cells)
        for tonnes in _TONNES.findall(text):
            weights.add(round(float(tonnes.replace(",", ".")) * 1000))
        for light, heavy in _GVW_KG.findall(text):
            weights.update(int(value) for value in (light, heavy) if value)
    return weights


def reconciles(miro: int | None, payload: int | None, gross_weights: set[int]) -> bool:
    """Rapido's own arithmetic: MIRO plus payload is one of the page's gross weights.

    Two printed figures checked against a third, which is what makes it worth having — a
    column slipped by one pairs one layout's MIRO with another's payload and the sum lands
    on no chassis Rapido sell. V55's 3045 with V62's 475 is 3520; nothing is sold at 3520.
    """
    if miro is None or payload is None or not gross_weights:
        return False
    return (miro + payload) in gross_weights


#: `TRUMA Combi 6 INET X / ALDE as option` — the standard system and an extra, in one cell.
_HEATING_OPTION = re.compile(r"\s*/\s*[^/]*\bas option\b.*$", re.I)


def standard_heating(value: str) -> str:
    """The heating a buyer gets without paying, out of a cell that offers two.

    Four layouts print an ALDE alternative beside the standard TRUMA. Reading the whole
    cell would call a blown-air motorhome wet-central off an option, so the clause marked
    as one is cut. A cell naming a single system is returned untouched.
    """
    return _HEATING_OPTION.sub("", value).strip()


@dataclass(frozen=True)
class _Column:
    """One layout's figures, as read off one page of the guide."""

    page: int
    length_mm: int | None = None
    width_mm: int | None = None
    height_mm: int | None = None
    miro: int | None = None
    payload: int | None = None
    berths: int | None = None
    seats: int | None = None
    chassis: str = ""
    heating: str = ""
    fridge: str = ""
    fridge_litres: str = ""
    garage: str = ""
    beds: tuple[str, ...] = ()


def _read_columns(rows: Sequence[_Row], count: int, page: int) -> list[_Column]:
    """Every column of one spec page, with any row that does not fit simply left out."""
    section = ""
    simple: dict[str, tuple[str, ...]] = {}
    garage: dict[str, tuple[str, ...]] = {}
    beds: list[tuple[str, tuple[str, ...]]] = []
    for row in rows:
        if len(row.cells) == 1 and _SECTION.match(row.label):
            section = row.label
            continue
        values = row.values
        if len(values) != count:
            continue
        if section.startswith(_GARAGE_SECTION):
            garage.setdefault(row.label, values)
        elif section.startswith(_BED_SECTION):
            beds.append((row.label, values))
        else:
            simple.setdefault(row.label, values)

    def at(label: str, index: int) -> str:
        found = simple.get(label)
        return found[index] if found else ""

    columns: list[_Column] = []
    for index in range(count):
        columns.append(
            _Column(
                page=page,
                length_mm=_metres_to_mm(at("Overall length", index)),
                width_mm=_metres_to_mm(
                    at("Overall width (excluding wing mirrors)", index)
                ),
                height_mm=_metres_to_mm(at("Overall height", index)),
                miro=_count(at(_MIRO_LABEL, index)),
                payload=_count(at("Payload (kg)", index)),
                berths=_count(at("Berths", index)),
                seats=_count(at("Registered (driving) seats", index)),
                chassis=at("Chassis", index),
                heating=at("Type of heating", index),
                fridge=at("Type of refrigerator", index),
                fridge_litres=at("Refrigerator volume", index),
                garage=", ".join(
                    f"{label.lower()} {values[index]} cm"
                    for label, values in garage.items()
                    if label in _GARAGE_LABELS and values[index] not in _ABSENT
                ),
                beds=tuple(
                    f"{label} {values[index]} mm"
                    for label, values in beds
                    if values[index] not in _ABSENT
                ),
            )
        )
    return columns


# --------------------------------------------------------------------------- #
# Fetching the flipbook
# --------------------------------------------------------------------------- #

#: How far apart to open the reader. Calaméo preloads a spread's neighbours, so a visit
#: yields roughly four pages either side of the one asked for; five keeps every visit
#: overlapping its predecessor, so no page can fall between two of them.
_READER_STEP = 5

#: A 32-page guide needs seven visits. The cap is what stops a changed reader — one that
#: stopped clamping past the last page, say — looping.
_MAX_VISITS = 14


def _reader_url(guide_url: str, page: int) -> str:
    separator = "&" if "?" in guide_url else "?"
    return f"{guide_url}{separator}page={page}"


def _capture_pages(
    browser: BrowserFetcher,
    guide_url: str,
    on_progress: Callable[[str], None],
) -> dict[int, Path]:
    """Every page of the flipbook, by page number.

    The assets are token-signed — the reader mints a short-lived token per file, and a
    direct fetch of `p1.svgz` is 403 — so they can only be had as the reader's own
    responses. Visits stop as soon as one brings nothing new, which is what happens once
    the reader is asked for a page past the end.
    """
    pages: dict[int, Path] = {}
    wanted = 1
    for _visit in range(_MAX_VISITS):
        _page, captured = browser.fetch_with_capture(
            _reader_url(guide_url, wanted),
            capture_url_contains=".svg",
            on_progress=on_progress,
        )
        fresh = 0
        for result in captured:
            number = _PAGE_NUMBER.search(result.url)
            if number is None or int(number.group(1)) in pages:
                continue
            pages[int(number.group(1))] = result.file_path
            fresh += 1
        on_progress(
            f"Technical Guide: opened at page {wanted}, "
            f"{fresh} new page(s), {len(pages)} held"
        )
        if not fresh:
            break
        wanted += _READER_STEP
    return pages


# --------------------------------------------------------------------------- #
# Building the product
# --------------------------------------------------------------------------- #


def _feature_value(features: dict[str, Feature], name: str) -> object | None:
    found = features.get(name)
    return found.value if found else None


def _specification_lines(column: _Column) -> list[str]:
    """What Rapido say about this layout's habitation, in their own words.

    Only the technical data is used. The comparator's `data-couchage` is deliberately left
    out of the reading: it lists the beds a layout *can* be had with rather than the one
    fitted — 686F reads "Central bed ; XL central bed ; Face-to-face bench seats" — so it
    is quoted for the reviewer and never parsed.
    """
    lines: list[str] = []
    heating = standard_heating(column.heating)
    if heating:
        lines.append(f"Type of heating: {heating}")
    if column.fridge:
        volume = (
            f", refrigerator volume {column.fridge_litres} litres"
            if column.fridge_litres
            else ""
        )
        lines.append(f"Type of refrigerator: {column.fridge}{volume}")
    return lines


def _build(
    entry: RosterEntry,
    column: _Column,
    guide_url: str,
    on_progress: Callable[[str], None],
) -> ExtractedMotorhome:
    label = entry.label
    page_url = _reader_url(guide_url, column.page)
    guide = f"the 2027 Technical Guide, page {column.page}"

    lines = _specification_lines(column)
    features = features_from(lines)

    body_type = BODY_TYPES.get(entry.body)
    if body_type is None:
        on_progress(f"{label}: body type '{entry.body}' is not one we know — left blank")

    gross = (
        column.miro + column.payload
        if column.miro is not None and column.payload is not None
        else None
    )
    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=entry.range_name,
        model=entry.name,
        base_vehicle_manufacturer=(
            fmlv_base_vehicle(column.chassis.split()[0].title())
            if column.chassis.split()
            else None
        ),
        mh_length_mm=column.length_mm,
        mh_width_mm=column.width_mm,
        mh_height_mm=column.height_mm,
        mro_kilograms=column.miro,
        mh_payload_kilograms=column.payload,
        mtplm_kilograms=gross,
        berths=column.berths,
        mh_passenger_seats_inc_driver=column.seats,
        body_type=body_type,
        rear_garage=True if column.garage else None,
        heating=_feature_value(features, "heating"),  # type: ignore[arg-type]
        refrigeration=_feature_value(features, "refrigeration"),  # type: ignore[arg-type]
        # No price: Rapido publish none and no importer sets one. See the module docstring.
    )

    provenance: dict[str, Provenance] = {}

    def record(field: str, snippet: str, *, url: str = page_url) -> None:
        provenance[field] = Provenance(source_url=url, snippet=f"{label} — {snippet}")

    record(
        "manufacturer_range",
        f"Rapido file this layout under {entry.range_name}",
        url=entry.url,
    )
    record("model", f"Rapido call this layout {entry.name}", url=entry.url)
    if motorhome.base_vehicle_manufacturer:
        record("base_vehicle_manufacturer", f"Chassis {column.chassis}, from {guide}")
    for field, printed in (
        ("mh_length_mm", f"Overall length {column.length_mm} mm"),
        ("mh_width_mm", f"Overall width (excluding wing mirrors) {column.width_mm} mm"),
        ("mh_height_mm", f"Overall height {column.height_mm} mm"),
        ("mro_kilograms", f"Mass in Running Order (MIRO) {column.miro} kg"),
        ("mh_payload_kilograms", f"Payload {column.payload} kg"),
    ):
        if getattr(motorhome, field) is not None:
            record(field, f"{printed}, from {guide}")
    if gross is not None:
        record(
            "mtplm_kilograms",
            f"MIRO {column.miro} kg plus payload {column.payload} kg = {gross} kg gross "
            f"vehicle weight, from {guide}",
        )
    if motorhome.berths is not None:
        record(
            "berths",
            f"Berths {column.berths}, the standard line rather than any option, "
            f"from {guide}",
        )
    if motorhome.mh_passenger_seats_inc_driver is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"Registered (driving) seats {column.seats}, from {guide}",
        )
    if body_type is not None:
        record(
            "body_type",
            f"Rapido file this layout under '{entry.body}', and the Technical Guide heads "
            f"its series with the same words",
            url=entry.url,
        )
    if column.garage:
        record("rear_garage", f"Storage area/garage: {column.garage}, from {guide}")

    for field, feature in features.items():
        note = f"{feature.note} " if feature.note else ""
        record(field, f"{note}{feature.snippet}")
    if "heating" not in features:
        unclear = heating_is_unclear(lines)
        if unclear:
            record("heating", f"heating left unread — {unclear}")
            on_progress(f"{label}: heating left unread — {unclear}")
    for field, reason in UNCONFIRMED_FEATURES.items():
        record(field, reason)

    # The positional fields need the drawing, and the model page is where it is. The bed
    # sizes and Rapido's own bed names ride along so the reviewer has them to hand.
    beds = "; ".join(column.beds) or "no bed sizes printed"
    comparator = f"; the comparator lists {entry.beds}" if entry.beds else ""
    provenance.update(
        floorplan_provenance(
            motorhome,
            entry.url,
            f"{label} (guide gives {beds}{comparator})",
            drawing="the model page's floorplan",
        )
    )
    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


# --------------------------------------------------------------------------- #
# collect
# --------------------------------------------------------------------------- #


def collect(
    http: Fetcher,
    browser: BrowserFetcher,
    snapshot_dir: Path,  # noqa: ARG001 — both fetchers snapshot for themselves
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every Rapido layout: the comparator for the roster, the flipbook for the figures."""
    wanted = {slug for slug, _label in ranges}

    comparator = http.fetch(COMPARATOR_URL).file_path.read_text(
        encoding="utf-8", errors="replace"
    )
    roster = parse_roster(comparator)
    if not roster:
        msg = f"no layouts found on the comparator at {COMPARATOR_URL}"
        raise RuntimeError(msg)
    on_progress(f"Comparator lists {len(roster)} layout(s)")
    if len(roster) != EXPECTED_MODELS:
        on_progress(
            f"NOTE: the comparator lists {len(roster)} layouts where {EXPECTED_MODELS} "
            f"were expected — the range has moved, so check the roster before accepting"
        )
    for slug in sorted({entry.series for entry in roster} - set(RANGE_NAMES)):
        on_progress(
            f"NOTE: series '{slug}' is one we have not met — its range is being called "
            f"'SERIE {slug.upper()}', which may not be what Rapido print"
        )

    catalogues = http.fetch(CATALOGUES_URL).file_path.read_text(
        encoding="utf-8", errors="replace"
    )
    guide_url = technical_guide_url(catalogues)
    if guide_url is None:
        msg = f"no Technical Guide link on {CATALOGUES_URL}"
        raise RuntimeError(msg)
    on_progress(f"Technical Guide: {guide_url}")

    pages = _capture_pages(browser, guide_url, on_progress)
    if not pages:
        msg = f"the Technical Guide reader at {guide_url} served no pages"
        raise RuntimeError(msg)

    by_key = {entry.key: entry for entry in roster}
    # Each series' layouts, in the order the comparator lists them, consumed page by page.
    # The guide runs through a series in that same order, which is what lets a page whose
    # headings are drawn as outlines rather than text still be placed — see below.
    unplaced: dict[str, list[str]] = {}
    for entry in roster:
        unplaced.setdefault(entry.series, []).append(entry.key)

    series: str | None = None
    columns: dict[str, _Column] = {}
    for number in sorted(pages):
        rows = page_cells(_svg_of(pages[number]))
        series = _series_of(rows) or series
        miro = next((row for row in rows if row.label == _MIRO_LABEL), None)
        if miro is None or not miro.values:
            continue
        count = len(miro.values)
        pool = unplaced.get(series or "", [])
        heading = model_columns(rows, pool or list(by_key), count)
        if heading is None and len(pool) >= count:
            # Calaméo outlines the odd heading letter instead of setting it as text —
            # page 9 of the 2027 guide loses the `i` of C66i and the `C` of C86i — so the
            # glued string is short and cannot be partitioned. Falling back on the order
            # the series is published in is only safe because what *was* read still has to
            # appear within the expected names, in order; it is narrated either way.
            ordered = tuple(pool[:count])
            glued = heading_key(rows)
            if glued and _is_subsequence(glued, "".join(ordered)):
                heading = ordered
                on_progress(
                    f"Guide page {number}: its headings read as '{glued}', which is short "
                    f"of a full set — taken as {', '.join(by_key[k].name for k in ordered)} "
                    f"on the order the series is published in, which that reading fits"
                )
        if heading is None:
            on_progress(
                f"Guide page {number}: {count} column(s) of specification, but its "
                f"headings do not read as exactly one set of layouts — page skipped"
            )
            continue
        for key in heading:
            if key in pool:
                pool.remove(key)
        gross = _gross_weights(rows)
        for key, column in zip(heading, _read_columns(rows, count, number), strict=True):
            if not reconciles(column.miro, column.payload, gross):
                on_progress(
                    f"Guide page {number}: {by_key[key].label} does not reconcile — "
                    f"MIRO {column.miro} plus payload {column.payload} is no gross weight "
                    f"printed on the page ({sorted(gross)}) — dropped"
                )
                continue
            columns[key] = column

    products: list[ExtractedMotorhome] = []
    for entry in roster:
        if entry.series not in wanted:
            continue
        column = columns.get(entry.key)
        if column is None:
            on_progress(
                f"{entry.label}: no column in the Technical Guide reconciled to it — "
                f"skipped, so the figures FMLV already holds stand"
            )
            continue
        if entry.length_mm is not None and column.length_mm != entry.length_mm:
            on_progress(
                f"NOTE: {entry.label} is {column.length_mm} mm in the guide and "
                f"{entry.length_mm} mm on the comparator — the guide is what is recorded"
            )
        products.append(_build(entry, column, guide_url, on_progress))

    on_progress(f"Built {len(products)} product(s) from {len(pages)} guide page(s)")
    return products
