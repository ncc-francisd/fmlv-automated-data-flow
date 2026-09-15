"""Mobilvetta — eight UK layouts, read from the importer's own range pages.

`docs/adapters/mobilvetta.md` is the survey; this is what it decided.

Third of six Trigano brands. The requester expected a two-source build — Marquis Leisure
defining the UK range and `mobilvetta.it` defining the numbers — but **Marquis publish the
whole story**, specification and price included, so the Italian parent is never fetched.
That matters beyond this brand: if Marquis use the same template for Benimar, Elnagh and
McLouis, none of those needs a parent site either.

Four things drive the module:

* **A page is a range, not a product.** Each range page carries one `Weights and
  Dimensions` block per layout, so `layout_blocks` splits a page into several products —
  the first adapter here to do so. One page even carries two different ranges, so the
  range comes from each block's own heading and never from the page.
* **The roster excludes the 80s**, by the requester's ruling. See `EXCLUDED_PAGES`.
* **There is no arithmetic self-check.** Marquis publish MTPLM and payload but no mass in
  running order, so MRO is derived and the identity is true by construction. The roster
  count is the only structural check available. See `_reconciles`.
* **Only a figure followed by `OTR` is a price.** Three pages also carry a `£4,000` offer.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle, width_from_mirrors_folded

BASE_URL = "https://www.marquisleisure.co.uk"
MANUFACTURER = "Mobilvetta"
MANUFACTURER_DISPLAY_NAME = "Mobilvetta"

#: The importer's brand index, which links every current range page.
#:
#: **Not the Italian parent**, which lists seven ranges against the four Marquis sell, and
#: **not a stock listing** — the requester's warning was *"you have to avoid the used stock
#: for sale pages"*. `_RANGE_HREF` only admits `mobilvetta-…-range` slugs, so a stock page
#: cannot reach the roster.
INDEX_URL = f"{BASE_URL}/new-motorhomes/mobilvetta"

#: Range pages that are not the range.
#:
#: **The requester's ruling, 14 September 2026.** FMLV's current Mobilvetta range is
#: exactly eight vehicles and neither 80 is among them: *"They may well be sold as current
#: stock. But remember, we're not looking for current stock. We're looking at the range
#: lineup."* FMLV holds both 80s only as 2025 rows, which the baseline filter drops, so
#: collecting them would add two products to a range meant to have eight.
#:
#: Recorded honestly: this page does not look like a stock page. Its slug says
#: `2026-motorhome-range` and it carries the same blocks and OTR prices as its siblings.
#: If Marquis ever promote the 80s, delete the entry.
EXCLUDED_PAGES: frozenset[str] = frozenset(
    {"mobilvetta-k-yacht-80-and-kea-80-2026-motorhome-range"}
)

#: Block-heading prefix -> FMLV `manufacturer_range`, **longest first** so `KEA KOMPAKT`
#: is not read as `KEA`. The remainder of the heading becomes the model.
RANGE_PREFIXES: tuple[tuple[str, str], ...] = (
    ("KEA KOMPAKT", "KEA Kompakt"),
    ("K.YACHT", "K-YACHT TEKNO LINE"),
    ("KEA", "KEA"),
    ("ADMIRAL", "ADMIRAL"),
)

#: Body type by FMLV range. Every layout in a Mobilvetta range shares one, and these are
#: what FMLV already holds across its eight current rows.
_BODY_TYPES: dict[str, BodyType] = {
    "K-YACHT TEKNO LINE": BodyType.A_CLASS,
    "KEA": BodyType.COACH_BUILT_LOW_PROFILE,
    "KEA Kompakt": BodyType.COACH_BUILT_LOW_PROFILE,
    "ADMIRAL": BodyType.CAMPERVAN_HIGH_TOP,
}

#: Every layout is a Fiat Ducato conversion, stated on each block's engine line.
BASE_VEHICLE = "Fiat"

#: `(slug fragment, label)` for `--range`. Matching is on the page slug.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (
    ("admiral", "Admiral"),
    ("k-yacht", "K-Yacht Tekno Line"),
    ("kea", "KEA"),
    ("kea-kompakt", "KEA Kompakt"),
)

# --- Reading the roster ----------------------------------------------------------------

_RANGE_HREF = re.compile(
    rf'href="(?:{re.escape(BASE_URL)})?/(?P<slug>mobilvetta-[a-z0-9-]*-range)"', re.I
)

_TAGS = re.compile(r"(?is)<(script|style)\b.*?</\1>")


def plain_text(page: str) -> str:
    """The page as one line, tags replaced by a single space and entities resolved."""
    stripped = re.sub(r"<[^>]+>", " ", _TAGS.sub(" ", page))
    return re.sub(r"\s+", " ", html.unescape(html.unescape(stripped))).strip()


def find_range_urls(index_html: str, ranges: Iterable[str]) -> list[str]:
    """Every current range page the brand index links, minus the excluded ones."""
    wanted = [key.lower() for key in ranges]
    urls: list[str] = []
    for match in _RANGE_HREF.finditer(index_html):
        slug = match.group("slug").lower()
        if slug in EXCLUDED_PAGES:
            continue
        if not any(f"mobilvetta-{key}-" in slug for key in wanted):
            continue
        url = f"{BASE_URL}/{slug}"
        if url not in urls:
            urls.append(url)
    return urls


# --- Reading one layout ----------------------------------------------------------------

#: One layout's block: its heading, then everything up to the next heading.
#:
#: The heading is upper case and contains a digit — `K.YACHT 59`, `KEA KOMPAKT 55`,
#: `ADMIRAL K 6.3`. The block runs to the *next* heading rather than a fixed window,
#: because the price sits at its end: a first extraction using 700 characters lost two of
#: the four K-Yacht prices.
_BLOCK = re.compile(
    r"(?P<name>[A-Z][A-Z.\s]*\d[\w.\s]*?)\s+Weights and Dimensions\s+(?P<body>.*?)"
    r"(?=[A-Z][A-Z.\s]*\d[\w.\s]*?\s+Weights and Dimensions|$)",
    re.S,
)

#: **Only a price followed by `OTR`.** Three pages carry a `£4,000` offer as well, which is
#: a discount rather than a vehicle.
_PRICE = re.compile(r"£\s*(?P<price>[\d,]{5,})\s*OTR", re.I)

_FIELDS: dict[str, re.Pattern[str]] = {
    "berths": re.compile(r"\bBERTHS\s+(\d+)", re.I),
    # `BELTS` is the travel-seat count, named unambiguously — unlike Pilote, where the
    # word "Berth" meant a seat.
    "seats": re.compile(r"\bBELTS\s+(\d+)", re.I),
    "length": re.compile(r"OVERALL LENGTH\s+(\d+)\s*mm", re.I),
    "width": re.compile(r"OVERALL WIDTH \(MIRRORS FOLDED\)\s+(\d+)\s*mm", re.I),
    "height": re.compile(r"OVERALL HEIGHT \(EXC TV AERIAL\)\s+(\d+)\s*mm", re.I),
    "mtplm": re.compile(r"\bMTPLM\s+(\d+)\s*kg", re.I),
    "payload": re.compile(r"MAX USER PAYLOAD\s+(\d+)\s*kg", re.I),
}


def _field(body: str, key: str) -> int | None:
    match = _FIELDS[key].search(body)
    return int(match.group(1)) if match else None


def _range_and_model(heading: str) -> tuple[str, str] | None:
    """The FMLV range and model from a block heading, or `None` if it is not a layout.

    `K.YACHT 59` is range `K-YACHT TEKNO LINE` and model `59`; `KEA KOMPAKT 55` is
    `KEA Kompakt` / `55`; `ADMIRAL K 6.3` is `ADMIRAL` / `K 6.3`.

    The range comes from the heading and **never from the page**, because one Marquis page
    carries a K.YACHT and a KEA together.

    **The last occurrence of the prefix wins, not the first.** The first block on every
    page has the page's own banner welded to its front:

    | captured heading | model |
    |---|---|
    | `MOBILVETTA K.YACHT A CLASS MOTORHOME RANGE K.YACHT 59` | `59` |
    | `MOBILVETTA ADMIRAL ADMIRAL K 6.3` | `K 6.3` |
    | `MOBILVETTA KEA COACHBUILT MOTORHOME RANGE KEA 86` | `86` |
    | `K.YACHT 86` | `86` |

    Taking the first match instead gave models like `A CLASS MOTORHOME RANGE K.YACHT 59`,
    which still *matched* their FMLV rows on token overlap — so the run looked almost
    right, with one product orphaned and three carrying nonsense as their model.
    """
    name = re.sub(r"\s+", " ", heading).strip()
    for prefix, fmlv_range in RANGE_PREFIXES:
        matches = list(re.finditer(rf"\b{re.escape(prefix)}\s+(?=\S)", name, re.I))
        if not matches:
            continue
        model = re.sub(r"\s+", " ", name[matches[-1].end() :]).strip()
        if model:
            return fmlv_range, model
    return None


@dataclass(frozen=True)
class MobilvettaProduct:
    """One layout, from one block of an importer range page."""

    source_url: str
    manufacturer_range: str
    model: str
    mh_passenger_seats_inc_driver: int | None = None
    berths: int | None = None
    mh_length_mm: int | None = None
    mh_width_mm: int | None = None
    mh_height_mm: int | None = None
    mtplm_kilograms: int | None = None
    mh_payload_kilograms: int | None = None
    rrp_pounds: int | None = None

    @property
    def label(self) -> str:
        return f"{self.manufacturer_range} {self.model}"

    @property
    def mro_kilograms(self) -> int | None:
        """Derived: MTPLM minus payload. Marquis publish no mass in running order.

        True by construction, so it checks nothing — see `_reconciles`.
        """
        if self.mtplm_kilograms is None or self.mh_payload_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mh_payload_kilograms

    @property
    def recorded_width_mm(self) -> int | None:
        """The width, but only where `mirrors folded` is the body — see `base`.

        **The Admiral is the one that is not.** At 2260 mm that figure is a Ducato's folded
        mirrors rather than its roughly 2050 mm body, which is what FMLV holds for it; the
        coachbuilts and the A-classes overhang their mirrors, so theirs is the body.
        """
        return width_from_mirrors_folded(self.mh_width_mm, self.body_type)

    @property
    def body_type(self) -> BodyType | None:
        return _BODY_TYPES.get(self.manufacturer_range)


def layout_blocks(page: str, source_url: str) -> list[MobilvettaProduct]:
    """Every layout on one range page, in page order.

    A page holding no recognisable block returns an empty list rather than raising; the
    caller narrates that, because a range page that stops yielding layouts is the first
    thing a Marquis redesign would break.
    """
    text = plain_text(page)
    products: list[MobilvettaProduct] = []
    for match in _BLOCK.finditer(text):
        identity = _range_and_model(match.group("name"))
        if identity is None:
            continue
        manufacturer_range, model = identity
        body = match.group("body")
        price = _PRICE.search(body)
        products.append(
            MobilvettaProduct(
                source_url=source_url,
                manufacturer_range=manufacturer_range,
                model=model,
                mh_passenger_seats_inc_driver=_field(body, "seats"),
                berths=_field(body, "berths"),
                mh_length_mm=_field(body, "length"),
                mh_width_mm=_field(body, "width"),
                mh_height_mm=_field(body, "height"),
                mtplm_kilograms=_field(body, "mtplm"),
                mh_payload_kilograms=_field(body, "payload"),
                rrp_pounds=int(price.group("price").replace(",", "")) if price else None,
            )
        )
    return products


# --- The self-check, which this source does not provide --------------------------------


def _reconciles(product: MobilvettaProduct) -> tuple[bool, str]:
    """`(ok, why not)` — all this can check is that a block is not half-empty.

    **Mobilvetta has no arithmetic self-check**, and it is worth saying so plainly rather
    than dressing one up. Marquis publish MTPLM and MAX USER PAYLOAD but no mass in
    running order, so `payload == MTPLM - MRO` is true by construction. Nor is there a
    naming convention: `K.YACHT 59` is 5990mm, but 86 and 90 are both 7470mm, so the
    numbers are layout codes rather than lengths.

    What is left is a completeness check. A block that yields a heading but none of its
    figures means the page's shape has changed under the parse, which is the failure this
    source is actually exposed to — and `collect` also compares the roster count, which is
    the other half of the same defence.
    """
    figures = (
        product.mh_length_mm,
        product.mh_width_mm,
        product.mh_height_mm,
        product.mtplm_kilograms,
        product.mh_payload_kilograms,
    )
    if any(figure is not None for figure in figures):
        return True, ""
    return False, (
        "the block yielded a heading but not one figure, so the page's shape has probably "
        "changed"
    )


# --- What reaches the reviewer ---------------------------------------------------------


def _build_extracted_motorhome(product: MobilvettaProduct) -> ExtractedMotorhome:
    """One layout as a `Motorhome`, plus the provenance a reviewer sees beside each field."""
    source_url = product.source_url
    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.manufacturer_range,
        model=product.model,
        base_vehicle_manufacturer=fmlv_base_vehicle(BASE_VEHICLE),
        rrp_pounds=product.rrp_pounds,
        mro_kilograms=product.mro_kilograms,
        mtplm_kilograms=product.mtplm_kilograms,
        mh_payload_kilograms=product.mh_payload_kilograms,
        mh_length_mm=product.mh_length_mm,
        mh_width_mm=product.recorded_width_mm,
        mh_height_mm=product.mh_height_mm,
        mh_passenger_seats_inc_driver=product.mh_passenger_seats_inc_driver,
        berths=product.berths,
        body_type=product.body_type,
    )

    provenance: dict[str, Provenance] = {}

    def record(field: str, snippet: str) -> None:
        provenance[field] = Provenance(
            source_url=source_url,
            snippet=f"{product.label} — Marquis Leisure's own range page, {snippet}",
        )

    if product.mh_length_mm is not None:
        record("mh_length_mm", f"'OVERALL LENGTH {product.mh_length_mm}mm'")
    if product.recorded_width_mm is not None:
        record(
            "mh_width_mm",
            f"'OVERALL WIDTH (MIRRORS FOLDED) {product.recorded_width_mm}mm'. On a "
            f"coachbuilt the body overhangs the folded mirrors, so this measures the body",
        )
    elif product.mh_width_mm is not None:
        # See `benimar`: without this the review says the width "was not found", which is
        # untrue and reads as a parse failure.
        record(
            "mh_width_mm",
            f"no width excluding mirrors is published. The page's 'OVERALL WIDTH (MIRRORS "
            f"FOLDED) {product.mh_width_mm}mm' is a Ducato's folded mirrors, not its "
            f"roughly 2050mm body, and a recorded width excludes mirrors — so FMLV's own "
            f"figure is kept rather than widened by about 210mm. Settled with the "
            f"requester on 12 September 2026",
        )
    if product.mh_height_mm is not None:
        record(
            "mh_height_mm",
            f"'OVERALL HEIGHT (EXC TV AERIAL) {product.mh_height_mm}mm'",
        )
    if product.mh_passenger_seats_inc_driver is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"'BELTS {product.mh_passenger_seats_inc_driver}', which is this page's word "
            f"for a belted travel seat",
        )
    if product.berths is not None:
        record("berths", f"'BERTHS {product.berths}'")
    if product.mtplm_kilograms is not None:
        record("mtplm_kilograms", f"'MTPLM {product.mtplm_kilograms}kg'")
    if product.mh_payload_kilograms is not None:
        record("mh_payload_kilograms", f"'MAX USER PAYLOAD {product.mh_payload_kilograms}kg'")
    if product.mro_kilograms is not None:
        record(
            "mro_kilograms",
            f"derived as MTPLM {product.mtplm_kilograms}kg minus payload "
            f"{product.mh_payload_kilograms}kg. Marquis publish no mass in running order, "
            f"so nothing on the page corroborates this",
        )
    if product.rrp_pounds is not None:
        record(
            "rrp_pounds",
            f"'£{product.rrp_pounds:,} OTR'. Marquis Leisure are the sole UK importer and "
            f"seller, so this is the price that counts",
        )
    if motorhome.body_type is not None:
        record("body_type", f"every layout in the {product.manufacturer_range} range shares it")
    record("base_vehicle_manufacturer", "every layout is a Fiat Ducato conversion")

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


# --- The run ---------------------------------------------------------------------------

#: What the roster should come to, as a standing check.
#:
#: This is the only structural defence the source offers — see `_reconciles` — so a change
#: in the count is narrated loudly rather than accepted quietly.
EXPECTED_LAYOUTS = 8


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 - plain HTTP throughout
    snapshot_dir: Path,  # noqa: ARG001 - `Fetcher` owns the snapshot directory
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every layout on the importer's current range pages."""
    on_progress(f"fetching the importer's brand index: {INDEX_URL}")
    index = http.fetch(INDEX_URL)
    if index.status_code != 200:
        message = f"{INDEX_URL} returned {index.status_code}; it is the roster"
        raise RuntimeError(message)

    urls = find_range_urls(
        index.file_path.read_text(encoding="utf-8", errors="replace"),
        (key for key, _label in ranges),
    )
    on_progress(
        f"{len(urls)} range page(s), each holding one or more layouts"
        + (
            f"; {len(EXCLUDED_PAGES)} page excluded as stock rather than range"
            if EXCLUDED_PAGES
            else ""
        )
    )

    results: list[ExtractedMotorhome] = []
    for url in urls:
        page_result = http.fetch(url)
        if page_result.status_code != 200:
            on_progress(f"SKIPPED: {url} returned {page_result.status_code}")
            continue
        page = page_result.file_path.read_text(encoding="utf-8", errors="replace")

        products = layout_blocks(page, url)
        if not products:
            on_progress(
                f"WARNING: {url} yielded no layout at all. A range page that stops "
                f"producing 'Weights and Dimensions' blocks is what a Marquis redesign "
                f"would break first"
            )
            continue
        on_progress(f"{url.rsplit('/', 1)[-1]}: {len(products)} layout(s)")

        for product in products:
            reconciles, why_not = _reconciles(product)
            if not reconciles:
                on_progress(f"SKIPPED [{product.label}]: {why_not}")
                continue
            if product.rrp_pounds is None:
                on_progress(
                    f"[{product.label}] WARNING: no OTR price in its block, so FMLV's own "
                    f"figure is left alone"
                )
            results.append(_build_extracted_motorhome(product))

    if len(results) != EXPECTED_LAYOUTS:
        on_progress(
            f"WARNING: collected {len(results)} layout(s) where the survey found "
            f"{EXPECTED_LAYOUTS}. This source publishes no arithmetic self-check, so the "
            f"roster count is the main defence — check the range pages before accepting"
        )
    on_progress(f"collected {len(results)} product(s)")
    return results
