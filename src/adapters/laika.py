"""Laika motorhomes, from the schema.org JSON-LD on its UK models index.

Twenty-second manufacturer. See `docs/adapters/laika.md` for the survey; this docstring
covers what the code does and why it is shaped this way.

**One fetch, and the data is structured.** `laika.it/en-gb/motorhomes/` embeds
`application/ld+json` describing every layout in the UK range — price, both masses, all
three dimensions, seats, berths and base chassis — in plain server-rendered HTML. No
JavaScript, no PDF, no login, and no columnar table to slice. That makes this the least
fragile source in the project: the fields are *named* rather than positioned, so the
whole class of column-alignment failures that the Morelo, Sunlight and Bürstner adapters
guard against cannot arise.

`/en-gb/` is a real market edition. Prices are `"priceCurrency": "GBP"`, so none of the
exchange-rate trouble that makes Morelo's data the worst in the project applies.

**The Technical Data panel is behind a terms-and-conditions click, and is not needed.** It
publishes interior width, headroom and insulation, and for every field FMLV records it
repeats the JSON-LD exactly — 659 / 225 / 299 / 2971 / 3500 on `L 2009`, checked value by
value on 9 September 2026. The gate never has to be passed.

**Two shapes, and missing the second drops a fifth of the range.** A multi-layout range is
a `ProductGroup` with `hasVariant`; a **one-layout range is a bare `["Product", "Vehicle"]`
with no `hasVariant` at all**. Both Kreos ranges are the second kind, so a parser written
for the group shape silently loses 2 of 10 — and on those pages `name` is the *range*
("Kreos"), not the layout. The index page has the layout names right, which is the second
reason to read the roster from there rather than from the four range pages.

**The self-check is the page stating its figures twice.** Each range page renders a
floorplan slider whose slides carry `data-price`, `data-length`, `data-width`,
`data-height`, `data-weight` and `data-sleeping` — an independent rendering of the same
record. They agree with the JSON-LD on 8 of the 8 multi-layout products. `_reconciles`
uses the arithmetic available in the index alone: mass in running order must be below the
technically permissible maximum, and the gap must be a plausible payload.

**Body type comes from the site's own words, not from the URL.** The index's meta
description reads *"Low-profile and A-class, one range hand-built since 1964"*, so the
`/coachbuilt/` path is low profile and `/a-class/` is A class. Neither is inferred from a
height or a model name.

**The range drops the `I`.** Laika's `vehicleConfiguration` distinguishes `Ecovip Titanio`
from `Ecovip Titanio I`, the `I` marking the integrated (A-class) build. That is a body
type, and FMLV already records it as one — so both file under `Ecovip Titanio`, exactly as
Adria's 60Y editions file under `Matrix` rather than `Matrix 60Y`.

**A drawing's filename says nothing about its content.** `L 5009 MB`'s plan is served as
`carado-imagebank-data_VE_Camper-Van_CV540_…png` — an Erwin Hymer Group image-bank name
Laika's WordPress kept from upload. The image itself is the correct Laika low-profile
drawing. So `parse_floorplans` trusts the slider's structure, which ties each drawing to
its own `data-name`, and never the filename.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..fetch.http import Fetcher
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from .base import (
    ExtractedMotorhome,
    Provenance,
    floorplan_provenance,
    fmlv_base_vehicle,
)

__all__ = [
    "BASE_URL",
    "DEFAULT_RANGES",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "LaikaLayout",
    "collect",
    "parse_floorplans",
    "parse_layouts",
]

BASE_URL = "https://www.laika.it"
MANUFACTURER = "Laika"
MANUFACTURER_DISPLAY_NAME = "Laika"

#: The UK models index — one fetch for the whole roster. Sterling, and server-rendered.
MODELS_INDEX_PATH = "/en-gb/motorhomes/"

#: `(low-profile page, A-class page, FMLV range label)`. Used only by `--range` and to
#: fetch the drawings: the roster itself comes from the index in one request.
#:
#: **Two entries, not four.** Laika splits each range across two body-style pages, but
#: `--range` keys on the label and FMLV files both under one range — so the pair travels
#: together, with the label last as `cli.resolve_ranges` requires. Same three-element shape
#: as `rimor.DEFAULT_RANGES`, and for the same reason: one FMLV range, several source URLs.
DEFAULT_RANGES: tuple[tuple[str, str, str], ...] = (
    (
        "/en-gb/motorhomes/coachbuilt/ecovip-titanio/",
        "/en-gb/motorhomes/a-class/ecovip-titanio/",
        "Ecovip Titanio",
    ),
    (
        "/en-gb/motorhomes/coachbuilt/kreos/",
        "/en-gb/motorhomes/a-class/kreos/",
        "Kreos",
    ),
)

#: Laika's own description of what it builds, from the index page's meta description:
#: *"Low-profile and A-class, one range hand-built since 1964."* The URL path segment is
#: what identifies which, and this is the mapping — read from the manufacturer's words
#: rather than guessed from a height or a model name.
BODY_TYPES: dict[str, BodyType] = {
    "coachbuilt": BodyType.COACH_BUILT_LOW_PROFILE,
    "a-class": BodyType.A_CLASS,
}

#: Every `application/ld+json` block on a page.
_JSON_LD = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.S
)

#: The trailing `I` Laika appends for the integrated build — `Ecovip Titanio I`. Dropped,
#: because it names a body type FMLV already records in its own column.
_INTEGRATED_SUFFIX = re.compile(r"\s+I$")

#: A floorplan slide. `data-name` is the layout, and the drawing follows within the slide.
_SLIDE = re.compile(r'data-name="([^"]+)"')

#: A drawing in the floorplan slider.
_SLIDE_IMAGE = re.compile(r'https://www\.laika\.it/wp-content/uploads/[^"\s]+?\.(?:png|jpe?g|webp)')

#: The narrowest payload this project will believe. Laika's own range is 329-755kg, so a
#: figure below this means the two masses have been read from different layouts.
MIN_PLAUSIBLE_PAYLOAD_KG = 100


@dataclass(frozen=True)
class LaikaLayout:
    """One layout, as the index page's structured data describes it."""

    range_label: str
    model: str
    body_type: BodyType | None = None
    rrp_pounds: int | None = None
    mro_kilograms: int | None = None
    mtplm_kilograms: int | None = None
    mh_length_mm: int | None = None
    mh_width_mm: int | None = None
    mh_height_mm: int | None = None
    mh_passenger_seats_inc_driver: int | None = None
    berths: int | None = None
    berths_published: str | None = None
    base_vehicle_manufacturer: str | None = None
    base_chassis_published: str | None = None
    source_url: str | None = None

    @property
    def label(self) -> str:
        return f"{self.range_label} {self.model}"

    @property
    def mh_payload_kilograms(self) -> int | None:
        """Payload from the two masses. Laika publishes none, so this is derived."""
        if self.mtplm_kilograms is None or self.mro_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mro_kilograms


def _quantity(entry: Any) -> int | None:
    """The number out of a schema.org `QuantitativeValue`, or `None`."""
    if not isinstance(entry, dict):
        return None
    value = entry.get("value")
    try:
        return int(round(float(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _centimetres_to_mm(entry: Any) -> int | None:
    """Laika publishes every dimension in whole centimetres, `unitCode: CMT`."""
    centimetres = _quantity(entry)
    return centimetres * 10 if centimetres is not None else None


def _properties(variant: dict[str, Any]) -> dict[str, str]:
    """`additionalProperty` as `{propertyID: value}`."""
    found: dict[str, str] = {}
    for entry in variant.get("additionalProperty") or []:
        if isinstance(entry, dict) and entry.get("propertyID"):
            found[str(entry["propertyID"])] = str(entry.get("value", ""))
    return found


def _lower_berth(published: str | None) -> int | None:
    """The standard figure out of Laika's `2 - 4`.

    The lower one, per `docs/adapters/README.md`: the extra berths need optional equipment,
    and recording the ceiling would say the vehicle sleeps more people than it does as
    bought.
    """
    if not published:
        return None
    numbers = re.findall(r"\d+", published)
    return int(numbers[0]) if numbers else None


def fmlv_range(vehicle_configuration: str | None) -> str | None:
    """The FMLV range for a `vehicleConfiguration`, with the integrated `I` dropped."""
    if not vehicle_configuration:
        return None
    return _INTEGRATED_SUFFIX.sub("", " ".join(vehicle_configuration.split())) or None


def body_type_for(url: str | None) -> BodyType | None:
    """The body type a layout's own URL names, or `None` for a path neither covers."""
    if not url:
        return None
    for segment, body_type in BODY_TYPES.items():
        if f"/{segment}/" in url:
            return body_type
    return None


def _model_name(variant: dict[str, Any], range_label: str | None) -> str | None:
    """The layout's own name, with a range prefix removed if the page carries one.

    The index publishes the A-class Kreos as `Kreos H 5109 MB` and the coachbuilt one as a
    plain `L 5009 MB`. Both are the same kind of thing, so the prefix comes off.
    """
    name = " ".join(str(variant.get("name") or variant.get("model") or "").split())
    if not name:
        return None
    if range_label and name.lower().startswith(f"{range_label.lower()} "):
        name = name[len(range_label) + 1 :].strip()
    return name or None


def _variants(block: Any) -> list[dict[str, Any]]:
    """Every vehicle in one JSON-LD block, whichever of the two shapes it uses.

    A multi-layout range is a `ProductGroup` carrying `hasVariant`. A **one-layout range is
    a bare `["Product", "Vehicle"]`** with no `hasVariant`, and reading only the first shape
    silently drops both Kreos ranges — see the module docstring.
    """
    found: list[dict[str, Any]] = []
    for item in block if isinstance(block, list) else [block]:
        if not isinstance(item, dict):
            continue
        variants = item.get("hasVariant")
        if isinstance(variants, list) and variants:
            found.extend(v for v in variants if isinstance(v, dict))
            continue
        types = item.get("@type")
        types = types if isinstance(types, list) else [types]
        if "Vehicle" in types:
            found.append(item)
    return found


def parse_layouts(index_html: str) -> list[LaikaLayout]:
    """Every layout the models index publishes, in document order, deduplicated by URL.

    The index carries one JSON-LD block per range, so this is the whole roster in one
    fetch. A vehicle without a name or a URL is skipped: neither the model nor the body
    type can be established without them, and a layout that cannot be identified must not
    become a product.
    """
    layouts: list[LaikaLayout] = []
    seen: set[str] = set()
    for raw in _JSON_LD.findall(index_html):
        try:
            block = json.loads(raw)
        except ValueError:
            continue
        for variant in _variants(block):
            url = str(variant.get("url") or variant.get("@id") or "")
            if not url or url in seen:
                continue
            range_label = fmlv_range(variant.get("vehicleConfiguration"))
            model = _model_name(variant, range_label)
            if not range_label or not model:
                continue
            seen.add(url)

            properties = _properties(variant)
            offers = variant.get("offers")
            price = None
            if isinstance(offers, dict) and str(offers.get("priceCurrency")) == "GBP":
                try:
                    price = int(round(float(offers["price"])))
                except (KeyError, TypeError, ValueError):
                    price = None
            chassis = properties.get("baseChassis")
            berths_published = properties.get("sleepingBerthsMinMax")

            layouts.append(
                LaikaLayout(
                    range_label=range_label,
                    model=model,
                    body_type=body_type_for(url),
                    rrp_pounds=price,
                    mro_kilograms=_quantity(variant.get("weight")),
                    mtplm_kilograms=_quantity(variant.get("weightTotal")),
                    mh_length_mm=_centimetres_to_mm(variant.get("depth")),
                    mh_width_mm=_centimetres_to_mm(variant.get("width")),
                    mh_height_mm=_centimetres_to_mm(variant.get("height")),
                    mh_passenger_seats_inc_driver=_quantity(
                        {"value": variant.get("vehicleSeatingCapacity")}
                    ),
                    berths=_lower_berth(berths_published),
                    berths_published=berths_published,
                    # Through the shared helper, never spelled locally — the make decides
                    # whether a run confirms `base_vehicle_manufacturer` or proposes a
                    # rename, so that call belongs in one place.
                    base_vehicle_manufacturer=fmlv_base_vehicle(
                        chassis.split()[0] if chassis else None
                    ),
                    base_chassis_published=chassis,
                    source_url=url.split("#", 1)[0] or None,
                )
            )
    return layouts


def parse_floorplans(range_html: str) -> dict[str, str]:
    """`{layout name: drawing URL}` from one range page's floorplan slider.

    **The structure is the guarantee, not the filename.** Each slide carries its layout in
    `data-name` and its own drawing inside it, so the search is bounded to the span between
    one `data-name` and the next — a slide with no image of its own yields nothing rather
    than borrowing its neighbour's.

    A filename check was tried here first and was **wrong**: Laika's WordPress keeps the
    name a file was uploaded under, and the Erwin Hymer Group brands share an image bank,
    so `L 5009 MB`'s perfectly correct low-profile drawing is served as
    `carado-imagebank-data_VE_Camper-Van_CV540_…png`. Requiring the filename to name the
    layout threw that plan away. The lesson is the general one: an asset's name is not
    evidence about its content, and on a shared image bank it is not even evidence about
    its brand.
    """
    section = range_html[range_html.find("section__floorplan-slider") :]
    if not section:
        return {}
    slides = list(_SLIDE.finditer(section))
    plans: dict[str, str] = {}
    for index, match in enumerate(slides):
        name = " ".join(match.group(1).split())
        if not name or name in plans:
            continue
        # Bounded to this slide, so a missing drawing cannot pick up the next layout's.
        end = slides[index + 1].start() if index + 1 < len(slides) else len(section)
        image = _SLIDE_IMAGE.search(section, match.end(), end)
        if image is not None:
            plans[name] = image.group(0)
    return plans


def _reconciles(layout: LaikaLayout) -> tuple[bool, str]:
    """`(keep, why not)` — the alignment check, from the two masses the index publishes.

    Laika publishes no payload, so there is no published figure to compare a derived one
    against. What there is: the mass in running order must sit below the technically
    permissible maximum, and the gap must be a payload a real motorhome could have. A
    slipped record pairing one layout's running order with another's maximum shows up here,
    which is the failure this exists to catch.
    """
    if layout.mro_kilograms is None or layout.mtplm_kilograms is None:
        return True, ""  # nothing to check against; the missing figure is its own signal
    payload = layout.mtplm_kilograms - layout.mro_kilograms
    if payload < MIN_PLAUSIBLE_PAYLOAD_KG:
        return False, (
            f"mass in running order {layout.mro_kilograms}kg against a permissible maximum "
            f"of {layout.mtplm_kilograms}kg leaves {payload}kg, below the "
            f"{MIN_PLAUSIBLE_PAYLOAD_KG}kg floor, so the two may be from different layouts"
        )
    return True, ""


def _build_extracted_motorhome(
    layout: LaikaLayout, floorplan_url: str | None = None
) -> ExtractedMotorhome:
    """One layout as a `Motorhome`, plus the provenance a reviewer sees beside each field."""
    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=layout.range_label,
        model=layout.model,
        base_vehicle_manufacturer=layout.base_vehicle_manufacturer,
        body_type=layout.body_type,
        berths=layout.berths,
        mh_passenger_seats_inc_driver=layout.mh_passenger_seats_inc_driver,
        rrp_pounds=layout.rrp_pounds,
        mro_kilograms=layout.mro_kilograms,
        mtplm_kilograms=layout.mtplm_kilograms,
        mh_payload_kilograms=layout.mh_payload_kilograms,
        mh_length_mm=layout.mh_length_mm,
        mh_width_mm=layout.mh_width_mm,
        mh_height_mm=layout.mh_height_mm,
    )

    source = layout.source_url or f"{BASE_URL}{MODELS_INDEX_PATH}"
    provenance: dict[str, Provenance] = {}

    def record(field: str, snippet: str) -> None:
        provenance[field] = Provenance(source_url=source, snippet=f"{layout.label} — {snippet}")

    if layout.rrp_pounds is not None:
        record("rrp_pounds", f"structured data, offers.price: £{layout.rrp_pounds:,} (GBP)")
    if layout.base_vehicle_manufacturer is not None:
        record("base_vehicle_manufacturer", f"Standard chassis: {layout.base_chassis_published}")
    if layout.body_type is not None:
        # Laika's own description of what it builds, not an inference from the height.
        record(
            "body_type",
            f"the site files this under /{ 'a-class' if layout.body_type is BodyType.A_CLASS else 'coachbuilt' }/, "
            f"and Laika describe their range as \"Low-profile and A-class\"",
        )
    if layout.berths is not None:
        # The published string, not the parsed integer: a reviewer seeing `2` needs to know
        # the source said `2 - 4`.
        record("berths", f"Berths: {layout.berths_published} — the standard figure")
    if layout.mh_passenger_seats_inc_driver is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"structured data, vehicleSeatingCapacity: {layout.mh_passenger_seats_inc_driver}",
        )
    for field, value, name in (
        ("mh_length_mm", layout.mh_length_mm, "depth"),
        ("mh_width_mm", layout.mh_width_mm, "width"),
        ("mh_height_mm", layout.mh_height_mm, "height"),
    ):
        if value is not None:
            record(field, f"structured data, {name}: {value // 10} cm")
    if layout.mro_kilograms is not None:
        record("mro_kilograms", f"structured data, weight: {layout.mro_kilograms} kg")
    if layout.mtplm_kilograms is not None:
        record("mtplm_kilograms", f"structured data, weightTotal: {layout.mtplm_kilograms} kg")
    if layout.mh_payload_kilograms is not None:
        record(
            "mh_payload_kilograms",
            f"derived: {layout.mtplm_kilograms}kg permissible maximum - "
            f"{layout.mro_kilograms}kg running order = {layout.mh_payload_kilograms}kg "
            f"(Laika publish no payload)",
        )

    if floorplan_url:
        provenance.update(floorplan_provenance(motorhome, floorplan_url, layout.label))

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


def collect(
    http: Fetcher,
    browser: object = None,  # noqa: ARG001 — server-rendered; `http` snapshots every fetch
    snapshot_dir: Path | None = None,  # noqa: ARG001 — `http` owns the snapshot directory
    *,
    ranges: tuple[tuple[str, ...], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Collect every UK Laika layout from the models index, with drawings from the ranges.

    Raises only if the index itself cannot be read — without it there is no roster at all,
    and collecting nothing silently would look like a manufacturer that had withdrawn its
    whole range. Anything narrower is narrated and skipped.
    """
    index_url = f"{BASE_URL}{MODELS_INDEX_PATH}"
    on_progress(f"fetching the models index {index_url} ...")
    index = http.fetch(index_url)
    if index.status_code != 200:
        msg = f"models index {index_url} returned {index.status_code}"
        raise RuntimeError(msg)

    layouts = parse_layouts(index.file_path.read_text(encoding="utf-8", errors="replace"))
    if not layouts:
        msg = f"no structured vehicle data on {index_url}"
        raise RuntimeError(msg)
    on_progress(f"the index publishes {len(layouts)} layout(s)")

    wanted = {entry[-1] for entry in ranges}

    # One fetch per body-style page, for the drawings only — every figure came from the
    # index. A page that cannot be read costs its own drawings and nothing else.
    plans: dict[str, str] = {}
    for entry in ranges:
        label = entry[-1]
        for path in entry[:-1]:
            page = http.fetch(f"{BASE_URL}{path}")
            if page.status_code != 200:
                on_progress(f"[{label}] {path} returned {page.status_code}, so no floorplans")
                continue
            found = parse_floorplans(
                page.file_path.read_text(encoding="utf-8", errors="replace")
            )
            plans.update(found)
            on_progress(f"[{label}] {path} — {len(found)} floorplan(s)")

    results: list[ExtractedMotorhome] = []
    for layout in layouts:
        if layout.range_label not in wanted:
            continue
        keep, reason = _reconciles(layout)
        if not keep:
            on_progress(f"{layout.label} — SKIPPED: {reason}")
            continue
        plan = plans.get(layout.model)
        if plan is None:
            on_progress(
                f"{layout.label} — no floorplan naming this layout, so the positional "
                f"fields carry no pointer"
            )
        results.append(_build_extracted_motorhome(layout, plan))

    on_progress(f"{len(results)} product(s) collected")
    return results
