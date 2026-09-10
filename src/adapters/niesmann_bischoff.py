"""Niesmann + Bischoff (niesmann-bischoff.com) — an Erwin Hymer Group brand, configurator only.

See `docs/adapters/niesmann-bischoff.md` for the full survey. Three ranges, seven layouts,
£110,220 to £208,800 — the most expensive brand in the project, and the only one whose data
lives entirely behind a configurator.

**Not the shared EHG configurator** that Eriba, Dethleffs, Bürstner and Carado use. This is
a bespoke React application, and `ehg_configurator` does not reach it. But the application
is only a front end: behind it is plain unauthenticated JSON, and **one call per range
returns every layout with almost everything FMLV needs** — price, both masses, all three
dimensions, seats, the floorplan, and a `details` list that is a full technical
specification.

**Nothing here is hardcoded that the site can change.** The bundle's filename carries a
build hash, so the adapter reads the configurator page for the script, the script for the
backend's base URL, and only then the data. Three fetches before the first layout, and a
redeploy of their site cannot silently point this at a stale host.

**The importer publishes nothing, so the factory is the price source.** Travelworld is the
UK importer — the NCC supplier name says `Niesmann + Bischoff shown by Travelworld` — but
their site is a 114-byte placeholder, and the requester ruled on 9 September 2026 that
their listings are individual stock vehicles anyway: *"they say they're new, but they are
different variants. I think we have to go from the manufacturer's spec rather than stock
spec."* The prices are sterling under `lang=en`, checked against FMLV's own figures.
"""

from __future__ import annotations

import ast
import json
import re
from collections.abc import Callable, Iterable
from urllib.parse import quote
from dataclasses import dataclass, field
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from . import habitation
from .base import (
    ExtractedMotorhome,
    Provenance,
    floorplan_provenance,
    fmlv_base_vehicle,
)

BASE_URL = "https://configurator.niesmann-bischoff.com"
MANUFACTURER = "Niesmann + Bischoff"
MANUFACTURER_DISPLAY_NAME = "Niesmann + Bischoff"

#: The three ranges, as the API's `modell` parameter spells them. Also the FMLV range, and
#: also `--range`'s label — the one manufacturer where all three agree.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (
    ("Arto", "Arto"),
    ("Flair", "Flair"),
    ("iSmove", "iSmove"),
)

#: Niesmann + Bischoff build **nothing but A-class integrated motorhomes** — there is no
#: low profile, no over-cab and no van in the range, and FMLV holds all six of its current
#: products as `type_a_class`. Stated as a map per range rather than a blanket constant so
#: that a range which is not one classifies itself as unknown instead of being mislabelled.
BODY_TYPES: dict[str, BodyType] = {
    "Arto": BodyType.A_CLASS,
    "Flair": BodyType.A_CLASS,
    "iSmove": BodyType.A_CLASS,
}

#: Where the layout drawings live. `imgGalleryFilename` is the per-layout one; the
#: `thumbFilename` beside it is **not** — Flair 880 and 920 share `cart_flair_2022.png`,
#: and both iSmoves share `cart_ismove.png`.
FLOORPLAN_PATH = "/assets/02-grundrisse/"

#: The configurator's own page, which names the bundle.
CONFIGURATOR_URL = f"{BASE_URL}/"

#: The bundle, whose filename carries a build hash that changes on every deploy.
_BUNDLE_SRC = re.compile(r'<script[^>]+src="(?P<src>/static/js/main\.[0-9a-f]+\.js)"')

#: The backend's base URL, as the bundle declares it. Note the host differs from the page's
#: by one letter — the app is served from **c**onfigurator and the API from
#: **k**onfigurator — which is exactly the sort of thing not to type from memory.
_BACKEND_BASE = re.compile(r'"(?P<base>https://[a-z0-9.-]*niesmann-bischoff\.com/backend)"')

#: `?modell=<range>&lang=en` — the call that returns a range's layouts. Every sibling
#: endpoint (`technik`, `chassis`, `aufbau`, `interieur`, `exterieur`, `pakete`,
#: `auflastung`) takes `&grundriss=<layout>` as well, and none of them is needed: the
#: layout record already carries the specification.
LAYOUTS_PATH = "/data/grundriss"

#: The equipment endpoint, `?modell=<range>&grundriss=<layout>&lang=en`. Its
#: `[Heating, Air Conditioning System]` group is the only place Niesmann say what heating
#: a layout has — the layout record itself carries the numbers and nothing habitational.
EQUIPMENT_PATH = "/data/technik"

#: **The flag that separates standard equipment from a paid extra.** Every item carries
#: `serie: True` or `serie: False`, and the configurator is an options catalogue, so
#: without this the adapter would report the fridge and microwave a buyer *may* add as
#: though they were fitted. `/data/interieur` has **zero** `serie: True` items — its
#: kitchen fridge and its 800-watt microwave are both upgrades — which is exactly the
#: reading that would have been wrong.
STANDARD_FLAG = "serie"

#: The market. Under `lang=en` the prices come back in sterling — established by comparing
#: all six against FMLV's own figures, which they exceed by 1.7 to 4.4 per cent. A euro
#: figure would be 15 to 20 per cent out. See the survey.
LANGUAGE = "en"


# --------------------------------------------------------------------------- #
# Reading the API's own address out of the site
# --------------------------------------------------------------------------- #


def parse_bundle_src(page_html: str) -> str | None:
    """The configurator's script, whose name carries a build hash."""
    match = _BUNDLE_SRC.search(page_html)
    return match.group("src") if match else None


def parse_backend_base(bundle_js: str) -> str | None:
    """The API's base URL, as the bundle declares it.

    Read rather than hardcoded, and the bundle also contains the developers' own staging
    hosts (`nibi-konfigurator.alpha.3st-dev.de`), so the pattern is anchored to the real
    domain rather than taking the first `/backend` it finds.
    """
    match = _BACKEND_BASE.search(bundle_js)
    return match.group("base") if match else None


def _decode(body: str) -> object | None:
    """The JSON in a response that may carry PHP notices before or after it.

    The backend emits `<br /><b>Notice</b>: Uninitialized string offset…` ahead of the
    payload when a parameter is missing, and trailing output after it — so a plain
    `json.loads` fails on responses that are otherwise perfectly good. This finds the
    document and stops at its end.
    """
    start = min((index for index in (body.find("{"), body.find("[")) if index >= 0), default=-1)
    if start < 0:
        return None
    try:
        return json.JSONDecoder().raw_decode(body[start:])[0]
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# One layout
# --------------------------------------------------------------------------- #

#: A `details` entry's label and value, both of which arrive with markup in them. The
#: label runs its section and its row together (`BedsRear bed(s) (length × width)`), which
#: is why `_label` splits the section off rather than matching the whole string.
_TAG = re.compile(r"<[^>]+>")

#: A dimension pair, `2,065 × 735` — and the site uses both `×` and a plain `x`.
_DIMENSION_PAIR = re.compile(r"([\d.,]+)\s*[×x]\s*([\d.,]+)")

#: A bed row in `details`. `Rear bed(s)` may hold two beds separated by a slash.
_BED_ROW = re.compile(r"\bbed\b", re.I)

#: Narrower than this and a bed sleeps one. Two Niesmann singles are 730 and 735 mm and
#: every double is 1,280 or wider, so the threshold sits in a gap of 545 mm — wide enough
#: that no plausible bed lands near it.
DOUBLE_BED_FROM_MM = 1200

#: The rows the self-check reads, as `(structured field, the text of its `details` row)`.
#: Every one of these figures is published **twice in the same response**, which is what
#: lets a parse be checked without a second source. See `_reconciles`.
_RESTATED: tuple[tuple[str, str], ...] = (
    ("weight", "Mass in running order"),
    ("totalMass", "Technically permissible laden mass"),
    ("length", "Overall length"),
    ("width", "Overall width"),
    ("height", "Overall height"),
)

LABEL_BASE_VEHICLE = "Base vehicle"
LABEL_GARAGE = "garage"


def _text(markup: str) -> str:
    return re.sub(r"\s+", " ", _TAG.sub(" ", markup)).strip()


def _number(value: str) -> int | None:
    """`'2,065'` -> `2065`. Thousands commas throughout, and no decimals in any figure."""
    digits = re.sub(r"[^\d]", "", value.split("(")[0])
    return int(digits) if digits else None


def detail_pairs(details: object) -> list[tuple[str, str]]:
    """The `details` list as `(label, value)`, in order.

    It arrives as a **Python literal inside a JSON string** — single-quoted dicts, which
    `json.loads` will not read — so it is parsed with `ast.literal_eval` and anything
    unparseable yields nothing rather than raising.
    """
    if isinstance(details, str):
        try:
            details = ast.literal_eval(details)
        except (ValueError, SyntaxError):
            return []
    if not isinstance(details, list):
        return []
    return [
        (_text(str(entry.get("dt", ""))), _text(str(entry.get("dd", ""))))
        for entry in details
        if isinstance(entry, dict)
    ]


def berths_from(pairs: Iterable[tuple[str, str]]) -> int | None:
    """How many the layout sleeps, counted off the published bed dimensions.

    **A derivation, and the requester approved it on 9 September 2026**: *"the fact that
    there are two double beds is our best guidance on the berths, so that would be four."*
    The API states bed sizes and never a berth count, and FMLV holds 4 for all six existing
    products — which this reproduces on all seven, including the iSmove 6.9 E where the
    rear is two singles rather than a double.

    Each dimension pair is one bed and its width decides whether it sleeps one or two;
    `Rear bed(s)` may hold two, slash-separated. `None` when no bed row is published at
    all, rather than a confident zero.
    """
    berths = 0
    found = False
    for label, value in pairs:
        if not _BED_ROW.search(label):
            continue
        for _length, width in _DIMENSION_PAIR.findall(value):
            measured = _number(width)
            if measured is None:
                continue
            found = True
            berths += 2 if measured >= DOUBLE_BED_FROM_MM else 1
    return berths if found else None


def parse_standard_equipment(payload: str) -> list[str]:
    """Every item a layout has **as standard**, category prefixed, from `/data/technik`.

    Options are dropped on the `serie` flag — see `STANDARD_FLAG`. The category is kept on
    the line so a reviewer reading the quote can see where it came from:
    `Heating, Air Conditioning System: Warm water heating with thermostat…`.
    """
    data = _decode(payload)
    if not isinstance(data, dict):
        return []
    lines: list[str] = []
    for group in data.get("items") or []:
        if not isinstance(group, dict):
            continue
        category = _text(str(group.get("title", "")))
        inner = group.get("items")
        if isinstance(inner, str):
            try:
                inner = ast.literal_eval(inner)
            except (ValueError, SyntaxError):
                inner = []
        for item in inner or []:
            if not isinstance(item, dict) or item.get(STANDARD_FLAG) is not True:
                continue
            title = _text(str(item.get("title", "")))
            if title:
                lines.append(f"{category}: {title}" if category else title)
    return lines


@dataclass(frozen=True)
class NbLayout:
    """One layout, as `/data/grundriss` returns it."""

    range_name: str
    title: str
    raw: dict[str, object] = field(default_factory=dict)

    @property
    def pairs(self) -> list[tuple[str, str]]:
        return detail_pairs(self.raw.get("details"))

    def _detail(self, needle: str) -> str | None:
        for label, value in self.pairs:
            if needle.lower() in label.lower():
                return value
        return None

    @property
    def fmlv_model(self) -> str:
        """`Arto 78` -> `78`, `iSmove 6.9 E` -> `6.9E`.

        The range is the first word and the model is the rest. The space is closed **only**
        between a number and a single trailing letter, which is the one difference between
        the API's spelling and FMLV's (`6.9 E` against `6.9E`) — a blanket strip would
        mangle any future multi-word model.
        """
        rest = self.title[len(self.range_name) :].strip() if self.title.startswith(
            self.range_name
        ) else self.title
        return rest.replace(" ", "") if re.fullmatch(r"[\d.]+ [A-Za-z]", rest) else rest

    @property
    def rrp_pounds(self) -> int | None:
        return _number(str(self.raw.get("price", "")))

    @property
    def mro_kilograms(self) -> int | None:
        return _number(str(self.raw.get("weight", "")))

    @property
    def mtplm_kilograms(self) -> int | None:
        return _number(str(self.raw.get("totalMass", "")))

    @property
    def mh_payload_kilograms(self) -> int | None:
        """`MTPLM - MRO`. Niesmann publish no payload, and their `Manufacturer-specified
        mass for optional equipment` row is **not** one — the trap Dethleffs, Etrusco,
        Bürstner, Sunlight and Carado all share."""
        if self.mtplm_kilograms is None or self.mro_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mro_kilograms

    @property
    def mh_length_mm(self) -> int | None:
        return _number(str(self.raw.get("length", "")))

    @property
    def mh_width_mm(self) -> int | None:
        return _number(str(self.raw.get("width", "")))

    @property
    def mh_height_mm(self) -> int | None:
        return _number(str(self.raw.get("height", "")))

    @property
    def seats_published(self) -> str | None:
        """The belt row, verbatim — `'2 (opt. 3, 4 or 5)'`, which the provenance quotes."""
        return self._detail("3-point safety belt")

    @property
    def mh_passenger_seats_inc_driver(self) -> int | None:
        """The **standard** number of three-point belts.

        Two settled rules meet here and agree: count three-point belts only, and record the
        base vehicle's figure rather than an optioned variant's. So `2 (opt. 3, 4 or 5)` is
        two. FMLV holds 4 for these products today, so expect a correction on every one —
        flagged in the survey because it changes every listing.
        """
        return _number(self.seats_published or str(self.raw.get("seats", "")))

    @property
    def berths(self) -> int | None:
        return berths_from(self.pairs)

    @property
    def base_vehicle_published(self) -> str | None:
        return self._detail(LABEL_BASE_VEHICLE)

    @property
    def base_vehicle_manufacturer(self) -> str | None:
        """The make, spelled FMLV's way — `Mercedes Benz 415 CDI` becomes `Mercedes`."""
        published = self.base_vehicle_published
        return fmlv_base_vehicle(published.split()[0]) if published else None

    @property
    def rear_garage(self) -> bool:
        """Whether a garage is published, which for this brand is the whole test.

        A proposed value rather than a finding, as the requester directed: every layout
        that has one publishes `Maximum garage height` and `Maximum available surface`.
        """
        return any(LABEL_GARAGE in label.lower() for label, _value in self.pairs)

    @property
    def floorplan_path(self) -> str | None:
        filename = str(self.raw.get("imgGalleryFilename") or "").strip()
        return FLOORPLAN_PATH + filename if filename else None

    @property
    def body_type(self) -> BodyType | None:
        return BODY_TYPES.get(self.range_name)


def parse_layouts(range_name: str, payload: str) -> list[NbLayout]:
    """Every layout in one range, from a `/data/grundriss` response."""
    data = _decode(payload)
    if not isinstance(data, dict):
        return []
    items = data.get("items")
    if not isinstance(items, list):
        return []
    layouts = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = _text(str(item.get("title", "")))
        if title:
            layouts.append(NbLayout(range_name=range_name, title=title, raw=item))
    return layouts


def _reconciles(layout: NbLayout) -> list[str]:
    """The figures whose two published values disagree — empty when the parse is sound.

    Every key number appears **twice in the same response**: once as a structured field and
    once as a prose row in `details`. That is a genuine redundancy rather than an
    arithmetic identity, so it catches a field read from the wrong place, which the printed
    ±5% mass band cannot.
    """
    disagreements = []
    for key, needle in _RESTATED:
        structured = _number(str(layout.raw.get(key, "")))
        restated = _number(layout._detail(needle) or "")
        if structured is not None and restated is not None and structured != restated:
            disagreements.append(f"{needle} ({structured} vs {restated})")
    return disagreements


# --------------------------------------------------------------------------- #
# Building a product
# --------------------------------------------------------------------------- #


#: How each habitation reading is introduced where `habitation` supplies no wording.
_FEATURE_NOTES: dict[str, str] = {
    "heating": "the heating fitted as standard",
    "refrigeration": "the refrigeration fitted as standard",
    "shower_toilet_separated": "the washroom fitted as standard",
}

#: Why a microwave is reported absent — and note how narrow the claim is. Niesmann **do**
#: offer one, as a priced option (`Microwave (230V, 800 watts, mounted behind cupboard
#: door)`), so this says only that none is fitted as standard. The check is given the
#: standard list alone, so the option neither triggers nor suppresses it; the wording
#: carries the nuance instead.
MICROWAVE_ABSENCE_NOTE = (
    "no microwave in the standard equipment. Niesmann do offer one as a priced option, so "
    "this says it is not fitted as standard rather than that it cannot be had"
)


def build_extracted(
    layout: NbLayout, equipment: list[str] | None = None
) -> ExtractedMotorhome:
    """One product, from one layout record and its standard-equipment list."""
    features = habitation.features_from(equipment or [])
    # `False` rather than left unset, so `findings.SILENCE_MEANS` does not append its
    # generic "no mention anywhere" reasoning — which would be wrong here. Niesmann
    # publish a microwave; it is simply not standard. See `MICROWAVE_ABSENCE_NOTE`.
    no_microwave = bool(equipment) and habitation.microwave_from(equipment) is None
    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=layout.range_name,
        model=layout.fmlv_model,
        base_vehicle_manufacturer=layout.base_vehicle_manufacturer,
        body_type=layout.body_type,
        rrp_pounds=layout.rrp_pounds,
        berths=layout.berths,
        mh_passenger_seats_inc_driver=layout.mh_passenger_seats_inc_driver,
        mro_kilograms=layout.mro_kilograms,
        mtplm_kilograms=layout.mtplm_kilograms,
        mh_payload_kilograms=layout.mh_payload_kilograms,
        mh_length_mm=layout.mh_length_mm,
        mh_width_mm=layout.mh_width_mm,
        mh_height_mm=layout.mh_height_mm,
        rear_garage=layout.rear_garage,
        # Habitation, from the standard equipment only — reported as findings rather than
        # proposed. See `parse_standard_equipment` for why the `serie` flag matters.
        heating=features["heating"].value if "heating" in features else None,
        refrigeration=(
            features["refrigeration"].value if "refrigeration" in features else None
        ),
        shower_toilet_separated=(
            features["shower_toilet_separated"].value
            if "shower_toilet_separated" in features
            else None
        ),
        microwave=False if no_microwave else None,
    )

    label = layout.title
    source = f"{BASE_URL}/"
    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str, *, url: str = source) -> None:
        provenance[field_name] = Provenance(source_url=url, snippet=f"{label} — {snippet}")

    identity = (
        f"the configurator publishes this layout as '{layout.title}'; FMLV holds range "
        f"'{layout.range_name}' and model '{layout.fmlv_model}'. The two halves belong "
        f"together — accept both or neither"
    )
    record("manufacturer_range", identity)
    record("model", identity)

    if layout.rrp_pounds is not None:
        record(
            "rrp_pounds",
            f"£{layout.rrp_pounds:,} from the manufacturer's configurator in its English "
            f"edition. Travelworld, the UK importer, publish only individual stock "
            f"vehicles, so this is the model's price rather than one van's",
        )
    if layout.base_vehicle_manufacturer is not None:
        record("base_vehicle_manufacturer", f"Base vehicle: {layout.base_vehicle_published}")
    if layout.body_type is not None:
        record(
            "body_type",
            "Niesmann + Bischoff build only A-class integrated motorhomes — there is no "
            "low profile, over-cab or van in the range",
        )
    if layout.berths is not None:
        beds = "; ".join(
            f"{label}: {value}" for label, value in layout.pairs if _BED_ROW.search(label)
        )
        record(
            "berths",
            f"counted from the published bed sizes, a bed {DOUBLE_BED_FROM_MM}mm or wider "
            f"sleeping two — {beds}. The configurator states bed dimensions and never a "
            f"berth count",
        )
    if layout.mh_passenger_seats_inc_driver is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"Seats fitted with 3-point safety belt: '{layout.seats_published}' — the "
            f"standard figure, the rest being options, and lap belts are never counted",
        )
    for field_name, needle in (
        ("mh_length_mm", "Overall length"),
        ("mh_width_mm", "Overall width"),
        ("mh_height_mm", "Overall height"),
    ):
        if getattr(motorhome, field_name) is not None:
            record(field_name, f"{needle}: {layout._detail(needle)}")
    if layout.mtplm_kilograms is not None:
        record(
            "mtplm_kilograms",
            f"Technically permissible laden mass: "
            f"{layout._detail('Technically permissible laden mass')}",
        )
    if layout.mro_kilograms is not None:
        record(
            "mro_kilograms",
            f"Mass in running order: {layout._detail('Mass in running order')}",
        )
    if layout.mh_payload_kilograms is not None:
        record(
            "mh_payload_kilograms",
            f"derived: {layout.mtplm_kilograms}kg permissible laden - "
            f"{layout.mro_kilograms}kg running order = {layout.mh_payload_kilograms}kg. "
            f"Niesmann publish no payload, and their 'manufacturer-specified mass for "
            f"optional equipment' is not one",
        )
    record(
        "rear_garage",
        (
            f"the specification publishes garage dimensions — "
            f"{layout._detail('Maximum garage height')} high"
            if layout.rear_garage
            else "the specification publishes no garage dimensions"
        ),
    )

    for name, feature in features.items():
        note = feature.note or _FEATURE_NOTES.get(name, "listed as standard equipment")
        record(name, f"{note}: {feature.snippet}")
    if equipment:
        unclear = habitation.heating_is_unclear(equipment)
        if unclear and "heating" not in features:
            record("heating", f"a heater is listed but its kind is not named: {unclear}")
        if no_microwave:
            record("microwave", MICROWAVE_ABSENCE_NOTE)

    if layout.floorplan_path:
        provenance.update(
            floorplan_provenance(motorhome, BASE_URL + layout.floorplan_path, label)
        )
    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 — the JSON needs no browser; see the module docstring
    snapshot_dir: Path,  # noqa: ARG001 — `http` already snapshots into it
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """The configurator page for the bundle, the bundle for the API, then one call a range.

    The first two fetches are what make the third safe: the bundle's name carries a build
    hash and the API lives on a different host from the page, so both are discovered rather
    than remembered. Either failing raises — without the base URL there is no data at all,
    and collecting nothing silently would look like a discontinued brand.
    """
    on_progress(f"fetching the configurator {CONFIGURATOR_URL} ...")
    page = http.fetch(CONFIGURATOR_URL)
    if page.status_code != 200:
        msg = f"{CONFIGURATOR_URL} returned {page.status_code}"
        raise RuntimeError(msg)
    src = parse_bundle_src(page.file_path.read_text(encoding="utf-8", errors="replace"))
    if src is None:
        msg = f"no configurator bundle found on {CONFIGURATOR_URL}"
        raise RuntimeError(msg)

    on_progress(f"reading the API's address out of {src} ...")
    bundle = http.fetch(BASE_URL + src)
    if bundle.status_code != 200:
        msg = f"{BASE_URL + src} returned {bundle.status_code}"
        raise RuntimeError(msg)
    backend = parse_backend_base(bundle.file_path.read_text(encoding="utf-8", errors="replace"))
    if backend is None:
        msg = f"no backend base URL declared in {src}"
        raise RuntimeError(msg)
    on_progress(f"the API is at {backend}")

    results: list[ExtractedMotorhome] = []
    for range_name, label in ranges:
        url = f"{backend}{LAYOUTS_PATH}?modell={range_name}&lang={LANGUAGE}"
        response = http.fetch(url)
        if response.status_code != 200:
            on_progress(f"[{label}] SKIPPED: {url} returned {response.status_code}")
            continue
        layouts = parse_layouts(
            range_name, response.file_path.read_text(encoding="utf-8", errors="replace")
        )
        if not layouts:
            # A stated roster beats a heuristic: a range that stops returning layouts is
            # narrated rather than quietly reducing the product count.
            on_progress(f"[{label}] WARNING: the API returned no layouts")
            continue
        on_progress(f"[{label}] {len(layouts)} layout(s)")

        for layout in layouts:
            disagreements = _reconciles(layout)
            if disagreements:
                on_progress(
                    f"[{layout.title}] SKIPPED: the record states these twice and the two "
                    f"disagree — {', '.join(disagreements)}"
                )
                continue
            for name, value in (
                ("price", layout.rrp_pounds),
                ("running order mass", layout.mro_kilograms),
                ("berths", layout.berths),
                ("base vehicle", layout.base_vehicle_manufacturer),
            ):
                if value is None:
                    on_progress(f"[{layout.title}] WARNING: no {name} published, left blank")
            if layout.floorplan_path is None:
                on_progress(f"[{layout.title}] no floorplan published")
            # One extra call a layout, for the only habitation the brand publishes.
            # Never fatal: a failure costs the findings and nothing else.
            equipment: list[str] = []
            kit_url = (
                f"{backend}{EQUIPMENT_PATH}?modell={range_name}"
                f"&grundriss={quote(layout.title)}&lang={LANGUAGE}"
            )
            kit = http.fetch(kit_url)
            if kit.status_code == 200:
                equipment = parse_standard_equipment(
                    kit.file_path.read_text(encoding="utf-8", errors="replace")
                )
            if not equipment:
                on_progress(f"[{layout.title}] no standard equipment read, so no findings")
            results.append(build_extracted(layout, equipment))

    on_progress(f"{len(results)} product(s) collected")
    return results
