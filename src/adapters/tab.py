"""T@B caravans, read from the `Technical data` table on tabme.de.

Knaus Tabbert's smallest brand, and the whole of it is five products. The source is plain
static HTML — no JavaScript, and no PDF at all: the site's only `CATALOGUE` link goes to
`shop.tabme.de`, which sells T@B merchandise, and every `/downloads/` path 404s.

## The roster is five products across three pages

`/en/models/basic/`, `/en/models/metropolis/` and `/en/models/offroad/` are **styles, not
ranges of their own**, and none of them has a specification table. Basic and Metropolis
*both* link the same `/en/320/` and `/en/400/`; Offroad links `/en/320-offroad/`. FMLV's
own identity agrees — `manufacturer_range` holds the style and `model` holds the number,
so `Basic` / `320` and `Metropolis` / `400`.

So three spec pages serve five products, and **one technical table is published per
page**. Basic/320 and Metropolis/320 necessarily receive identical figures, as do
Basic/400 and Metropolis/400; the site publishes no per-style weights.

## Three masses, and the middle one is the MRO

Each table prints `Mass of unladen vehicle` (320: 620), `Mass in ready to travel
condition` (653, **this one**) and `Tecnically maximum authorized laden mass` (800, the
MTPLM — the site's own misspelling of *Technically*, matched as published).

The summary card above the table repeats length, width, beds and a bare `Mass`, and that
`Mass` is the *unladen* figure. Everything here is read from inside the table.

## The published payload is not the payload

`Maximum payload, approx.` assumes full gas bottles and a full water tank, so it
undershoots badly — 57 kg on the 320 against an arithmetic 147:

| model | MTPLM | MRO | published | MTPLM - MRO |
|---|---|---|---|---|
| 320 | 800 | 653 | 57 | **147** |
| 400 | 1200 | 986 | 106 | **214** |
| 320 Offroad | 1000 | 708 | 202 | **292** |

This is a Knaus Tabbert house habit rather than a T@B quirk: `knaus.py` records the same
trap (SKY TI 650 MEG prints 8 kg) and so does `weinsberg.py` (CaraCore 700 MEG prints 18).

`docs/adapters/README.md` says that for **caravans** the personal-effects payload is not
MTPLM minus MRO but one half of a split. T@B is a documented exception to that, because
its own baseline settles it: all 23 rows in the export hold
`personal_effects_payload_kilograms` exactly equal to MTPLM minus MRO, and
`optional_equipment_payload_kilograms` is empty on every one. The requester confirmed 147
for the 320 directly.

## The self-check

Every page states its MTPLM twice, in different markup hundreds of lines apart: once in
the table, and once as a `Load increase to N kg` line in the equipment list. They agree on
all three pages, and the agreement also settles which figure is the base vehicle — the
matching load increase is under `Standard Equipment`, while the larger ones are under
`Optional equipment` / `Packages`:

| page | table MTPLM | standard load increase | optional |
|---|---|---|---|
| `/en/320/` | 800 | **800** | 850, 1000 |
| `/en/400/` | 1200 | **1200** | 1500, 1300, 1400 |
| `/en/320-offroad/` | 1000 | **1000** | — |

So the 320 reads 800 rather than its 750 kg bare chassis, because the load increase to 800
is standard equipment.

## Prices: the English edition drops the headline, and one panel is stale

Two figures are published, and they are not equally trustworthy.

The **German** page carries a headline `Listenpreis ab` at the top. The **English** page
does not carry it at all — it has only an `AVAILABLE STYLES` panel listing each style with
a `List price from`. On the 320 the two agree exactly, and on the 400 they do not:

| page | German headline | `AVAILABLE STYLES` panel |
|---|---|---|
| `/320/` | 14.990 | BASIC 14.990, METROPOLIS 16.380, OFFROAD 18.490 |
| `/400/` | **24.390** | BASIC 13.990, METROPOLIS 15.380 |
| `/320-offroad/` | 18.490 | *(no panel)* |

The 400's panel is 74% under its own headline, and FMLV holds GBP 24,970 and GBP 24,394
for the two 400 products, which corroborates the headline. The panel is also undated where
the 320's carries `(08/2026)`. So a panel is used **only when its base-style price equals
the page's own headline**, and rejected otherwise — see `resolve_prices`.

Offroad/320 is the one product priced from two independent statements that agree: the 320
panel's OFFROAD entry and the 320-offroad page's own headline are both 18.490.

## Body type is deliberately not emitted

The requester states these are micros and FMLV holds `type_micro` on all 23 baseline rows.
The settled rule needs the manufacturer's own naming **as well as** MTPLM of 1250 kg or
lower, and the naming is absent: *micro* appears zero times on tabme.de in English and in
German, and zero times on knaustabbert.de.

Since all five products match rows that already hold `type_micro`, emitting nothing leaves
it standing. Asserting `type_rigid` — the usual answer — would propose downgrading five
rows that are already correct, which is `wingamm_caravan.py`'s mistake in reverse.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.caravan import Caravan
from ..vehicle_class import VehicleClass
from . import habitation
from .base import ExtractedCaravan, Provenance

__all__ = [
    "BASE_URL",
    "EUR_PER_GBP_RATE",
    "EXPECTED_PRODUCTS",
    "LAYOUTS",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "TabCaravan",
    "standard_equipment",
    "VEHICLE_CLASS",
    "collect",
]

BASE_URL = "https://www.tabme.de"

#: Byte-for-byte the export's `manufacturer`, which is the join key back to product ids.
MANUFACTURER = "Knaus Tabbert AG T@B"
MANUFACTURER_DISPLAY_NAME = "T@B"

#: Without this, `ADAPTERS` would register the module under the motorhome class.
VEHICLE_CLASS = VehicleClass.CARAVAN

#: Euros per pound, so a euro price is **divided** by it. The requester chose 1.15 on
#: 2026-09-19, "like we've done on some of the other brands".
#:
#: `morelo.EUR_TO_GBP_RATE` is the same judgement expressed the other way up — 0.855
#: pounds per euro, a multiplier, which is 1/1.1696. The two are close but not equal and
#: neither is a typo of the other; they were set on different dates by different people.
#: Stated here as one obvious, greppable constant because it *will* go stale.
#:
#: Worth a reviewer's eye: this converts a **German domestic list price including 19% VAT**
#: and is not a UK on-the-road price. Every converted figure lands below what FMLV already
#: holds, which is what a home-market price at spot rate does. Each price records the euro
#: figure, the rate and that basis in its provenance.
EUR_PER_GBP_RATE = 1.15
EUR_PER_GBP_RATE_DATE = "2026-09-19"

#: The five products the site publishes. Asserted so that a style being added or dropped
#: is a loud failure rather than a quiet one.
EXPECTED_PRODUCTS = 5


@dataclass(frozen=True)
class _Layout:
    """One specification page, and the FMLV products its single table serves.

    `styles` is in the site's own order, and its **first entry is the base style** — the
    one the page's headline price belongs to. That ordering is load-bearing in
    `resolve_prices`, which falls back to the headline when a style panel is rejected.
    """

    slug: str
    model: str
    styles: tuple[str, ...]


#: `320-offroad` is not a fourth model: it is the 320's OFFROAD style, which the 320 page
#: links as "GO TO 320 OFFROAD" and which FMLV holds as range `Offroad`, model `320`. It
#: gets its own page because the style includes the 1,000 kg chassis, so its weights differ
#: from the other two 320 products.
LAYOUTS: tuple[_Layout, ...] = (
    _Layout("320", "320", ("Basic", "Metropolis")),
    _Layout("400", "400", ("Basic", "Metropolis")),
    _Layout("320-offroad", "320", ("Offroad",)),
)

#: Section headings, used to tell standard equipment from optional. `Packages` opens the
#: optional half on some pages and `Optional equipment` on others, so the boundary is
#: whichever comes first.
_TECHNICAL_DATA = "Technical data"
_STANDARD_EQUIPMENT = "Standard Equipment"
_OPTIONAL_HEADINGS = ("Optional equipment", "Packages")

#: A whole-number figure, with either separator. The table uses German dots (`1.200`) and
#: the optional-equipment lines use English commas (`1,000 kg`) **on the same page**, so
#: both are accepted and both are stripped. Anchored so that a decimal such as `2,75 kg`
#: in the gas-bottle line can never be read as 275.
_WHOLE_NUMBER = re.compile(r"^(\d{1,3}(?:[.,]\d{3})*)$")

#: `Load increase to 800 kg (850 kg chassis)`. The first figure is the MTPLM this option
#: confers; the parenthesised one is the chassis rating and is deliberately not read.
_LOAD_INCREASE = re.compile(r"Load increase to\s+(\d{1,3}(?:[.,]\d{3})*)\s*kg")

#: `List price from 14.990,–`, the per-style price in the `AVAILABLE STYLES` panel. The
#: trailing dash is an en dash on the site, not a hyphen.
_STYLE_PRICE = re.compile(r"List price from\s+(\d{1,3}(?:\.\d{3})*),\s*[-–]")

#: `Listenpreis ab` / `24.390,- *` on the German page, which is the authoritative headline.
_HEADLINE_LABEL = "Listenpreis ab"
_HEADLINE_PRICE = re.compile(r"^(\d{1,3}(?:\.\d{3})*),\s*[-–]")

_STYLES_PANEL = "AVAILABLE STYLES"

_TAGS = re.compile(r"<[^>]+>")
_BLOCK_TAGS = re.compile(r"<(tr|/tr|li|/li|dt|dd|br|p|div|h\d)\b[^>]*>", re.I)
_SCRIPTS = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)


def visible_lines(html: str) -> list[str]:
    """The page as the reader sees it, one text run per line.

    Every figure on this site sits on its own line *below* its label rather than beside
    it, so the parse is label-then-value throughout and the line split is what makes it
    possible.
    """
    text = _SCRIPTS.sub(" ", html)
    text = _BLOCK_TAGS.sub("\n", text)
    text = _TAGS.sub(" ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return [
        stripped
        for line in text.splitlines()
        if (stripped := re.sub(r"[ \t]+", " ", line).strip())
    ]


def _whole_number(value: str) -> int | None:
    """`1.200` and `1,000` both mean 1200 and 1000; anything else means nothing."""
    match = _WHOLE_NUMBER.match(value.strip())
    if match is None:
        return None
    return int(match.group(1).replace(".", "").replace(",", ""))


def _first_of_pair(value: str) -> int | None:
    """`201 / 180` is overall then interior, and the overall figure is the one recorded."""
    return _whole_number(value.split("/")[0])


def _section_bounds(lines: list[str]) -> tuple[int, int]:
    """Where `Standard Equipment` starts and the optional half begins.

    Returns `(len(lines), len(lines))` when the headings are missing, so a caller reading
    "standard" gets nothing rather than silently reading the optional list.
    """
    try:
        start = lines.index(_STANDARD_EQUIPMENT)
    except ValueError:
        return len(lines), len(lines)
    ends = [lines.index(h) for h in _OPTIONAL_HEADINGS if h in lines]
    return start, min(ends) if ends else len(lines)


def value_after(lines: list[str], anchor: str, *, within: int = 4) -> str | None:
    """The first value line after the line containing `anchor`, or `None`.

    Labels wrap: `Overall Width` / `/` / `interior width in cm` are three lines before the
    value, and `Number of beds` is followed by a bare `up to` before its figure. So the
    anchor is the *last* fragment of each label and the scan skips the connective lines
    rather than assuming a fixed offset.
    """
    for index, line in enumerate(lines):
        if anchor not in line:
            continue
        for candidate in lines[index + 1 : index + 1 + within]:
            if candidate in ("/", "up to", "-", "–"):
                continue
            return candidate
    return None



def standard_equipment(lines: list[str]) -> list[str]:
    """The `Standard Equipment` list, stopping where the optional half begins.

    Scoped deliberately: the optional list on `/en/400/` offers a Truma air conditioner
    and a larger refrigerator, and reading the two sections as one would report kit the
    caravan does not come with.
    """
    start, end = _section_bounds(lines)
    if start >= len(lines):
        return []
    return lines[start + 1 : end]


@dataclass
class _Figures:
    """What one `Technical data` table states, before it is attached to any style."""

    shipping_length_mm: int | None = None
    overall_width_mm: int | None = None
    height_mm: int | None = None
    headroom_mm: int | None = None
    mro_kilograms: int | None = None
    mtplm_kilograms: int | None = None
    berths: int | None = None
    unladen_kilograms: int | None = None
    published_payload_kilograms: int | None = None


def parse_technical_data(lines: list[str]) -> _Figures:
    """The specification table, scoped to it so equipment prose cannot leak in.

    Everything is read from *below* `Technical data`. The summary card above it repeats
    length, width, beds and a bare `Mass`, and that `Mass` is the unladen figure — reading
    the page unscoped would take 620 kg for the 320's mass in running order.
    """
    try:
        body = lines[lines.index(_TECHNICAL_DATA) :]
    except ValueError:
        return _Figures()

    def centimetres(anchor: str, *, pair: bool = False) -> int | None:
        raw = value_after(body, anchor)
        if raw is None:
            return None
        value = _first_of_pair(raw) if pair else _whole_number(raw)
        return None if value is None else value * 10

    def kilograms(anchor: str) -> int | None:
        raw = value_after(body, anchor)
        return None if raw is None else _whole_number(raw)

    return _Figures(
        shipping_length_mm=centimetres("Overall length in cm"),
        overall_width_mm=centimetres("interior width in cm", pair=True),
        height_mm=centimetres("interieur height in cm", pair=True),
        headroom_mm=_interior_height(body),
        mro_kilograms=kilograms("Mass in ready to travel condition"),
        # As the site spells it. Matching the misspelling is deliberate.
        mtplm_kilograms=kilograms("maximum authorized laden mass"),
        berths=kilograms("Number of beds"),
        unladen_kilograms=kilograms("Mass of unladen vehicle"),
        published_payload_kilograms=kilograms("Maximum payload"),
    )


def _interior_height(body: list[str]) -> int | None:
    """The second half of the `244 / 182` height pair, which is FMLV's headroom."""
    raw = value_after(body, "interieur height in cm")
    if raw is None or "/" not in raw:
        return None
    value = _whole_number(raw.split("/")[1])
    return None if value is None else value * 10


def parse_load_increases(lines: list[str]) -> tuple[list[int], list[int]]:
    """`(standard, optional)` load-increase ratings, by which section they sit in.

    The standard one restates the MTPLM and is the self-check; the optional ones are the
    bigger chassis a buyer can pay for, and reading them as the vehicle's own mass would
    put an optioned figure in `mtplm_kilograms`.
    """
    start, end = _section_bounds(lines)
    standard: list[int] = []
    optional: list[int] = []
    for index, line in enumerate(lines):
        match = _LOAD_INCREASE.search(line)
        if match is None:
            continue
        value = _whole_number(match.group(1))
        if value is None:
            continue
        (standard if start <= index < end else optional).append(value)
    return standard, optional


def parse_styles(lines: list[str]) -> list[tuple[str, int]]:
    """The `AVAILABLE STYLES` panel as `[(style, euro price)]`, in the site's order.

    The panel alternates an upper-case style name and its `List price from` line, so a
    price is only taken when it directly follows a name — a stray price elsewhere on the
    page cannot be picked up as a style.
    """
    try:
        start = lines.index(_STYLES_PANEL)
    except ValueError:
        return []

    styles: list[tuple[str, int]] = []
    index = start + 1
    while index + 1 < len(lines):
        name, price_line = lines[index], lines[index + 1]
        match = _STYLE_PRICE.search(price_line)
        if match is None or not name.isupper():
            break
        price = _whole_number(match.group(1))
        if price is not None:
            styles.append((name.title(), price))
        index += 2
    return styles


def parse_headline_price(lines: list[str]) -> int | None:
    """The German page's `Listenpreis ab` figure, which the English edition omits."""
    for index, line in enumerate(lines):
        if _HEADLINE_LABEL not in line:
            continue
        for candidate in lines[index + 1 : index + 3]:
            match = _HEADLINE_PRICE.match(candidate)
            if match is not None:
                return _whole_number(match.group(1))
    return None


@dataclass(frozen=True)
class _Prices:
    """Euro prices for one layout's styles, with the basis a reviewer needs to see."""

    by_style: dict[str, int]
    basis: dict[str, str]
    note: str | None


def resolve_prices(
    layout: _Layout, styles: list[tuple[str, int]], headline: int | None
) -> _Prices:
    """Which euro price belongs to which style, trusting the panel only when it checks out.

    The panel is accepted only if its **base style's** price equals the page's own headline.
    On the 320 they agree exactly, so all its styles are priced from the panel. On the 400
    the panel says 13.990 against a headline of 24.390 — 74% under, and FMLV's own GBP
    24,970 and 24,394 side with the headline — so the panel is discarded entirely rather
    than half-trusted, and only the base style is priced.

    A page with no panel at all (`/320-offroad/`) prices its single style from the headline.
    """
    by_style: dict[str, int] = {}
    basis: dict[str, str] = {}
    panel = dict(styles)
    base_style = layout.styles[0]

    panel_agrees = (
        headline is not None
        and base_style in panel
        and panel[base_style] == headline
    )

    if panel_agrees:
        for style in layout.styles:
            if style in panel:
                by_style[style] = panel[style]
                basis[style] = (
                    f"the AVAILABLE STYLES panel on /en/{layout.slug}/ lists "
                    f"{style.upper()} at EUR {panel[style]:,}, and that panel is trusted "
                    f"because its {base_style.upper()} price matches the page's own "
                    f"headline Listenpreis ab of EUR {headline:,} exactly"
                )
        return _Prices(by_style, basis, None)

    if headline is not None:
        by_style[base_style] = headline
        basis[base_style] = (
            f"the headline 'Listenpreis ab EUR {headline:,}' at the top of "
            f"/{layout.slug}/ on the German site, which is the base {base_style} style"
        )

    if not panel:
        return _Prices(by_style, basis, None)

    unpriced = [s for s in layout.styles if s not in by_style]
    note = (
        f"{layout.model}: the AVAILABLE STYLES panel is REJECTED. It prices "
        f"{base_style.upper()} at EUR {panel.get(base_style, 0):,} against the page's own "
        f"headline of EUR {headline:,} — the panel is also undated where the 320's carries "
        f"(08/2026), and FMLV's own sterling sides with the headline. Priced from the "
        f"headline instead"
    )
    if unpriced:
        note += f"; no price proposed for {', '.join(unpriced)} {layout.model}"
    return _Prices(by_style, basis, note)


@dataclass
class TabCaravan:
    """One FMLV product: a style crossed with a layout's specification table."""

    range_name: str
    model: str
    figures: _Figures
    price_eur: int | None = None
    price_basis: str | None = None

    @property
    def label(self) -> str:
        return f"{self.range_name} {self.model}"

    @property
    def derived_payload_kilograms(self) -> int | None:
        """MTPLM minus MRO — never the site's own `Maximum payload`, which assumes full
        gas bottles and a full water tank and undershoots by 90 kg on the 320."""
        mtplm, mro = self.figures.mtplm_kilograms, self.figures.mro_kilograms
        if mtplm is None or mro is None:
            return None
        return mtplm - mro

    @property
    def rrp_pounds(self) -> int | None:
        if self.price_eur is None:
            return None
        return round(self.price_eur / EUR_PER_GBP_RATE)


def _reconciles(product: TabCaravan, standard_load_increase: list[int]) -> tuple[bool, str]:
    """Does the equipment list's standard load increase restate the table's MTPLM?

    The two figures sit in different sections of the page in different markup, so agreeing
    is real corroboration and not the same parse read twice. A page that fails this has
    been misread, and the product is dropped rather than proposed.
    """
    mtplm = product.figures.mtplm_kilograms
    if mtplm is None:
        return False, "no technically maximum authorized laden mass in the table"
    if not standard_load_increase:
        return False, (
            f"the table says MTPLM {mtplm}kg but no 'Load increase to N kg' line appears "
            f"under Standard Equipment to corroborate it"
        )
    if standard_load_increase != [mtplm]:
        return False, (
            f"the table says MTPLM {mtplm}kg but Standard Equipment says "
            f"{standard_load_increase} — one of the two was misread"
        )
    return True, (
        f"MTPLM {mtplm}kg, corroborated by 'Load increase to {mtplm} kg' in the page's own "
        f"Standard Equipment list; the larger increases on the page are optional"
    )


#: How each habitation reading is introduced. These are findings for a person to type in,
#: not proposals, so the wording says which list they came from.
_FEATURE_NOTES: dict[str, str] = {
    "heating": "the heating named in the page's Standard Equipment list",
    "refrigeration": "the refrigeration named in the page's Standard Equipment list",
    "microwave": "a microwave named in the page's Standard Equipment list",
    "shower_toilet_separated": "the washroom as the Standard Equipment list describes it",
}


def build_extracted(
    product: TabCaravan,
    source_url: str,
    *,
    mass_basis: str,
    equipment: tuple[str, ...] = (),
) -> ExtractedCaravan:
    """One product as a `Caravan` plus the provenance a reviewer sees beside it."""
    features = habitation.features_from(equipment)
    # Dropped for the same reason as on Swift and Bessacarr: the `Bed size, front/rear`
    # rows give dimensions without saying whether a bed is built in or made up from the
    # seating, which is the distinction `BedType` exists to carry.
    features.pop("bed_types", None)

    figures = product.figures
    caravan = Caravan(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.range_name,
        model=product.model,
        berths=figures.berths,
        rrp_pounds=product.rrp_pounds,
        mtplm_kilograms=figures.mtplm_kilograms,
        mro_kilograms=figures.mro_kilograms,
        personal_effects_payload_kilograms=product.derived_payload_kilograms,
        shipping_length_mm=figures.shipping_length_mm,
        overall_width_mm=figures.overall_width_mm,
        height_mm=figures.height_mm,
        headroom_mm=figures.headroom_mm,
    )
    for name, feature in features.items():
        setattr(caravan, name, feature.value)

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=source_url, snippet=f"{product.label} — {snippet}"
        )

    # Both halves of the identity, always: `compare_fields` walks only fields carrying
    # provenance, and accepting a range change without its model corrupts the name.
    record(
        "manufacturer_range",
        f'range "{product.range_name}" — the style, which is what FMLV holds as the '
        f"range; accept with the model, they are one name",
    )
    record(
        "model",
        f'model "{product.model}" — accept with the range, they are one name',
    )

    if figures.berths is not None:
        record("berths", f"Number of beds: up to {figures.berths}")
    if figures.mtplm_kilograms is not None:
        record("mtplm_kilograms", f"Tecnically maximum authorized laden mass (kg): {mass_basis}")
    if figures.mro_kilograms is not None:
        record(
            "mro_kilograms",
            f"Mass in ready to travel condition, approx. in kg: {figures.mro_kilograms}. "
            f"NOT the 'Mass of unladen vehicle' on the line above it "
            f"({figures.unladen_kilograms}kg), and not the bare 'Mass' on the summary card",
        )
    if product.derived_payload_kilograms is not None:
        record(
            "personal_effects_payload_kilograms",
            f"{product.derived_payload_kilograms}kg, derived as MTPLM minus MRO "
            f"({figures.mtplm_kilograms} - {figures.mro_kilograms}). The page's own "
            f"'Maximum payload, approx.' of {figures.published_payload_kilograms}kg is a "
            f"homologation figure assuming full gas bottles and a full water tank, and is "
            f"deliberately not recorded — the same trap as Knaus and Weinsberg",
        )
        record(
            "optional_equipment_payload_kilograms",
            "T@B publish no payload split, so there is no separate optional-equipment "
            "payload. Left blank so the two payload columns sum to the derived "
            f"{product.derived_payload_kilograms}kg",
        )
    if figures.shipping_length_mm is not None:
        record(
            "shipping_length_mm",
            f"Overall length in cm: {figures.shipping_length_mm // 10} -> "
            f"{figures.shipping_length_mm}mm",
        )
    if figures.overall_width_mm is not None:
        record(
            "overall_width_mm",
            f"Overall Width / interior width in cm: {figures.overall_width_mm // 10} / ... "
            f"-> {figures.overall_width_mm}mm, the overall figure",
        )
    if figures.height_mm is not None:
        record(
            "height_mm",
            f"Overall height / interieur height in cm: {figures.height_mm // 10} / ... -> "
            f"{figures.height_mm}mm, the overall figure",
        )
    if figures.headroom_mm is not None:
        record(
            "headroom_mm",
            f"Overall height / interieur height in cm: ... / {figures.headroom_mm // 10} "
            f"-> {figures.headroom_mm}mm, the interior figure",
        )
    if product.price_eur is not None:
        record(
            "rrp_pounds",
            f"EUR {product.price_eur:,} / {EUR_PER_GBP_RATE} = GBP {product.rrp_pounds:,}. "
            f"Source: {product.price_basis}. Converted at a fixed rate recorded "
            f"{EUR_PER_GBP_RATE_DATE}, not a live one. NOTE this is a German domestic list "
            f"price including 19% German VAT, not a UK on-the-road price — check before "
            f"accepting",
        )

    for name, feature in features.items():
        note = feature.note or _FEATURE_NOTES.get(name, "read from the page")
        record(name, f"{note}: {feature.snippet}")

    return ExtractedCaravan(caravan=caravan, provenance=provenance)


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001
    snapshot_dir: Path,  # noqa: ARG001
    *,
    ranges: tuple[tuple[str, str], ...] = (),  # noqa: ARG001
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedCaravan]:
    """Every T@B caravan the site publishes.

    Six fetches: each of the three specification pages in English, for the table and the
    style panel, and again in German, for the headline price the English edition omits.
    """
    extracted: list[ExtractedCaravan] = []

    for layout in LAYOUTS:
        english_url = f"{BASE_URL}/en/{layout.slug}/"
        on_progress(f"fetching {english_url}")
        english = visible_lines(
            http.fetch(english_url).file_path.read_text(encoding="utf-8", errors="replace")
        )

        figures = parse_technical_data(english)
        standard, optional = parse_load_increases(english)
        styles = parse_styles(english)

        german_url = f"{BASE_URL}/{layout.slug}/"
        headline = parse_headline_price(
            visible_lines(
                http.fetch(german_url).file_path.read_text(encoding="utf-8", errors="replace")
            )
        )
        if headline is None:
            on_progress(
                f"{layout.model}: no 'Listenpreis ab' headline on {german_url} — the "
                f"English edition carries no headline price at all, so the style panel "
                f"cannot be checked against anything"
            )

        prices = resolve_prices(layout, styles, headline)
        if prices.note:
            on_progress(prices.note)

        published = {name for name, _price in styles}
        unexpected = published - set(layout.styles) - {"Offroad"}
        missing = set(layout.styles) - published - {"Offroad"}
        if unexpected or missing:
            on_progress(
                f"{layout.model}: the AVAILABLE STYLES panel lists {sorted(published)} "
                f"where this layout is built for {list(layout.styles)} — a style may have "
                f"been added or dropped, which changes the roster"
            )

        equipment = tuple(standard_equipment(english))
        if not equipment:
            on_progress(
                f"{layout.model}: no Standard Equipment list read — no habitation findings"
            )

        for style in layout.styles:
            product = TabCaravan(
                range_name=style,
                model=layout.model,
                figures=figures,
                price_eur=prices.by_style.get(style),
                price_basis=prices.basis.get(style),
            )
            reconciles, reason = _reconciles(product, standard)
            if not reconciles:
                on_progress(f"dropping {product.label} — {reason}")
                continue
            extracted.append(
                build_extracted(product, english_url, mass_basis=reason, equipment=equipment)
            )
            on_progress(
                f"read {product.label}: {figures.shipping_length_mm}mm, "
                f"{figures.mtplm_kilograms}kg, "
                + (f"GBP {product.rrp_pounds:,}" if product.rrp_pounds else "no price")
            )

        if optional:
            on_progress(
                f"{layout.model}: load increases to {optional}kg are OPTIONAL equipment "
                f"and are not recorded — the base vehicle is {figures.mtplm_kilograms}kg"
            )

    if len(extracted) != EXPECTED_PRODUCTS:
        on_progress(
            f"expected {EXPECTED_PRODUCTS} products and collected {len(extracted)} — "
            f"check whether a style has been added or dropped"
        )

    on_progress(
        "NOT PROPOSED, deliberately: BODY TYPE, because the word 'micro' appears nowhere "
        "on tabme.de in English or German nor on knaustabbert.de, and the settled rule "
        "needs the manufacturer's own naming as well as MTPLM <= 1250kg. FMLV already "
        "holds type_micro on every row, and emitting nothing leaves it standing. Also "
        "internal_length_mm and exterior_body_length_mm: the site's 'Usable length' is a "
        "different measurement (320: 3980mm against FMLV's 3400mm) and the body length is "
        "published nowhere."
    )
    on_progress(f"collected {len(extracted)} T@B caravan(s)")
    return extracted
