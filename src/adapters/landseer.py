"""Landseer — five campervans, read from two 4pp PDFs the site's media library lists.

`docs/adapters/landseer.md` is the survey; this is what it decided.

**Nothing numeric is on the website.** Both model pages are prose — the Artemis's is 79
displayed lines with not one weight on it, and the only `kg` either page prints is a
towing capacity. Everything a buyer would want is in two 4pp A4 PDFs, and the nav links
neither. `MEDIA_URL` finds them: WordPress serves its media library over the REST API
without authentication, and `media_type=application` narrows it to the documents.

Four things make this adapter unlike the others.

* **Take the date from the listing, never from the path, and never hardcode a URL.**
  `57682-Landseer-Artemis-4pp-A4-1.pdf` exists under `/2026/10/` *and* under `/2026/08/`,
  byte-identical in name and different in content. The listing is the only thing that can
  tell the current edition from a superseded one. Landseer reissue roughly every two
  months — ten documents in fifteen months — which is why `documents` picks the newest of
  each kind every run instead of trusting a path.

* **The self-check is a price grid, not mass arithmetic.** No edition Landseer have ever
  published carries a mass in running order or a payload for anything, so the
  `payload == MTPLM - MRO` reconciliation that guards every other adapter does not exist
  here. What the price list does offer is a rectangle that has to close — see
  `price_grid_holds`, and `_reconciles` for the seat count, which is printed twice.

* **The two documents are not equals.** The Custom sheet is a real price list carrying the
  price, the GVW, all three dimensions, the travel seats with their belt type named, the
  heating and the refrigeration. The Artemis brochure is a brochure: a launch price, a base
  vehicle, a long standard-equipment list and an options list, with **no mass, no
  dimension and no berth count anywhere**. So the Artemis is collected for its price, its
  identity and its habitation findings, and left blank everywhere Landseer are silent.

* **`automatic.rrp_pounds` is populated, which no adapter before this one has done.** The
  column exists for a model offered with an automatic, and until now no surveyed
  manufacturer published a separate price for one. Landseer print it as its own priced
  line on every wheelbase. See `_build_extracted_motorhome`.

**No mass in running order and no payload are ever emitted.** Neither is published, so
neither gets provenance, so neither is proposed — which leaves alone the figures FMLV
already holds for the two Custom 2.0 rows (2,400kg / 2,450kg and 775kg), whose source is
not any Landseer document and which this adapter must not blank. That is the settled rule
on unfound specifications in `docs/adapters/README.md`.
"""

from __future__ import annotations

import html as html_module
import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from ..fetch.browser import BrowserFetcher
from ..fetch.http import Fetcher
from ..fetch.pdf import extract_text
from ..product_model.enums import BodyType
from ..product_model.model import AutomaticVariant, Motorhome
from . import gearbox, habitation
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

__all__ = [
    "ARTEMIS",
    "BASE_URL",
    "CUSTOM_2_0",
    "CUSTOM_2_5",
    "DEFAULT_RANGES",
    "EXPECTED_PRODUCTS",
    "LandseerProduct",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "collect",
    "documents",
    "parse_artemis_brochure",
    "parse_pricing_sheet",
    "parse_roster",
    "price_grid_holds",
]

BASE_URL = "https://landseerleisure.com"

#: Byte-for-byte the `manufacturer` value in FMLV's own export — confirmed against the
#: Landseer export of 10 November 2026, which carries `Landseer` on both products.
#:
#: **The NCC supplier dropdown spells it differently**, as `Landseer Leisure`. That string
#: belongs in the registry row's `ncc_supplier_name` and nowhere near this constant: they
#: are two different keys into two different systems, and crossing them means the run
#: finds an empty baseline and proposes all five products as new.
MANUFACTURER = "Landseer"
MANUFACTURER_DISPLAY_NAME = "Landseer"

#: Where the documents are found, since nothing links them.
MEDIA_URL = (
    f"{BASE_URL}/wp-json/wp/v2/media"
    "?per_page=100&media_type=application&_fields=id,source_url,title,date"
)

#: The models index, watched every run by `parse_roster` for a third model page.
MODELS_INDEX_URL = f"{BASE_URL}/campervans"

#: FMLV already files the Ford as range `Custom 2.0` with the wheelbase as the model, so
#: the other two ranges follow that shape: the model is the wheelbase, always.
CUSTOM_2_0 = "Custom 2.0"

#: The PHEV. Landseer print it as `Custom 2.5 - PHEV 232ps 1 Speed Automatic`, a different
#: engine at £13,000 more, and the requester's decision of 10 November 2026 is that it is
#: a product of its own rather than a variant. `PHEV` is kept in the range name because a
#: buyer searches for that word and not for `2.5`.
CUSTOM_2_5 = "Custom 2.5 PHEV"

#: The MAN TGE. New in June 2026 and **not** a rename of anything — see the survey.
ARTEMIS = "Artemis"

#: The Artemis's only wheelbase, used as its model so the product is not `Artemis Artemis`.
#: Landseer name it in two standard lines — the roof rack and the pop-top option are both
#: `for MWB MAN TGE` — and offer no other.
ARTEMIS_MODEL = "MWB"

#: `(key, label)` for `--range`.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (
    ("custom-2-0", CUSTOM_2_0),
    ("custom-2-5-phev", CUSTOM_2_5),
    ("artemis", ARTEMIS),
)

#: Two wheelbases of Custom 2.0, two of Custom 2.5 PHEV, one Artemis. FMLV holds the first
#: two today; the other three are new.
EXPECTED_PRODUCTS = 5

#: Priced lines the pricing sheet must carry: three drivetrains across two wheelbases.
EXPECTED_PRICE_LINES = 6

#: The settled campervan threshold, shared with `aura`, `auto_sleepers` and `auto_trail`.
HIGH_TOP_ABOVE_MM = 2300


# --------------------------------------------------------------------------- #
# Finding the documents
# --------------------------------------------------------------------------- #

#: What a media-library title has to say for the document to be the Artemis brochure.
#: Every edition of it has carried the word and no edition of the pricing sheet has.
_ARTEMIS_TITLE = re.compile(r"\bartemis\b", re.I)


def documents(payload: str) -> dict[str, tuple[str, str, str]]:
    """`{"artemis"|"custom": (url, title, date)}` — the newest edition of each.

    **Classified on the title and not on the five-digit print job number**, although that
    number is the more distinctive key. It is stable across reissues of one job — `57688`
    served the pricing sheet in June, August and October 2026 — but it changes when the job
    is re-set, as `56143` became `57688`, so keying on it would quietly stop finding the
    document at the next reprint. The word `Artemis` has survived every retitling, and the
    pricing sheet is then simply the newest PDF that is not the Artemis.

    That makes the Artemis test the positive one and the pricing sheet the remainder, so a
    *third* model's brochure would be mistaken for a pricing sheet. `collect` guards that
    from two directions: `parse_roster` watches the index for a third model page, and
    `parse_pricing_sheet` raises unless the document it is handed holds a full price grid.
    """
    try:
        items = json.loads(payload)
    except ValueError:
        return {}
    if not isinstance(items, list):
        return {}

    newest: dict[str, tuple[str, str, str]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        url = item.get("source_url")
        if not isinstance(url, str) or not url.lower().endswith(".pdf"):
            continue
        rendered = item.get("title")
        title = rendered.get("rendered") if isinstance(rendered, dict) else rendered
        if not isinstance(title, str):
            continue
        title = " ".join(html_module.unescape(title).split())
        date = item.get("date") if isinstance(item.get("date"), str) else ""
        kind = "artemis" if _ARTEMIS_TITLE.search(title) else "custom"
        if kind in newest and newest[kind][2] >= date:
            continue
        newest[kind] = (url, title, date)
    return newest


#: A link to a model page on the campervans index. Landseer's nav carries exactly two.
_MODEL_LINK = re.compile(r"/campervans/([a-z0-9][a-z0-9-]*)", re.I)

#: Pages under `/campervans/` that sell no vehicle, with what each one is. Watched every
#: run by `parse_roster` so that a page dropping out of here is noticed, never fetched.
NOT_A_MODEL: dict[str, str] = {
    "conversions": (
        "Landseer's bespoke conversion service — 'we welcome the opportunity to convert "
        "your camper to our own high specification'. A body shop, a paint booth, awnings "
        "and accessibility adaptations, with no vehicle, no price and no specification of "
        "its own. The nav lists exactly two camper vans above it, the Custom 2.0 and the "
        "Artemis"
    ),
}

#: The two model pages that are accounted for. Anything else on the index that is not in
#: `NOT_A_MODEL` is a model nobody has surveyed, and `collect` narrates it rather than
#: guessing at it.
KNOWN_MODEL_PAGES: frozenset[str] = frozenset(
    {"ford-custom-landseer", "landseer-artemis"}
)


def parse_roster(index_html: str) -> tuple[str, ...]:
    """Every model-page slug the campervans index links, in first-seen order.

    One page sells **both** Custom wheelbases, which is the whole reason FMLV holds two
    products where the site shows one page. So this counts pages, never products, and
    `collect` uses it only to notice a page nobody has accounted for.
    """
    seen: list[str] = []
    for slug in _MODEL_LINK.findall(index_html):
        lowered = slug.lower()
        if lowered not in seen:
            seen.append(lowered)
    return tuple(seen)


# --------------------------------------------------------------------------- #
# Reading the pricing sheet
# --------------------------------------------------------------------------- #

#: One priced model line.
#:
#: `[^£\n]*` between the wheelbase and the price is not slack for its own sake: the August
#: 2026 edition extracts as `(LWB) °°£81,000`, two stray glyphs where the October edition
#: has none. Anchoring on `£` and skipping whatever sits in front of it reads both.
#:
#: The `Leighton LV-RF™ Edition` line cannot reach this: it names two engines as
#: `Custom 2.0/2.5`, which the engine group will not match, and it carries no wheelbase.
#: That matters, because it is an **option at one price on either vehicle** — £7,000 — and
#: collecting it would invent a sixth Custom.
_PRICE_LINE = re.compile(
    r"(?P<season>20\d{2})\s+Landseer\s+Custom\s+(?P<engine>\d\.\d)\s*[-–—]\s*"
    r"(?P<variant>[^()\n]*?)\s*\((?P<wheelbase>SWB|LWB)\)[^£\n]*£\s*(?P<price>\d[\d,]*)",
    re.I,
)

#: `Dimensions - SWB 5.05m long, LWB 5.45m long, 2.15m wide (mirrors folded), 2.07m high`.
#: One line gives both lengths and the shared width and height.
_DIMENSIONS = re.compile(
    r"Dimensions[^\n]*?\bSWB\s+(?P<swb>\d+(?:\.\d+)?)\s*m\s+long"
    r"[^\n]*?\bLWB\s+(?P<lwb>\d+(?:\.\d+)?)\s*m\s+long"
    r"[^\n]*?(?P<width>\d+(?:\.\d+)?)\s*m\s+wide\s*(?P<width_note>\([^)\n]*\))?"
    r"[^\n]*?(?P<height>\d+(?:\.\d+)?)\s*m\s+high",
    re.I,
)

#: `Maximum GVW SWB 3175kg, LWB 3225kg`. The only mass on the document, and it is a gross
#: vehicle weight: an MTPLM, not a mass in running order.
_GVW = re.compile(
    r"Maximum\s+GVW\s+SWB\s+(?P<swb>[\d,]+)\s*kg[^\n]*?LWB\s+(?P<lwb>[\d,]+)\s*kg", re.I
)

#: `5 travelling seats (upgradable to 7)`. The upgrade is a paid extra and is not counted.
_SEATS = re.compile(r"(?P<seats>\d+)\s+travelling\s+seats", re.I)

#: `with 3 x 3-point safety belts`. Three in the rear, on the Mobiframe bench. **Only
#: three-point belts are counted** — see `docs/adapters/README.md` — and Landseer name the
#: type, so nothing has to be assumed about them.
_REAR_BELTS = re.compile(
    r"(?P<belts>\d+)\s*x\s*3\s*-?\s*point\s+safety\s+belts", re.I
)

#: The base vehicle, from the one line on each document that names the donor van.
_BASE_VEHICLE = re.compile(
    r"high\s+specification\s+(?P<make>Ford|MAN|VW|Volkswagen|Mercedes(?:[- ]Benz)?"
    r"|Peugeot|Fiat|Citro[eë]n|Renault|IVECO)\b",
    re.I,
)

#: An elevating roof fitted as standard. Matched against the **standard** lines only: the
#: Artemis offers a pop-top too, at £9,200, and a paid roof says nothing about the body
#: type of the vehicle as built.
_POP_TOP = re.compile(r"\bpop\s*-?\s*top\b|\belevating\s+roof\b|\brising\s+roof\b", re.I)

#: Where the standard specification stops and the priced extras start. Both documents have
#: one, worded differently. The split is **structural**, which is the stronger of the two
#: guards: `habitation.usable_lines` also drops any line carrying a price, but a standard
#: feature listed without one would otherwise be indistinguishable from an extra.
_OPTIONS_HEADING = re.compile(
    r"^[^\n]*\bOptional\s+(?:extras|upgrades)\b[^\n]*$", re.I | re.M
)

#: The Artemis's price, on the brochure's own pricing panel.
_LAUNCH_PRICE = re.compile(r"LAUNCH\s+PRICING\s*£\s*(?P<price>[\d,]+)", re.I)

#: `Automatic` anywhere in a drivetrain description. Used only to tell the two priced
#: Custom lines apart, never to decide `automatic_available` — `gearbox` does that, from
#: the whole document, with a vocabulary built for the job.
_IS_AUTOMATIC = re.compile(r"\bautomatic\b", re.I)

#: A standard line describing where somebody sleeps, quoted whole into the run narration.
#:
#: **Not a second bed-type vocabulary.** `habitation.bed_types_from` decides the field; this
#: only makes sure the reviewer sees the wording, because that module drops any line
#: carrying the word `mattress` — a sound rule against "bed linen and mattresses" copy that
#: here costs the Artemis its shape, whose only statement is *"Custom Design Premium Memory
#: Foam Mattress – 6' 5" Transverse Bed"*. The field is a finding a person types in, so the
#: fix is to put the sentence in front of them rather than to loosen a filter seventy
#: adapters share.
_BED_LINE = re.compile(r"\bbeds?\b|\bbunks?\b|\bsleep", re.I)

#: A washroom fitting, wherever it is named. Read against the **options** as well as the
#: standard specification, which is the whole point of it: the Custom's shower and toilet
#: are both priced extras, so a buyer's van has neither unless they paid, and FMLV's two
#: existing Custom rows nonetheless carry `rear_shower_toilet`. Narrated, never proposed.
_WASHROOM_LINE = re.compile(r"\bshower\b|\btoilet\b|\bwashroom\b|\bwet\s*room\b", re.I)


def _pounds(raw: str) -> int:
    return int(raw.replace(",", "").replace(" ", ""))


def _metres_to_millimetres(raw: str) -> int:
    return round(float(raw) * 1000)


def _lines(text: str) -> list[str]:
    return [" ".join(line.split()) for line in text.splitlines() if line.strip()]


def _split_at_options(text: str) -> tuple[list[str], list[str], list[str]]:
    """`(standard lines, option lines, every line)`.

    Where the document has no options heading every line counts as standard, which is the
    safe way round: `habitation.usable_lines` still drops anything carrying a price, so a
    priced extra cannot be read as fitted just because the structural split was missing.
    """
    everything = _lines(text)
    heading = _OPTIONS_HEADING.search(text)
    if heading is None:
        return everything, [], everything
    return _lines(text[: heading.start()]), _lines(text[heading.end() :]), everything


@dataclass(frozen=True)
class _PriceLine:
    """One priced row of the model-options table."""

    engine: str
    wheelbase: str
    is_automatic: bool
    pounds: int
    text: str


def _price_lines(text: str) -> list[_PriceLine]:
    found: list[_PriceLine] = []
    for match in _PRICE_LINE.finditer(text):
        variant = " ".join(match.group("variant").split())
        found.append(
            _PriceLine(
                engine=match.group("engine"),
                wheelbase=match.group("wheelbase").upper(),
                is_automatic=bool(_IS_AUTOMATIC.search(variant)),
                pounds=_pounds(match.group("price")),
                text=" ".join(match.group(0).split()),
            )
        )
    return found


def price_grid_holds(lines: Iterable[_PriceLine]) -> tuple[bool, str]:
    """Whether the price table closes as a rectangle — this adapter's only self-check.

    Landseer publish no mass in running order and no payload, so there is no
    `payload == MTPLM - MRO` to lean on. What the model-options table does offer is a
    redundancy the manufacturer printed against itself:

    * the **long wheelbase costs the same uplift over the short one on every drivetrain**
      — £5,000 across all three in the 2027 sheet, £6,000 across both in the 2026 one; and
    * the **automatic costs the same over the manual on both wheelbases** — £3,950 in each
      of the two seasons published so far.

    Six figures and two constants. A column shifted by one, a dropped row or a price that
    has landed on its neighbour breaks it immediately, which is exactly the failure a
    columnar PDF extractor produces and exactly the failure nothing downstream would
    notice: the prices would still be plausible, still internally consistent, and simply
    attached to the wrong vehicles.

    It is weaker than mass arithmetic because it checks only the price parse. It is also
    the only check there is, so a failure drops every product off this document rather
    than being narrated and passed over.
    """
    prices = {(line.engine, line.wheelbase, line.is_automatic): line.pounds for line in lines}
    if not prices:
        return False, "no priced model line was found at all"

    uplifts: dict[tuple[str, bool], int] = {}
    for (engine, wheelbase, is_automatic), pounds in prices.items():
        if wheelbase != "SWB":
            continue
        long_wheelbase = prices.get((engine, "LWB", is_automatic))
        if long_wheelbase is not None:
            uplifts[(engine, is_automatic)] = long_wheelbase - pounds

    gearbox_uplifts: dict[tuple[str, str], int] = {}
    for (engine, wheelbase, is_automatic), pounds in prices.items():
        if is_automatic:
            continue
        automatic = prices.get((engine, wheelbase, True))
        if automatic is not None:
            gearbox_uplifts[(engine, wheelbase)] = automatic - pounds

    if len(uplifts) < 2:
        return False, (
            f"only {len(uplifts)} drivetrain(s) priced on both wheelbases, so the "
            f"wheelbase uplift cannot be cross-checked"
        )
    if len(set(uplifts.values())) != 1:
        detail = ", ".join(
            f"{engine}{' automatic' if is_automatic else ' manual'} £{value:,}"
            for (engine, is_automatic), value in sorted(uplifts.items())
        )
        return False, f"the LWB uplift is not constant across drivetrains ({detail})"
    if len(gearbox_uplifts) >= 2 and len(set(gearbox_uplifts.values())) != 1:
        detail = ", ".join(
            f"{engine} {wheelbase} £{value:,}"
            for (engine, wheelbase), value in sorted(gearbox_uplifts.items())
        )
        return False, f"the automatic uplift is not constant across wheelbases ({detail})"

    uplift = next(iter(set(uplifts.values())))
    note = f"the LWB costs £{uplift:,} more than the SWB on all {len(uplifts)} drivetrains"
    if gearbox_uplifts:
        gear = next(iter(set(gearbox_uplifts.values())))
        note += f", and the automatic £{gear:,} more than the manual on both wheelbases"
    return True, note


@dataclass
class LandseerProduct:
    """One campervan as the documents describe it, before it becomes a `Motorhome`."""

    manufacturer_range: str
    model: str
    source_url: str
    document_label: str

    base_vehicle: str | None = None
    rrp_pounds: int | None = None
    rrp_line: str | None = None
    automatic_rrp_pounds: int | None = None
    automatic_rrp_line: str | None = None
    #: True for the PHEV, which Landseer offer as `1 Speed Automatic` and nothing else, so
    #: its automatic price and its only price are the same figure.
    automatic_is_the_only_gearbox: bool = False
    #: True where the document prices more than one engine against **one** specification
    #: block — which the pricing sheet does. Everything but the price is then shared, and
    #: the provenance says so rather than implying Landseer published it per engine.
    specification_is_shared_across_engines: bool = False

    mtplm_kilograms: int | None = None
    mh_length_mm: int | None = None
    mh_width_mm: int | None = None
    #: Landseer's own qualification of the width, e.g. `(mirrors folded)`, quoted back to
    #: the reviewer rather than silently dropped.
    mh_width_note: str | None = None
    mh_height_mm: int | None = None
    mh_passenger_seats_inc_driver: int | None = None
    seats_line: str | None = None
    rear_three_point_belts: int | None = None
    belts_line: str | None = None
    body_type: BodyType | None = None
    body_type_note: str | None = None

    standard_lines: list[str] = field(default_factory=list)
    #: Everything below the document's own options heading. Read for the gearbox, which is
    #: a paid extra almost everywhere, and narrated for the washroom, which on the Custom
    #: is only ever a paid extra.
    option_lines: list[str] = field(default_factory=list)
    all_lines: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return f"{MANUFACTURER_DISPLAY_NAME} {self.manufacturer_range} {self.model}"


def _body_type(height_mm: int | None, standard_lines: Iterable[str]) -> tuple[BodyType | None, str | None]:
    """The body type, or `None` where the documents do not settle it.

    Four of the eight columns are campervans and the published height picks between them,
    but **only once there is a published height**. The Artemis has none, so it gets
    nothing: the rule is to derive a body type or leave it blank, never to guess across
    eight mutually exclusive columns.

    A dimension never decides this on its own — the roof does, and the height only says
    which kind of roof it is. A pop-top fitted as standard under the threshold is an
    elevating roof; the same van over the threshold would be a high top with one.
    """
    if height_mm is None:
        return None, None
    elevating = any(_POP_TOP.search(line) for line in standard_lines)
    high_top = height_mm > HIGH_TOP_ABOVE_MM
    if high_top and elevating:
        return (
            BodyType.CAMPERVAN_HIGH_TOP_ELEVATING_ROOF,
            f"{height_mm}mm, above the {HIGH_TOP_ABOVE_MM}mm high-top threshold, with an "
            f"elevating roof fitted as standard",
        )
    if high_top:
        return (
            BodyType.CAMPERVAN_HIGH_TOP,
            f"{height_mm}mm, above the {HIGH_TOP_ABOVE_MM}mm high-top threshold",
        )
    if elevating:
        return (
            BodyType.CAMPERVAN_ELEVATING_ROOF,
            f"{height_mm}mm with a pop-top roof fitted as standard, so a campervan with an "
            f"elevating roof rather than a high top — the threshold is "
            f"{HIGH_TOP_ABOVE_MM}mm",
        )
    return (
        BodyType.CAMPERVAN,
        f"{height_mm}mm, below the {HIGH_TOP_ABOVE_MM}mm high-top threshold, with no "
        f"elevating roof in the standard specification",
    )


def parse_pricing_sheet(text: str, source_url: str, document_label: str) -> list[LandseerProduct]:
    """Every Custom product the pricing sheet prices, four of them on the current edition.

    Raises `ValueError` where the document does not hold a full price grid, which is how a
    document misidentified as the pricing sheet is caught rather than silently producing
    nothing — see `documents`.
    """
    priced = _price_lines(text)
    if len(priced) != EXPECTED_PRICE_LINES:
        raise ValueError(
            f"expected {EXPECTED_PRICE_LINES} priced model lines on the pricing sheet, "
            f"found {len(priced)}"
        )
    grid_holds, grid_note = price_grid_holds(priced)
    if not grid_holds:
        raise ValueError(f"the price grid does not reconcile: {grid_note}")

    standard_lines, option_lines, all_lines = _split_at_options(text)

    dimensions = _DIMENSIONS.search(text)
    gvw = _GVW.search(text)
    seats = _SEATS.search(text)
    belts = _REAR_BELTS.search(text)
    base_vehicle = _BASE_VEHICLE.search(text)

    lengths: dict[str, int] = {}
    width = height = None
    width_note = None
    if dimensions is not None:
        lengths = {
            "SWB": _metres_to_millimetres(dimensions.group("swb")),
            "LWB": _metres_to_millimetres(dimensions.group("lwb")),
        }
        width = _metres_to_millimetres(dimensions.group("width"))
        height = _metres_to_millimetres(dimensions.group("height"))
        raw_note = dimensions.group("width_note")
        width_note = " ".join(raw_note.split()) if raw_note else None

    masses: dict[str, int] = {}
    if gvw is not None:
        masses = {
            "SWB": _pounds(gvw.group("swb")),
            "LWB": _pounds(gvw.group("lwb")),
        }

    body_type, body_type_note = _body_type(height, standard_lines)

    by_key = {(line.engine, line.wheelbase, line.is_automatic): line for line in priced}
    engines = sorted({line.engine for line in priced})

    products: list[LandseerProduct] = []
    for engine in engines:
        manufacturer_range = CUSTOM_2_0 if engine == "2.0" else CUSTOM_2_5
        for wheelbase in ("SWB", "LWB"):
            manual = by_key.get((engine, wheelbase, False))
            automatic = by_key.get((engine, wheelbase, True))
            if manual is None and automatic is None:
                continue
            base = manual or automatic
            assert base is not None  # noqa: S101 - narrowing for the type checker
            products.append(
                LandseerProduct(
                    manufacturer_range=manufacturer_range,
                    model=wheelbase,
                    source_url=source_url,
                    document_label=document_label,
                    base_vehicle=base_vehicle.group("make") if base_vehicle else None,
                    rrp_pounds=base.pounds,
                    rrp_line=base.text,
                    automatic_rrp_pounds=automatic.pounds if automatic else None,
                    automatic_rrp_line=automatic.text if automatic else None,
                    automatic_is_the_only_gearbox=manual is None,
                    specification_is_shared_across_engines=len(engines) > 1,
                    mtplm_kilograms=masses.get(wheelbase),
                    mh_length_mm=lengths.get(wheelbase),
                    mh_width_mm=width,
                    mh_width_note=width_note,
                    mh_height_mm=height,
                    mh_passenger_seats_inc_driver=(
                        int(seats.group("seats")) if seats else None
                    ),
                    seats_line=" ".join(seats.group(0).split()) if seats else None,
                    rear_three_point_belts=int(belts.group("belts")) if belts else None,
                    belts_line=" ".join(belts.group(0).split()) if belts else None,
                    body_type=body_type,
                    body_type_note=body_type_note,
                    standard_lines=standard_lines,
                    option_lines=option_lines,
                    all_lines=all_lines,
                )
            )
    return products


def parse_artemis_brochure(text: str, source_url: str, document_label: str) -> LandseerProduct:
    """The Artemis, which is a price, a base vehicle and an equipment list.

    **Six fields the other three products carry are deliberately absent**, because the
    brochure and the model page between them publish no mass, no dimension, no berth count
    and no unambiguous travel-seat count. A field with no provenance is never proposed, so
    this creates the product with the figures Landseer actually state and leaves the rest
    for a person to fill in once Landseer answer.
    """
    standard_lines, option_lines, all_lines = _split_at_options(text)
    price = _LAUNCH_PRICE.search(text)
    base_vehicle = _BASE_VEHICLE.search(text)
    return LandseerProduct(
        manufacturer_range=ARTEMIS,
        model=ARTEMIS_MODEL,
        source_url=source_url,
        document_label=document_label,
        base_vehicle=base_vehicle.group("make") if base_vehicle else None,
        rrp_pounds=_pounds(price.group("price")) if price else None,
        rrp_line=" ".join(price.group(0).split()) if price else None,
        standard_lines=standard_lines,
        option_lines=option_lines,
        all_lines=all_lines,
    )


def _reconciles(product: LandseerProduct) -> tuple[bool, str]:
    """Whether the seat count agrees with the belts, which the sheet prints separately.

    The Custom sheet states the travel seats in one line and the belts that carry them in
    another: `5 travelling seats` and `with 3 x 3-point safety belts`. Three belted
    positions on the Mobiframe bench plus the driver and passenger is five, so the two
    lines check each other, and a garbled extraction of that block shows up here instead
    of reaching a reviewer as a plausible seat count.

    **The Artemis has no such pair and is not asked for one.** Its bench is described as
    `2 travel positions, see options for 4 positions` with no belt type named anywhere, so
    this adapter records no seat count for it at all rather than inventing one — which
    leaves nothing to reconcile.
    """
    if product.mh_passenger_seats_inc_driver is None:
        return True, "no seat count is claimed, so there is nothing to reconcile"
    if product.rear_three_point_belts is None:
        return False, (
            f"{product.mh_passenger_seats_inc_driver} travelling seats are claimed but no "
            f"three-point belt count was found to check them against"
        )
    expected = product.rear_three_point_belts + 2
    if expected != product.mh_passenger_seats_inc_driver:
        return False, (
            f"{product.rear_three_point_belts} rear three-point belts plus the two cab "
            f"seats is {expected}, but the sheet claims "
            f"{product.mh_passenger_seats_inc_driver} travelling seats"
        )
    return True, (
        f"{product.rear_three_point_belts} rear three-point belts plus the two cab seats "
        f"is {product.mh_passenger_seats_inc_driver}, as claimed"
    )


def _build_extracted_motorhome(product: LandseerProduct) -> ExtractedMotorhome:
    """One product as a `Motorhome`, with the provenance a reviewer reads beside each field.

    Fields deliberately left with **no provenance, and so never proposed**:

    * `mro_kilograms` and `mh_payload_kilograms` — no Landseer document has ever published
      either, for any model, in any of the ten editions the media library holds. FMLV's own
      2,400kg / 2,450kg and 775kg on the two Custom 2.0 rows come from somewhere else and
      must survive this run untouched.
    * `berths` — not published for anything. The Custom's two beds and the Artemis's one
      make 4 and 2 obvious enough, but obvious is not published, and FMLV already holds 4
      on both Customs.
    * `sleeping_area`, `kitchen_location`, `lounge_location` and `bathroom_layout` — only a
      drawing settles those and Landseer publish no floorplan, so there is not even a
      reviewer pointer to offer.
    * `body_type` on the Artemis — no height is published, and a pop-top offered at £9,200
      is an option rather than evidence about the vehicle as built.

    **`automatic.rrp_pounds` is populated here, which is new.** Landseer print the
    automatic as its own priced line on every wheelbase, which is precisely what the field
    guide's "IF AUTOMATIC OPTION, COMPLETE THESE EXTRA COLUMNS TO FEATURE IN AUTOMATIC
    FILTER RESULTS" asks for. Its mass columns stay blank: no automatic weight is published
    either.
    """
    features = habitation.features_from(product.standard_lines)
    automatic = gearbox.automatic_available_from(product.all_lines)

    automatic_variant: AutomaticVariant | None = None
    if product.automatic_rrp_pounds is not None:
        automatic_variant = AutomaticVariant(rrp_pounds=product.automatic_rrp_pounds)

    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.manufacturer_range,
        model=product.model,
        base_vehicle_manufacturer=fmlv_base_vehicle(product.base_vehicle),
        rrp_pounds=product.rrp_pounds,
        mtplm_kilograms=product.mtplm_kilograms,
        mh_length_mm=product.mh_length_mm,
        mh_width_mm=product.mh_width_mm,
        mh_height_mm=product.mh_height_mm,
        mh_passenger_seats_inc_driver=product.mh_passenger_seats_inc_driver,
        body_type=product.body_type,
        automatic=automatic_variant,
        automatic_available=automatic[0] if automatic else None,
        # Habitation: findings, never proposals — see `docs/adapters/README.md`.
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

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=product.source_url,
            snippet=f"{product.label} — {snippet}",
        )

    record(
        "manufacturer_range",
        f"range {product.manufacturer_range!r}, from {product.document_label}",
    )
    if product.base_vehicle is not None:
        record(
            "base_vehicle_manufacturer",
            f"the donor van is named as {product.base_vehicle}, from the line that opens "
            f"the standard specification",
        )
    if product.rrp_pounds is not None:
        basis = (
            "Landseer state the basis themselves — \"OTR = Registered 'on the road' and "
            "with 1 year's VED included\" — which is FMLV's own"
            if product.manufacturer_range != ARTEMIS
            else "the brochure's own pricing panel, inc. VAT. Landseer sell direct, so "
            "their headline figure is the guide price"
        )
        gearbox_note = (
            " This is the automatic's price because Landseer offer no manual: the PHEV is "
            "a 1-speed automatic only."
            if product.automatic_is_the_only_gearbox
            else ""
        )
        record("rrp_pounds", f"{product.rrp_line!r}. {basis}.{gearbox_note}")
    if product.automatic_rrp_pounds is not None:
        if product.automatic_is_the_only_gearbox:
            detail = (
                f"£{product.automatic_rrp_pounds:,}, the same figure as the price above, "
                f"because the PHEV is offered as a 1-speed automatic and nothing else. It "
                f"is recorded here as well so the product appears in FMLV's automatic "
                f"filter, which reads this column"
            )
        else:
            detail = (
                f"{product.automatic_rrp_line!r} — Landseer price the automatic as its own "
                f"line, so this is a published figure rather than a derived one. No "
                f"automatic mass is published, so those columns stay blank"
            )
        record("automatic.rrp_pounds", detail)
    if product.mtplm_kilograms is not None:
        shared = (
            " Landseer state ONE GVW pair for the whole sheet, so this is the figure they "
            "publish for this wheelbase whichever engine it carries, not one measured for "
            "the PHEV."
            if product.specification_is_shared_across_engines
            else ""
        )
        record(
            "mtplm_kilograms",
            f"'Maximum GVW {product.model} {product.mtplm_kilograms:,}kg'. Landseer publish "
            f"NO mass in running order and NO payload, in any edition, for any model — so "
            f"this figure stands alone and neither of those two is proposed.{shared}",
        )
    if product.mh_length_mm is not None:
        record(
            "mh_length_mm",
            f"'Dimensions - {product.model} {product.mh_length_mm / 1000:.2f}m long'",
        )
    if product.mh_width_mm is not None:
        note = (
            f" Landseer qualify it as {product.mh_width_note}, which is their only "
            f"published width; it is recorded as they state it and their wording is "
            f"mirrored here rather than adjusted."
            if product.mh_width_note
            else ""
        )
        record("mh_width_mm", f"'{product.mh_width_mm / 1000:.2f}m wide'.{note}")
    if product.mh_height_mm is not None:
        record("mh_height_mm", f"'{product.mh_height_mm / 1000:.2f}m high'")
    if product.mh_passenger_seats_inc_driver is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"{product.seats_line!r}, carried on {product.belts_line!r} — three belted "
            f"positions on the Mobiframe bench plus the driver and passenger. The upgrade "
            f"to seven is a paid extra and is not counted, and only three-point belts are",
        )
    if product.body_type is not None and product.body_type_note is not None:
        record("body_type", f"a campervan at {product.body_type_note}")
    if automatic is not None:
        record("automatic_available", gearbox.provenance_note(automatic))

    for field_name, feature in features.items():
        detail = f" — {feature.note}" if feature.note else ""
        provenance[field_name] = Provenance(
            source_url=product.source_url,
            snippet=f"{product.label} — the specification says {feature.snippet!r}{detail}",
        )

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


# --------------------------------------------------------------------------- #
# The run
# --------------------------------------------------------------------------- #


def _narrate_habitation(
    product: LandseerProduct, on_progress: Callable[[str], None]
) -> None:
    """Quote the beds and the washroom into the run, for the person typing them in.

    Habitation fields are findings rather than proposals, so what a reviewer actually needs
    is the manufacturer's sentence. Two of them are worth saying out loud on every run:

    * **the beds**, because `habitation.bed_types_from` cannot read the Artemis's — see
      `_BED_LINE`; and
    * **the washroom**, because on the Custom there isn't one. The shower attachment is
      £240 and the Thetford porta toilet £100, both in the options list, so the vehicle as
      built has neither — and FMLV's two existing Custom 2.0 rows both carry
      `rear_shower_toilet`. That is not something this adapter can propose away, since
      silence about a washroom is not a statement that there is none, but it is something a
      person should be looking at.
    """
    beds = [line for line in product.standard_lines if _BED_LINE.search(line)]
    if beds:
        on_progress(f"{product.label} — beds, as Landseer describe them: " + " | ".join(beds))

    standard_washroom = [
        line for line in product.standard_lines if _WASHROOM_LINE.search(line)
    ]
    optional_washroom = [
        line for line in product.option_lines if _WASHROOM_LINE.search(line)
    ]
    if standard_washroom:
        on_progress(
            f"{product.label} — washroom, in the standard specification: "
            + " | ".join(standard_washroom)
        )
    elif optional_washroom:
        on_progress(
            f"{product.label} — NO washroom in the standard specification. Every shower "
            f"and toilet on this document is a priced option: " + " | ".join(optional_washroom)
        )


def _check_roster(http: Fetcher, on_progress: Callable[[str], None]) -> None:
    """Narrate any model page on the index that this adapter does not account for."""
    index = http.fetch(MODELS_INDEX_URL)
    if index.status_code != 200:
        on_progress(
            f"could not read the campervans index (HTTP {index.status_code}), so a new "
            f"model page would go unnoticed this run"
        )
        return
    slugs = parse_roster(index.file_path.read_text(encoding="utf-8", errors="replace"))
    unknown = [
        slug
        for slug in slugs
        if slug not in KNOWN_MODEL_PAGES and slug not in NOT_A_MODEL
    ]
    if unknown:
        on_progress(
            "NEW MODEL PAGE on the campervans index, which no document here is read for: "
            + ", ".join(f"/campervans/{slug}" for slug in unknown)
        )
    missing = [slug for slug in KNOWN_MODEL_PAGES if slug not in slugs]
    if missing:
        on_progress(
            "a model page this adapter expects is no longer linked from the index: "
            + ", ".join(f"/campervans/{slug}" for slug in sorted(missing))
        )


def _read_document(
    http: Fetcher, url: str, title: str, date: str, on_progress: Callable[[str], None]
) -> str:
    """One PDF's text, narrating which edition it is."""
    on_progress(f"reading {title!r}, uploaded {date[:10] or 'unknown date'} — {url}")
    result = http.fetch(url)
    if result.status_code != 200:
        raise RuntimeError(f"{title!r} returned HTTP {result.status_code} from {url}")
    return extract_text(result.file_path).text


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 - no page on this site needs rendering
    snapshot_dir: Path,  # noqa: ARG001 - `Fetcher` already snapshots every request
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every Landseer campervan the two current documents describe."""
    wanted = {entry[-1] for entry in ranges}

    _check_roster(http, on_progress)

    media = http.fetch(MEDIA_URL)
    if media.status_code != 200:
        raise RuntimeError(
            f"the media library returned HTTP {media.status_code} from {MEDIA_URL}, and "
            f"nothing on this site links the documents, so there is no other way in"
        )
    found = documents(media.file_path.read_text(encoding="utf-8", errors="replace"))
    if found:
        on_progress(
            "the media library lists "
            + ", ".join(
                f"{kind}: {title!r} of {date[:10]}"
                for kind, (_, title, date) in sorted(found.items())
            )
        )
    else:
        on_progress("the media library lists no PDF at all")

    products: list[LandseerProduct] = []

    if {CUSTOM_2_0, CUSTOM_2_5} & wanted:
        if "custom" not in found:
            raise RuntimeError("no pricing sheet was found in the media library")
        url, title, date = found["custom"]
        text = _read_document(http, url, title, date, on_progress)
        parsed = parse_pricing_sheet(text, url, f"{title!r} of {date[:10]}")
        grid_holds, grid_note = price_grid_holds(_price_lines(text))
        on_progress(f"the price grid reconciles: {grid_note}")
        products.extend(
            product for product in parsed if product.manufacturer_range in wanted
        )

    if ARTEMIS in wanted:
        if "artemis" not in found:
            on_progress("no Artemis brochure was found in the media library, so it is skipped")
        else:
            url, title, date = found["artemis"]
            text = _read_document(http, url, title, date, on_progress)
            products.append(parse_artemis_brochure(text, url, f"{title!r} of {date[:10]}"))

    extracted: list[ExtractedMotorhome] = []
    for product in products:
        reconciles, note = _reconciles(product)
        if not reconciles:
            on_progress(f"DROPPED {product.label}: {note}")
            continue
        extracted.append(_build_extracted_motorhome(product))

        gaps = []
        if product.mtplm_kilograms is None:
            gaps.append("no MTPLM")
        if product.mh_length_mm is None:
            gaps.append("no dimensions")
        if product.mh_passenger_seats_inc_driver is None:
            gaps.append("no travel-seat count")
        if product.body_type is None:
            gaps.append("no height, so no body type")
        gap_note = f"; {', '.join(gaps)} published" if gaps else ""
        price = f"£{product.rrp_pounds:,}" if product.rrp_pounds else "no price"
        on_progress(
            f"{product.label}: {price}, NO mass in running order and NO payload published "
            f"(neither is proposed, so FMLV's own figures stand){gap_note}"
        )
        _narrate_habitation(product, on_progress)

    if len(extracted) != EXPECTED_PRODUCTS and wanted == {label for _, label in DEFAULT_RANGES}:
        on_progress(
            f"collected {len(extracted)} products where Landseer's two documents describe "
            f"{EXPECTED_PRODUCTS}"
        )
    return extracted
