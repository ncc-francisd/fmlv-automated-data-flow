"""Vantage Motorhomes' van conversions, from `vantagemotorhomes.co.uk`.

Surveyed and built 17 September 2026. See `docs/adapters/vantage.md`. FMLV manufacturer
id **88**, name and display name **`Vantage`**, NCC supplier name **`Vantage
Motorhomes`**. **Campervans only** — Vantage convert panel vans at their own factory in
Leeds. **Thirteen models across three ranges.**

## The range is the vehicle's length

**Identity is inverted from every other brand in this project.** The `manufacturer_range`
is how long the van is and the `model` is its name:

    manufacturer_range = "5.41m"      model = "CUB"
    manufacturer_range = "5.99m"      model = "ORA F-Line"

The requester put it plainly on 17 September 2026 — *"the range is 5.41 metres which seems
confusing and then the model is the cub or the gem or the med or the max or the aura or
the soul or the teo"* — and FMLV's own export holds exactly that, so nothing here is
inferred. Every model page states both in its heading: `CUB | 5.41m (17'9")`.

`_identity` therefore reads the range **from the page**, and the index that led there is
used only to check it. The two are written independently and a model moving between the
length pages is the shape of error that would otherwise pass unseen.

## The site sells other people's vehicles, and its own used stock

The requester flagged this before the survey began, and it is the single easiest way to
get this adapter badly wrong. Alongside the thirteen models the site carries:

* **`/pilote`, `/pilote-atlas`, `/pilote-pacific`, `/pilote-panel-vans`, `/galaxy`** —
  Pilote products. Pilote are separate FMLV manufacturers (ids 104, 105, 261) with their
  own adapters, so reading these would propose one manufacturer's vehicles against
  another's `product_id`s;
* **`/motorhome-stock` and `/vantage-r`** — used and ex-demo stock. `/vantage-r` reads
  *"Stock Bonus Of £5000 Off This Stock Model, IMMEDIATE DELIVERY"* against individual
  2025 vehicles, each with a used price.

**Nothing here starts from the site root or from `/vantage-range`.** The roster is taken
from the three length index pages only, and every candidate then has to *parse as a
Vantage model page* — carrying both a `NAME | x.xxm` heading and a `Base Vehicle
Specification` line — before it is collected. A stock listing has neither, so the page
itself is the filter rather than a list of paths to avoid. `_KNOWN_NON_MODELS` exists only
to keep the narration quiet about the site's own navigation.

## Model pages are at the site root, and linked absolutely

`/cub`, `/ora-f-line`, `/vue` — **not** under `/panel-vans/` or the index path, and the
hrefs are written in full (`https://www.vantagemotorhomes.co.uk/cub`). A pattern looking
for relative or nested paths finds nothing at all, which is how this nearly read as a site
with no models on it.

## The base vehicle splits the range, and not where the menu says

Eleven models are **Fiat Ducato 2.2 Multijet3 140bhp** and the two **F-Line** models are
**Ford Transit V363 350 L3 H2**. The requester's framing was "the campervans are Fords,
the panel vans are Fiats" — true of the vehicles, and **not** of the site's own menu:
*both F-Lines are linked from the 5.99m panel van index*, and `/campervans` links no model
pages at all.

So the make is read from each page's own `Base Vehicle Specification` line and never from
which index led there. Deriving it from the section would put Fiat on two Fords.

## The self-check, and its limit

**Said plainly because it is thinner than most:** Vantage publish two masses and the third
is derived, so `payload == GVW - MRO` would be true by construction and is not a check.
Gross Vehicle Weight is **3500 kg on all thirteen**, so it cannot discriminate either.

What is real is a **cross-check on identity**: the length index page states the range and
the model page states its own, independently, and `_reconciles` drops a layout where the
two disagree. Everything else rests on the roster count and on the fact that a page which
does not parse is dropped rather than guessed at.

**The derivation is corroborated once, which is worth recording.** `MRO = GVW - payload`
reproduces FMLV's stored mass in running order *exactly* on all eleven existing models —
3500-600=2900, 3500-500=3000, 3500-450=3050, 3500-400=3100, 3500-380=3120. That is a
one-time agreement rather than a running check, but it is the reason the derivation is
trusted at all.

## Length, width and height are not emitted

**The site rounds and FMLV does not.** The only length published is the range name itself,
`5.41m`, while FMLV holds **5413**; the 5.99m models are 5998 and the 6.36m are 6363.
Emitting 5410 would degrade eleven good figures to make a blank go away, which
`docs/adapters/README.md` forbids — a figure that cannot be found is left alone.

**No width or height is published anywhere on the site.** Both are emitted as nothing, so
FMLV's own figures stand and arrive as a flagged no-op the reviewer can confirm — the
requester's instruction, 17 September 2026: *"we'll have to have the option of using the
current height and width if it's an existing vehicle"*.

The consequence to know: the **two new F-Line models have no stored figure to preserve**,
so their length, width and height arrive blank and need filling by hand. That is narrated
per layout rather than left to be discovered in the review.

## Body type is asserted, because nothing published could derive it

All thirteen are **`campervan_high_top`** — the requester, 17 September 2026: *"all
definitely high top camper vans"*. It is asserted rather than derived because the
campervan roof rule in `docs/adapters/README.md` works off a published height and Vantage
publish none. FMLV already holds `type_campervan_high_top` on all eleven existing models,
so this agrees with the baseline rather than proposing against it, and the two new F-Lines
get a body type instead of a blank — the gap `swift.py` had to go back and fill.

No elevating roof appears in any model's equipment list; `ELEVATING_ROOF_WORDS` checks for
one per layout and narrates a hit rather than silently keeping the assertion, so the day
Vantage add a pop-top it is a warning and not a wrong answer.

## The price is on the page, and so are the options that must not be read

Every model page carries `FROM £74,995 (OTR)` — sterling, on-the-road, the manufacturer's
own headline figure, which is exactly what `docs/adapters/README.md` asks for.

**The trap is further down the same page.** A "Vehicle Quotation Calculator" lists
`8 Speed Automatic Transmission £2520`, `Primo Pack £4200`, `CAT 1 Alarm £525` and a dozen
more. Those are options, and the first `£` on the page is not necessarily the price — so
the pattern requires the `FROM` and the `(OTR)` around it, and a page carrying option
prices but no OTR line yields no price at all rather than a £525 campervan.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from html import unescape
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from ..vehicle_class import VehicleClass
from . import habitation
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

__all__ = [
    "BASE_URL",
    "DEFAULT_RANGES",
    "EXPECTED_LAYOUTS",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "VEHICLE_CLASS",
    "VantageProduct",
    "collect",
]

BASE_URL = "https://www.vantagemotorhomes.co.uk"

MANUFACTURER = "Vantage"
MANUFACTURER_DISPLAY_NAME = "Vantage"

#: Campervans live in the motorhome product area — see `vehicle_class`.
VEHICLE_CLASS = VehicleClass.MOTORHOME

#: (index path, label) per length. The label is the range FMLV holds, and it is what a
#: `--range` run picks; the authoritative range still comes from each model page, with
#: this used to check it.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (
    ("5-41m-panel-vans", "5.41m"),
    ("5-99m-panel-vans", "5.99m"),
    ("6-36m-panel-vans", "6.36m"),
)

#: Eleven Fiats and two Fords. Vantage publish no count of their own, so this is the only
#: thing that would notice an index page losing a card.
EXPECTED_LAYOUTS = 13

_SCRIPTS = re.compile(r"<(script|style)\b.*?</\1>", re.DOTALL | re.IGNORECASE)
_MARKUP = re.compile(r"<[^>]+>")

#: A model page link. **Absolute**, and at the site root — see the module docstring.
_MODEL_HREF = re.compile(re.escape(BASE_URL) + r"/([a-z0-9][a-z0-9-]{1,40})/?(?=[\"#?])")

#: The site's own navigation, plus Pilote and the stock pages. Not a safety mechanism —
#: `parse_model_page` returning `None` is what actually keeps a non-model out — but
#: without it every run would narrate thirty "this is not a model page" lines.
_KNOWN_NON_MODELS = frozenset(
    {
        "2026-vantage", "about-us", "advice-hub", "book-your-tour", "brochures",
        "campervans", "contact-us", "cookie-policy", "customer-hub", "events",
        "galaxy", "gallery", "handover-day", "insurance", "motorhome-stock",
        "panel-vans", "part-exchange", "pilote", "pilote-atlas", "pilote-pacific",
        "pilote-panel-vans", "privacy-policy", "ten-motorhoming-tips",
        "terms-conditions", "vantage-news", "vantage-r", "vantage-range",
        "virtual-tours", "what-our-customers-say",
        "5-41m-panel-vans", "5-99m-panel-vans", "6-36m-panel-vans",
    }
)

#: A model page's heading: `CUB | 5.41m (17'9")`.
#:
#: **The name is not all upper-case**, which cost the two F-Lines their first run: eleven
#: pages head themselves `CUB` or `VUE`, and the other two head themselves `ORA F Line`
#: and `SOL F Line`. An upper-case-only class silently collected 11 of 13 and reported the
#: pair as "not a Vantage model page" — the exact shape of a silent drop, caught only
#: because `EXPECTED_LAYOUTS` disagreed.
#:
#: Widening the name is safe because the metre figure is what anchors this, not the name.
_HEADING = re.compile(r"\|\s*([A-Z][A-Za-z0-9 \-]{1,20}?)\s*\|\s*(\d\.\d{1,2}m)\s*\(")

#: `| 2 | Berth` and `| 4 | Travel Seats`.
_BERTHS = re.compile(r"\|\s*(\d+)\s*\|\s*Berths?\b", re.IGNORECASE)
_TRAVEL_SEATS = re.compile(r"\|\s*(\d+)\s*\|\s*Travel Seats?\b", re.IGNORECASE)

#: `Base Vehicle Specification | Fiat Ducato 2.2 Multijet3 140bhp Manual`. Only the make
#: is recorded — `docs/adapters/README.md` wants one name per company, not the trim.
_BASE_VEHICLE = re.compile(
    r"Base Vehicle Specification\s*\|\s*([A-Z][A-Za-z\-]+)\b([^|]{0,70})", re.IGNORECASE
)

#: `Gross Vehicle Weight | – 3500Kg` and `Maximum Payload | – 600Kg`. The dash is an en
#: dash on the live pages and a hyphen is accepted too.
_GVW = re.compile(r"Gross Vehicle Weight\s*\|\s*[–—-]?\s*(\d{3,5})\s*Kg", re.IGNORECASE)
_PAYLOAD = re.compile(r"Maximum Payload\s*\|\s*[–—-]?\s*(\d{2,4})\s*Kg", re.IGNORECASE)

#: `FROM | £74,995 (OTR)`. **Both halves are required** — see the module docstring on the
#: quotation calculator's option prices, any of which the first bare `£` might be.
_PRICE = re.compile(r"FROM\s*\|?\s*£\s*([\d,]+)\s*\|?\s*\(\s*OTR", re.IGNORECASE)

#: What a pop-top would be called if Vantage ever fit one. Checked per layout so the
#: asserted high top becomes a narrated warning rather than a wrong answer.
#:
#: **Matched against the equipment list only, never the page's prose.** The CUB's copy
#: sells it as "the ideal upgrade from a pop-top", which is a sentence about a *different*
#: kind of van, and scanning the whole page turned that into a body-type warning on every
#: run — a false alarm that would train a reviewer to ignore the real one.
ELEVATING_ROOF_WORDS = re.compile(r"elevating roof|pop[\s-]?top|rising roof", re.IGNORECASE)


def elevating_roof_in(equipment: tuple[str, ...]) -> str | None:
    """The equipment line offering a raisable roof, or `None` — see `ELEVATING_ROOF_WORDS`."""
    return next((line for line in equipment if ELEVATING_ROOF_WORDS.search(line)), None)

#: `ORA F Line` in the page heading, `ORA F-Line` in its title and its own prose. The
#: hyphenated form is the one proposed, because these two are new products and the name
#: this adapter writes becomes the name FMLV holds.
_F_LINE = re.compile(r"\bF\s+Line\b", re.IGNORECASE)


def _flatten(page_html: str) -> str:
    """The page as one line, tags becoming `|` so a label and its value stay separable."""
    text = _MARKUP.sub("|", _SCRIPTS.sub(" ", page_html))
    return re.sub(r"(\|\s*)+", "|", re.sub(r"\s+", " ", unescape(text)))


def _int(value: str | None) -> int | None:
    if value is None:
        return None
    cleaned = value.replace(",", "").strip()
    return int(cleaned) if cleaned.isdigit() else None


@dataclass(frozen=True)
class VantageProduct:
    """One van conversion, as read from its own page."""

    slug: str
    manufacturer_range: str
    model: str
    index_range: str | None = None
    berths: int | None = None
    travel_seats: int | None = None
    base_vehicle_manufacturer: str | None = None
    #: The whole `Base Vehicle Specification` line, quoted to the reviewer — the make
    #: alone is recorded but the trim is the evidence for it.
    base_vehicle_evidence: str | None = None
    mtplm_kilograms: int | None = None
    payload_kilograms: int | None = None
    rrp_pounds: int | None = None

    @property
    def label(self) -> str:
        return f"{self.manufacturer_range} {self.model}"

    @property
    def mro_kilograms(self) -> int | None:
        """`GVW - payload`. Vantage publish no mass in running order — see the docstring."""
        if self.mtplm_kilograms is None or self.payload_kilograms is None:
            return None
        return self.mtplm_kilograms - self.payload_kilograms


def find_model_slugs(index_html: str) -> list[str]:
    """Candidate model pages linked from one length index, first-seen order.

    Candidates, not models: the site's navigation is on every page, so this is filtered
    by `_KNOWN_NON_MODELS` for quiet and then by whether each page actually parses.
    """
    seen: list[str] = []
    for match in _MODEL_HREF.finditer(_SCRIPTS.sub(" ", index_html)):
        slug = match.group(1)
        if slug not in _KNOWN_NON_MODELS and slug not in seen:
            seen.append(slug)
    return seen


def parse_model_page(page_html: str, slug: str, *, index_range: str | None = None) -> VantageProduct | None:
    """One model page, or `None` where the page is not a Vantage model at all.

    `None` is the mechanism that keeps stock listings and Pilote pages out: both lack the
    `NAME | x.xxm` heading, and a page without one is not a vehicle this adapter knows how
    to read. See the module docstring.
    """
    text = _flatten(page_html)
    heading = _HEADING.search(text)
    if heading is None:
        return None

    model = _F_LINE.sub("F-Line", heading.group(1).strip())
    base = _BASE_VEHICLE.search(text)
    price = _PRICE.search(text)

    return VantageProduct(
        slug=slug,
        manufacturer_range=heading.group(2).strip(),
        model=model,
        index_range=index_range,
        berths=_int(_BERTHS.search(text).group(1) if _BERTHS.search(text) else None),
        travel_seats=_int(
            _TRAVEL_SEATS.search(text).group(1) if _TRAVEL_SEATS.search(text) else None
        ),
        # Routed through the shared helper rather than taken verbatim: the spelling
        # decides whether a run confirms this field or proposes a rename, and that
        # decision belongs in one place. `Fiat` and `Ford` pass through unchanged.
        base_vehicle_manufacturer=fmlv_base_vehicle(base.group(1)) if base else None,
        base_vehicle_evidence=(base.group(1) + base.group(2)).strip() if base else None,
        mtplm_kilograms=_int(_GVW.search(text).group(1) if _GVW.search(text) else None),
        payload_kilograms=_int(_PAYLOAD.search(text).group(1) if _PAYLOAD.search(text) else None),
        rrp_pounds=_int(price.group(1)) if price else None,
    )


def _reconciles(product: VantageProduct) -> tuple[bool, str]:
    """Whether the page holds together, and agrees with the index that led to it.

    The identity cross-check is the only genuinely independent one this source offers —
    see the module docstring on why the masses cannot provide one.
    """
    missing = [
        name
        for name, value in (
            ("a berth count", product.berths),
            ("a gross vehicle weight", product.mtplm_kilograms),
            ("a maximum payload", product.payload_kilograms),
        )
        if value is None
    ]
    if missing:
        return False, f"the page publishes no {', no '.join(missing)}"

    if product.payload_kilograms >= product.mtplm_kilograms:
        return False, (
            f"a payload of {product.payload_kilograms}kg against a gross vehicle weight "
            f"of {product.mtplm_kilograms}kg leaves no vehicle"
        )

    if product.index_range is not None and product.index_range != product.manufacturer_range:
        return False, (
            f"the {product.index_range} index links this page and the page calls itself "
            f"{product.manufacturer_range}"
        )

    return True, (
        f"gross vehicle weight {product.mtplm_kilograms}kg less a {product.payload_kilograms}kg "
        f"payload gives a mass in running order of {product.mro_kilograms}kg"
    )


def build_extracted(
    product: VantageProduct,
    source_url: str,
    *,
    basis: str,
    equipment: tuple[str, ...] = (),
) -> ExtractedMotorhome:
    """One parsed model as a `Motorhome` plus the provenance a reviewer sees beside it."""
    features = habitation.features_from(equipment)
    features.pop("bed_types", None)

    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.manufacturer_range,
        model=product.model,
        berths=product.berths,
        mh_passenger_seats_inc_driver=product.travel_seats,
        base_vehicle_manufacturer=product.base_vehicle_manufacturer,
        mtplm_kilograms=product.mtplm_kilograms,
        mro_kilograms=product.mro_kilograms,
        mh_payload_kilograms=product.payload_kilograms,
        rrp_pounds=product.rrp_pounds,
        body_type=BodyType.CAMPERVAN_HIGH_TOP,
        # Habitation, reported as findings rather than proposed.
        heating=features["heating"].value if "heating" in features else None,
        refrigeration=features["refrigeration"].value if "refrigeration" in features else None,
        microwave=features["microwave"].value if "microwave" in features else None,
    )

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=source_url, snippet=f"{product.label} — {snippet}"
        )

    # Both halves of the identity, always — and here the range is the unusual half, so it
    # says what it is rather than leaving a reviewer to wonder why it is a measurement.
    record(
        "manufacturer_range",
        f'range "{product.manufacturer_range}", which is the vehicle\'s length: Vantage '
        f'head this page "{product.model} | {product.manufacturer_range}" and FMLV files '
        f"the range the same way — accept with the model, they are one name",
    )
    record(
        "model",
        f'model "{product.model}" from the page heading — accept with the range, they are '
        f"one name",
    )

    if product.berths is not None:
        record("berths", f"{product.berths} Berth")
    if product.travel_seats is not None:
        record("mh_passenger_seats_inc_driver", f"{product.travel_seats} Travel Seats")
    if product.base_vehicle_manufacturer is not None:
        record(
            "base_vehicle_manufacturer",
            f"Base Vehicle Specification: {product.base_vehicle_evidence} — read from this "
            f"model's own page, not from the section it is listed under",
        )
    if product.mtplm_kilograms is not None:
        record("mtplm_kilograms", f"Gross Vehicle Weight – {product.mtplm_kilograms}Kg")
    if product.payload_kilograms is not None:
        record("mh_payload_kilograms", f"Maximum Payload – {product.payload_kilograms}Kg")
    if product.mro_kilograms is not None:
        record(
            "mro_kilograms",
            f"{product.mro_kilograms}kg, derived: {basis}. Vantage publish no mass in "
            f"running order, and note that the figures are 'weights with standard "
            f"equipment installed'",
        )
    if product.rrp_pounds is not None:
        record(
            "rrp_pounds",
            f"FROM £{product.rrp_pounds:,} (OTR) — the headline on-the-road price, not "
            f"one of the quotation calculator's option prices lower down the page",
        )

    record(
        "body_type",
        "Campervan, high top. Asserted rather than derived: the roof-class rule needs a "
        "published height and Vantage publish none, so the requester settled it on "
        "17 September 2026 — 'all definitely high top camper vans'. No elevating roof "
        "appears in this model's equipment.",
    )

    for name, feature in features.items():
        record(name, f"{feature.note or 'from the model page'}: {feature.snippet}")

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


def collect(
    http: Fetcher,
    browser: object = None,  # noqa: ARG001
    snapshot_dir: Path | None = None,  # noqa: ARG001
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Fetch and parse every current Vantage van conversion, or just the named ranges.

    `browser` and `snapshot_dir` are unused — the pages are server-rendered and `http`
    snapshots every request itself — but stay in the signature because `cli.execute_run`
    passes them positionally to every adapter.
    """
    extracted: list[ExtractedMotorhome] = []
    collected_slugs: set[str] = set()

    for path, label in ranges:
        index_url = f"{BASE_URL}/{path}"
        on_progress(f"fetching the {label} index: {index_url}")
        index_html = http.fetch(index_url).file_path.read_text(encoding="utf-8", errors="replace")

        slugs = [slug for slug in find_model_slugs(index_html) if slug not in collected_slugs]
        if not slugs:
            on_progress(f"no model pages linked from {index_url} — skipping {label}")
            continue

        for slug in slugs:
            url = f"{BASE_URL}/{slug}"
            page_html = http.fetch(url).file_path.read_text(encoding="utf-8", errors="replace")

            product = parse_model_page(page_html, slug, index_range=label)
            if product is None:
                # A stock listing, a Pilote page or something new in the navigation. The
                # page's own shape is what excludes it, so nothing has to be kept in step
                # with the site's menu.
                on_progress(f"{url} is not a Vantage model page — skipping")
                continue

            reconciles, reason = _reconciles(product)
            if not reconciles:
                on_progress(f"dropping {product.label} — {reason}")
                continue

            equipment = tuple(habitation.list_items(page_html))
            if roof_line := elevating_roof_in(equipment):
                on_progress(
                    f"{product.label}: the equipment lists {roof_line!r}, but this adapter "
                    f"asserts a fixed high top. Check the body type before accepting it."
                )
            if product.rrp_pounds is None:
                on_progress(
                    f"{product.label}: no 'FROM £x (OTR)' line on the page, so no price is "
                    f"proposed. FMLV's own figure stands."
                )

            extracted.append(
                build_extracted(product, url, basis=reason, equipment=equipment)
            )
            collected_slugs.add(slug)
            on_progress(
                f"read {product.label}: {product.base_vehicle_manufacturer}, "
                f"{product.berths} berths, {product.travel_seats} travel seats, "
                f"{product.mtplm_kilograms}kg, £{product.rrp_pounds or 0:,}"
            )

    # Length, width and height are published nowhere — said once rather than per layout,
    # because it is the same sentence thirteen times.
    on_progress(
        "no length, width or height is published on any model page: the only length is "
        "the rounded range name (5.41m against FMLV's 5413mm), so all three are left "
        "alone and FMLV's figures stand. A model new to FMLV arrives with all three blank."
    )
    if len(extracted) != EXPECTED_LAYOUTS:
        on_progress(
            f"expected {EXPECTED_LAYOUTS} models and collected {len(extracted)} — Vantage "
            f"publish no count of their own, so check this is a real range change"
        )
    on_progress(f"collected {len(extracted)} Vantage van conversion(s)")
    return extracted
