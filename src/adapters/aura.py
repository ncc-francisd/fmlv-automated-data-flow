"""AURA (auracampervans.co.uk) — Hobby, rebadged for the UK.

See `docs/adapters/aura.md` for the survey. Hobby is no longer sold in Britain under its
own name; AURA is the badge, and the vehicles are Hobby's. **This module is the motorhome
and campervan half**; `aura_caravan.py` is the other, and imports its parsing from here.

**The join key is `manufacturer = Hobby` with the display name `AURA`.** NCC id 243 is a
*different* Aura — the brand as it was when it had its own vehicles — and its ten products
sit in the very same export under `manufacturer = AURA`, every one deactivated. The
manufacturer column separates them, and so does `active`; but the **display name is part
of the adapter key** regardless, because NCC id 37 is also `Hobby`.

**What the site is good for, and what it is not.**

* **Motorhomes and campervans: good.** Each layout block publishes MTPLM, MIRO *and*
  payload, so `mtplm - miro == payload` can be checked per product without a second
  source — it holds on all thirteen. The masses agree with FMLV on twelve of the thirteen.
* **Caravans: weaker.** Those pages publish no payload at all, so there is nothing to
  check a parse against, and their masses disagree with FMLV on every layout. See
  `aura_caravan.py`.
* **Prices: never.** The site carries only range-level `from` figures, and they do not
  match any FMLV row at the entry end — motorhomes advertise from £83,995 where the
  cheapest layout is £85,795. Prices come from the importer's own lists.

**The site lags, and that is the thing to hold on to.** Its footer reads 2026 where
Hobby's own site is already on 2027, and the requester's ruling of 7 October 2026 is that
Mike Lake's spreadsheets are authoritative because they are defensible. So this adapter
proposes what the site publishes *where our own rules say the site is right* — berths,
belts, masses — and leaves the rest alone.

**Three things the site says that FMLV gets wrong**, each a settled rule rather than a
judgement:

* **Berths read `3 (up to 4)`** and FMLV holds the upper figure on seven of thirteen. The
  rule takes the lower: the extra berths need an option.
* **The OnTour A 720 GFM reads `Seat Belts 6 (inc x2 lap belts)`.** A lap belt is not a
  travel seat, so that is four, not the six FMLV holds.
* **The campervan Prestige 640 ET reads MIRO 3120** against FMLV's 3032.

**Every layout block is rendered twice** on these pages — once in a slider and once in a
dialog — so a parser that does not dedupe reports each product two or three times.
"""

from __future__ import annotations

import html as htmllib
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from src.adapters.base import ExtractedMotorhome, Provenance, fmlv_base_vehicle
from src.fetch.browser import BrowserFetcher
from src.fetch.http import Fetcher
from src.product_model.enums import BodyType
from src.product_model.model import Motorhome
from src.vehicle_class import VehicleClass

__all__ = [
    "BASE_URL",
    "DEFAULT_RANGES",
    "EXPECTED_LAYOUTS",
    "FIRST_EDITION",
    "HIGH_TOP_ABOVE_MM",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "PAGES",
    "VEHICLE_CLASS",
    "AuraLayout",
    "FMLV_MODEL_NAMES",
    "Specification",
    "AURA_HEADING",
    "collect",
    "columns_of",
    "lower_of_a_range",
    "parse_layouts",
    "three_point_belts",
    "visible_text",
]

#: The settled campervan threshold, shared with every other adapter that derives one.
HIGH_TOP_ABOVE_MM = 2300

BASE_URL = "https://www.auracampervans.co.uk"
MANUFACTURER = "Hobby"
MANUFACTURER_DISPLAY_NAME = "AURA"
VEHICLE_CLASS = VehicleClass.MOTORHOME


@dataclass(frozen=True)
class _Page:
    """One layout page, and the FMLV range and base vehicle its layouts carry."""

    path: str
    fmlv_range: str
    base_vehicle: str
    body_type: BodyType


#: **The base vehicle is not derivable from the range name and must be declared.** OnTour
#: *C* is a Citroën and OnTour *T* and *A* are Fiats, then the campervans go back to
#: Citroën — confirmed against the importer's own list, which names the make per layout.
PAGES: tuple[_Page, ...] = (
    _Page("aura-motorhomes-ontour-c-layouts.php", "OnTour C", "Citroën",
          BodyType.COACH_BUILT_LOW_PROFILE),
    _Page("aura-motorhomes-ontour-t-layouts.php", "OnTour T", "Fiat",
          BodyType.COACH_BUILT_LOW_PROFILE),
    _Page("aura-motorhomes-ontour-a-layouts.php", "OnTour A", "Fiat",
          BodyType.COACH_BUILT_OVER_CAB_BED),
    _Page("aura-motorhomes-prestige-t-layouts.php", "Prestige T", "Fiat",
          BodyType.COACH_BUILT_LOW_PROFILE),
    _Page("aura-motorhomes-maxia-layouts.php", "Maxia T", "Fiat",
          BodyType.COACH_BUILT_LOW_PROFILE),
    _Page("aura-campervans-ontour-layouts.php", "OnTour", "Citroën", BodyType.CAMPERVAN),
    _Page("aura-campervans-prestige-layouts.php", "Prestige", "Citroën", BodyType.CAMPERVAN),
)

#: **Twenty-three**: thirteen layouts, ten of which are published a second time badged
#: `First Edition`. FMLV held only the thirteen until 8 October 2026, because this
#: adapter had been collapsing each pair into one.
EXPECTED_LAYOUTS = 23

DEFAULT_RANGES: tuple[tuple[str, str], ...] = tuple(
    (page.path, page.fmlv_range) for page in PAGES
)

_BY_LABEL = {page.fmlv_range: page for page in PAGES}

#: **Never read.** Individual used and ex-demo vehicles at their own prices — the trap
#: `vantage.py` documents.
STOCK_PAGES = ("aura-ex-display-demo-campervans.php",)


def visible_text(page_html: str) -> str:
    """The page's text with every tag boundary marked by a pipe.

    These pages are a run of `Label value` pairs inside separate elements, with no table
    around them, so the boundaries are the only thing separating one field from the next.
    """
    body = re.sub(
        r"(?is)<(script|style|head|nav|footer)\b.*?</\1>", " ", htmllib.unescape(page_html)
    )
    collapsed = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", body))
    return re.sub(r"(?:\s*\|\s*)+", " | ", collapsed)


def lower_of_a_range(value: str) -> int | None:
    """`3 (up to 4)` is three berths, not four.

    The settled rule in `docs/adapters/README.md`: a berth range takes the lower figure,
    because the extra berths need an option. FMLV holds the upper figure on seven of the
    thirteen, which is what makes this worth its own function and its own test.
    """
    match = re.match(r"\s*(\d+)", value)
    return int(match.group(1)) if match else None


def three_point_belts(value: str) -> int | None:
    """Belts that are actually travel seats — lap belts do not count.

    The OnTour A 720 GFM states `6 (inc x2 lap belts)`. `docs/adapters/README.md` is
    explicit that a lap belt is not a safe adult travel seat, so that vehicle has **four**,
    and FMLV's six is wrong. Stated as a subtraction rather than a hardcoded four, so a
    layout that gains or loses a lap belt still reads correctly.
    """
    total = re.match(r"\s*(\d+)", value)
    if not total:
        return None
    lap = re.search(r"(?:inc\.?\s*)?x?\s*(\d+)\s*lap\s*belts?", value, re.I)
    return int(total.group(1)) - (int(lap.group(1)) if lap else 0)


#: **FMLV's spelling, where the site's differs.** The site writes `700 F` and `700 FH`
#: where FMLV holds `700F` and `700FH`, and the space is not cosmetic: `700 FH` failed to
#: match its FMLV row at all, arriving as a new product beside a disappearance notice for
#: the row it was meant to update.
FMLV_MODEL_NAMES: dict[str, str] = {
    "700 F": "700F",
    "700 FH": "700FH",
}


@dataclass(frozen=True)
class Specification:
    """One layout block from a motorhome or campervan page."""

    berths: int | None = None
    travel_seats: int | None = None
    length_mm: int | None = None
    width_mm: int | None = None
    height_mm: int | None = None
    mtplm_kilograms: int | None = None
    mro_kilograms: int | None = None
    published_payload_kilograms: int | None = None


@dataclass(frozen=True)
class AuraLayout:
    """One layout: how the page heads it, and the figures beneath it."""

    fmlv_range: str
    fmlv_model: str
    spec: Specification
    #: Whether the page badges this one `First Edition`. The model name already carries
    #: the badge; this is kept so the provenance can say where the name came from.
    first_edition: bool = False

    @property
    def label(self) -> str:
        return f"{self.fmlv_range} {self.fmlv_model}"


#: Dimensions on these pages are centimetres (`Length 676cm`); the caravan pages use
#: metres. Masses are kilograms, with MIRO and payload marked `*` as estimates.
_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("berths", r"Berths", "range"),
    ("travel_seats", r"Seat Belts", "belts"),
    ("length_mm", r"Length", "cm"),
    ("width_mm", r"Width", "cm"),
    ("height_mm", r"Height", "cm"),
    ("mtplm_kilograms", r"MTPLM", "kg"),
    ("mro_kilograms", r"MIRO", "kg"),
    ("published_payload_kilograms", r"Payload", "kg"),
)


def _centimetres(value: str) -> int | None:
    match = re.match(r"\s*([\d.]+)\s*cm", value)
    return round(float(match.group(1)) * 10) if match else None


def _kilograms(value: str) -> int | None:
    match = re.match(r"\s*([\d,]+)", value)
    return int(match.group(1).replace(",", "")) if match else None


def _read(kind: str, value: str) -> int | None:
    if kind == "cm":
        return _centimetres(value)
    if kind == "range":
        return lower_of_a_range(value)
    if kind == "belts":
        return three_point_belts(value)
    return _kilograms(value)


#: A layout heading cell: `AURA OnTour C 680 GE`, or `AURA Prestige 640 ET`. The trailing
#: `First Edition` is a badge, not part of the name, and sits in its own element.
#: A heading cell, in the four shapes the site actually uses:
#:
#: * `AURA OnTour C 680 GE` — the common one;
#: * `AURA Prestige 710 GE | First Edition` — the badge shares the cell, so the pattern
#:   must not be anchored to the end of it;
#: * `AURA Prestige | 640 ET` — the range and the model are separate elements;
#: * `Beachy 360` — the caravan pages drop the `AURA` prefix altogether.
#:
#: **Only the model is taken from here.** The FMLV range comes from the page, because the
#: headings do not carry it reliably: the Prestige T and Maxia T pages both head their
#: layouts `AURA Prestige …` and `AURA Maxia …`, without the `T`.
AURA_HEADING = re.compile(
    r"(?:AURA|OnTour|Prestige|Maxia|DeLuxe|Beachy)\b[^|]*?\|?\s*"
    r"(?P<model>\d{3}\s?[A-Za-z]{0,4}\+?)",
    re.I,
)

_TABLE = re.compile(r"(?is)<table\b.*?</table>")
_ROW = re.compile(r"(?is)<tr\b.*?</tr>")
_CELL = re.compile(r"(?is)<t[dh]\b[^>]*>(.*?)</t[dh]>")


def _cell_text(cell_html: str) -> str:
    """One table cell as plain text, with element boundaries kept as pipes."""
    collapsed = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", htmllib.unescape(cell_html)))
    return re.sub(r"(?:\s*\|\s*)+", " | ", collapsed).strip(" |")


def columns_of(page_html: str) -> list[tuple[str, str]]:
    """Every `(heading, figures)` pair on the page, read **column by column**.

    **This is the shape of the whole site and the reason it cannot be parsed from
    flattened text.** Each table lays two layouts side by side — their names in one row,
    their floorplans in the next, their figures in the one after — so reading the page as
    a stream pairs the second layout's name with the first one's figures. On the Maxia
    page that silently gave the 740 WE the 710 GE's weights, which is precisely the
    failure `docs/adapters/README.md` describes as plausible and internally consistent.

    Pairs are returned in page order, and a table whose heading and figure counts disagree
    yields nothing rather than a guess at the alignment.
    """
    pairs: list[tuple[str, str]] = []
    for table in _TABLE.findall(page_html):
        headings: list[str] = []
        figures: list[str] = []
        for row in _ROW.findall(table):
            cells = [_cell_text(c) for c in _CELL.findall(row)]
            named = [c for c in cells if AURA_HEADING.search(c)]
            if named:
                # **Not every cell in the row need be a heading.** A `First Edition` badge
                # shares the row on several pages, and a single-layout table pairs one
                # heading with one block — requiring the whole row to be names dropped the
                # Prestige T and the Prestige campervan entirely.
                headings = named
                continue
            spec = [c for c in cells if re.search(r"\bBerths\b", c)]
            if spec:
                figures = spec
        if not headings or not figures:
            continue
        if len(headings) != len(figures):
            # A cardinality failure. Drop the table rather than align by guesswork.
            continue
        pairs.extend(zip(headings, figures))
    return pairs


#: The badge AURA appends to a layout's heading to mark the launch edition.
FIRST_EDITION = "First Edition"

_FIRST_EDITION = re.compile(r"first\s*edition", re.I)


def parse_layouts(page_html: str, fmlv_range: str) -> list[AuraLayout]:
    """Every distinct layout on one page, with the figures from its own column.

    **A `First Edition` is its own product, not a duplicate.** Ten of the thirteen layouts
    are published twice — once badged `First Edition` and once not — with *byte-identical*
    weights and dimensions, and for a while this adapter collapsed each pair into one. They
    are two products by the settled rule in `docs/adapters/README.md`: a trim or option
    package is not a second product *"unless that extra package comes with a different name
    to it … then it's got a different name, it's a different model"*. `First Edition` is
    such a name, and AURA price the two differently — the edition is between £1,800 and
    £11,000 cheaper on every one of the ten.

    So the key is the model **and** the badge. The three with no twin — OnTour T 700 FH,
    OnTour T 710 GE and OnTour A 720 GFM — are exactly the three absent from AURA's own
    First Edition price list, which is the roster checking out against the site.

    **Still deduplicated within each of the two**, because the tables repeat: a layout
    appears in a slider and again in a dialog.
    """
    found: dict[tuple[str, bool], AuraLayout] = {}
    for heading, figures in columns_of(page_html):
        match = AURA_HEADING.search(heading)
        if match is None:
            continue
        model = re.sub(r"\s+", " ", match.group("model")).strip()
        model = FMLV_MODEL_NAMES.get(model, model)
        first_edition = bool(_FIRST_EDITION.search(heading))
        if first_edition:
            model = f"{model} {FIRST_EDITION}"
        if (model, first_edition) in found:
            continue
        values: dict[str, int] = {}
        for field, label, kind in _FIELDS:
            cell = re.search(rf"(?:^|\|)\s*{label}\s+([^|]+?)\s*(?:\||$)", figures)
            if cell:
                value = _read(kind, cell.group(1))
                if value is not None:
                    values[field] = value
        if not values:
            continue
        found[model, first_edition] = AuraLayout(
            fmlv_range, model, Specification(**values), first_edition=first_edition
        )
    return list(found.values())


def _reconciles(spec: Specification) -> tuple[bool, str]:
    """`mtplm - miro == payload`, all three of which these pages publish.

    The caravan pages publish no payload and so have no such check; this one holds on all
    thirteen motorhomes and campervans.
    """
    mtplm, mro, payload = (
        spec.mtplm_kilograms,
        spec.mro_kilograms,
        spec.published_payload_kilograms,
    )
    if mtplm is None or mro is None:
        return False, "no MTPLM or no MIRO in the block"
    if payload is None:
        return False, "no published payload to check the two masses against"
    if mtplm - mro != payload:
        return (
            False,
            f"MTPLM {mtplm} - MIRO {mro} = {mtplm - mro}kg against a published payload of "
            f"{payload}kg",
        )
    return True, f"MTPLM {mtplm} - MIRO {mro} = payload {payload}kg"


def _body_type_for(page: _Page, spec: Specification) -> BodyType | None:
    """The body type, **only where the site settles it.**

    For a campervan the height does: over `HIGH_TOP_ABOVE_MM` it is a high top, which is
    what FMLV already holds for all three at 2670mm. For a coach-built it does not, and
    nothing is proposed — the OnTour A describes an over-cab bed as an *option*, so the
    range name alone cannot tell a low profile from an over-cab, and FMLV's own value is
    better than a guess made from a page title.
    """
    if page.body_type is not BodyType.CAMPERVAN:
        return None
    if spec.height_mm is None:
        return None
    return (
        BodyType.CAMPERVAN_HIGH_TOP
        if spec.height_mm > HIGH_TOP_ABOVE_MM
        else BodyType.CAMPERVAN
    )


def build_extracted(layout: AuraLayout, page: _Page, basis: str) -> ExtractedMotorhome:
    """One AURA motorhome or campervan, with provenance on everything it proposes."""
    spec = layout.spec
    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=layout.fmlv_range,
        model=layout.fmlv_model,
        # **Routed through the shared helper**, never spelled locally: FMLV holds
        # `Citroën` with the diaeresis, and an adapter that picks its own spelling
        # proposes a pointless rename on every product it touches.
        base_vehicle_manufacturer=fmlv_base_vehicle(page.base_vehicle),
        berths=spec.berths,
        mh_passenger_seats_inc_driver=spec.travel_seats,
        # The site publishes only range-level "from" prices, which match no FMLV row.
        rrp_pounds=None,
        mh_length_mm=spec.length_mm,
        mh_width_mm=spec.width_mm,
        mh_height_mm=spec.height_mm,
        mtplm_kilograms=spec.mtplm_kilograms,
        mro_kilograms=spec.mro_kilograms,
        mh_payload_kilograms=spec.published_payload_kilograms,
        body_type=_body_type_for(page, spec),
    )

    provenance: dict[str, Provenance] = {}

    def record(field: str, snippet: str) -> None:
        provenance[field] = Provenance(
            source_url=f"{BASE_URL}/{page.path}", snippet=f"{layout.label} — {snippet}"
        )

    if layout.first_edition:
        record(
            "model",
            f"the page badges this layout {FIRST_EDITION!r}. It is a product rather than an "
            f"option because it carries a name of its own — the settled rule — and AURA "
            f"price it separately, below the unbadged model, though the two publish "
            f"identical weights and dimensions",
        )
    record("base_vehicle_manufacturer", f"{page.base_vehicle}, which the importer's own "
                                        f"list names per layout — it is not derivable from "
                                        f"the range, since OnTour C is a Citroën where "
                                        f"OnTour T and A are Fiats")
    if spec.berths is not None:
        record(
            "berths",
            f"{spec.berths} — the page states the standard berths and an optional upper "
            f"figure, and the settled rule takes the lower",
        )
    if spec.travel_seats is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"{spec.travel_seats} three-point belts. A lap belt is not a travel seat, so "
            f"any the page counts in its total are subtracted",
        )
    # **No dimension is proposed.** The site publishes centimetres where FMLV holds
    # millimetres, so every length comes back rounded: 676cm against FMLV's 6759mm, 288cm
    # against 2883. Proposing those would be 30 rows of noise asking a reviewer to make
    # good data worse. The masses are exact kilograms on both sides, so they are proposed.
    for field, label in (
        ("mtplm_kilograms", "MTPLM"),
        ("mro_kilograms", "MIRO, which the page marks an estimate"),
    ):
        value = getattr(motorhome, field)
        if value is not None:
            record(field, f"{value} from the page's '{label}'")
    if spec.published_payload_kilograms is not None:
        record("mh_payload_kilograms", f"{spec.published_payload_kilograms}kg — {basis}")
    if motorhome.body_type is not None:
        record(
            "body_type",
            f"a campervan {spec.height_mm}mm tall, "
            + (
                f"over the {HIGH_TOP_ABOVE_MM}mm high-top threshold"
                if motorhome.body_type is BodyType.CAMPERVAN_HIGH_TOP
                else f"under the {HIGH_TOP_ABOVE_MM}mm high-top threshold"
            ),
        )
    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


def collect(
    http: Fetcher,
    browser: BrowserFetcher,  # noqa: ARG001
    snapshot_dir: Path,  # noqa: ARG001
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every AURA motorhome and campervan, one fetch per layout page."""
    wanted = {label for _path, label in ranges}
    pages = [page for page in PAGES if page.fmlv_range in wanted]

    results: list[ExtractedMotorhome] = []
    for page in pages:
        url = f"{BASE_URL}/{page.path}"
        result = http.fetch(url)
        if result.status_code != 200:
            on_progress(f"[{page.fmlv_range}] SKIPPED: {url} returned {result.status_code}")
            continue
        html = result.file_path.read_text(encoding="utf-8", errors="replace")

        layouts = parse_layouts(html, page.fmlv_range)
        if not layouts:
            on_progress(
                f"[{page.fmlv_range}] SKIPPED: no layout block found on {url} — the page "
                f"shape has changed"
            )
            continue
        for layout in layouts:
            reconciles, basis = _reconciles(layout.spec)
            if not reconciles:
                on_progress(f"[{page.fmlv_range}] {layout.fmlv_model} — DROPPED: {basis}")
                continue
            results.append(build_extracted(layout, page, basis))
            on_progress(
                f"[{page.fmlv_range}] {layout.fmlv_model} — read: "
                f"{layout.spec.length_mm}mm, {layout.spec.mtplm_kilograms}kg, "
                f"{layout.spec.berths} berth, {layout.spec.travel_seats} belted seats"
            )

    on_progress(
        "NO PRICE IS PROPOSED. The site carries only range-level 'from' figures and they "
        "match no FMLV row at the entry end — motorhomes advertise from GBP83,995 where "
        "the cheapest layout is GBP85,795. Prices come from the importer's own lists."
    )
    on_progress(
        "BERTHS ARE THE LOWER OF THE PUBLISHED RANGE and SEATS COUNT THREE-POINT BELTS "
        "ONLY. The pages read 'Berths 3 (up to 4)', where FMLV holds the upper figure on "
        "seven of thirteen; and the OnTour A 720 GFM reads 'Seat Belts 6 (inc x2 lap "
        "belts)', which is four travel seats, not the six FMLV holds. Both are settled "
        "rules in docs/adapters/README.md rather than judgements made here."
    )
    if len(pages) == len(PAGES) and len(results) != EXPECTED_LAYOUTS:
        on_progress(
            f"expected {EXPECTED_LAYOUTS} layouts and collected {len(results)} — check "
            f"whether the range has changed"
        )
    on_progress(f"collected {len(results)} AURA motorhome(s) and campervan(s)")
    return results
