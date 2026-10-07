"""Freedom Caravans (freedomcaravans.com) — small, lightweight British caravans.

See `docs/adapters/freedom.md` for the survey. One page per model under
`/models/<slug>/`, each carrying a `Weights & Dimensions` block in plain HTML. No tables,
no JavaScript, no login, and no price list anywhere: the whole site links a single PDF, a
2025 brochure with not one price in it that still describes models no longer sold.

**The trap is the price, and it is the reason this adapter never reads `/models/`.** That
index page carries a `from £x` beside every model and **disagrees with the model pages on
six of the eight**. The model pages are right: they agree with FMLV to the pound on every
product it holds. The index is dearer on the Jetstreams and cheaper on the Sunseeker, so
it is a page nobody has maintained rather than a superseded price round — there is no
pattern to correct for. The index is used for the roster and for nothing else, and
`parse_price` is only ever given a model page.

**Two lengths, and FMLV holds both.** `Overall Length` is the shipping length including
the hitch; `Body Length` is the exterior body. They differ by more than a metre on the
Microlites — 4.00 m against 2.82 m — and FMLV's own rows carry them as 4000 and 2820, so
the mapping is confirmed rather than assumed. No internal length is published by any model.

**The self-check is arithmetic and it is published.** Every page states MTPLM, Unladen
Weight *and* Payload, so `mtplm - unladen == payload` can be checked per product without a
second source. It holds on all eight. A product that fails it is dropped, never proposed.

**Berths come from the page title and only when they are there.** Five pages title
themselves `… 3 Berth Caravan …`; three do not, and for those the adapter emits nothing so
FMLV's own figure stands. The requester confirmed on 7 October 2026 that the missing ones
were settled in earlier correspondence with Freedom and have not changed.

**Every model is a micro**, by the two-part test in `docs/adapters/README.md`: Freedom
describe themselves as a maker of small lightweight caravans, and the heaviest in the
range is 1000 kg against the 1250 kg ceiling. All nine FMLV rows already read `type_micro`.
Two Microlites are pop-tops — their pages say `Height (Roof Down)` and `Headroom (Roof Up)`
where the rest say plain `Height` — but the type columns are single-select and FMLV has
settled on micro, so the roof is read for its dimensions only.
"""

from __future__ import annotations

import html as htmllib
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from src.adapters.base import ExtractedCaravan, Provenance
from src.fetch.browser import BrowserFetcher
from src.fetch.http import Fetcher
from src.product_model.caravan import Caravan
from src.product_model.enums import CaravanBodyType
from src.vehicle_class import VehicleClass

__all__ = [
    "BASE_URL",
    "DEFAULT_RANGES",
    "EXPECTED_MODELS",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "MODELS",
    "RENAMED_MODELS",
    "VEHICLE_CLASS",
    "collect",
    "parse_berths",
    "parse_price",
    "parse_specification",
    "roster_slugs",
]

BASE_URL = "https://www.freedomcaravans.com"
MANUFACTURER = "Freedom Caravans"
MANUFACTURER_DISPLAY_NAME = "Freedom"

#: What makes this the caravan adapter rather than a motorhome one.
VEHICLE_CLASS = VehicleClass.CARAVAN

MODELS_INDEX = f"{BASE_URL}/models/"


@dataclass(frozen=True)
class FreedomModel:
    """One model: its page, and the identity FMLV files it under."""

    #: The `/models/<slug>/` path segment.
    slug: str
    #: FMLV's range — the **model family**, not the site's `Classic Range` grouping.
    fmlv_range: str
    fmlv_model: str

    @property
    def url(self) -> str:
        return f"{BASE_URL}/models/{self.slug}/"

    @property
    def label(self) -> str:
        return f"{self.fmlv_range} {self.fmlv_model}"


#: **The names Freedom use, which is the requester's rule for this brand** (7 October
#: 2026): *"we just match the website for the names — if they call it the Freedom
#: Sunseeker we'll call it the Freedom Sunseeker."*
#:
#: The range is the model family. The site also groups five of these under a `Classic
#: Range` heading, but that is a page section rather than a model name and FMLV has never
#: used it.
#:
#: **The Sunseeker is the one that argues with FMLV.** Freedom give it no variant name —
#: the page is simply `/models/sunseeker/` — where FMLV still holds `Sunseeker / Classic`,
#: a name the site no longer uses anywhere. Repeating the range as the model is what FMLV
#: does for a product with no variant: 27 rows across Auto-Sleepers, Hymer, Wingamm,
#: Wildax, Westfalia, Visiontech and Moto-Trek do exactly this, and **not one row in any
#: export leaves the model blank**. So the correction is proposed, and `RENAMED_MODELS`
#: below keeps it matching the row it is correcting.
MODELS: tuple[FreedomModel, ...] = (
    FreedomModel("jetstream-twin-sport", "Jetstream", "Twin Sport"),
    FreedomModel("jetstream-first-class", "Jetstream", "First Class"),
    FreedomModel("sunseeker", "Sunseeker", "Sunseeker"),
    FreedomModel("microlite-discovery", "Microlite", "Discovery"),
    FreedomModel("microlite-sport", "Microlite", "Sport"),
    FreedomModel("carpento-360", "Carpento", "360"),
    FreedomModel("wayfarer-quad", "Wayfarer", "Quad"),
    FreedomModel("wayfarer-duet", "Wayfarer", "Duet"),
)

#: What the site now says, against what FMLV still holds — for **matching only**; nothing
#: here renames anything in FMLV.
#:
#: Without it `Sunseeker / Sunseeker` scores exactly **0.500** against `Sunseeker /
#: Classic`, which is the default threshold itself: one shared token of a two-token union.
#: It matches, but with no margin at all, and the failure if it ever slipped is the one
#: `docs/adapters/README.md` warns of — the correction arriving as a new product beside a
#: disappearance notice for the row it was meant to correct.
#:
#: With the entry it scores 1.000 against the name FMLV holds today **and** 1.000 against
#: its own name once the correction is accepted, because `token_similarity` takes the
#: better of the two. That is what makes it safe to leave here afterwards.
RENAMED_MODELS: dict[tuple[str, str], tuple[str, str]] = {
    ("Sunseeker", "Sunseeker"): ("Sunseeker", "Classic"),
}

#: Eight on the site against FMLV's nine. The ninth is `Carpento / 410`, which Freedom no
#: longer list — the requester's "slightly fewer models now". A run reports it missing.
EXPECTED_MODELS = 8

_BY_SLUG = {model.slug: model for model in MODELS}

#: One per range, so `--range` can scope a run the way every other adapter allows.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (
    ("jetstream", "Jetstream"),
    ("sunseeker", "Sunseeker"),
    ("microlite", "Microlite"),
    ("carpento", "Carpento"),
    ("wayfarer", "Wayfarer"),
)

#: Freedom publish nothing heavier than 1000kg and describe themselves as a maker of small
#: lightweight caravans — the two-part micro test in `docs/adapters/README.md`.
MICRO_MAX_MTPLM_KG = 1250


def _text(page: str) -> str:
    """The page's visible text, with every tag boundary marked by a pipe.

    The spec block is a run of `Label: | value |` pairs with no table around it, so the
    boundaries are the only thing separating a label from its value.
    """
    body = re.sub(r"(?is)<(script|style|head|nav|footer)\b.*?</\1>", " ", htmllib.unescape(page))
    collapsed = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", body))
    return re.sub(r"(?:\s*\|\s*)+", " | ", collapsed)


def roster_slugs(index_html: str) -> list[str]:
    """Every model slug linked from `/models/`, in page order and without duplicates.

    **The roster is all this page is used for.** Its prices are stale — see the module
    docstring — so nothing else is read from it.
    """
    seen: list[str] = []
    for slug in re.findall(r"freedomcaravans\.com/models/([a-z0-9-]+)/", index_html, re.I):
        if slug not in seen:
            seen.append(slug)
    return seen


def parse_price(page_html: str) -> int | None:
    """The model's own `from £x`, read from its own page and never from the index."""
    match = re.search(r"from\s*£\s*([\d,]+)", _text(page_html), re.I)
    return int(match.group(1).replace(",", "")) if match else None


def parse_berths(page_html: str) -> int | None:
    """The berth count from the page `<title>`, or `None` where it does not say.

    Three of the eight pages carry no berth count anywhere. Returning `None` is what keeps
    FMLV's own figure — guessing one from the bed sizes is exactly the invention the
    adapter guide warns against, and the Jetstream Twin Sport shows why: it lists a double
    *and* a single where FMLV holds two berths.
    """
    title = re.search(r"<title[^>]*>(.*?)</title>", page_html, re.S)
    if not title:
        return None
    berths = re.search(r"(\d)\s*berth", htmllib.unescape(title.group(1)), re.I)
    return int(berths.group(1)) if berths else None


@dataclass(frozen=True)
class Specification:
    """The `Weights & Dimensions` block of one model page."""

    mtplm_kilograms: int | None = None
    mro_kilograms: int | None = None
    published_payload_kilograms: int | None = None
    shipping_length_mm: int | None = None
    exterior_body_length_mm: int | None = None
    overall_width_mm: int | None = None
    height_mm: int | None = None
    headroom_mm: int | None = None


#: `Height` and `Headroom` carry a roof qualifier on the two pop-top Microlites and not on
#: the other six, so both spellings are accepted and the first one found wins.
_LABELS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("mtplm_kilograms", ("MTPLM",)),
    ("mro_kilograms", ("Unladen Weight",)),
    ("published_payload_kilograms", ("Payload",)),
    ("shipping_length_mm", ("Overall Length",)),
    ("exterior_body_length_mm", ("Body Length",)),
    ("overall_width_mm", ("Width",)),
    ("height_mm", ("Height (Roof Down)", "Height")),
    ("headroom_mm", ("Headroom (Roof Up)", "Headroom")),
)


def _kilograms(value: str) -> int | None:
    match = re.search(r"([\d,]+)\s*kg", value, re.I)
    return int(match.group(1).replace(",", "")) if match else None


def _millimetres(value: str) -> int | None:
    """`4m`, `2.82m` and `1.94m (6′,4″)` all arrive here; the feet are decoration."""
    match = re.match(r"\s*(\d+(?:\.\d+)?)\s*m\b", value)
    return round(float(match.group(1)) * 1000) if match else None


def parse_specification(page_html: str) -> Specification:
    """The weights and dimensions of one model, from its own page."""
    text = _text(page_html)
    found: dict[str, int] = {}
    for field_name, labels in _LABELS:
        for label in labels:
            match = re.search(rf"\|\s*{re.escape(label)}:\s*\|\s*([^|]+?)\s*\|", text)
            if match:
                reader = _kilograms if field_name.endswith("_kilograms") else _millimetres
                value = reader(match.group(1))
                if value is not None:
                    found[field_name] = value
                break
    return Specification(**found)


def _reconciles(spec: Specification) -> tuple[bool, str]:
    """`mtplm - unladen == payload`, which every page publishes all three sides of.

    The one check available without a second source, and the reason a misread column
    cannot reach a reviewer as a plausible caravan carrying another model's weights.
    """
    mtplm, mro, payload = (
        spec.mtplm_kilograms,
        spec.mro_kilograms,
        spec.published_payload_kilograms,
    )
    if mtplm is None or mro is None:
        return False, "no MTPLM or no unladen weight on the page"
    if payload is None:
        return False, "no published payload to check the two masses against"
    derived = mtplm - mro
    if derived != payload:
        return (
            False,
            f"MTPLM {mtplm} - unladen {mro} = {derived}kg against a published payload of "
            f"{payload}kg",
        )
    return True, f"MTPLM {mtplm} - unladen {mro} = payload {payload}kg"


def build_extracted(
    model: FreedomModel,
    spec: Specification,
    *,
    price_pounds: int | None,
    berths: int | None,
    basis: str,
) -> ExtractedCaravan:
    """One Freedom caravan as a `Caravan`, with provenance on everything it proposes."""
    payload = spec.published_payload_kilograms
    caravan = Caravan(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=model.fmlv_range,
        model=model.fmlv_model,
        berths=berths,
        rrp_pounds=price_pounds,
        mtplm_kilograms=spec.mtplm_kilograms,
        mro_kilograms=spec.mro_kilograms,
        # The derived figure, per `docs/adapters/README.md`. It equals the published one:
        # `_reconciles` has already refused the product otherwise.
        personal_effects_payload_kilograms=payload,
        # Deliberately no value — see the record below.
        optional_equipment_payload_kilograms=None,
        shipping_length_mm=spec.shipping_length_mm,
        exterior_body_length_mm=spec.exterior_body_length_mm,
        # Published by no model, so never proposed.
        internal_length_mm=None,
        overall_width_mm=spec.overall_width_mm,
        height_mm=spec.height_mm,
        headroom_mm=spec.headroom_mm,
        body_type=CaravanBodyType.MICRO,
        twin_axle=False,
    )

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=model.url, snippet=f"{model.label} — {snippet}"
        )

    record("manufacturer_range", f'range "{model.fmlv_range}" — the model family, which is '
                                 f"how FMLV files it; the site groups it under a "
                                 f'"Classic Range" heading FMLV does not use')
    moved = (
        '. FMLV still holds "Classic", a name the site uses nowhere: Freedom give this '
        "model no variant, and repeating the range is what FMLV does for a product that "
        "has none"
        if model.fmlv_range == model.fmlv_model
        else ""
    )
    record("model", f'model "{model.fmlv_model}" — the name Freedom use for it{moved}')
    if price_pounds is not None:
        record(
            "rrp_pounds",
            f"GBP{price_pounds:,} — the model page's own 'from' price. **Not** the figure "
            f"on /models/, which disagrees on six of the eight and is stale",
        )
    if berths is not None:
        record("berths", f"{berths} — the page titles itself a {berths} berth caravan")
    for field_name, label in (
        ("mtplm_kilograms", "MTPLM"),
        ("mro_kilograms", "Unladen Weight"),
        ("shipping_length_mm", "Overall Length, which includes the hitch"),
        ("exterior_body_length_mm", "Body Length, the exterior body"),
        ("overall_width_mm", "Width"),
        ("height_mm", "Height"),
        ("headroom_mm", "Headroom"),
    ):
        value = getattr(caravan, field_name)
        if value is not None:
            record(field_name, f"{value} from the page's '{label}'")
    if payload is not None:
        record(
            "personal_effects_payload_kilograms",
            f"{payload}kg — {basis}, and the page publishes the same figure",
        )
        # **No value, on purpose.** `diff.compare` turns a value-to-nothing change into a
        # confirm-or-clear row rather than a silent blanking, so a stale optional figure
        # can be cleared and the two columns then sum to the published payload. FMLV holds
        # it blank on all nine Freedom rows, so this comes back confirmed and silent.
        record(
            "optional_equipment_payload_kilograms",
            "Freedom publish one payload figure and no optional-equipment allowance, so "
            "the whole of it is recorded as personal effects",
        )
    record(
        "body_type",
        f"a micro caravan: Freedom build small lightweight caravans and this one is "
        f"{spec.mtplm_kilograms}kg, under the {MICRO_MAX_MTPLM_KG}kg threshold",
    )
    record("twin_axle", "single axle — Freedom build no twin-axle caravan")
    return ExtractedCaravan(caravan=caravan, provenance=provenance)


def collect(
    http: Fetcher,
    browser: BrowserFetcher,  # noqa: ARG001
    snapshot_dir: Path,  # noqa: ARG001
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedCaravan]:
    """Every Freedom caravan, one fetch of the index and one per model page."""
    wanted = {label for _path, label in ranges}
    requested = [model for model in MODELS if model.fmlv_range in wanted]

    on_progress(f"reading the roster: {MODELS_INDEX}")
    index_html = http.fetch(MODELS_INDEX).file_path.read_text(encoding="utf-8", errors="replace")
    listed = roster_slugs(index_html)

    for slug in listed:
        if slug not in _BY_SLUG:
            on_progress(
                f"the index lists /models/{slug}/, which this adapter does not know. It is "
                f"a new model and needs adding to MODELS with the range and model name "
                f"FMLV should file it under — nothing is collected for it"
            )
    for model in requested:
        if model.slug not in listed:
            on_progress(
                f"{model.label} is no longer listed on {MODELS_INDEX} — its page is still "
                f"read, but check whether Freedom have withdrawn it"
            )

    results: list[ExtractedCaravan] = []
    for model in requested:
        prefix = f"[{model.fmlv_range}] {model.fmlv_model}"
        result = http.fetch(model.url)
        if result.status_code != 200:
            on_progress(f"{prefix} — SKIPPED: {model.url} returned {result.status_code}")
            continue
        page = result.file_path.read_text(encoding="utf-8", errors="replace")

        spec = parse_specification(page)
        reconciles, basis = _reconciles(spec)
        if not reconciles:
            on_progress(f"{prefix} — DROPPED: {basis}")
            continue

        berths = parse_berths(page)
        if berths is None:
            on_progress(
                f"{prefix} — no berth count on the page, so none is proposed and FMLV's "
                f"own figure stands"
            )
        price = parse_price(page)
        if price is None:
            on_progress(f"{prefix} — no price on the page, so none is proposed")

        results.append(
            build_extracted(model, spec, price_pounds=price, berths=berths, basis=basis)
        )
        on_progress(
            f"{prefix} — read: {spec.shipping_length_mm}mm over the hitch, "
            f"{spec.mtplm_kilograms}kg, {berths if berths else '?'} berth, "
            + (f"GBP{price:,}" if price else "no price")
        )

    on_progress(
        "PRICES ARE READ FROM THE MODEL PAGES AND NEVER FROM /models/. That index carries "
        "a 'from' price beside every model and disagrees with the model pages on six of "
        "the eight; the model pages agree with FMLV to the pound on every product it "
        "holds. It is dearer on the Jetstreams and cheaper on the Sunseeker, so there is "
        "no pattern to correct for — it is simply unmaintained."
    )
    if len(requested) == len(MODELS) and len(results) != EXPECTED_MODELS:
        on_progress(
            f"expected {EXPECTED_MODELS} models and collected {len(results)} — check "
            f"whether the range has changed"
        )
    on_progress(f"collected {len(results)} Freedom caravan(s)")
    return results
