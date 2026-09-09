"""Hymer (hymer.com) — the Erwin Hymer Group's own brand, and the last of them.

See `docs/adapters/hymer.md` for the survey. Motorhomes and campervans, no caravans. The
biggest EHG roster this project handles: **25 layouts across 11 range pages**, against 42
products FMLV still holds.

**The `/gb/en/` edition is a real market edition** and differs from `/de/en/`, so it is the
one read. Same shape as Dethleffs, Carado and the Eriba Car — `has-columns--1+`
specification tables, a layout heading before each block, floorplans — and it shares the
Eriba Car's quirk of **rendering each layout's specification twice**.

**A page is not a product and a heading is not a block.** Two things make the join
awkward, and `parse_layouts` exists for them:

* A layout's name appears more than once — as a teaser near the top of the page and again
  immediately above its specification. Taking the first occurrence gives a region with no
  tables in it.
* A layout's specification then appears twice within that region, identically.

So each *specification* is attributed to the nearest heading above it, the distinct owners
are taken in order, and each layout's region runs from its own heading to the next
owner's. Duplicate tables inside a region re-state the same values and are harmless.

**The roster is a stated list of range pages, not the sitemap.** The GB sitemap's
`/motorhomes/` section is mostly category pages — `2-berth-motorhomes`,
`winterized-motorhomes`, `luxury-motorhomes` — and the navigation names ranges that have no
page in this market at all. `DEFAULT_RANGES` is therefore the roster, and `collect`
narrates a range page that stops producing layouts.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from . import habitation
from .base import (
    ExtractedMotorhome,
    Provenance,
    floorplan_provenance,
    fmlv_base_vehicle,
)

BASE_URL = "https://www.hymer.com"
MANUFACTURER = "HYMER"
MANUFACTURER_DISPLAY_NAME = "Hymer"

#: (page path, `--range` label). A **stated roster**: the sitemap's motorhome section is
#: mostly category pages and the navigation names ranges this market does not sell, so a
#: crawl would find both too much and too little. A range that vanishes from here is a
#: deliberate edit; a range that stops producing layouts is narrated by `collect`.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (
    ("/gb/en/motorhomes/hymer-b-class-masterline", "B-ML I"),
    ("/gb/en/motorhomes/hymer-b-class-masterline-t", "B-ML T"),
    ("/gb/en/motorhomes/hymer-b-class-moderncomfort-i", "B-MC I"),
    ("/gb/en/motorhomes/hymer-b-class-moderncomfort-t", "B-MC T"),
    ("/gb/en/motorhomes/hymer-exsis-t", "Exsis-t"),
    ("/gb/en/motorhomes/hymer-gt-s", "GT-S"),
    ("/gb/en/motorhomes/hymer-ml-t", "ML-T"),
    ("/gb/en/motorhomes/hymer-venture-s", "Venture S"),
    ("/gb/en/camper-vans-class-b/hymer-grand-canyon-s", "Grand Canyon S"),
    ("/gb/en/camper-vans-class-b/hymer-redwood", "Redwood"),
    ("/gb/en/camper-vans-class-b/hymer-yellowstone", "Yellowstone"),
)


@dataclass(frozen=True)
class RangeRule:
    """How one of the site's ranges maps onto FMLV, and what body its layouts have.

    FMLV is inconsistent about where the body letter sits and whether it is spaced —
    `B-Class MasterLine` / `I 780` against `B-Class ModernComfort I` / `I600` — so the
    template is per range rather than a rule. Checked against the real export for
    manufacturer 86 on 9 September 2026.
    """

    #: `manufacturer_range` as the export spells it.
    fmlv_range: str
    #: `{code}` is the layout's published number. `Venture S` has none and is a literal.
    model_template: str
    #: `None` for a campervan, whose type its height and roof decide.
    body_type: BodyType | None


#: Site range -> FMLV. The site's own label is never what FMLV holds.
RANGE_MAP: dict[str, RangeRule] = {
    "B-ML I": RangeRule("B-Class MasterLine", "I {code}", BodyType.A_CLASS),
    "B-ML T": RangeRule("B-Class MasterLine", "T {code}", BodyType.COACH_BUILT_LOW_PROFILE),
    "B-MC I": RangeRule("B-Class ModernComfort I", "I{code}", BodyType.A_CLASS),
    "B-MC T": RangeRule(
        "B-Class ModernComfort T", "T{code}", BodyType.COACH_BUILT_LOW_PROFILE
    ),
    "Exsis-t": RangeRule("Exsis-T", "{code}", BodyType.COACH_BUILT_LOW_PROFILE),
    "GT-S": RangeRule("GT-S", "{code}", BodyType.COACH_BUILT_LOW_PROFILE),
    "ML-T": RangeRule("ML-T", "{code}", BodyType.COACH_BUILT_LOW_PROFILE),
    "Venture S": RangeRule("Venture", "S", BodyType.COACH_BUILT_LOW_PROFILE),
    "Grand Canyon S": RangeRule("Grand Canyon S", "{code}", None),
    "Redwood": RangeRule("Redwood", "{code}", None),
    "Yellowstone": RangeRule("Yellowstone", "{code}", None),
}

#: Above this a campervan is a high top — the settled threshold.
HIGH_TOP_ABOVE_MM = 2300

#: The marker Hymer put on a figure that is a paid upgrade rather than the standard fit.
#: It decides three things: the standard berth count, the standard seat count, and — the
#: one that changes what a vehicle *is* — whether a rising roof is fitted as standard.
OPTIONAL_MARK = "○"


# --------------------------------------------------------------------------- #
# The page
# --------------------------------------------------------------------------- #

_TABLE = re.compile(r"<table[^>]*has-columns--1\+[^>]*>(?P<body>.*?)</table>", re.S)
_ROW = re.compile(r"<tr[^>]*>(?P<row>.*?)</tr>", re.S)
_CELL = re.compile(r"<td[^>]*>(?P<cell>.*?)</td>", re.S)

#: Any heading, at any level — Hymer uses `h2` on one range page and `h4` on another, so
#: the level cannot be part of the pattern.
_HEADING = re.compile(r"<h[1-6][^>]*>(?P<text>.*?)</h[1-6]>", re.S)

#: The row every specification block has, and the anchor the blocks are found by. Chosen
#: over the price because `Price` also appears in option tables.
BLOCK_ANCHOR = "Mass in running order"

LABEL_PRICE = "Price"
LABEL_CHASSIS = "Standard chassis"
LABEL_DIMENSIONS = "Length / Width / Height (cm)"
LABEL_MRO = "Mass in running order (-/+ 5%) (kg)*"
LABEL_MTPLM = "Technically permissible maximum laden mass (kg)*"
LABEL_SEATS = "Permitted number of seats (including driver) *"
LABEL_BERTHS = "Berths"
LABEL_ROOF = "Roof type"
LABEL_HEATING = "Standard heating"
LABEL_REFRIGERATION = "Fridge volume (freezer compartment) (l)"
LABEL_GARAGE = "Overall clearance storage- / garage door W x H (cm)"

#: Sits beside the two masses, exactly where payload would, and is not payload. Every EHG
#: brand publishes it and every one of these adapters names it so the mistake is documented.
LABEL_NOT_PAYLOAD = "Manufacturer-specified mass for optional equipment (kg)*"

#: The only rows fed to `habitation`. An allow-list for the reason
#: `carado.HABITATION_SPEC_LABELS` is one: a bed *dimension* row's label enumerates the beds
#: a vehicle might have rather than stating what is fitted, and reading one gives a product
#: a bed type off a measurement heading.
HABITATION_SPEC_LABELS: frozenset[str] = frozenset({LABEL_HEATING, LABEL_REFRIGERATION})


def _clean(markup: str) -> str:
    """Cell text, entities resolved.

    `html.unescape` matters here and did not on the sibling sites: Hymer's labels carry
    `&nbsp;` inside them — `Price&nbsp;&nbsp;` and `Mass in running order (-/+ 5%)&nbsp;(kg)*`
    — so a lookup on the printed label misses without it.
    """
    markup = re.sub(r"<sup[^>]*>.*?</sup>", " ", markup, flags=re.S)
    markup = re.sub(r"<button.*?</button>", " ", markup, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", markup))
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def _first_int(value: str) -> int | None:
    """The first whole number — the standard figure of a `'2 - 4 (○)'` pair."""
    match = re.search(r"\d[\d,]*", value)
    return int(match.group(0).replace(",", "")) if match else None


def _band(value: str) -> tuple[int, int] | None:
    """`'2824 (2683 - 2965)*'` -> `(2683, 2965)`, the printed ±5% range."""
    match = re.search(r"\(\s*([\d,]+)\s*(?:to|-|–)\s*([\d,]+)\s*\)", value)
    if match is None:
        return None
    return int(match.group(1).replace(",", "")), int(match.group(2).replace(",", ""))


def _centimetres(value: str) -> list[int]:
    """`'659 / 222 / 279'` -> `[6590, 2220, 2790]`. Hymer quote whole centimetres."""
    return [int(n) * 10 for n in re.findall(r"\d+", value)]


@dataclass(frozen=True)
class HymerLayout:
    """One layout, from its region of a range page."""

    range_label: str
    code: str
    title: str
    specs: dict[str, str] = field(default_factory=dict)
    floorplan_path: str | None = None

    @property
    def rule(self) -> RangeRule | None:
        return RANGE_MAP.get(self.range_label)

    @property
    def fmlv_range(self) -> str:
        rule = self.rule
        return rule.fmlv_range if rule else self.range_label

    @property
    def fmlv_model(self) -> str:
        rule = self.rule
        return rule.model_template.format(code=self.code) if rule else self.code

    @property
    def rrp_pounds(self) -> int | None:
        return _first_int(self.specs.get(LABEL_PRICE, ""))

    @property
    def chassis(self) -> str | None:
        return self.specs.get(LABEL_CHASSIS) or None

    @property
    def base_vehicle_manufacturer(self) -> str | None:
        chassis = self.chassis
        return fmlv_base_vehicle(chassis.split()[0]) if chassis else None

    @property
    def _dimensions(self) -> list[int]:
        return _centimetres(self.specs.get(LABEL_DIMENSIONS, ""))

    @property
    def mh_length_mm(self) -> int | None:
        found = self._dimensions
        return found[0] if len(found) > 0 else None

    @property
    def mh_width_mm(self) -> int | None:
        found = self._dimensions
        return found[1] if len(found) > 1 else None

    @property
    def mh_height_mm(self) -> int | None:
        found = self._dimensions
        return found[2] if len(found) > 2 else None

    @property
    def mro_kilograms(self) -> int | None:
        return _first_int(self.specs.get(LABEL_MRO, ""))

    @property
    def mro_band(self) -> tuple[int, int] | None:
        return _band(self.specs.get(LABEL_MRO, ""))

    @property
    def mtplm_kilograms(self) -> int | None:
        return _first_int(self.specs.get(LABEL_MTPLM, ""))

    @property
    def mh_payload_kilograms(self) -> int | None:
        if self.mtplm_kilograms is None or self.mro_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mro_kilograms

    @property
    def mh_passenger_seats_inc_driver(self) -> int | None:
        return _first_int(self.specs.get(LABEL_SEATS, ""))

    @property
    def berths_published(self) -> str | None:
        return self.specs.get(LABEL_BERTHS) or None

    @property
    def berths(self) -> int | None:
        return _first_int(self.berths_published or "")

    @property
    def roof_published(self) -> str | None:
        return self.specs.get(LABEL_ROOF) or None

    @property
    def has_standard_elevating_roof(self) -> bool:
        """Whether a rising roof is fitted **as standard**, which is the only kind that
        changes what the vehicle is.

        Both campervan ranges publish `Roof type: Sleeping roof (○)`, and the circle marks
        it as a paid upgrade — so by the rule in `docs/adapters/README.md` neither is an
        elevating-roof body. FMLV currently disagrees on the Grand Canyon S; see the survey.
        """
        roof = self.roof_published or ""
        return bool(roof) and OPTIONAL_MARK not in roof and "roof" in roof.lower()

    @property
    def rear_garage(self) -> bool:
        """Whether a garage opening is published — the same test as Dethleffs and Carado."""
        return bool(self.specs.get(LABEL_GARAGE))

    @property
    def body_type(self) -> BodyType | None:
        """From the range for a motorhome, and from the roof and height for a campervan."""
        rule = self.rule
        if rule is None:
            return None
        if rule.body_type is not None:
            return rule.body_type
        if self.mh_height_mm is None:
            return None
        high_top = self.mh_height_mm > HIGH_TOP_ABOVE_MM
        if self.has_standard_elevating_roof:
            return (
                BodyType.CAMPERVAN_HIGH_TOP_ELEVATING_ROOF
                if high_top
                else BodyType.CAMPERVAN_ELEVATING_ROOF
            )
        return BodyType.CAMPERVAN_HIGH_TOP if high_top else BodyType.CAMPERVAN

    @property
    def spec_lines(self) -> list[str]:
        return [
            f"{label} {self.specs[label]}"
            for label in HABITATION_SPEC_LABELS
            if self.specs.get(label)
        ]


def layout_name(text: str, range_label: str) -> str | None:
    """The layout code in a heading, or `None` if the heading is not one.

    `Hymer Exsis-t 474` gives `474`. **`Hymer Venture S` gives `S`** — a layout with no
    number at all, which is why a pattern requiring digits misses it and why the first
    sweep of this site found 24 layouts instead of 25.
    """
    cleaned = re.sub(r"\s+", " ", text).strip()
    prefix = f"Hymer {range_label}"
    if not cleaned.lower().startswith(prefix.lower()):
        return None
    rest = cleaned[len(prefix) :].strip()
    if not rest:
        # `Hymer Venture S` — the label already carries the whole name.
        return range_label.split()[-1]
    return rest if re.fullmatch(r"[\w.\- ]{1,20}", rest) else None


def parse_layouts(page_html: str, range_label: str) -> list[HymerLayout]:
    """Every layout on one range page, each with its own figures.

    **Attributing a specification to a layout is the whole problem here.** A layout's name
    appears twice — a teaser near the top and again above its specification — and its
    specification then appears twice inside that region, identically. So:

    1. find each specification by its `Mass in running order` row;
    2. give it to the nearest heading above it, which is always the real one;
    3. take the distinct owners in order, and run each layout's region from its own
       heading to the next owner's.

    Duplicate tables inside a region simply re-state the same values, and `setdefault`
    keeps the first. Nothing has to be deduplicated and no count has to be guessed.
    """
    headings: list[tuple[int, str, str]] = []
    for match in _HEADING.finditer(page_html):
        text = _clean(match.group("text"))
        code = layout_name(text, range_label)
        if code is not None:
            headings.append((match.start(), code, text))
    if not headings:
        return []

    owners: list[tuple[int, str, str]] = []
    for anchor in (m.start() for m in re.finditer(re.escape(BLOCK_ANCHOR), page_html)):
        above = [entry for entry in headings if entry[0] < anchor]
        if not above:
            continue
        owner = above[-1]
        if owner not in owners:
            owners.append(owner)

    layouts: list[HymerLayout] = []
    for index, (start, code, title) in enumerate(owners):
        end = owners[index + 1][0] if index + 1 < len(owners) else len(page_html)
        rows: dict[str, str] = {}
        for table in _TABLE.finditer(page_html):
            if not (start <= table.start() < end):
                continue
            for row in _ROW.findall(table.group("body")):
                cells = [_clean(cell) for cell in _CELL.findall(row)]
                if len(cells) == 2 and cells[0]:
                    rows.setdefault(cells[0], cells[1])
        if rows:
            layouts.append(
                HymerLayout(
                    range_label=range_label,
                    code=code,
                    # The heading's own words, so `Hymer Venture S` does not become
                    # `Hymer Venture S S` when the label already carries the whole name.
                    title=title,
                    specs=rows,
                    floorplan_path=floorplan_for(code, page_html),
                )
            )
    return layouts


#: A layout drawing, told from the page's photography by its **resizer preset** — the
#: Carado lesson. Hymer also publish a low-fidelity SVG of the same plan under
#: `lofi-grundrisse_...`; the `wls-floorplan` one is the drawing the page shows.
_FLOORPLAN = re.compile(
    r'[^"\s]*/image-thumb__[^"\s/]*wls-floorplan[^"\s/]*/(?P<file>[^"\s/]+\.(?:png|jpe?g|svg|webp))',
    re.I,
)


def floorplan_for(code: str, page_html: str) -> str | None:
    """The drawing whose filename carries this layout's code, as a whole token.

    **A token, not a suffix.** Hymer name these three different ways on three pages —
    `hymer-exsis-t-474.jpg`, `hymer-redwood-600-hoch.png` and
    `hymer-b-ml-i-780_bis_2026.png` — so a rule anchored to the end of the stem finds the
    Exsis-t's and misses the other two. Splitting on every non-alphanumeric run and looking
    for the code among the parts finds all three, and still refuses a partial match: `600`
    does not match `6001` or `60`.

    Each drawing is published several times over, the extras being `~-~media--…--query`
    derivatives of the first. The plain one wins.
    """
    wanted = [part for part in re.split(r"[^a-z0-9]+", code.lower()) if part]
    if not wanted:
        return None
    for match in _FLOORPLAN.finditer(page_html):
        filename = match.group("file")
        if "~-~" in filename:
            continue
        stem = filename.rsplit(".", 1)[0].lower()
        parts = [part for part in re.split(r"[^a-z0-9]+", stem) if part]
        if all(part in parts for part in wanted):
            return match.group(0)
    return None


def _reconciles(layout: HymerLayout) -> bool:
    """Whether the printed ±5% band really is ±5% of the stated running order."""
    if layout.mro_kilograms is None or layout.mro_band is None:
        return True
    low, high = layout.mro_band
    return (
        abs(low - round(layout.mro_kilograms * 0.95)) <= 2
        and abs(high - round(layout.mro_kilograms * 1.05)) <= 2
    )


# --------------------------------------------------------------------------- #
# Building a product
# --------------------------------------------------------------------------- #

_FEATURE_NOTES: dict[str, str] = {
    "heating": "the heater fitted as standard",
    "refrigeration": "the specification's fridge row",
}

MICROWAVE_ABSENCE_NOTE = (
    "no mention of a microwave in the specification. Hymer itemise the kitchen down to the "
    "fridge's freezer compartment and the socket count, so the vocabulary is there and unused"
)


def build_extracted(layout: HymerLayout) -> ExtractedMotorhome:
    """One product from one layout."""
    features = habitation.features_from(layout.spec_lines)
    absent = habitation.microwave_from(layout.spec_lines) is None

    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=layout.fmlv_range,
        model=layout.fmlv_model,
        base_vehicle_manufacturer=layout.base_vehicle_manufacturer,
        body_type=layout.body_type,
        rrp_pounds=layout.rrp_pounds,
        berths=layout.berths,
        mh_passenger_seats_inc_driver=layout.mh_passenger_seats_inc_driver,
        mro_kilograms=layout.mro_kilograms,
        mtplm_kilograms=layout.mtplm_kilograms,
        mh_payload_kilograms=layout.mh_payload_kilograms,
        mh_length_mm=layout.mh_length_mm,
        mh_width_mm=layout.mh_width_mm,
        mh_height_mm=layout.mh_height_mm,
        rear_garage=layout.rear_garage,
        heating=features["heating"].value if "heating" in features else None,
        refrigeration=(
            features["refrigeration"].value if "refrigeration" in features else None
        ),
        microwave=False if absent else None,
    )

    source = BASE_URL + _page_path(layout.range_label)
    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=source, snippet=f"{layout.title} — {snippet}"
        )

    identity = (
        f"the site publishes this as '{layout.title}'; FMLV holds range "
        f"'{layout.fmlv_range}' and model '{layout.fmlv_model}'. The two halves belong "
        f"together — accept both or neither"
    )
    record("manufacturer_range", identity)
    record("model", identity)

    if layout.rrp_pounds is not None:
        record("rrp_pounds", f"Price: {layout.specs.get(LABEL_PRICE)}")
    if layout.base_vehicle_manufacturer is not None:
        record("base_vehicle_manufacturer", f"Standard chassis: {layout.chassis}")
    if layout.body_type is not None:
        if layout.rule and layout.rule.body_type is not None:
            detail = f"every {layout.fmlv_range} is a {layout.body_type.value.replace('type_', '').replace('_', ' ')}"
        else:
            roof = layout.roof_published or "none published"
            detail = (
                f"Roof type '{roof}', so a rising roof is "
                f"{'standard' if layout.has_standard_elevating_roof else 'not standard'}, "
                f"and {layout.mh_height_mm}mm is "
                f"{'above' if (layout.mh_height_mm or 0) > HIGH_TOP_ABOVE_MM else 'not above'} "
                f"the {HIGH_TOP_ABOVE_MM}mm high-top threshold"
            )
        record("body_type", detail)
    if layout.berths is not None:
        record(
            "berths",
            f"Berths '{layout.berths_published}', standard figure {layout.berths} — a "
            f"higher one marked {OPTIONAL_MARK} is an option",
        )
    if layout.mh_passenger_seats_inc_driver is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"Permitted number of seats (including driver): {layout.specs.get(LABEL_SEATS)}",
        )
    for field_name, axis in (
        ("mh_length_mm", "length"),
        ("mh_width_mm", "width"),
        ("mh_height_mm", "height"),
    ):
        if getattr(motorhome, field_name) is not None:
            record(
                field_name,
                f"Length / Width / Height (cm): '{layout.specs.get(LABEL_DIMENSIONS)}' "
                f"— the {axis}",
            )
    if layout.mtplm_kilograms is not None:
        record(
            "mtplm_kilograms",
            f"Technically permissible maximum laden mass: {layout.mtplm_kilograms}kg",
        )
    if layout.mro_kilograms is not None:
        band = (
            f" (permissible range {layout.mro_band[0]} to {layout.mro_band[1]}kg, ±5%)"
            if layout.mro_band
            else ""
        )
        record("mro_kilograms", f"Mass in running order: {layout.mro_kilograms}kg{band}")
    if layout.mh_payload_kilograms is not None:
        record(
            "mh_payload_kilograms",
            f"derived: {layout.mtplm_kilograms}kg maximum laden - {layout.mro_kilograms}kg "
            f"running order = {layout.mh_payload_kilograms}kg. Hymer publish no payload, and "
            f"their 'manufacturer-specified mass for optional equipment' is not one",
        )
    record(
        "rear_garage",
        (
            f"the specification publishes a garage opening — {layout.specs.get(LABEL_GARAGE)}"
            if layout.rear_garage
            else "the specification publishes no garage-opening row"
        ),
    )

    for name, feature in features.items():
        note = feature.note or _FEATURE_NOTES.get(name, "read from the specification")
        record(name, f"{note}: {feature.snippet}")
    if absent:
        record("microwave", MICROWAVE_ABSENCE_NOTE)

    if layout.floorplan_path:
        url = layout.floorplan_path
        provenance.update(
            floorplan_provenance(
                motorhome, url if url.startswith("http") else BASE_URL + url, layout.title
            )
        )
    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


def _page_path(range_label: str) -> str:
    for path, label in DEFAULT_RANGES:
        if label == range_label:
            return path
    return "/gb/en/motorhomes"


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 — the pages are server-rendered
    snapshot_dir: Path,  # noqa: ARG001 — `http` already snapshots into it
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """One fetch per range page. A page that cannot be read is narrated and skipped.

    Nothing raises for a single range: eleven pages, and one being rebuilt should not cost
    the other ten. A range that returns no layout is narrated loudly, because a stated
    roster going quietly wrong is how Dethleffs lost six.
    """
    results: list[ExtractedMotorhome] = []
    for path, label in ranges:
        if label not in RANGE_MAP:
            on_progress(f"[{label}] WARNING: no RANGE_MAP entry, so FMLV's range is unknown")
        page = http.fetch(BASE_URL + path)
        if page.status_code != 200:
            on_progress(f"[{label}] SKIPPED {path}: returned {page.status_code}")
            continue
        layouts = parse_layouts(
            page.file_path.read_text(encoding="utf-8", errors="replace"), label
        )
        if not layouts:
            on_progress(f"[{label}] WARNING: no layouts found on {path}")
            continue
        on_progress(f"[{label}] {len(layouts)} layout(s): {', '.join(x.code for x in layouts)}")

        for layout in layouts:
            if not _reconciles(layout):
                on_progress(
                    f"[{layout.title}] SKIPPED: the printed band {layout.mro_band} is not "
                    f"±5% of the {layout.mro_kilograms}kg running order"
                )
                continue
            if layout.floorplan_path is None:
                on_progress(f"[{layout.title}] no floorplan found")
            for name, value in (
                ("price", layout.rrp_pounds),
                ("running order mass", layout.mro_kilograms),
                ("berths", layout.berths),
                ("body type", layout.body_type),
            ):
                if value is None:
                    on_progress(f"[{layout.title}] WARNING: no {name} published, left blank")
            results.append(build_extracted(layout))

    identities: dict[tuple[str | None, str | None], int] = {}
    for extracted in results:
        key = (extracted.motorhome.manufacturer_range, extracted.motorhome.model)
        identities[key] = identities.get(key, 0) + 1
    for (range_name, model), count in sorted(
        ((item for item in identities.items() if item[1] > 1)), key=lambda i: str(i[0])
    ):
        on_progress(
            f"WARNING: {count} products share the identity '{range_name}' / '{model}' — "
            f"they would upload as duplicate rows. Check RANGE_MAP."
        )

    on_progress(f"{len(results)} product(s) collected")
    return results
