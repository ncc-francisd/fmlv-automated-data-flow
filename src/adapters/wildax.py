"""Wildax campervans, read from the `Essentials Spec.` panels on wildaxmotorhomes.com.

Eighteen models across eight ranges, every one a campervan. Plain WordPress HTML with
Alpine.js on top, and the Alpine only drives behaviour — the spec tables, the habitation
positions and the whole price list are all server-rendered, so a browser is never needed.

**The site is not the one the name suggests.** `wildax.co.uk` is a Boston Terrier breeder
in Merseyside; it resolves, returns 200, and its page title is `About Wildax`. The
motorhome company is `wildaxmotorhomes.com`.

## Eight fetches, and the price list rides along

Each range page carries every model in that range, so eight fetches cover all eighteen. The
price list is not a ninth: it is an off-canvas nav panel whose full contents sit in *every*
page's HTML, so it is read from the first page fetched and reused.

## The price list and the model list are keyed differently

This is the one real design decision here. The price list is keyed on **gearbox, engine and
paint** — `Constellation XL Manual`, `Meteor (Blue) 165 Auto`, `Equinox 4x4 (Grey) 130
Manual` — while the models are keyed on **layout**. They do not line up one to one:

- **Constellation 3 and Constellation 4 share one price row.** The list knows only
  `Constellation` and `Constellation XL`; the 3 and the 4 differ by belt count, not money.
- **Pulsar, Altair RS and Altair RL are priced only as automatics**, although every spec
  panel on the site says `6-Speed Manual`. No manual price is published for them at all.
- **Meteor is priced four ways** across two engines and two paints.

`resolve_price` strips the gearbox, engine and paint from each row to get a base name, then
takes the **lowest** price in that group — the settled base-vehicle rule, manual over
automatic and cheaper paint over dearer. The exception is the Meteor, which carries an
`engine` filter: FMLV holds the model as `165` and the requester chose the 165's price on
23 September 2026 rather than let the rule pick a 130 for a van named 165.

`Altair Sport Upgrade £7,400` is an option, not a vehicle. Nothing maps to it, so it is
never built into a product.

## The self-check: Est Payload == MTPLM - MRO

WildAx publish all three, and the arithmetic is FMLV's own payload formula, so the parse is
checkable without a second document. **Fifteen of eighteen reconcile exactly**, and the
three that do not are WildAx's typos rather than the parser's:

| model | MTPLM | MRO | stated | MTPLM - MRO | settled by |
|---|---|---|---|---|---|
| Constellation 3 XL | **3496** | 3058 | 442 | 438 | its own stated payload, and FMLV's 3500 |
| Aurora XL | 3500 | 3013 | **485** | 487 | Aurora Leisure XL, same MRO, states 487 |
| Altair RL | 3500 | 3190 | **306** | 310 | nothing — off by 4, undetermined |

FMLV independently holds 310 for the Altair RL and 487 for the Aurora XL, which is the
derived figure rather than WildAx's printed one. So the rule and the reading agree.

**A mismatch is narrated, never silently resolved, and never a reason to drop a product.**
Payload is derived under the settled rule regardless, so the published figure is only ever
the check. What *does* drop a product is a panel with no MTPLM or no MRO at all, because
then there is nothing to derive from and nothing to check.

## Dimensions are published to the centimetre

The site gives `5.99 m`, `2.05 m`, `2.7 m` — two decimal places at best — where FMLV holds
millimetres. Converting gives figures that differ from FMLV's by a millimetre or ten on
about half the roster, which is precision rather than remeasurement.

They are proposed anyway, with the published string quoted verbatim in the provenance so a
reviewer can see it is `5.98 m` against `5981`, because the alternative leaves two genuine
errors standing: FMLV holds **2005** for the Fiat models and **2004** for the MAN, where
the site says `2.05 m` and `2.04 m`. Those read like a decimal point lost on entry — a
Ducato is 2050 mm wide, not 2005 — and they are 45 mm and 36 mm out, far beyond rounding.
The Ford's 2059 is a real Transit figure and better than the site's rounded `2.05 m`.

## Habitation comes stated, which is unusual

Every model publishes a `Campervan Layout` block:

```
Lounge  Front      Kitchen  Rear Side      Shower/Toilet  Rear Side
Sleeping area 1  Front      Sleeping area 2  Rear
```

Those are normally floorplan-only facts. They are still **findings** rather than proposals,
which the pipeline decides; this adapter's job is to read them and quote the line.

Positions are mapped on which of `Front`, `Rear` and `Side` appear, and **refused where the
enum cannot express the combination**: `Rear Side` is both rear and side, and
`KitchenLocation` and `BathroomLayout` each make those exclusive. Refusing is the settled
"derive it or leave it blank" rule — a guess across mutually exclusive columns is worse
than a gap, because a gap blocks the upload until a person looks.

`Sleeping area 1` and `2` together give `sleeping_area_both`. The Equinox states its second
area as `Elevating Roof`, which is neither front nor rear, so it is left unset and
narrated.
"""

from __future__ import annotations

import dataclasses
import html as htmllib
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.enums import (
    BathroomLayout,
    BedType,
    BodyType,
    KitchenLocation,
    LoungeLocation,
    SleepingArea,
)
from ..product_model.model import Motorhome
from . import habitation
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

__all__ = [
    "BASE_URL",
    "EXPECTED_MODELS",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "MODELS",
    "WildaxCampervan",
    "body_type_for",
    "collect",
    "parse_price_list",
    "resolve_price",
    "spec_panels",
    "visible_lines",
]

BASE_URL = "https://wildaxmotorhomes.com"

#: The NCC list spells the manufacturer `Wildax`; the supplier list spells it
#: `WildAx Motorhomes`. Both are right and neither is a typo of the other — one name per
#: company per role, which is the settled rule. This is the manufacturer.
MANUFACTURER = "Wildax"
MANUFACTURER_DISPLAY_NAME = "Wildax"

#: Eighteen models across the eight ranges the site publishes.
EXPECTED_MODELS = 18


@dataclass(frozen=True)
class _Model:
    """One model, as the site publishes it and as FMLV files it."""

    slug: str
    #: `Range` and `Model` exactly as the `Essentials Spec.` panel prints them, which is
    #: how a panel is matched to this entry.
    panel_range: str
    panel_model: str
    #: What FMLV holds. **Deliberately not derived from the panel**: FMLV shouts some of
    #: its names (`AURORA`, `SOLARIS`, `PULSAR`, `EUROPA`, `EQUINOX`) and title-cases
    #: others, inconsistently, and re-casing 15 live rows is churn nobody asked for.
    manufacturer_range: str
    model: str
    #: The price list's base name for this model, once gearbox, engine and paint are
    #: stripped. Several models legitimately share one.
    price_key: str
    #: Only the Meteor sets this. See the module docstring.
    price_engine: str | None = None

    @property
    def url(self) -> str:
        return f"{BASE_URL}/{self.slug}"

    @property
    def label(self) -> str:
        return f"{self.manufacturer_range} {self.model}"

    @property
    def panel_label(self) -> str:
        return f"{self.panel_range} {self.panel_model}"


#: The roster, hardcoded so that FMLV's own naming survives and so that a model appearing
#: or disappearing on the site is *narrated* rather than silently changing the run's shape.
#: `collect` checks every range page's panels against this list each run.
#:
#: Three of these are not in FMLV as of 23 September 2026 — `Aurora Leisure`,
#: `Aurora Leisure XL` and `Equinox 4x4` — and are named in the site's own title case,
#: since there is no existing row whose casing to preserve.
MODELS: tuple[_Model, ...] = (
    _Model("aurora", "Aurora", "Aurora", "AURORA", "AURORA", "Aurora"),
    _Model("aurora", "Aurora", "Leisure", "AURORA", "Leisure", "Aurora Leisure"),
    _Model("aurora", "Aurora", "XL", "AURORA", "XL", "Aurora XL"),
    _Model("aurora", "Aurora", "Leisure XL", "AURORA", "Leisure XL", "Aurora Leisure XL"),
    _Model("europa", "Europa", "Europa", "Europa", "EUROPA", "Europa"),
    _Model("europa", "Europa", "XL", "Europa", "XL", "Europa XL"),
    _Model("pulsar", "Pulsar", "Pulsar", "PULSAR", "PULSAR", "Pulsar"),
    _Model("solaris", "Solaris", "6m", "SOLARIS", "SOLARIS", "Solaris"),
    _Model("solaris", "Solaris", "XL", "SOLARIS XL", "XL", "Solaris XL"),
    _Model("constellation", "Constellation", "3", "Constellation", "3", "Constellation"),
    _Model("constellation", "Constellation", "4", "Constellation", "4", "Constellation"),
    _Model(
        "constellation", "Constellation", "3 XL", "Constellation", "3 XL", "Constellation XL"
    ),
    _Model(
        "constellation", "Constellation", "4 XL", "Constellation", "4 XL", "Constellation XL"
    ),
    _Model("equinox", "Equinox", "Equinox", "Equinox", "EQUINOX", "Equinox"),
    _Model("equinox", "Equinox", "4x4", "Equinox", "4x4", "Equinox 4x4"),
    _Model("meteor", "Meteor", "165", "Meteor", "165", "Meteor", price_engine="165"),
    _Model("altair", "Altair", "RS", "Altair", "RS", "Altair RS"),
    _Model("altair", "Altair", "RL", "Altair", "RL", "Altair RL"),
)

#: One fetch per range page, in the order the site lists them.
RANGE_SLUGS: tuple[str, ...] = (
    "aurora",
    "europa",
    "pulsar",
    "solaris",
    "constellation",
    "equinox",
    "meteor",
    "altair",
)

_DROP = re.compile(r"<(script|style|noscript|svg)\b.*?</\1>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")


def visible_lines(page_html: str) -> list[str]:
    """Every non-empty run of visible text, in document order.

    Tags become line breaks, so a label and its value always land on separate lines — which
    is what `spec_panels` relies on, and what makes a wrapped two-word label such as
    `Bed type` arrive as two lines rather than one.
    """
    text = _TAG.sub("\n", _DROP.sub(" ", page_html))
    out: list[str] = []
    for raw in text.split("\n"):
        line = re.sub(r"\s+", " ", htmllib.unescape(raw)).strip()
        if line:
            out.append(line)
    return out


#: The `Essentials Spec.` labels, each as the tokens it arrives as. The markup wraps the
#: two-word ones, so `Bed type` is two lines and has to be matched as two.
_SPEC_LABELS: tuple[str, ...] = (
    "Range",
    "Model",
    "Type",
    "Chassis",
    "Bodystyle",
    "Bed type",
    "Berths",
    "Seatbelts",
    "Layout type",
    "Gearbox",
    "Engine",
    "Drive side",
    "MTPLM",
    "MRO",
    "Est Payload",
    "Length (m)",
    "Width (m)",
    "Height (m)",
    "Lounge",
    "Kitchen",
    "Shower/Toilet",
)

#: `Sleeping area` is followed by an index and *then* the value, so it needs its own pass.
_SLEEPING_AREA = "Sleeping area"


@dataclass(frozen=True)
class _Panel:
    """One `Essentials Spec.` panel: its fields, its sleeping areas and its equipment."""

    fields: dict[str, str]
    sleeping_areas: tuple[str, ...]
    equipment: tuple[str, ...]

    @property
    def identity(self) -> tuple[str, str]:
        return self.fields.get("Range", ""), self.fields.get("Model", "")


def _panel_fields(window: list[str]) -> tuple[dict[str, str], tuple[str, ...]]:
    found: dict[str, str] = {}
    areas: list[str] = []
    i = 0
    while i < len(window):
        if window[i : i + 2] == _SLEEPING_AREA.split(" ") or window[i] == _SLEEPING_AREA:
            step = 1 if window[i] == _SLEEPING_AREA else 2
            # `Sleeping area` / `1` / `Front` — skip the index, take the place.
            if i + step + 1 < len(window):
                areas.append(window[i + step + 1])
                i += step + 1
                continue
        for label in _SPEC_LABELS:
            parts = label.split(" ")
            if window[i : i + len(parts)] == parts and i + len(parts) < len(window):
                found.setdefault(label, window[i + len(parts)])
                i += len(parts)
                break
        i += 1
    return found, tuple(areas)


def spec_panels(lines: list[str]) -> list[_Panel]:
    """Every model's panel on one range page, in document order.

    A panel runs from its `Essentials Spec.` heading to the next one, or to the page's
    trailing boilerplate. The equipment is the standard-fit lists only — everything from
    `General Features` up to `Optional Extras`, which is excluded because an option is not
    a specification.
    """
    starts = [i for i, line in enumerate(lines) if line == "Essentials Spec."]
    panels: list[_Panel] = []
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        block = lines[start + 1 : end]
        fields, areas = _panel_fields(block[:120])

        equipment: tuple[str, ...] = ()
        if "General Features" in block:
            first = block.index("General Features")
            last = block.index("Optional Extras") if "Optional Extras" in block else len(block)
            equipment = tuple(block[first:last])

        if fields:
            panels.append(_Panel(fields=fields, sleeping_areas=areas, equipment=equipment))
    return panels


# --- the price list -------------------------------------------------------------------

#: Everything a price row says about the *variant* rather than the vehicle. Stripping these
#: leaves the base name that a model's `price_key` matches.
_VARIANT_TOKENS = re.compile(
    r"\s*\((?:Blue|Grey)\)|\b(?:Manual|Auto)\b|\b(?:130|165)\b", re.IGNORECASE
)
_CHASSIS_NAMES = frozenset({"Fiat", "Ford", "MAN"})
_PRICE = re.compile(r"^£\s*([\d,]+)$")


@dataclass(frozen=True)
class PriceRow:
    """One line of the price list."""

    label: str
    base_name: str
    chassis: str
    pounds: int

    @property
    def engine(self) -> str | None:
        match = re.search(r"\b(130|165)\b", self.label)
        return match.group(1) if match else None


def parse_price_list(lines: list[str]) -> list[PriceRow]:
    """Every priced line in the off-canvas price list panel.

    The panel prints `name` / `chassis` / `price` as three consecutive runs, and the
    chassis name is what makes a vehicle row recognisable — the options list below it
    (`Awning 4m (XL vans)` / `£1,600`) has no chassis and is skipped for free.
    """
    rows: list[PriceRow] = []
    for i, line in enumerate(lines):
        if line not in _CHASSIS_NAMES or i == 0 or i + 1 >= len(lines):
            continue
        price = _PRICE.match(lines[i + 1])
        if price is None:
            continue
        label = lines[i - 1]
        base = re.sub(r"\s{2,}", " ", _VARIANT_TOKENS.sub("", label)).strip()
        rows.append(
            PriceRow(
                label=label,
                base_name=base,
                chassis=line,
                pounds=int(price.group(1).replace(",", "")),
            )
        )
    return rows


def resolve_price(
    rows: Iterable[PriceRow], model: _Model
) -> tuple[int | None, str, str | None]:
    """`(pounds, reason, chassis)` for one model — the cheapest row in its group.

    The settled base-vehicle rule: where a manufacturer publishes several prices for one
    vehicle, record the base, not the optioned variant. Here that means manual over
    automatic and the cheaper paint over the dearer, because those are the only things the
    price list varies.
    """
    group = [row for row in rows if row.base_name.casefold() == model.price_key.casefold()]
    if model.price_engine is not None:
        group = [row for row in group if row.engine == model.price_engine]
    if not group:
        return None, f"no price list row matches {model.price_key!r}", None

    cheapest = min(group, key=lambda row: row.pounds)
    others = sorted(row for row in {r.pounds for r in group} if row != cheapest.pounds)
    reason = f'"{cheapest.label}" £{cheapest.pounds:,}'
    if others:
        reason += (
            f", the lowest of {len(group)} prices published for this vehicle "
            f"({', '.join(f'£{p:,}' for p in others)} for the other variants) — the "
            f"base vehicle rather than the optioned one"
        )
    if model.price_engine is not None:
        reason += (
            f". Restricted to the {model.price_engine} engine because FMLV holds this "
            f"model as {model.model!r}; the cheaper 130 is a different vehicle"
        )
    if len(group) == 1 and "auto" in cheapest.label.casefold():
        reason += (
            ". NOTE this is an AUTOMATIC price and the only one published for this model, "
            "although its own spec panel states a 6-speed manual"
        )
    return cheapest.pounds, reason, cheapest.chassis


# --- figures --------------------------------------------------------------------------


def _kilograms(value: str | None) -> int | None:
    if value is None:
        return None
    match = re.match(r"(\d+)\s*kg", value.strip(), re.IGNORECASE)
    return int(match.group(1)) if match else None


def _millimetres(value: str | None) -> int | None:
    """`6.36 m` and `6 m` alike, to the millimetre.

    The site publishes two decimal places at best, so the result is only ever accurate to
    the centimetre — which the provenance says explicitly.
    """
    if value is None:
        return None
    match = re.match(r"([\d.]+)\s*m\b", value.strip(), re.IGNORECASE)
    if match is None:
        return None
    return round(float(match.group(1)) * 1000)


def _count(value: str | None) -> int | None:
    if value is None:
        return None
    match = re.match(r"(\d+)", value.strip())
    return int(match.group(1)) if match else None


def base_vehicle_make(chassis: str | None) -> str | None:
    """`Fiat Ducato` -> `Fiat`, `MAN TGE` -> `MAN`, `Ford` -> `Ford`.

    The panel names the make *and* the model; FMLV holds the make alone under the settled
    abbreviation rule, so the first word is taken and `fmlv_base_vehicle` then does the
    spelling (VW, not Volkswagen). Without this the run proposes `Fiat Ducato` over
    `Fiat` on every Wildax row.
    """
    if not chassis:
        return None
    return chassis.strip().split(" ")[0] or None


def body_type_for(bodystyle: str | None, height_mm: int | None) -> tuple[BodyType | None, str]:
    """The body style, derived from what the panel states and the published height.

    Every Wildax is a van conversion, so the only question is the roof. `High Top` on seven
    ranges and `Elevating Roof` on the Equinox, whose height of 2.8 m puts it well over the
    settled 2300 mm threshold — so it is a high top *with* an elevating roof, which is what
    FMLV already holds for it.
    """
    if not bodystyle:
        return None, "the panel states no bodystyle"
    lowered = bodystyle.casefold()
    over_threshold = height_mm is not None and height_mm > 2300
    if "elevat" in lowered or "pop" in lowered:
        if over_threshold:
            return BodyType.CAMPERVAN_HIGH_TOP_ELEVATING_ROOF, (
                f'a high top campervan with an elevating roof: the panel states '
                f'"{bodystyle}" and the published height of {height_mm}mm is over the '
                f"2300mm threshold, so the fixed roof is a high top in its own right"
            )
        return BodyType.CAMPERVAN_ELEVATING_ROOF, (
            f'an elevating-roof campervan: the panel states "{bodystyle}" and the '
            f"published height does not reach the 2300mm high-top threshold"
        )
    if "high" in lowered and over_threshold:
        return BodyType.CAMPERVAN_HIGH_TOP, (
            f'a high top campervan: the panel states "{bodystyle}" and the published '
            f"height of {height_mm}mm is over the 2300mm threshold"
        )
    return None, f'no body style can be derived from "{bodystyle}" at {height_mm}mm'


# --- habitation -----------------------------------------------------------------------


def _position(value: str | None) -> tuple[bool, bool, bool]:
    """`(front, rear, side)` — which position words a published phrase contains."""
    lowered = (value or "").casefold()
    return "front" in lowered, "rear" in lowered, "side" in lowered


def lounge_location_for(value: str | None) -> LoungeLocation | None:
    front, rear, _ = _position(value)
    if front and not rear:
        return LoungeLocation.FRONT
    if rear and not front:
        return LoungeLocation.REAR
    return None


def kitchen_location_for(value: str | None) -> KitchenLocation | None:
    """`Side` and `Rear` map; `Rear Side` does not.

    `KitchenLocation` makes rear and side mutually exclusive, so a kitchen WildAx describe
    as both cannot be expressed. Guessing across an exclusive group is the thing the
    settled rule forbids.
    """
    _, rear, side = _position(value)
    if side and not rear:
        return KitchenLocation.SIDE
    if rear and not side:
        return KitchenLocation.REAR
    return None


def bathroom_layout_for(value: str | None) -> list[BathroomLayout]:
    """Same exclusivity as the kitchen, and a list because FMLV holds this column as one.

    `Front Side` is a side washroom — the enum has no front, and nothing in `Front Side`
    claims the rear. `Rear Side` claims both, which the column cannot express, so it
    returns empty rather than picking one.
    """
    _, rear, side = _position(value)
    if side and not rear:
        return [BathroomLayout.SIDE_SHOWER_TOILET]
    if rear and not side:
        return [BathroomLayout.REAR_SHOWER_TOILET]
    return []


def sleeping_area_for(areas: Iterable[str]) -> tuple[SleepingArea | None, str]:
    """Front, rear or both, from the one or two areas the panel names.

    The settled rule is that `sleeping_area` is only ever front, rear or both — no
    manufacturer designates a separate children's area. The Equinox names its second area
    as `Elevating Roof`, which is neither, so that model is left unset rather than guessed
    at from its first area alone.
    """
    listed = tuple(areas)
    if not listed:
        return None, "the panel names no sleeping area"

    unplaceable = [area for area in listed if not any(_position(area)[:2])]
    if unplaceable:
        return None, (
            f"not proposed: {', '.join(repr(a) for a in unplaceable)} is neither front nor "
            f"rear, so the areas this model publishes ({', '.join(listed)}) cannot be "
            f"reduced to one value"
        )

    front = any(_position(area)[0] for area in listed)
    rear = any(_position(area)[1] for area in listed)
    if front and rear:
        return SleepingArea.BOTH, (
            f"both: the panel names {len(listed)} sleeping areas, {' and '.join(listed)}"
        )
    if front:
        return SleepingArea.FRONT, f"front: {', '.join(listed)}"
    return SleepingArea.REAR, f"rear: {', '.join(listed)}"


#: What the `Bed type` field says, and the FMLV bed type it names. A conversion is a
#: make-up bed whichever end of the van it is at.
_BED_TYPES: tuple[tuple[re.Pattern[str], BedType], ...] = (
    (re.compile(r"transverse", re.IGNORECASE), BedType.TRANSVERSE),
    (re.compile(r"bunk", re.IGNORECASE), BedType.FIXED_BUNKS),
    (re.compile(r"twin|single", re.IGNORECASE), BedType.FIXED_SEPARATE),
    (re.compile(r"island", re.IGNORECASE), BedType.ISLAND),
    (re.compile(r"conversion|make.?up", re.IGNORECASE), BedType.MAKE_UP),
    (re.compile(r"drop.?down", re.IGNORECASE), BedType.DROP_DOWN),
)


def bed_types_for(value: str | None) -> list[BedType]:
    if not value:
        return []
    return [bed for pattern, bed in _BED_TYPES if pattern.search(value)]


# --- the product ----------------------------------------------------------------------


@dataclass(frozen=True)
class WildaxCampervan:
    """One model, ready to become an `ExtractedMotorhome`."""

    spec: _Model
    panel: _Panel
    rrp_pounds: int | None
    price_reason: str
    #: Whether the panel's own three masses agree. `False` withholds all of them.
    reconciles: bool = True

    def value(self, label: str) -> str | None:
        return self.panel.fields.get(label)

    @property
    def mtplm_kilograms(self) -> int | None:
        return _kilograms(self.value("MTPLM"))

    @property
    def mro_kilograms(self) -> int | None:
        return _kilograms(self.value("MRO"))

    @property
    def stated_payload_kilograms(self) -> int | None:
        return _kilograms(self.value("Est Payload"))

    @property
    def derived_payload_kilograms(self) -> int | None:
        if self.mtplm_kilograms is None or self.mro_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mro_kilograms


def _reconciles(product: WildaxCampervan) -> tuple[bool, str]:
    """`(ok, reason)` — does the published payload equal MTPLM minus MRO?

    A failure does **not** drop the product: payload is derived under the settled rule
    anyway, so the published figure is a check rather than a source, and all three known
    failures are WildAx's own typos. Missing masses do drop it, because then there is
    nothing to derive and nothing to check.
    """
    if product.mtplm_kilograms is None or product.mro_kilograms is None:
        return False, "the panel states no MTPLM or no MRO, so no payload can be derived"
    stated, derived = product.stated_payload_kilograms, product.derived_payload_kilograms
    if stated is None:
        return True, (
            f"MTPLM {product.mtplm_kilograms}kg less MRO {product.mro_kilograms}kg "
            f"= {derived}kg; the panel publishes no payload to check it against"
        )
    if stated == derived:
        return True, (
            f"MTPLM {product.mtplm_kilograms}kg less MRO {product.mro_kilograms}kg "
            f"= {derived}kg, which is the payload WildAx publish"
        )
    return False, (
        f"MTPLM {product.mtplm_kilograms}kg less MRO {product.mro_kilograms}kg = "
        f"{derived}kg but WildAx publish {stated}kg, a difference of "
        f"{abs(derived - stated)}kg"
    )


def suspect_copied_figures(
    collected: Iterable[tuple[_Model, WildaxCampervan]],
) -> list[str]:
    """Siblings on one range page whose figures contradict each other.

    Two things on this site are genuinely wrong, and **neither is visible to the payload
    self-check**, because the copied figure is copied consistently:

    * **Same mass, different length.** The Solaris XL publishes the 6m's 3040kg although
      it is 370mm longer. 3500 less 3040 is the 460 WildAx print, so the panel agrees
      with itself and is wrong. FMLV holds 3134.
    * **An XL no longer than its own base model.** The base Europa publishes the XL's
      6.36m. FMLV holds 5990 for it. The name is the evidence here: an XL that is not
      longer is not an XL.

    **Sharing a length is otherwise normal and is not reported.** The Altair RS and RL
    are one 6840mm van with two interiors, and the two Equinoxes are one 5980mm van with
    two drivetrains. Reporting those is the Globecar mistake — a range shares
    wheelbases, so length on its own proves nothing.

    Narrated, never withheld: nothing on the page can tell a pasted cell from a genuine
    coincidence, and only FMLV settles it.
    """
    by_page: dict[str, list[tuple[_Model, int | None, int | None]]] = {}
    for spec, product in collected:
        by_page.setdefault(spec.slug, []).append(
            (spec, product.mro_kilograms, _millimetres(product.value("Length (m)")))
        )

    suspect: list[str] = []
    for slug, members in sorted(by_page.items()):
        # A. one mass across models of different lengths
        by_mass: dict[int, list[tuple[str, int | None]]] = {}
        for spec, mro, length in members:
            if mro is not None:
                by_mass.setdefault(mro, []).append((spec.label, length))
        for mass, group in sorted(by_mass.items()):
            lengths = {length for _, length in group if length is not None}
            if len(group) < 2 or len(lengths) < 2:
                continue
            suspect.append(
                f"on the {slug} page, {', '.join(name for name, _ in group)} all state "
                f"the same mass in running order ({mass}kg) although their length runs "
                f"from {min(lengths)}mm to {max(lengths)}mm — a longer van has to "
                f"weigh more"
            )

        # B. an XL that is no longer than the model it extends
        for spec, _, length in members:
            if "XL" not in spec.panel_model.upper() or length is None:
                continue
            shorter = [
                (other.label, other_length)
                for other, _, other_length in members
                if "XL" not in other.panel_model.upper()
                and other_length is not None
                and other_length >= length
            ]
            for name, other_length in shorter:
                suspect.append(
                    f"on the {slug} page, {spec.label} states {length}mm but {name}, "
                    f"which it extends, states {other_length}mm — an XL that is not "
                    f"longer is not an XL"
                )
    return suspect


def build_extracted(product: WildaxCampervan, *, payload_basis: str) -> ExtractedMotorhome:
    """The product and a provenance line for every field it proposes."""
    spec, panel = product.spec, product.panel
    source_url = spec.url

    height_mm = _millimetres(product.value("Height (m)"))
    body_type, body_reason = body_type_for(product.value("Bodystyle"), height_mm)
    sleeping_area, sleeping_reason = sleeping_area_for(panel.sleeping_areas)
    features = habitation.features_from(panel.equipment)

    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=spec.manufacturer_range,
        model=spec.model,
        base_vehicle_manufacturer=fmlv_base_vehicle(base_vehicle_make(product.value("Chassis"))
        ),
        mh_length_mm=_millimetres(product.value("Length (m)")),
        mh_width_mm=_millimetres(product.value("Width (m)")),
        mh_height_mm=height_mm,
        berths=_count(product.value("Berths")),
        mh_passenger_seats_inc_driver=_count(product.value("Seatbelts")),
        # **Cleared, not merely unprovenanced, when the self-check fails.** The pipeline
        # derives payload from whatever MTPLM and MRO a product carries, so leaving the
        # values on and dropping their provenance still proposed 442 -> 438 on the
        # Constellation 3 XL, off the back of the 3496 typo. Emitting nothing is what
        # raises the no-op "not found this run" row that preserves FMLV's figures.
        mtplm_kilograms=product.mtplm_kilograms if product.reconciles else None,
        mro_kilograms=product.mro_kilograms if product.reconciles else None,
        mh_payload_kilograms=(
            product.derived_payload_kilograms if product.reconciles else None
        ),
        rrp_pounds=product.rrp_pounds,
        body_type=body_type,
        sleeping_area=sleeping_area,
        lounge_location=lounge_location_for(product.value("Lounge")),
        kitchen_location=kitchen_location_for(product.value("Kitchen")),
        bathroom_layout=bathroom_layout_for(product.value("Shower/Toilet")),
        bed_types=bed_types_for(product.value("Bed type")),
        heating=features["heating"].value if "heating" in features else None,
        refrigeration=features["refrigeration"].value if "refrigeration" in features else None,
        microwave=features["microwave"].value if "microwave" in features else None,
        shower_toilet_separated=(
            features["shower_toilet_separated"].value
            if "shower_toilet_separated" in features
            else None
        ),
    )

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=source_url, snippet=f"{spec.label} — {snippet}"
        )

    # Both halves of the identity, always: `compare_fields` walks only fields carrying
    # provenance, and accepting a range change without its model corrupts the name.
    record(
        "manufacturer_range",
        f'range "{spec.manufacturer_range}", as the {spec.panel_range} range page groups '
        f"this model — accept with the model, they are one name",
    )
    record(
        "model",
        f'model "{spec.model}", published as "{spec.panel_label}" — accept with the '
        f"range, they are one name",
    )

    if motorhome.base_vehicle_manufacturer is not None:
        record(
            "base_vehicle_manufacturer",
            f'Chassis: {product.value("Chassis")}, abbreviated to the make',
        )

    for field_name, label in (
        ("mh_length_mm", "Length (m)"),
        ("mh_width_mm", "Width (m)"),
        ("mh_height_mm", "Height (m)"),
    ):
        if getattr(motorhome, field_name) is not None:
            record(
                field_name,
                f'{label.split(" ")[0]}: {product.value(label)} as published, which is '
                f"{getattr(motorhome, field_name)}mm. WildAx state dimensions to two "
                f"decimal places in metres, so this is accurate to the centimetre — a "
                f"difference of a few mm from FMLV's figure is precision, not a change",
            )

    if motorhome.berths is not None:
        record("berths", f'Berths: {product.value("Berths")}')
    if motorhome.mh_passenger_seats_inc_driver is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f'Seatbelts: {product.value("Seatbelts")}',
        )
    # **No mass is proposed by a panel that contradicts itself.** Where WildAx's own
    # payload does not equal MTPLM less MRO, one of the three figures is a typo and
    # nothing on the page says which, so proposing any of them risks overwriting a
    # correct FMLV figure with a wrong one. All three known cases prove the point: FMLV
    # holds 3500 where the Constellation 3 XL publishes 3496, and holds the derived
    # payload for the Aurora XL and the Altair RL where WildAx print something else.
    # Emitting nothing raises a no-op "not found this run" row and preserves all of it.
    if product.reconciles:
        if product.mtplm_kilograms is not None:
            record("mtplm_kilograms", f'MTPLM: {product.value("MTPLM")}. {payload_basis}')
        if product.mro_kilograms is not None:
            record("mro_kilograms", f'MRO: {product.value("MRO")}. {payload_basis}')
        if product.derived_payload_kilograms is not None:
            record(
                "mh_payload_kilograms",
                f"payload {product.derived_payload_kilograms}kg, derived as MTPLM less "
                f"MRO per the settled rule rather than taken from the panel. "
                f"{payload_basis}",
            )
    if product.rrp_pounds is not None:
        record("rrp_pounds", f"price list: {product.price_reason}")
    if body_type is not None:
        record("body_type", body_reason)

    if sleeping_area is not None:
        record("sleeping_area", f"Campervan Layout — {sleeping_reason}")
    for field_name, label in (
        ("lounge_location", "Lounge"),
        ("kitchen_location", "Kitchen"),
        ("bathroom_layout", "Shower/Toilet"),
    ):
        if getattr(motorhome, field_name):
            record(field_name, f'Campervan Layout — {label}: {product.value(label)}')
    if motorhome.bed_types:
        record("bed_types", f'Bed type: {product.value("Bed type")}')

    for name, feature in features.items():
        record(name, f"{feature.note or 'read from the specification'}: {feature.snippet}")

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001
    snapshot_dir: Path,  # noqa: ARG001
    *,
    ranges: tuple[tuple[str, str], ...] = (),  # noqa: ARG001
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every Wildax campervan the site publishes.

    Eight fetches, one per range page. The price list is read from the first of them and
    reused, because its panel is baked into every page.
    """
    panels: dict[tuple[str, str], _Panel] = {}
    prices: list[PriceRow] = []
    seen_on_site: set[tuple[str, str]] = set()

    for slug in RANGE_SLUGS:
        url = f"{BASE_URL}/{slug}"
        on_progress(f"fetching {url}")
        lines = visible_lines(
            http.fetch(url).file_path.read_text(encoding="utf-8", errors="replace")
        )
        if not prices:
            prices = parse_price_list(lines)
            on_progress(
                f"read the price list from {url}: {len(prices)} priced vehicle lines. It "
                f"is an off-canvas nav panel present in every page, so it costs no extra "
                f"fetch"
            )
        found = spec_panels(lines)
        if not found:
            on_progress(f"NO SPEC PANELS on {url} — every model on this page is lost")
            continue
        for panel in found:
            panels[panel.identity] = panel
            seen_on_site.add(panel.identity)
        on_progress(
            f"read {len(found)} model(s) from {slug}: "
            + ", ".join(" ".join(p.identity).strip() for p in found)
        )

    if not prices:
        on_progress(
            "NO PRICE LIST FOUND on any range page. It is normally an off-canvas panel "
            "reachable from the Pricelist item in the nav; if the site has moved it, no "
            "price is proposed this run and FMLV's own figures stand"
        )

    extracted: list[ExtractedMotorhome] = []
    collected: list[tuple[_Model, WildaxCampervan]] = []
    mismatches: list[str] = []
    unpriced: list[str] = []
    unplaced: list[str] = []

    for spec in MODELS:
        panel = panels.get((spec.panel_range, spec.panel_model))
        if panel is None:
            on_progress(
                f"dropping {spec.label} — no '{spec.panel_label}' panel on "
                f"{spec.url}. Either the model has gone or its published name has changed"
            )
            continue
        seen_on_site.discard((spec.panel_range, spec.panel_model))

        pounds, price_reason, _ = resolve_price(prices, spec)
        if pounds is None:
            unpriced.append(f"{spec.label} ({price_reason})")

        product = WildaxCampervan(
            spec=spec, panel=panel, rrp_pounds=pounds, price_reason=price_reason
        )
        reconciles, reason = _reconciles(product)
        if product.mtplm_kilograms is None or product.mro_kilograms is None:
            on_progress(f"dropping {spec.label} — {reason}")
            continue
        if not reconciles:
            mismatches.append(f"{spec.label}: {reason}")

        extracted.append(
            build_extracted(
                dataclasses.replace(product, reconciles=reconciles), payload_basis=reason
            )
        )
        collected.append((spec, product))

        _, sleeping_reason = sleeping_area_for(panel.sleeping_areas)
        for label, value in (
            ("kitchen", panel.fields.get("Kitchen")),
            ("washroom", panel.fields.get("Shower/Toilet")),
        ):
            front, rear, side = _position(value)
            if rear and side:
                unplaced.append(f"{spec.label} {label} ({value})")
        if not panel.sleeping_areas or "not proposed" in sleeping_reason:
            unplaced.append(f"{spec.label} sleeping area ({sleeping_reason})")

        on_progress(
            f"read {spec.label}: {product.mtplm_kilograms}kg, "
            f"{product.derived_payload_kilograms}kg payload, "
            f"{_count(product.value('Berths'))} berth, "
            f"{_count(product.value('Seatbelts'))} belted seats, "
            + (f"£{pounds:,}" if pounds is not None else "no price")
        )

    for identity in sorted(seen_on_site):
        on_progress(
            f"ON THE SITE BUT NOT IN THIS ADAPTER: {' '.join(identity).strip()}. It is not "
            f"collected, so it cannot reach FMLV until the roster is updated"
        )

    if mismatches:
        on_progress(
            "THE PUBLISHED PAYLOAD DOES NOT RECONCILE on "
            + "; ".join(mismatches)
            + ". NO MASS IS PROPOSED for these: one of the three figures is a typo "
            "and nothing on the page says which, so FMLV's own MTPLM, MRO and "
            "payload all stand rather than risk overwriting a correct figure with a "
            "wrong one. All three known cases prove the point — FMLV holds 3500 "
            "where the Constellation 3 XL publishes 3496, and holds the derived "
            "payload for the Aurora XL and the Altair RL. A NEW one would mean the "
            "parse had moved"
        )

    for suspect in suspect_copied_figures(collected):
        on_progress(
            f"A FIGURE LOOKS COPIED BETWEEN SIBLING MODELS: {suspect}. Two "
            f"models on one page are different vehicles, so this looks like a "
            f"pasted cell. The published payload reconciles either way, so the "
            f"self-check cannot settle it — check against FMLV "
            f"before accepting"
        )

    if unpriced:
        on_progress(
            f"NO PRICE PROPOSED for {', '.join(unpriced)}. No POA is invented and FMLV's "
            f"own figure stands"
        )

    if unplaced:
        on_progress(
            "HABITATION POSITION NOT PROPOSED for "
            + "; ".join(unplaced)
            + ". WildAx describe these as both rear and side, and FMLV makes those "
            "mutually exclusive, so there is no value to record. Left blank deliberately "
            "rather than guessed"
        )

    on_progress(
        "PRICES ARE VARIANT-KEYED: the price list is keyed on gearbox, engine and paint "
        "where the models are keyed on layout, so the lowest price in each group is "
        "recorded as the base vehicle. Constellation 3 and 4 share one row, as do 3 XL and "
        "4 XL; Pulsar, Altair RS and Altair RL publish an automatic price only, although "
        "their panels state a 6-speed manual"
    )

    if len(extracted) != EXPECTED_MODELS:
        on_progress(
            f"expected {EXPECTED_MODELS} models and collected {len(extracted)} — check "
            f"whether the range has really changed"
        )
    on_progress(f"collected {len(extracted)} Wildax campervan(s)")
    return extracted
