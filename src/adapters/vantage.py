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

**Every dimension is published, and published as pixels.** Each model page carries a
drawing giving the length, the height "inc. Hekis" and three widths — bare, "inc. mirrors
folded" and "inc. mirrors" — and not one of those numbers is in the HTML. So all three
fields are emitted as nothing, FMLV's own figures stand and arrive as a flagged no-op the
reviewer can confirm — the requester's instruction, 17 September 2026: *"we'll have to
have the option of using the current height and width if it's an existing vehicle"* — and
`dimensions_drawing` names the drawing per layout so a blank can be filled without
hunting.

**The drawings corroborate FMLV rather than contradicting it.** The CUB's gives 5413,
2600 and 2280 inc. mirrors folded; FMLV holds exactly those three, the 2280 included
rather than the bare 2050 or the 2480 with mirrors out — which is what the mirrors-folded
rule asks for. Leaving the stored figures alone was right, and is now evidenced.

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

## The two campervans are a different vehicle, and a different roof

Fuze and Luna are **not** panel vans and must not be given the panel vans' body type. They
are Ford Transit Customs at 4.97m x 2.08m x **2.15m**, against the panel vans' 2.6m — a
standard-roof van with a **pop-top**, so `campervan_elevating_roof` and neither
`campervan_high_top` nor `campervan_high_top_elevating_roof`. FMLV holds exactly that.

Both over-assertions were made and both were caught by diffing against the real baseline
before anything reached a reviewer: first the panel vans' high top, then the high-top
*variant* of the elevating roof. The lesson is the one
`docs/adapters/README.md` already draws for caravans — **fetch the baseline before writing
a rule about what a field means** — and it applies to a body type asserted from a
requester's sentence just as much as to one derived from a figure. "All definitely high
top camper vans" was true of the thirteen panel vans in front of us and not of the two
vehicles neither of us was looking at.

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

#: Thirteen panel vans — eleven Fiats and two Fords — plus the two campervans, Fuze and
#: Luna. Vantage publish no count of their own, so this is the only thing that would
#: notice an index page losing a card; it is what caught the mixed-case heading bug.
EXPECTED_LAYOUTS = 15

#: The campervan section. Two vehicles, and they are **not** panel vans — see
#: `read_campervans`.
CAMPERVANS_PATH = "campervans"

#: `(modal key, range, model)` for the two campervans, spelt as FMLV holds them: range
#: `Fuze`, model `Conversion`. The page heads each modal "Fuze Conversion", so the split
#: is corroborated, but it is a constant because a modal key is not a product name.
_CAMPERVAN_MODELS: tuple[tuple[str, str, str], ...] = (
    ("fuze_modal", "Fuze", "Conversion"),
    ("luna_modal", "Luna", "Conversion"),
)

#: The campervans' own prose, which is where their roof is stated: "a pop-top double bed
#: with ladder access". Distinct from `ELEVATING_ROOF_WORDS`, which reads an equipment
#: list — here the claim is about a **bed in the roof**, which is what makes it evidence
#: of a raisable roof rather than the CUB's "upgrade from a pop-top" marketing comparison.
_POP_TOP_BED = re.compile(r"pop[\s-]?top[^.]{0,40}\bbed\b", re.IGNORECASE)

#: `With a Ford Transit Custom base`. The campervan modals carry no
#: `Base Vehicle Specification` line — that is in the flipbook — so the make comes from
#: the sentence that names it.
_CAMPERVAN_BASE = re.compile(
    r"\b(Ford|Fiat|Peugeot|Citro[eë]n|Volkswagen|Renault|Mercedes)\b[^.]{0,40}\bbase\b",
    re.IGNORECASE,
)

#: How much of a campervan dialogue to read. Its description sits a few thousand
#: characters past the key; the next dialogue is far enough away not to be reached.
_MODAL_LENGTH = 14000

#: Where the dimensions drawing lives on a model page. Everything under the "Vehicle
#: Specification" heading, which is the block that carries the chassis logo, a photograph
#: and the drawing.
_SPEC_BLOCK_HEADING = "Vehicle Specification"
_SPEC_BLOCK_LENGTH = 6000

#: What the drawing is *not*: the chassis maker's logo, and any photograph. WordPress
#: stamps a resized image with its pixel size (`AVAST_CUB-1-1200x772.jpg`,
#: `IMG_6713-1-1067x800.jpg`), and the drawings are served at their natural size, so that
#: suffix separates them cleanly. Matching on the drawing's *name* does not work — they
#: are called `CUB-Measurements-.png`, `SOL-6.png` and `NEO-2.png`, with no pattern, and a
#: filename filter found three of thirteen and reported the other ten as having none.
_NOT_A_DRAWING = re.compile(r"logo|\d{3,4}x\d{3,4}", re.IGNORECASE)

_IMG_SRC = re.compile(r'<img[^>]+?src="([^"]+)"', re.IGNORECASE)

#: The two F-Lines' dimensions, in millimetres, as `(length, width, height)`.
#:
#: **Read by hand from `Sol-F-Line-Dimensions.png`** — the drawing both F-Line pages
#: carry — and supplied by the requester on 17 September 2026. Nothing here can read it:
#: see `dimensions_drawing` on why every Vantage dimension is pixels.
#:
#: **Why a constant here and emit-nothing everywhere else.** For the eleven Fiats the
#: blank is the right answer: FMLV already holds their figures, correctly, so emitting
#: nothing preserves them and the reviewer confirms a no-op. **A new product has no stored
#: value to preserve**, so for these two "leave it alone" would have meant blank forever —
#: the same reasoning as `swift._MANUALLY_SOURCED_HEIGHT_MM`, which exists for the nine
#: brand-new Merlins for exactly this reason.
#:
#: **The width is the mirrors-folded figure**, 2112mm, not the bare 2032mm and not the
#: 2474mm with mirrors out — `docs/adapters/README.md`'s rule, and the same choice FMLV
#: made for the eleven Fiats, where it holds 2280 against a bare 2050.
#:
#: **These are a Ford Transit L3 H2 and share nothing with the Fiats.** 5931 against 5998,
#: 2112 against 2280, 2650 against 2600. Copying the panel vans' figures across would have
#: been wrong on all three, which is why they were not guessed at.
#:
#: **Like every manually sourced constant this cannot refresh itself.** It is narrated on
#: every run, and `test_the_f_line_dimensions_are_still_not_published` is the canary that
#: says when Vantage start publishing them as text and this can go.
_MANUALLY_SOURCED_DIMENSIONS_MM: dict[str, tuple[int, int, int]] = {
    "ORA F-Line": (5931, 2112, 2650),
    "SOL F-Line": (5931, 2112, 2650),
}

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



def dimensions_drawing(page_html: str) -> str | None:
    """The URL of this model's dimensions drawing, or `None`.

    **Vantage publish every dimension, and publish them as pixels.** The drawing gives
    the length, the height "inc. Hekis", and three widths — bare, "inc. mirrors folded"
    and "inc. mirrors" — and not one of those numbers appears anywhere in the page's
    HTML. So nothing here can read them, and this returns the URL instead: a reviewer
    filling a blank dimension is pointed straight at the drawing rather than hunting for
    it.

    **The drawings corroborate FMLV rather than replacing it**, which is why not reading
    them costs nothing on an existing vehicle. The CUB's gives 5413, 2600 and 2280 (inc.
    mirrors folded), and FMLV holds exactly those three — including 2280 rather than the
    bare 2050 or the 2480 with mirrors out, which is what `docs/adapters/README.md`'s
    mirrors-folded rule asks for. It matters for a product FMLV does *not* hold, where
    the field arrives blank and someone has to type it.

    **One drawing serves a whole length.** `SOL-6.png` is on all four 5.99m pages and
    `NEO-2.png` on all four 6.36m ones, which is correct rather than careless — those
    models share a bodyshell, and it is the same reason the range is the length here. The
    two F-Lines share `Sol-F-Line-Dimensions.png` for the same reason; they are the Ford
    pair.
    """
    start = page_html.find(_SPEC_BLOCK_HEADING)
    if start < 0:
        return None
    block = page_html[start : start + _SPEC_BLOCK_LENGTH]
    for src in _IMG_SRC.findall(block):
        if _NOT_A_DRAWING.search(src.rsplit("/", 1)[-1]):
            continue
        # Absolute, because the point of returning it is that somebody opens it. The
        # site writes these as site-relative paths.
        return f"{BASE_URL}{src}" if src.startswith("/") else src
    return None


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

    dimensions = _MANUALLY_SOURCED_DIMENSIONS_MM.get(product.model)
    length_mm, width_mm, height_mm = dimensions if dimensions else (None, None, None)

    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.manufacturer_range,
        model=product.model,
        mh_length_mm=length_mm,
        mh_width_mm=width_mm,
        mh_height_mm=height_mm,
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

    if dimensions is not None:
        note = (
            "read by hand from the dimensions drawing both F-Line pages carry, and "
            "supplied by the requester on 17 September 2026 — Vantage publish it as an "
            "image, so nothing can re-read it. Re-verify at model-year changeover"
        )
        record("mh_length_mm", f"{length_mm}mm: {note}")
        record(
            "mh_width_mm",
            f"{width_mm}mm, the figure marked 'inc.mirrors folded' — not the bare 2032mm "
            f"and not the 2474mm with mirrors out: {note}",
        )
        record("mh_height_mm", f"{height_mm}mm: {note}")

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



@dataclass(frozen=True)
class VantageCampervan:
    """One of the two campervans, as much of it as the site publishes in HTML.

    Deliberately thin — see `read_campervans`. Everything this does not carry is left for
    FMLV's own figures, which are already right.
    """

    manufacturer_range: str
    model: str
    base_vehicle_manufacturer: str | None = None
    #: The sentence proving the roof rises, quoted for the reviewer.
    pop_top_evidence: str | None = None

    @property
    def label(self) -> str:
        return f"{self.manufacturer_range} {self.model}"


def read_campervans(page_html: str) -> list[VantageCampervan]:
    """The two campervans from `/campervans`, which links no model pages at all.

    **These are why a run must not report Fuze and Luna as discontinued.** They are real
    and current, but the section is built from modal dialogues rather than pages: a card
    carries `data-modal-target="fuze_modal"` and the dialogue itself repeats that key.
    There is no `/fuze` or `/luna` — both 404 — so without this they are reported as
    having left the range every run.

    **The full specification is unreachable, and that is stated rather than worked around.**
    The dialogue's "View Full Specifications" button opens a *Flipsnack* flipbook
    (`player.flipsnack.com/?hash=...`), a third-party viewer whose page is a 7.5 KB
    JavaScript shell carrying no text and no PDF; the book's pages are rendered images.
    The masses, payload and price live only there, so none is emitted and FMLV's own
    figures stand.

    **The dialogue is found by its key's last occurrence, not by the card's heading.** The
    card and the dialogue both name the vehicle, the card comes first, and the card carries
    none of the prose — scoping to it read 2,600 characters of thumbnail markup and found
    nothing.

    **The roof is emitted only where the page states it, which is Luna and not Fuze.**
    "pop-top" appears exactly once in the whole document, in Luna's description: *"In
    addition to a pop-top double bed with ladder access"*. Fuze's own pop-top is stated
    only inside the flipbook. So Luna carries a body type and Fuze carries none — FMLV
    holds both as `campervan_high_top_elevating_roof` already, and emitting nothing
    preserves that, where asserting the panel vans' fixed high top would have been a real
    error on a live vehicle.
    """
    found: list[VantageCampervan] = []
    for key, manufacturer_range, model in _CAMPERVAN_MODELS:
        occurrences = [match.start() for match in re.finditer(re.escape(key), page_html)]
        if not occurrences:
            continue
        block = _flatten(page_html[occurrences[-1] : occurrences[-1] + _MODAL_LENGTH])
        roof = _POP_TOP_BED.search(block)
        base = _CAMPERVAN_BASE.search(block)
        found.append(
            VantageCampervan(
                manufacturer_range=manufacturer_range,
                model=model,
                base_vehicle_manufacturer=(
                    fmlv_base_vehicle(base.group(1)) if base else None
                ),
                pop_top_evidence=(
                    block[max(0, roof.start() - 40) : roof.end() + 40].replace("|", " ").strip()
                    if roof
                    else None
                ),
            )
        )
    return found


def build_extracted_campervan(product: VantageCampervan, source_url: str) -> ExtractedMotorhome:
    """One campervan as a `Motorhome`, carrying only what the HTML actually states."""
    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.manufacturer_range,
        model=product.model,
        base_vehicle_manufacturer=product.base_vehicle_manufacturer,
        # Only where the page says so — see `read_campervans`. `None` leaves FMLV's own
        # value alone, which is already right for both.
        #
        # **Elevating roof, not the high-top variant of it.** The two campervans are Ford
        # Transit Customs at 2.15m overall — a standard-roof van with a pop-top, well
        # under the ~2300mm `docs/adapters/README.md` sets for a high top, and nothing
        # like the 2.6m panel vans. FMLV holds `campervan_elevating_roof` and is right;
        # an earlier version of this proposed the high-top value and the baseline caught
        # it, which is the second time on this adapter.
        body_type=(
            BodyType.CAMPERVAN_ELEVATING_ROOF if product.pop_top_evidence else None
        ),
    )

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=source_url, snippet=f"{product.label} — {snippet}"
        )

    record(
        "manufacturer_range",
        f'range "{product.manufacturer_range}" from the campervan section, which heads '
        f'this vehicle "{product.label}" — accept with the model, they are one name',
    )
    record(
        "model",
        f'model "{product.model}" — accept with the range, they are one name',
    )
    if product.base_vehicle_manufacturer is not None:
        record(
            "base_vehicle_manufacturer",
            f"{product.base_vehicle_manufacturer}, from the campervan's own description "
            f"of its base vehicle",
        )
    if product.pop_top_evidence:
        record(
            "body_type",
            f"Campervan with an elevating roof — not the fixed high top the panel vans "
            f"get, and not the high-top-plus-elevating-roof variant either: this is a "
            f"standard-roof Transit Custom at 2.15m with a pop-top. Its own description "
            f"says so: {product.pop_top_evidence!r}",
        )

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

            if product.model in _MANUALLY_SOURCED_DIMENSIONS_MM:
                length_mm, width_mm, height_mm = _MANUALLY_SOURCED_DIMENSIONS_MM[
                    product.model
                ]
                on_progress(
                    f"{product.label}: proposing {length_mm}x{width_mm}x{height_mm}mm from "
                    f"a hand-read constant — this model is new to FMLV, so there is no "
                    f"stored figure to preserve and a blank would be permanent. The width "
                    f"is the mirrors-folded one. This CANNOT refresh itself; re-verify it "
                    f"at model-year changeover."
                )
            elif drawing := dimensions_drawing(page_html):
                on_progress(
                    f"{product.label}: length, height and width are published only as a "
                    f"drawing, so none is proposed — read them from {drawing} if a figure "
                    f"needs filling in. It gives three widths; take the one marked "
                    f"'inc. mirrors folded'."
                )
            elif dimensions_drawing(page_html) is None:
                on_progress(
                    f"{product.label}: no dimensions drawing on the page, so there is "
                    f"nowhere on the site to read its length, height or width from"
                )

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

    # The two campervans, which live in modal dialogues rather than on pages of their own.
    # Skipped on a `--range` run, which narrows to one length index and means panel vans.
    if tuple(ranges) == DEFAULT_RANGES:
        campervans_url = f"{BASE_URL}/{CAMPERVANS_PATH}"
        on_progress(f"fetching the campervan section: {campervans_url}")
        campervans_html = http.fetch(campervans_url).file_path.read_text(
            encoding="utf-8", errors="replace"
        )
        campervans = read_campervans(campervans_html)
        if not campervans:
            on_progress(
                f"no campervans found on {campervans_url} — Fuze and Luna will be reported "
                f"as disappeared, so check whether they have really been withdrawn"
            )
        for campervan in campervans:
            if campervan.pop_top_evidence is None:
                # Not a reason to drop it — dropping it is what reports a live vehicle as
                # discontinued. The body type simply goes unproposed and FMLV's stands.
                on_progress(
                    f"{campervan.label}: its roof is stated only inside the flipbook, so "
                    f"no body type is proposed and FMLV's own value stands"
                )
            extracted.append(build_extracted_campervan(campervan, campervans_url))
            on_progress(
                f"read {campervan.label}: {campervan.base_vehicle_manufacturer or 'base '
                'vehicle not stated'}. Its masses, payload and price are published only "
                f"inside a Flipsnack flipbook, which carries no readable text, so FMLV's "
                f"own figures stand."
            )

    # Length, width and height are published nowhere — said once rather than per layout,
    # because it is the same sentence thirteen times.
    on_progress(
        "no length, width or height is published as text on any model page — every one is "
        "in a drawing, as pixels, and the only figure in the HTML is the rounded range "
        "name (5.41m against FMLV's 5413mm). So all three are left alone, FMLV's figures "
        "stand, and each layout above names the drawing to read them from."
    )
    if len(extracted) != EXPECTED_LAYOUTS:
        on_progress(
            f"expected {EXPECTED_LAYOUTS} models and collected {len(extracted)} — Vantage "
            f"publish no count of their own, so check this is a real range change"
        )
    on_progress(f"collected {len(extracted)} Vantage van conversion(s)")
    return extracted
