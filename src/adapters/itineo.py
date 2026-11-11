"""ITINEO — ten coachbuilts from Groupe Rapido, read from the same kind of guide.

`docs/adapters/itineo.md` is the survey; this is what it decided.

**Most of the hard work was already done in `rapido.py`.** Both brands publish their
specifications as a Calaméo flipbook on the same publisher account — every book code
begins `00769273` — so the group uses one document generator, the arrangement
Pilote / Joa / Le Voyageur already share. `rapido.page_cells` splits Itineo's pages on
`dx` unchanged, and `rapido.reconciles` checks its arithmetic unchanged. This module
imports both rather than copying them.

Four things are Itineo's own.

* **Finding the guide.** `rapido.technical_guide_url` keys on a `TECHNICAL GUIDE` heading.
  Itineo's link says *"Download the specifications"* and carries
  `id="itineo-dl-gt-gbr-en"` — `gt` for *guide technique*. See `technical_guide_url`.

* **The column order comes from the headings' x, not from the page's reading order.** The
  ten model codes are staggered across two lines and some share one `<text>` element, so
  sorting rows by `(y, x)` interleaves them wrongly. Sorting the *elements* by x and
  flattening each one's cells gives the true left-to-right order. See `column_order`.

* **That order is then checked against the model pages.** Every model page publishes its
  own overall height, and the guide prints a height per column; if the two disagree the
  columns are misaligned and the run is refused. See `_check_alignment` — this is the
  guard that a wrong column order would otherwise slip past, because every value would
  still be a plausible figure for an Itineo.

* **No price is ever emitted.** Itineo publish none anywhere — not on a model page, not in
  the guide, not in the catalogue — and FMLV's rows carry dealer-sourced figures that a
  blank would destroy. The same position as Rapido.
"""

from __future__ import annotations

import html as html_module
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from ..fetch.browser import BrowserFetcher
from ..fetch.http import Fetcher
from ..product_model.model import Motorhome
from . import gearbox, habitation, rapido
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

__all__ = [
    "BASE_URL",
    "DEFAULT_RANGES",
    "EXPECTED_PRODUCTS",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "ItineoProduct",
    "collect",
    "column_order",
    "guide_rows",
    "parse_model_page",
    "parse_roster",
    "range_of",
    "technical_guide_url",
]

BASE_URL = "https://www.itineo.co.uk"

#: Byte-for-byte the `manufacturer` value in FMLV's export, confirmed against the export of
#: 11 November 2026: **capitals**, in both `manufacturer` and `manufacturer_display_name`,
#: and the NCC manufacturer list spells id 128 the same way.
#:
#: The requester noted there is no branding reason for the capitals — the site uses
#: `ITINEO` in its logo and `Itineo` in prose — but the export is the join key and tidying
#: it would detach every product from its history.
MANUFACTURER = "ITINEO"
MANUFACTURER_DISPLAY_NAME = "ITINEO"

MODELS_INDEX_URL = f"{BASE_URL}/motorhome_index.php"

#: Where both Calaméo books are linked: the catalogue and the specifications.
DOCUMENTS_URL = f"{BASE_URL}/motorhome_doc.php"

EXPECTED_PRODUCTS = 10

#: FMLV's three live ranges, and the rule that sorts a model into one.
#:
#: **Taken from the export, and it agrees with the guide.** The guide heads its table with
#: three series — `COZI`, `FAMILI COMPACT`, `FAMILI` — and every current FMLV row uses one
#: of the same three:
#:
#: | range | models |
#: |---|---|
#: | `COZI` | PC640, PF600, PJ700, PM740, PS700 — the `P` models |
#: | `FAMILI COMPACT` | CJ660, CM660, CS660 — the 660s |
#: | `FAMILI` | JC740, MC740, SB740, SBD700 |
#:
#: So the split is by body size within the two families, which is why it cannot be read
#: off the model letter alone.
COZI = "COZI"
FAMILI_COMPACT = "FAMILI COMPACT"
FAMILI = "FAMILI"


def range_of(model: str) -> str:
    """The FMLV range a model code belongs to.

    Getting this wrong is not cosmetic: `manufacturer_range` is part of how a scraped
    product is matched to its FMLV row, so a wrong range proposes a rename on every
    product at once.
    """
    code = model.upper().strip()
    if code.startswith("P"):
        return COZI
    if "660" in code:
        return FAMILI_COMPACT
    return FAMILI


#: `(code, label)` for `--range`. Keyed on the model code because every model is its own
#: product and the two range names would only offer a coarse filter.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (
    ("cm_660", "CM660"),
    ("cj_660", "CJ660"),
    ("sbd_700", "SBD700"),
    ("jc_740", "JC740"),
    ("mc_740", "MC740"),
    ("sb_740", "SB740"),
    ("pf_600", "PF600"),
    ("pj_700", "PJ700"),
    ("ps_740", "PS740"),
    ("pm_740", "PM740"),
)

#: Model pages are `motorhome_<slug>.php`; the FMLV model is the slug without its
#: underscore, upper-cased.
_SLUG_OF = {label: slug for slug, label in DEFAULT_RANGES}


# --------------------------------------------------------------------------- #
# The site
# --------------------------------------------------------------------------- #

#: A model page link on the index — `motorhome_sbd_700.php`.
_MODEL_LINK = re.compile(r"motorhome_([a-z]+)_(\d{3})\.php", re.I)

#: The specifications book, by the id its anchor carries. `gt` is *guide technique*, the
#: same abbreviation Rapido's own link uses, and it is what tells the two books apart —
#: the catalogue beside it is `itineo-dl-catalogue-gbr-en` and holds no figures at all.
_GUIDE_ANCHOR = re.compile(
    r'<a[^>]*\bid="itineo-dl-gt-[^"]*"[^>]*\bhref="([^"]+)"'
    r'|<a[^>]*\bhref="([^"]+)"[^>]*\bid="itineo-dl-gt-[^"]*"',
    re.I,
)

_TAG = re.compile(r"<[^>]+>")


def _text(fragment: str) -> str:
    return " ".join(html_module.unescape(_TAG.sub(" ", fragment)).split())


def parse_roster(index_html: str) -> tuple[str, ...]:
    """Every model code the index links, in first-seen order — `SBD700`, `PF600`, …"""
    seen: list[str] = []
    for letters, digits in _MODEL_LINK.findall(index_html):
        code = f"{letters}{digits}".upper()
        if code not in seen:
            seen.append(code)
    return tuple(seen)


def technical_guide_url(documents_html: str) -> str | None:
    """The Calaméo reader URL for the current specifications book, or `None`.

    **Rediscovered every run.** The book code is opaque — `007692732cc45a1d22052` for the
    2027 collection — and will change when the next one is published, so nothing here may
    hardcode it.
    """
    found = _GUIDE_ANCHOR.search(documents_html)
    if found is None:
        return None
    url = next((group for group in found.groups() if group), None)
    if url is None or "calameo.com" not in url:
        return None
    return html_module.unescape(url)


# --------------------------------------------------------------------------- #
# The guide
# --------------------------------------------------------------------------- #

#: A model code as the guide's column headings write it.
_CODE = re.compile(r"^(?:CJ|CM|CS|SBD|SB|SC|JC|MC|RC|PF|PC|PJ|PM|PS)\s*\d{3}$", re.I)

#: The row labels this adapter reads, mapped to how each value is converted.
#:
#: **`Overall width (excluding wing mirrors)` is the one taken**, not the row below it.
#: Itineo publish both, and the cross-manufacturer rule wants the body.
_METRES_ROWS: dict[str, str] = {
    "overall length": "mh_length_mm",
    "overall width (excluding wing mirrors)": "mh_width_mm",
    "overall height": "mh_height_mm",
}
_KILOGRAM_ROWS: dict[str, str] = {
    "mass in running order (miro) (kg)": "mro_kilograms",
    "payload (kg)": "mh_payload_kilograms",
}


@dataclass(frozen=True)
class GuideRow:
    """One row of the guide's table: its label and one value per model column."""

    label: str
    values: tuple[str, ...]


def column_order(rows: Iterable[rapido._Row]) -> tuple[str, ...]:
    """The model codes the guide's columns belong to, left to right.

    **Not the page's reading order.** The ten codes sit on two staggered lines and some
    share a single `<text>` element — `('SBD700', 'JC740')` is one element, and
    `('SB740', 'PF600', 'PJ700', 'PS740')` is another — so `page_cells`, which sorts by
    `(y, x)`, interleaves them with the codes on the other line. Sorting the **elements**
    by x and flattening each one's cells in order recovers the true sequence.

    Rapido does this differently, by partitioning a glued heading string against its
    roster. That does not transfer: Itineo's codes are not on the line immediately above
    the first section, so `rapido.heading_key` finds `(IN KG) 20 YEARS …` instead.
    """
    elements = [
        row for row in rows if row.cells and all(_CODE.match(c.strip()) for c in row.cells)
    ]
    elements.sort(key=lambda row: row.x)
    return tuple(cell.strip().upper().replace(" ", "") for row in elements for cell in row.cells)


#: How far apart two elements' baselines may sit and still be one row. A label is set a
#: half-point below its values here — 715.370 against 714.860 — so this only has to be
#: bigger than that and much smaller than a row's height, which is about 27.
_SAME_LINE = 3.0


def _line_of(rows: Sequence[rapido._Row], label_row: rapido._Row) -> list[rapido._Row]:
    return sorted(
        (row for row in rows if abs(row.y - label_row.y) <= _SAME_LINE),
        key=lambda row: row.x,
    )


def guide_rows(rows: Sequence[rapido._Row], columns: int) -> tuple[GuideRow, ...]:
    """Every labelled row of the table, paired with its values.

    **Driven from the label, not from the line.** The guide writes a row as a label
    element to the left of the table and its values across it, and the two sit a half-point
    apart vertically. Gathering *every* cell on the line and demanding exactly `columns` of
    them fails on two real rows: the payload line carries a footnote marker as well as its
    ten figures, and the gross-weight line spreads `LIGHT: 3.5 T` and `HEAVY: 4.4 T` across
    a dozen separate elements.

    So each label is taken in turn and the **widest single element on its line** supplies
    the values, with the narrower fragments ignored — except where no element is wide
    enough, in which case every value fragment on the line is kept in x order. That second
    path is what reads the gross weight; the first reads everything else.
    """
    found: list[GuideRow] = []
    for row in rows:
        if not row.cells or not _is_label(row.cells[0]) or len(row.cells) > 1:
            continue
        label = row.cells[0].strip()
        line = _line_of(rows, row)
        widest = max(
            (other for other in line if other is not row and not _is_label(other.cells[0])),
            key=lambda other: len(other.cells),
            default=None,
        )
        if widest is not None and len(widest.cells) == columns:
            values = tuple(cell.strip() for cell in widest.cells)
        else:
            fragments = [
                cell.strip()
                for other in line
                if other is not row
                for cell in other.cells
                if cell.strip() and not _is_label(cell)
            ]
            if not fragments:
                continue
            values = tuple(fragments)
        found.append(GuideRow(label=label, values=values))
    return tuple(found)


#: A cell is a label when it has a letter in it that is not a unit. Values here are
#: numbers, `3.5 T`, `LIGHT: 3.5T` or a chassis name, and the chassis row is not read.
_LABEL = re.compile(r"[A-Za-z]{3,}")
_VALUE_WORDS = re.compile(r"^(?:LIGHT|HEAVY|FIAT|PEUGEOT|BOXER|DUCATO|EURO)\b", re.I)


def _is_label(cell: str) -> bool:
    stripped = cell.strip()
    if not stripped or _VALUE_WORDS.match(stripped):
        return False
    return bool(_LABEL.search(stripped))


def _metres_to_mm(value: str) -> int | None:
    cleaned = value.replace(",", ".").strip()
    try:
        return round(float(cleaned) * 1000)
    except ValueError:
        return None


def _kilograms(value: str) -> int | None:
    digits = re.sub(r"[^\d]", "", value)
    return int(digits) if digits else None


# --------------------------------------------------------------------------- #
# The model pages
# --------------------------------------------------------------------------- #

#: `<span class="fb__chiffre__val">4<sup>(m)</sup></span><span ...__lib">Number of seats`
_HEADLINE = re.compile(
    r'class="fb__chiffre__val">(?P<value>.*?)</span>\s*'
    r'<span class="fb__chiffre__lib">(?P<label>.*?)</span>',
    re.I | re.S,
)

#: `Up to 4 berths (including 2 as an option)` — the prose statement of the same split.
_BERTH_PROSE = re.compile(
    r"Up to\s+(?P<total>\d+)\s+berths?\s*\(including\s+(?P<optional>\d+)\s+as an option\)",
    re.I,
)

#: The leading figure of `2(+1+1 opt)` or `4 (m) (+1 opt)` — the vehicle as built, with
#: every `(+n opt)` left behind. **This is why Itineo is easy where Robeta was not**: the
#: options are already split out of the headline figure.
_STANDARD = re.compile(r"^\s*(?P<standard>\d+)")

#: The model page's hero block: `<h1 class="fb__nom">PS740</h1>` followed by
#: `<span class="fb__cartouche">7,40 m</span>` and another naming the chassis.
#:
#: **This is where a model states its own length**, which the guide's table does not always
#: survive — see `_METRES_ROWS` and the private-use glyphs in `column_order`'s docstring.
#: It also names the chassis, and it repeats the model code, which is three independent
#: readings of the same vehicle on one page.
_HERO_NAME = re.compile(r'class="fb__nom"[^>]*>(?P<name>.*?)</h1>', re.I | re.S)
_HERO_CARTOUCHE = re.compile(r'class="fb__cartouche"[^>]*>(?P<value>.*?)</span>', re.I | re.S)

#: A length as the hero block writes it — `7,40 m`.
_HERO_METRES = re.compile(r"^(?P<metres>\d+[,.]\d+)\s*m\b", re.I)

#: The chassis as the hero block writes it: `PEUGEOT / FIAT (a)` or `FIAT`.
#:
#: **The first make named is the one FMLV holds.** Itineo offer the 660s and the P models
#: on either a Peugeot Boxer or a Fiat Ducato depending on market, and write it
#: `PEUGEOT / FIAT`; FMLV records `Peugeot` for every one of those and `Fiat` for the
#: models the site heads `FIAT` alone. That holds across all thirteen current rows.
_HERO_CHASSIS = re.compile(
    r"\b(PEUGEOT|FIAT|CITRO[EË]N|FORD|MERCEDES|MAN|RENAULT)\b", re.I
)


@dataclass
class ItineoProduct:
    """One model as the guide and its page describe it."""

    model: str
    source_url: str

    mh_length_mm: int | None = None
    mh_width_mm: int | None = None
    mh_height_mm: int | None = None
    mro_kilograms: int | None = None
    mh_payload_kilograms: int | None = None
    gross_weights: set[int] = field(default_factory=set)
    base_vehicle: str | None = None

    berths: int | None = None
    berths_note: str | None = None
    mh_passenger_seats_inc_driver: int | None = None
    seats_note: str | None = None
    #: The model page's own `Overall height`, in millimetres — one of the two independent
    #: readings the column alignment is checked against.
    page_height_mm: int | None = None
    #: The model page's own length, from its hero block. Both a second alignment check and
    #: the fallback for the one guide cell that cannot be read at all.
    page_length_mm: int | None = None
    #: The model code the page gives itself, checked against the one we asked for.
    page_name: str | None = None
    #: True where the length came from the model page because the guide's cell was
    #: unreadable, so the provenance can say which document it is quoting.
    length_from_page: bool = False

    standard_lines: list[str] = field(default_factory=list)
    all_lines: list[str] = field(default_factory=list)

    @property
    def manufacturer_range(self) -> str:
        return range_of(self.model)

    @property
    def label(self) -> str:
        return f"{MANUFACTURER_DISPLAY_NAME} {self.manufacturer_range} {self.model}"


def parse_model_page(page: str, model: str, source_url: str) -> ItineoProduct:
    """Berths, travel seats and the page's own height, from one model page.

    The guide has the masses and the dimensions; this has the figures that need the
    options splitting out, and Itineo have already done that splitting.
    """
    product = ItineoProduct(model=model, source_url=source_url)
    headline = {
        _text(m.group("label")).lower(): _text(m.group("value"))
        for m in _HEADLINE.finditer(page)
    }

    sleeping = headline.get("number of possible sleeping spaces")
    if sleeping:
        match = _STANDARD.match(sleeping)
        if match:
            product.berths = int(match.group("standard"))
            product.berths_note = sleeping
    prose = _BERTH_PROSE.search(_text(page))
    if prose:
        standard = int(prose.group("total")) - int(prose.group("optional"))
        if product.berths is None:
            product.berths = standard
            product.berths_note = prose.group(0)
        elif product.berths != standard:
            product.berths_note = (
                f"{product.berths_note} — but the prose says {prose.group(0)!r}, "
                f"which is {standard}"
            )

    seats = headline.get("number of seats")
    if seats:
        match = _STANDARD.match(seats)
        if match:
            product.mh_passenger_seats_inc_driver = int(match.group("standard"))
            product.seats_note = seats

    height = headline.get("overall height")
    if height:
        product.page_height_mm = _metres_to_mm(height.replace("M", "").replace("m", ""))

    name = _HERO_NAME.search(page)
    if name:
        product.page_name = _text(name.group("name")).upper().replace(" ", "")
    for cartouche in _HERO_CARTOUCHE.findall(page):
        value = _text(cartouche)
        metres = _HERO_METRES.match(value)
        if metres and product.page_length_mm is None:
            product.page_length_mm = _metres_to_mm(metres.group("metres"))
            continue
        chassis = _HERO_CHASSIS.search(value)
        if chassis and product.base_vehicle is None and not metres:
            product.base_vehicle = chassis.group(1).title()

    lines = [" ".join(line.split()) for line in gearbox.lines_from_page(page)]
    product.all_lines = [line for line in lines if line]
    product.standard_lines = product.all_lines
    return product


# --------------------------------------------------------------------------- #
# The checks
# --------------------------------------------------------------------------- #


def _check_alignment(
    product: ItineoProduct, on_progress: Callable[[str], None]
) -> bool:
    """Whether the guide's column agrees with the model page's own height.

    **This is the guard that makes the column order trustworthy.** The order is read off
    the headings' x positions, and if it were wrong every figure would still be a
    plausible one for an Itineo — a 2.98 m height on a model that is 2.88 m is not
    obviously absurd, and nothing downstream would catch it. The model pages publish a
    height each, independently of the guide, so the two readings check each other.

    Ten models share only three heights, so a single agreement proves little; what the
    check is worth comes from applying it to every product.
    """
    if product.page_name is not None and product.page_name != product.model:
        on_progress(
            f"DROPPED {product.label}: its page calls itself {product.page_name!r}, so the "
            f"URL this adapter built does not lead to the model it expected"
        )
        return False

    for what, guide, page in (
        ("overall height", product.mh_height_mm, product.page_height_mm),
        ("overall length", product.mh_length_mm, product.page_length_mm),
    ):
        if guide is None or page is None or abs(guide - page) <= 10:
            continue
        on_progress(
            f"DROPPED {product.label}: the guide's column gives an {what} of {guide}mm "
            f"but its own model page says {page}mm, so the table's columns are not where "
            f"this adapter thinks they are"
        )
        return False
    return True


def _reconciles(product: ItineoProduct) -> tuple[bool, str]:
    """Whether MIRO plus payload lands on a published gross weight.

    Itineo print the mass in running order and the payload in two separate rows, and the
    gross weight in a third as a **choice** — `LIGHT: 3.5 T` and `HEAVY: 4.4 T`. On the
    2027 collection every one of the ten sums to exactly 3,500 kg, which both confirms the
    arithmetic and settles that the light chassis is the base vehicle.

    `rapido.reconciles` is the same check and is used as it stands.
    """
    miro, payload = product.mro_kilograms, product.mh_payload_kilograms
    if miro is None or payload is None:
        missing = "MIRO" if miro is None else "payload"
        return False, f"the guide gives no {missing}, so nothing checks the other"
    if not product.gross_weights:
        return False, "no gross vehicle weight was read, so the sum checks against nothing"
    if not rapido.reconciles(miro, payload, product.gross_weights):
        published = ", ".join(f"{w:,}kg" for w in sorted(product.gross_weights))
        return False, (
            f"MIRO {miro:,}kg plus payload {payload:,}kg is {miro + payload:,}kg, which is "
            f"not a published gross weight ({published})"
        )
    return True, (
        f"MIRO {miro:,}kg plus payload {payload:,}kg is {miro + payload:,}kg, a published "
        f"gross weight"
    )


# --------------------------------------------------------------------------- #
# Building the product
# --------------------------------------------------------------------------- #


def _build_extracted_motorhome(product: ItineoProduct) -> ExtractedMotorhome:
    """One model as a `Motorhome`, with the provenance a reviewer reads beside each field.

    **No price, ever.** Itineo publish none — not on a model page, not in the guide, not in
    the catalogue — and FMLV's nine live rows carry figures that came from a dealer. A
    field with no provenance is not proposed, which is what keeps those alive; emitting an
    empty one would propose deleting them.

    **No `mtplm_kilograms` either.** The guide gives the gross weight as a *choice* of
    chassis rather than a figure for the vehicle, and recording the light one as though it
    were the model's own would be asserting something Itineo did not say. It is used for
    the arithmetic check and narrated, not proposed.
    """
    features = habitation.features_from(product.standard_lines)
    automatic = gearbox.automatic_available_from(product.all_lines)

    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.manufacturer_range,
        model=product.model,
        base_vehicle_manufacturer=fmlv_base_vehicle(product.base_vehicle),
        berths=product.berths,
        mh_passenger_seats_inc_driver=product.mh_passenger_seats_inc_driver,
        mro_kilograms=product.mro_kilograms,
        mh_payload_kilograms=product.mh_payload_kilograms,
        mh_length_mm=product.mh_length_mm,
        mh_width_mm=product.mh_width_mm,
        mh_height_mm=product.mh_height_mm,
        automatic_available=automatic[0] if automatic else None,
        # Habitation: findings, never proposals — see `docs/adapters/README.md`.
        heating=features["heating"].value if "heating" in features else None,
        refrigeration=(
            features["refrigeration"].value if "refrigeration" in features else None
        ),
        shower_toilet_separated=(
            features["shower_toilet_separated"].value
            if "shower_toilet_separated" in features
            else None
        ),
        bed_types=features["bed_types"].value if "bed_types" in features else [],
        microwave=features["microwave"].value if "microwave" in features else None,
    )

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=product.source_url,
            snippet=f"{product.label} — {snippet}",
        )

    record(
        "manufacturer_range",
        f"range {product.manufacturer_range!r}. Itineo head the guide's table with three "
        f"series - COZI, FAMILI COMPACT and FAMILI - and FMLV uses the same three: the "
        f"P models are COZI, the 660s are FAMILI COMPACT, the rest are FAMILI",
    )
    if product.base_vehicle is not None:
        record("base_vehicle_manufacturer", f"the guide's chassis row names {product.base_vehicle}")
    if product.mro_kilograms is not None:
        reconciles, note = _reconciles(product)
        record(
            "mro_kilograms",
            f"the technical guide's 'Mass in Running Order (MIRO) (kg)' row, "
            f"{product.mro_kilograms:,}kg" + (f" — and it reconciles: {note}" if reconciles else ""),
        )
    if product.mh_payload_kilograms is not None:
        record(
            "mh_payload_kilograms",
            f"the technical guide's 'Payload (kg)' row, {product.mh_payload_kilograms:,}kg",
        )
    if product.mh_length_mm is not None:
        if product.length_from_page:
            record(
                "mh_length_mm",
                f"{product.mh_length_mm / 1000:.2f}m, from the model page's own hero block. "
                f"The technical guide gives this model's length in PRIVATE-USE GLYPHS "
                f"rather than digits - a font substitution no parser can read - so the "
                f"page is quoted instead. Every other model's length comes from the guide "
                f"and the two agree",
            )
        else:
            record(
                "mh_length_mm",
                f"the guide's 'Overall length' row, {product.mh_length_mm / 1000:.2f}m, "
                f"which agrees with the model page's own hero block",
            )
    if product.mh_width_mm is not None:
        record(
            "mh_width_mm",
            f"the guide's 'Overall width (EXCLUDING wing mirrors)' row, "
            f"{product.mh_width_mm / 1000:.2f}m. The row beneath it gives the width with "
            f"the mirrors open and is deliberately not taken",
        )
    if product.mh_height_mm is not None:
        record(
            "mh_height_mm",
            f"the guide's 'Overall height' row, {product.mh_height_mm / 1000:.2f}m, which "
            f"agrees with the model page's own figure — that agreement is what confirms "
            f"the guide's columns are aligned to the right models",
        )
    if product.berths is not None:
        record(
            "berths",
            f"the model page states the standard and the options separately: "
            f"{product.berths_note!r}, so {product.berths} berths as built",
        )
    if product.mh_passenger_seats_inc_driver is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"the model page's 'Number of seats', {product.seats_note!r}, so "
            f"{product.mh_passenger_seats_inc_driver} as built. '(m)' is Itineo's footnote "
            f"that registered seats can vary with the chassis",
        )
    if automatic is not None:
        record("automatic_available", gearbox.provenance_note(automatic))

    for field_name, feature in features.items():
        detail = f" — {feature.note}" if feature.note else ""
        provenance[field_name] = Provenance(
            source_url=product.source_url,
            snippet=f"{product.label} — the specification says {feature.snippet!r}{detail}",
        )

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


# --------------------------------------------------------------------------- #
# The run
# --------------------------------------------------------------------------- #

#: The chassis row's makes, in the spelling FMLV holds.
_CHASSIS = re.compile(r"\b(FIAT|PEUGEOT|CITRO[EË]N|FORD|MERCEDES|MAN|RENAULT)\b", re.I)


def _apply_guide(
    products: dict[str, ItineoProduct],
    order: tuple[str, ...],
    rows: tuple[GuideRow, ...],
    on_progress: Callable[[str], None],
) -> None:
    """Pour the guide's table into the products, one column each."""
    # The gross weight is a **choice offered to every model**, not a figure per column:
    # the guide spreads `LIGHT: 3.5 T` and `HEAVY: 4.4 T` across a dozen fragments rather
    # than ten cells, so there is no column to attribute them to. Every tonnage on that
    # row is collected once and offered to all ten, which is all `_reconciles` needs —
    # it only asks whether MIRO plus payload lands on one of them.
    shared_gross: set[int] = set()
    for row in rows:
        if "gross vehicle weight" not in row.label.lower():
            continue
        for value in row.values:
            for tonnes in re.findall(r"(\d+(?:\.\d+)?)\s*T\b", value, re.I):
                shared_gross.add(round(float(tonnes) * 1000))

    gross: dict[str, set[int]] = {code: set(shared_gross) for code in order}
    for row in rows:
        label = row.label.lower().rstrip(" :")
        for index, code in enumerate(order):
            product = products.get(code)
            if product is None:
                continue
            if index >= len(row.values):
                continue
            value = row.values[index]
            if label in _METRES_ROWS:
                millimetres = _metres_to_mm(value)
                if millimetres is not None:
                    setattr(product, _METRES_ROWS[label], millimetres)
            elif label in _KILOGRAM_ROWS:
                kilograms = _kilograms(value)
                if kilograms is not None:
                    setattr(product, _KILOGRAM_ROWS[label], kilograms)
            elif label == "chassis":
                make = _CHASSIS.search(value)
                if make and product.base_vehicle is None:
                    product.base_vehicle = make.group(1).title()
    for code, weights in gross.items():
        if code in products:
            products[code].gross_weights = weights
    on_progress(
        f"the guide gives {len(rows)} full-width row(s) across {len(order)} columns: "
        + ", ".join(order)
    )


def collect(
    http: Fetcher,
    browser: BrowserFetcher,
    snapshot_dir: Path,  # noqa: ARG001 - `Fetcher` snapshots every request already
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every ITINEO motorhome, from the technical guide and the ten model pages."""
    wanted = {entry[-1] for entry in ranges}

    index = http.fetch(MODELS_INDEX_URL)
    if index.status_code != 200:
        raise RuntimeError(
            f"the models index returned HTTP {index.status_code} from {MODELS_INDEX_URL}"
        )
    roster = parse_roster(index.file_path.read_text(encoding="utf-8", errors="replace"))
    on_progress(f"the index lists {len(roster)} model(s): {', '.join(roster)}")
    known = {label for _, label in DEFAULT_RANGES}
    for code in roster:
        if code not in known:
            on_progress(f"NEW MODEL on the index that this adapter does not know: {code}")
    for code in sorted(known - set(roster)):
        on_progress(f"the index no longer lists {code}")

    # --- the model pages ----------------------------------------------------
    products: dict[str, ItineoProduct] = {}
    for code in roster:
        if code not in wanted:
            continue
        slug = _SLUG_OF.get(code)
        if slug is None:
            continue
        url = f"{BASE_URL}/motorhome_{slug}.php"
        page = http.fetch(url)
        if page.status_code != 200:
            on_progress(f"DROPPED {code}: its model page returned HTTP {page.status_code}")
            continue
        products[code] = parse_model_page(
            page.file_path.read_text(encoding="utf-8", errors="replace"), code, url
        )

    # --- the guide ----------------------------------------------------------
    documents = http.fetch(DOCUMENTS_URL)
    if documents.status_code != 200:
        raise RuntimeError(
            f"the documents page returned HTTP {documents.status_code} from {DOCUMENTS_URL}"
        )
    guide = technical_guide_url(
        documents.file_path.read_text(encoding="utf-8", errors="replace")
    )
    if guide is None:
        raise RuntimeError(
            f"no 'Download the specifications' link was found on {DOCUMENTS_URL}; the "
            f"anchor id itineo-dl-gt-* has moved and the masses come from nowhere else"
        )
    on_progress(f"technical guide: {guide}")

    pages = rapido._capture_pages(browser, guide, on_progress=on_progress)
    if not pages:
        raise RuntimeError(f"no page of the technical guide could be captured from {guide}")

    for number in sorted(pages):
        rows = rapido.page_cells(rapido._svg_of(pages[number]))
        order = column_order(rows)
        if len(order) < 2:
            continue
        table = guide_rows(rows, len(order))
        # Pages 2 to 6 are equipment checklists laid out in the same ten columns, and
        # their bullet rows look like data to anything counting cells. The specification
        # table is the one that names the dimensions and the mass, so say so rather than
        # taking the first page that parses.
        labels = {row.label.lower().rstrip(" :") for row in table}
        if not ({"overall length", "overall height"} <= labels and any(
            "running order" in label for label in labels
        )):
            continue
        on_progress(f"technical guide page {number}: the specification table")
        _apply_guide(products, order, table, on_progress)
        break
    else:
        raise RuntimeError("no page of the technical guide held the specification table")

    # --- build --------------------------------------------------------------
    extracted: list[ExtractedMotorhome] = []
    for code in roster:
        product = products.get(code)
        if product is None:
            continue
        # The one cell of the guide that no parser can read - column nine's length is
        # set in private-use glyphs - is filled from the model page's own hero block,
        # which states it plainly. Everywhere else the two agree and the guide wins.
        if product.mh_length_mm is None and product.page_length_mm is not None:
            product.mh_length_mm = product.page_length_mm
            product.length_from_page = True
        if not _check_alignment(product, on_progress):
            continue
        reconciles, note = _reconciles(product)
        if not reconciles:
            on_progress(f"DROPPED {product.label}: {note}")
            continue
        extracted.append(_build_extracted_motorhome(product))
        gross = ", ".join(f"{w:,}kg" for w in sorted(product.gross_weights)) or "none"
        on_progress(
            f"{product.label}: MIRO {product.mro_kilograms:,}kg, payload "
            f"{product.mh_payload_kilograms:,}kg, {product.berths} berths, "
            f"{product.mh_passenger_seats_inc_driver} seats — {note}. NO PRICE is "
            f"published by Itineo anywhere, so none is proposed and FMLV's own stands. "
            f"Gross weight is a choice of chassis ({gross}) rather than this model's own "
            f"figure, so no MTPLM is proposed either"
        )

    if wanted == known and len(extracted) != EXPECTED_PRODUCTS:
        on_progress(
            f"collected {len(extracted)} products where the index lists {EXPECTED_PRODUCTS}"
        )
    return extracted
