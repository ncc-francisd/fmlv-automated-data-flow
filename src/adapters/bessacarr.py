"""Bessacarr By Design touring caravans, from `bessacarrcaravan.co.uk`.

Surveyed and built 17 September 2026. See `docs/adapters/bessacarr.md`.

**The third brand under `Swift Group Ltd`**, after `swift.py` (id 26) and `ace.py`
(id 264). `ADAPTERS` is keyed on `(manufacturer, display name, product area)`, which the
Ace build introduced for exactly this reason, so this module needed no wiring change of
its own — only a key naming the brand.

**It is a brand, not a dealer special, and that was ruled on rather than assumed.** The
site is Couplands Caravans', Couplands are the only retailer, and the vehicles are built
on the Swift Elegance Grande, so the shape of a dealer special is all there — FMLV holds
the predecessor range that way, `Cameo by Design`, same dealer, model year 2022, with
`dealer`, `dealer_specials_range` and `dealer_model_variant` all filled. The requester
settled it on 17 September 2026: Swift no longer do dealer specials, Bessacarr has its own
public-facing website separate from Couplands' own (which sells Bailey and others), and
the arrangement is the one Benimar has with Marquis Leisure — sole UK retailer, still a
brand in its own right. **So the three dealer columns are written by nothing here**, which
matches FMLV's own four rows, where all three are blank.

**Everything is a rebadged Swift Elegance Grande**, and that is what makes the numbers
checkable. Every dimension FMLV holds for the 2025/26 Elegance Grande is byte-identical to
this site — internal 6360, shipping 7980, awning 10490, height 2590, width 2450 — and the
masses move consistently: MRO is **+43kg on all four**, which is the Couplands kit (Truma
Aventa aircon, E&P levelling, solar, Alde heating), and the MTPLM is **plated up to a flat
2250kg** from Swift's 2055-2123.

That plate-up is the single most valuable thing this adapter proposes. FMLV holds
2125/2104/2111/2057, which is `MRO + 160` on all four — derived from the old
personal-effects figure of 160kg rather than from any published plate — and 160kg is what
FMLV holds in the payload column too. The site's 2250 reconciles exactly against the site's
own published payloads on all four. **Both figures are stale in FMLV and this run corrects
them.**

## The source is the poorest of the three Swift Group brands

Plain server-rendered HTML, one page per model at `/bessacarr<model>`. **No JSON, no
JavaScript, no PDF** — the opposite of `ace.py`, whose range pages carry their whole
dataset inline. The spec table is a label/value list, and the labels are spelt out in
English including the misspelling: `Maximum Technical Permissable Laden Mass (MTPLM)`.
There is no `mtplm` token anywhere in the raw HTML, so every pattern here anchors on the
printed words.

## The roster comes from the range page's cards, not from its navigation

**The 780 must not be collected**, and telling it apart is the whole job of
`model_range_roster`. `/model-range` links all five model pages from its navigation
dropdown, 780 included, but publishes only **four cards** — `835 4 berth 2250 MTPLM Twin
Axle Grade 3 Insulation` and the same for 845, 850 and 860. The 780 is a 2025 model, is
marked SOLD OUT on its own page, is inactive in FMLV and has no card.

So the roster is read from the card shape, which requires an MTPLM beside the berth count.
Taking the `/bessacarr\\d+` hrefs instead would collect five, and the fifth is a vehicle
nobody wants reviewed. `EXPECTED_LAYOUTS` is the backstop: Bessacarr publish no count of
their own, so nothing else would notice a card being lost.

## Two self-checks, and the excluded 780 is what proves they work

1. **`Total User Payload == MTPLM - MRO`**, within the spec table. All three figures are
   published independently, so this is a real check rather than the true-by-construction
   identity several adapters settle for. It holds on all four: 285, 306, 299, 353.
2. **The `/model-range` card's MTPLM against the model page's own spec table**, which is a
   genuine cross-document check — two pages, written separately, agreeing on 2250.

The 780 fails both, which is the reassurance that neither is vacuous. Its MRO of 1774 plus
its payload of 215 makes 1989 against a stated MTPLM of 1900, and its own header badge says
**1800kg**, a third figure. The reason is now visible: its published Personal Effects
Payload of 156kg is *exactly* what FMLV holds for the Swift Elegance Grande 780, and 1900
is exactly Swift's MTPLM, so the page is carrying the base Elegance Grande's spec sheet
with only the MRO updated for the conversion. Even if it were wanted, it could not be
collected safely — one published figure is wrong and nothing on the site says which.

## Payload: the total, not the figure labelled personal effects

Bessacarr print **both** halves FMLV has columns for, which Swift no longer do —
`swift_caravan.py` has to derive `MTPLM - MRO` into the personal-effects column precisely
because the split was withdrawn. So the obvious move is to take the figure whose label
matches the column. **It is the wrong one.**

`Total User Payload` and `Personal Effects Payload` are printed **equal** on the 835, 845
and 860, which says the site is not using the split rigorously. On the **850** they differ
— total 299, personal effects **306** — and 306 is the 845's figure, one row up, copied.
It exceeds its own vehicle's total capacity, so it is not merely a different basis.

So `personal_effects_payload_kilograms` takes the **total**, which is the one figure that
reconciles against the masses on all four, and the disagreement on the 850 is narrated
rather than silently resolved. This is also the requester's settled rule of 4 September
2026, applied unchanged: *where a model has one published payload figure, use it as the
personal-effects total.* `optional_equipment_payload_kilograms` is recorded with **no
value**, saying the adapter looked — FMLV holds it blank on all four, so the field comes
back confirmed and no reviewer sees a row.

## Habitation is thin, and it is the wrong equipment list

Worth stating plainly rather than leaving a reviewer to infer it. The only per-model list
on the site is **`Exclusive Bessacarr Features`** — the kit Couplands *add* to the base
caravan. The underlying Swift equipment is published nowhere on this site, and Swift
publish nothing about Bessacarr at all, so there is no standard-equipment list to read.

What survives is genuine but sparse: a `Freezer Shelf` on the twin-axles, `Truma Aventa
Comfort` air conditioning, solar, and `Alde Heating` where the prose mentions it. These
reach the reviewer as **findings** with the page's own words attached, never as proposals.

**`bed_types` is dropped**, for the same reason as on both halves of Swift. The pages carry
a per-model `Bed Sizes` block, but it names *positions* — `Front Double`, `Rear Double`,
`Side Bunk (Offside) 4 berth only` — without saying whether a bed is built in or made up
from the seating, which is exactly what `BedType` has to distinguish. The lists also carry
the same class of copy error as the payloads: the 835, 850 and 860 each list `Front Single
(Nearside)` twice where one is plainly the offside. Left to the reviewer and the drawing.

## Model year

The pages say `Model 2025` and link a `2024 brochure`, while FMLV holds all four as 2026.
`year` is a carry-through field only a person bumps (`src/diff/year_rollover.py`), so
nothing here emits it — but if FMLV's rows ever fall behind the current calendar year,
`cli._is_current_model_year` drops them from the baseline and all four arrive as new.
"""

from __future__ import annotations

import html as html_module
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.caravan import Caravan
from ..product_model.enums import CaravanBodyType
from ..vehicle_class import VehicleClass
from . import habitation
from .base import ExtractedCaravan, Provenance

__all__ = [
    "BASE_URL",
    "DEFAULT_RANGES",
    "EXPECTED_LAYOUTS",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "MANUFACTURER_RANGE",
    "VEHICLE_CLASS",
    "BessacarrCaravan",
    "collect",
]

BASE_URL = "https://www.bessacarrcaravan.co.uk"

#: The *legal* manufacturer, shared with `swift.py` and `ace.py` — see the module
#: docstring. The brand is carried by `MANUFACTURER_DISPLAY_NAME`, which is what
#: `ADAPTERS` keys on alongside it.
MANUFACTURER = "Swift Group Ltd"
MANUFACTURER_DISPLAY_NAME = "Bessacarr"

#: What makes this the caravan adapter. Without it `ADAPTERS` would register the module
#: under a motorhome key and it would answer for a product area it knows nothing about.
VEHICLE_CLASS = VehicleClass.CARAVAN

#: One range, spelt as FMLV's own export spells it. Every model page titles itself
#: `Bessacarr By Design 835`, so this is corroborated rather than assumed — but it is a
#: constant because the range is not derivable per layout the way Swift's titles are.
MANUFACTURER_RANGE = "Bessacarr By Design"

#: The page carrying the roster. Not the site root: the root's own model links include
#: the withdrawn 780.
MODEL_RANGE_PATH = "model-range"

#: Bessacarr publish no count of their own, so this is the only thing that would notice a
#: card being lost from `/model-range` — the failure that looks exactly like a
#: discontinuation. The 780 is deliberately **not** in it; see the module docstring.
EXPECTED_LAYOUTS = 4

#: There is one range, so `--range` has a single value. Present for the CLI's sake and to
#: keep the `Adapter` protocol's shape.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = ((MANUFACTURER_RANGE, MANUFACTURER_RANGE),)

_SCRIPTS = re.compile(r"<(script|style)\b.*?</\1>", re.DOTALL | re.IGNORECASE)
_MARKUP = re.compile(r"<[^>]+>")

#: One card on `/model-range`, e.g. `835 4 berth 2250kg MTPLM`. **The `kg` is optional**:
#: the 835 and 845 cards omit it where the 850 and 860 carry it, which is the site's usual
#: standard of consistency and would silently halve the roster if required.
#:
#: The MTPLM is captured rather than skipped because it is the cross-document half of the
#: self-check — this page and the model page are written separately and must agree.
_MODEL_CARD = re.compile(
    r"\b(\d{3})\s+(\d+)\s*berth\s+(\d{3,4})\s*(?:kg)?\s*MTPLM", re.IGNORECASE
)

#: The per-model header, e.g. `Bessacarr By Design 835 £54995.00`. Anchored on the range
#: name so a price elsewhere on the page cannot be picked up, and the pence are discarded.
_HEADER_PRICE = re.compile(
    rf"{re.escape(MANUFACTURER_RANGE)}\s+(\d{{3}})\s*£\s*([\d,]+)(?:\.\d{{2}})?",
    re.IGNORECASE,
)

#: The header badge's own MTPLM, e.g. `2250kg MTPLM`, which is a *third* statement of the
#: figure on top of the card and the spec table. Read only to be narrated when it
#: disagrees — it is the 780's `1800kg` against a table saying 1900.
_BADGE_MTPLM = re.compile(r"(\d{3,4})\s*kg\s+MTPLM", re.IGNORECASE)

#: The spec table, from its first row to the footnotes. Scoped rather than searched
#: page-wide so the navigation's `780 (4 Berth)` entries cannot reach the berth pattern:
#: the nav writes `Berth` singular and the table writes `Berths`, which is too thin a
#: distinction to rely on alone.
_SPEC_BLOCK = re.compile(r"\bBerths\b.*?(?=\*\s*Estimated weights|$)", re.DOTALL)


def _flatten(page_html: str) -> str:
    """The page as one line of text, tags and entities resolved.

    The spec table's labels are split across several elements — `Internal Length` and
    `(at bed box height)` are separate — so nothing here can rely on a row being a line.
    Flattening and matching on the printed label is what survives that.
    """
    text = _MARKUP.sub(" ", _SCRIPTS.sub(" ", page_html))
    return re.sub(r"\s+", " ", html_module.unescape(text)).strip()


def _labelled(block: str, label: str, unit: str) -> str | None:
    """The first figure printed after `label`, in `unit`.

    `[^0-9]*?` skips the parenthetical half of a two-part label — `(at bed box height)`,
    `(inc. TV Aerial)#`, `(inc. tolerance)`, `(MTPLM)` — none of which carries a digit.
    A label whose parenthetical ever gains one would stop matching rather than capture the
    wrong number, which is the right way round.
    """
    match = re.search(rf"{label}[^0-9]*?([\d.]+)\s*{unit}", block, re.IGNORECASE)
    return match.group(1) if match else None


def _metres_to_mm(value: str | None) -> int | None:
    """`5.95` to `5950`. Bessacarr publish metres and FMLV holds millimetres."""
    if value is None:
        return None
    try:
        return round(float(value) * 1000)
    except ValueError:
        return None


def _int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


@dataclass(frozen=True)
class BessacarrCaravan:
    """One model, as read from its own page's spec table."""

    model: str
    berths: int | None = None
    rrp_pounds: int | None = None
    mtplm_kilograms: int | None = None
    mro_kilograms: int | None = None
    #: `Total User Payload` — the figure that reconciles, and the one emitted. See the
    #: module docstring for why the row labelled `Personal Effects Payload` is not it.
    total_payload_kilograms: int | None = None
    #: `Personal Effects Payload` as printed, kept only so a disagreement with the total
    #: can be narrated with both numbers in it.
    stated_personal_effects_kilograms: int | None = None
    internal_length_mm: int | None = None
    shipping_length_mm: int | None = None
    awning_length_mm: int | None = None
    overall_width_mm: int | None = None
    height_mm: int | None = None
    headroom_mm: int | None = None
    twin_axle: bool = False
    #: The printed `Numbers of Axles`, quoted beside `twin_axle` so a reviewer sees the
    #: evidence rather than a bare Yes.
    axle_evidence: str | None = None
    #: What the `/model-range` card said, for the cross-document check.
    card_mtplm_kilograms: int | None = None
    #: What the page's own header badge said — a third statement, narrated when it differs.
    badge_mtplm_kilograms: int | None = None

    @property
    def label(self) -> str:
        return f"{MANUFACTURER_RANGE} {self.model}"

    @property
    def derived_payload_kilograms(self) -> int | None:
        """`MTPLM - MRO`, which the published total is checked against."""
        if self.mtplm_kilograms is None or self.mro_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mro_kilograms


def model_range_roster(page_html: str) -> list[tuple[str, int]]:
    """Every model `/model-range` publishes a card for, with the MTPLM that card states.

    **Not the navigation links**, which include the withdrawn 780 — see the module
    docstring. First-seen order, de-duplicated.
    """
    roster: list[tuple[str, int]] = []
    seen: set[str] = set()
    for model, _berths, mtplm in _MODEL_CARD.findall(_flatten(page_html)):
        if model not in seen:
            seen.add(model)
            roster.append((model, int(mtplm)))
    return roster


def parse_model_page(
    page_html: str, model: str, *, card_mtplm: int | None = None
) -> BessacarrCaravan | None:
    """One model's spec table, or `None` where the page carries no table at all.

    `None` means the page's shape has changed — a site rebuild is what would break this
    adapter first — and `collect` narrates it rather than reporting an empty range.
    """
    text = _flatten(page_html)
    found = _SPEC_BLOCK.search(text)
    if found is None:
        return None
    block = found.group(0)

    axles = _labelled(block, r"Numbers?\s+of\s+Axles", "")
    price = next(
        (amount for card, amount in _HEADER_PRICE.findall(text) if card == model), None
    )
    badge = next(
        (int(value) for value in _BADGE_MTPLM.findall(text)),
        None,
    )

    return BessacarrCaravan(
        model=model,
        berths=_int(_labelled(block, r"Berths", "")),
        rrp_pounds=_int(price.replace(",", "")) if price else None,
        # The label is misspelt on the site — `Permissable` — so the pattern is loose
        # across the word rather than quoting it, and would survive them fixing it.
        mtplm_kilograms=_int(
            _labelled(block, r"Maximum Technical Permiss\w+ Laden Mass", "kg")
        ),
        mro_kilograms=_int(_labelled(block, r"Mass in Running Order", "kg")),
        total_payload_kilograms=_int(_labelled(block, r"Total User Payload", "kg")),
        stated_personal_effects_kilograms=_int(
            _labelled(block, r"Personal Effects Payload", "kg")
        ),
        # Four lengths and they are not interchangeable. `Overall Length` is the body
        # plus the towing hitch, which is FMLV's shipping length; the awning figure is a
        # rail measurement and routinely exceeds both.
        internal_length_mm=_metres_to_mm(_labelled(block, r"Internal Length", "m")),
        shipping_length_mm=_metres_to_mm(_labelled(block, r"Overall Length", "m")),
        awning_length_mm=_metres_to_mm(_labelled(block, r"Awning A/A Dimension", "m")),
        overall_width_mm=_metres_to_mm(_labelled(block, r"Overall Width", "m")),
        # Published only as "Overall Height (inc. TV Aerial)", which reads like the wrong
        # figure and is not: FMLV's 2610 and 2590 match it exactly on the Elegance Grande.
        height_mm=_metres_to_mm(_labelled(block, r"Overall Height", "m")),
        headroom_mm=_metres_to_mm(_labelled(block, r"Maximum Internal Headroom", "m")),
        twin_axle=axles == "2",
        axle_evidence=f"Numbers of Axles: {axles}" if axles else None,
        card_mtplm_kilograms=card_mtplm,
        badge_mtplm_kilograms=badge,
    )


def _reconciles(product: BessacarrCaravan) -> tuple[bool, str]:
    """Whether this model's published figures agree with each other and with the card.

    Two independent checks, both of which the withdrawn 780 fails — see the module
    docstring. A `False` here drops the product: a vehicle whose own page contradicts
    itself cannot be proposed, because nothing on the site says which figure is wrong.
    """
    missing = [
        name
        for name, value in (
            ("MTPLM", product.mtplm_kilograms),
            ("MRO", product.mro_kilograms),
            ("Total User Payload", product.total_payload_kilograms),
        )
        if value is None
    ]
    if missing:
        return False, f"no {', '.join(missing)} in the spec table"

    derived = product.derived_payload_kilograms
    if derived != product.total_payload_kilograms:
        return False, (
            f"MTPLM {product.mtplm_kilograms}kg - MRO {product.mro_kilograms}kg = "
            f"{derived}kg, but the page says Total User Payload "
            f"{product.total_payload_kilograms}kg"
        )

    if (
        product.card_mtplm_kilograms is not None
        and product.card_mtplm_kilograms != product.mtplm_kilograms
    ):
        return False, (
            f"the model range page's card says MTPLM {product.card_mtplm_kilograms}kg "
            f"where this page's spec table says {product.mtplm_kilograms}kg"
        )

    return True, (
        f"MTPLM {product.mtplm_kilograms}kg - MRO {product.mro_kilograms}kg = "
        f"{derived}kg, matching the published Total User Payload"
    )


def _discrepancies(product: BessacarrCaravan) -> list[str]:
    """Published figures that disagree without being fatal — narrated, never silent.

    Both of these are live on the current site rather than defensive: the 850 prints the
    845's personal-effects figure, and the 780's header badge contradicts its own table.
    """
    notes: list[str] = []

    stated = product.stated_personal_effects_kilograms
    if stated is not None and stated != product.total_payload_kilograms:
        notes.append(
            f"the page prints Personal Effects Payload {stated}kg against a Total User "
            f"Payload of {product.total_payload_kilograms}kg"
            + (
                " — higher than the whole payload, so it is not a subdivision of it"
                if product.total_payload_kilograms is not None
                and stated > product.total_payload_kilograms
                else ""
            )
            + f"; recording the total, which reconciles against the masses"
        )

    badge = product.badge_mtplm_kilograms
    if badge is not None and badge != product.mtplm_kilograms:
        notes.append(
            f"the page's header badge says {badge}kg MTPLM where its own spec table says "
            f"{product.mtplm_kilograms}kg"
        )

    return notes


#: How each habitation reading is introduced. The wording says what these lists actually
#: are — Couplands' added kit — rather than implying a standard-equipment list, because
#: the base caravan's equipment is published nowhere on this site.
_FEATURE_NOTES: dict[str, str] = {
    "heating": "the heating named in the Exclusive Bessacarr Features list",
    "refrigeration": "the refrigeration named in the Exclusive Bessacarr Features list",
    "microwave": "a microwave named in the Exclusive Bessacarr Features list",
    "shower_toilet_separated": "the washroom as the page describes it",
}


def build_extracted(
    product: BessacarrCaravan,
    source_url: str,
    *,
    payload_basis: str | None = None,
    equipment: tuple[str, ...] = (),
) -> ExtractedCaravan:
    """One parsed model as a `Caravan` plus the provenance a reviewer sees beside it."""
    features = habitation.features_from(equipment)
    # Dropped for the same reason as on both halves of Swift: the `Bed Sizes` block names
    # positions without saying whether a bed is built in or made up from the seating,
    # which is exactly the distinction `BedType` exists to carry.
    features.pop("bed_types", None)

    caravan = Caravan(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=MANUFACTURER_RANGE,
        model=product.model,
        berths=product.berths,
        rrp_pounds=product.rrp_pounds,
        mtplm_kilograms=product.mtplm_kilograms,
        mro_kilograms=product.mro_kilograms,
        personal_effects_payload_kilograms=product.total_payload_kilograms,
        internal_length_mm=product.internal_length_mm,
        shipping_length_mm=product.shipping_length_mm,
        awning_length_mm=product.awning_length_mm,
        overall_width_mm=product.overall_width_mm,
        height_mm=product.height_mm,
        headroom_mm=product.headroom_mm,
        twin_axle=product.twin_axle,
        body_type=CaravanBodyType.RIGID,
        # Habitation, reported as findings rather than proposed — the pipeline never
        # writes these.
        heating=features["heating"].value if "heating" in features else None,
        refrigeration=(
            features["refrigeration"].value if "refrigeration" in features else None
        ),
        shower_toilet_separated=(
            features["shower_toilet_separated"].value
            if "shower_toilet_separated" in features
            else None
        ),
        microwave=features["microwave"].value if "microwave" in features else None,
    )

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=source_url, snippet=f"{product.label} — {snippet}"
        )

    # Both halves of the identity, always. `compare_fields` walks only fields that have
    # provenance, so a `model` read but left unrecorded is neither compared nor reported —
    # and accepting a range change without its model corrupts the name.
    record(
        "manufacturer_range",
        f'range "{MANUFACTURER_RANGE}", as the page titles itself '
        f'"{product.label}" — accept with the model, they are one name',
    )
    record(
        "model",
        f'model "{product.model}" from the page title "{product.label}" '
        f"— accept with the range, they are one name",
    )

    if product.rrp_pounds is not None:
        record("rrp_pounds", f"£{product.rrp_pounds:,}")
    if product.berths is not None:
        record("berths", f"Berths: {product.berths}")
    if product.mtplm_kilograms is not None:
        record(
            "mtplm_kilograms",
            f"Maximum Technical Permissable Laden Mass (MTPLM): "
            f"{product.mtplm_kilograms}kg"
            + (
                f", and the model range page's card agrees"
                if product.card_mtplm_kilograms == product.mtplm_kilograms
                else ""
            ),
        )
    if product.mro_kilograms is not None:
        record(
            "mro_kilograms",
            f"Mass in Running Order (inc. tolerance): {product.mro_kilograms}kg",
        )
    if product.total_payload_kilograms is not None:
        record(
            "personal_effects_payload_kilograms",
            f"Total User Payload: {product.total_payload_kilograms}kg"
            + (f"; {payload_basis}" if payload_basis else ""),
        )
        # Recorded with no value, which is the point: it says the adapter looked. FMLV
        # holds this blank on all four, so it comes back confirmed and no row appears.
        record(
            "optional_equipment_payload_kilograms",
            "Bessacarr publish one usable payload figure and no split, so there is no "
            "separate optional-equipment payload. Leave this blank so the two payload "
            f"columns sum to the published {product.total_payload_kilograms}kg",
        )
    if product.internal_length_mm is not None:
        record(
            "internal_length_mm",
            f"Internal Length (at bed box height): "
            f"{product.internal_length_mm / 1000:.2f}m — the habitable space, not the "
            f"overall figure",
        )
    if product.shipping_length_mm is not None:
        record(
            "shipping_length_mm",
            f"Overall Length: {product.shipping_length_mm / 1000:.2f}m — the body plus "
            f"the towing hitch",
        )
    if product.awning_length_mm is not None:
        record(
            "awning_length_mm",
            f"Awning A/A Dimension: {product.awning_length_mm / 1000:.2f}m — an awning "
            f"rail measurement, not a vehicle dimension",
        )
    if product.overall_width_mm is not None:
        record("overall_width_mm", f"Overall Width: {product.overall_width_mm / 1000:.2f}m")
    if product.height_mm is not None:
        record(
            "height_mm",
            f"Overall Height (inc. TV Aerial): {product.height_mm / 1000:.2f}m — the only "
            f"height Bessacarr publish, and the one FMLV already holds for these bodies",
        )
    if product.headroom_mm is not None:
        record(
            "headroom_mm",
            f"Maximum Internal Headroom: {product.headroom_mm / 1000:.2f}m",
        )

    # Always recorded, never conditional — a reviewer should see the evidence for an
    # axle count and the rule behind a body type, not infer either from a bare value.
    record("twin_axle", product.axle_evidence or "Numbers of Axles: not stated")
    record(
        "body_type",
        "A touring caravan is rigid unless its walls fold or rise — a lifting roof does "
        "not change the type, even where a manufacturer calls it a pop-up (NCC rule, "
        "7 September 2026). Bessacarr market no micro, and nothing here folds.",
    )

    for name, feature in features.items():
        note = feature.note or _FEATURE_NOTES.get(name, "read from the model page")
        record(name, f"{note}: {feature.snippet}")

    return ExtractedCaravan(caravan=caravan, provenance=provenance)


def collect(
    http: Fetcher,
    browser: object = None,  # noqa: ARG001
    snapshot_dir: Path | None = None,  # noqa: ARG001
    *,
    ranges: tuple[tuple[str, str], ...] | None = None,  # noqa: ARG001
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedCaravan]:
    """Fetch and parse every current Bessacarr By Design caravan.

    `browser` and `snapshot_dir` are unused — the pages are server-rendered and `http`
    snapshots every request itself — but stay in the signature because `cli.execute_run`
    passes them positionally to every adapter. `ranges` is accepted and ignored: there is
    one range, so there is nothing for `--range` to narrow.
    """
    roster_url = f"{BASE_URL}/{MODEL_RANGE_PATH}"
    on_progress(f"fetching the Bessacarr model range: {roster_url}")
    roster_html = http.fetch(roster_url).file_path.read_text(
        encoding="utf-8", errors="replace"
    )

    roster = model_range_roster(roster_html)
    if not roster:
        # The site's shape has changed. Said loudly rather than reported as an empty
        # range, which is what a discontinued brand would look like.
        on_progress(
            f"no model cards found on {roster_url} — the page's shape has changed, and "
            f"nothing can be collected until this adapter is updated"
        )
        return []

    on_progress(
        f"{len(roster)} model(s) published on the model range page: "
        + ", ".join(model for model, _mtplm in roster)
    )
    if len(roster) != EXPECTED_LAYOUTS:
        on_progress(
            f"expected {EXPECTED_LAYOUTS} models and the page publishes {len(roster)} — "
            f"Bessacarr publish no count of their own, so check this is a real range "
            f"change rather than a lost card"
        )

    extracted: list[ExtractedCaravan] = []
    for model, card_mtplm in roster:
        url = f"{BASE_URL}/bessacarr{model}"
        page_html = http.fetch(url).file_path.read_text(encoding="utf-8", errors="replace")

        product = parse_model_page(page_html, model, card_mtplm=card_mtplm)
        if product is None:
            on_progress(f"no specification table on {url} — skipping {model}")
            continue

        reconciles, reason = _reconciles(product)
        if not reconciles:
            on_progress(f"dropping {product.label} — {reason}")
            continue

        for note in _discrepancies(product):
            on_progress(f"{product.label}: {note}")

        equipment = tuple(habitation.list_items(page_html))
        if not equipment:
            on_progress(f"{product.label}: no feature list on {url} — no habitation findings")

        extracted.append(
            build_extracted(product, url, payload_basis=reason, equipment=equipment)
        )
        on_progress(f"read {product.label}")

    on_progress(f"collected {len(extracted)} Bessacarr caravan(s)")
    return extracted
