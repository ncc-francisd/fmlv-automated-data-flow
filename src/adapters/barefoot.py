"""Barefoot Caravans (go-barefoot.co.uk) — one fibreglass shell, six interiors.

See `docs/adapters/barefoot.md` for the survey. **The catalogue is the source**, and
page 10 of it is a real specification table covering the whole range at once: berths,
axles, the two masses, the published payload, and below them a dimension block. Its
figures are FMLV's exactly on all four products FMLV already holds, so this document is
demonstrably where they came from.

**Three further fetches, each for one thing the catalogue does not carry:**

* `/vital-statistics/` — the **internal length**, 3560mm, which the catalogue omits and
  FMLV holds.
* `/barefoot-caravan-prices/` — the prices, which the catalogue omits entirely.
* each model's own page — the habitation findings, which only the two new models publish.

**The range repeats the model**, per the single-name convention in
`docs/adapters/README.md`: FMLV files the Classic as range `Classic`, model `Classic`,
because Nova will not take a blank.

## Every mass is published as a pair, and the lower one is the product

`750/850`, `1000/1100`, `1100/1200` — *"the MTPLM towing weight can be specified as 750 or
850kg (specify at time of order)"*. That is an option at the point of order, so the base
vehicle is the lower of the two and the payload follows the same choice. The requester
settled it on 8 October 2026, and FMLV already holds 1100 rather than 1200.

## The self-check is real, and the catalogue fails it once

`MTPLM - MRO` must equal the printed `Maximum User Payload`, and the table prints all
three for every column. It holds on three columns and fails on the **Lite**, where
`1100/1200` against an MRO of 900 gives 200/300 rather than the printed 100/200 — out by
exactly 100 on *both* members of the pair, which is a column error rather than a typo.
The Lite's own page settles which figure is wrong: *"The tow weight is just 1,000kg"*. So
`ERRATA` rewrites that one cell, and everything downstream — the self-check included —
runs on the corrected pair.

## The columns are read from the table's own headings

Neither block hardcodes which model sits in which column. The specification header
introduces each column with the word `Barefoot`, and the dimension header separates models
*within* a column with a comma or an ampersand and models in *different* columns with
nothing at all. Both are parsed, so a seventh model appearing in either block is picked up
rather than silently mapped onto its neighbour's weights — which is the failure
`docs/adapters/README.md` warns is invisible downstream.
"""

from __future__ import annotations

import html as htmllib
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from src.adapters import habitation
from src.adapters.base import ExtractedCaravan, Provenance
from src.fetch.browser import BrowserFetcher
from src.fetch.http import Fetcher
from src.fetch.pdf import extract_text
from src.product_model.caravan import Caravan
from src.product_model.enums import CaravanBodyType
from src.vehicle_class import VehicleClass

__all__ = [
    "BASE_URL",
    "ERRATA",
    "EXPECTED_MODELS",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "MICRO_MAX_MTPLM_KG",
    "MODEL_PAGES",
    "PRICES_URL",
    "VEHICLE_CLASS",
    "VITAL_STATISTICS_URL",
    "Specification",
    "body_type_for",
    "build_extracted",
    "catalogue_url",
    "collect",
    "internal_length_from",
    "parse_dimensions",
    "parse_specifications",
    "prices_from",
    "spec_lines",
]

BASE_URL = "https://www.go-barefoot.co.uk"
MANUFACTURER = "Barefoot Caravans"
MANUFACTURER_DISPLAY_NAME = "Barefoot"
VEHICLE_CLASS = VehicleClass.CARAVAN

VITAL_STATISTICS_URL = f"{BASE_URL}/vital-statistics/"
PRICES_URL = f"{BASE_URL}/barefoot-caravan-prices/"

#: Six on the site's own navigation — Bothy, Lite, Eclipse, Classic, Forward and Country
#: Living — of which FMLV holds four. Compared against the collected count so a column
#: quietly dropped by a changed heading is reported rather than read as a discontinuation.
EXPECTED_MODELS = 6

#: Where a model's own page lives, for the habitation findings. Only the two new models
#: publish a fittings list; the four older pages carry prose and navigation alone. That
#: costs nothing, because findings are recorded for new products only and the new products
#: are exactly those two.
MODEL_PAGES: dict[str, str] = {
    "Bothy": "/barefoot-bothy/",
    "Lite": "/barefoot-lite/",
    "Classic": "/barefoot-classic/",
    "Forward": "/barefoot-forward/",
    "Eclipse": "/barefoot-eclipse/",
    "Country Living": "/country-living-barefoot/",
}

#: A cell the catalogue prints wrong, keyed by `(model, row)` and **applied only when the
#: published value is still the wrong one**, so it lapses of its own accord the day
#: Barefoot fix it rather than quietly overwriting a corrected figure.
#:
#: The Lite is the only entry. The catalogue's MTPLM column reads `1100/1200`, which
#: against its MRO of 900 gives a payload of 200/300 where the same table prints 100/200 —
#: wrong by 100 on both members of the pair, which is a column error rather than a typo.
#: `/barefoot-lite/` settles it: *"The tow weight is just 1,000kg"*, and 1000/1100
#: reconciles exactly.
ERRATA: dict[tuple[str, str], tuple[str, str]] = {
    ("Lite", "mtplm"): ("1100/1200", "1000/1100"),
}

#: Applied rather than asserted, per `docs/adapters/README.md` — `wingamm_caravan.py`
#: found the brand that breaks the usual answer by asserting it.
MICRO_MAX_MTPLM_KG = 1250

#: Where a model page's own content stops and the site furniture starts. The fittings list
#: and the footer navigation are the same markup, so without this the Bothy's thirty-odd
#: fittings arrive followed by "Home", "Gallery" and "Contact".
_PAGE_FURNITURE = re.compile(
    r"field is for validation|^(?:Home|Email|URL|LinkedIn|Facebook|Contact)$", re.I
)


# --- The catalogue's specification table ---------------------------------------------

#: The specification block's rows, as `(label, key)`. Every one carries one cell per
#: column, and a row that does not is dropped rather than guessed at.
_SPEC_ROWS: tuple[tuple[str, str], ...] = (
    (r"Berth", "berths"),
    (r"Axles", "axles"),
    (r"Weight \(MTPLM\*\), kg", "mtplm"),
    (r"Weight \(MRO\*\*\), kg", "mro"),
    (r"Maximum User Payload\*\*\*, kg", "payload"),
)

#: The dimension block's rows, as `(label, field)`. Each cell is a millimetre figure
#: followed by the same measurement in feet and inches, which is discarded.
_DIMENSION_ROWS: tuple[tuple[str, str], ...] = (
    (r"Overall Length", "shipping_length_mm"),
    (r"Overall Width", "overall_width_mm"),
    (r"External Height", "height_mm"),
    (r"Body Length \(shell\)", "exterior_body_length_mm"),
    (r"Internal Height", "headroom_mm"),
)


def _column_models(heading: str) -> list[str]:
    """One specification column's heading as the model names in it.

    `Classic, Forward & Eclipse` is three models sharing a column; `x Country Living` is
    one, the `x` being the collaboration's own branding rather than part of the name.
    """
    names: list[str] = []
    for part in re.split(r",|&", heading):
        name = " ".join(part.replace("\n", " ").split())
        name = re.sub(r"^x\s+", "", name).strip()
        if name:
            names.append(name)
    return names


def _spec_columns(page_text: str) -> list[list[str]] | None:
    """Which models sit in which specification column, read from the table's own heading.

    The heading introduces every column with the word **Barefoot** — `Specification
    Barefoot Bothy Barefoot Lite Barefoot Classic, Forward & Eclipse Barefoot x Country
    Living` — so splitting on it gives the columns in order, and nothing about the roster
    has to be known in advance.
    """
    match = re.search(
        r"^Specification\s+Barefoot\b(?P<rest>.*?)(?=^Berth\b)", page_text, re.M | re.S
    )
    if match is None:
        return None
    columns = [
        _column_models(heading) for heading in re.split(r"\bBarefoot\b", match.group("rest"))
    ]
    columns = [column for column in columns if column]
    return columns or None


def _dimension_columns(page_text: str, roster: Iterable[str]) -> list[list[str]] | None:
    """Which models share which dimension column, by how their names are punctuated.

    The dimension heading lists every model in one run — `Classic, Eclipse, Country
    Living, Forward, Lite Bothy` — and the only thing marking the column boundary is the
    **absence** of a separator: names within a column are divided by a comma or an
    ampersand, names in different columns by nothing at all.
    """
    # Deliberately **not** `[^\n]*` after the label: the heading wraps mid-column, so
    # consuming its first line swallows the models printed on it. That left the shared
    # column reading `Forward, Lite` and the Classic with no dimensions at all.
    match = re.search(
        r"^Dimensions in mm(?P<rest>.*?)(?=^Overall Length\b)", page_text, re.M | re.S
    )
    if match is None:
        return None
    heading = " ".join(match.group("rest").split())
    found: list[tuple[int, int, str]] = []
    # Longest first, so `Country Living` is found rather than a bare `Country`.
    for name in sorted(roster, key=len, reverse=True):
        for hit in re.finditer(rf"\b{re.escape(name)}\b", heading):
            if any(start < hit.end() and hit.start() < end for start, end, _ in found):
                continue
            found.append((hit.start(), hit.end(), name))
    found.sort()
    if not found:
        return None
    columns: list[list[str]] = [[found[0][2]]]
    for (_, previous_end, _), (start, _, name) in zip(found, found[1:]):
        if re.search(r"[,&]", heading[previous_end:start]):
            columns[-1].append(name)
        else:
            columns.append([name])
    return columns


def _cells(page_text: str, label: str, count: int) -> list[str] | None:
    """One row's cells, or `None` unless there are exactly `count` of them.

    A row whose cell count disagrees with the heading's column count is **dropped rather
    than aligned by guesswork** — the misalignment `docs/adapters/README.md` calls
    invisible downstream, because every figure it produces is plausible.
    """
    cells = r"\s+".join([r"(\S+)"] * count)
    match = re.search(rf"^{label}\s+{cells}\s*$", page_text, re.M)
    return list(match.groups()) if match else None


def _dimension_cells(page_text: str, label: str, count: int) -> list[int] | None:
    """One dimension row, discarding the feet-and-inches repeat of each figure."""
    cell = r"(\d[\d,]*)\s*\([^)]*\)"
    match = re.search(rf"^{label}\s+{' +'.join([cell] * count)}\s*$", page_text, re.M)
    if match is None:
        return None
    return [int(value.replace(",", "")) for value in match.groups()]


def _lower(cell: str) -> int | None:
    """The base figure of a published pair. `750/850` is 750; `960` is 960."""
    cleaned = cell.strip().rstrip("*")
    if not cleaned or cleaned.upper() in {"N/A", "-"}:
        return None
    parts = [part for part in cleaned.split("/") if part.strip()]
    try:
        return min(int(part.replace(",", "")) for part in parts)
    except ValueError:
        return None


@dataclass
class Specification:
    """One model, assembled from the catalogue's two blocks and the pages beside them."""

    model: str
    berths: int | None = None
    twin_axle: bool | None = None
    mtplm_kilograms: int | None = None
    mro_kilograms: int | None = None
    published_payload_kilograms: int | None = None
    #: What the catalogue printed before `ERRATA`, kept so the narration can say so.
    published_mtplm_cell: str | None = None
    corrected_mtplm_cell: str | None = None
    shipping_length_mm: int | None = None
    exterior_body_length_mm: int | None = None
    overall_width_mm: int | None = None
    height_mm: int | None = None
    headroom_mm: int | None = None
    internal_length_mm: int | None = None
    rrp_pounds: int | None = None
    equipment: list[str] = field(default_factory=list)

    @property
    def derived_payload_kilograms(self) -> int | None:
        if self.mtplm_kilograms is None or self.mro_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mro_kilograms


def parse_specifications(page_text: str) -> list[Specification]:
    """The specification block: berths, axles and the three masses, column by column."""
    columns = _spec_columns(page_text)
    if columns is None:
        return []
    rows: dict[str, list[str]] = {}
    for label, key in _SPEC_ROWS:
        cells = _cells(page_text, label, len(columns))
        if cells is not None:
            rows[key] = cells

    found: list[Specification] = []
    for index, models in enumerate(columns):
        for model in models:
            spec = Specification(model=model)
            if (berths := rows.get("berths")) is not None:
                spec.berths = _lower(berths[index])
            if (axles := rows.get("axles")) is not None:
                spec.twin_axle = axles[index].strip().lower() not in {"single", "1"}
            if (mtplm := rows.get("mtplm")) is not None:
                published = mtplm[index].strip()
                correction = ERRATA.get((model, "mtplm"))
                cell = correction[1] if correction and correction[0] == published else published
                spec.published_mtplm_cell = published
                spec.corrected_mtplm_cell = cell
                spec.mtplm_kilograms = _lower(cell)
            if (mro := rows.get("mro")) is not None:
                spec.mro_kilograms = _lower(mro[index])
            if (payload := rows.get("payload")) is not None:
                spec.published_payload_kilograms = _lower(payload[index])
            found.append(spec)
    return found


def parse_dimensions(page_text: str, roster: Iterable[str]) -> dict[str, dict[str, int]]:
    """The dimension block, as `{model: {field: millimetres}}`."""
    columns = _dimension_columns(page_text, roster)
    if columns is None:
        return {}
    figures: dict[str, dict[str, int]] = {}
    for label, name in _DIMENSION_ROWS:
        cells = _dimension_cells(page_text, label, len(columns))
        if cells is None:
            continue
        for index, models in enumerate(columns):
            for model in models:
                figures.setdefault(model, {})[name] = cells[index]
    return figures


# --- The three pages the catalogue does not cover -------------------------------------


def catalogue_url(home_html: str) -> str | None:
    """The catalogue's address, **read from the home page rather than constructed**.

    Its folder carries a year — `uploads/2025/10/` — so the URL moves with each edition.
    """
    hrefs = [
        htmllib.unescape(href) for href in re.findall(r'href="([^"]+\.pdf)"', home_html, re.I)
    ]
    if not hrefs:
        return None
    href = next((candidate for candidate in hrefs if "cat" in candidate.lower()), hrefs[0])
    return href if href.startswith("http") else f"{BASE_URL}/{href.lstrip('/')}"


def _flatten(page_html: str) -> str:
    """A page as one line of text, every tag become a `|` separator."""
    body = re.sub(r"(?is)<(script|style|head)\b.*?</\1>", " ", htmllib.unescape(page_html))
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", body))
    return re.sub(r"(?:\s*\|\s*)+", " | ", text)


def internal_length_from(page_html: str) -> int | None:
    """The internal length off `/vital-statistics/`, which is a label-then-value list.

    The catalogue gives every other dimension and not this one, and FMLV holds 3560 — so
    this page is the source for it, and that is the only reason the fetch exists.
    """
    match = re.search(r"\bInternal length\b[^\d]{0,20}(\d{3,5})", _flatten(page_html), re.I)
    return int(match.group(1)) if match else None


def prices_from(page_html: str, roster: Iterable[str]) -> dict[str, int]:
    """The price per model, from the prices page's own sentences.

    Each sentence names its models and then its price — *"Barefoot Classic, Barefoot
    Forward, Barefoot Eclipse – all £39,950"*. Only models named **before** the first price
    in a sentence are taken, which is what keeps the payment terms out (*"£15,000 (£10,000
    for Bothy) payment required..."* names its model afterwards) and the `Barefoot and Go`
    accessory bundle too, since that sentence names none at all before its £41,500.

    A model given two different prices is dropped rather than arbitrated.
    """
    names = sorted(roster, key=len, reverse=True)
    prices: dict[str, int] = {}
    contested: set[str] = set()
    for sentence in _flatten(page_html).split("|"):
        match = re.search(r"£\s?([\d,]{4,})", sentence)
        if match is None:
            continue
        price = int(match.group(1).replace(",", ""))
        remaining = sentence[: match.start()]
        for name in names:
            if not re.search(rf"\b{re.escape(name)}\b", remaining):
                continue
            remaining = re.sub(rf"\b{re.escape(name)}\b", " ", remaining)
            if prices.get(name, price) != price:
                contested.add(name)
            prices[name] = price
    for name in contested:
        prices.pop(name, None)
    return prices


def spec_lines(page_html: str) -> list[str]:
    """A model page's fittings, stopping where the page's own content stops.

    The fittings list and the site's footer navigation are the same markup, so without the
    cut the Bothy's thirty-odd fittings arrive followed by `Home` and `Gallery`.
    """
    # `nav`, `header` and `footer` go too, and that is the whole trick: the site's menus
    # are lists of exactly the same markup and they come *first* in the document, so
    # without this the furniture cut fires on the first item and the page reads as empty.
    stripped = re.sub(r"(?is)<(script|style|head|nav|header|footer)\b.*?</\1>", " ", page_html)
    lines: list[str] = []
    for item in habitation.list_items(stripped):
        text = " ".join(htmllib.unescape(item).split())
        if _PAGE_FURNITURE.search(text):
            break
        if text:
            lines.append(text)
    return lines


# --- Judgement ------------------------------------------------------------------------


def body_type_for(site_text: str, mtplm: int | None) -> tuple[CaravanBodyType, str]:
    """`type_rigid` unless Barefoot *name* a micro and the weight allows one.

    Both halves are needed, and here only one is met: every Barefoot is under the weight,
    the 1100kg Classic included, but the site's own word throughout is **small caravan**,
    never micro or mini. Asserting rigid outright would be the mistake
    `wingamm_caravan.py` made in the other direction, so the test is applied each run.
    """
    named = re.search(r"\bmicro[- ]?caravan\b|\bmini[- ]caravan\b", site_text, re.IGNORECASE)
    if named and mtplm is not None and mtplm <= MICRO_MAX_MTPLM_KG:
        return CaravanBodyType.MICRO, (
            f"a micro: Barefoot call it {named.group(0)!r} and its permissible mass is "
            f"{mtplm}kg, at or under the {MICRO_MAX_MTPLM_KG}kg the rule allows"
        )
    reason = "a rigid one-piece fibreglass body"
    if mtplm is not None and mtplm <= MICRO_MAX_MTPLM_KG:
        reason += (
            f": at {mtplm}kg it is light enough for a micro, but the rule needs the maker's "
            f"own naming too, and Barefoot's word throughout is 'small caravan'"
        )
    return CaravanBodyType.RIGID, reason


def _reconciles(spec: Specification) -> tuple[bool, str]:
    """`MTPLM - MRO` against the payload the same table prints.

    The strongest kind of self-check there is — the manufacturer publishing the same
    quantity twice — and the one that caught the Lite's MTPLM column. A column read one
    place off breaks it immediately, because no two Barefoots share all three masses.
    """
    mtplm, mro = spec.mtplm_kilograms, spec.mro_kilograms
    published = spec.published_payload_kilograms
    if mtplm is None or mro is None:
        return False, "no permissible mass or no mass in running order"
    if mtplm <= mro:
        return False, f"a {mro}kg mass in running order at or above the {mtplm}kg maximum"
    if published is None:
        return False, "the catalogue printed no user payload to check the masses against"
    derived = mtplm - mro
    if derived != published:
        return False, (
            f"MTPLM {mtplm}kg minus MRO {mro}kg is {derived}kg, where the same table prints "
            f"a maximum user payload of {published}kg"
        )
    return True, (
        f"MTPLM {mtplm}kg minus MRO {mro}kg is {derived}kg, exactly the maximum user "
        f"payload the same table prints"
    )


#: How each habitation reading is introduced. Findings for a person to type in.
_FEATURE_NOTES: dict[str, str] = {
    "heating": "the heating in the model page's own fittings list",
    "refrigeration": "the refrigeration in the model page's own fittings list",
    "microwave": "a microwave in the model page's own fittings list",
    "shower_toilet_separated": "the washroom as the model page's fittings list describes it",
    "bathroom_layout": "the washroom as the model page's fittings list describes it",
}


def build_extracted(spec: Specification, *, basis: str, catalogue: str) -> ExtractedCaravan:
    """One Barefoot as a `Caravan`, with provenance on everything it proposes."""
    features = habitation.features_from(spec.equipment)
    # Dropped for the same reason as on every other caravan adapter: the copy names beds
    # without saying which are built in and which are made up from the seating.
    features.pop("bed_types", None)

    body_type, body_reason = body_type_for(" ".join(spec.equipment), spec.mtplm_kilograms)
    payload = spec.derived_payload_kilograms
    caravan = Caravan(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        # The range repeats the model: this product has one name, Nova will not take a
        # blank, and FMLV files all four of its existing Barefoots that way.
        manufacturer_range=spec.model,
        model=spec.model,
        berths=spec.berths,
        rrp_pounds=spec.rrp_pounds,
        price_min_range_pounds=spec.rrp_pounds,
        mtplm_kilograms=spec.mtplm_kilograms,
        mro_kilograms=spec.mro_kilograms,
        personal_effects_payload_kilograms=payload,
        optional_equipment_payload_kilograms=None,
        internal_length_mm=spec.internal_length_mm,
        exterior_body_length_mm=spec.exterior_body_length_mm,
        shipping_length_mm=spec.shipping_length_mm,
        overall_width_mm=spec.overall_width_mm,
        height_mm=spec.height_mm,
        headroom_mm=spec.headroom_mm,
        body_type=body_type,
        twin_axle=bool(spec.twin_axle),
    )
    for name, feature in features.items():
        setattr(caravan, name, feature.value)

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str, *, source: str = catalogue) -> None:
        provenance[field_name] = Provenance(
            source_url=source, snippet=f"Barefoot {spec.model} — {snippet}"
        )

    record(
        "manufacturer_range",
        f'range "{spec.model}", repeating the model: this product has one name, and Nova '
        f"will not take a blank range",
    )
    if spec.berths is not None:
        record("berths", f"{spec.berths} berths, from the catalogue's 'Berth' row")
    for name, label in (
        ("shipping_length_mm", "Overall Length"),
        ("exterior_body_length_mm", "Body Length (shell)"),
        ("overall_width_mm", "Overall Width"),
        ("height_mm", "External Height"),
        ("headroom_mm", "Internal Height"),
    ):
        value = getattr(caravan, name)
        if value is not None:
            record(name, f"{value}mm, from the catalogue's '{label}' row")
    if spec.internal_length_mm is not None:
        record(
            "internal_length_mm",
            f"{spec.internal_length_mm}mm — the catalogue publishes no internal length, and "
            f"this is the one figure taken from Vital Statistics. Every Barefoot shares the "
            f"one shell, which the catalogue's own dimension block confirms",
            source=VITAL_STATISTICS_URL,
        )
    if spec.mtplm_kilograms is not None:
        pair = spec.corrected_mtplm_cell or ""
        upgrade = (
            f", the lower of the {pair} the catalogue publishes — the heavier figure is "
            f"specified at the time of order, so the base caravan is this one"
            if "/" in pair
            else ""
        )
        corrected = (
            f". The catalogue prints {spec.published_mtplm_cell} here, which against the "
            f"mass in running order gives a payload 100kg larger than the one it prints in "
            f"the next row; /barefoot-lite/ says 'The tow weight is just 1,000kg', and "
            f"{pair} reconciles exactly"
            if spec.corrected_mtplm_cell != spec.published_mtplm_cell
            else ""
        )
        record("mtplm_kilograms", f"{spec.mtplm_kilograms}kg{upgrade}{corrected}")
    if spec.mro_kilograms is not None:
        record("mro_kilograms", f"{spec.mro_kilograms}kg, from the catalogue's MRO row")
    if payload is not None:
        record(
            "personal_effects_payload_kilograms",
            f"{payload}kg — {basis}. Barefoot publish one payload and no optional-equipment "
            f"allowance, so the whole of it is recorded as personal effects",
        )
        record(
            "optional_equipment_payload_kilograms",
            "Barefoot publish no optional-equipment allowance, so the whole payload is "
            "recorded as personal effects",
        )
    if spec.rrp_pounds is not None:
        record(
            "rrp_pounds",
            f"£{spec.rrp_pounds:,} including VAT, from the prices page",
            source=PRICES_URL,
        )
        record(
            "price_min_range_pounds",
            f"£{spec.rrp_pounds:,} — Barefoot publish one price per model, not a range",
            source=PRICES_URL,
        )
    record("body_type", body_reason)
    record(
        "twin_axle",
        ("twin axles" if caravan.twin_axle else "a single axle")
        + ", from the catalogue's 'Axles' row",
    )
    for name, feature in features.items():
        provenance[name] = Provenance(
            source_url=f"{BASE_URL}{MODEL_PAGES.get(spec.model, '/')}",
            snippet=(
                f"Barefoot {spec.model} — {feature.note or _FEATURE_NOTES.get(name, name)}: "
                f"{feature.snippet!r}"
            ),
        )
    return ExtractedCaravan(caravan=caravan, provenance=provenance)


def collect(
    http: Fetcher,
    browser: BrowserFetcher,  # noqa: ARG001
    snapshot_dir: Path,  # noqa: ARG001
    *,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedCaravan]:
    """Every Barefoot, from the catalogue and the three pages beside it."""
    home = http.fetch(f"{BASE_URL}/").file_path.read_text(encoding="utf-8", errors="replace")
    url = catalogue_url(home)
    if url is None:
        msg = f"no catalogue PDF linked from {BASE_URL}/ — the only source of the figures is gone"
        raise RuntimeError(msg)
    on_progress(f"reading the catalogue: {url}")

    result = http.fetch(url)
    if result.status_code != 200:
        msg = f"the catalogue at {url} returned {result.status_code}"
        raise RuntimeError(msg)

    # Page by page, never the joined text: the dimension block repeats row labels the
    # specification block uses, and a document-wide search would pair them wrongly.
    page_text = next(
        (
            page.text
            for page in extract_text(result.file_path).pages
            if "Maximum User Payload" in page.text
        ),
        None,
    )
    if page_text is None:
        msg = f"no specification table found in the catalogue at {url}"
        raise RuntimeError(msg)

    specs = parse_specifications(page_text)
    if not specs:
        msg = (
            f"the catalogue's specification heading at {url} no longer reads 'Specification "
            f"Barefoot ...', so which model owns which column cannot be told"
        )
        raise RuntimeError(msg)
    roster = [spec.model for spec in specs]
    on_progress(f"the catalogue's specification table names {len(roster)}: {', '.join(roster)}")

    dimensions = parse_dimensions(page_text, roster)
    if not dimensions:
        on_progress(
            "NO DIMENSIONS WERE READ — the catalogue's dimension heading has changed shape, "
            "so every length, width and height is left to FMLV's own figures"
        )
    for spec in specs:
        if spec.model not in dimensions:
            on_progress(f"{spec.model} — no dimension column names it, so none is proposed")
            continue
        for name, value in dimensions[spec.model].items():
            setattr(spec, name, value)

    vital = http.fetch(VITAL_STATISTICS_URL).file_path.read_text(
        encoding="utf-8", errors="replace"
    )
    internal_length = internal_length_from(vital)
    if internal_length is None:
        on_progress(
            f"NO INTERNAL LENGTH — {VITAL_STATISTICS_URL} no longer states one and the "
            f"catalogue never did, so FMLV's own figure stands"
        )
    else:
        on_progress(f"internal length {internal_length}mm, from Vital Statistics")
        for spec in specs:
            spec.internal_length_mm = internal_length

    prices = prices_from(
        http.fetch(PRICES_URL).file_path.read_text(encoding="utf-8", errors="replace"), roster
    )
    for spec in specs:
        spec.rrp_pounds = prices.get(spec.model)
        if spec.rrp_pounds is None:
            on_progress(f"{spec.model} — no price found on {PRICES_URL}, so none is proposed")

    for spec in specs:
        path = MODEL_PAGES.get(spec.model)
        if path is None:
            on_progress(f"{spec.model} — no model page is known for it, so no habitation findings")
            continue
        page = http.fetch(f"{BASE_URL}{path}").file_path.read_text(
            encoding="utf-8", errors="replace"
        )
        spec.equipment = habitation.usable_lines(spec_lines(page))
        if not spec.equipment:
            on_progress(
                f"{spec.model} — its page publishes no fittings list, so there are no "
                f"habitation findings to report"
            )
            continue
        stated = set(habitation.features_from(spec.equipment)) - {"bed_types"}
        if not stated:
            on_progress(
                f"{spec.model} — its {len(spec.equipment)} fittings were read and settle no "
                f"habitation field. Barefoot describe the washroom in their own words rather "
                f"than the industry's, and fit a cool box rather than a fridge, so nothing is "
                f"asserted: silence is not a negative"
            )

    results: list[ExtractedCaravan] = []
    for spec in specs:
        reconciles, basis = _reconciles(spec)
        if not reconciles:
            on_progress(f"{spec.model} — DROPPED: {basis}")
            continue
        results.append(build_extracted(spec, basis=basis, catalogue=url))
        on_progress(
            f"{spec.model} — read: {spec.berths} berth, {spec.mtplm_kilograms}kg MTPLM, "
            f"{spec.mro_kilograms}kg MRO, {spec.derived_payload_kilograms}kg payload, "
            f"{spec.shipping_length_mm}mm over the hitch"
        )

    for spec in specs:
        if spec.corrected_mtplm_cell == spec.published_mtplm_cell:
            continue
        on_progress(
            f"{spec.model} — THE CATALOGUE'S MTPLM IS WRONG AND HAS BEEN CORRECTED: it "
            f"prints {spec.published_mtplm_cell}, which does not reconcile with the payload "
            f"printed in the next row; {spec.corrected_mtplm_cell} does, and the model's own "
            f"page says 'The tow weight is just 1,000kg'"
        )
    on_progress(
        "EVERY MASS IS PUBLISHED AS A PAIR and the lower of each is taken — the heavier "
        "figure is specified at the time of order, so the base caravan is the lighter one."
    )
    on_progress(
        "THE BOTHY'S MASS IN RUNNING ORDER IS CONTESTED BY BAREFOOT'S OWN PAGES: the "
        "catalogue and /barefoot-bothy/ both say 706kg, Vital Statistics says 720kg. The "
        "catalogue is taken, being two sources to one and the only figure that reconciles."
    )
    on_progress(
        "NO AWNING LENGTH AND NO LAYOUT DRAWING ARE PUBLISHED ANYWHERE, so FMLV's own awning "
        "figures stand and the positional habitation fields cannot be answered."
    )
    if len(results) != EXPECTED_MODELS:
        on_progress(
            f"expected {EXPECTED_MODELS} models and collected {len(results)} — check whether "
            f"the range has changed"
        )
    on_progress(f"collected {len(results)} Barefoot caravan(s)")
    return results
