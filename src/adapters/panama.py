"""Panama — five Ford-based campervans from a UK site that carries the whole story.

`docs/adapters/panama.md` is the survey; this is what it decided.

Second of six Trigano brands, and **not** the two-source shape the other Marquis ones
have: `panamauk.co.uk` publishes the roster *and* the numbers, so Panama is closer to
Auto-Sleepers than to Benimar.

Four things drive the module:

* **The roster comes from the homepage, not the sitemap.** `sitemap.xml` lists five *other*
  sitemaps — videos, news, events — and no model page at all. See `find_model_urls`.
* **The model name carries a backslash**, and it is a real `U+005C` rather than a rendering
  artefact: `P\\12`, `P\\57`, `P\\10E Hybrid`. FMLV holds two of the three with a forward
  slash instead, which the requester is correcting at upload. It costs nothing in matching
  — the identity tokeniser splits on non-alphanumerics, so `\\12` and `/12` both reduce to
  the same bag.
* **The P\\12 publishes two columns for one vehicle**, and only the first is taken. See
  `_FIRST_COLUMN`.
* **The labels and the escaping vary between sibling pages.** One says `MTPLM (A) kg` and
  four say `MTPLM (A)`; one misspells `Berths (sleeping potitions)`; one leaves its HTML
  entities unescaped where the others do not.
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

BASE_URL = "https://www.panamauk.co.uk"
MANUFACTURER = "Panama"
MANUFACTURER_DISPLAY_NAME = "Panama"

#: **The roster page, because the sitemap is useless here.** `sitemap.xml` names five
#: dynamic sitemaps for videos, news and events and lists no vehicle. The homepage links
#: every model directly.
INDEX_URL = f"{BASE_URL}/"

#: Panama sell one range, which FMLV holds as `P` with the layout in the model.
FMLV_RANGE = "P"

#: Every layout is a Ford Tourneo Custom conversion — stated on each page and matching
#: what FMLV holds for all three of its rows.
BASE_VEHICLE = "Ford"

#: `(slug, label)`. One entry, because Panama have one range and `--range` has nothing
#: finer to select on; kept so the adapter honours the same contract as the others.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (("p", "Panama campervans"),)

#: A campervan taller than this would be a high top. Every Panama is 2000-2070mm, well
#: under it, and every one has a pop-up roof — so all five are elevating-roof campervans,
#: which is what FMLV already holds for its three.
HIGH_TOP_ABOVE_MM = 2300

# --- Reading the roster ----------------------------------------------------------------

#: A model link on the homepage: `/p12`, `/p12-plus`, `/p57`, `/p50-plus`, `/p10-e`.
#: Anchored so `/panama-media`, `/panama-owners` and `/pages-sitemap.xml` cannot match.
_MODEL_HREF = re.compile(
    rf'href="(?:{re.escape(BASE_URL)})?(?P<path>/p\d+(?:-[a-z]+)?|/p\d+-e)"', re.I
)

_TAGS = re.compile(r"(?is)<(script|style)\b.*?</\1>")


def plain_text(page: str) -> str:
    """The page as one line, tags replaced by a single space and entities resolved.

    **Entities are resolved twice over on purpose.** The P\\10E Hybrid page reaches the
    reader still carrying `&#x27;` and `&quot;` where its siblings give real characters,
    so one pass leaves it holding escapes that the others never had.
    """
    stripped = re.sub(r"<[^>]+>", " ", _TAGS.sub(" ", page))
    return re.sub(r"\s+", " ", html.unescape(html.unescape(stripped))).strip()


def find_model_urls(index_html: str, ranges: Iterable[str]) -> list[str]:
    """Every model page the homepage links, in page order, deduplicated."""
    if not list(ranges):
        return []
    urls: list[str] = []
    for match in _MODEL_HREF.finditer(index_html):
        url = f"{BASE_URL}{match.group('path').lower()}"
        if url not in urls:
            urls.append(url)
    return urls


# --- Reading one page ------------------------------------------------------------------

#: The model as Panama write it, from the page title: `P\12 | Panama MPV Campervan`.
_TITLE_NAME = re.compile(r"<title>\s*(?P<name>P.\S*(?:\s+Hybrid)?)\s*\|", re.I)

#: **Stems, because the labels vary between sibling pages.** `MTPLM (A) kg` on the P\12
#: and `MTPLM (A)` on the other four; `sleeping positions` on four and `sleeping potitions`
#: on the P\10E Hybrid. Each pattern stops before the value.
_LABELS: dict[str, re.Pattern[str]] = {
    "seats": re.compile(r"Approved Belted Travel Seats \(including driver\)", re.I),
    "berths": re.compile(r"Berths \(sleeping po[st]itions\)", re.I),
    "length": re.compile(r"Overall Length", re.I),
    "width": re.compile(r"Overall Width \(mirrors folded\)", re.I),
    "height": re.compile(r"Overall Height", re.I),
    "mtplm": re.compile(r"MTPLM \(A\)", re.I),
    "mro": re.compile(r"Mass in Running Order \(B\)", re.I),
    "payload": re.compile(r"Maximum User Payload \(A-B\)", re.I),
}

#: How far into the text after a label to look for its value.
_VALUE_WINDOW = 90

#: `Prices from £61,995 OTR` — Marquis are the sole UK seller, so this is the price that
#: counts by the settled importer rule, and it is on every page.
_PRICE = re.compile(r"Prices\s+from\s*£\s*(?P<price>[\d,]+)", re.I)


def _after_label(text: str, key: str) -> str | None:
    pattern = _LABELS[key]
    match = pattern.search(text)
    if match is None:
        return None
    window = text[match.end() : match.end() + _VALUE_WINDOW]
    return window or None


def _first_millimetres(value: str | None) -> int | None:
    """The **first** `NNNNmm` after a label. See `_FIRST_COLUMN`."""
    if value is None:
        return None
    match = re.search(r"(\d{3,5})\s*mm", value)
    return int(match.group(1)) if match else None


def _first_kilograms(value: str | None) -> int | None:
    if value is None:
        return None
    match = re.search(r"(\d{3,5})\s*kg", value)
    return int(match.group(1)) if match else None


def _first_count(value: str | None) -> int | None:
    if value is None:
        return None
    match = re.search(r"\b(\d{1,2})\b", value)
    return int(match.group(1)) if match else None


#: Why every reader above takes the *first* figure it finds.
#:
#: **The P\\12 page publishes two columns for one FMLV product** — five belted seats
#: against seven, and 2558kg mass in running order against 2630kg, with everything else
#: identical. The other four pages have one column each.
#:
#: The requester's ruling, 14 September 2026: *"we should use the five belted seats version
#: because the seven people seatbelted version is an option — it says on the title."* That
#: is the settled base-vehicle rule, and the first column is the five-seat one, so taking
#: the leading figure everywhere is both correct and uniform.
#:
#: It also means a page that gains a second column later keeps reporting its base vehicle
#: rather than silently switching, which is the safe direction to fail in.
_FIRST_COLUMN = "the first column, which is the base vehicle where a page has two"


@dataclass(frozen=True)
class PanamaProduct:
    """One layout, from its own page."""

    source_url: str
    model: str
    mh_passenger_seats_inc_driver: int | None = None
    berths: int | None = None
    mh_length_mm: int | None = None
    mh_width_mm: int | None = None
    mh_height_mm: int | None = None
    mtplm_kilograms: int | None = None
    mro_kilograms: int | None = None
    #: Only three of the five pages print this; `mro_kilograms` covers the rest.
    published_payload_kilograms: int | None = None
    rrp_pounds: int | None = None
    copy_lines: tuple[str, ...] = ()

    @property
    def manufacturer_range(self) -> str:
        return FMLV_RANGE

    @property
    def label(self) -> str:
        return f"{FMLV_RANGE}{self.model}"

    @property
    def mh_payload_kilograms(self) -> int | None:
        """The printed payload where there is one, else MTPLM minus MRO.

        Panama print `Maximum User Payload (A-B)` on three of the five pages. Where they
        do, `_reconciles` has already checked it against the other two masses; where they
        do not, this derives it and the identity is true by construction.
        """
        if self.published_payload_kilograms is not None:
            return self.published_payload_kilograms
        if self.mtplm_kilograms is None or self.mro_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mro_kilograms

    @property
    def body_type(self) -> BodyType | None:
        """Every Panama is a pop-up-roof campervan below the high-top threshold.

        FMLV holds `campervan_elevating_roof` on all three of its rows, and every page
        lists a `Pop-Up roof bed`, so this is a range fact rather than an inference.
        """
        if self.mh_height_mm is None:
            return None
        return (
            BodyType.CAMPERVAN_HIGH_TOP_ELEVATING_ROOF
            if self.mh_height_mm > HIGH_TOP_ABOVE_MM
            else BodyType.CAMPERVAN_ELEVATING_ROOF
        )


#: Panama's own name for a layout, reduced to what FMLV holds in `model`.
#:
#: The title gives `P\\12`, `P\\12+`, `P\\10E Hybrid`. FMLV splits that into range `P` and
#: model `\\12`, so the leading `P` comes off and the separator stays exactly as Panama
#: write it — a real backslash.
def _model_from_title(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip()[1:]


def parse_model_page(page: str, source_url: str) -> PanamaProduct | None:
    """One layout from its own page, or `None` if the title carries no model name."""
    title = _TITLE_NAME.search(page)
    if title is None:
        return None
    text = plain_text(page)
    price = _PRICE.search(text)
    return PanamaProduct(
        source_url=source_url,
        model=_model_from_title(html.unescape(title.group("name"))),
        mh_passenger_seats_inc_driver=_first_count(_after_label(text, "seats")),
        berths=_first_count(_after_label(text, "berths")),
        mh_length_mm=_first_millimetres(_after_label(text, "length")),
        mh_width_mm=_first_millimetres(_after_label(text, "width")),
        mh_height_mm=_first_millimetres(_after_label(text, "height")),
        mtplm_kilograms=_first_kilograms(_after_label(text, "mtplm")),
        mro_kilograms=_first_kilograms(_after_label(text, "mro")),
        published_payload_kilograms=_first_kilograms(_after_label(text, "payload")),
        rrp_pounds=int(price.group("price").replace(",", "")) if price else None,
        copy_lines=_copy_lines(page),
    )


_COPY_ITEM = re.compile(r"<li[^>]*>(?P<text>.*?)</li>|<p[^>]*>(?P<para>.*?)</p>", re.S)


def _copy_lines(page: str) -> tuple[str, ...]:
    """The model's own prose, which is where the habitation facts are."""
    lines: list[str] = []
    for match in _COPY_ITEM.finditer(_TAGS.sub(" ", page)):
        raw = match.group("text") or match.group("para") or ""
        text = re.sub(r"\s+", " ", html.unescape(html.unescape(re.sub(r"<[^>]+>", " ", raw)))).strip()
        if text:
            lines.append(text)
    return tuple(dict.fromkeys(lines))


# --- The self-check --------------------------------------------------------------------


def _reconciles(product: PanamaProduct) -> tuple[bool, str]:
    """`(ok, why not)` — whether a printed payload agrees with the two masses beside it.

    Panama print `Maximum User Payload (A-B)` on the P\\12+, P\\50+ and P\\10E Hybrid, and
    it was exact on all three at survey. Where it is printed this is a real check on the
    parse; where it is not, there is nothing to check and the payload is derived instead.

    That makes this weaker than Auto-Sleepers, whose every page prints the subtraction, and
    stronger than Joa or Pilote, where nothing does.

    **A failure drops the three masses, not the product** — one URL is one vehicle, so the
    dimensions and the price are not in doubt.
    """
    printed = product.published_payload_kilograms
    if printed is None or product.mtplm_kilograms is None or product.mro_kilograms is None:
        return True, ""
    derived = product.mtplm_kilograms - product.mro_kilograms
    if derived == printed:
        return True, ""
    return False, (
        f"the page states MTPLM {product.mtplm_kilograms}kg, MRO {product.mro_kilograms}kg "
        f"and payload {printed}kg, but its own A-B gives {derived}kg"
    )


# --- What reaches the reviewer ---------------------------------------------------------


def _build_extracted_motorhome(product: PanamaProduct) -> ExtractedMotorhome:
    """One layout as a `Motorhome`, plus the provenance a reviewer sees beside each field."""
    source_url = product.source_url
    features = habitation.features_from(product.copy_lines)
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
        mh_width_mm=product.mh_width_mm,
        mh_height_mm=product.mh_height_mm,
        mh_passenger_seats_inc_driver=product.mh_passenger_seats_inc_driver,
        berths=product.berths,
        body_type=product.body_type,
        # Habitation, from the model's own prose. Findings, never proposals.
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
        record("mh_length_mm", f"'Overall Length ... {product.mh_length_mm}mm', {_FIRST_COLUMN}")
    if product.mh_width_mm is not None:
        record(
            "mh_width_mm",
            f"'Overall Width (mirrors folded) ... {product.mh_width_mm}mm'. **The "
            f"'(inc mirrors) ... 2275mm' figure above it is never recorded** — a column "
            f"mixing folded and extended mirrors would mean nothing",
        )
    if product.mh_height_mm is not None:
        record("mh_height_mm", f"'Overall Height ... {product.mh_height_mm}mm'")
    if product.mh_passenger_seats_inc_driver is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"'Approved Belted Travel Seats (including driver) "
            f"{product.mh_passenger_seats_inc_driver}', {_FIRST_COLUMN}. Where a page "
            f"offers a seven-seat version alongside, that is an option rather than the "
            f"base vehicle",
        )
    if product.berths is not None:
        record("berths", f"'Berths (sleeping positions) {product.berths}'")
    if product.mtplm_kilograms is not None:
        record("mtplm_kilograms", f"'MTPLM (A) {product.mtplm_kilograms}kg', {_FIRST_COLUMN}")
    if product.mro_kilograms is not None:
        record(
            "mro_kilograms",
            f"'Mass in Running Order (B) {product.mro_kilograms}kg', {_FIRST_COLUMN}",
        )
    if product.mh_payload_kilograms is not None:
        record(
            "mh_payload_kilograms",
            f"'Maximum User Payload (A-B) {product.mh_payload_kilograms}kg' as printed"
            if product.published_payload_kilograms is not None
            else f"derived as MTPLM {product.mtplm_kilograms}kg minus MRO "
            f"{product.mro_kilograms}kg — this page prints no payload row",
        )
    if product.rrp_pounds is not None:
        record(
            "rrp_pounds",
            f"'Prices from £{product.rrp_pounds:,} OTR'. Marquis Leisure are the sole UK "
            f"importer and seller, so this is the price that counts",
        )
    record(
        "body_type",
        f"a pop-up roof campervan at {product.mh_height_mm}mm, below the "
        f"{HIGH_TOP_ABOVE_MM}mm high-top threshold"
        if product.mh_height_mm
        else "a pop-up roof campervan",
    )
    record("base_vehicle_manufacturer", "every layout is a Ford Tourneo Custom conversion")

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
    """Every layout the homepage links."""
    on_progress(f"fetching the model index: {INDEX_URL}")
    index = http.fetch(INDEX_URL)
    if index.status_code != 200:
        message = (
            f"{INDEX_URL} returned {index.status_code}; it is the roster, because "
            f"sitemap.xml lists no model pages at all"
        )
        raise RuntimeError(message)

    urls = find_model_urls(
        index.file_path.read_text(encoding="utf-8", errors="replace"),
        (key for key, _label in ranges),
    )
    on_progress(f"{len(urls)} model page(s) linked from the homepage")

    results: list[ExtractedMotorhome] = []
    for url in urls:
        page_result = http.fetch(url)
        if page_result.status_code != 200:
            on_progress(f"SKIPPED: {url} returned {page_result.status_code}")
            continue
        page = page_result.file_path.read_text(encoding="utf-8", errors="replace")

        product = parse_model_page(page, url)
        if product is None:
            on_progress(f"SKIPPED: {url} carries no model name in its title")
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
                published_payload_kilograms=None,
            )
        elif product.published_payload_kilograms is None:
            on_progress(
                f"[{product.label}] no payload row on this page, so it is derived from "
                f"the two masses and nothing corroborates it"
            )

        if not product.copy_lines:
            on_progress(
                f"[{product.label}] WARNING: no model copy found, so this layout gets no "
                f"habitation findings"
            )

        results.append(_build_extracted_motorhome(product))

    on_progress(f"collected {len(results)} product(s)")
    return results
