"""Carado (carado.com) — an Erwin Hymer Group brand on the same platform as Dethleffs.

See `docs/adapters/carado.md` for the full survey. Motorhomes and campervans only; the GB
edition lists no caravans.

**Two pages, and each answers what the other cannot.**

* `/gb/en/motorhomes/model-comparison` is the **roster**: every vehicle grouped under its
  range headline, with a price. It is the entry point, the product count, and — at the
  requester's direction, 9 September 2026 — the **price source**.
* the 23 layout pages carry everything else in plain tables: chassis, all three dimensions,
  both masses, seats, berths, the equipment lists and a per-vehicle floorplan.

**The trap is that a page is not a product.** Four camper-van pages carry more than one
vehicle — `cv600` and `cv640` each hold a base, a `PRO` and a `PRO+` — and `cv602-pro`'s two
are *both* Fiat Ducato £4,300 apart, so the tier is an equipment level rather than a chassis
badge. 23 pages, **29 vehicles**. Taking one price per page would lose six of them and
mis-price four more. The join is positional and asserted: the Nth `<h1>` names the Nth
specification block, and a page whose counts disagree is skipped rather than guessed at.

**The configurator must not be used**, even though Carado is on the shared EHG platform and
`ehg_configurator` reaches it: it publishes no prices at all, duplicates its series *within*
one model year, and lists four alcoves the UK site does not sell. The website over-rules,
which is the standing rule in `docs/adapters/README.md` regardless.

**Neither the path name nor the model name says what a vehicle is.** `Van` is a 214 mm-narrow
low profile, not a van — the requester warned of it and the site's own copy agrees ("the
advantages of a semi-integrated model … only 2.14 m wide"), on a GRP body with 34 mm walls.
Body type comes from the body-style path, checked against the construction lines.
"""

from __future__ import annotations

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

BASE_URL = "https://www.carado.com"
MANUFACTURER = "Carado"
MANUFACTURER_DISPLAY_NAME = "Carado"

SITEMAP_URL = f"{BASE_URL}/sitemap.xml"

#: The roster page: every vehicle, its range headline and its price. One fetch, and the
#: only place the range headline and the price are published together.
ROSTER_PATH = "/gb/en/motorhomes/model-comparison"

#: (body-style path, label) per range, for `--range` and progress output. These are the
#: site's own URL segments; the range that reaches FMLV comes from the roster page's
#: headline via `RANGE_MAP`.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (
    ("alcoves", "Alcoves"),
    ("camper-van", "Camper Vans"),
    ("integrated", "Integrated"),
    ("semi-integrated", "Semi-Integrated"),
    ("van", "Vans"),
)

#: Roster-page headline -> the FMLV range **without** its PRO tier. The site's plurals and
#: capitals are not what FMLV holds: it has `Semi-integrated` with a small `i`, and `Van`
#: singular. Confirmed against real FMLV rows by the requester, 9 September 2026.
RANGE_MAP: dict[str, str] = {
    "Integrated": "Integrated",
    "Semi-Integrated": "Semi-integrated",
    "Vans": "Van",
    "Alcoves": "Alcoves",
    "Camper Vans": "Campervan",
}

#: The equipment tier, which belongs in the **range** and not the model. The requester's
#: ruling, 9 September 2026, with two FMLV rows in front of him: *"the PRO element in the
#: name should be part of the range name. Unfortunately we have got some where the PRO
#: element has been put in the model name."* FMLV's own `Alcoves` + `A464 PRO` is one of
#: those, and should be `Alcoves PRO` + `A464` — so the adapter proposes the fix rather
#: than copying the mistake.
#:
#: Ordered longest-first: `PRO+` has to be tested before `PRO`, or every `PRO+` reads as a
#: `PRO` with a stray `+` left on the model.
TIER_SUFFIXES: tuple[str, ...] = (" PRO+", " PRO")

#: Body type per body-style path. **Never from the model name or the chassis**, both of
#: which mislead here: the `Van` range is a low profile, and a Fiat Ducato underpins a low
#: profile, an A class and a campervan alike.
#:
#: `camper-van` is absent deliberately — a van's type turns on its roof height, so it is
#: decided by `_campervan_body_type` against the settled threshold.
BODY_TYPES: dict[str, BodyType] = {
    "alcoves": BodyType.COACH_BUILT_OVER_CAB_BED,
    "integrated": BodyType.A_CLASS,
    "semi-integrated": BodyType.COACH_BUILT_LOW_PROFILE,
    "van": BodyType.COACH_BUILT_LOW_PROFILE,
}

#: The body-style path whose type the height decides.
CAMPERVAN_PATH = "camper-van"

#: Above this, a campervan is a high top — the settled rule in `docs/adapters/README.md`.
#: Every Carado campervan is 258-281 cm, so all thirteen clear it; written as a rule rather
#: than a constant so a future low-roof conversion classifies itself.
HIGH_TOP_ABOVE_MM = 2300

#: What a coachbuilt body is made of, and the check that a page under a coachbuilt path is
#: still the vehicle we think it is. All ten motorhome layouts publish both lines; not one
#: campervan does. A cheap corroboration of `BODY_TYPES` rather than a source in itself.
_COACHBUILT_CONSTRUCTION = re.compile(r"\bGRP\b.*\broof\b|\baluminium sidewalls\b", re.I)


# --------------------------------------------------------------------------- #
# The roster page
# --------------------------------------------------------------------------- #

#: One range's block on the roster page, so a model is read together with its headline.
_ROSTER_GROUP = re.compile(
    r"o-compare-form__model-group[^>]*>(?P<body>.*?)(?=o-compare-form__model-group|\Z)",
    re.S,
)
_ROSTER_HEADLINE = re.compile(r"o-compare-form__group-headline[^>]*>(?P<text>.*?)</h2>", re.S)
_ROSTER_ITEM = re.compile(
    r'data-id="(?P<id>\d+)".*?'
    r'm-compare-list-item__title"[^>]*>(?P<name>.*?)</span>.*?'
    r'<span class="price"[^>]*>(?P<price>.*?)</span>',
    re.S,
)

#: A layout page, `/gb/en/motorhomes/<body style>/<slug>`. Anchored so the index pages
#: themselves (`/gb/en/motorhomes/alcoves`) and the deeper editorial paths are excluded.
_MODEL_URL = re.compile(
    r"^https://(?:www\.)?carado\.com/gb/en/motorhomes/(?P<style>[a-z0-9-]+)/(?P<slug>[a-z0-9-]+)/?$"
)

_SITEMAP_LOC = re.compile(r"<loc>([^<]+)</loc>")


def _text(markup: str) -> str:
    """Tag-stripped, whitespace-collapsed text."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", markup)).strip()


def _slugify(name: str) -> str:
    """`CV640 PRO+` -> `cv640-pro-plus`, the form the site uses in its own asset paths."""
    lowered = name.lower().replace("+", "-plus")
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", lowered)).strip("-")


def _pounds(value: str) -> int | None:
    """`'from £61,990'` -> `61990`. The roster prints a `from` price; it is the layout's."""
    digits = re.sub(r"[^\d]", "", value)
    return int(digits) if digits else None


@dataclass(frozen=True)
class RosterEntry:
    """One vehicle as the roster page publishes it."""

    name: str
    range_headline: str
    rrp_pounds: int | None
    model_id: str

    @property
    def tier(self) -> str:
        """`' PRO+'`, `' PRO'` or `''` — the part of the name that belongs in the range."""
        for suffix in TIER_SUFFIXES:
            if self.name.upper().endswith(suffix):
                return suffix
        return ""

    @property
    def fmlv_range(self) -> str:
        """`Campervan PRO+` — the mapped headline plus the tier. See `RANGE_MAP`."""
        base = RANGE_MAP.get(self.range_headline, self.range_headline)
        return f"{base}{self.tier}"

    @property
    def fmlv_model(self) -> str:
        """`CV600` — the published name with the tier removed and nothing else.

        `EDITION27` and `4x4 X-EDITION` stay: they are model-year and drivetrain editions
        rather than an equipment tier, and dropping a published qualifier would be
        inventing. FMLV has no precedent for either, so this is the one identity decision
        the first run has to confirm.
        """
        tier = self.tier
        return self.name[: -len(tier)].strip() if tier else self.name

    @property
    def slug(self) -> str:
        """`CV640 PRO+` -> `cv640-pro-plus`, which is how the site names its floorplan path."""
        return _slugify(self.name)


def parse_roster(page_html: str) -> list[RosterEntry]:
    """Every vehicle on the roster page, with its range headline and price.

    The grouping is the point: a model's range is only knowable from the headline it sits
    under, and the headline is the one thing the layout pages never state.
    """
    entries: list[RosterEntry] = []
    for group in _ROSTER_GROUP.finditer(page_html):
        body = group.group("body")
        headline = _ROSTER_HEADLINE.search(body)
        if headline is None:
            continue
        range_headline = _text(headline.group("text"))
        for item in _ROSTER_ITEM.finditer(body):
            name = _text(item.group("name"))
            if not name:
                continue
            entries.append(
                RosterEntry(
                    name=name,
                    range_headline=range_headline,
                    rrp_pounds=_pounds(_text(item.group("price"))),
                    model_id=item.group("id"),
                )
            )
    return entries


def parse_sitemap_model_urls(*documents: str) -> list[str]:
    """Every layout-page URL in the sitemaps, deduplicated and sorted.

    A stated roster beats a heuristic, so the sitemap decides which pages exist rather
    than a crawl of the index pages — and `semi-integrated-ford`, which links to four
    T-models that live under `/semi-integrated/`, cannot introduce duplicates this way.
    """
    found = {
        url
        for document in documents
        for url in _SITEMAP_LOC.findall(document)
        if _MODEL_URL.match(url)
    }
    return sorted(found)


# --------------------------------------------------------------------------- #
# A layout page
# --------------------------------------------------------------------------- #

#: A specification or equipment table. Carado share Dethleffs' platform and its class.
_TABLE = re.compile(r"<table[^>]*has-columns--1\+[^>]*>(?P<body>.*?)</table>", re.S)
_ROW = re.compile(r"<tr[^>]*>(?P<row>.*?)</tr>", re.S)
_CELL = re.compile(r"<td[^>]*>(?P<cell>.*?)</td>", re.S)
_TH = re.compile(r"<th[^>]*>(?P<cell>.*?)</th>", re.S)

#: The vehicle names, all together at the top of the page in the order their specification
#: blocks appear further down. On a one-vehicle page there is one.
_H1 = re.compile(r"<h1[^>]*>(?P<text>.*?)</h1>", re.S)

#: The row that starts a vehicle. Exactly one per vehicle, which is what makes it the
#: reliable divider on a page carrying three of them.
LABEL_PRICE = "Basic price incl. VAT"

#: The only specification rows fed to `habitation` — an **allow-list**, because a
#: dimension row's label enumerates possibilities rather than stating what is fitted.
#:
#: `Lying area Alcove / pull-down bed / Clever-lift bed (cm) | 195 x 140 - 110 OPT` is the
#: one that proved it: passed in, it gave 14 of the 29 products a bed type read off a
#: *measurement heading* listing three things a Carado might have. `Bed dimension middle`
#: and `Bed dimension rear` are the same shape. The equipment lists are safe wholesale —
#: every line there is a statement about this vehicle — so only these two are wanted, and
#: naming them is safer than excluding the rows that look like dimensions.
#:
#: The same class of mistake as Rimor's `Tags` metadata line, which `habitation._METADATA`
#: filters, and Laika's misleading floorplan filename: text that looks like content and is
#: not.
HABITATION_SPEC_LABELS: frozenset[str] = frozenset(
    {
        "Refrigerator volume incl. freezer (l)",
        "Heating type",
    }
)

LABEL_CHASSIS = "Chassis"
LABEL_DIMENSIONS = "Length | Width | Height (cm)"
LABEL_SEATS = "Permitted number of seats (including driver)*"
LABEL_BERTHS = "Berths"
LABEL_MRO = "Mass in running order (kg)*"
LABEL_MTPLM = "Technically permissible maximum laden mass (kg) *"

#: Sits between the two masses, exactly where payload would, and is **not** payload — it
#: caps factory-fitted extras. Named so the mistake is documented rather than merely
#: avoided; Dethleffs, Etrusco, Sunlight and Bürstner share the trap.
LABEL_NOT_PAYLOAD = "Manufacturer-specified mass for optional equipment (kg)*"

#: The accordion that opens the fitted-as-standard list. Everything under `Optional
#: equipment` or `Edition equipment` is a paid extra and is never read as specification —
#: the standing rule in `habitation`.
STANDARD_EQUIPMENT = "Standard equipment"

_ACCORDION_TITLE = re.compile(r'o-accordion__(?:tab|title)[^>]*>(?P<text>.*?)<', re.S)

#: The marker Carado put on an optional figure, so `'2 - 5 OPT'` and `'78 (11) 156 (29)
#: OPT'` both yield the standard one. The **first** figure is the standard one throughout.
OPTIONAL_MARK = "OPT"


#: The "facts" card: `<dd class="m-facts__label">Berths</dd><dt class="m-facts__info">2</dt>`.
#:
#: On 22 of the 23 pages this is a **six-item summary** beside the full specification
#: tables — Carado's equivalent of Dethleffs' main-facts card. On `cv601-pro` it *is* the
#: specification: that page publishes all 25 rows this way and its tables carry only the
#: equipment lists. Same platform, two templates, and a parser that knew about only the
#: tables silently lost that vehicle.
_FACT = re.compile(
    r'<dd class="m-facts__label"[^>]*>(?P<label>.*?)</dd>\s*'
    r'<dt class="m-facts__info"[^>]*>(?P<value>.*?)</dt>',
    re.S,
)


def _clean(markup: str) -> str:
    """Cell text with footnote superscripts and info buttons removed.

    Both matter, and for the reason they matter on Dethleffs: a footnote marker sits
    *inside* the value cell, and the info button's `data-content` is a URL-encoded
    paragraph full of digits.
    """
    markup = re.sub(r"<sup[^>]*>.*?</sup>", " ", markup, flags=re.S)
    markup = re.sub(r"<button.*?</button>", " ", markup, flags=re.S)
    return _text(markup)


def _first_int(value: str) -> int | None:
    """The first integer in a cell — the standard figure of a `'2 - 5 OPT'` pair.

    The lower of a berth range per `docs/adapters/README.md`, and the base vehicle's figure
    rather than an optional upgrade's.
    """
    match = re.search(r"\d+", value.replace(",", ""))
    return int(match.group(0)) if match else None


def _band(value: str) -> tuple[int, int] | None:
    """`'2911 (2765 to 3057)*'` -> `(2765, 3057)`, the printed ±5% range."""
    match = re.search(r"\(\s*(\d+)\s*(?:to|-|–)\s*(\d+)\s*\)", value)
    return (int(match.group(1)), int(match.group(2))) if match else None


def _dimensions_mm(value: str) -> tuple[int | None, int | None, int | None]:
    """`'741 / 232 / 290'` -> `(7410, 2320, 2900)`. Carado quote whole centimetres."""
    figures = [int(n) * 10 for n in re.findall(r"\d+", value)[:3]]
    while len(figures) < 3:
        figures.append(None)  # type: ignore[arg-type]
    return figures[0], figures[1], figures[2]


@dataclass(frozen=True)
class CaradoVehicle:
    """One vehicle read off a layout page — not one page, which may hold three.

    `name` is the site's own (`CV640 PRO+`), which is neither the FMLV range nor the FMLV
    model. `RosterEntry` splits it.
    """

    url: str
    style: str
    name: str
    specs: dict[str, str] = field(default_factory=dict)
    standard_equipment: tuple[str, ...] = ()
    floorplan_path: str | None = None

    @property
    def chassis(self) -> str | None:
        return self.specs.get(LABEL_CHASSIS) or None

    @property
    def base_vehicle_manufacturer(self) -> str | None:
        """The make, spelled FMLV's way — `Citroën` keeps its diaeresis."""
        chassis = self.chassis
        return fmlv_base_vehicle(chassis.split()[0]) if chassis else None

    @property
    def mh_length_mm(self) -> int | None:
        return _dimensions_mm(self.specs.get(LABEL_DIMENSIONS, ""))[0]

    @property
    def mh_width_mm(self) -> int | None:
        return _dimensions_mm(self.specs.get(LABEL_DIMENSIONS, ""))[1]

    @property
    def mh_height_mm(self) -> int | None:
        return _dimensions_mm(self.specs.get(LABEL_DIMENSIONS, ""))[2]

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
        """`MTPLM - MRO`. Carado publish no payload, as Dethleffs and Etrusco do not."""
        if self.mtplm_kilograms is None or self.mro_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mro_kilograms

    @property
    def berths(self) -> int | None:
        return _first_int(self.specs.get(LABEL_BERTHS, ""))

    @property
    def mh_passenger_seats_inc_driver(self) -> int | None:
        return _first_int(self.specs.get(LABEL_SEATS, ""))

    @property
    def is_coachbuilt_construction(self) -> bool:
        """Whether the equipment list describes a GRP-and-aluminium body.

        Corroborates `BODY_TYPES` rather than deciding anything: every motorhome layout
        publishes it and no campervan does, so a coachbuilt path that stops publishing it
        is a page that has changed into something else.
        """
        return any(_COACHBUILT_CONSTRUCTION.search(line) for line in self.standard_equipment)

    @property
    def spec_lines(self) -> list[str]:
        """Everything on the page that **states** a fitted feature, for `habitation`.

        The standard equipment wholesale — every line of it is a statement about this
        vehicle — plus the two specification rows that state a feature rather than measure
        one. See `HABITATION_SPEC_LABELS` for why that list is an allow-list and not
        everything.
        """
        return [
            *(
                f"{label} {value}"
                for label, value in self.specs.items()
                if label in HABITATION_SPEC_LABELS
            ),
            *self.standard_equipment,
        ]

    def body_type(self, *, is_campervan_high_top: bool | None = None) -> BodyType | None:
        """From the body-style path, and the roof height for a campervan."""
        if self.style == CAMPERVAN_PATH:
            if is_campervan_high_top is None:
                return None
            return (
                BodyType.CAMPERVAN_HIGH_TOP
                if is_campervan_high_top
                else BodyType.CAMPERVAN
            )
        return BODY_TYPES.get(self.style)


def parse_standard_equipment(region_html: str) -> list[str]:
    """The fitted-as-standard equipment in one vehicle's region, category prefixed.

    Carado put standard and optional equipment in **separate accordions**, so the split is
    structural rather than a guess from a price — which is what makes the habitation read
    trustworthy here. `Optional equipment` and the PRO+ tiers' `Edition equipment` are
    both excluded.

    The accordion titles appear twice, once as a tab and once on the panel itself. Both are
    treated as boundaries: the tab pair sits together with no tables between them, so it
    contributes nothing and needs no special case.
    """
    titles = [
        (match.start(), _clean(match.group("text")))
        for match in _ACCORDION_TITLE.finditer(region_html)
        if _clean(match.group("text"))
    ]
    lines: list[str] = []
    for index, (start, title) in enumerate(titles):
        if title.casefold() != STANDARD_EQUIPMENT.casefold():
            continue
        end = titles[index + 1][0] if index + 1 < len(titles) else len(region_html)
        for table in _TABLE.finditer(region_html[start:end]):
            body = table.group("body")
            headers = [_clean(cell) for cell in _TH.findall(body)]
            category = headers[0] if headers else ""
            for row in _ROW.findall(body):
                cells = [_clean(cell) for cell in _CELL.findall(row)]
                if len(cells) == 1 and cells[0]:
                    lines.append(f"{category}: {cells[0]}" if category else cells[0])
    return lines


#: A floorplan drawing, and **the marker is what makes it one**: every image on the page
#: is served through the same `/image-thumb__<id>__<preset>/` resizer, so the preset name is
#: the only thing separating a layout drawing from a photograph of the lounge. Carado's
#: drawings all use `wls-carado-floorplan-large`.
#:
#: Without that token this matched the photography too, and every product got a "floorplan"
#: that might be a picture of a kitchen. The `docs/adapters/laika.md` lesson says a filename
#: is metadata about an upload rather than about an image — but here the *preset* is the
#: site's own statement of what the image is for, which is markup and can be trusted.
#:
#: The slug segment before the resizer names the vehicle that owns the drawing, and is what
#: `floorplan_for` joins on.
_FLOORPLAN = re.compile(
    r'/carado/[^"\s]*?/(?P<slug>[a-z0-9-]+)/image-thumb__[^"\s/]*?wls-carado-floorplan'
    r'[^"\s/]*/(?P<file>[^"\s/]+\.(?:png|jpe?g|svg|webp))',
    re.I,
)


def parse_floorplans(page_html: str) -> dict[str, str]:
    """`{slug: path}` for every floorplan on the page, keyed on the slug that owns it.

    A multi-vehicle page carries one drawing per vehicle and the **path names which** —
    `/wohnmobile/camper-van/cv640-pro-plus/…/cv640pro_plus_quer.png`. The slug segment is
    the join, not the filename: `RosterEntry.slug` produces exactly it.

    Each drawing is published twice, the second a `~-~media--…--query` derivative of the
    first. The plain one wins.
    """
    plans: dict[str, str] = {}
    for match in _FLOORPLAN.finditer(page_html):
        if "~-~" in match.group("file"):
            continue
        plans.setdefault(match.group("slug").lower(), match.group(0))
    return plans


def _spec_blocks_from_tables(page_html: str) -> list[tuple[int, dict[str, str]]]:
    """`(position, {label: value})` per vehicle, from the specification tables.

    **One price row per vehicle, so the price row is the divider.** A table without one is
    a continuation of the block above it — the specification is split across six of them
    (chassis and engine, dimensions, weights, technology, interior, miscellaneous), each
    introduced by its own little heading outside the table.
    """
    blocks: list[tuple[int, dict[str, str]]] = []
    for table in _TABLE.finditer(page_html):
        rows: dict[str, str] = {}
        for row in _ROW.findall(table.group("body")):
            cells = [_clean(cell) for cell in _CELL.findall(row)]
            if len(cells) == 2 and cells[0]:
                rows.setdefault(cells[0], cells[1])
        if not rows:
            continue
        if any(label.startswith(LABEL_PRICE) for label in rows):
            blocks.append((table.start(), rows))
        elif blocks:
            for label, value in rows.items():
                blocks[-1][1].setdefault(label, value)
    return blocks


def _spec_blocks_from_facts(page_html: str) -> list[tuple[int, dict[str, str]]]:
    """The same, from the facts card — the template `cv601-pro` uses. See `_FACT`.

    Only reached when the tables yielded nothing, so the 22 pages that publish a
    six-item summary card *beside* their tables are unaffected by it.
    """
    blocks: list[tuple[int, dict[str, str]]] = []
    for fact in _FACT.finditer(page_html):
        label, value = _clean(fact.group("label")), _clean(fact.group("value"))
        if not label:
            continue
        if label.startswith(LABEL_PRICE) or not blocks:
            blocks.append((fact.start(), {}))
        blocks[-1][1].setdefault(label, value)
    return blocks


def floorplan_for(slug: str, plans: dict[str, str]) -> str | None:
    """The drawing belonging to one vehicle, by the **longest** slug that prefixes its own.

    An exact match is not enough. `CV595 4x4 X-EDITION` slugifies to
    `cv595-4x4-x-edition` and its drawing sits under `/cv595/`; the `EDITION27` T-models do
    the same. But a prefix match alone would give `CV540` its PRO sibling's drawing on the
    page they share, so the longest wins: `cv540-pro` beats `cv540` for the PRO, and only
    `cv540` prefixes plain `CV540`.
    """
    candidates = [key for key in plans if slug.startswith(key)]
    if not candidates:
        return None
    return plans[max(candidates, key=len)]


def parse_page_vehicles(url: str, page_html: str) -> list[CaradoVehicle]:
    """Every vehicle on one layout page, in the order the page names them.

    **The join is positional and asserted.** All the `<h1>`s sit together at the top,
    naming the vehicles in order; each vehicle then has its own specification block further
    down, and its equipment accordions after that. So the Nth heading owns the Nth block.

    Returns `[]` when the counts disagree — that is not a case to guess at, since guessing
    attributes one vehicle's weights and price to another. `collect` narrates the skip.
    """
    match = _MODEL_URL.match(url)
    if match is None:
        return []
    style = match.group("style")

    names = [_clean(m.group("text")) for m in _H1.finditer(page_html)]
    names = [name for name in names if name]

    blocks = _spec_blocks_from_tables(page_html) or _spec_blocks_from_facts(page_html)
    if len(names) != len(blocks) or not blocks:
        return []

    plans = parse_floorplans(page_html)
    vehicles: list[CaradoVehicle] = []
    for index, (start, specs) in enumerate(blocks):
        end = blocks[index + 1][0] if index + 1 < len(blocks) else len(page_html)
        name = names[index]
        vehicles.append(
            CaradoVehicle(
                url=url,
                style=style,
                name=name,
                specs=specs,
                standard_equipment=tuple(parse_standard_equipment(page_html[start:end])),
                floorplan_path=floorplan_for(_slugify(name), plans),
            )
        )
    return vehicles


# --------------------------------------------------------------------------- #
# Building a product
# --------------------------------------------------------------------------- #

#: How each habitation reading's quote is introduced where `habitation` supplies no wording
#: of its own. Every quote already carries its own category prefix, so this only has to say
#: which of the two sources in `spec_lines` it came from.
_FEATURE_NOTES: dict[str, str] = {
    "heating": "the heater fitted as standard",
    "refrigeration": "read from the specification and the standard kitchen",
    "shower_toilet_separated": "the standard bathroom equipment",
    "bed_types": "read from the page's own wording",
}

#: Why a microwave is reported absent. Carado itemise an oven — `Oven in kitchen (only in
#: conjunction with 156 l fridge)` — so an equipment list with no microwave in it is the
#: document saying there is none, which is the itemised-table exception in
#: `docs/adapters/README.md`.
MICROWAVE_ABSENCE_NOTE = (
    "no mention of a microwave in the specification or the standard equipment. Carado "
    "itemise an oven where one is fitted, so the vocabulary is there and unused"
)


def microwave_absence_note(lines: list[str]) -> str | None:
    """The reason to report `microwave = No`, or `None` where a microwave is named.

    A mention **anywhere** stops the assertion, an options list included: a microwave the
    buyer may not have is still one the page named.
    """
    if habitation.microwave_from(lines) is not None:
        return None
    return MICROWAVE_ABSENCE_NOTE


def _feature_value(features: dict[str, habitation.Feature], name: str) -> object | None:
    found = features.get(name)
    return found.value if found is not None else None


def build_extracted(vehicle: CaradoVehicle, entry: RosterEntry) -> ExtractedMotorhome:
    """One product, from its layout page and its roster entry.

    The price comes from the **roster page**, at the requester's direction of 9 September
    2026, after the two renderings were found to disagree on the three Alcoves. Where the
    layout page states a different figure the snippet says both, so the reviewer sees the
    disagreement rather than a silently chosen winner.
    """
    features = habitation.features_from(vehicle.spec_lines)
    absence = microwave_absence_note(vehicle.spec_lines)
    high_top = (
        vehicle.mh_height_mm > HIGH_TOP_ABOVE_MM if vehicle.mh_height_mm is not None else None
    )
    body_type = vehicle.body_type(is_campervan_high_top=high_top)

    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=entry.fmlv_range,
        model=entry.fmlv_model,
        base_vehicle_manufacturer=vehicle.base_vehicle_manufacturer,
        body_type=body_type,
        rrp_pounds=entry.rrp_pounds,
        berths=vehicle.berths,
        mh_passenger_seats_inc_driver=vehicle.mh_passenger_seats_inc_driver,
        mtplm_kilograms=vehicle.mtplm_kilograms,
        mro_kilograms=vehicle.mro_kilograms,
        mh_payload_kilograms=vehicle.mh_payload_kilograms,
        mh_length_mm=vehicle.mh_length_mm,
        mh_width_mm=vehicle.mh_width_mm,
        mh_height_mm=vehicle.mh_height_mm,
        # Habitation, reported as findings rather than proposed — the pipeline never writes
        # these. See `product_model.findings`.
        heating=_feature_value(features, "heating"),
        refrigeration=_feature_value(features, "refrigeration"),
        shower_toilet_separated=_feature_value(features, "shower_toilet_separated"),
        bed_types=_feature_value(features, "bed_types") or [],
        microwave=False if absence else None,
    )

    label = entry.name
    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str, *, url: str = vehicle.url) -> None:
        provenance[field_name] = Provenance(source_url=url, snippet=f"{label} — {snippet}")

    roster_url = BASE_URL + ROSTER_PATH

    # Both halves of the identity, always together: they are one name split across two
    # columns, and accepting a range rename without the matching model rename corrupts it.
    identity = (
        f"the site publishes this as '{entry.name}' under the '{entry.range_headline}' "
        f"heading; FMLV holds range '{entry.fmlv_range}' and model '{entry.fmlv_model}'. "
        f"The tier belongs in the range, so the two halves belong together — accept both "
        f"or neither"
    )
    record("manufacturer_range", identity, url=roster_url)
    record("model", identity, url=roster_url)

    if entry.rrp_pounds is not None:
        page_price = _pounds(vehicle.specs.get(LABEL_PRICE, ""))
        note = (
            f"£{entry.rrp_pounds:,} from the model-comparison page, the UK on-the-road "
            f"price including VAT"
        )
        if page_price is not None and page_price != entry.rrp_pounds:
            note += (
                f". **The layout's own page says £{page_price:,}** — the two renderings "
                f"disagree by £{abs(entry.rrp_pounds - page_price):,}, and the comparison "
                f"page is the one taken"
            )
        record("rrp_pounds", note, url=roster_url)

    if vehicle.base_vehicle_manufacturer is not None:
        record("base_vehicle_manufacturer", f"Chassis: {vehicle.chassis}")
    if body_type is not None:
        detail = f"listed under /{vehicle.style}"
        if vehicle.style == CAMPERVAN_PATH:
            detail += (
                f", and {vehicle.mh_height_mm} mm is "
                f"{'above' if high_top else 'not above'} the {HIGH_TOP_ABOVE_MM} mm "
                f"high-top threshold"
            )
        elif vehicle.is_coachbuilt_construction:
            detail += ", whose GRP roof and aluminium sidewalls confirm a coachbuilt body"
        record("body_type", f"{detail} — not from the model name or the chassis")

    if vehicle.berths is not None:
        record("berths", f"Berths '{vehicle.specs.get(LABEL_BERTHS)}', standard figure {vehicle.berths}")
    if vehicle.mh_passenger_seats_inc_driver is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"Permitted number of seats (including driver): "
            f"'{vehicle.specs.get(LABEL_SEATS)}', standard figure "
            f"{vehicle.mh_passenger_seats_inc_driver}",
        )
    for field_name, axis in (
        ("mh_length_mm", "length"),
        ("mh_width_mm", "width"),
        ("mh_height_mm", "height"),
    ):
        if getattr(motorhome, field_name) is not None:
            record(
                field_name,
                f"Length | Width | Height (cm) '{vehicle.specs.get(LABEL_DIMENSIONS)}' "
                f"— the {axis}",
            )
    if vehicle.mtplm_kilograms is not None:
        record("mtplm_kilograms", f"Technically permissible maximum laden mass: {vehicle.mtplm_kilograms}kg")
    if vehicle.mro_kilograms is not None:
        band = (
            f" (permissible range {vehicle.mro_band[0]} to {vehicle.mro_band[1]}kg, ±5%)"
            if vehicle.mro_band
            else ""
        )
        record("mro_kilograms", f"Mass in running order: {vehicle.mro_kilograms}kg{band}")
    if vehicle.mh_payload_kilograms is not None:
        record(
            "mh_payload_kilograms",
            f"derived: {vehicle.mtplm_kilograms}kg maximum laden - {vehicle.mro_kilograms}kg "
            f"running order = {vehicle.mh_payload_kilograms}kg. Carado publish no payload, "
            f"and their 'manufacturer-specified mass for optional equipment' is not one",
        )

    for name, feature in features.items():
        note = feature.note or _FEATURE_NOTES.get(name, "read from the page")
        record(name, f"{note}: {feature.snippet}")
    if absence:
        record("microwave", absence)

    if vehicle.floorplan_path:
        provenance.update(
            floorplan_provenance(motorhome, BASE_URL + vehicle.floorplan_path, label)
        )
    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 — Carado needs no JS; see the module docstring
    snapshot_dir: Path,  # noqa: ARG001 — `http` already snapshots into it
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """The roster page for what exists and what it costs, then one fetch per layout page.

    The roster is fetched first and is required: without it there is no range headline and
    no price, and every product would go out with a blank range. A *layout* page that
    cannot be read is narrated and skipped, so one rebuilt page does not cost the other 22.
    """
    roster_url = BASE_URL + ROSTER_PATH
    on_progress(f"fetching the roster {roster_url} ...")
    roster_page = http.fetch(roster_url)
    if roster_page.status_code != 200:
        msg = f"roster page {roster_url} returned {roster_page.status_code}"
        raise RuntimeError(msg)
    roster = parse_roster(roster_page.file_path.read_text(encoding="utf-8", errors="replace"))
    if not roster:
        msg = f"no vehicles found on the roster page {roster_url}"
        raise RuntimeError(msg)
    by_name = {entry.name: entry for entry in roster}
    on_progress(
        f"roster: {len(roster)} vehicle(s) across "
        f"{len({entry.range_headline for entry in roster})} range(s)"
    )

    on_progress(f"fetching the sitemap index {SITEMAP_URL} ...")
    index = http.fetch(SITEMAP_URL)
    if index.status_code != 200:
        msg = f"sitemap index {SITEMAP_URL} returned {index.status_code}"
        raise RuntimeError(msg)
    index_xml = index.file_path.read_text(encoding="utf-8", errors="replace")
    documents = [index_xml]
    for url in [u for u in _SITEMAP_LOC.findall(index_xml) if u.endswith(".xml")]:
        page = http.fetch(url)
        if page.status_code == 200:
            documents.append(page.file_path.read_text(encoding="utf-8", errors="replace"))

    model_urls = parse_sitemap_model_urls(*documents)
    if not model_urls:
        msg = "no layout pages found in the sitemap"
        raise RuntimeError(msg)

    wanted = {path for path, _label in ranges}
    on_progress(f"{len(model_urls)} layout page(s) in the sitemap")

    results: list[ExtractedMotorhome] = []
    seen: set[str] = set()
    for url in model_urls:
        match = _MODEL_URL.match(url)
        assert match is not None
        style = match.group("style")
        if style not in wanted:
            continue
        page = http.fetch(url)
        if page.status_code != 200:
            on_progress(f"SKIPPED {url}: returned {page.status_code}")
            continue
        vehicles = parse_page_vehicles(
            url, page.file_path.read_text(encoding="utf-8", errors="replace")
        )
        if not vehicles:
            # Either no specification at all, or — the case worth narrating — the headings
            # and the specification blocks did not agree in number, which is the one thing
            # this parser must never guess at.
            on_progress(f"SKIPPED {url}: no vehicle whose heading and specification agree")
            continue
        for vehicle in vehicles:
            entry = by_name.get(vehicle.name)
            if entry is None:
                on_progress(
                    f"SKIPPED {vehicle.name} ({url}): not on the roster page, so it has "
                    f"no range and no price"
                )
                continue
            if vehicle.floorplan_path is None:
                on_progress(f"[{vehicle.name}] no floorplan found on the page")
            results.append(build_extracted(vehicle, entry))
            seen.add(vehicle.name)
        on_progress(f"[{style}] {url.rsplit('/', 1)[-1]}: {len(vehicles)} vehicle(s)")

    # A stated roster beats a heuristic: a vehicle the roster page lists and no layout page
    # produced is narrated, rather than quietly reducing the product count.
    for entry in roster:
        if entry.name not in seen and RANGE_MAP.get(entry.range_headline) is not None:
            on_progress(f"MISSING {entry.name}: on the roster page but no layout page produced it")

    on_progress(f"{len(results)} product(s) collected from {len(roster)} on the roster")
    return results
