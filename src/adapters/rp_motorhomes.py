"""RP Motorhomes (rpmotorhomes.com) — Sprinter-based high-top campervans, two ranges.

See `docs/adapters/rp-motorhomes.md` for the survey. **The source is the 2027 brochures**,
one per range, rediscovered from each range's own page per run.

## The prices are in the brochure and nowhere else

RP publish no price on any page of their site. Page 21 of each brochure is a
`Technical Data` spread that prices the range outright, and every figure FMLV holds is
about **£21,000 light** — the largest single correction any adapter here has been built
for. That spread is the whole reason for this adapter.

The PDFs sit on Squarespace `/s/` paths and fetch without any form, the same as
`fifth_wheel.py`.

## Each dimension is published twice, and the summary tiles are wrong

The spread gives every dimension as a rounded tile *and* as a figure on a scale drawing.
**They disagree, and the drawing is the reliable one.**

The Rebel's tiles read `5.9m` and `7.0m` for RWD and AWD while **both** drawings say
`5932 mm`, and FMLV holds 5932 for both. The `7.0m` is an error, almost certainly copied
from the Rebellion page — whose models genuinely are 6967mm. Taking the tile would stretch
a Rebel AWD by a metre.

So nothing is read from the tiles except the GVW, which they give cleanly and the drawings
do not give at all.

## The drawing's six figures, and how they are assigned

Both brochures lay the drawing figures out identically:

```
2020 mm      the body width
2345 mm      the width across the mirrors — not FMLV's
5932 mm      the length, once per drawing
5932 mm
2780 mm      the lower height
2900 mm      the taller height
```

The width pair is told apart by size, and FMLV records the body — the settled rule.

**The heights are assigned by magnitude, not by position**, because position cannot be
trusted: the captions beneath them run AWD first and then RWD, the reverse of the figures
above. An all-wheel-drive Sprinter sits higher than the rear-wheel-drive one on the same
body, which is true of both ranges and of all four products FMLV holds, so the taller
figure is the AWD's.

**A length is only recorded when both drawings agree.** They do on both ranges today. If a
range ever gave two, there would be no safe way to say which belonged to which model — the
tiles cannot arbitrate, having already been shown wrong — so it is dropped and narrated.

## No payload, no mass in running order, and so no self-check

Every model's payload reads **`TBC*`**, footnoted *"Payload is affected by additional
habitation options"*, and neither brochure publishes a mass in running order anywhere —
only the GVW. `MTPLM - MRO = payload` cannot be run, so the check here is structural, and
FMLV's own masses carry through untouched. A `TBC` is not a figure.

## The Rebel Raid is reported, not collected

The brochure's contents page reads `2027 Specification REBEL RWD AWD RAID` and page 23
prices a `Special Edition Rebel Raid - £199,995` on the AWD platform. The settled rule makes
a named edition a product, and FMLV does not hold it.

**But pages 24 to 26 carry no technical figures at all** — no GVW, no dimensions, nothing
of its own. Creating it would mean inferring every required field from the Rebel AWD, and a
new product with guessed masses is worse than a documented absence. So the run reports it
and asks for its data instead.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from ..fetch.http import Fetcher
from ..fetch.pdf import extract_text
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from . import habitation
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

__all__ = [
    "BASE_URL",
    "DRIVETRAINS",
    "EXPECTED_PRODUCTS",
    "HIGH_TOP_ABOVE_MM",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "MINIMUM_CREDIBLE_PRICE",
    "RANGE_PATHS",
    "Drawing",
    "RangeBrochure",
    "SPECIAL_EDITION",
    "body_type_for",
    "build_extracted",
    "collect",
    "find_brochure_url",
    "parse_drawing",
    "parse_gross_weights",
    "parse_prices",
    "parse_range_brochure",
]

BASE_URL = "https://rpmotorhomes.com"
MANUFACTURER = "RP Motorhomes"
MANUFACTURER_DISPLAY_NAME = "RP Motorhomes"

#: The two ranges and the page that links each brochure. **The `-2027` pages, deliberately**
#: — the site keeps `/rebel` and `/rebellion` alongside them, and those are last season's.
RANGE_PATHS: dict[str, str] = {
    "Rebel": "/rebel-2027",
    "Rebellion": "/rebellion-2027",
}

#: How FMLV splits these: the range is the family and the model is the drivetrain. In the
#: order the brochure's tiles use, which is also the order its prices appear in.
DRIVETRAINS: tuple[str, str] = ("RWD", "AWD")

#: Two ranges at two drivetrains, which is what FMLV holds.
EXPECTED_PRODUCTS = 4

#: Below this, a figure on the Technical Data spread is an option rather than a vehicle.
#: The cheapest RP is £147,000 and the dearest option on the page is £4,051.
MINIMUM_CREDIBLE_PRICE = 50_000

#: A campervan taller than this is a high top — the same threshold as every other adapter
#: that needs it. Every RP clears it by at least 480mm.
HIGH_TOP_ABOVE_MM = 2300

#: A named edition that is a product by the settled rule and cannot be built yet, because
#: the brochure gives it no specification of its own. Reported on every run.
SPECIAL_EDITION: dict[str, str] = {
    "Rebel Raid": (
        "the brochure's contents page reads '2027 Specification REBEL RWD AWD RAID' and "
        "page 23 prices a 'Special Edition Rebel Raid - £199,995' on the AWD platform. A "
        "named edition is a product under the settled rule and FMLV does not hold it — but "
        "pages 24 to 26 carry NO technical figures at all, so every required field would "
        "have to be inferred from the Rebel AWD. Ask RP for its data rather than creating "
        "a product with guessed masses"
    ),
}

#: `/s/2027-Rebel-Brochure-Final-Share-Version-v1.pdf`.
_BROCHURE_LINK = re.compile(r'["\'](/s/[^"\']*\.pdf)["\']', re.I)

#: `Rebel RWD: £147,000`, `Rebel AWD:  £155,000`.
_PRICE = re.compile(r"(?P<range>\w+)\s+(?P<drivetrain>RWD|AWD)\s*:\s*£?\s*(?P<price>[\d,]{6,})")

#: The GVW tile row — `3,500 4,100`, RWD then AWD, alone on its line. The only thing read
#: from the tiles, because the drawings do not carry it.
_GROSS_WEIGHTS = re.compile(r"^\s*(?P<rwd>[1-9],\d{3})\s+(?P<awd>[1-9],\d{3})\s*$", re.M)

#: `2020 mm`, `5932 mm`. Four digits and a unit, which no tile figure uses — those are
#: written in metres.
_DRAWING_FIGURE = re.compile(r"(\d{4})\s*mm")

#: `Special Edition Rebel Raid - £199,995`.
_SPECIAL_EDITION_PRICE = re.compile(
    r"Special Edition\s+(?P<name>[\w\s]+?)\s*[-–]\s*£?\s*(?P<price>[\d,]{6,})", re.I
)

#: How many figures the drawing block carries, and what each is. Anything else means the
#: spread has been redrawn and the reading is refused rather than guessed at.
_DRAWING_FIGURE_COUNT = 6


@dataclass(frozen=True)
class Drawing:
    """The scale drawings' own figures, in millimetres."""

    width_mm: int
    width_including_mirrors_mm: int
    length_mm: int | None
    heights_mm: tuple[int, ...]

    def height_for(self, drivetrain: str) -> int | None:
        """The height of one drivetrain, assigned by magnitude.

        **Not by position.** The captions beneath the drawings run AWD first and then RWD,
        the reverse of the figures above them, so position proves nothing. An all-wheel-
        drive Sprinter sits higher than the rear-wheel-drive one on the same body, which
        holds on both ranges and on all four products FMLV already carries.
        """
        if len(self.heights_mm) != len(DRIVETRAINS):
            return None
        return self.heights_mm[DRIVETRAINS.index(drivetrain)]


def parse_drawing(page_text: str) -> Drawing | None:
    """The six figures the Technical Data drawings carry.

    Laid out identically in both brochures: the body width, the width across the mirrors,
    the length once per drawing, and then the two heights. The widths are told apart by
    size and the heights are sorted, so neither depends on the order they were extracted
    in.
    """
    figures = [int(value) for value in _DRAWING_FIGURE.findall(page_text)]
    if len(figures) != _DRAWING_FIGURE_COUNT:
        return None
    widths = sorted(figures[:2])
    lengths = {figures[2], figures[3]}
    heights = tuple(sorted(figures[4:]))
    return Drawing(
        width_mm=widths[0],
        width_including_mirrors_mm=widths[1],
        # **Only where both drawings agree.** With two different lengths there is nothing
        # that could say which belonged to which model: the tiles cannot arbitrate, having
        # already been shown wrong on the Rebel AWD.
        length_mm=lengths.pop() if len(lengths) == 1 else None,
        heights_mm=heights,
    )


def parse_prices(page_text: str) -> dict[str, int]:
    """`{drivetrain: price}` from the spread's own headline prices."""
    found: dict[str, int] = {}
    for match in _PRICE.finditer(page_text):
        price = int(match.group("price").replace(",", ""))
        if price >= MINIMUM_CREDIBLE_PRICE:
            found.setdefault(match.group("drivetrain"), price)
    return found


def parse_gross_weights(page_text: str) -> dict[str, int]:
    """`{drivetrain: GVW}` from the tile row, which the drawings do not carry.

    The GVW upgrades beside it — `3,880kg GVW £505`, `4,400kg GVW £505` — are **priced
    options**, so the base-vehicle rule records the figures in this row and not those.
    They are excluded by the pattern requiring the pair to sit alone on its line.
    """
    match = _GROSS_WEIGHTS.search(page_text)
    if match is None:
        return {}
    return {
        "RWD": int(match.group("rwd").replace(",", "")),
        "AWD": int(match.group("awd").replace(",", "")),
    }


def find_brochure_url(page_html: str) -> str | None:
    """The range's 2027 brochure, from the `/s/` path its own page carries."""
    for match in _BROCHURE_LINK.finditer(page_html):
        path = match.group(1)
        if "brochure" in path.lower():
            return f"{BASE_URL}{path}"
    return None


def body_type_for(height_mm: int | None) -> tuple[BodyType | None, str]:
    """`campervan_high_top` for every RP, from its own published height."""
    if height_mm is None:
        return None, "no height could be read from the drawing, so no body type is proposed"
    if height_mm <= HIGH_TOP_ABOVE_MM:
        return BodyType.CAMPERVAN, (
            f"a campervan: {height_mm}mm is at or below the {HIGH_TOP_ABOVE_MM}mm high-top "
            f"threshold"
        )
    return BodyType.CAMPERVAN_HIGH_TOP, (
        f"a high-top campervan: {height_mm}mm is above the {HIGH_TOP_ABOVE_MM}mm threshold"
    )


@dataclass
class RangeBrochure:
    """One range's 2027 brochure, as read."""

    manufacturer_range: str
    url: str
    prices: dict[str, int] = field(default_factory=dict)
    gross_weights: dict[str, int] = field(default_factory=dict)
    drawing: Drawing | None = None
    special_editions: dict[str, int] = field(default_factory=dict)
    equipment: list[str] = field(default_factory=list)


def parse_range_brochure(text: str, *, manufacturer_range: str, url: str) -> RangeBrochure:
    """One brochure: its Technical Data spread, and the equipment prose for the findings.

    The spread is found by its own heading rather than by page number, so a brochure that
    gains a page still reads.
    """
    page = next(
        (
            candidate
            for candidate in text.split("\n\n")
            if "Technical Data" in candidate and "GVW" in candidate
        ),
        "",
    )
    return RangeBrochure(
        manufacturer_range=manufacturer_range,
        url=url,
        prices=parse_prices(page),
        gross_weights=parse_gross_weights(page),
        drawing=parse_drawing(page),
        special_editions={
            match.group("name").strip(): int(match.group("price").replace(",", ""))
            for match in _SPECIAL_EDITION_PRICE.finditer(text)
        },
        equipment=habitation.usable_lines(
            line.strip() for line in text.splitlines() if line.strip()
        ),
    )


@dataclass
class Product:
    """One RP campervan: a range at one drivetrain."""

    manufacturer_range: str
    drivetrain: str
    url: str
    rrp_pounds: int | None = None
    mtplm_kilograms: int | None = None
    mh_length_mm: int | None = None
    mh_width_mm: int | None = None
    mh_height_mm: int | None = None
    width_including_mirrors_mm: int | None = None
    equipment: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return f"{self.manufacturer_range} {self.drivetrain}"


def _products(brochure: RangeBrochure) -> list[Product]:
    drawing = brochure.drawing
    return [
        Product(
            manufacturer_range=brochure.manufacturer_range,
            drivetrain=drivetrain,
            url=brochure.url,
            rrp_pounds=brochure.prices.get(drivetrain),
            mtplm_kilograms=brochure.gross_weights.get(drivetrain),
            mh_length_mm=drawing.length_mm if drawing else None,
            mh_width_mm=drawing.width_mm if drawing else None,
            mh_height_mm=drawing.height_for(drivetrain) if drawing else None,
            width_including_mirrors_mm=(
                drawing.width_including_mirrors_mm if drawing else None
            ),
            equipment=brochure.equipment,
        )
        for drivetrain in DRIVETRAINS
    ]


def _reconciles(product: Product) -> tuple[bool, str]:
    """**Structural, because RP publish no payload to check the masses against.**

    Every model's payload reads `TBC`, and no mass in running order appears in either
    brochure, so the arithmetic every stronger adapter here leans on does not exist. What
    can be verified is that each figure came from the right part of the spread: a price
    above what any option on the page costs, a gross weight in the band a Sprinter is
    plated in, and a body width narrower than the figure across the mirrors.
    """
    if product.rrp_pounds is None:
        return False, "no price was read for this drivetrain from the Technical Data spread"
    if product.mtplm_kilograms is None:
        return False, "no gross vehicle weight was read for this drivetrain"
    if not 3000 <= product.mtplm_kilograms <= 5500:
        return False, (
            f"{product.mtplm_kilograms}kg is outside what a Sprinter is plated at, so the "
            f"GVW row has been misread"
        )
    if (
        product.mh_width_mm is not None
        and product.width_including_mirrors_mm is not None
        and product.mh_width_mm >= product.width_including_mirrors_mm
    ):
        return False, (
            f"the body width {product.mh_width_mm}mm is not narrower than the "
            f"{product.width_including_mirrors_mm}mm across the mirrors, so the two have "
            f"been taken the wrong way round"
        )
    return True, (
        f"£{product.rrp_pounds:,} and {product.mtplm_kilograms}kg, both from the brochure's "
        f"own Technical Data spread rather than from the options priced beside it"
    )


#: How each habitation reading is introduced.
_FEATURE_NOTES: dict[str, str] = {
    "heating": "the heating in the brochure's own specification",
    "refrigeration": "the refrigeration in the brochure's own specification",
    "microwave": "a microwave in the brochure's own specification",
    "shower_toilet_separated": "the washroom as the brochure describes it",
}


def build_extracted(product: Product, *, basis: str) -> ExtractedMotorhome:
    """One RP campervan, with provenance on everything it proposes."""
    features = habitation.features_from(product.equipment)
    features.pop("bed_types", None)

    body_type, body_type_reason = body_type_for(product.mh_height_mm)
    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.manufacturer_range,
        model=product.drivetrain,
        base_vehicle_manufacturer=fmlv_base_vehicle("Mercedes"),
        rrp_pounds=product.rrp_pounds,
        price_min_range_pounds=product.rrp_pounds,
        mtplm_kilograms=product.mtplm_kilograms,
        mh_length_mm=product.mh_length_mm,
        mh_width_mm=product.mh_width_mm,
        mh_height_mm=product.mh_height_mm,
        body_type=body_type,
        # **Deliberately absent.** The payload reads `TBC` on every model and neither
        # brochure publishes a mass in running order, so FMLV's own figures stand.
        mro_kilograms=None,
        mh_payload_kilograms=None,
        # Not proposed either: the tiles state the belts and the beds as bare digits that
        # run into the figure beside them in the extracted text — `2.9m2 2` — so neither
        # can be read reliably. FMLV holds 2 and 2 on all four.
        berths=None,
        mh_passenger_seats_inc_driver=None,
    )
    for name, feature in features.items():
        setattr(motorhome, name, feature.value)

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=product.url, snippet=f"{product.label} — {snippet}"
        )

    record(
        "manufacturer_range",
        f'range "{product.manufacturer_range}", the brochure this came from',
    )
    record(
        "model",
        f'model "{product.drivetrain}", the drivetrain. FMLV splits these as family plus '
        f"drivetrain, which is how RP market them",
    )
    if product.rrp_pounds is not None:
        record("rrp_pounds", f"£{product.rrp_pounds:,}. {basis}")
        record(
            "price_min_range_pounds",
            f"£{product.rrp_pounds:,} — the brochure's headline price for this drivetrain, "
            f"before the options listed beneath it",
        )
    if product.mtplm_kilograms is not None:
        record(
            "mtplm_kilograms",
            f"{product.mtplm_kilograms}kg GVW, from the Technical Data tile row. The "
            f"heavier plates offered beside it are priced options, so the base is recorded",
        )
    if product.mh_length_mm is not None:
        record(
            "mh_length_mm",
            f"{product.mh_length_mm}mm, from the scale drawing. NOT the summary tile: the "
            f"Rebel's tiles read 5.9m and 7.0m where both its drawings say 5932mm, so the "
            f"tile is wrong and the drawing is what FMLV already holds",
        )
    if product.mh_width_mm is not None:
        record(
            "mh_width_mm",
            f"{product.mh_width_mm}mm body width. The drawing also gives "
            f"{product.width_including_mirrors_mm}mm across the mirrors, which FMLV does "
            f"not record",
        )
    if product.mh_height_mm is not None:
        record(
            "mh_height_mm",
            f"{product.mh_height_mm}mm, from the scale drawing — assigned to the "
            f"{product.drivetrain} by height rather than by position, since an all-wheel-"
            f"drive Sprinter sits higher on the same body and the drawings' own captions "
            f"run in the opposite order to their figures",
        )
    if body_type is not None:
        record("body_type", body_type_reason)
    for name, feature in features.items():
        provenance[name] = Provenance(
            source_url=product.url,
            snippet=(
                f"{product.label} — {feature.note or _FEATURE_NOTES.get(name, name)}: "
                f"{feature.snippet!r}"
            ),
        )
    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


def _notes(brochure: RangeBrochure) -> Iterable[str]:
    """What the brochure offered that is deliberately not recorded."""
    if brochure.drawing and brochure.drawing.length_mm is None:
        yield (
            f"[{brochure.manufacturer_range}] NO LENGTH IS PROPOSED: its two drawings give "
            f"different lengths and nothing can say which belongs to which model — the "
            f"summary tiles cannot arbitrate, having already been shown wrong"
        )
    for name, price in brochure.special_editions.items():
        reason = SPECIAL_EDITION.get(name)
        yield (
            f"[{brochure.manufacturer_range}] SPECIAL EDITION NOT COLLECTED: "
            f"{name} at £{price:,}. "
            + (reason or "No technical data is published for it, so it cannot be built")
        )


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 — plain HTML and plain PDFs throughout
    snapshot_dir: Path,  # noqa: ARG001 — `http` already snapshots into it
    *,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every RP campervan, from the 2027 brochure each range page links."""
    results: list[ExtractedMotorhome] = []
    for manufacturer_range, path in RANGE_PATHS.items():
        page = http.fetch(f"{BASE_URL}{path}")
        if page.status_code != 200:
            on_progress(f"[{manufacturer_range}] SKIPPED: {path} returned {page.status_code}")
            continue
        url = find_brochure_url(page.file_path.read_text(encoding="utf-8", errors="replace"))
        if url is None:
            on_progress(
                f"[{manufacturer_range}] SKIPPED: {path} links no brochure PDF, and the "
                f"prices are in the brochure and nowhere else on this site"
            )
            continue

        document = http.fetch(url)
        if document.status_code != 200:
            on_progress(
                f"[{manufacturer_range}] SKIPPED: {url} returned {document.status_code}"
            )
            continue
        try:
            text = extract_text(document.file_path).text
        except Exception as error:  # noqa: BLE001 — a bad PDF costs one range, not the run
            on_progress(f"[{manufacturer_range}] SKIPPED: its brochure would not parse — {error}")
            continue

        brochure = parse_range_brochure(text, manufacturer_range=manufacturer_range, url=url)
        if brochure.drawing is None:
            on_progress(
                f"[{manufacturer_range}] its Technical Data drawings did not give the "
                f"{_DRAWING_FIGURE_COUNT} figures expected, so no dimension is proposed for "
                f"either model. The price and the GVW are unaffected"
            )
        on_progress(
            f"[{manufacturer_range}] read its Technical Data spread: "
            f"{len(brochure.prices)} price(s), {len(brochure.gross_weights)} gross weight(s)"
        )

        for product in _products(brochure):
            reconciles, basis = _reconciles(product)
            if not reconciles:
                on_progress(f"[{product.label}] DROPPED: {basis}")
                continue
            results.append(build_extracted(product, basis=basis))
            on_progress(
                f"[{product.label}] read: £{product.rrp_pounds:,}, "
                f"{product.mtplm_kilograms}kg, "
                f"{product.mh_length_mm}x{product.mh_width_mm}x{product.mh_height_mm}mm"
            )
        for note in _notes(brochure):
            on_progress(note)

    on_progress(
        "NO PAYLOAD AND NO MASS IN RUNNING ORDER IS PROPOSED. Every model's payload reads "
        "'TBC' in the 2027 brochures, footnoted that it depends on the habitation options "
        "chosen, and neither brochure publishes a mass in running order at all — only the "
        "GVW. FMLV's own figures for both carry through untouched."
    )
    on_progress(
        "NO BERTHS OR SEATS ARE PROPOSED. The tiles state them as bare digits that run into "
        "the figure beside them in the extracted text — '2.9m2 2' — so neither can be read "
        "reliably. FMLV holds 2 berths and 2 seats on all four."
    )
    on_progress(
        "THERE IS NO ARITHMETIC SELF-CHECK, which is worth knowing. With no payload and no "
        "mass in running order published there is nothing to test a parse against; the "
        "check here is structural."
    )
    if len(results) != EXPECTED_PRODUCTS:
        on_progress(
            f"expected {EXPECTED_PRODUCTS} products and collected {len(results)} — check "
            f"whether a range or a drivetrain has changed"
        )
    on_progress(f"collected {len(results)} RP Motorhomes campervan(s)")
    return results
