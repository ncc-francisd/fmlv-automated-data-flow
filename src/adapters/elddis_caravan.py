"""Elddis touring caravans, from the brand's own configurator API.

The sibling of `elddis.py`, and a separate module rather than a flag on it: FMLV keeps
motorhomes and touring caravans as separate exports with separate schemas, so this one
produces `Caravan`s and registers under `("Elddis (EHG UK)", caravan)`. See
`docs/adapters/elddis-caravan.md` for the survey this was built from.

**Why it exists at all.** On 26 November 2026 `elddis.py` reported a range it did not
recognise, `Riviera`, and collecting it would have filed five touring caravans as
motorhomes — 1800kg, no travel seats, no price. The motorhome adapter now drops caravan
series by the API's own `vehicleType`; this module is where they go instead.

**The source is the same two endpoints as the motorhome side**, so there is no browser, no
PDF and no price list::

    /configurator-api/brand/elddis/series   -> Riviera, vehicleType=caravan, modelYear 2027
    /configurator-api/series/<id>/models    -> five layouts with technicalData

## Elddis have not launched this range, and the adapter says so every run

Every layout comes back `available: false` and `availableForWebsite: false`, with
`grossPrice: null` and no `layoutImage`. `elddis.co.uk` links no Riviera page — which is
why the requester could find the range on social media and not on the site.

**They are collected and emitted anyway**, on the requester's instruction of 26 November
2026: *"it looks like we're going to have to enter those as new models, but yeah, build
them, and then the moment they go on their website we will activate them, and probably
not before."* FMLV's staging state is an inactive product, not an absent one — see the
settled rule that an inactive product is one in progress — so the right place for an
unlaunched model is a row somebody has created and not yet switched on.

`UNPUBLISHED_WARNING` is therefore narrated once per affected layout rather than used to
drop it, and it names the flag it read so a reviewer knows what they are looking at.

## What the API publishes, and what it does not

Confirmed against **Eriba**, which is the same API and whose caravans FMLV already holds,
by matching layouts on their two masses and comparing every dimension. On the eighteen
2027 Eriba layouts:

| API field | FMLV field | agreement |
|---|---|---|
| `lengthOverall` | `shipping_length_mm` | 17 of 18 exact |
| `heightOverall` | `height_mm` | 17 of 18 exact |
| `headroomLivingArea` | `headroom_mm` | 18 of 18 exact |

The single disagreement in each of the first two columns is one layout whose masses
collide with an earlier model year's row, not a mapping failure.

**That settles the trap `docs/adapters/README.md` names as the most likely way to get a
caravan adapter wrong.** A caravan has four lengths and they are not interchangeable;
`lengthOverall` is the shipping length — body plus drawbar — and mapping it to
`internal_length_mm` would overstate every caravan's habitable space by well over a metre
while looking entirely plausible on any one product. Eriba's API says 506cm for a Touring
310 and FMLV holds `shipping_length_mm=5060, internal_length_mm=3660`.

Not published anywhere in the payload, so not emitted:

* **No price.** `grossPrice` is `null` on all five.
* **No internal or body length**, and no awning size.
* **No axle count**, so `twin_axle` is left alone — see `build_extracted`.
* **No nose weight.** `trailingLoadMax` and `trailingLoadMaxUnrestrained` are present and
  empty on every layout, which is a label with no value rather than a figure.
* **No equipment of any kind**, so the kitchen, washroom, lounge, heating, refrigeration
  and microwave findings cannot be reported. The motorhome adapter gets those from the
  public site, one page per layout, and the Riviera has no pages.
* **No floorplan.** `layoutImage` is `null`, as it is for every Elddis motorhome layout.

## The self-check

`_reconciles`, shared in spirit with the motorhome side: Elddis publish no payload row, so
there is no third figure, and what can be tested is the arithmetic the two masses imply. A
mass in running order at or above the permissible maximum, or a payload outside what a
caravan of this size can carry, means a figure came from the wrong field.

`manufacturerSpecifiedWeightForOptionalEquipment` is read alongside it and deliberately
**not** recorded as the payload: it is the allowance for factory-fitted options, not the
user payload, and on the 580 FL the two are 438kg and 535kg. It is narrated so the
difference is visible rather than rediscovered.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..fetch.http import Fetcher
from ..product_model.caravan import Caravan
from ..product_model.enums import BedType, CaravanBodyType, CaravanSleepingArea
from ..vehicle_class import VehicleClass
from . import ehg_configurator as ehg
from .base import ExtractedCaravan, Provenance

__all__ = [
    "BED_TYPES_BY_CONFIGURATOR_NAME",
    "DEFAULT_RANGES",
    "EXPECTED_LAYOUTS",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "UNPUBLISHED_WARNING",
    "VEHICLE_CLASS",
    "ElddisCaravanLayout",
    "beds_from",
    "build_extracted",
    "collect",
    "parse_layouts",
    "sleeping_area_from",
]

BASE_URL = "https://elddis.co.uk"
MANUFACTURER = "Elddis (EHG UK)"
MANUFACTURER_DISPLAY_NAME = "Elddis"

#: What makes this the caravan adapter rather than a second motorhome one.
VEHICLE_CLASS = VehicleClass.CARAVAN

#: The key the configurator API knows this brand by. Lower case exactly — `ELDDIS` answers
#: `There is no brand for brandKey ELDDIS`. The same brand serves both product areas; the
#: series index carries motorhomes, campervans and caravans together and is separated on
#: `vehicleType`.
BRAND_KEY = "elddis"

#: The 2027 caravan range: one series, five layouts. Reconciled against the API on every
#: full sweep rather than trusted, the same way `elddis.DEFAULT_RANGES` is.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (("Riviera", "Riviera"),)

EXPECTED_LAYOUTS = 5

#: What a caravan of this size can credibly carry. Wider than the published spread
#: deliberately: the five Rivieras imply 465-620kg, and the band is here to catch a figure
#: read out of the wrong field, not to second-guess a published one.
_PAYLOAD_RANGE = (50, 1200)

#: The configurator's bed vocabulary, mapped to FMLV's. Extends the six `eriba_caravan`
#: established with the three the Riviera adds — `single-bed`, `single-to-double-bed` and
#: `queen-bed`. Kept here rather than imported from Eriba so neither brand's additions can
#: silently change the other's reading; every overlapping entry agrees with Eriba's.
#:
#: `single-to-double-bed` is the infill that turns two fixed singles into one double. It is
#: `isOptional: yes` on both layouts that offer it and is excluded from the finding for
#: that reason rather than for what it is — the settled rule being that a bed needing
#: something fitted is not the standard configuration.
BED_TYPES_BY_CONFIGURATOR_NAME: dict[str, BedType] = {
    "seating-group-bed": BedType.MAKE_UP,
    "twin-bed": BedType.FIXED_SEPARATE,
    "single-bed": BedType.FIXED_SEPARATE,
    "bunk-bed": BedType.FIXED_BUNKS,
    "double-bed": BedType.FIXED,
    "french-bed": BedType.FIXED,
    "queen-bed": BedType.FIXED,
    "v-bed": BedType.FIXED,
    "single-to-double-bed": BedType.FIXED,
}

#: Where the configurator says a bed is installed, mapped to the end of the caravan FMLV
#: means. `middle` is a seating-group bed in a mid lounge; it is neither end, so it is
#: **not** treated as one — a layout whose only other bed is at the front reads `front`,
#: which is what a person looking at the drawing would say.
_FRONT, _REAR = "front", "rear"

#: Narrated per layout, never used to drop one. See the module docstring.
UNPUBLISHED_WARNING = (
    "NOT YET PUBLISHED BY ELDDIS: the configurator flags this layout "
    "`availableForWebsite: false` and publishes no price and no floorplan, and "
    "elddis.co.uk links no page for it. It is collected so the product can be created in "
    "FMLV ready to go, and it should be left INACTIVE until Elddis put it on their site"
)

_SOURCE_URL = f"{BASE_URL}/configurator-api/brand/{BRAND_KEY}/series"


def _centimetres(value: str | None) -> int | None:
    """A technical-data length, which the API publishes in **centimetres**."""
    if value is None:
        return None
    try:
        return round(float(str(value).replace(",", ".")) * 10)
    except ValueError:
        return None


def _kilograms(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return round(float(str(value).replace(",", ".")))
    except ValueError:
        return None


def _count(value: str | None) -> int | None:
    """A whole number, or `None` — the API writes an absent count as `''` or `'None'`."""
    if value is None or str(value).strip() in {"", "None"}:
        return None
    try:
        return int(float(str(value)))
    except ValueError:
        return None


def model_name(marketing_name: str, series_name: str) -> str | None:
    """`Riviera 580 FL` in series `Riviera` is the model `580 FL`.

    The same shape as `elddis.model_name` and deliberately a separate function: that one
    strips `Elddis <series>` as well, because the motorhome API prefixes the brand on some
    ranges and not others. The caravan payload has never done so, and a shared helper
    would make this module's behaviour depend on what the motorhome side discovers next.
    """
    name = " ".join((marketing_name or "").split())
    for prefix in (f"{MANUFACTURER_DISPLAY_NAME} {series_name}", series_name):
        if name.lower().startswith(prefix.lower()):
            stripped = name[len(prefix) :].strip()
            return stripped or None
    return name or None


class ElddisCaravanLayout:
    """One Riviera layout, as the configurator describes it.

    A plain class rather than a dataclass only because it carries a `beds` list that the
    findings read and nothing else does; everything here comes straight off the payload.
    """

    def __init__(
        self,
        *,
        manufacturer_range: str,
        model: str,
        berths: int | None = None,
        rrp_pounds: int | None = None,
        mtplm_kilograms: int | None = None,
        mro_kilograms: int | None = None,
        optional_equipment_allowance_kilograms: int | None = None,
        shipping_length_mm: int | None = None,
        overall_width_mm: int | None = None,
        height_mm: int | None = None,
        headroom_mm: int | None = None,
        beds: list[dict[str, Any]] | None = None,
        published: bool = False,
    ) -> None:
        self.manufacturer_range = manufacturer_range
        self.model = model
        self.berths = berths
        self.rrp_pounds = rrp_pounds
        self.mtplm_kilograms = mtplm_kilograms
        self.mro_kilograms = mro_kilograms
        self.optional_equipment_allowance_kilograms = optional_equipment_allowance_kilograms
        self.shipping_length_mm = shipping_length_mm
        self.overall_width_mm = overall_width_mm
        self.height_mm = height_mm
        self.headroom_mm = headroom_mm
        self.beds = beds or []
        self.published = published

    @property
    def label(self) -> str:
        return f"{self.manufacturer_range} {self.model}".strip()

    @property
    def payload_kilograms(self) -> int | None:
        """MTPLM less MRO. Elddis publish no payload row, so this is the only one there is."""
        if self.mtplm_kilograms is None or self.mro_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mro_kilograms


def _bed_values(entry: Any) -> dict[str, Any]:
    """One bed's `values` block, or `{}` — the API nests every bed one level down."""
    if not isinstance(entry, dict):
        return {}
    values = entry.get("values")
    return values if isinstance(values, dict) else {}


def _dimension(values: dict[str, Any], key: str) -> str | None:
    """A bed's width or length, which the API wraps as `{key, value, unit, …}`."""
    entry = values.get(key)
    if not isinstance(entry, dict):
        return None
    value = entry.get("value")
    return str(value) if value not in (None, "") else None


def parse_layouts(payload: str, series_name: str) -> list[ElddisCaravanLayout]:
    """Every layout in one caravan series' API response.

    A layout with no usable name is skipped rather than guessed at; everything else is
    carried through with whatever the response holds, and `_reconciles` decides whether
    the masses are believable.
    """
    try:
        entries = json.loads(payload)
    except ValueError:
        return []
    if not isinstance(entries, list):
        return []

    layouts: list[ElddisCaravanLayout] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        model = model_name(str(entry.get("marketingName") or ""), series_name)
        if not model:
            continue
        technical: dict[str, Any] = entry.get("technicalData") or {}

        def read(key: str, data: dict[str, Any] = technical) -> str | None:
            return ehg.technical_value(data, key)

        bed_block = technical.get("technicalDataBed")
        items = []
        if isinstance(bed_block, dict) and isinstance(bed_block.get("value"), dict):
            raw = bed_block["value"].get("items")
            items = [_bed_values(item) for item in raw] if isinstance(raw, list) else []

        price = entry.get("grossPrice")
        layouts.append(
            ElddisCaravanLayout(
                manufacturer_range=series_name,
                model=model,
                berths=_count(read("sleepingBerths")),
                rrp_pounds=round(price) if isinstance(price, (int, float)) else None,
                mtplm_kilograms=_kilograms(read("weightGrossVehicle")),
                mro_kilograms=_kilograms(read("weightRoadworthy")),
                optional_equipment_allowance_kilograms=_kilograms(
                    read("manufacturerSpecifiedWeightForOptionalEquipment")
                ),
                shipping_length_mm=_centimetres(read("lengthOverall")),
                overall_width_mm=_centimetres(read("widthOverallwithoutMirrors")),
                height_mm=_centimetres(read("heightOverall")),
                headroom_mm=_centimetres(read("headroomLivingArea")),
                beds=[values for values in items if values],
                published=bool(entry.get("availableForWebsite")),
            )
        )
    return layouts


def beds_from(layout: ElddisCaravanLayout) -> tuple[list[BedType], list[str]]:
    """The bed types a layout carries as standard, and the lines they were read from.

    **Optional beds are excluded**, which on the Riviera means the `single-to-double-bed`
    infill on the 590 SDW and the 640 LS and three of the 600 FDB's five bunks. The
    settled rule is that a configuration needing something fitted is not the standard one,
    the same rule that makes `berths` the lower end of a range.

    A `bedType` this module has not been taught is **skipped and named** rather than
    guessed at — the caller narrates it — because a wrong bed type is worse than a gap a
    person can see, and this is a finding somebody types in by hand either way.
    """
    found: list[BedType] = []
    quotes: list[str] = []
    for values in layout.beds:
        if str(values.get("isOptional") or "").strip().lower() == "yes":
            continue
        name = str(values.get("bedType") or "").strip()
        bed = BED_TYPES_BY_CONFIGURATOR_NAME.get(name)
        if bed is None:
            continue
        if bed not in found:
            found.append(bed)
        width = _dimension(values, "width")
        length = _dimension(values, "length")
        where = str(values.get("installedIn") or "").strip() or "unstated"
        size = f"{width}x{length}cm" if width and length else "no dimensions"
        quotes.append(f"{name} {where}, {size}")
    return found, quotes


def unknown_bed_types(layout: ElddisCaravanLayout) -> list[str]:
    """Standard beds whose `bedType` this module has not been taught, for narration."""
    return sorted(
        {
            str(values.get("bedType") or "").strip()
            for values in layout.beds
            if str(values.get("isOptional") or "").strip().lower() != "yes"
            and str(values.get("bedType") or "").strip()
            and str(values.get("bedType") or "").strip() not in BED_TYPES_BY_CONFIGURATOR_NAME
        }
    )


def sleeping_area_from(layout: ElddisCaravanLayout) -> CaravanSleepingArea | None:
    """Which end of the caravan the standard beds are at, or `None` if it cannot be read.

    `installedIn` is `front`, `rear` or `middle`. **`middle` is not an end**, and a layout
    whose only other bed is at the front reads `front` rather than `both` — a mid-lounge
    seating-group bed is not a second sleeping area in FMLV's sense, and the settled rule
    is that this group is only ever front, rear or both.

    Reported as a finding, never proposed, so a person checking it against the drawing is
    confirming a reading rather than correcting a value already written in.
    """
    ends = {
        str(values.get("installedIn") or "").strip().lower()
        for values in layout.beds
        if str(values.get("isOptional") or "").strip().lower() != "yes"
    }
    front, rear = _FRONT in ends, _REAR in ends
    if front and rear:
        return CaravanSleepingArea.BOTH
    if front:
        return CaravanSleepingArea.FRONT
    if rear:
        return CaravanSleepingArea.REAR
    return None


def _reconciles(layout: ElddisCaravanLayout) -> tuple[bool, str]:
    """Whether the two masses make sense together.

    Elddis publish no payload row for a caravan any more than for a motorhome, so there is
    no third figure to check the other two against; this tests the arithmetic those two
    imply. A mass in running order at or above the permissible maximum, or a payload
    outside what a caravan of this size can carry, means a figure came from the wrong
    field.
    """
    mtplm, mro = layout.mtplm_kilograms, layout.mro_kilograms
    if mtplm is None or mro is None:
        return False, (
            "the configurator states no permissible maximum or no mass in running order"
        )
    payload = mtplm - mro
    low, high = _PAYLOAD_RANGE
    if payload <= 0:
        return False, (
            f"a mass in running order of {mro}kg at or above the {mtplm}kg permissible "
            f"maximum, which would make the payload zero or negative"
        )
    if not low <= payload <= high:
        return False, (
            f"MTPLM {mtplm}kg less MRO {mro}kg is {payload}kg, outside the {low}-{high}kg "
            f"a caravan of this size can credibly carry"
        )
    return True, (
        f"MTPLM {mtplm}kg less mass in running order {mro}kg, giving a payload of "
        f"{payload}kg"
    )


def build_extracted(layout: ElddisCaravanLayout) -> ExtractedCaravan:
    """One layout as a `Caravan` plus the provenance a reviewer sees beside it.

    **`twin_axle` is set by nothing here.** The payload carries no axle count, and the
    field is a `bool` that defaults to `False`, so writing it would assert a single axle on
    a 2000kg caravan this module knows nothing about. Recording no provenance for it is
    what keeps it out of the diff entirely — `diff.compare` walks the provenance, not the
    product — which is the difference between "we did not look" and "we looked and the
    answer is no".

    `body_type` is `RIGID` on the settled rule rather than on anything Elddis publish: a
    caravan is rigid unless its *walls* fold or rise, and the micro rule needs the maker's
    own naming as well as a low MTPLM.
    """
    caravan = Caravan(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=layout.manufacturer_range,
        model=layout.model,
        berths=layout.berths,
        rrp_pounds=layout.rrp_pounds,
        mtplm_kilograms=layout.mtplm_kilograms,
        mro_kilograms=layout.mro_kilograms,
        personal_effects_payload_kilograms=layout.payload_kilograms,
        shipping_length_mm=layout.shipping_length_mm,
        overall_width_mm=layout.overall_width_mm,
        height_mm=layout.height_mm,
        headroom_mm=layout.headroom_mm,
        body_type=CaravanBodyType.RIGID,
    )

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=_SOURCE_URL, snippet=f"{layout.label} — {snippet}"
        )

    if layout.berths is not None:
        record("berths", f"the configurator's `sleepingBerths` is {layout.berths}")
    if layout.rrp_pounds is not None:
        record("rrp_pounds", f"the configurator's `grossPrice` is £{layout.rrp_pounds:,}")
    if layout.mtplm_kilograms is not None:
        record(
            "mtplm_kilograms",
            f"`weightGrossVehicle` {layout.mtplm_kilograms}kg, the technically "
            f"permissible maximum laden mass",
        )
    if layout.mro_kilograms is not None:
        record(
            "mro_kilograms",
            f"`weightRoadworthy` {layout.mro_kilograms}kg, the mass in running order",
        )
    if layout.payload_kilograms is not None:
        allowance = layout.optional_equipment_allowance_kilograms
        note = (
            f". Elddis also publish a {allowance}kg allowance for factory-fitted optional "
            f"equipment, which is a different quantity and is deliberately NOT recorded "
            f"as the payload"
            if allowance is not None
            else ""
        )
        record(
            "personal_effects_payload_kilograms",
            f"derived as {layout.mtplm_kilograms} − {layout.mro_kilograms} = "
            f"{layout.payload_kilograms}kg; Elddis publish no payload row{note}",
        )
    if layout.shipping_length_mm is not None:
        record(
            "shipping_length_mm",
            f"`lengthOverall` {layout.shipping_length_mm / 1000:.3f}m. This is the "
            f"SHIPPING length — body plus drawbar — confirmed against Eriba, the same API, "
            f"where it matches FMLV's own figure on 17 of 18 layouts",
        )
    if layout.overall_width_mm is not None:
        record(
            "overall_width_mm",
            f"`widthOverallwithoutMirrors` {layout.overall_width_mm}mm",
        )
    if layout.height_mm is not None:
        record("height_mm", f"`heightOverall` {layout.height_mm}mm")
    if layout.headroom_mm is not None:
        record("headroom_mm", f"`headroomLivingArea` {layout.headroom_mm}mm")
    record(
        "body_type",
        "rigid. Not read from Elddis, who publish no body type for a caravan: the settled "
        "rule is that a caravan is rigid unless its WALLS fold or rise, and the micro type "
        "needs the manufacturer's own naming as well as a low MTPLM",
    )

    # --- findings: stated with a source, for a person to type in -----------------------
    beds, quotes = beds_from(layout)
    if beds:
        caravan.bed_types = beds
        record(
            "bed_types",
            f"from the configurator's own bed table: {'; '.join(quotes)}. Optional beds "
            f"are excluded",
        )
    area = sleeping_area_from(layout)
    if area is not None:
        caravan.sleeping_area = area
        where = ", ".join(
            str(values.get("installedIn") or "?")
            for values in layout.beds
            if str(values.get("isOptional") or "").strip().lower() != "yes"
        )
        record(
            "sleeping_area",
            f"the standard beds are installed {where}. A `middle` bed is a mid-lounge "
            f"seating group and is not counted as an end",
        )

    return ExtractedCaravan(caravan=caravan, provenance=provenance)


def _series_url() -> str:
    return f"{BASE_URL}{ehg.BRAND_SERIES_PATH.format(brand_key=BRAND_KEY)}"


def _models_url(series_id: int) -> str:
    return f"{BASE_URL}{ehg.SERIES_MODELS_PATH.format(series_id=series_id)}?{ehg.UK_QUERY}"


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 — the API is plain JSON; see the module docstring
    snapshot_dir: Path,  # noqa: ARG001 — `http` already snapshots into it
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedCaravan]:
    """Every current Elddis touring caravan, from the brand's own configurator API."""
    index_url = _series_url()
    on_progress(f"fetching the series index {index_url} ...")
    index = http.fetch(index_url)
    if index.status_code != 200:
        msg = f"the series index {index_url} returned {index.status_code}"
        raise RuntimeError(msg)
    payload = index.file_path.read_text(encoding="utf-8", errors="replace")

    model_year = ehg.latest_model_year(payload)
    if model_year is None:
        msg = f"no model year could be read from {index_url}, so the range cannot be scoped"
        raise RuntimeError(msg)
    series = ehg.parse_series_index(payload, model_year=model_year)
    if not series:
        msg = f"the series index at {index_url} lists nothing for model year {model_year}"
        raise RuntimeError(msg)

    # **One catalogue, two product areas.** The mirror image of `elddis.collect`: that one
    # drops the caravans, this one keeps only them. A series with no `vehicleType` is NOT
    # swept here — the motorhome side treats an unstated type as a motorhome, so sweeping
    # it in both places would collect one vehicle into two product areas.
    caravans = [s for s in series if s.vehicle_type == ehg.CARAVAN_VEHICLE_TYPE]
    on_progress(
        f"model year {model_year}: {len(series)} series in the catalogue, "
        f"{len(caravans)} of them touring caravans — "
        f"{', '.join(s.name for s in caravans) or 'none'}"
    )
    if not caravans:
        msg = (
            f"the {model_year} series index at {index_url} lists no caravan series at all, "
            f"so there is nothing for this adapter to collect. Elddis have either "
            f"withdrawn the caravan range or moved it somewhere this does not look"
        )
        raise RuntimeError(msg)

    known = {label for _key, label in DEFAULT_RANGES}
    if tuple(ranges) == DEFAULT_RANGES:
        for name in sorted({s.name for s in caravans} - known):
            on_progress(
                f"NEW RANGE: {name!r} is in Elddis's {model_year} caravan catalogue and "
                f"not in this adapter's list — collected anyway. Add it to DEFAULT_RANGES "
                f"so `--range` can select it"
            )
        for name in sorted(known - {s.name for s in caravans}):
            on_progress(
                f"RANGE RETIRED: {name!r} is in this adapter's list and no longer in the "
                f"{model_year} catalogue, so nothing is collected for it"
            )
    else:
        wanted = {label for _key, label in ranges}
        caravans = [s for s in caravans if s.name in wanted]
        on_progress(
            f"limited to {len(caravans)} series: {', '.join(s.name for s in caravans)}"
        )

    results: list[ExtractedCaravan] = []
    for entry in caravans:
        url = _models_url(entry.id)
        response = http.fetch(url)
        if response.status_code != 200:
            on_progress(
                f"[{entry.name}] SKIPPED: its layouts returned {response.status_code}, so "
                f"none of them can be collected this run"
            )
            continue
        layouts = parse_layouts(
            response.file_path.read_text(encoding="utf-8", errors="replace"), entry.name
        )
        on_progress(f"[{entry.name}] {len(layouts)} layout(s)")

        for layout in layouts:
            ok, basis = _reconciles(layout)
            if not ok:
                on_progress(
                    f"[{layout.label}] SKIPPED: {basis}, so a mass has come from the "
                    f"wrong field and none of this layout's figures can be trusted"
                )
                continue
            if not layout.published:
                on_progress(f"[{layout.label}] {UNPUBLISHED_WARNING}")
            if layout.rrp_pounds is None:
                on_progress(
                    f"[{layout.label}] WARNING: no price published, left blank rather "
                    f"than guessed at"
                )
            for name in unknown_bed_types(layout):
                on_progress(
                    f"[{layout.label}] BED TYPE NOT RECOGNISED: the configurator calls a "
                    f"standard bed {name!r}, which is not a value this adapter has been "
                    f"taught. It is left out of the bed-types finding rather than guessed "
                    f"at — add it to BED_TYPES_BY_CONFIGURATOR_NAME"
                )
            on_progress(
                f"[{layout.label}] read: {layout.berths} berth, {basis}, "
                f"{layout.shipping_length_mm}mm shipping length"
            )
            results.append(build_extracted(layout))

    on_progress(
        "NO FLOORPLAN AND NO PHOTOGRAPH IS PUBLISHED by the configurator for any Elddis "
        "layout, so the positional habitation fields cannot be pointed at a drawing. The "
        "bed types and the sleeping area are read from the configurator's own bed table "
        "instead; the kitchen, washroom, lounge, heating, refrigeration and microwave are "
        "published nowhere this adapter can reach, because the Riviera has no model pages."
    )
    if len(results) != EXPECTED_LAYOUTS:
        on_progress(
            f"expected {EXPECTED_LAYOUTS} layouts and collected {len(results)} — check "
            f"whether the range has really changed"
        )
    on_progress(f"collected {len(results)} Elddis caravan(s)")
    return results
