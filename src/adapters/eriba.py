"""Eriba's campervans (eriba.com) — the motorhome-side adapter for a caravan brand.

Eriba builds both, so it has **two adapter modules and not one with a flag** (DESIGN.md
§3): `eriba_caravan` for the 18 touring caravans, and this for the two campervans. Same
manufacturer id 196, same `MANUFACTURER` string, different `VehicleClass`, so the registry
keys them apart. The Bailey pair is the same arrangement.

**One page: `/gb/en/models/camper-vans/eriba-car`.** It carries both layouts' full
specification — price, chassis, all three dimensions, both masses, seats, berths, the roof
type, the heating and the fridge — in the same `has-columns--1+` tables the other Erwin
Hymer Group sites use. No PDF, no login, no JavaScript.

**Three things about that page shape the parser:**

* **Each layout's specification is rendered twice**, byte for byte. Four blocks, two
  vehicles. `parse_layouts` collapses them, and their agreeing is a free self-check.
* **`Roof type` is published**, so the campervan body type is *derived* rather than
  assumed — `Fix roof` at 2,700 mm is a high top. A pop-top would classify itself.
* **`Berths 2 - 4 (○)`** — the `(○)` marks an optional upgrade, and the standard figure is
  the lower one, which is the rule in `docs/adapters/README.md` and what FMLV holds.

**The configurator lists a layout the UK does not sell.** `/configurator/eriba-car` returns
600, **601** and 602, but 601 appears nowhere on the UK model page and the requester
confirmed on 9 September 2026 that the GB configurator offers only two. So the **page** is
the roster and the API is used for one thing only: the floorplans, which the page does not
carry. A layout in the API and not on the page is narrated, never collected.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.enums import BodyType, Heating, Refrigeration
from ..product_model.model import Motorhome
from . import ehg_configurator as ehg
from . import habitation
from .base import (
    ExtractedMotorhome,
    Provenance,
    floorplan_provenance,
    fmlv_base_vehicle,
)

BASE_URL = "https://www.eriba.com"
MANUFACTURER = "Eriba"
MANUFACTURER_DISPLAY_NAME = "Eriba"

#: The campervan model page — the roster and the whole specification.
MODEL_PATH = "/gb/en/models/camper-vans/eriba-car"

#: The configurator, for the floorplans and nothing else. See the module docstring.
CONFIGURATOR_PATH = "/gb/en/configurator/eriba-car"

#: `--range` support. One range today; written as a roster so a second one is added here
#: rather than discovered by accident.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = ((MODEL_PATH, "ERIBA Car"),)

#: The range **as FMLV spells it**, which is in capitals and repeats the brand: the export
#: holds `Eriba` / `ERIBA CAR` / `600`, so a product reads back as "Eriba ERIBA CAR 600".
#: Emitted as FMLV has it rather than tidied, because the export decides these strings
#: (`docs/adapters/README.md`) and a rename would risk two rows for one vehicle. Worth
#: raising with the requester as a data-quality tidy-up, not worth an unasked-for rename.
FMLV_RANGE = "ERIBA CAR"

#: Above this a campervan is a high top — the settled threshold. Both layouts are 2,700 mm
#: with a `Fix roof`, so both clear it; kept as a rule so a pop-top classifies itself.
HIGH_TOP_ABOVE_MM = 2300

#: The `Roof type` values seen, and what each means for the body type. A **standard**
#: elevating roof changes what the vehicle is; an optional one does not, which is why this
#: reads the standard-fit row rather than the options list.
ROOF_FIXED = "fix roof"
ROOF_ELEVATING = ("pop-up", "pop up", "elevating", "rising")


# --------------------------------------------------------------------------- #
# The page
# --------------------------------------------------------------------------- #

#: The specification tables, the same class Dethleffs and Carado use — all three sites are
#: Erwin Hymer Group builds.
_TABLE = re.compile(r"<table[^>]*has-columns--1\+[^>]*>(?P<body>.*?)</table>", re.S)
_ROW = re.compile(r"<tr[^>]*>(?P<row>.*?)</tr>", re.S)
_CELL = re.compile(r"<td[^>]*>(?P<cell>.*?)</td>", re.S)

#: A layout's own heading, `ERIBA Car 600`. The model is the trailing number.
_LAYOUT_HEADING = re.compile(r"<h[1-6][^>]*>\s*(?P<title>ERIBA Car (?P<model>\d{3}))\s*</h[1-6]>")

#: What divides one layout's specification from the next. Every block opens with it.
BLOCK_MARKER = "Pricing information"

LABEL_PRICE = "Price"
LABEL_CHASSIS = "Standard chassis"
LABEL_DIMENSIONS = "Length / Width / Height (cm)"
LABEL_MRO = "Mass in running order (-/+ 5%) (kg)*"
LABEL_MTPLM = "Technically permissible maximum laden mass (kg)*"
LABEL_SEATS = "Permitted number of seats (including driver) *"
LABEL_BERTHS = "Berths"
LABEL_ROOF = "Roof type"
LABEL_HEATING = "Standard heating"
LABEL_REFRIGERATION = "Refrigerator volume incl. freezer (l)"

#: Sits between the two masses, exactly where payload would, and is not payload. Named so
#: the mistake is documented rather than merely avoided — Dethleffs, Etrusco, Bürstner,
#: Sunlight, Carado and Niesmann all publish the same row.
LABEL_NOT_PAYLOAD = "Manufacturer-specified mass for optional equipment (kg)*"

#: The marker on a figure that is an optional upgrade rather than the standard fit.
OPTIONAL_MARK = "○"


def _clean(markup: str) -> str:
    """Cell text with footnote superscripts and info buttons removed."""
    markup = re.sub(r"<sup[^>]*>.*?</sup>", " ", markup, flags=re.S)
    markup = re.sub(r"<button.*?</button>", " ", markup, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", markup)).strip()


def _first_int(value: str) -> int | None:
    """The first whole number, which is the standard figure of a `'2 - 4 (○)'` pair."""
    match = re.search(r"\d[\d,]*", value)
    return int(match.group(0).replace(",", "")) if match else None


def _band(value: str) -> tuple[int, int] | None:
    """`'2880 (2736 - 3024)*'` -> `(2736, 3024)`, the printed ±5% range."""
    match = re.search(r"\(\s*([\d,]+)\s*(?:to|-|–)\s*([\d,]+)\s*\)", value)
    if match is None:
        return None
    return int(match.group(1).replace(",", "")), int(match.group(2).replace(",", ""))


def _centimetres(value: str) -> list[int]:
    """`'599 / 207 / 270'` -> `[5990, 2070, 2700]`. Eriba quote whole centimetres."""
    return [int(n) * 10 for n in re.findall(r"\d+", value)]


@dataclass(frozen=True)
class EribaCampervan:
    """One layout, from its block of the model page."""

    model: str
    title: str
    specs: dict[str, str] = field(default_factory=dict)
    floorplan_url: str | None = None

    @property
    def rrp_pounds(self) -> int | None:
        return _first_int(self.specs.get(LABEL_PRICE, ""))

    @property
    def chassis(self) -> str | None:
        return self.specs.get(LABEL_CHASSIS) or None

    @property
    def base_vehicle_manufacturer(self) -> str | None:
        """`VW Crafter 35` -> `VW`, which is FMLV's spelling for the base vehicle."""
        chassis = self.chassis
        return fmlv_base_vehicle(chassis.split()[0]) if chassis else None

    @property
    def _dimensions(self) -> list[int]:
        return _centimetres(self.specs.get(LABEL_DIMENSIONS, ""))

    @property
    def mh_length_mm(self) -> int | None:
        found = self._dimensions
        return found[0] if len(found) > 0 else None

    @property
    def mh_width_mm(self) -> int | None:
        found = self._dimensions
        return found[1] if len(found) > 1 else None

    @property
    def mh_height_mm(self) -> int | None:
        found = self._dimensions
        return found[2] if len(found) > 2 else None

    @property
    def mro_kilograms(self) -> int | None:
        return _first_int(self.specs.get(LABEL_MRO, ""))

    @property
    def mro_band(self) -> tuple[int, int] | None:
        return _band(self.specs.get(LABEL_MRO, ""))

    @property
    def mtplm_kilograms(self) -> int | None:
        return _first_int(self.specs.get(LABEL_MTPLM, ""))

    @property
    def mh_payload_kilograms(self) -> int | None:
        """`MTPLM - MRO`. Eriba publish no payload for these, and the optional-equipment
        mass beside it is not one — see `LABEL_NOT_PAYLOAD`."""
        if self.mtplm_kilograms is None or self.mro_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mro_kilograms

    @property
    def mh_passenger_seats_inc_driver(self) -> int | None:
        return _first_int(self.specs.get(LABEL_SEATS, ""))

    @property
    def berths_published(self) -> str | None:
        return self.specs.get(LABEL_BERTHS) or None

    @property
    def berths(self) -> int | None:
        """The standard figure of `'2 - 4 (○)'`, the upper one being a paid upgrade."""
        return _first_int(self.berths_published or "")

    @property
    def roof_published(self) -> str | None:
        return self.specs.get(LABEL_ROOF) or None

    @property
    def has_standard_elevating_roof(self) -> bool:
        """Whether the **standard** roof rises. An optional pop-top does not change what
        the vehicle is, per `docs/adapters/README.md`; both current layouts say `Fix roof`."""
        roof = (self.roof_published or "").lower()
        return any(marker in roof for marker in ROOF_ELEVATING)

    @property
    def body_type(self) -> BodyType | None:
        """Derived from the published roof type and the published height, never assumed.

        No height read means no guess — a blank beats the nearest known type, which is the
        rule in `docs/adapters/README.md`.
        """
        if self.mh_height_mm is None:
            return None
        high_top = self.mh_height_mm > HIGH_TOP_ABOVE_MM
        if self.has_standard_elevating_roof:
            return (
                BodyType.CAMPERVAN_HIGH_TOP_ELEVATING_ROOF
                if high_top
                else BodyType.CAMPERVAN_ELEVATING_ROOF
            )
        return BodyType.CAMPERVAN_HIGH_TOP if high_top else BodyType.CAMPERVAN

    @property
    def spec_lines(self) -> list[str]:
        """The rows that state a fitted feature, for `habitation.features_from`.

        An allow-list, for the reason `carado.HABITATION_SPEC_LABELS` exists: a bed
        *dimension* row's label enumerates the beds a vehicle might have rather than
        stating what is fitted, and feeding it in reads a bed type off a measurement.
        """
        return [
            f"{label} {self.specs[label]}"
            for label in (LABEL_HEATING, LABEL_REFRIGERATION)
            if self.specs.get(label)
        ]


def parse_layout_titles(page_html: str) -> list[tuple[str, str]]:
    """`(title, model)` for each layout the page heads, in order and deduplicated."""
    found: list[tuple[str, str]] = []
    for match in _LAYOUT_HEADING.finditer(page_html):
        entry = (match.group("title"), match.group("model"))
        if entry not in found:
            found.append(entry)
    return found


def parse_spec_blocks(page_html: str) -> list[dict[str, str]]:
    """Each layout's specification, **with the duplicate renderings collapsed**.

    The page prints every block twice, byte for byte — four blocks for two vehicles. That
    is a rendering artefact rather than two variants, and the two agreeing is a free check
    on the parse, so an exact repeat is dropped and a *differing* one is kept and left for
    the caller's cardinality check to notice.
    """
    starts = [m.start() for m in re.finditer(re.escape(BLOCK_MARKER), page_html)]
    bounds = [*starts, len(page_html)]
    blocks: list[dict[str, str]] = []
    for index, start in enumerate(starts):
        rows: dict[str, str] = {}
        for table in _TABLE.finditer(page_html):
            if not (start <= table.start() < bounds[index + 1]):
                continue
            for row in _ROW.findall(table.group("body")):
                cells = [_clean(cell) for cell in _CELL.findall(row)]
                if len(cells) == 2 and cells[0]:
                    rows.setdefault(cells[0], cells[1])
        if rows and rows not in blocks:
            blocks.append(rows)
    return blocks


def parse_layouts(page_html: str) -> list[EribaCampervan]:
    """Both campervans from the model page, or `[]` if the join cannot be trusted.

    **The join is positional and asserted**: the Nth heading owns the Nth specification
    block. If the counts disagree the page is refused rather than guessed at, because a
    guess attributes one vehicle's price and weights to another.
    """
    titles = parse_layout_titles(page_html)
    blocks = parse_spec_blocks(page_html)
    if not titles or len(titles) != len(blocks):
        return []
    return [
        EribaCampervan(model=model, title=title, specs=specs)
        for (title, model), specs in zip(titles, blocks, strict=True)
    ]


def _reconciles(layout: EribaCampervan) -> bool:
    """Whether the printed ±5% band really is ±5% of the stated running order.

    Weak by construction — the band is a function of the mass, so it catches a misread
    digit and not a row read from the wrong place. It is what this page offers, and the
    duplicate blocks agreeing is the stronger check `parse_spec_blocks` already applies.
    """
    if layout.mro_kilograms is None or layout.mro_band is None:
        return True
    low, high = layout.mro_band
    return (
        abs(low - round(layout.mro_kilograms * 0.95)) <= 2
        and abs(high - round(layout.mro_kilograms * 1.05)) <= 2
    )


# --------------------------------------------------------------------------- #
# Building a product
# --------------------------------------------------------------------------- #

_FEATURE_NOTES: dict[str, str] = {
    "heating": "the standard heating",
    "refrigeration": "the specification's refrigerator row",
}

#: Why a microwave is reported absent. The page itemises the kitchen down to the fridge's
#: freezer compartment and the socket count, so a microwave missing from it is the document
#: saying there is none — the itemised-table exception in `docs/adapters/README.md`.
MICROWAVE_ABSENCE_NOTE = (
    "no mention of a microwave in the specification. The page itemises the kitchen down to "
    "the fridge's freezer volume and the socket count, so the vocabulary is there and unused"
)


def build_extracted(layout: EribaCampervan) -> ExtractedMotorhome:
    """One product from one layout block."""
    features = habitation.features_from(layout.spec_lines)
    absent = habitation.microwave_from(layout.spec_lines) is None

    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=FMLV_RANGE,
        model=layout.model,
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
        # Habitation, reported as findings rather than proposed — see
        # `product_model.findings`.
        heating=features["heating"].value if "heating" in features else None,
        refrigeration=(
            features["refrigeration"].value if "refrigeration" in features else None
        ),
        microwave=False if absent else None,
    )

    source = BASE_URL + MODEL_PATH
    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=source, snippet=f"{layout.title} — {snippet}"
        )

    identity = (
        f"the site publishes this as '{layout.title}'; FMLV holds range '{FMLV_RANGE}' and "
        f"model '{layout.model}'. The two halves belong together — accept both or neither"
    )
    record("manufacturer_range", identity)
    record("model", identity)

    if layout.rrp_pounds is not None:
        record("rrp_pounds", f"Price: {layout.specs.get(LABEL_PRICE)}")
    if layout.base_vehicle_manufacturer is not None:
        record("base_vehicle_manufacturer", f"Standard chassis: {layout.chassis}")
    if layout.body_type is not None:
        roof = "rises as standard" if layout.has_standard_elevating_roof else "is fixed"
        record(
            "body_type",
            f"Roof type: '{layout.roof_published}', so the roof {roof}, and {layout.mh_height_mm}mm "
            f"is {'above' if (layout.mh_height_mm or 0) > HIGH_TOP_ABOVE_MM else 'not above'} "
            f"the {HIGH_TOP_ABOVE_MM}mm high-top threshold",
        )
    if layout.berths is not None:
        record(
            "berths",
            f"Berths '{layout.berths_published}', standard figure {layout.berths} — the "
            f"higher one is marked as an option",
        )
    if layout.mh_passenger_seats_inc_driver is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"Permitted number of seats (including driver): "
            f"{layout.specs.get(LABEL_SEATS)}",
        )
    for field_name, axis in (
        ("mh_length_mm", "length"),
        ("mh_width_mm", "width"),
        ("mh_height_mm", "height"),
    ):
        if getattr(motorhome, field_name) is not None:
            record(
                field_name,
                f"Length / Width / Height (cm): '{layout.specs.get(LABEL_DIMENSIONS)}' "
                f"— the {axis}",
            )
    if layout.mtplm_kilograms is not None:
        record(
            "mtplm_kilograms",
            f"Technically permissible maximum laden mass: {layout.mtplm_kilograms}kg",
        )
    if layout.mro_kilograms is not None:
        band = (
            f" (permissible range {layout.mro_band[0]} to {layout.mro_band[1]}kg, ±5%)"
            if layout.mro_band
            else ""
        )
        record("mro_kilograms", f"Mass in running order: {layout.mro_kilograms}kg{band}")
    if layout.mh_payload_kilograms is not None:
        record(
            "mh_payload_kilograms",
            f"derived: {layout.mtplm_kilograms}kg maximum laden - {layout.mro_kilograms}kg "
            f"running order = {layout.mh_payload_kilograms}kg. Eriba publish no payload for "
            f"these, and their 'manufacturer-specified mass for optional equipment' is not one",
        )

    for name, feature in features.items():
        note = feature.note or _FEATURE_NOTES.get(name, "read from the specification")
        record(name, f"{note}: {feature.snippet}")
    if absent:
        record("microwave", MICROWAVE_ABSENCE_NOTE)

    if layout.floorplan_url:
        provenance.update(floorplan_provenance(motorhome, layout.floorplan_url, layout.title))
    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #


def _floorplans(http: Fetcher, on_progress: Callable[[str], None]) -> dict[str, str]:
    """`{marketing name: drawing URL}` from the configurator, which the page lacks.

    Never raises and never adds a product: a configurator that cannot be read costs the
    drawings and nothing else. A layout it lists that the page does not is narrated —
    `ERIBA Car 601` is one, and it is not sold in the UK.
    """
    page = http.fetch(BASE_URL + CONFIGURATOR_PATH)
    if page.status_code != 200:
        on_progress(f"no floorplans: {CONFIGURATOR_PATH} returned {page.status_code}")
        return {}
    series_id = ehg.parse_series_id(page.file_path.read_text(encoding="utf-8", errors="replace"))
    if series_id is None:
        on_progress(f"no floorplans: no series id on {CONFIGURATOR_PATH}")
        return {}
    models = http.fetch(BASE_URL + ehg.SERIES_MODELS_PATH.format(series_id=series_id))
    if models.status_code != 200:
        on_progress(f"no floorplans: the configurator API returned {models.status_code}")
        return {}
    found = {}
    for model in ehg.parse_models(
        models.file_path.read_text(encoding="utf-8", errors="replace")
    ):
        if model.floorplan_url:
            url = model.floorplan_url
            found[model.marketing_name] = url if url.startswith("http") else BASE_URL + url
    return found


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 — the page is server-rendered
    snapshot_dir: Path,  # noqa: ARG001 — `http` already snapshots into it
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """The model page for the roster and the specification, the configurator for drawings.

    An unreadable model page raises — it is the only source of the products themselves, and
    collecting nothing silently would look like a discontinued range.
    """
    plans = _floorplans(http, on_progress)
    if plans:
        on_progress(f"the configurator offers {len(plans)} drawing(s)")

    results: list[ExtractedMotorhome] = []
    for path, label in ranges:
        page = http.fetch(BASE_URL + path)
        if page.status_code != 200:
            msg = f"{BASE_URL + path} returned {page.status_code}"
            raise RuntimeError(msg)
        html_text = page.file_path.read_text(encoding="utf-8", errors="replace")
        layouts = parse_layouts(html_text)
        if not layouts:
            titles = len(parse_layout_titles(html_text))
            blocks = len(parse_spec_blocks(html_text))
            msg = (
                f"{path}: {titles} heading(s) but {blocks} specification block(s), so no "
                f"layout can be trusted to its own figures"
            )
            raise RuntimeError(msg)
        on_progress(f"[{label}] {len(layouts)} layout(s)")

        for layout in layouts:
            if not _reconciles(layout):
                on_progress(
                    f"[{layout.title}] SKIPPED: the printed band {layout.mro_band} is not "
                    f"±5% of the {layout.mro_kilograms}kg running order"
                )
                continue
            with_plan = EribaCampervan(
                model=layout.model,
                title=layout.title,
                specs=layout.specs,
                floorplan_url=plans.get(layout.title),
            )
            if with_plan.floorplan_url is None:
                on_progress(f"[{layout.title}] no floorplan in the configurator")
            for name, value in (
                ("price", layout.rrp_pounds),
                ("running order mass", layout.mro_kilograms),
                ("berths", layout.berths),
                ("body type", layout.body_type),
            ):
                if value is None:
                    on_progress(f"[{layout.title}] WARNING: no {name} published, left blank")
            results.append(build_extracted(with_plan))

        # A stated roster beats a heuristic, and here the page is the roster: the
        # configurator carries `ERIBA Car 601`, which the UK does not sell.
        collected = {layout.title for layout in layouts}
        for name in sorted(set(plans) - collected):
            on_progress(
                f"{name} is in the configurator but not on the UK model page, so it is "
                f"not collected"
            )

    on_progress(f"{len(results)} product(s) collected")
    return results
