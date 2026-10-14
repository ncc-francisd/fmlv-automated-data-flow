"""Airstream (lowdhams.com) — American caravans sold in the UK by one exclusive importer.

See `docs/adapters/airstream.md` for the survey. **The source is Lowdhams' browse page**,
`/browse/new-airstream-caravans`, which is server-rendered and carries a card per vehicle
linking a page with a structured `Specification` block.

## This adapter proposes no mass and no dimension, and that is the whole point of it

Airstream publish their European figures in their own owner's manual, and **FMLV already
holds every one of them, correctly, to the kilogram and the millimetre**. There is nothing
to propose and a great deal to protect, because the pages this adapter reads carry masses
and dimensions of their own that are *not* the model's.

What it maintains is what the importer decides: the roster, the price and the berths —
plus the twin axle, which nothing else here publishes.

## The trap is an MTPLM that looks like data and is a plating choice

Airstream publish an MTPLM **band** per model, not a figure:

```
                                 534      684     25IB
MASS IN RUNNING ORDER          1580kg   2165kg  2475kg
MTPLM Lower limit              1830kg   2500kg  2800kg
MTPLM Upper limit              1900kg   2920kg  3500kg
```

A caravan can be plated anywhere inside its band — downplating is routine, usually so the
outfit fits a driving licence — so **the MTPLM on a specific unit is a fact about that
unit**, not about the model. FMLV holds the upper limit, which is what MTPLM means: the
maximum technically permissible mass.

Lowdhams' stock pages print the plate. The 534 reads 1830kg, which is its band's *lower*
limit; the 684 reads 2400kg against FMLV's 2920. Recorded, those would have cut 520kg off
a product and looked entirely plausible doing it. `plating_verdict` tests every stock-page
MTPLM against the published band and narrates what it found, so the refusal is reasoned
and visible rather than a silent omission.

The dimensions are refused for a duller reason: the stock pages give two decimals of a
metre where FMLV holds millimetres, so taking `6.80m` would round 6860 down to 6800.

## `Overall Height` is the interior height under an exterior label

The one field that is not merely imprecise but wrong. The World Traveller brochure prints
`Exterior height 2.74 m` and `Interior height 2 m`; the stock page's `Overall Height` reads
`2.00m` and FMLV holds 2740. The 534 (1.99m) and 25 IB (1.99m) show the same shape, while
the 684's 2.69m looks like a genuine exterior figure — so the field is inconsistent as well
as mislabelled, and is never read.

## Condition, not the slug, decides what is a product

Every card carries `New` or `Used`. The International 25 IB is a used 2024 unit at £97,500
and is **not the current range** — the requester confirmed on 14 October 2026 that it is
discontinued. It is dropped on its `Condition`, which is the manufacturer-independent test,
rather than on its `used-` slug, which is incidental.

**Dropping it reports it as disappeared, which is the intended signal**: a reviewer sees it
and deactivates it in FMLV. Nothing here archives anything.

## Lowdhams is the importer, and that decides what is taken from where

The settled rule: an exclusive importer decides **what exists and what it costs**, and the
factory decides **every number**. Lowdhams is both importer and dealer, so the division
does more work here than usual — it is exactly why the price is taken and the MTPLM is not.
"""

from __future__ import annotations

import html as htmllib
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.caravan import Caravan
from ..product_model.enums import CaravanBodyType
from ..vehicle_class import VehicleClass
from . import habitation
from .base import ExtractedCaravan, Provenance

__all__ = [
    "BASE_URL",
    "BROWSE_URL",
    "EUROPEAN_SPECIFICATION",
    "EXPECTED_PRODUCTS",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "MICRO_CARAVAN_CEILING_KG",
    "MINIMUM_CREDIBLE_PRICE",
    "VEHICLE_CLASS",
    "Card",
    "PublishedSpecification",
    "Vehicle",
    "body_type_for",
    "build_extracted",
    "collect",
    "find_vehicle_paths",
    "parse_cards",
    "parse_features",
    "parse_specification",
    "parse_vehicle",
    "plating_verdict",
]

BASE_URL = "https://www.lowdhams.com"
MANUFACTURER = "Airstream"
MANUFACTURER_DISPLAY_NAME = "Airstream"

#: Towed, so a caravan. Without this the module registers under the motorhome class.
VEHICLE_CLASS = VehicleClass.CARAVAN

#: The one page that lists the range. Server-rendered, so no browser is needed, and it
#: links the used stock as well as the new — hence the `Condition` test below.
BROWSE_URL = f"{BASE_URL}/browse/new-airstream-caravans"

#: Three `New` caravans — International 534, International 684, World Traveller 22RB. The
#: browse page links a fourth, the used 25 IB, which is dropped rather than counted.
EXPECTED_PRODUCTS = 3

#: Below this, a figure on a card is not the price of an Airstream. The cheapest is the
#: World Traveller at £72,995 and the monthly finance figures beside each price are
#: four-digit — £1,229 on the 684 — so this sits in a very wide gap.
MINIMUM_CREDIBLE_PRICE = 30_000

#: A caravan is a micro only where the manufacturer calls it one **and** its MTPLM is at
#: or below this. Airstream call nothing a micro and the lightest here is 1830kg, so the
#: ceiling is never reached; it is named so `body_type_for` states the test it applied
#: rather than asserting `rigid` from nowhere.
MICRO_CARAVAN_CEILING_KG = 1250


@dataclass(frozen=True)
class PublishedSpecification:
    """One model's figures as **Airstream's own European owner's manual** prints them.

    Written down rather than fetched, deliberately. The manual
    (`2024-aeu-owners-manual-rev01.pdf`) lives on a content-hashed CDN URL behind an
    Algolia-driven index that serves no links to a plain fetch, so there is no rediscovery
    path worth depending on — and nothing here would be proposed anyway. Every figure
    below is already in FMLV, unchanged, and this table exists to *defend* it: it is what
    `plating_verdict` tests the stock pages against.

    `mtplm_upper_kilograms` is the MTPLM proper — the maximum technically permissible
    mass, and what FMLV holds. `mtplm_lower_kilograms` is the floor of the band a unit may
    be plated down to.
    """

    mro_kilograms: int
    mtplm_lower_kilograms: int
    mtplm_upper_kilograms: int
    shipping_length_mm: int
    height_mm: int
    width_mm: int


#: Keyed by the `Model` the stock page's specification block states.
#:
#: The three Internationals are the manual's own table, page 7. The World Traveller is not
#: in it — it is a Lowdhams exclusive — and comes from its brochure, which publishes a
#: single MTPLM rather than a band, so its limits are equal.
EUROPEAN_SPECIFICATION: dict[str, PublishedSpecification] = {
    "534": PublishedSpecification(1580, 1830, 1900, 6860, 2700, 2280),
    "684": PublishedSpecification(2165, 2500, 2920, 8290, 2750, 2490),
    "25 IB": PublishedSpecification(2475, 2800, 3500, 8290, 2840, 2490),
    "22RB": PublishedSpecification(1700, 2000, 2000, 7210, 2740, 2290),
}

#: `Only &pound;109,950` on the card. **Anchored on the word**, because the finance figure
#: beside it is also a price — `£1,229 / Monthly` — and is the smaller of the two, so
#: neither "the first" nor "the lowest" would pick the right one.
_CARD_PRICE = re.compile(r"Only\s*(?:&pound;|£)\s*([\d,]+)", re.I)

#: `/vehicle/new-airstream-international-534-caravan-424170`. Absolute on this page, so the
#: host is optional in the pattern rather than assumed away.
_VEHICLE_LINK = re.compile(rf'href="(?:{re.escape(BASE_URL)})?(/vehicle/[a-z0-9-]+)"', re.I)

#: The structured blocks every vehicle page carries, label then value.
_SPEC_BLOCK = re.compile(r'id="product-specs"')
_FEATURES_BLOCK = re.compile(r'id="product-features"')

#: Where the features list stops being the caravan and starts being Lowdhams. Everything
#: from here on is dealership copy — warranty, part exchange, insurance — and reads as
#: equipment if it is not cut off.
_DEALERSHIP_COPY = re.compile(r"^(MEMBERSHIP BENEFITS|Description|Enquire now)$", re.I)

#: The labels worth reading out of the specification block. Everything else there is
#: either dealer metadata (`Unique ID`) or a field this adapter refuses (`MTPLM`,
#: `Overall Length`, `Overall Width`, `Overall Height`) — and the refused ones are still
#: read, so the run can say what it turned down and why.
_WANTED_LABELS = frozenset(
    {
        "Make",
        "Range",
        "Model",
        "Type",
        "Condition",
        "Berths",
        "Axles",
        "Bedroom Layout",
        "Registration",
        "MTPLM",
        "Overall Length",
        "Overall Width",
        "Overall Height",
    }
)


def _plain(fragment: str) -> str:
    """Markup as readable lines, one per block element."""
    body = re.sub(r"(?is)<(script|style|head|nav|header|footer)\b.*?</\1>", " ", fragment)
    text = re.sub(
        r"(?i)</(p|h\d|div|li|tr|td|th|dt|dd|br|span|a|strong)>|<br\s*/?>", "\n", body
    )
    return re.sub(r"<[^>]+>", " ", htmllib.unescape(text))


def _lines(fragment: str) -> list[str]:
    return [" ".join(line.split()) for line in _plain(fragment).split("\n") if line.strip()]


def find_vehicle_paths(browse_html: str) -> list[str]:
    """Every `/vehicle/` page the browse page links, in the order it links them.

    **Rediscovered each run rather than written in.** Lowdhams publish no other roster, and
    a hardcoded list would miss a new Airstream in silence — the one way an adapter is
    badly wrong while looking healthy.
    """
    seen: dict[str, None] = {}
    for match in _VEHICLE_LINK.finditer(browse_html):
        seen.setdefault(match.group(1), None)
    return list(seen)


@dataclass(frozen=True)
class Card:
    """What the browse page's card says, which is the price and nothing else reliable."""

    path: str
    rrp_pounds: int | None


def parse_cards(browse_html: str) -> dict[str, Card]:
    """The price per vehicle path, from the cards on the browse page.

    **The price is only here.** The vehicle page itself prints no £ figure for the
    caravan — only finance furniture — so the browse page is not an optional extra fetch.

    Each card is read as the markup following its own link rather than by splitting the
    page into cards: the link appears twice per card, once on the image and once on the
    title, and the window is wide enough that either occurrence reaches the price.
    """
    cards: dict[str, Card] = {}
    for match in _VEHICLE_LINK.finditer(browse_html):
        path = match.group(1)
        if path in cards and cards[path].rrp_pounds is not None:
            continue
        window = browse_html[match.start() : match.end() + 3000]
        found = _CARD_PRICE.search(window)
        price = int(found.group(1).replace(",", "")) if found else None
        if price is not None and price < MINIMUM_CREDIBLE_PRICE:
            price = None
        if path not in cards or price is not None:
            cards[path] = Card(path=path, rrp_pounds=price)
    return cards


def parse_specification(page_html: str) -> dict[str, str]:
    """The vehicle page's `Specification` block, as `{label: value}`.

    The block is a flat run of alternating labels and values, so it is paired off in order
    against the labels worth having. A label whose value is missing would otherwise pair
    with the next label, so only a value that is **not itself a label** is kept.
    """
    start = _SPEC_BLOCK.search(page_html)
    if start is None:
        return {}
    rest = page_html[start.start() :]
    end = _FEATURES_BLOCK.search(rest)
    lines = _lines(rest[: end.start()] if end else rest[:20000])

    found: dict[str, str] = {}
    for index, line in enumerate(lines[:-1]):
        if line not in _WANTED_LABELS or line in found:
            continue
        value = lines[index + 1]
        if value in _WANTED_LABELS:
            continue
        found[line] = value
    return found


def parse_features(page_html: str) -> list[str]:
    """The vehicle page's `Features` list, cut off before the dealership copy begins.

    **These are a dealer's notes on one unit, not a manufacturer's standard
    specification**, and they carry priced extras in among the equipment — `Motor mover
    (Optional Extra)`. `habitation.usable_lines` discards a line that marks itself that
    way, which is the whole defence available here, and the provenance says where the
    reading came from so a reviewer can weigh it.

    Two of the four pages carry no features block at all, so an empty list is ordinary.
    """
    start = _FEATURES_BLOCK.search(page_html)
    if start is None:
        return []
    lines = _lines(page_html[start.start() : start.start() + 20000])
    # The block opens with its own `Features` heading; what precedes it is the div's tag.
    try:
        begin = lines.index("Features") + 1
    except ValueError:
        return []
    items: list[str] = []
    for line in lines[begin:]:
        if _DEALERSHIP_COPY.match(line):
            break
        items.append(line)
    return items


@dataclass
class Vehicle:
    """One caravan as its stock page describes it, refusals included.

    The masses and dimensions are carried **so the run can say what it turned down**. They
    are never built into a `Caravan` and never given provenance.
    """

    url: str
    manufacturer_range: str | None = None
    model: str | None = None
    condition: str | None = None
    berths: int | None = None
    twin_axle: bool | None = None
    registration: str | None = None
    rrp_pounds: int | None = None
    stock_mtplm_kilograms: int | None = None
    stock_dimensions: dict[str, str] = field(default_factory=dict)
    equipment: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return " ".join(part for part in (self.manufacturer_range, self.model) if part)

    @property
    def is_new(self) -> bool:
        return (self.condition or "").strip().lower() == "new"


def _integer(value: str | None) -> int | None:
    if value is None:
        return None
    match = re.search(r"\d[\d,]*", value)
    return int(match.group(0).replace(",", "")) if match else None


def parse_vehicle(
    page_html: str, url: str, *, rrp_pounds: int | None = None
) -> Vehicle | None:
    """One stock page, or `None` when it carries no specification block at all."""
    spec = parse_specification(page_html)
    if not spec:
        return None
    axles = (spec.get("Axles") or "").strip().lower()
    return Vehicle(
        url=url,
        manufacturer_range=spec.get("Range"),
        model=spec.get("Model"),
        condition=spec.get("Condition"),
        berths=_integer(spec.get("Berths")),
        twin_axle={"twin": True, "single": False}.get(axles),
        registration=spec.get("Registration"),
        rrp_pounds=rrp_pounds,
        stock_mtplm_kilograms=_integer(spec.get("MTPLM")),
        stock_dimensions={
            label: spec[label]
            for label in ("Overall Length", "Overall Width", "Overall Height")
            if label in spec
        },
        equipment=parse_features(page_html),
    )


def plating_verdict(model: str | None, stock_mtplm_kilograms: int | None) -> str:
    """What the stock page's MTPLM is, tested against Airstream's published band.

    This is the self-check, and it is a real one — Airstream publish a lower and an upper
    limit, so a figure can be *placed* rather than merely doubted. Nothing is ever proposed
    from it; the verdict is narrated so a reviewer can see that a smaller MTPLM was found,
    considered and refused, which is a different thing from one never having been read.
    """
    published = EUROPEAN_SPECIFICATION.get(model or "")
    if stock_mtplm_kilograms is None:
        return "the page states no MTPLM"
    if published is None:
        return (
            f"the page plates this unit at {stock_mtplm_kilograms}kg. Airstream publish no "
            f"European band for a model named {model!r}, so there is nothing to place it "
            f"against and nothing is proposed"
        )
    upper = published.mtplm_upper_kilograms
    lower = published.mtplm_lower_kilograms
    if stock_mtplm_kilograms == upper:
        return (
            f"this unit is plated at {stock_mtplm_kilograms}kg, which is Airstream's "
            f"published upper limit and so the model's MTPLM. FMLV already holds it"
        )
    if lower <= stock_mtplm_kilograms < upper:
        return (
            f"this unit is plated at {stock_mtplm_kilograms}kg, inside Airstream's "
            f"published band of {lower}-{upper}kg but below its upper limit — a downplate "
            f"of this unit, not the model's MTPLM, which is {upper}kg and is what FMLV "
            f"holds. Nothing is proposed"
        )
    return (
        f"this unit is plated at {stock_mtplm_kilograms}kg, which is OUTSIDE Airstream's "
        f"published band of {lower}-{upper}kg. Either it is plated unusually or the model "
        f"has changed since the European manual — worth asking Lowdhams about. Nothing is "
        f"proposed"
    )


def body_type_for(vehicle: Vehicle) -> tuple[CaravanBodyType | None, str]:
    """`rigid` for every Airstream, with the micro test stated rather than skipped."""
    published = EUROPEAN_SPECIFICATION.get(vehicle.model or "")
    mtplm = published.mtplm_upper_kilograms if published else None
    if mtplm is not None and mtplm <= MICRO_CARAVAN_CEILING_KG:
        return None, (
            f"no body type proposed: at {mtplm}kg this is light enough to be a micro, and "
            f"the rule needs the manufacturer to call it one as well. Airstream do not"
        )
    weight = (
        f", and its MTPLM of {mtplm}kg is far above the {MICRO_CARAVAN_CEILING_KG}kg a "
        f"micro has to sit under"
        if mtplm is not None
        else ""
    )
    return CaravanBodyType.RIGID, (
        f"a rigid caravan: a riveted aluminium monocoque with no folding or elevating "
        f"part{weight}"
    )


def _reconciles(vehicle: Vehicle) -> tuple[bool, str]:
    """**Structural, because every arithmetic figure here is refused.**

    What can be checked is that the page identifies one caravan: that it names a range and
    a model, and that any price found is credible for one. The MTPLM band does the other
    half of the work, in `plating_verdict`, where it belongs — a unit plated below its
    model's limit is correct data about the wrong subject, not a misparse, so it must not
    drop the product.
    """
    if not vehicle.manufacturer_range or not vehicle.model:
        return False, (
            "the specification block names no range or no model, so nothing identifies "
            "which caravan this page is"
        )
    if vehicle.rrp_pounds is not None and vehicle.rrp_pounds < MINIMUM_CREDIBLE_PRICE:
        return False, (
            f"£{vehicle.rrp_pounds:,} is below the £{MINIMUM_CREDIBLE_PRICE:,} an "
            f"Airstream can credibly cost — that will be the monthly finance figure"
        )
    if vehicle.rrp_pounds is None:
        return True, (
            "no price is published on this vehicle's card, so FMLV's own figure stands"
        )
    return True, (
        f"£{vehicle.rrp_pounds:,}, the headline price on Lowdhams' own card. They are the "
        f"exclusive UK importer, so the price is theirs to state"
    )


#: How each habitation reading is introduced. Findings for a person to type in, and every
#: one says where it came from, because a dealer's notes on one unit are a weaker source
#: than a manufacturer's standard specification.
_FEATURE_NOTES: dict[str, str] = {
    "heating": "the heating in Lowdhams' feature list for this unit",
    "refrigeration": "the refrigeration in Lowdhams' feature list for this unit",
    "microwave": "a microwave in Lowdhams' feature list for this unit",
    "shower_toilet_separated": "the washroom as Lowdhams' feature list describes it",
}


def build_extracted(vehicle: Vehicle, *, basis: str) -> ExtractedCaravan:
    """One Airstream, with provenance on everything it proposes — and no mass or size."""
    features = habitation.features_from(vehicle.equipment)
    # Dropped as on every other adapter: a feature list names beds without saying which
    # are built in and which are made up out of the seating.
    features.pop("bed_types", None)

    body_type, body_type_reason = body_type_for(vehicle)
    caravan = Caravan(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=vehicle.manufacturer_range,
        model=vehicle.model,
        berths=vehicle.berths,
        rrp_pounds=vehicle.rrp_pounds,
        price_min_range_pounds=vehicle.rrp_pounds,
        body_type=body_type,
        twin_axle=bool(vehicle.twin_axle),
        # **Deliberately absent, every one of them.** Airstream's own European manual
        # holds these and FMLV already matches it exactly; the figures on this page are
        # one unit's plate and two decimals of a metre. See the module docstring.
        mtplm_kilograms=None,
        mro_kilograms=None,
        personal_effects_payload_kilograms=None,
        shipping_length_mm=None,
        exterior_body_length_mm=None,
        internal_length_mm=None,
        overall_width_mm=None,
        height_mm=None,
    )
    for name, feature in features.items():
        setattr(caravan, name, feature.value)

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=vehicle.url, snippet=f"{vehicle.label} — {snippet}"
        )

    record(
        "manufacturer_range",
        f'range "{vehicle.manufacturer_range}", from the specification block\'s own Range '
        f"field",
    )
    record("model", f'model "{vehicle.model}", from the specification block\'s Model field')
    if vehicle.rrp_pounds is not None:
        record("rrp_pounds", basis)
        record(
            "price_min_range_pounds",
            f"£{vehicle.rrp_pounds:,} — Lowdhams list one price for this caravan, so the "
            f"range minimum is the same figure",
        )
    if vehicle.berths is not None:
        record("berths", f"{vehicle.berths} berths, from the specification block")
    if vehicle.twin_axle is not None:
        record(
            "twin_axle",
            f"Axles: {'Twin' if vehicle.twin_axle else 'Single'}. Lowdhams state this "
            f"outright, which no Airstream document does",
        )
    if body_type is not None:
        record("body_type", body_type_reason)
    for name, feature in features.items():
        provenance[name] = Provenance(
            source_url=vehicle.url,
            snippet=(
                f"{vehicle.label} — {feature.note or _FEATURE_NOTES.get(name, name)}: "
                f"{feature.snippet!r}. NOTE: this is Lowdhams' feature list for one unit, "
                f"not an Airstream standard specification"
            ),
        )
    return ExtractedCaravan(caravan=caravan, provenance=provenance)


def _refusal_notes(vehicle: Vehicle) -> Iterable[str]:
    """What this page offered that was turned down, and on what grounds."""
    yield (
        f"{vehicle.label} — MTPLM: "
        f"{plating_verdict(vehicle.model, vehicle.stock_mtplm_kilograms)}"
    )
    # **`Full central heating` is deliberately not resolved.** Every other appearance of
    # "central heating" in this repo's fixtures carries `Alde` or `radiator` with it and
    # reads as wet, but one is `Truma diesel central heating`, which is warm air — so the
    # bare phrase does not settle the kind, and teaching the shared vocabulary that it
    # does would misread that vehicle. Narrated instead, which is what the gap is for.
    if unclear := habitation.heating_is_unclear(vehicle.equipment):
        yield (
            f"{vehicle.label} — HEATING NOT PROPOSED: {unclear!r} names a heating system "
            f"without naming its kind. 'Central heating' alone is not enough — it is wet "
            f"where Alde or a radiator is named and warm air on a Truma diesel — so FMLV's "
            f"own value stands"
        )
    if vehicle.stock_dimensions:
        stated = ", ".join(f"{k} {v}" for k, v in vehicle.stock_dimensions.items())
        yield (
            f"{vehicle.label} — DIMENSIONS NOT PROPOSED. The page states {stated}. The "
            f"length and width are two decimals of a metre where FMLV holds millimetres, "
            f"so recording them would round 6860 to 6800; and `Overall Height` is the "
            f"INTERIOR height under an exterior label — Airstream's brochure prints "
            f"'Exterior height 2.74 m' and 'Interior height 2 m' for the 22RB, which this "
            f"page lists as 2.00m"
        )


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 — the browse page and the stock pages are plain HTML
    snapshot_dir: Path,  # noqa: ARG001 — `http` already snapshots into it
    *,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedCaravan]:
    """Every current Airstream caravan Lowdhams list as new."""
    browse = http.fetch(BROWSE_URL)
    if browse.status_code != 200:
        msg = f"{BROWSE_URL} returned {browse.status_code} — the only roster there is"
        raise RuntimeError(msg)
    browse_html = browse.file_path.read_text(encoding="utf-8", errors="replace")

    paths = find_vehicle_paths(browse_html)
    if not paths:
        msg = (
            f"no /vehicle/ pages linked from {BROWSE_URL} — Lowdhams publish no other "
            f"roster, so this cannot be read as the range having been withdrawn"
        )
        raise RuntimeError(msg)
    cards = parse_cards(browse_html)
    on_progress(f"the browse page links {len(paths)} vehicle page(s)")

    results: list[ExtractedCaravan] = []
    for path in paths:
        url = f"{BASE_URL}{path}"
        page = http.fetch(url)
        if page.status_code != 200:
            on_progress(f"SKIPPED: {url} returned {page.status_code}")
            continue
        card = cards.get(path)
        vehicle = parse_vehicle(
            page.file_path.read_text(encoding="utf-8", errors="replace"),
            url,
            rrp_pounds=card.rrp_pounds if card else None,
        )
        if vehicle is None:
            on_progress(f"SKIPPED: {url} carries no Specification block")
            continue
        if not vehicle.is_new:
            on_progress(
                f"{vehicle.label} — NOT THE CURRENT RANGE: this page is Condition "
                f"'{vehicle.condition}', a second-hand unit Lowdhams happen to have in "
                f"stock. It is not collected, so it will be reported as disappeared for a "
                f"reviewer to deactivate"
            )
            continue

        reconciles, basis = _reconciles(vehicle)
        if not reconciles:
            on_progress(f"{vehicle.label or url} — DROPPED: {basis}")
            continue

        results.append(build_extracted(vehicle, basis=basis))
        on_progress(
            f"{vehicle.label} — "
            + (f"£{vehicle.rrp_pounds:,}" if vehicle.rrp_pounds else "no price on its card")
            + f", {vehicle.berths} berth, "
            + ("twin axle" if vehicle.twin_axle else "single axle")
        )
        for note in _refusal_notes(vehicle):
            on_progress(note)

    on_progress(
        "NO MASS AND NO DIMENSION IS PROPOSED, and that is the point of this adapter. "
        "Airstream publish their European figures in their own owner's manual and FMLV "
        "already holds every one of them exactly. What Lowdhams print is one unit's "
        "plated MTPLM — which may be a downplate — and dimensions rounded to two decimals "
        "of a metre, with the interior height labelled as the overall height."
    )
    if len(results) != EXPECTED_PRODUCTS:
        on_progress(
            f"expected {EXPECTED_PRODUCTS} caravans and collected {len(results)} — check "
            f"whether Lowdhams have changed the range"
        )
    on_progress(f"collected {len(results)} Airstream caravan(s)")
    return results
