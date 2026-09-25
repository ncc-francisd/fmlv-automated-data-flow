"""Auto-Sleepers — 18 layouts from a UK site that publishes everything, and labels it.

`docs/adapters/auto-sleepers.md` is the survey; this is what it decided.

The first of six Trigano brands being added together, and the odd one out: the other five
are sold through Marquis Leisure, who define the UK range while a European parent site
defines the numbers. Auto-Sleepers' own UK site defines both, and the requester confirms
*"all models on the website are current in the UK"* — so the sitemap is the roster with no
importer subset to reconcile.

Four things drive the module:

* **The URL carries the body type and the base vehicle**, before the page is read:
  `/<campervans|motorhomes>/<fiat|fiat-active|mercedes>/<model>`. See `_MODEL_URL`.
* **The detailed table is the source and the summary strip is the cross-check**, which is
  the opposite of how the survey first planned it. The 2027 changeover is under way and
  *between two fetches on one day* the Bourton's summary strip lost every value while its
  detailed table stood untouched. The detailed table is also the better-labelled of the
  two. See `_DETAIL_ROW`.
* **The self-check is printed on the page.** `Maximum User Payload (c) (c=a-b)` — so
  `payload == MTPLM - MRO` tests the parse rather than being true by construction, and it
  held on 18 of 18 at survey. See `_reconciles`.
* **The labels move, so match on their stems.** One row was `Maximum Technically
  Permissible Laden Mass (a) (est)` in the morning and `Maximum Permissable Laden Mass (a)
  (est)` in the afternoon — reworded and misspelled in a single edit.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from . import habitation
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

BASE_URL = "https://auto-sleepers.com"
MANUFACTURER = "Auto-Sleepers Limited"
MANUFACTURER_DISPLAY_NAME = "Auto-Sleepers"

#: 325 URLs, of which exactly 18 are model pages. A complete, accurate roster — unusual
#: enough to be worth saying, after Le Voyageur's sitemap described a different country's
#: site and Pilote's carried a broken placeholder.
SITEMAP_URL = f"{BASE_URL}/sitemap.xml"

#: `(<body-type>/<base-vehicle>, label)`. The pair is what `--range` selects on, and it is
#: also the whole of what the URL has to say before the page is fetched.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (
    ("campervans/fiat", "Fiat campervans"),
    ("campervans/fiat-active", "Fiat Active campervans"),
    ("campervans/mercedes", "Mercedes campervans"),
    ("motorhomes/fiat", "Fiat motorhomes"),
    ("motorhomes/mercedes", "Mercedes motorhomes"),
    # Added 25 September 2026. Auto-Sleepers launched the LXV line under URL segments of
    # its own and four products - Broadway EL LXV, Broadway IB LXV, Warwick XL LXV and
    # Kingham LXV - were invisible to the roster until this was here. See `unknown_segments`.
    ("motorhomes/lxv", "LXV motorhomes"),
    ("campervans/lxv-campervans", "LXV campervans"),
)

#: Base vehicle by URL segment. `fiat-active` is still a Fiat; `Active` is Auto-Sleepers'
#: own sub-brand, and FMLV holds it as the *range* rather than as part of the base vehicle.
_BASE_VEHICLES = {
    "fiat": "Fiat",
    "fiat-active": "Fiat",
    # LXV is Auto-Sleepers' luxury line, not a chassis. All four LXV pages state
    # `Fiat Ducato Series 2 chassis` in their own specification.
    "lxv": "Fiat",
    "lxv-campervans": "Fiat",
    "mercedes": "Mercedes",
}

#: The one range name that is not in the page heading.
#:
#: FMLV holds the three Active campervans as range `Active`, models `FG635` / `FL635` /
#: `KB635` — so the range comes from the URL's `fiat-active` segment, not from the `FG 635`
#: heading. The requester corrected these in Nova on 14 September 2026; before that FMLV
#: had them as `FG365 Active` / `FG365`, with the digits transposed.
ACTIVE_RANGE = "Active"

#: How far the printed payload may sit from `MTPLM - MRO` before the product is dropped.
#:
#: Zero, deliberately. Auto-Sleepers publish the subtraction *and* label it `(c=a-b)`, and
#: it held exactly on all 18 layouts at survey with no rounding slack. A mismatch here is
#: a misread row rather than a manufacturer rounding, so there is nothing to be tolerant
#: of. See `_reconciles`.
PAYLOAD_TOLERANCE_KG = 0

#: A campervan taller than this is a high top — the shared NCC threshold.
HIGH_TOP_ABOVE_MM = 2300

# --- Reading the roster ----------------------------------------------------------------

_MODEL_URL = re.compile(
    re.escape(BASE_URL)
    + r"/(?P<body>campervans|motorhomes)"
    # `lxv-campervans` before `lxv`, and `fiat-active` before `fiat`: the alternation
    # is ordered longest-first so the shorter name cannot claim the longer one's URL.
    + r"/(?P<base>fiat-active|fiat|lxv-campervans|lxv|mercedes)"
    # The lookahead, not `$`: this same pattern is run over the whole sitemap with
    # `finditer`, where every URL is followed by `</loc>` rather than by end-of-string.
    # Anchoring on `$` matched nothing and the first run collected zero products.
    + r"/(?P<slug>[a-z0-9-]+)/?(?=<|\s|$)"
)

_TAGS = re.compile(r"(?is)<(script|style)\b.*?</\1>")


def plain_text(page: str) -> str:
    """The page as one line, tags replaced by a single space and entities resolved.

    Entities matter here: the page writes `6445mm / 21&#39;1&quot;`, and a reviewer should
    not be shown the escape sequences.
    """
    stripped = re.sub(r"<[^>]+>", " ", _TAGS.sub(" ", page))
    return re.sub(r"\s+", " ", html.unescape(stripped)).strip()


def find_model_urls(sitemap_xml: str, ranges: Iterable[str]) -> list[str]:
    """Every model page in the sitemap, for the body-type/base-vehicle pairs asked for."""
    wanted = {key.lower() for key in ranges}
    urls: list[str] = []
    for match in _MODEL_URL.finditer(sitemap_xml):
        if f"{match.group('body')}/{match.group('base')}" not in wanted:
            continue
        url = match.group(0).rstrip("/")
        if url not in urls:
            urls.append(url)
    return urls


#: Any `/<body>/<segment>/<slug>` URL, whatever the segment. `find_model_urls` only
#: collects the segments it knows; this finds the ones it does not.
_ANY_MODEL_URL = re.compile(
    re.escape(BASE_URL)
    + r"/(?P<body>campervans|motorhomes)/(?P<base>[a-z0-9-]+)/(?P<slug>[a-z0-9-]+)/?(?=<|\s|$)"
)


def unknown_segments(sitemap_xml: str, ranges: Iterable[str]) -> dict[str, list[str]]:
    """`{body/segment: [urls]}` for product URLs under a segment the roster does not know.

    **This is the check the adapter lacked, and it cost four products.** Auto-Sleepers
    launched their LXV line in its own URL segments - `/motorhomes/lxv/` and
    `/campervans/lxv-campervans/` - and because `_MODEL_URL` listed the segments it knew,
    Broadway EL LXV, Broadway IB LXV, Warwick XL LXV and Kingham LXV were simply not seen.
    Nothing failed; the roster was quietly four short, and stayed that way until the
    requester noticed a mailshot for a model FMLV had never been offered.

    A sitemap that is the roster is only a complete roster if you read all of it.
    """
    wanted = {key.lower() for key in ranges}
    found: dict[str, list[str]] = {}
    for match in _ANY_MODEL_URL.finditer(sitemap_xml):
        key = f"{match.group('body')}/{match.group('base')}"
        if key in wanted:
            continue
        found.setdefault(key, []).append(match.group(0).rstrip("/"))
    return found


# --- Reading one page ------------------------------------------------------------------

#: One row of the detailed specification table: a label cell then a value cell.
_DETAIL_ROW = re.compile(
    r'<div class="cell small-6"><strong>(?P<label>.*?)</strong></div>\s*'
    r'<div class="cell[^"]*">(?P<value>.*?)</div>',
    re.S,
)

#: The page's own heading, which is the model as Auto-Sleepers write it.
_HEADING = re.compile(r"(?is)<h1[^>]*>(?P<name>.*?)</h1>")

#: `Prices from £69,749 OTR` — the manufacturer's headline on-the-road price, which is
#: what `rrp_pounds` wants. No emailed document is needed for any field on this brand.
_PRICE = re.compile(r"Prices\s+from\s*£\s*(?P<price>[\d,]+)", re.I)

#: **Matched on stems, because the labels move.** The same Bourton row was `Maximum
#: Technically Permissible Laden Mass (a) (est)` and then `Maximum Permissable Laden Mass
#: (a) (est)` within one day — reworded and misspelled at once. Anchoring on `Laden Mass
#: (a)` survives both, and the `(a)` / `(b)` / `(c)` markers are the stable part because
#: the page's own arithmetic refers to them.
_LABELS: dict[str, re.Pattern[str]] = {
    "seats": re.compile(r"Designated Passenger Seats", re.I),
    "berths": re.compile(r"Berths \(Sleeping positions\)", re.I),
    "length": re.compile(r"Overall Length", re.I),
    "width": re.compile(r"Overall Width \(mirrors folded\)", re.I),
    "height": re.compile(r"Overall Height Standard Roof", re.I),
    "pop_top_height": re.compile(r"Overall Height Pop Top Roof", re.I),
    "mtplm": re.compile(r"Laden Mass \(a\)", re.I),
    "mro": re.compile(r"Running Order \(b\)", re.I),
    "payload": re.compile(r"User Payload \(c\)", re.I),
}


def _clean(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def detail_rows(page: str) -> dict[str, str]:
    """Every `label -> value` row of the detailed specification table, in page order."""
    rows: dict[str, str] = {}
    for match in _DETAIL_ROW.finditer(page):
        label = _clean(match.group("label"))
        if label and label not in rows:
            rows[label] = _clean(match.group("value"))
    return rows


def _value(rows: dict[str, str], key: str) -> str | None:
    pattern = _LABELS[key]
    for label, value in rows.items():
        if pattern.search(label):
            return value or None
    return None


def _millimetres(value: str | None) -> int | None:
    """`6445mm / 21'1"` -> 6445. The imperial half is ignored."""
    if value is None:
        return None
    match = re.search(r"(\d[\d,]*)\s*mm", value)
    return int(match.group(1).replace(",", "")) if match else None


def _kilograms(value: str | None) -> int | None:
    if value is None:
        return None
    match = re.search(r"(\d[\d,]*)\s*kg", value)
    return int(match.group(1).replace(",", "")) if match else None


def _count(value: str | None) -> int | None:
    if value is None:
        return None
    match = re.search(r"\d+", value)
    return int(match.group(0)) if match else None


def _range_and_model(heading: str, base_segment: str) -> tuple[str, str]:
    """The FMLV range and model, which are not both in the heading.

    FMLV uses two shapes and the page only ever gives one string:

    | heading | base segment | FMLV range | FMLV model |
    |---|---|---|---|
    | `Bourton` | mercedes | `Bourton` | `Bourton` |
    | `Broadway EB` | fiat | `Broadway` | `EB` |
    | `Nuevo EK Plus` | fiat | `Nuevo` | `EK Plus` |
    | `FG 635` | **fiat-active** | **`Active`** | `FG635` |

    So a singleton repeats itself, a family splits on its first word — and the three
    Active campervans take their range from the URL instead, with the heading's space
    closed up to match what FMLV holds.
    """
    name = re.sub(r"\s+", " ", heading).strip()
    if base_segment == "fiat-active":
        return ACTIVE_RANGE, name.replace(" ", "")
    first, _, rest = name.partition(" ")
    return first, rest or first


@dataclass(frozen=True)
class AutoSleepersProduct:
    """One layout, from its own page."""

    source_url: str
    manufacturer_range: str
    model: str
    body_segment: str
    base_segment: str
    mh_passenger_seats_inc_driver: int | None = None
    berths: int | None = None
    mh_length_mm: int | None = None
    mh_width_mm: int | None = None
    mh_height_mm: int | None = None
    mtplm_kilograms: int | None = None
    mro_kilograms: int | None = None
    mh_payload_kilograms: int | None = None
    rrp_pounds: int | None = None
    #: Whether the page states a separate pop-top roof height. See `body_type`.
    has_pop_top: bool = False
    #: The standard-equipment prose, for the habitation findings.
    copy_lines: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        return f"{self.manufacturer_range} {self.model}"

    @property
    def base_vehicle(self) -> str:
        return _BASE_VEHICLES[self.base_segment]

    @property
    def body_type(self) -> BodyType | None:
        """From the URL's body segment, refined by the roof rows the page publishes.

        Every Auto-Sleepers coachbuilt is a low profile — the range has no over-cab bed
        and no A-class. A campervan is a high top above the shared 2300mm threshold, and
        one that also publishes a **pop-top** height has an elevating roof as well, which
        is the distinction FMLV already draws on the three Active vans.
        """
        if self.body_segment == "motorhomes":
            return BodyType.COACH_BUILT_LOW_PROFILE
        if self.mh_height_mm is None:
            return None
        if self.mh_height_mm <= HIGH_TOP_ABOVE_MM:
            return (
                BodyType.CAMPERVAN_ELEVATING_ROOF if self.has_pop_top else BodyType.CAMPERVAN
            )
        return (
            BodyType.CAMPERVAN_HIGH_TOP_ELEVATING_ROOF
            if self.has_pop_top
            else BodyType.CAMPERVAN_HIGH_TOP
        )


def parse_model_page(page: str, source_url: str) -> AutoSleepersProduct | None:
    """One layout from its own page, or `None` if the URL is not a model page."""
    match = _MODEL_URL.match(source_url.rstrip("/") + "/")
    heading = _HEADING.search(page)
    if match is None or heading is None:
        return None

    rows = detail_rows(page)
    manufacturer_range, model = _range_and_model(
        _clean(heading.group("name")), match.group("base")
    )
    price = _PRICE.search(plain_text(page))
    return AutoSleepersProduct(
        source_url=source_url,
        manufacturer_range=manufacturer_range,
        model=model,
        body_segment=match.group("body"),
        base_segment=match.group("base"),
        mh_passenger_seats_inc_driver=_count(_value(rows, "seats")),
        berths=_count(_value(rows, "berths")),
        mh_length_mm=_millimetres(_value(rows, "length")),
        mh_width_mm=_millimetres(_value(rows, "width")),
        mh_height_mm=_millimetres(_value(rows, "height")),
        mtplm_kilograms=_kilograms(_value(rows, "mtplm")),
        mro_kilograms=_kilograms(_value(rows, "mro")),
        mh_payload_kilograms=_kilograms(_value(rows, "payload")),
        rrp_pounds=int(price.group("price").replace(",", "")) if price else None,
        has_pop_top=_value(rows, "pop_top_height") is not None,
        copy_lines=_copy_lines(page),
    )


#: The model copy, which is where the habitation facts are. There is no fittings table:
#: `Essential Habitation Equipment (d) 17kg` in the specification is a **mass allowance**,
#: not an equipment list, and must never be read as one.
_COPY_ITEM = re.compile(r"<li[^>]*>(?P<text>.*?)</li>", re.S)


def _copy_lines(page: str) -> tuple[str, ...]:
    """Every bulleted line of the model's own copy, deduplicated and in page order."""
    lines = [_clean(m.group("text")) for m in _COPY_ITEM.finditer(page)]
    return tuple(dict.fromkeys(line for line in lines if line))


# --- The self-check --------------------------------------------------------------------


def _reconciles(product: AutoSleepersProduct) -> tuple[bool, str]:
    """`(ok, why not)` — whether the page's own printed subtraction holds.

    Auto-Sleepers publish `Maximum User Payload (c) (c=a-b)`, so all three masses are
    stated *and* their relationship is named. That makes this a real check on the parse,
    unlike Joa, Murvi, Le Voyageur or Pilote, where the payload has to be derived and the
    identity is therefore true by construction.

    It held exactly on all 18 layouts at survey, so the tolerance is zero.

    **A failure drops the three masses, not the product.** One URL is one vehicle here, so
    there is no alignment to have gone wrong and no reason to distrust the dimensions or
    the price — the same reasoning as `joa.py` and `le_voyageur.py`. Any product missing
    one of the three passes, having nothing to contradict; `collect` narrates that
    separately.
    """
    masses = (product.mtplm_kilograms, product.mro_kilograms, product.mh_payload_kilograms)
    if any(mass is None for mass in masses):
        return True, ""
    mtplm, mro, payload = masses
    gap = abs((mtplm - mro) - payload)
    if gap <= PAYLOAD_TOLERANCE_KG:
        return True, ""
    return False, (
        f"the page states MTPLM {mtplm}kg, MRO {mro}kg and payload {payload}kg, but its "
        f"own 'c=a-b' gives {mtplm - mro}kg — {gap}kg out"
    )


# --- What reaches the reviewer ---------------------------------------------------------

#: Every published weight carries this, and a reviewer should see that it is the
#: manufacturer's hedge rather than ours.
_ESTIMATE_NOTE = "the page marks every weight '(est)'"


def _build_extracted_motorhome(product: AutoSleepersProduct) -> ExtractedMotorhome:
    """One layout as a `Motorhome`, plus the provenance a reviewer sees beside each field."""
    source_url = product.source_url
    features = habitation.features_from(product.copy_lines)
    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.manufacturer_range,
        model=product.model,
        base_vehicle_manufacturer=fmlv_base_vehicle(product.base_vehicle),
        rrp_pounds=product.rrp_pounds,
        mro_kilograms=product.mro_kilograms,
        mtplm_kilograms=product.mtplm_kilograms,
        mh_payload_kilograms=product.mh_payload_kilograms,
        mh_length_mm=product.mh_length_mm,
        mh_width_mm=product.mh_width_mm,
        mh_height_mm=product.mh_height_mm,
        mh_passenger_seats_inc_driver=product.mh_passenger_seats_inc_driver,
        berths=product.berths,
        body_type=product.body_type,
        # Habitation, from the model's own copy. Findings, never proposals.
        heating=features["heating"].value if "heating" in features else None,
        refrigeration=(
            features["refrigeration"].value if "refrigeration" in features else None
        ),
        shower_toilet_separated=(
            features["shower_toilet_separated"].value
            if "shower_toilet_separated" in features
            else None
        ),
        bed_types=features["bed_types"].value if "bed_types" in features else [],
        microwave=features["microwave"].value if "microwave" in features else None,
    )

    provenance: dict[str, Provenance] = {}

    def record(field: str, snippet: str) -> None:
        provenance[field] = Provenance(
            source_url=source_url, snippet=f"{product.label} — {snippet}"
        )

    if product.mh_length_mm is not None:
        record("mh_length_mm", f"specification table, 'Overall Length {product.mh_length_mm}mm'")
    if product.mh_width_mm is not None:
        record(
            "mh_width_mm",
            f"specification table, 'Overall Width (mirrors folded) {product.mh_width_mm}mm' "
            f"— the mirrors-extended figure beside it is not recorded",
        )
    if product.mh_height_mm is not None:
        record(
            "mh_height_mm",
            f"specification table, 'Overall Height Standard Roof (excl TV aerial) "
            f"{product.mh_height_mm}mm'. FMLV's own figure is 25-35mm larger across the "
            f"range and probably includes the aerial; the requester's ruling on 14 "
            f"September 2026 is to take the site's, so every dimension sits on one "
            f"definition",
        )
    if product.mh_passenger_seats_inc_driver is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"specification table, 'Designated Passenger Seats "
            f"{product.mh_passenger_seats_inc_driver}'",
        )
    if product.berths is not None:
        record("berths", f"specification table, 'Berths (Sleeping positions) {product.berths}'")
    for field, key, value in (
        ("mtplm_kilograms", "Laden Mass (a)", product.mtplm_kilograms),
        ("mro_kilograms", "Mass in Running Order (b)", product.mro_kilograms),
        ("mh_payload_kilograms", "Maximum User Payload (c) (c=a-b)", product.mh_payload_kilograms),
    ):
        if value is not None:
            record(field, f"specification table, '{key}' {value}kg — {_ESTIMATE_NOTE}")
    if product.rrp_pounds is not None:
        record("rrp_pounds", f"'Prices from £{product.rrp_pounds:,} OTR' on the model page")
    record(
        "body_type",
        f"from the site's own path, '{product.body_segment}/{product.base_segment}'"
        + (
            ", and the page publishes a separate pop-top roof height"
            if product.has_pop_top
            else ""
        ),
    )
    record("base_vehicle_manufacturer", f"from the site's own path, '{product.base_segment}'")

    for field, feature in features.items():
        detail = f" — {feature.note}" if feature.note else ""
        provenance[field] = Provenance(
            source_url=source_url,
            snippet=f"{product.label} — the model's copy says {feature.snippet!r}{detail}",
        )

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


# --- The run ---------------------------------------------------------------------------


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 - plain HTTP throughout; no JavaScript on this site
    snapshot_dir: Path,  # noqa: ARG001 - `Fetcher` owns the snapshot directory
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every layout the sitemap lists, for the body-type/base-vehicle pairs asked for."""
    on_progress(f"fetching the sitemap: {SITEMAP_URL}")
    sitemap = http.fetch(SITEMAP_URL)
    if sitemap.status_code != 200:
        message = f"{SITEMAP_URL} returned {sitemap.status_code}; it is the roster"
        raise RuntimeError(message)

    sitemap_xml = sitemap.file_path.read_text(encoding="utf-8", errors="replace")
    urls = find_model_urls(sitemap_xml, (key for key, _label in ranges))
    on_progress(f"{len(urls)} model page(s) in the sitemap")

    # **Read all of the sitemap, not only the parts already known.** The LXV line shipped
    # in URL segments of its own and four products went unseen for weeks, with nothing
    # failing and no count to compare against.
    for segment, missed in sorted(unknown_segments(sitemap_xml, (k for k, _ in ranges)).items()):
        on_progress(
            f"PRODUCTS UNDER AN UNKNOWN URL SEGMENT: the sitemap lists {len(missed)} "
            f"page(s) under '{segment}', which this adapter does not collect - "
            f"{', '.join(u.rsplit('/', 1)[-1] for u in missed)}. If these are vehicles, "
            f"add the segment to DEFAULT_RANGES and _BASE_VEHICLES; they are invisible "
            f"until you do"
        )

    results: list[ExtractedMotorhome] = []
    for url in urls:
        page_result = http.fetch(url)
        if page_result.status_code != 200:
            on_progress(f"SKIPPED: {url} returned {page_result.status_code}")
            continue
        page = page_result.file_path.read_text(encoding="utf-8", errors="replace")

        product = parse_model_page(page, url)
        if product is None:
            on_progress(f"SKIPPED: {url} carries no recognisable heading")
            continue

        reconciles, why_not = _reconciles(product)
        if not reconciles:
            on_progress(
                f"[{product.label}] MASSES DISCARDED and left for FMLV's own figures: "
                f"{why_not}"
            )
            product = replace(
                product,
                mtplm_kilograms=None,
                mro_kilograms=None,
                mh_payload_kilograms=None,
            )

        # The 2027 changeover is republishing these pages one at a time, and a page
        # part-way through states its labels with no values. That must reach a reviewer as
        # a field not found, preserving FMLV's figure, rather than as a blank vehicle.
        absent = [
            name
            for name, value in (
                ("length", product.mh_length_mm),
                ("width", product.mh_width_mm),
                ("height", product.mh_height_mm),
                ("MTPLM", product.mtplm_kilograms),
                ("MRO", product.mro_kilograms),
                ("payload", product.mh_payload_kilograms),
            )
            if value is None
        ]
        if absent:
            on_progress(
                f"[{product.label}] no {', '.join(absent)} on the page, left for FMLV's "
                f"own figures — the 2027 changeover is republishing these pages and one "
                f"part-way through carries its labels with no values"
            )
        if not product.copy_lines:
            on_progress(
                f"[{product.label}] WARNING: no model copy found, so this layout gets no "
                f"habitation findings"
            )

        results.append(_build_extracted_motorhome(product))

    on_progress(f"collected {len(results)} product(s)")
    return results
