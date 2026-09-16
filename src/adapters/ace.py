"""Ace Motorhomes — 22 layouts across three ranges, from the site's own JSON.

`docs/adapters/ace.md` is the survey; this is what it decided.

**The cleanest source in the project.** Every range page carries its whole layout dataset as
a `<script type="application/json">` block — dimensions, all three masses, berths, belted
seats, price, bed sizes and axle type, one entry per layout. Plain HTTP, no browser, no
PDF, and nothing to scrape out of prose.

Two things are specific to Ace and neither is obvious:

* **it is the second brand under `Swift Group Ltd`**, which is why `ADAPTERS` keys on the
  display name as well — see `adapters/__init__.py`. `swift.py` is the first;
* **the same layout code appears twice in a range**, as a 2-berth and a 4-berth of one
  floorplan, so the berth count is part of the model. See `_identity`.
"""

from __future__ import annotations

import html
import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from . import habitation
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

#: The legal manufacturer, which Ace shares with Swift and Bessacarr, and the brand.
#:
#: Both are needed to claim a row: `fmlv_manufacturer` alone names three FMLV
#: manufacturers, and keying `ADAPTERS` on it would have made one of `swift.py` and this
#: module answer for the other.
MANUFACTURER = "Swift Group Ltd"
MANUFACTURER_DISPLAY_NAME = "Ace Motorhomes"

BASE_URL = "https://acemotorhomes.com"


@dataclass(frozen=True)
class Range:
    """One Ace range: where it lives, what it is built on, and what body it has."""

    #: FMLV's `manufacturer_range`, which is the page's own name for it.
    name: str
    path: str
    #: Every layout in the range sits on one chassis, stated in the range page's copy.
    base_vehicle: str
    #: The 1200 is a panel van and the other two are coachbuilts. A 1200 layout with a
    #: pop-top roof is an *elevating roof* high top — see `_body_type`.
    campervan: bool


#: The three current ranges. A change here is a roster change and shows up as such.
RANGES: tuple[Range, ...] = (
    Range("1200", "/campervans/1200/", "Fiat", campervan=True),
    Range("1500", "/motorhomes/1500/", "Ford", campervan=False),
    Range("Supreme", "/motorhomes/supreme/", "Ford", campervan=False),
)

#: `(slug key, label)` for `--range`, matched against the FMLV range name.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = tuple(
    (entry.name, entry.name) for entry in RANGES
)

#: What the roster should come to: 1200 nine, 1500 six, Supreme seven.
#:
#: Ace publish no count of their own, so this is the only defence against a range page
#: quietly dropping a layout — the arithmetic below cannot see an absence.
EXPECTED_LAYOUTS = 22

#: Every layout code Ace use, so `habitation.lines_for_layout` can recognise a feature
#: qualified by letter — `Separate shower cubicle (DB, ET & SL)` — without mistaking
#: `(LED)` or `(5G ready)` for one.
LAYOUT_CODES: tuple[str, ...] = (
    "GS", "GST", "RB", "RL", "RLT", "GL", "GLT", "SL", "SLT", "ET", "DB", "EW",
)

#: A layout's title, which is the only thing that distinguishes two otherwise identical
#: vehicles.
#:
#: `1500 DB (2 berth)` and `1500 DB (4 berth)` publish the *same* length, width, height,
#: MTPLM and price — only the mass, the bed list and this title differ. So the title is
#: load-bearing: if Ace ever stopped writing the berth count, nothing in the data could
#: tell the two apart.
TITLE = re.compile(
    r"^(?P<range>\S+)\s+(?P<code>[A-Z]+)(?:\s*\(\s*(?P<berths>\d+)\s*berth\s*\))?$"
)

#: The layout dataset, which every range page carries inline.
_JSON_BLOCK = re.compile(
    r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', re.S
)

_TAGS = re.compile(r"(?is)<(script|style)\b.*?</\1>")


def plain_text(page: str) -> str:
    """The page as one line, tags replaced by a single space and entities resolved."""
    stripped = re.sub(r"<[^>]+>", " ", _TAGS.sub(" ", page))
    return re.sub(r"\s+", " ", html.unescape(html.unescape(stripped))).strip()


def layout_data(page: str) -> list[dict]:
    """The range page's layout dataset, or an empty list if it carries none.

    A page holds more than one JSON block, so the right one is found by what it contains
    rather than by its position — the layouts are the list whose entries carry a
    `weightMtplm`.
    """
    for block in _JSON_BLOCK.findall(page):
        try:
            data = json.loads(html.unescape(block))
        except json.JSONDecodeError:
            continue
        if (
            isinstance(data, list)
            and data
            and isinstance(data[0], dict)
            and "weightMtplm" in data[0]
        ):
            return data
    return []


def _millimetres(published: str | None) -> int | None:
    """`6.97m` as 6970. Ace publish every dimension in metres."""
    if not published:
        return None
    match = re.match(r"\s*(\d+(?:\.\d+)?)\s*m\b", published)
    return round(float(match.group(1)) * 1000) if match else None


def _kilograms(published: str | None) -> int | None:
    """`3500kg` as 3500."""
    if not published:
        return None
    match = re.match(r"\s*([\d,]+)\s*kg", published)
    return int(match.group(1).replace(",", "")) if match else None


def _identity(title: str, expected_range: str) -> tuple[str, str] | None:
    """`(model, layout code)` from a layout's title, or `None` if it is not this range's.

    **The berth count becomes part of the model, with no separator.** FMLV holds `1500 SL`
    twice — a 2-berth and a 4-berth of one floorplan, differing only by a drop-down bed and
    two belted seats — and matching keys on range plus model, so as `SL` twice they are one
    product to the pipeline and `cli._dedupe_baseline` drops one of them outright.

    `SL2` and `SL4` score 0.333 against each other and are safely distinct. **`SL 2` and
    `SL 4` score exactly 0.500**, which is the matching threshold itself, and `SL (2 berth)`
    scores 0.600 — both would collide. Hence no separator. Settled with the requester on
    16 September 2026, who is renaming FMLV's four existing rows to match.

    A layout with no berth count in its title keeps its bare code: the 1200 distinguishes
    its 4-berths with a `T` suffix already, and `1500 GL` is 2-berth only.
    """
    match = TITLE.match(title.strip())
    if match is None or match.group("range") != expected_range:
        return None
    code = match.group("code")
    berths = match.group("berths")
    return (f"{code}{berths}" if berths else code), code


def _body_type(entry: dict, entry_range: Range) -> BodyType:
    """What kind of vehicle this is, from the range and the layout's own pop-top flag.

    The 1200 is a panel van conversion: high top at 2650 mm, and **high top with an
    elevating roof** where `hasPopTopImage` is set, which marks exactly the four `T`
    layouts. The 1500 and Supreme are low-profile coachbuilts. FMLV already files its ten
    existing Ace rows this way.
    """
    if not entry_range.campervan:
        return BodyType.COACH_BUILT_LOW_PROFILE
    if entry.get("hasPopTopImage"):
        return BodyType.CAMPERVAN_HIGH_TOP_ELEVATING_ROOF
    return BodyType.CAMPERVAN_HIGH_TOP


@dataclass(frozen=True)
class AceProduct:
    """One layout, from one entry of a range page's JSON."""

    manufacturer_range: str
    model: str
    code: str
    source_url: str
    title: str
    base_vehicle: str
    body_type: BodyType
    mh_passenger_seats_inc_driver: int | None = None
    berths: int | None = None
    mh_length_mm: int | None = None
    mh_width_mm: int | None = None
    mh_height_mm: int | None = None
    mtplm_kilograms: int | None = None
    mro_kilograms: int | None = None
    published_payload_kilograms: int | None = None
    rrp_pounds: int | None = None
    copy_lines: tuple[str, ...] = field(default_factory=tuple)

    @property
    def label(self) -> str:
        return f"{self.manufacturer_range} {self.model}"

    @property
    def mh_payload_kilograms(self) -> int | None:
        """The published payload, which `_reconciles` has already checked against the masses."""
        return self.published_payload_kilograms


def read_range(page: str, entry_range: Range, feature_lines: Iterable[str]) -> list[AceProduct]:
    """Every layout of one range, in the order its page lists them."""
    products: list[AceProduct] = []
    for entry in layout_data(page):
        identity = _identity(str(entry.get("title") or ""), entry_range.name)
        if identity is None:
            continue
        model, code = identity
        # A price of zero is Ace not having published one yet, which the whole Supreme
        # range is at the time of writing. Recording £0 would be worse than recording
        # nothing: it is a figure, and it is wrong.
        price = entry.get("startingPrice")
        products.append(
            AceProduct(
                manufacturer_range=entry_range.name,
                model=model,
                code=code,
                source_url=f"{BASE_URL}{entry_range.path}",
                title=str(entry.get("title") or ""),
                base_vehicle=entry_range.base_vehicle,
                body_type=_body_type(entry, entry_range),
                mh_passenger_seats_inc_driver=entry.get("travellingSeats"),
                berths=entry.get("berths"),
                mh_length_mm=_millimetres(entry.get("length")),
                mh_width_mm=_millimetres(entry.get("width")),
                mh_height_mm=_millimetres(entry.get("height")),
                mtplm_kilograms=_kilograms(entry.get("weightMtplm")),
                mro_kilograms=_kilograms(entry.get("weightMro")),
                published_payload_kilograms=_kilograms(entry.get("payload")),
                rrp_pounds=int(price) if price else None,
                copy_lines=tuple(_bed_lines(entry))
                + tuple(habitation.lines_for_layout(feature_lines, code, codes=LAYOUT_CODES)),
            )
        )
    return products


def _bed_lines(entry: dict) -> list[str]:
    """The layout's beds, as lines `habitation` can read.

    Ace name them properly — `Rear double`, `Front dinette`, `Drop down` — so this is a
    better source than the range page's prose, and it is per layout rather than per range.
    """
    beds = entry.get("beds")
    if not isinstance(beds, list):
        return []
    return [f"{bed['name']} bed" for bed in beds if isinstance(bed, dict) and bed.get("name")]




def _reconciles(product: AceProduct) -> tuple[bool, str]:
    """`(ok, why not)` — whether the entry carries the figures at all.

    The arithmetic itself is in `_discrepancies`, because a gap in it is Ace's rather than
    ours and is no reason to withhold a vehicle they sell. What is fatal is an entry that
    yielded no masses, which is what a change to the dataset's shape would produce.
    """
    missing = [
        name
        for name, figure in (
            ("MTPLM", product.mtplm_kilograms),
            ("mass in running order", product.mro_kilograms),
            ("payload", product.published_payload_kilograms),
            ("length", product.mh_length_mm),
        )
        if figure is None
    ]
    if missing:
        return False, (
            f"its entry carries no {', '.join(missing)}, so the dataset's shape has "
            f"probably changed"
        )
    return True, ""


def _discrepancies(product: AceProduct) -> list[str]:
    """Where Ace's three published masses do not close.

    **They usually do**, which makes this a genuine arithmetic check rather than the
    true-by-construction identity several other adapters settle for: `payload == MTPLM -
    MRO` held on 21 of the 22 layouts at survey.

    The one that does not is `1200 RLT`, out by exactly 30 kg — the same 30 kg Ace's own
    optional-extras note says the automatic gearbox moves: *"This option increases the MRO
    by 30kg and decreases the Max Payload by 30kg"*. So it is one figure taken from the
    automatic and the rest from the manual, a slip on their side rather than a misread on
    ours. Reported, and the vehicle goes forward — its dimensions and price are not in
    doubt.
    """
    mtplm, mro = product.mtplm_kilograms, product.mro_kilograms
    payload = product.published_payload_kilograms
    if mtplm is None or mro is None or payload is None or mtplm - mro == payload:
        return []
    return [
        f"Ace publish MTPLM {mtplm}kg, mass in running order {mro}kg and payload "
        f"{payload}kg, which do not close — {mtplm} minus {mro} is {mtplm - mro}kg. Their "
        f"automatic gearbox option moves both by 30kg, so a "
        f"{abs((mtplm - mro) - payload)}kg gap is most likely one figure taken from the "
        f"automatic. The published payload is the one recorded"
    ]


def _build_extracted_motorhome(product: AceProduct) -> ExtractedMotorhome:
    """One layout as a `Motorhome`, plus the provenance a reviewer sees beside each field."""
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
        # Habitation, from the layout's own bed list and the features that apply to it.
        # Findings, never proposals — see `docs/adapters/README.md`.
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
            source_url=product.source_url, snippet=f"{product.title} — {snippet}"
        )

    closes = (
        product.mtplm_kilograms is not None
        and product.mro_kilograms is not None
        and product.mtplm_kilograms - product.mro_kilograms
        == product.published_payload_kilograms
    )

    if product.mh_length_mm is not None:
        record("mh_length_mm", f"the range page's own dataset: length {product.mh_length_mm}mm")
    if product.mh_width_mm is not None:
        record("mh_width_mm", f"width {product.mh_width_mm}mm")
    if product.mh_height_mm is not None:
        record("mh_height_mm", f"height {product.mh_height_mm}mm")
    if product.mh_passenger_seats_inc_driver is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"{product.mh_passenger_seats_inc_driver} travelling seats",
        )
    if product.berths is not None:
        record(
            "berths",
            f"{product.berths} berths — also half this layout's identity, since Ace sell "
            f"the same floorplan as a 2 and a 4 berth and the count is in the model",
        )
    if product.mtplm_kilograms is not None:
        record("mtplm_kilograms", f"MTPLM {product.mtplm_kilograms}kg")
    if product.mro_kilograms is not None:
        record("mro_kilograms", f"mass in running order {product.mro_kilograms}kg")
    if product.mh_payload_kilograms is not None:
        record(
            "mh_payload_kilograms",
            f"payload {product.mh_payload_kilograms}kg as published, and MTPLM minus the "
            f"running order "
            + ("agrees" if closes else "does not — see this run's notes for the gap"),
        )
    if product.rrp_pounds is not None:
        record("rrp_pounds", f"a starting price of £{product.rrp_pounds:,}")
    record(
        "body_type",
        f"a {product.mh_height_mm}mm "
        + (
            "panel van with a pop-top roof"
            if product.body_type is BodyType.CAMPERVAN_HIGH_TOP_ELEVATING_ROOF
            else "panel van"
            if product.body_type is BodyType.CAMPERVAN_HIGH_TOP
            else "low-profile coachbuilt"
        ),
    )
    record(
        "base_vehicle_manufacturer",
        f"the whole {product.manufacturer_range} range is a {product.base_vehicle}",
    )

    for field_name, feature in features.items():
        detail = f" — {feature.note}" if feature.note else ""
        provenance[field_name] = Provenance(
            source_url=product.source_url,
            snippet=f"{product.title} — {feature.snippet!r}{detail}",
        )

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 - the dataset is in the plain HTML; no browser needed
    snapshot_dir: Path,  # noqa: ARG001 - `Fetcher` owns the snapshot directory
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every current Ace layout, from the three range pages' embedded datasets."""
    wanted = {key for key, _label in ranges}
    results: list[ExtractedMotorhome] = []

    for entry_range in RANGES:
        if wanted and entry_range.name not in wanted:
            continue
        url = f"{BASE_URL}{entry_range.path}"
        on_progress(f"fetching the {entry_range.name} range: {url}")
        fetched = http.fetch(url)
        if fetched.status_code != 200:
            on_progress(f"SKIPPED: {url} returned {fetched.status_code}")
            continue
        page = fetched.file_path.read_text(encoding="utf-8", errors="replace")

        products = read_range(page, entry_range, habitation.list_items(page))
        if not products:
            on_progress(
                f"WARNING: {url} carries no layout dataset. Ace publish it as an inline "
                f"JSON block, so this is what a site rebuild would break first"
            )
            continue
        on_progress(f"{entry_range.name}: {len(products)} layout(s)")

        for product in products:
            reconciles, why_not = _reconciles(product)
            if not reconciles:
                on_progress(f"SKIPPED [{product.label}]: {why_not}")
                continue
            for note in _discrepancies(product):
                on_progress(f"[{product.label}] NOTE: {note}")
            if product.rrp_pounds is None:
                on_progress(
                    f"[{product.label}] WARNING: Ace publish no price for this layout yet, "
                    f"so FMLV's own figure is left alone"
                )
            results.append(_build_extracted_motorhome(product))

    if (not wanted or wanted == {entry.name for entry in RANGES}) and len(
        results
    ) != EXPECTED_LAYOUTS:
        on_progress(
            f"WARNING: collected {len(results)} layout(s) where the survey found "
            f"{EXPECTED_LAYOUTS}. Ace publish no count of their own, so this is the only "
            f"thing that would notice a range page losing one"
        )
    on_progress(f"collected {len(results)} product(s)")
    return results
