"""Volkswagen's California — the only pre-built campervan VW sell.

See `docs/adapters/volkswagen.md` for the survey. **Scope is the California and nothing
else**: ordinary vans are out, and so is the *"build your own"* configurator the site
pushes hard. We record the pre-built model at its **base variant**, never a configured one.

## Two names that look like mistakes and are not

`fmlv_manufacturer` is **`Volkswagen`** (NCC id 259 — 188 is also called `Volkswagen` and
is a different record) while every product's **base vehicle is `VW`**. That is the naming
protocol in `base.py`, one name per company per role, and neither is to be "corrected".

## Four documents, all UK editions in sterling

The web pages carry almost nothing; the figures are in PDFs under `/importers/gb/`, all
linked from `/en/download-a-brochure.html` and rediscovered there each run.

| document | what is read from it |
|---|---|
| `california-brochure.pdf` | weights per variant and engine, width and height, length |
| `california-pl.pdf` | prices **and the seat count** |
| `grand_california-brochure.pdf` | weights, seats, beds and prices — it has no price guide |

**There is no separate Grand California price guide.** The price-guide folder holds eleven
files and none of them is it; its prices are inside its own brochure.

## The self-check is published, and the two brochures weigh differently

The California's footnote reads *"Payload = gross vehicle weight minus unladen weight"* and
it prints all three columns, so the arithmetic checks itself: 2,850 − 2,383 = 467.

**The Grand California does not work the same way, and the difference is the driver.** Its
column is a *kerb* weight, footnoted *"includes 90% fuel load with no driver or
passengers"*, where the California's unladen weight *"includes approximately 90% fuel load
and 75kg for driver"*. Its printed payload is consistently **75kg less** than gross minus
kerb, on every one of its eight rows:

```
600 3.5T    3,500 − 3,021 = 479   printed payload 404
600 3.88T   3,880 − 3,024 = 856   printed payload 781
680 3.88T   3,880 − 3,196 = 684   printed payload 609
```

So the mass in running order is **kerb + 75**, which reproduces FMLV's 3,098 and 3,273 to
within two kilograms. Recording the kerb weight itself would put a different quantity in
that column. `DRIVER_ALLOWANCE_KG` is that 75, and `_reconciles` checks the right
subtraction for each document.

## The base variant, and what it leaves

The lowest-engine row per named model — the requester's instruction, 11 October 2026. That
takes the 150PS 2.0 TDI for Beach, Coast and Ocean and the 245PS eHybrid for the hybrids,
and leaves the 204PS 2.0 TSI, the Grand California's 4MOTION and 3.88T upgrades, and the
**Dune** trims entirely.

## What is deliberately not proposed

* **The Grand California's dimensions.** Its brochure gives them only as `5.99m 2.04m
  2.97m` — two decimal places of a metre, where FMLV holds 5986, 2040 and 2971. Proposing
  5990 and 2970 would replace better figures with rounder ones.
* **The California's berths.** Neither brochure states a berth count as a figure; the
  California's is prose about *"two additional sleeping spaces"*. The Grand California
  *does* print `Number of beds: 2`, so that one is proposed and the other is not.
"""

from __future__ import annotations

import html as htmllib
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..fetch.http import Fetcher
from ..fetch.pdf import extract_text
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

__all__ = [
    "BASE_URL",
    "BROCHURE_INDEX",
    "DRIVER_ALLOWANCE_KG",
    "EXPECTED_PRODUCTS",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "CaliforniaWeight",
    "GrandWeight",
    "Product",
    "base_variants",
    "collect",
    "find_documents",
    "parse_california_dimensions",
    "parse_california_prices",
    "parse_california_weights",
    "parse_grand_prices",
    "parse_grand_weights",
]

BASE_URL = "https://www.volkswagen-vans.co.uk"
MANUFACTURER = "Volkswagen"
MANUFACTURER_DISPLAY_NAME = "Volkswagen"
BROCHURE_INDEX = f"{BASE_URL}/en/download-a-brochure.html"

#: Six Californias and two Grand Californias, which is exactly what FMLV holds.
EXPECTED_PRODUCTS = 8

#: The driver the Grand California's kerb weight leaves out and the California's unladen
#: weight includes. See the module docstring — this is read off VW's own arithmetic, not
#: assumed: their payload is 75kg below gross minus kerb on all eight Grand rows.
DRIVER_ALLOWANCE_KG = 75

#: A campervan taller than this is a high top.
HIGH_TOP_ABOVE_MM = 2300

#: Trims out of scope. **Dune is a trim of the Grand California**, not a model FMLV holds,
#: and the requester's instruction is the base variant only.
_EXCLUDED_TRIMS = ("Dune",)

#: `California Beach Camper` heads the Beach's rows; FMLV files it as `Beach`.
_CALIFORNIA_VARIANTS: dict[str, str] = {
    "California Beach Camper": "Beach",
    "California Coast": "Coast",
    "California Ocean": "Ocean",
}

_EHYBRID = re.compile(r"\beHybrid\b", re.I)
_POWER = re.compile(r"(\d{2,3})\s*PS", re.I)

#: One weights row: the engine, then gross weight, two axle/trailer pairs, the gross train
#: weight, the unladen or kerb weight, and the payload.
_WEIGHT_ROW = re.compile(
    r"^(?P<engine>.+?)\s+(?P<gross>\d{1,2},\d{3})\d*\s+"
    r"[\d,]+\s*/\s*[\d,]+\s+[\d,]+\s*/\s*[\d,]+\s+"
    r"(?P<train>[\d,]+)\s+(?P<mass>\d{1,2},\d{3})\d*\s+(?P<payload>\d{3,4})\s*$"
)

#: One price row of the California price list: the model, its type approval, the seat count
#: and five money columns. **The fifth is the one the website headlines** — the California
#: page shows £64,432 for the Beach, which is `Total RRP inc. OTR inc. VAT`.
_PRICE_ROW = re.compile(
    r"^California\s+(?P<variant>Beach Camper|Coast|Ocean)\s+(?P<engine>.+?)\s+"
    r"M1\s+(?:SP\s+Camper|Car)\s+(?P<seats>\d)\s+"
    r"(?:£[\d,]+\.\d{2}\s+){4}£(?P<price>[\d,]+)\.\d{2}\s*$"
)

#: The Grand California's price rows carry four money columns, not five, and name their
#: weight class as `3.5T` or `3.88T` where the weights table says `3,500` or `3,880`.
_GRAND_PRICE_ROW = re.compile(
    r"^(?P<engine>2\.0TDI.+?)\s+(?P<tonnage>\d\.\d{1,2})T\d*\s+Diesel\s+"
    r"(?:£[\d,]+\.\d{2}\s+){3}£(?P<price>[\d,]+)\.\d{2}\s*$"
)

_GRAND_MODEL = re.compile(r"^Grand California\s+(?P<model>\d{3})(?P<trim>\s+\w+)?\s*$")


def _number(raw: str | None) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw.replace(",", "").strip())
    except ValueError:
        return None


def find_documents(index_html: str) -> dict[str, str]:
    """The three California PDFs, by the name in their own filename.

    **Rediscovered rather than written in.** Their paths carry a folder per model and VW
    reissue them; the index page is the one place all three are listed together.
    """
    found: dict[str, str] = {}
    for url in re.findall(r'https?://[^"\')\s]+\.pdf', htmllib.unescape(index_html), re.I):
        name = url.rsplit("/", 1)[-1].lower()
        if name == "california-brochure.pdf":
            found.setdefault("california_brochure", url)
        elif name == "california-pl.pdf":
            found.setdefault("california_prices", url)
        elif name == "grand_california-brochure.pdf":
            found.setdefault("grand_brochure", url)
    return found


@dataclass(frozen=True)
class CaliforniaWeight:
    """One engine's row of the California weights table."""

    variant: str
    engine: str
    gross_kilograms: int
    #: Already the mass in running order: VW's unladen weight includes 75kg for a driver.
    mro_kilograms: int
    payload_kilograms: int

    @property
    def is_ehybrid(self) -> bool:
        return bool(_EHYBRID.search(self.engine))

    @property
    def power(self) -> int:
        match = _POWER.search(self.engine)
        return int(match.group(1)) if match else 0

    @property
    def model(self) -> str:
        return f"{self.variant} eHybrid" if self.is_ehybrid else self.variant


@dataclass(frozen=True)
class GrandWeight:
    """One row of the Grand California weights table.

    `kerb_kilograms` is **not** the mass in running order — it excludes the driver. See
    `mro_kilograms`.
    """

    model: str
    engine: str
    gross_kilograms: int
    kerb_kilograms: int
    payload_kilograms: int

    @property
    def mro_kilograms(self) -> int:
        """Kerb weight plus the driver VW leave out of it."""
        return self.kerb_kilograms + DRIVER_ALLOWANCE_KG

    @property
    def is_four_motion(self) -> bool:
        return "4MOTION" in self.engine.upper()


def parse_california_weights(brochure_text: str) -> list[CaliforniaWeight]:
    """Every engine row of the California weights table, under its variant heading."""
    variant: str | None = None
    rows: list[CaliforniaWeight] = []
    for raw in brochure_text.splitlines():
        line = " ".join(raw.split())
        if line in _CALIFORNIA_VARIANTS:
            variant = _CALIFORNIA_VARIANTS[line]
            continue
        if variant is None:
            continue
        match = _WEIGHT_ROW.match(line)
        if not match:
            continue
        gross = _number(match.group("gross"))
        mass = _number(match.group("mass"))
        payload = _number(match.group("payload"))
        if gross is None or mass is None or payload is None:
            continue
        rows.append(
            CaliforniaWeight(
                variant=variant,
                engine=match.group("engine").strip(),
                gross_kilograms=gross,
                mro_kilograms=mass,
                payload_kilograms=payload,
            )
        )
    return rows


def parse_grand_weights(brochure_text: str) -> list[GrandWeight]:
    """The Grand California weights table, **excluding the Dune trims**."""
    model: str | None = None
    rows: list[GrandWeight] = []
    for raw in brochure_text.splitlines():
        line = " ".join(raw.split())
        heading = _GRAND_MODEL.match(line)
        if heading:
            trim = (heading.group("trim") or "").strip()
            model = None if trim in _EXCLUDED_TRIMS else heading.group("model")
            continue
        if model is None:
            continue
        match = _WEIGHT_ROW.match(line)
        if not match:
            continue
        gross = _number(match.group("gross"))
        kerb = _number(match.group("mass"))
        payload = _number(match.group("payload"))
        if gross is None or kerb is None or payload is None:
            continue
        rows.append(
            GrandWeight(
                model=model,
                engine=match.group("engine").strip(),
                gross_kilograms=gross,
                kerb_kilograms=kerb,
                payload_kilograms=payload,
            )
        )
    return rows


def parse_california_prices(price_list_text: str) -> dict[str, tuple[int, int]]:
    """`{model: (price, seats)}` from the price list's model table.

    The price taken is the **fifth** money column, `Total RRP inc. OTR inc. VAT`, which is
    the figure the website headlines.
    """
    found: dict[str, tuple[int, int]] = {}
    for raw in price_list_text.splitlines():
        match = _PRICE_ROW.match(" ".join(raw.split()))
        if not match:
            continue
        variant = _CALIFORNIA_VARIANTS[f"California {match.group('variant')}"]
        model = f"{variant} eHybrid" if _EHYBRID.search(match.group("engine")) else variant
        price, seats = _number(match.group("price")), _number(match.group("seats"))
        if price is None or seats is None:
            continue
        # The lowest-priced row per model is the base variant; a dearer engine never wins.
        if model not in found or price < found[model][0]:
            found[model] = (price, seats)
    return found


def parse_grand_prices(brochure_text: str) -> dict[tuple[str, int], int]:
    """`{(model, gross weight): price}` from the Grand California's own brochure.

    Keyed on the weight class because that is what joins a price row to a weights row —
    the price list writes `3.5T` where the weights table writes `3,500`.
    """
    model: str | None = None
    found: dict[tuple[str, int], int] = {}
    for raw in brochure_text.splitlines():
        line = " ".join(raw.split())
        heading = _GRAND_MODEL.match(line)
        if heading:
            trim = (heading.group("trim") or "").strip()
            model = None if trim in _EXCLUDED_TRIMS else heading.group("model")
            continue
        if model is None:
            continue
        match = _GRAND_PRICE_ROW.match(line)
        if not match:
            continue
        price = _number(match.group("price"))
        gross = round(float(match.group("tonnage")) * 1000)
        if price is None:
            continue
        key = (model, gross)
        # 4MOTION is dearer than front-wheel drive at the same weight; the base is cheaper.
        if key not in found or price < found[key]:
            found[key] = price
    return found


def parse_california_dimensions(brochure_text: str) -> dict[str, int]:
    """Length, width and height, in millimetres.

    Width and height are labelled rows — `W1 Width – mm 1,941`. **The length is not**: the
    dimensions page prints it as a bare figure beside a diagram, so it is read from the
    prose on the model page instead, where it is stated outright and wraps across two
    lines. `Width including mirrors` is published and deliberately ignored.
    """
    flat = " ".join(brochure_text.split())
    found: dict[str, int] = {}
    for key, pattern in (
        ("mh_width_mm", r"W1 Width\s*[–-]\s*mm\s+([\d,]+)"),
        ("mh_height_mm", r"H3 Vehicle height\s*[–-]\s*mm\s+([\d,]+)"),
        ("mh_length_mm", r"California measures\s+([\d,]+)\s*mm in length"),
    ):
        match = re.search(pattern, flat, re.I)
        value = _number(match.group(1)) if match else None
        if value is not None:
            found[key] = value
    return found


def base_variants(rows: list[CaliforniaWeight]) -> list[CaliforniaWeight]:
    """One row per FMLV model: the **lowest-powered** engine of each.

    That is the base-vehicle rule applied to an engine range — it takes the 150PS TDI over
    the 204PS TSI on the Coast and the Ocean, and leaves the dearer one uncollected.
    """
    best: dict[str, CaliforniaWeight] = {}
    for row in rows:
        current = best.get(row.model)
        if current is None or row.power < current.power:
            best[row.model] = row
    return list(best.values())


@dataclass
class Product:
    """One vehicle as it will be proposed."""

    manufacturer_range: str
    model: str
    gross_kilograms: int
    mro_kilograms: int
    payload_kilograms: int
    source_url: str
    mass_basis: str
    rrp_pounds: int | None = None
    seats: int | None = None
    berths: int | None = None
    mh_length_mm: int | None = None
    mh_width_mm: int | None = None
    mh_height_mm: int | None = None
    body_type: BodyType | None = None
    body_type_reason: str = ""

    @property
    def label(self) -> str:
        return f"{self.manufacturer_range} {self.model}"


def _reconciles_california(row: CaliforniaWeight) -> tuple[bool, str]:
    """`payload == gross − unladen`, which is what the brochure's own footnote says."""
    derived = row.gross_kilograms - row.mro_kilograms
    if derived != row.payload_kilograms:
        return False, (
            f"gross {row.gross_kilograms}kg less unladen {row.mro_kilograms}kg is "
            f"{derived}kg, where the table prints a payload of {row.payload_kilograms}kg"
        )
    return True, (
        f"gross {row.gross_kilograms}kg less unladen {row.mro_kilograms}kg, matching the "
        f"{row.payload_kilograms}kg payload the same table prints. VW's unladen weight "
        f"already includes {DRIVER_ALLOWANCE_KG}kg for a driver, so it is the mass in "
        f"running order"
    )


def _reconciles_grand(row: GrandWeight) -> tuple[bool, str]:
    """`payload == gross − kerb − 75`, which is what VW's own figures do.

    Their footnote claims payload is gross minus kerb, and it is not: the printed figure is
    75kg lower on every row, because the kerb weight leaves out the driver the payload
    accounts for.
    """
    derived = row.gross_kilograms - row.mro_kilograms
    if derived != row.payload_kilograms:
        return False, (
            f"gross {row.gross_kilograms}kg less kerb {row.kerb_kilograms}kg plus the "
            f"{DRIVER_ALLOWANCE_KG}kg driver is {derived}kg, where the table prints "
            f"{row.payload_kilograms}kg"
        )
    return True, (
        f"gross {row.gross_kilograms}kg less a mass in running order of "
        f"{row.mro_kilograms}kg — VW's kerb weight of {row.kerb_kilograms}kg excludes the "
        f"driver, so {DRIVER_ALLOWANCE_KG}kg is added to it — matching the "
        f"{row.payload_kilograms}kg payload printed beside it"
    )


def build_extracted(product: Product) -> ExtractedMotorhome:
    """One California, with provenance on everything it proposes."""
    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.manufacturer_range,
        model=product.model,
        base_vehicle_manufacturer=fmlv_base_vehicle("VW"),
        rrp_pounds=product.rrp_pounds,
        berths=product.berths,
        mh_passenger_seats_inc_driver=product.seats,
        mtplm_kilograms=product.gross_kilograms,
        mro_kilograms=product.mro_kilograms,
        mh_payload_kilograms=product.payload_kilograms,
        mh_length_mm=product.mh_length_mm,
        mh_width_mm=product.mh_width_mm,
        mh_height_mm=product.mh_height_mm,
        body_type=product.body_type,
    )

    provenance: dict[str, Provenance] = {}

    def record(field: str, snippet: str, *, source: str | None = None) -> None:
        provenance[field] = Provenance(
            source_url=source or product.source_url, snippet=f"{product.label} — {snippet}"
        )

    record("manufacturer_range", f'range "{product.manufacturer_range}", as VW name it')
    record(
        "base_vehicle_manufacturer",
        "VW — the abbreviated form is the base vehicle and the full form the manufacturer, "
        "which is why this product reads Volkswagen / VW and not one or the other twice",
    )
    record("mtplm_kilograms", f"{product.gross_kilograms}kg gross vehicle weight")
    record("mro_kilograms", f"{product.mro_kilograms}kg — {product.mass_basis}")
    record("mh_payload_kilograms", f"{product.payload_kilograms}kg, as published")
    if product.rrp_pounds is not None:
        record(
            "rrp_pounds",
            f"£{product.rrp_pounds:,}, the 'Total RRP inc. OTR inc. VAT' column — the "
            f"figure VW headline on the vehicle's own page",
        )
    if product.seats is not None:
        record("mh_passenger_seats_inc_driver", f"{product.seats} seats including the driver")
    if product.berths is not None:
        record(
            "berths",
            f"{product.berths} beds, as the brochure states. An over-cab bed is offered as "
            f"an option on top, and the lower figure is what the settled rule asks for",
        )
    for field, value, label in (
        ("mh_length_mm", product.mh_length_mm, "length"),
        ("mh_width_mm", product.mh_width_mm, "width, excluding the mirrors VW also publish"),
        ("mh_height_mm", product.mh_height_mm, "height"),
    ):
        if value is not None:
            record(field, f"{value}mm {label}")
    if product.body_type is not None:
        record("body_type", product.body_type_reason)
    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


def _text(http: Fetcher, url: str, what: str) -> str:
    result = http.fetch(url)
    if result.status_code != 200:
        msg = f"the {what} at {url} returned {result.status_code}"
        raise RuntimeError(msg)
    return extract_text(result.file_path).text


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 — the PDFs are plain; see the module docstring
    snapshot_dir: Path,  # noqa: ARG001 — `http` already snapshots into it
    *,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every California and Grand California, at its base variant."""
    index = http.fetch(BROCHURE_INDEX)
    if index.status_code != 200:
        msg = f"the brochure index {BROCHURE_INDEX} returned {index.status_code}"
        raise RuntimeError(msg)
    documents = find_documents(index.file_path.read_text(encoding="utf-8", errors="replace"))
    missing = {"california_brochure", "california_prices", "grand_brochure"} - set(documents)
    if missing:
        msg = (
            f"{BROCHURE_INDEX} no longer links {sorted(missing)} — the figures live in "
            f"those PDFs and nowhere else"
        )
        raise RuntimeError(msg)
    on_progress(f"found {len(documents)} document(s) on the brochure index")

    brochure = _text(http, documents["california_brochure"], "California brochure")
    price_list = _text(http, documents["california_prices"], "California price list")
    grand = _text(http, documents["grand_brochure"], "Grand California brochure")

    dimensions = parse_california_dimensions(brochure)
    if len(dimensions) < 3:
        on_progress(
            f"ONLY {sorted(dimensions)} READ from the California's dimensions — the rest "
            f"are not proposed and FMLV's own figures stand"
        )
    prices = parse_california_prices(price_list)
    products: list[Product] = []

    rows = parse_california_weights(brochure)
    on_progress(f"the California weights table lists {len(rows)} engine row(s)")
    for row in sorted(rows, key=lambda r: (r.variant, r.is_ehybrid)):
        if row not in base_variants(rows):
            on_progress(
                f"[California {row.model}] not the base variant — {row.engine} is "
                f"{row.power}PS and a lower-powered engine is published for this model"
            )
            continue
        ok, basis = _reconciles_california(row)
        if not ok:
            on_progress(f"[California {row.model}] DROPPED: {basis}")
            continue
        price, seats = prices.get(row.model, (None, None))
        if price is None:
            on_progress(f"[California {row.model}] WARNING: no price in the price list")
        products.append(
            Product(
                manufacturer_range="California",
                model=row.model,
                gross_kilograms=row.gross_kilograms,
                mro_kilograms=row.mro_kilograms,
                payload_kilograms=row.payload_kilograms,
                source_url=documents["california_brochure"],
                mass_basis=basis,
                rrp_pounds=price,
                seats=seats,
                # Prose only — see the module docstring.
                berths=None,
                body_type=BodyType.CAMPERVAN_ELEVATING_ROOF,
                body_type_reason=(
                    "a campervan with an elevating roof: the brochure states 'A pop-up roof "
                    "will be standard too' on every California"
                ),
                **dimensions,
            )
        )

    grand_prices = parse_grand_prices(grand)
    grand_rows = parse_grand_weights(grand)
    on_progress(f"the Grand California weights table lists {len(grand_rows)} row(s), Dune excluded")
    by_model: dict[str, GrandWeight] = {}
    for row in grand_rows:
        current = by_model.get(row.model)
        # The base is the lightest class, and front-wheel drive before 4MOTION within it.
        if (
            current is None
            or row.gross_kilograms < current.gross_kilograms
            or (row.gross_kilograms == current.gross_kilograms and current.is_four_motion)
        ):
            by_model[row.model] = row
    for model, row in sorted(by_model.items()):
        ok, basis = _reconciles_grand(row)
        if not ok:
            on_progress(f"[Grand California {model}] DROPPED: {basis}")
            continue
        price = grand_prices.get((model, row.gross_kilograms))
        if price is None:
            on_progress(f"[Grand California {model}] WARNING: no price for its weight class")
        products.append(
            Product(
                manufacturer_range="Grand California",
                model=model,
                gross_kilograms=row.gross_kilograms,
                mro_kilograms=row.mro_kilograms,
                payload_kilograms=row.payload_kilograms,
                source_url=documents["grand_brochure"],
                mass_basis=basis,
                rrp_pounds=price,
                seats=4,
                berths=2,
                body_type=BodyType.CAMPERVAN_HIGH_TOP,
                body_type_reason=(
                    "a high-top campervan: its brochure gives an exterior height of 2.97m, "
                    f"well above the {HIGH_TOP_ABOVE_MM}mm threshold"
                ),
            )
        )

    results = [build_extracted(product) for product in products]
    for product in products:
        on_progress(
            f"[{product.label}] read: £{product.rrp_pounds or 0:,}, "
            f"{product.gross_kilograms}kg gross, {product.mro_kilograms}kg running order, "
            f"{product.payload_kilograms}kg payload, {product.seats} seats"
        )

    on_progress(
        "THE GRAND CALIFORNIA'S DIMENSIONS ARE NOT PROPOSED. Its brochure gives them only "
        "as metres to two decimals — 5.99m, 2.04m, 2.97m — where FMLV holds 5986, 2040 and "
        "2971, so proposing them would replace better figures with rounder ones."
    )
    on_progress(
        "THE CALIFORNIA'S BERTHS ARE NOT PROPOSED. Neither brochure states a berth count as "
        "a figure for it; the Grand California does print 'Number of beds: 2', which is "
        "proposed."
    )
    on_progress(
        "THE BASE VARIANT IS THE LOWEST-POWERED ENGINE of each model, which leaves the "
        "204PS 2.0 TSI on the Coast and the Ocean, the Grand California's 4MOTION and 3.88T "
        "upgrades, and the Dune trims uncollected."
    )
    if len(results) != EXPECTED_PRODUCTS:
        on_progress(
            f"expected {EXPECTED_PRODUCTS} products and collected {len(results)} — check "
            f"whether the range has changed"
        )
    on_progress(f"collected {len(results)} Volkswagen California product(s)")
    return results
