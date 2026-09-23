"""Carthago motorhomes, read from the per-product pages on carthago.com/en/.

Six A-class ranges and three semi-integrated (low-profile coachbuilt), 76 products, no
campervans and no caravans. Static HTML throughout — no browser.

## A product is a layout, a trim, a weight class and a chassis

Carthago sell one layout as up to four vehicles, and they are genuinely different rather
than options on one product:

| | length | height | MRO |
|---|---|---|---|
| C1-tourer T 143 KB-LE lightweight 3.5 t **Fiat** | 6900 | 2920 | 2943 |
| C1-tourer T 143 KB-LE lightweight 3.5 t **Mercedes** | **7060** | **2950** | **2896** |

FMLV holds all four, distinguished by `base_vehicle_manufacturer` alone — 22 of its 53 live
rows share a range and model with a sibling on another chassis. That is what made the base
vehicle part of a product's identity across the pipeline on 23 September 2026; before it,
those 22 were discarded from the baseline without a word.

**A third chassis the brief did not mention: Iveco.** All three Chic S-plus and two of the
four Liner-for-two are `Iveco Daily`, which FMLV spells `IVECO`.

## Nine range pages, two templates, one of them invisible to the other reader

Eight ranges server-render a card per product, each linking that product's own page. The
**C2-tourer alone** uses `wp-block-carthago-grundrissberater`, whose entire dataset sits
inline in `<script type="application/json" class="cgrb__data">` and which renders no cards
at all — so a card-only reader silently returns **zero** for the largest range in the
line-up, 26 of the 76. Both readers are needed, and `roster_from` tries each.

The range pages are used for nothing else: every product page carries its own identity,
price and full specification.

## The identity comes from the page it was found on, not only its title

Product titles are `C1-tourer T 143 KB-LE lightweight 3.5 t`, and the range is stripped off
the front to leave the model. But **one title drops its layout letter** — the T 148 KB-LE H
is headed `C1-tourer 148 KB-LE H comfort 4.2 t`, where FMLV holds `T 148 KB-LE H comfort
4.2 t` — so the letter comes from the range page instead and is restored when the title has
left it out. `RANGES` carries both the site's spelling and FMLV's for each.

FMLV's ranges are not the site's: it files `C1-tourer T` and `C1-tourer EDITION+ T` under
ranges without the trailing `T`, and its `chic c-line` holds both the A-class `I` models and
the semi-integrated `T 4.9 LE`.

## The prices are sterling, whatever the JSON says

The `cgrb__data` blob labels them `104.500 €` while the rendered page shows `₤104.500` for
the same vehicle, and a product page prints `90.730,- £`. **They are sterling**, and
applying the euro conversion would divide a pound price by 1.15. Three things settle it:
the French site prices all 26 C2-tourer products differently, at a steady ≈1.128; every
configurator link carries `MPL_PREISLISTE=GB`; and FMLV already holds the figure the site
shows. Thousands are separated by a dot and `,-` stands in for the pence.

Only the product page's own price is read, never the range card's, because one product page
states one price and nothing has to be paired up.

## Four fields state a base and an upgrade

`4.250 / 4.500`, `2 / 3`, `4 / 5`, `3125 (3290 2)` — the settled base-vehicle rule takes the
first of each, and for berths the settled lower-figure rule says the same. Footnote 2 on the
mass is `Optional weight increase` in Carthago's own words.

**No payload is published**, so it is `MTPLM − MRO`. There is a `Weight of additional
equipment in series production specified by the manufacturer (kg)`, which is **not** FMLV's
payload — the same trap as Frankia's `Nutzlast`.

## The self-check: a ±5% band on every mass

`Weight in running order (kg) 2.983 (2.834 - 3.132)` — the bracket is the production
tolerance, and 2983 × 0.95 and × 1.05 give it to the kilogram. It verifies the parse per
product with no second document, which matters here because 76 products are read from one
template and a column slipping would be invisible otherwise.

## A parse trap that cost a pass

`Basic vehicle` appears **twice** on every page: first in the range-navigation card, where
its value is a floor-plan count (`Basic vehicle / 2 / Floor plans`), and again in the
technical table where it is `Fiat Ducato`. Reading the first gives `2`. Every label is
therefore looked up inside the technical block, which is anchored on `Type of construction`.
"""

from __future__ import annotations

import html as htmllib
import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from . import habitation
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

__all__ = [
    "BASE_URL",
    "EXPECTED_PRODUCTS",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "RANGES",
    "CarthagoMotorhome",
    "body_type_for",
    "collect",
    "identity_for",
    "parse_price",
    "parse_technical_data",
    "roster_from",
    "visible_lines",
]

BASE_URL = "https://www.carthago.com"

#: The NCC list spells the manufacturer `Carthago`; the supplier list adds `Motorhomes`.
#: Both are right — one name per company per role.
MANUFACTURER = "Carthago"
MANUFACTURER_DISPLAY_NAME = "Carthago"

#: Carthago's own claim: each range overview card states a `Floor plans` count, and the
#: nine add to exactly this.
EXPECTED_PRODUCTS = 76


@dataclass(frozen=True)
class _Range:
    """One range page, and the identity FMLV files its products under."""

    slug: str
    #: `a-class-motorhomes` or `semi-integrated-motorhomes`, which is only the URL.
    family: str
    #: How a product title spells the series, so it can be stripped off the front.
    site_series: str
    #: What FMLV holds. Deliberately not derived: FMLV drops the trailing `T` and files
    #: the A-class and semi-integrated `chic c-line` under one range.
    fmlv_range: str
    #: `I` for an A-class, `T` for a semi-integrated. Restored when a title omits it.
    letter: str

    @property
    def url(self) -> str:
        return f"{BASE_URL}/en/motorhomes/{self.family}/{self.slug}/"


_A_CLASS = "a-class-motorhomes"
_SEMI = "semi-integrated-motorhomes"

RANGES: tuple[_Range, ...] = (
    _Range("c1-tourer-edition", _A_CLASS, "C1-tourer Edition+", "C1-tourer Edition+", "I"),
    _Range("c2-tourer", _A_CLASS, "C2-tourer", "C2-tourer", "I"),
    _Range("chic-c-line", _A_CLASS, "chic c-line", "chic c-line", "I"),
    _Range("chic-e-line", _A_CLASS, "chic e-line", "chic e-line", "I"),
    _Range("chic-s-plus", _A_CLASS, "chic s-plus", "chic s-plus", "I"),
    _Range("liner-for-two", _A_CLASS, "liner-for-two", "liner-for-two", "I"),
    _Range("c1-tourer-edition-t", _SEMI, "C1-tourer Edition+", "C1-tourer Edition+", "T"),
    _Range("c1-tourer-t", _SEMI, "C1-tourer", "C1-tourer", "T"),
    _Range("chic-c-line-t", _SEMI, "chic c-line", "chic c-line", "T"),
)

_DROP = re.compile(r"<(script|style|noscript|svg)\b.*?</\1>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")


def visible_lines(page_html: str) -> list[str]:
    """Every non-empty run of visible text, in document order."""
    text = _TAG.sub("\n", _DROP.sub(" ", page_html))
    out: list[str] = []
    for raw in text.split("\n"):
        line = re.sub(r"\s+", " ", htmllib.unescape(raw)).strip()
        if line:
            out.append(line)
    return out


# --- the roster -----------------------------------------------------------------------

_CARD_LINK = re.compile(
    r'href="(https://www\.carthago\.com/en/motorhomes/[^"]*?/)\?cgrb_return'
)
_BLOB = re.compile(r'<script[^>]*class="cgrb__data"[^>]*>(.*?)</script>', re.S | re.I)


def roster_from(page_html: str, config: _Range) -> list[tuple[str, str | None]]:
    """Every product page this range links, as `(url, chassis)`, by either template.

    The JSON blob is preferred where it exists because it is the component's own data, and
    because **it names the chassis where the URL does not**: eight C2-tourer permalinks end
    `-2` and say nothing about the base vehicle, which on this manufacturer is half a
    product's identity. The card ranges all spell it in the URL.

    **A range that yields nothing is a template change, not an empty range** — `collect`
    says so rather than quietly collecting 50 products instead of 76.
    """
    blob = _BLOB.search(page_html)
    if blob is not None:
        data = json.loads(htmllib.unescape(blob.group(1)))
        found: dict[str, str | None] = {}
        for entry in data.get("models", []):
            link = entry.get("permalink")
            if link:
                found[link] = _chassis_from_label(entry.get("basisfahrzeugLabel"))
        if found:
            return sorted(found.items())

    links = {
        htmllib.unescape(link)
        for link in _CARD_LINK.findall(page_html)
        if f"/{config.slug}/" in link
    }
    return sorted((link, chassis_from_url(link)) for link in links)


# --- identity -------------------------------------------------------------------------

#: The chassis, as the product page's URL slug ends. FMLV shouts `IVECO`.
_CHASSIS_IN_SLUG: tuple[tuple[str, str], ...] = (
    ("mercedes-benz", "Mercedes"),
    ("fiat-ducato", "Fiat"),
    ("iveco-daily", "IVECO"),
    ("iveco", "IVECO"),
)


def _chassis_from_label(label: str | None) -> str | None:
    """`Fiat Ducato 8)` -> `Fiat`, `Mercedes-Benz Sprinter` -> `Mercedes`.

    The JSON states the base vehicle for every entry, footnote markers and all.
    """
    if not label:
        return None
    lowered = label.casefold()
    for needle, make in _CHASSIS_IN_SLUG:
        if needle.split("-")[0] in lowered:
            return make
    return None


def chassis_from_url(url: str) -> str | None:
    """`...-lightweight-3-5-t-2-fiat-ducato/` -> `Fiat`.

    Read from the URL rather than the page because it is the one place every product
    states it unambiguously — the technical table's `Basic vehicle` shares its label with
    a navigation card, and the range card states it only as an icon class.
    """
    tail = url.rstrip("/").rsplit("/", 1)[-1]
    for needle, make in _CHASSIS_IN_SLUG:
        if tail.endswith(needle):
            return make
    return None


def identity_for(title: str, config: _Range) -> tuple[str, str] | None:
    """`(manufacturer_range, model)` from a product page's title.

    The range is stripped off the front and the layout letter restored if the title has
    dropped it — the T 148 KB-LE H is headed `C1-tourer 148 KB-LE H comfort 4.2 t` where
    every sibling carries its `T`, and FMLV holds the `T`.
    """
    name = re.sub(r"\s*[-–]\s*Carthago\s*$", "", title).strip()
    lowered, series = name.casefold(), config.site_series.casefold()
    if not lowered.startswith(series):
        return None

    model = name[len(config.site_series) :].strip()
    if not model:
        return None
    if not re.match(rf"{config.letter}\b", model):
        model = f"{config.letter} {model}"
    return config.fmlv_range, model


# --- the technical block --------------------------------------------------------------

#: Anchors the block. Unique on a product page, where `Basic vehicle` is not.
_ANCHOR = "Type of construction"

_LABELS = (
    "Lightweight / Comfort",
    "Type of construction",
    "Basic vehicle",
    "Transmission",
    "Length / width / height (mm)",
    "Technically permissible gross vehicle weight (kg)",
    "Weight in running order (kg)",
    "Max. number of seats with 3-point safety belt while driving standard / optional",
    "Sleeping berths standard / optional",
    "Rear garage interior height (mm)",
    "Refrigerator volume / of which freezer compartment (l)",
    "Heating system",
)


def parse_technical_data(lines: list[str]) -> dict[str, str]:
    """The technical table as `{label: value}`, read only inside its own block.

    **Anchored on `Type of construction`**, because `Basic vehicle` appears earlier on
    every page as a navigation card whose value is a floor-plan count. Reading labels
    document-wide gives that page a base vehicle of `2`.
    """
    if _ANCHOR not in lines:
        return {}
    start = max(0, lines.index(_ANCHOR) - 4)
    block = lines[start : start + 90]

    found: dict[str, str] = {}
    for i, line in enumerate(block):
        if line in _LABELS and line not in found and i + 1 < len(block):
            found[line] = block[i + 1]
    return found


_FOOTNOTE = re.compile(r"\d\)")


def _dimensions(lines: list[str]) -> tuple[int | None, int | None, int | None]:
    """Length, width and height, which run across several lines and carry footnotes.

    The page states `6900 / 2270 1) / 2920` as three visible runs, and the Chic S-plus
    adds a second height as `3125 (3290 2)`. Footnote markers are stripped, the parts
    split on `/`, and the first number of each taken — the base figure, never the
    bracketed alternative.
    """
    label = "Length / width / height (mm)"
    if label not in lines:
        return None, None, None
    start = lines.index(label) + 1
    joined = " ".join(lines[start : start + 5])
    joined = _FOOTNOTE.sub(" ", joined)
    parts = joined.split("/")

    out: list[int | None] = []
    for part in parts[:3]:
        digits = re.search(r"(\d{3,5})", part.replace(".", ""))
        out.append(int(digits.group(1)) if digits else None)
    while len(out) < 3:
        out.append(None)
    return out[0], out[1], out[2]


def _first_number(value: str | None) -> int | None:
    """The first figure of a `standard / optional` pair, dots stripped.

    `4.250 / 4.500` is 4250 and `2 / 3` is 2 — the base vehicle and the lower berth count,
    which the settled rules ask for separately and agree on here.
    """
    if not value:
        return None
    match = re.search(r"(\d[\d.]*)", value)
    if match is None:
        return None
    return int(match.group(1).replace(".", ""))


_MASS_BAND = re.compile(r"(\d[\d.]*)\s*\(\s*(\d[\d.]*)\s*[-–]\s*(\d[\d.]*)\s*\)")


def parse_running_order(value: str | None) -> tuple[int | None, tuple[int, int] | None]:
    """`2.983 (2.834 - 3.132)` -> `(2983, (2834, 3132))`.

    The bracket is the ±5% production tolerance Carthago print with every mass, and it is
    this adapter's self-check.
    """
    if not value:
        return None, None
    band = _MASS_BAND.search(value)
    if band is None:
        return _first_number(value), None
    base, low, high = (int(x.replace(".", "")) for x in band.groups())
    return base, (low, high)


_PRICE = re.compile(r"(\d[\d.]*)\s*(?:,-)?\s*£")


def parse_price(lines: list[str]) -> int | None:
    """The product page's own price, in pounds.

    `90.730,- £` — dot thousands, `,-` for the pence. **Sterling despite the JSON's euro
    label**; see the module docstring. Only the value under this page's own `Price` label
    is read, so nothing has to be paired to a card.
    """
    for i, line in enumerate(lines):
        if line != "Price" or i + 1 >= len(lines):
            continue
        match = _PRICE.match(lines[i + 1])
        if match:
            return int(match.group(1).replace(".", ""))
    return None


# --- body type ------------------------------------------------------------------------

#: Carthago state the body style outright, so nothing is derived from a height. The
#: coachbuilts are all low profile — confirmed by the requester, 23 September 2026.
_BODY_TYPES: tuple[tuple[str, BodyType], ...] = (
    ("a class", BodyType.A_CLASS),
    ("a-class", BodyType.A_CLASS),
    ("integrated", BodyType.A_CLASS),
    ("coachbuilt", BodyType.COACH_BUILT_LOW_PROFILE),
    ("semi-integrated", BodyType.COACH_BUILT_LOW_PROFILE),
)


def body_type_for(construction: str | None) -> tuple[BodyType | None, str]:
    """The body style, from `Type of construction` — stated, not derived."""
    if not construction:
        return None, "the page states no type of construction"
    lowered = construction.casefold()
    for needle, body_type in _BODY_TYPES:
        if needle in lowered:
            return body_type, (
                f'Type of construction: "{construction}". Carthago state the body style '
                f"outright, so it is not derived from a height"
            )
    return None, f'no body style is known for "{construction}"'


# --- the product ----------------------------------------------------------------------


@dataclass(frozen=True)
class CarthagoMotorhome:
    """One product page, read."""

    config: _Range
    url: str
    manufacturer_range: str
    model: str
    chassis: str | None
    fields: dict[str, str]
    lines: list[str]

    @property
    def label(self) -> str:
        chassis = f" {self.chassis}" if self.chassis else ""
        return f"{self.manufacturer_range} {self.model}{chassis}"

    @property
    def mtplm_kilograms(self) -> int | None:
        return _first_number(
            self.fields.get("Technically permissible gross vehicle weight (kg)")
        )

    @property
    def mro_kilograms(self) -> int | None:
        return parse_running_order(self.fields.get("Weight in running order (kg)"))[0]

    @property
    def tolerance_band(self) -> tuple[int, int] | None:
        return parse_running_order(self.fields.get("Weight in running order (kg)"))[1]

    @property
    def derived_payload_kilograms(self) -> int | None:
        if self.mtplm_kilograms is None or self.mro_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mro_kilograms

    @property
    def berths(self) -> int | None:
        return _first_number(self.fields.get("Sleeping berths standard / optional"))

    @property
    def travel_seats(self) -> int | None:
        return _first_number(
            self.fields.get(
                "Max. number of seats with 3-point safety belt while driving "
                "standard / optional"
            )
        )


def _reconciles(product: CarthagoMotorhome) -> tuple[bool, str]:
    """`(ok, reason)` — does the published ±5% band match the mass it brackets?

    Carthago print `2.983 (2.834 - 3.132)` with every mass in running order, so the parse
    is checkable per product without a second document. A product that fails is **dropped
    with a warning**, never proposed: 76 products come off one template, and a column
    slipping would otherwise produce plausible motorhomes carrying each other's weights.
    """
    mro, band = product.mro_kilograms, product.tolerance_band
    if mro is None:
        return False, "the page states no weight in running order"
    if product.mtplm_kilograms is None:
        return False, "the page states no permissible gross weight"
    if band is None:
        return True, (
            f"mass in running order {mro}kg; the page prints no tolerance band to check "
            f"it against"
        )
    low, high = band
    if abs(round(mro * 0.95) - low) <= 1 and abs(round(mro * 1.05) - high) <= 1:
        return True, (
            f"mass in running order {mro}kg, and the page's own ±5% production band "
            f"({low}-{high}kg) brackets it exactly"
        )
    return False, (
        f"mass in running order reads {mro}kg but the page's ±5% band is "
        f"{low}-{high}kg, which brackets {round((low + high) / 2)}kg — the parse has "
        f"taken figures from different rows"
    )


def build_extracted(product: CarthagoMotorhome, *, mass_basis: str) -> ExtractedMotorhome:
    """The product and a provenance line for every field it proposes."""
    length_mm, width_mm, height_mm = _dimensions(product.lines)
    construction = product.fields.get("Type of construction")
    body_type, body_reason = body_type_for(construction)
    price = parse_price(product.lines)
    features = habitation.features_from(product.lines)

    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.manufacturer_range,
        model=product.model,
        base_vehicle_manufacturer=fmlv_base_vehicle(product.chassis),
        mh_length_mm=length_mm,
        mh_width_mm=width_mm,
        mh_height_mm=height_mm,
        berths=product.berths,
        mh_passenger_seats_inc_driver=product.travel_seats,
        mtplm_kilograms=product.mtplm_kilograms,
        mro_kilograms=product.mro_kilograms,
        mh_payload_kilograms=product.derived_payload_kilograms,
        rrp_pounds=price,
        body_type=body_type,
        rear_garage="Rear garage interior height (mm)" in product.fields or None,
        heating=features["heating"].value if "heating" in features else None,
        refrigeration=features["refrigeration"].value if "refrigeration" in features else None,
        microwave=features["microwave"].value if "microwave" in features else None,
    )

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=product.url, snippet=f"{product.label} — {snippet}"
        )

    # Both halves of the identity, always: `compare_fields` walks only fields carrying
    # provenance, and accepting a range change without its model corrupts the name.
    record(
        "manufacturer_range",
        f'range "{product.manufacturer_range}", as the {product.config.slug} page groups '
        f"this product — accept with the model, they are one name",
    )
    record(
        "model",
        f'model "{product.model}" — accept with the range, they are one name',
    )
    if motorhome.base_vehicle_manufacturer is not None:
        record(
            "base_vehicle_manufacturer",
            f"{product.chassis}, from this product's own URL. **The chassis is part of "
            f"the identity here**: Carthago sell this layout on more than one, and the "
            f"two are different vehicles with different lengths, masses and prices",
        )

    if length_mm is not None:
        record("mh_length_mm", f"Length / width / height: {length_mm}mm long")
    if width_mm is not None:
        record(
            "mh_width_mm",
            f"Length / width / height: {width_mm}mm wide, the body figure — the page's "
            f"footnote adds the wheel arches separately",
        )
    if height_mm is not None:
        record("mh_height_mm", f"Length / width / height: {height_mm}mm high")
    if product.berths is not None:
        record(
            "berths",
            f'Sleeping berths standard / optional: '
            f'{product.fields.get("Sleeping berths standard / optional")} — the '
            f"standard figure, per the settled rule that a berth range takes the lower",
        )
    if product.travel_seats is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"Max. number of seats with 3-point safety belt: "
            f"{product.fields.get(
                'Max. number of seats with 3-point safety belt while driving '
                'standard / optional'
            )}. Carthago state three-point in so many words, which is the settled rule",
        )
    if product.mtplm_kilograms is not None:
        record(
            "mtplm_kilograms",
            f"Technically permissible gross vehicle weight: "
            f'{product.fields.get("Technically permissible gross vehicle weight (kg)")} '
            f"— the first figure, the base vehicle. The second is Carthago's own "
            f"optional weight increase",
        )
    if product.mro_kilograms is not None:
        record("mro_kilograms", f"Weight in running order: {mass_basis}")
    if product.derived_payload_kilograms is not None:
        record(
            "mh_payload_kilograms",
            f"payload {product.derived_payload_kilograms}kg, derived as MTPLM less MRO. "
            f"Carthago publish no payload; their 'weight of additional equipment in "
            f"series production' is a different figure and is not recorded",
        )
    if price is not None:
        record(
            "rrp_pounds",
            f"Price: {price:,} — STERLING, despite the range page's JSON labelling it "
            f"in euro. The French site prices the same vehicles ~12.8% higher and every "
            f"configurator link asks for the GB price list",
        )
    if body_type is not None:
        record("body_type", body_reason)
    if motorhome.rear_garage:
        record(
            "rear_garage",
            f"Rear garage interior height: "
            f'{product.fields.get("Rear garage interior height (mm)")}',
        )
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
    """Every Carthago the UK site publishes.

    **85 fetches** — nine range pages for the roster, then one per product. Easily the
    largest of any adapter here, and worth knowing before a run.
    """
    roster: list[tuple[_Range, str, str | None]] = []
    for config in RANGES:
        on_progress(f"fetching {config.url}")
        page = http.fetch(config.url).file_path.read_text(encoding="utf-8", errors="replace")
        links = roster_from(page, config)
        if not links:
            on_progress(
                f"NO PRODUCTS FOUND on {config.url}. This range links none by either "
                f"reader — the card markup or the cgrb__data JSON — which means "
                f"its template has changed, not that the range is empty. Its products "
                f"cannot be collected this run"
            )
            continue
        on_progress(f"  {config.slug}: {len(links)} product(s)")
        roster.extend((config, link, chassis) for link, chassis in links)

    on_progress(f"roster: {len(roster)} products across {len(RANGES)} ranges")

    extracted: list[ExtractedMotorhome] = []
    dropped: list[str] = []
    #: Products whose page carries no technical table at all. Kept apart from a parse
    #: failure because the two mean opposite things to a reviewer: one is a page Carthago
    #: have not finished, the other is this adapter getting it wrong.
    stubs: list[str] = []
    unpriced: list[str] = []
    no_chassis: list[str] = []

    for config, url, chassis in roster:
        try:
            lines = visible_lines(
                http.fetch(url).file_path.read_text(encoding="utf-8", errors="replace")
            )
        except Exception as error:  # noqa: BLE001
            dropped.append(f"{url} ({type(error).__name__})")
            on_progress(f"dropping {url} — could not fetch it ({type(error).__name__})")
            continue

        identity = identity_for(lines[0] if lines else "", config)
        if identity is None:
            dropped.append(url)
            on_progress(
                f"dropping {url} — its title {lines[0] if lines else '(empty)'!r} does "
                f"not begin with the {config.site_series!r} series, so no model name can "
                f"be read from it"
            )
            continue

        manufacturer_range, model = identity
        product = CarthagoMotorhome(
            config=config,
            url=url,
            manufacturer_range=manufacturer_range,
            model=model,
            chassis=chassis,
            fields=parse_technical_data(lines),
            lines=lines,
        )
        if chassis is None:
            no_chassis.append(product.label)

        # **A page with no technical table is still a product.** The T 148 KB-LE H pages
        # publish nothing at all — no weights, no dimensions, no price — and dropping them
        # left their FMLV rows unclaimed, which is worse than it sounds: the matcher gave
        # 8899 and 8904 to two unmatched *C2-tourer* products and proposed renaming a
        # C1-tourer into one. Emitting the identity alone claims the row, proposes no
        # field, and leaves FMLV's own figures standing.
        if not product.fields:
            stubs.append(product.label)
            extracted.append(build_extracted(product, mass_basis=""))
            on_progress(
                f"read {product.label}: identity only — its page publishes no technical "
                f"table"
            )
            continue

        reconciles, reason = _reconciles(product)
        if not reconciles:
            dropped.append(product.label)
            on_progress(f"dropping {product.label} — {reason}")
            continue

        if parse_price(lines) is None:
            unpriced.append(product.label)

        extracted.append(build_extracted(product, mass_basis=reason))
        on_progress(
            f"read {product.label}: {product.mtplm_kilograms}kg, "
            f"{product.derived_payload_kilograms}kg payload, {product.berths} berth, "
            f"{product.travel_seats} belted seats"
        )

    if stubs:
        on_progress(
            f"NO FIGURES PUBLISHED, so none are proposed: {', '.join(stubs)}. Carthago "
            f"list these and they have a page, but the page carries NO TECHNICAL TABLE AT "
            f"ALL — no weights, no dimensions, no price. They are collected on their "
            f"identity alone so that they match their FMLV rows and nothing is overwritten; "
            f"every field will show as not found this run. They are not discontinued and "
            f"must not be deactivated — the pages are unfinished"
        )

    if no_chassis:
        on_progress(
            f"NO CHASSIS READ for {', '.join(no_chassis)}. The base vehicle comes from the "
            f"product URL's last segment, so a URL that stops naming it leaves these "
            f"products indistinguishable from their siblings on another chassis"
        )
    if unpriced:
        on_progress(
            f"NO PRICE PROPOSED for {', '.join(unpriced)}. No POA is invented and FMLV's "
            f"own figures stand"
        )

    on_progress(
        "PRICES ARE STERLING. The range page's JSON labels them in euro and the rendered "
        "page shows a pound sign for the same number; the French site prices the same "
        "vehicles about 12.8% higher, every configurator link carries MPL_PREISLISTE=GB, "
        "and FMLV already holds the figure this site shows. No conversion is applied"
    )
    on_progress(
        "THE CHASSIS IS PART OF THE IDENTITY. Carthago sell one layout on up to three base "
        "vehicles and FMLV holds each as its own row, distinguished by that column alone. "
        "Two products here sharing a range and model are not duplicates"
    )

    if len(extracted) != EXPECTED_PRODUCTS:
        on_progress(
            f"expected {EXPECTED_PRODUCTS} products and collected {len(extracted)} "
            f"— check whether the range has really changed"
            + (f"; dropped {len(dropped)}" if dropped else "")
        )
    on_progress(f"collected {len(extracted)} Carthago motorhome(s)")
    return extracted
