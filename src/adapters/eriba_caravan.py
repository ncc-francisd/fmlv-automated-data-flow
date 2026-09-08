"""Eriba touring caravans, from the UK price list, cross-checked against the website.

Twenty-first manufacturer and the third caravan brand. See `docs/adapters/eriba.md` for
the survey; this docstring covers only what the code does and why it is shaped this way.

**The price list is the source, because the website only holds half the range.** Eriba's
Touring range page publishes **no technical data at all** — no floorplan slider, no spec
tables, no model ids — and the international English page at `/de/en` has the same gap, so
it is a site-wide template difference rather than a UK omission. That is nine of the
eighteen layouts, including the range Eriba is famous for. The UK price list PDF is the
only document that covers them.

**Which is a documented divergence from `docs/adapters/README.md`'s "the website overrules
the PDF".** That rule rests on a reason — a PDF is usually the last thing updated, so it is
usually the stale one — and the reason does not hold here. Three pieces of evidence:

* The price list is the **leading** document, not the lagging one: page 1 reads
  `ERIBA CARAVANS 2027 / Price list for UK and IRL - Valid from 1 July 2026`.
* On the nine layouts both sources cover, they agree on **165 of 165** comparable values.
  The only differences are the website appending a `(○)` standard-equipment marker.
* The website cannot be the source of record for a roster it is missing half of.

So the website is kept and fetched **every run as a verification rather than a value
source**: `cross_check` compares the two and narrates any field that disagrees, without
overriding. That deliberately leaves a divergence for a human instead of silently resolving
it in either direction — if the site ever moves ahead of the price list, the run says so
loudly and the next person decides which is right. Overriding would have quietly pulled the
whole range back a model year in the one scenario the rule is meant to prevent.

**The columns cannot be read from coordinates.** The spec pages set four or five layouts
side by side, and on page 5 pypdf places about 70 of 167 runs and reports **97 at (0, 0)**,
including the entire header row as one run. This is the Morelo problem, so
`extract_positioned_text` is not usable at all. The line-based text *is* complete, so
`parse_spec_page` locates a known label, reads to the start of the **next** known label, and
splits that span with a typed regex per field — requiring **exactly one value per model
named in the page header**, and dropping the page otherwise. Four traps make the obvious
whitespace split impossible:

* **Values contain spaces** — `185 R14 C 102 L`, `Gas heating, 3.5 kW`,
  `188 x 73 - 53 / 188 x 73`.
* **Labels wrap across lines** — `Manufacturer-specified mass for optional equipment` then
  `(kg)*`, with the values trailing the second line. Reading to the next label handles it.
* **Blank cells exist**, but only in the four bed-dimension rows and the storage-compartment
  clearance: page 16 prints `Bed dimension: Sleeping roof` with three values against four
  models. **Which** model is missing cannot be recovered from the line, so those rows are
  never parsed — this is Rimor's "present and unattributable" in miniature. Every field FMLV
  needs carries one value per model on all four spec pages.
* **Page 15 does not extract.** The Touring Silver Edition table yields
  `BASE PRICE (incl. VAT) £ £ £  3.0 3.0` and `PRICE xxxxx`. It carries no
  `PRICES AND TECHNICAL DATA` heading so it is never selected, which is the intended
  outcome: it is an editions-and-options table, not a layout roster.

**The self-check is the printed ±5% band**, the same device as Sunlight and Etrusco. The
mass in running order is published with its legally permissible range —
`820 (779 - 861)*` — and 820 × 0.95 = 779, × 1.05 = 861, so the band is a *function* of the
mass and a slipped column pairs one layout's mass with another's band. All eighteen pass
within 1 kg of the printed rounding; `_TOLERANCE_SLACK_KG` allows 3, as `etrusco.py` does.
`reconciles` adds a second, free alignment check: the unladen weight must be below the mass
in running order, which it is by a range-constant 41 kg (Touring) or 61 kg (the others).

**Payload goes whole into the personal-effects column**, exactly as `swift_caravan.py` does,
with Eriba's published optional-equipment allowance quoted in the provenance rather than
emitted. The tempting reading — allowance into `optional_equipment_payload_kilograms`, the
remainder into personal effects — is wrong three times over: FMLV's field guide marks
personal effects `REQUIRED`/`in_scope` and optional `NOT REQUIRED - rarely published`; the
base-vehicle rule records the caravan *as standard*, with no options fitted, so the whole
difference is usable payload; and Eriba's own footnote describes the figure as a **ceiling
on what may be ordered**, which is the same label the motorhome half of `README.md` names as
a cap and not payload. FMLV has these two columns the wrong way round on all 18 Eriba rows,
so the optional column is recorded with **no value** to raise a confirm-or-clear.

**Body type is `RIGID` on all eighteen, and that corrects FMLV on fifteen.** Eriba publishes
a `Roof type` row reading `Pop-up roof` on six Touring layouts and `Sleeping roof` on six
more, and the baseline had followed that wording. Per the NCC rule of 7 September 2026 a
caravan is rigid unless its *walls* fold or rise, so the type does not follow the roof. The
run must say this is deliberate: fifteen identical changes to one field is otherwise exactly
the shape a reviewer is told to distrust.

**Not a micro, either.** Five layouts are at or under the 1250 kg threshold — Touring 310 at
1000, Touring 420 and 430 at 1100, Feeling 425 and Novaline 465 at 1200 — but `micro` needs
the manufacturer's own naming as well as the weight, and the words "micro" and "compact"
appear nowhere in the price list.

**Prices are sterling, and the document libels itself.** Its footnote reads *"All prices are
recommended retail prices in Euro including legal applicable VAT ex works"*, which is
un-localised boilerplate from the German master: the title says `Price list for UK and IRL`,
every figure carries a pound sign, the Silver Edition page quotes a `2.840 GBP` advantage,
and `EUR` appears zero times. So `price_list_currency_problem` asserts on the **pound sign
and the title**, never on the footnote — the inverse of the Weinsberg trap, where a
reassuring "UK" label hid a euro document. The basis, from the website's own tooltip, is
GBP including VAT and On The Road charges.

**Floorplans exist for only nine of eighteen.** Feeling and Novaline slides carry a
per-layout SVG; all nine predicted Touring URLs return a genuine 404 and no Touring drawing
appears anywhere on the site. So the positional fields get a `reviewer_reference` pointer on
the nine that have one and nothing on the nine that do not, which is narrated rather than
left to look like an oversight.
"""

from __future__ import annotations

import base64
import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from html import unescape
from pathlib import Path

from ..fetch.http import Fetcher
from ..fetch.pdf import extract_text
from ..product_model.caravan import Caravan
from ..product_model.enums import BedType, CaravanBodyType, CaravanSleepingArea
from ..vehicle_class import VehicleClass
from . import habitation
from .base import ExtractedCaravan, Provenance

__all__ = [
    "DEFAULT_RANGES",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "VEHICLE_CLASS",
    "BED_TYPES_BY_CONFIGURATOR_NAME",
    "ConfiguratorLayout",
    "EribaCaravan",
    "build_extracted",
    "collect",
    "cross_check",
    "find_price_list_url",
    "parse_configurator_models",
    "parse_configurator_series_id",
    "parse_range_page",
    "parse_spec_page",
    "price_list_currency_problem",
]

BASE_URL = "https://www.eriba.com"
MANUFACTURER = "Eriba"
MANUFACTURER_DISPLAY_NAME = "Eriba"

#: What makes this the caravan adapter. Eriba build one campervan, the Eriba Car, which is
#: out of scope and would be a second module declaring `VehicleClass.MOTORHOME`.
VEHICLE_CLASS = VehicleClass.CARAVAN

#: `(range page slug, FMLV range name)`. The label is last, as `cli.resolve_ranges`
#: requires, and it **is** the FMLV `manufacturer_range` — confirmed against the export, so
#: the default `cli.baseline_scope` match on that column is correct and no
#: `baseline_in_scope` hook is needed. The slug is the website range page, used only for the
#: cross-check; Touring's page carries no data, which `collect` narrates rather than treating
#: as a failure.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (
    ("eriba-touring", "Touring"),
    ("eriba-feeling", "Feeling"),
    ("eriba-novaline", "Novaline"),
)

BROCHURES_PATH = "/gb/en/service/brochures"
RANGE_PAGE_PATH = "/gb/en/models/caravans/{slug}"

#: Eriba's own range words, and the only ones a layout name may start with. Used to find the
#: model header line on a spec page, so a new range has to be added here deliberately rather
#: than being picked up from arbitrary text.
RANGE_WORDS: tuple[str, ...] = ("Touring", "Feeling", "Novaline")

#: The heading that marks a columnar specification spread. Page 15's Silver Edition table
#: lacks it and is therefore never selected, which is intended — see the module docstring.
SPEC_PAGE_MARKER = "PRICES AND TECHNICAL DATA"

#: How far the printed ±5% band may sit from the exact arithmetic before the layout is
#: dropped. The document rounds to whole kilograms, so a kilogram or two of drift is the
#: rounding and not a misalignment; `etrusco.py` allows the same 3 kg for the same reason.
_TOLERANCE_SLACK_KG = 3

_MASS_TOLERANCE = 0.05


def _canonical(label: str) -> str:
    """One spec-row label reduced to a key both sources agree on.

    The PDF and the website print the same rows with slightly different unit suffixes —
    `Manufacturer-specified mass for optional equipment` against the same label with
    `(kg)*` appended — so comparing raw labels would silently fail to line up the very
    fields the cross-check exists to compare. Bracketed units are dropped, punctuation is
    flattened, and what is left is unique across every row in the document.
    """
    text = re.sub(r"\(.*?\)", " ", label.lower())
    text = re.sub(r"[^a-z0-9/+\- ]", " ", text)
    return " ".join(text.split())


#: Every label on a specification spread, in the order they are printed. Presence in this
#: list is what makes a label a **boundary**: `parse_spec_page` reads each row's values from
#: the end of its own label to the start of the next one, so a label omitted here would let
#: the row before it swallow both the label and its values. Several are here purely as
#: boundaries and are never emitted — `Tire size`, `Interior width (cm)`,
#: `Maximum nose weight (kg)`, the four bed dimensions — because FMLV has no column for them
#: or, for the bed rows, because they may be blank and are then unattributable.
SPEC_LABELS: tuple[str, ...] = (
    "Price £",
    "Axle",
    "Tire size",
    "Length / Width / Height (cm)",
    "Body length (exterior) (cm)",
    "Interior length (cm)",
    "Interior width (cm)",
    "Roof type",
    "Headroom in living area (cm)",
    "A-measurement awning (cm)",
    "Mass in running order (-/+ 5%) (kg)*",
    "Manufacturer-specified mass for optional equipment",
    "Unladen weight, approx. kg",
    "Technically permissible maximum laden mass (kg)*",
    "Maximum nose weight (kg)",
    "Insulation floor / side walls / roof (mm)",
    "Clearance of storage compartment / garage doors or flap,",
    "Bed dimension: Front bed, L x W (cm)",
    "Bed dimension: Rear bed, L x W (cm)",
    "Bed dimension: Central / middle bed, L x W (cm)",
    "Bed dimension: Sleeping roof, L x W (cm)",
    "Berths",
    "Burner hob",
    "Refrigerator volume incl. freezer (l)",
    "Heating type",
    "Gas bottle storage (Filling weight)",
    "Fresh water supply (l)",
    "Warm water tank (l)",
    "Sockets: 230 V",
    "Sockets: USB",
    # Terminators. The legend that follows the last data row, so `Sockets: USB` stops at the
    # end of its own values rather than running into the footnote paragraph.
    "Standard equipment",
    "The specified mass in running order",
)

#: Canonical key back to the label Eriba actually print. The provenance a reviewer reads has
#: to carry **the manufacturer's own words**, not this module's internal key, so a snippet
#: says `Refrigerator volume incl. freezer (l): 83 (10)` rather than the flattened form used
#: to line the two sources up. Built from `SPEC_LABELS` so it can never drift from them.
_PRINTED_LABEL: dict[str, str] = {_canonical(label): label for label in SPEC_LABELS}

#: An integer that is a whole cell, not a fragment of a larger number. The lookarounds keep
#: `1,200` from yielding `200` and `27,390.-` from yielding `390`.
_INT = r"(?<![\d,.])(\d{2,5})(?![\d,.])"

#: How to split each row FMLV needs, keyed by canonical label. Every pattern is anchored on
#: the **shape of the value** rather than on position, which is what makes one-value-per-
#: model a meaningful check instead of an assumption.
_VALUE_PATTERNS: dict[str, str] = {
    "price": r"([\d,]+)\.-",
    "axle": r"(Mono|Tandem)",
    "length / width / height": r"(\d+) / (\d+) / (\d+)",
    "body length": _INT,
    "interior length": _INT,
    "roof type": r"(Pop-up roof|Sleeping roof|Fix roof)",
    "headroom in living area": _INT,
    "a-measurement awning": _INT,
    "mass in running order": r"(\d+) \((\d+) - (\d+)\)",
    "manufacturer-specified mass for optional equipment": r"(?<![\d,.])(\d{1,4})(?![\d,.])",
    "unladen weight approx kg": _INT,
    "technically permissible maximum laden mass": _INT,
    "berths": r"(\d(?: - \d)?)",
    "refrigerator volume incl freezer": r"(\d+ \(\d+\))",
}

#: `Heating type` is deliberately **not** parsed, and this is the second row in the document
#: to earn that treatment for the bed dimensions' reason. Page 6 prints
#: `Gas heating, 3.5 kW` **twice against five models**, so three of the five Tourings state
#: no heating and which three cannot be recovered from the line. The cardinality check found
#: it on the first live run, which is what that check is for.
#:
#: Nothing is lost either way: `Gas heating, 3.5 kW` names the fuel and the output but not
#: whether the system is warm-air or water-based, and that distinction is the only thing
#: FMLV's `heating` column records. So the field would have been left unset even where the
#: value did parse.
_HEATING_NOT_COLLECTED = (
    "heating type not collected: Eriba print 'Gas heating, 3.5 kW', which does not say "
    "whether it is blown air or wet central, and the row is blank on some Touring layouts "
    "in a way that cannot be attributed to a column. FMLV's own value stands"
)

#: The positional fields no specification table can settle — they need the layout drawing.
#: Recorded as `reviewer_reference` pointers at the floorplan, one per field, so the link
#: sits beside the field being decided. `bed_types` is deliberately absent: Eriba publishes
#: bed *dimensions*, but in rows that may be blank and are therefore never parsed.
FLOORPLAN_FIELDS: tuple[str, ...] = (
    "sleeping_area",
    "kitchen_location",
    "lounge_location",
    "bathroom_layout",
)


#: The configurator page for one range. It renders nothing server-side — the layouts, the
#: drawings and the technical data all arrive from an API — which is why the range pages
#: were read as the only source and Touring concluded to have no floorplan anywhere. It
#: does, and so does every other layout; the requester found the per-layout URL by hand on
#: 9 September 2026: *"that pointer does take you to specific model layouts, and then you
#: can click technical specification and get more."*
CONFIGURATOR_PATH = "/gb/en/configurator/{slug}"

#: The base64 JSON the configurator page hands its own JavaScript. It carries the
#: `seriesId` the API is keyed on, so the id is **read rather than hardcoded** and a range
#: Eriba renumbers cannot silently point at another range's layouts.
_CONFIG_BLOB = re.compile(r"data-config='([A-Za-z0-9+/=]+)'")

#: The endpoint the configurator bundle names `fetchModels`. Public, unauthenticated and
#: plain JSON — no browser needed. The query pins the UK locale, so the marketing names
#: come back in English and match what the price list calls each layout.
CONFIGURATOR_MODELS_PATH = "/configurator-api/series/{series_id}/models"
CONFIGURATOR_MODELS_QUERY = "locale=en_GB&country=GB&currencyCode=GBP"

#: Where a reviewer lands for one layout, which is the whole reason this was worth wiring.
CONFIGURATOR_LAYOUT_URL = BASE_URL + "/gb/en/configurator/{slug}?selectedModelId={model_id}"

#: The configurator's `bedType` vocabulary, and what FMLV records for each.
#:
#: The field earns its keep by naming `seating-group-bed` separately, that being the only
#: made-up kind: everything else here is a bed that stands there whether or not anyone
#: makes it up. So the rest are fixed, and which *fixed* column each takes follows the
#: requester's hierarchy of 8 September 2026 — the most specific type that fits, with
#: `fixed_bed` as the fallback for a permanent bed that is none of the others.
#:
#: `french-bed` and `v-bed` are shapes FMLV has no column for, so they take that fallback
#: rather than contributing nothing: the shape is not recordable but the *fixedness* is,
#: and this field is what establishes it. That is different from reading "French bed" out
#: of marketing prose, which settles nothing on its own — Rimor's Horus 12 has "a rear
#: double French bed that also lifts to create more storage space".
BED_TYPES_BY_CONFIGURATOR_NAME: dict[str, BedType] = {
    "seating-group-bed": BedType.MAKE_UP,
    "twin-bed": BedType.FIXED_SEPARATE,
    "bunk-bed": BedType.FIXED_BUNKS,
    "double-bed": BedType.FIXED,
    "french-bed": BedType.FIXED,
    "v-bed": BedType.FIXED,
}

#: Where the configurator says a bed is installed, and the end that implies. `middle` is
#: absent on purpose: the column offers front, rear or both, and a bed amidships is not a
#: third answer — Novaline 515 has one alongside a front double and rear bunks, and the
#: right answer there is `both`.
_SLEEPING_ENDS: dict[str, str] = {"front": "front", "rear": "rear"}


@dataclass(frozen=True)
class ConfiguratorLayout:
    """One layout as the configurator API describes it.

    A second, independent source for what the price list already gives — berths and the
    two masses — and the *only* source for three things the price list cannot express: a
    per-layout drawing, the type of each bed, and which end each bed is at.
    """

    label: str
    model_id: int
    url: str
    floorplan_url: str | None = None
    bed_types: tuple[BedType, ...] = ()
    bed_evidence: str = ""
    sleeping_area: CaravanSleepingArea | None = None
    berths: int | None = None
    mtplm_kilograms: int | None = None
    mro_kilograms: int | None = None


def parse_configurator_series_id(page_html: str) -> int | None:
    """The `seriesId` the configurator page hands its JavaScript, or `None`."""
    blob = _CONFIG_BLOB.search(page_html)
    if blob is None:
        return None
    try:
        config = json.loads(base64.b64decode(blob.group(1)))
    except (ValueError, TypeError):
        return None
    series_id = config.get("seriesId")
    return series_id if isinstance(series_id, int) else None


def _technical_value(technical_data: dict, key: str) -> str | None:
    """One `technicalData` entry's value. Each is `{key, value, unit, unitLong}` or null."""
    entry = technical_data.get(key)
    if not isinstance(entry, dict):
        return None
    value = entry.get("value")
    return str(value) if value not in (None, "") else None


def _beds_from(
    technical_data: dict,
) -> tuple[tuple[BedType, ...], str, CaravanSleepingArea | None]:
    """`(bed types, the evidence, sleeping area)` from one layout's bed records.

    **Optional beds are excluded**, per the standing rule that a paid extra is not what
    the buyer has: Touring 620, 630 and 642 each list a pop-top double as an option, and
    counting it would both add a bed type and move the sleeping area.

    Order follows the document, deduplicated, so the value and its evidence read the same
    way round.
    """
    entry = technical_data.get("technicalDataBed")
    items = ((entry or {}).get("value") or {}).get("items") or []

    found: list[BedType] = []
    quoted: list[str] = []
    ends: set[str] = set()
    for item in items:
        values = item.get("values") or {}
        if values.get("isOptional") == "yes":
            continue
        name = values.get("bedType")
        where = values.get("installedIn")
        bed_type = BED_TYPES_BY_CONFIGURATOR_NAME.get(name)
        if bed_type is None:
            continue
        quoted.append(f"{name} ({where})" if where else str(name))
        if bed_type not in found:
            found.append(bed_type)
        if where in _SLEEPING_ENDS:
            ends.add(_SLEEPING_ENDS[where])

    if ends == {"front", "rear"}:
        sleeping = CaravanSleepingArea.BOTH
    elif ends == {"front"}:
        sleeping = CaravanSleepingArea.FRONT
    elif ends == {"rear"}:
        sleeping = CaravanSleepingArea.REAR
    else:
        sleeping = None
    return tuple(found), ", ".join(quoted), sleeping


def parse_configurator_models(payload: str, slug: str) -> list[ConfiguratorLayout]:
    """Every layout in one series' API response.

    The label comes from the API's own `marketingName` ("Touring 310"), which is what the
    price list calls the layout too, so the join needs no translation table.
    """
    try:
        models = json.loads(payload)
    except ValueError:
        return []
    if not isinstance(models, list):
        return []

    layouts: list[ConfiguratorLayout] = []
    for model in models:
        if not isinstance(model, dict):
            continue
        name = " ".join(str(model.get("marketingName") or "").split())
        model_id = model.get("id")
        if not name or not isinstance(model_id, int):
            continue
        technical_data = model.get("technicalData") or {}
        bed_types, bed_evidence, sleeping = _beds_from(technical_data)
        plan = model.get("layoutImageVertical") or model.get("layoutImage") or {}
        source = plan.get("overlayImageSource") if isinstance(plan, dict) else None
        layouts.append(
            ConfiguratorLayout(
                label=name,
                model_id=model_id,
                url=CONFIGURATOR_LAYOUT_URL.format(slug=slug, model_id=model_id),
                floorplan_url=f"{BASE_URL}{source}" if source else None,
                bed_types=bed_types,
                bed_evidence=bed_evidence,
                sleeping_area=sleeping,
                berths=_int_or_none(_technical_value(technical_data, "sleepingBerths")),
                mtplm_kilograms=_int_or_none(
                    _technical_value(technical_data, "weightGrossVehicle")
                ),
                mro_kilograms=_int_or_none(
                    _technical_value(technical_data, "weightRoadworthy")
                ),
            )
        )
    return layouts


def _clean(html: str) -> str:
    """Tag-stripped, whitespace-collapsed text from a fragment of markup."""
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", html)).split())


def _int_or_none(text: str | None) -> int | None:
    if text is None:
        return None
    digits = text.replace(",", "").strip()
    return int(digits) if digits.isdigit() else None


def _cm_to_mm(text: str | None) -> int | None:
    centimetres = _int_or_none(text)
    return None if centimetres is None else centimetres * 10


# --------------------------------------------------------------------------- #
# Finding the document
# --------------------------------------------------------------------------- #

#: The caravan price list, and not its two neighbours on the same page: the Eriba Car
#: campervan list at `preislisten/campervans/` and the Original Parts catalogue under
#: `eriba-op/`. Anchored on the `preislisten/caravans/` directory, which is what actually
#: distinguishes them — the filename carries no year, so there is no archive to match by
#: accident and nothing to mislead. Rediscovered every run rather than hardcoded.
_PRICE_LIST_HREF = re.compile(
    r'href="(/[^"]*?preislisten/caravans/[^"]*?\.pdf)"', re.IGNORECASE
)


def find_price_list_url(brochures_html: str) -> str | None:
    """The absolute URL of the UK caravan price list, or `None` if the card has gone.

    Returning `None` rather than raising keeps a site reshuffle a narratable skip, per the
    error policy every adapter here follows.
    """
    match = _PRICE_LIST_HREF.search(brochures_html)
    if match is None:
        return None
    return f"{BASE_URL}{match.group(1)}"


def price_list_currency_problem(text: str) -> str | None:
    """Why this document's prices cannot be trusted as sterling, or `None` if they can.

    Reads the **price column and the title**, never the footnote, which claims euros ex
    works in a document titled for the UK whose every figure carries a pound sign — see the
    module docstring. The check that matters is the inverse of Weinsberg's: refuse a
    document actually quoting euros, and ignore boilerplate that merely says so.
    """
    if "£" not in text:
        return "no pound sign anywhere in the document"
    if re.search(r"\bEUR\b|€", text):
        return "the document quotes EUR"
    if not re.search(r"price list for uk", text, re.IGNORECASE):
        return "the document does not describe itself as a UK price list"
    return None


# --------------------------------------------------------------------------- #
# Parsing a specification spread
# --------------------------------------------------------------------------- #


def _model_header(page_text: str) -> list[tuple[str, str]] | None:
    """The `(range, model)` pairs a spec page's header names, in column order.

    Found by looking for a line that is **entirely** layout names, which is what separates
    the header from prose mentioning one: page 10's `Package Comfort package Touring 310
    Comfort package` contains a layout name and is not a header, and page 15's
    `LAYOUT 430 530 542 630 642` names no range and is not one either.
    """
    token = rf"(?:{'|'.join(RANGE_WORDS)}) \d{{3}}"
    whole_line = re.compile(rf"^\s*(?:{token})(?:\s+{token})+\s*$")
    for line in page_text.splitlines():
        if whole_line.match(line):
            return [
                (name.split()[0], name.split()[1])
                for name in re.findall(token, line)
            ]
    return None


def _row_spans(page_text: str) -> dict[str, str]:
    """Each spec label mapped to the text between it and the next label.

    Reading to the *next* label rather than taking a fixed number of values is what makes a
    wrapped label harmless and stops a short row swallowing the following label — the trap
    `docs/adapters/README.md` warns about, where the swallowed label pads the count back to
    what was expected and defeats the very check meant to catch it.
    """
    flat = re.sub(r"[ \t]+", " ", page_text)
    found = sorted(
        (flat.find(label), label) for label in SPEC_LABELS if flat.find(label) >= 0
    )
    spans: dict[str, str] = {}
    for index, (start, label) in enumerate(found):
        end = found[index + 1][0] if index + 1 < len(found) else len(flat)
        value = flat[start + len(label) : end].replace("\n", " ").strip()
        spans[_canonical(label)] = value
    return spans


def parse_spec_page(page_text: str) -> tuple[list[tuple[str, str, dict[str, str]]], list[str]]:
    """One `PRICES AND TECHNICAL DATA` spread as `(range, model, {label: value})` rows.

    Returns the layouts and a list of problems to narrate. A row whose value count does not
    match the number of models in the header is **dropped from every layout on the page**
    rather than being guessed at, and reported — per the standing rule, a mismatch means the
    alignment is unknown, and a partly-aligned row is worse than a missing one.
    """
    problems: list[str] = []
    header = _model_header(page_text)
    if not header:
        return [], ["no layout header found on the page"]

    spans = _row_spans(page_text)
    columns: list[dict[str, str]] = [{} for _ in header]
    for key, pattern in _VALUE_PATTERNS.items():
        if key not in spans:
            problems.append(f"row {key!r} is missing from the page")
            continue
        matches = re.findall(pattern, spans[key])
        if len(matches) != len(header):
            problems.append(
                f"row {key!r} gave {len(matches)} value(s) for {len(header)} model(s) "
                f"— dropping the row rather than guessing the alignment"
            )
            continue
        for column, value in zip(columns, matches, strict=True):
            column[key] = value if isinstance(value, str) else " / ".join(value)

    layouts = [
        (range_name, model, column)
        for (range_name, model), column in zip(header, columns, strict=True)
    ]
    return layouts, problems


# --------------------------------------------------------------------------- #
# The website, for the cross-check and the floorplans
# --------------------------------------------------------------------------- #

_SLIDE = re.compile(r'<div class="b-floorplaninteractive__slide[ "]')
_SLIDE_MODEL = re.compile(
    r'<h2 class="b-floorplaninteractive__model">(.*?)</h2>', re.DOTALL
)
_TABLE_ROW = re.compile(r'<tr class="m-table__rows[^"]*">(.*?)</tr>', re.DOTALL)
_TABLE_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL)
_FLOORPLAN_SRC = re.compile(r'(?:src|data-src)="([^"]*grundriss[^"]*\.svg)"', re.IGNORECASE)

#: The standard-equipment ring the website appends to some values and the PDF does not —
#: `Sleeping roof (○)` against `Sleeping roof`. Stripped before comparing, otherwise the
#: cross-check reports six disagreements that are not disagreements.
_EQUIPMENT_MARKER = re.compile(r"\s*\((?:○|●|–|-)\)\s*$")


def parse_range_page(html: str) -> list[tuple[str, dict[str, str], str | None]]:
    """Each layout a range page publishes, as `(layout name, {label: value}, floorplan)`.

    Every layout's block is rendered **twice** in the served HTML, once per button wrapper,
    so the rows are read into a dict and the duplicate collapses. Returns `[]` for the
    Touring page, which carries no slides at all — see the module docstring.
    """
    marks = [match.start() for match in _SLIDE.finditer(html)]
    if not marks:
        return []
    bounds = [*marks, len(html)]

    layouts: list[tuple[str, dict[str, str], str | None]] = []
    for index in range(len(marks)):
        slide = html[bounds[index] : bounds[index + 1]]
        name = _SLIDE_MODEL.search(slide)
        if name is None:
            continue
        rows: dict[str, str] = {}
        for row in _TABLE_ROW.finditer(slide):
            cells = _TABLE_CELL.findall(row.group(1))
            if len(cells) == 2:
                label, value = _clean(cells[0]), _clean(cells[1])
                if label:
                    rows[_canonical(label)] = _EQUIPMENT_MARKER.sub("", value)
        plan = _FLOORPLAN_SRC.search(slide)
        floorplan = plan.group(1) if plan else None
        if floorplan and floorplan.startswith("/"):
            floorplan = f"{BASE_URL}{floorplan}"
        layouts.append((_clean(name.group(1)), rows, floorplan))
    return layouts


# --------------------------------------------------------------------------- #
# One caravan
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class EribaCaravan:
    """One layout, read from either source into the same shape.

    Both the price list's columns and the website's two-cell tables reduce to a
    `{canonical label: value}` mapping, so `from_rows` builds this from either and
    `cross_check` can compare two of them field by field. That is the whole reason the two
    parsers return the same structure.
    """

    manufacturer_range: str
    model: str
    rrp_pounds: int | None = None
    berths: int | None = None
    berths_published: str | None = None
    mtplm_kilograms: int | None = None
    mro_kilograms: int | None = None
    mass_band: tuple[int, int] | None = None
    unladen_kilograms: int | None = None
    optional_equipment_allowance_kg: int | None = None
    shipping_length_mm: int | None = None
    exterior_body_length_mm: int | None = None
    internal_length_mm: int | None = None
    awning_length_mm: int | None = None
    overall_width_mm: int | None = None
    height_mm: int | None = None
    headroom_mm: int | None = None
    twin_axle: bool = False
    axle_evidence: str | None = None
    roof_type: str | None = None
    spec_lines: tuple[str, ...] = field(default_factory=tuple)

    @property
    def label(self) -> str:
        return f"{self.manufacturer_range} {self.model}"

    @property
    def derived_payload_kilograms(self) -> int | None:
        """`MTPLM - MRO`, which is the whole payload — see the module docstring."""
        if self.mtplm_kilograms is None or self.mro_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mro_kilograms

    @property
    def minimum_payload_kilograms(self) -> int | None:
        """What is left for baggage once the optional-equipment ceiling is reserved.

        Not emitted — quoted in the payload provenance as Eriba's own evidence that the
        derived figure leaves a legal minimum, and negative would mean the two masses and
        the allowance cannot all be right.
        """
        payload = self.derived_payload_kilograms
        if payload is None or self.optional_equipment_allowance_kg is None:
            return None
        return payload - self.optional_equipment_allowance_kg

    @property
    def band_reconciles(self) -> bool | None:
        """Whether the printed ±5% band is the arithmetic of the printed mass.

        `None` when either is missing, so "could not check" stays distinct from "checked
        and failed" — only the latter drops a layout.
        """
        if self.mro_kilograms is None or self.mass_band is None:
            return None
        low, high = self.mass_band
        expected_low = round(self.mro_kilograms * (1 - _MASS_TOLERANCE))
        expected_high = round(self.mro_kilograms * (1 + _MASS_TOLERANCE))
        return (
            abs(expected_low - low) <= _TOLERANCE_SLACK_KG
            and abs(expected_high - high) <= _TOLERANCE_SLACK_KG
        )

    def reconciles(self) -> tuple[bool, str]:
        """`(keep it, why)` — the alignment defence this adapter drops products on.

        Two checks, both cheap and both about the *columns* rather than the values. The band
        is the real one. The unladen weight is a second free one: it is the mass before gas
        and water, so it must sit below the mass in running order, and a swapped pair of
        columns is likely to break that even where both masses are individually plausible.
        """
        if self.band_reconciles is None:
            return True, "no mass band published, so the parse cannot be checked"
        if not self.band_reconciles:
            low, high = self.mass_band or (0, 0)
            return False, (
                f"mass in running order {self.mro_kilograms}kg does not match its printed "
                f"+/-5% band {low}-{high}kg, so this column is misaligned"
            )
        if (
            self.unladen_kilograms is not None
            and self.mro_kilograms is not None
            and self.unladen_kilograms >= self.mro_kilograms
        ):
            return False, (
                f"unladen weight {self.unladen_kilograms}kg is not below the mass in "
                f"running order {self.mro_kilograms}kg, so this column is misaligned"
            )
        low, high = self.mass_band or (0, 0)
        return True, f"mass in running order {self.mro_kilograms}kg matches its band {low}-{high}kg"

    @classmethod
    def from_rows(
        cls, manufacturer_range: str, model: str, rows: dict[str, str]
    ) -> EribaCaravan:
        """Build one layout from either source's `{canonical label: value}` mapping."""
        dimensions = (rows.get("length / width / height") or "").split(" / ")
        shipping, width, height = (dimensions + ["", "", ""])[:3]

        mass_text = rows.get("mass in running order") or ""
        mass_parts = mass_text.split(" / ") if " / " in mass_text else mass_text.split()
        mass = _int_or_none(mass_parts[0]) if mass_parts else None
        band: tuple[int, int] | None = None
        if len(mass_parts) >= 3:
            low, high = _int_or_none(mass_parts[1]), _int_or_none(mass_parts[2])
            if low is not None and high is not None:
                band = (low, high)

        berths_published = rows.get("berths")
        berths = None
        if berths_published:
            # The lower figure of a range, per `docs/adapters/README.md` — the higher one is
            # reached only with options. FMLV's own baseline agrees on all 18.
            berths = _int_or_none(berths_published.split(" - ")[0].strip())

        axle = rows.get("axle")
        return cls(
            manufacturer_range=manufacturer_range,
            model=model,
            rrp_pounds=_int_or_none(rows.get("price")),
            berths=berths,
            berths_published=berths_published,
            mtplm_kilograms=_int_or_none(rows.get("technically permissible maximum laden mass")),
            mro_kilograms=mass,
            mass_band=band,
            unladen_kilograms=_int_or_none(rows.get("unladen weight approx kg")),
            optional_equipment_allowance_kg=_int_or_none(
                rows.get("manufacturer-specified mass for optional equipment")
            ),
            shipping_length_mm=_cm_to_mm(shipping),
            exterior_body_length_mm=_cm_to_mm(rows.get("body length")),
            internal_length_mm=_cm_to_mm(rows.get("interior length")),
            awning_length_mm=_cm_to_mm(rows.get("a-measurement awning")),
            overall_width_mm=_cm_to_mm(width),
            height_mm=_cm_to_mm(height),
            headroom_mm=_cm_to_mm(rows.get("headroom in living area")),
            twin_axle=(axle or "").strip().lower() == "tandem",
            axle_evidence=axle,
            roof_type=rows.get("roof type"),
            # Eriba's printed label, not the canonical key — this is what a reviewer reads.
            spec_lines=tuple(
                f"{_PRINTED_LABEL.get(key, key)}: {value}"
                for key, value in sorted(rows.items())
                if value
            ),
        )


#: The fields the website republishes, and so the ones the cross-check can compare. Only
#: fields FMLV holds — there is no point reporting a divergence in a row nothing reads.
CROSS_CHECKED_FIELDS: tuple[str, ...] = (
    "rrp_pounds",
    "berths",
    "mtplm_kilograms",
    "mro_kilograms",
    "shipping_length_mm",
    "exterior_body_length_mm",
    "internal_length_mm",
    "awning_length_mm",
    "overall_width_mm",
    "height_mm",
    "headroom_mm",
)


def cross_check(
    from_pdf: EribaCaravan, from_site: EribaCaravan
) -> tuple[int, list[str]]:
    """`(fields agreed, disagreements)` between the price list and the range page.

    Verification, **not** a value source: a disagreement is reported and the price list's
    figure is still emitted. See the module docstring for why this diverges from the
    website-overrules-the-PDF rule, and note the consequence — if this ever starts
    reporting disagreements, that is a question for a human and not something the adapter
    should resolve on its own.
    """
    agreed = 0
    problems: list[str] = []
    for name in CROSS_CHECKED_FIELDS:
        mine, theirs = getattr(from_pdf, name), getattr(from_site, name)
        if mine is None or theirs is None:
            continue
        if mine == theirs:
            agreed += 1
        else:
            problems.append(f"{name}: price list says {mine}, the range page says {theirs}")
    return agreed, problems


# --------------------------------------------------------------------------- #
# Building the product
# --------------------------------------------------------------------------- #


def build_extracted(
    product: EribaCaravan,
    source_url: str,
    *,
    payload_basis: str | None = None,
    corroboration: str | None = None,
    floorplan_url: str | None = None,
    configurator: ConfiguratorLayout | None = None,
) -> ExtractedCaravan:
    """One layout as a `Caravan` plus the provenance a reviewer sees beside each field.

    `corroboration` is what the range page had to say about this layout, so a reviewer can
    see that two independent sources agree rather than taking the PDF on trust.
    `floorplan_url` is `None` for every Touring layout, which is why the positional fields
    are recorded conditionally.
    """
    features = habitation.features_from(product.spec_lines)

    caravan = Caravan(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.manufacturer_range,
        model=product.model,
        berths=product.berths,
        rrp_pounds=product.rrp_pounds,
        mtplm_kilograms=product.mtplm_kilograms,
        mro_kilograms=product.mro_kilograms,
        personal_effects_payload_kilograms=product.derived_payload_kilograms,
        shipping_length_mm=product.shipping_length_mm,
        exterior_body_length_mm=product.exterior_body_length_mm,
        internal_length_mm=product.internal_length_mm,
        awning_length_mm=product.awning_length_mm,
        overall_width_mm=product.overall_width_mm,
        height_mm=product.height_mm,
        headroom_mm=product.headroom_mm,
        twin_axle=product.twin_axle,
        body_type=CaravanBodyType.RIGID,
    )
    if "refrigeration" in features:
        caravan.refrigeration = features["refrigeration"].value  # type: ignore[assignment]

    # The two fields the price list cannot express and the configurator states outright.
    # Neither is guessed from the drawing — `technicalDataBed` names each bed's type and
    # which end it is installed at, so these are read values like any other.
    if configurator is not None:
        if configurator.bed_types:
            caravan.bed_types = list(configurator.bed_types)
        if configurator.sleeping_area is not None:
            caravan.sleeping_area = configurator.sleeping_area

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=source_url, snippet=f"{product.label} — {snippet}"
        )

    # Both halves of the identity, always. `compare_fields` walks only fields that have
    # provenance and the missing-field check fires only where nothing at all was found, so a
    # `model` read but left unrecorded is neither compared nor reported — and accepting a
    # range change without its model corrupts the name. FMLV already holds both exactly as
    # emitted here, so in practice these come back confirmed.
    record(
        "manufacturer_range",
        f'range "{product.manufacturer_range}" from the price list heading '
        f"— accept with the model, they are one name",
    )
    record(
        "model",
        f'model "{product.model}" from the price list column header '
        f"— accept with the range, they are one name",
    )

    if product.rrp_pounds is not None:
        record(
            "rrp_pounds",
            f"Price £{product.rrp_pounds:,} — recommended retail price in GBP "
            f"including VAT and On The Road charges (delivery from Germany, registration "
            f"and PDI), per Eriba's own published basis. Import duties excluded",
        )
    if product.berths is not None:
        published = product.berths_published or str(product.berths)
        note = (
            f'published as "{published}", and FMLV records the standard figure'
            if published != str(product.berths)
            else "published as a single figure"
        )
        record("berths", f"Berths {published} — {note}")
    if product.mtplm_kilograms is not None:
        record(
            "mtplm_kilograms",
            f"Technically permissible maximum laden mass: {product.mtplm_kilograms}kg",
        )
    if product.mro_kilograms is not None:
        low, high = product.mass_band or (0, 0)
        record(
            "mro_kilograms",
            f"Mass in running order (-/+ 5%): {product.mro_kilograms}kg ({low} - {high})*. "
            f"The band is the mass +/-5%, which is what checks this column's alignment",
        )
    if product.derived_payload_kilograms is not None:
        minimum = product.minimum_payload_kilograms
        basis = (
            f"; reserving Eriba's {product.optional_equipment_allowance_kg}kg "
            f"optional-equipment ceiling still leaves {minimum}kg for baggage"
            if minimum is not None
            else ""
        )
        record(
            "personal_effects_payload_kilograms",
            f"Payload {product.derived_payload_kilograms}kg, derived as MTPLM - MRO "
            f"({product.mtplm_kilograms} - {product.mro_kilograms}){basis}"
            f"{'; ' + payload_basis if payload_basis else ''}",
        )
        # No value on the product, deliberately. Eriba's published optional-equipment
        # figure is a ceiling on what may be ordered, not weight that is fitted, so it is
        # not this column's value — and FMLV holds the whole payload here on all 18 rows
        # with the required column blank, which this turns into a confirm-or-clear.
        record(
            "optional_equipment_payload_kilograms",
            f"Eriba publish no optional-equipment payload — their "
            f"{product.optional_equipment_allowance_kg}kg is a ceiling on what may be "
            f"ordered, not weight the caravan carries. Leave this blank so the two payload "
            f"columns sum to the published {product.derived_payload_kilograms}kg",
        )

    if product.shipping_length_mm is not None:
        record(
            "shipping_length_mm",
            f"Length / Width / Height: {product.shipping_length_mm // 10}cm overall, "
            f"which includes the towing hitch",
        )
    if product.exterior_body_length_mm is not None:
        record(
            "exterior_body_length_mm",
            f"Body length (exterior): {product.exterior_body_length_mm // 10}cm — the body "
            f"alone, published separately from the overall and interior lengths",
        )
    if product.internal_length_mm is not None:
        record(
            "internal_length_mm",
            f"Interior length: {product.internal_length_mm // 10}cm",
        )
    if product.awning_length_mm is not None:
        record(
            "awning_length_mm",
            f"A-measurement awning: {product.awning_length_mm // 10}cm — an awning rail "
            f"measurement, which is why it exceeds the body length",
        )
    if product.overall_width_mm is not None:
        record("overall_width_mm", f"Width: {product.overall_width_mm // 10}cm")
    if product.height_mm is not None:
        record("height_mm", f"Height: {product.height_mm // 10}cm")
    if product.headroom_mm is not None:
        record(
            "headroom_mm",
            f"Headroom in living area: {product.headroom_mm // 10}cm",
        )
    if "refrigeration" in features:
        record("refrigeration", features["refrigeration"].snippet)

    # Always recorded, never conditional: both are asserted by this adapter rather than read
    # off a row, and a reviewer should see that stated rather than infer it from a value
    # appearing with no source.
    record("twin_axle", f"Axle: {product.axle_evidence or 'not stated'}")
    record(
        "body_type",
        "A touring caravan is rigid unless its walls fold or rise — a lifting roof does not "
        "change the type, even where a manufacturer calls it a pop-up (NCC rule, "
        f"7 September 2026). Eriba publish this one as \"Roof type: "
        f"{product.roof_type or 'not stated'}\", and market no micro. Where FMLV holds "
        "pop-up, this correction is deliberate",
    )

    if corroboration:
        for name in ("mro_kilograms", "mtplm_kilograms", "rrp_pounds"):
            if name in provenance:
                existing = provenance[name]
                provenance[name] = Provenance(
                    source_url=existing.source_url,
                    snippet=f"{existing.snippet}. {corroboration}",
                )

    # Read from the configurator, so it links there rather than to the drawing: a reviewer
    # checking a bed type wants the record that states it, and the drawing is one click on.
    if configurator is not None:
        if configurator.bed_types:
            provenance["bed_types"] = Provenance(
                source_url=configurator.url,
                snippet=(
                    f"{product.label} — the configurator's standard beds: "
                    f"{configurator.bed_evidence}"
                ),
            )
        if configurator.sleeping_area is not None:
            provenance["sleeping_area"] = Provenance(
                source_url=configurator.url,
                snippet=(
                    f"{product.label} — which end each standard bed is installed at: "
                    f"{configurator.bed_evidence}"
                ),
            )

    # The configurator's rendered interior in preference to the range page's line drawing:
    # it exists for all eighteen layouts where the SVG exists for nine, and the requester
    # judged it the more readable of the two — *"if you select layout, you actually get a
    # really nice diagram of the inside that could be used to better depict the layout."*
    plan = (configurator.floorplan_url if configurator else None) or floorplan_url
    if plan:
        for name in FLOORPLAN_FIELDS:
            if name in provenance:
                continue  # already answered outright, so there is nothing to send anyone to
            provenance[name] = Provenance(
                source_url=plan,
                snippet=(
                    f"{product.label} — Eriba's specification does not say where this is. "
                    f"Open the floorplan to see the layout, then choose"
                ),
                reviewer_reference=True,
            )

    return ExtractedCaravan(caravan=caravan, provenance=provenance)


# --------------------------------------------------------------------------- #
# collect
# --------------------------------------------------------------------------- #


def _site_layouts(
    http: Fetcher,
    wanted: Sequence[tuple[str, str]],
    on_progress: Callable[[str], None],
) -> dict[str, tuple[EribaCaravan, str, str | None]]:
    """Every layout the website publishes, keyed `"<Range> <model>"`.

    Failures here are narrated and swallowed: the website is a cross-check, so losing it
    must not cost the run its products.
    """
    found: dict[str, tuple[EribaCaravan, str, str | None]] = {}
    for slug, range_name in wanted:
        url = f"{BASE_URL}{RANGE_PAGE_PATH.format(slug=slug)}"
        try:
            html = http.fetch(url).file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as error:  # noqa: BLE001 - a cross-check must never fail the run
            on_progress(f"could not fetch {url} for the cross-check ({error}) — continuing")
            continue
        layouts = parse_range_page(html)
        if not layouts:
            # Expected for Touring, whose range page has never carried technical data.
            on_progress(
                f"{range_name}: the range page publishes no technical data, so there is "
                f"nothing to cross-check and no floorplan to link ({url})"
            )
            continue
        for name, rows, floorplan in layouts:
            parts = name.split()
            if len(parts) < 2 or parts[0] not in RANGE_WORDS:
                on_progress(f"skipping unrecognised layout name {name!r} on {url}")
                continue
            caravan = EribaCaravan.from_rows(parts[0], parts[1], rows)
            found[caravan.label] = (caravan, url, floorplan)
        on_progress(f"{range_name}: {len(layouts)} layout(s) on the range page")
    return found


def _configurator_layouts(
    http: Fetcher,
    wanted: Sequence[tuple[str, str]],
    on_progress: Callable[[str], None],
) -> dict[str, ConfiguratorLayout]:
    """Every layout the configurator API publishes, keyed `"<Range> <model>"`.

    Two fetches per range: the configurator page for its `seriesId`, then the models
    endpoint. Failures are narrated and swallowed, exactly as for the range pages — this
    supplies bed types, the sleeping area and a drawing, all of which a reviewer can
    answer without, so none of it is worth losing the run's products over.
    """
    found: dict[str, ConfiguratorLayout] = {}
    for slug, range_name in wanted:
        # The range-page slug carries an `eriba-` prefix the configurator's does not.
        configurator_slug = slug.removeprefix("eriba-")
        page_url = f"{BASE_URL}{CONFIGURATOR_PATH.format(slug=configurator_slug)}"
        try:
            page = http.fetch(page_url).file_path.read_text(encoding="utf-8", errors="replace")
            series_id = parse_configurator_series_id(page)
            if series_id is None:
                on_progress(f"{range_name}: no series id on {page_url} — no configurator data")
                continue
            models_url = (
                f"{BASE_URL}{CONFIGURATOR_MODELS_PATH.format(series_id=series_id)}"
                f"?{CONFIGURATOR_MODELS_QUERY}"
            )
            payload = http.fetch(models_url).file_path.read_text(encoding="utf-8")
        except Exception as error:  # noqa: BLE001 - a supplementary source must never fail the run
            on_progress(f"could not read {range_name}'s configurator ({error}) — continuing")
            continue

        layouts = parse_configurator_models(payload, configurator_slug)
        if not layouts:
            on_progress(f"{range_name}: configurator series {series_id} listed no layouts")
            continue
        for layout in layouts:
            found[layout.label] = layout
        with_beds = sum(1 for layout in layouts if layout.bed_types)
        with_plan = sum(1 for layout in layouts if layout.floorplan_url)
        on_progress(
            f"{range_name}: configurator series {series_id} gives {len(layouts)} layout(s), "
            f"{with_beds} with bed types and {with_plan} with a drawing"
        )
    return found


def collect(
    http: Fetcher,
    browser: object = None,  # noqa: ARG001 - server-rendered; `http` snapshots every fetch
    snapshot_dir: Path | None = None,  # noqa: ARG001 - `http` owns the snapshot directory
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedCaravan]:
    """Fetch and parse every current Eriba caravan, or just the named ranges.

    Raises only where the whole source is unusable — the price list cannot be found,
    fetched, read, or is not the sterling UK edition. Anything narrower is narrated and
    skipped, per the error policy the other adapters follow.
    """
    wanted = tuple(ranges) if ranges else DEFAULT_RANGES
    wanted_labels = {label for _slug, label in wanted}

    brochures_url = f"{BASE_URL}{BROCHURES_PATH}"
    on_progress(f"fetching the Eriba brochures page: {brochures_url}")
    brochures_html = http.fetch(brochures_url).file_path.read_text(
        encoding="utf-8", errors="replace"
    )

    price_list_url = find_price_list_url(brochures_html)
    if price_list_url is None:
        msg = f"no caravan price list link found on {brochures_url}"
        raise ValueError(msg)

    on_progress(f"fetching the UK caravan price list: {price_list_url}")
    document = extract_text(http.fetch(price_list_url).file_path)
    if document.is_empty():
        msg = f"the price list at {price_list_url} yielded no text"
        raise ValueError(msg)

    problem = price_list_currency_problem(document.text)
    if problem is not None:
        msg = (
            f"refusing to read prices from {price_list_url}: {problem}. Eriba's UK list is "
            f"in sterling; a document that is not must not reach rrp_pounds"
        )
        raise ValueError(msg)

    model_year = re.search(r"ERIBA CARAVANS (\d{4})", document.text)
    if model_year:
        on_progress(f"price list is the {model_year.group(1)} model year")

    site = _site_layouts(http, wanted, on_progress)
    configurator = _configurator_layouts(http, wanted, on_progress)

    spec_pages = [
        (number, page.text)
        for number, page in enumerate(document.pages, start=1)
        if SPEC_PAGE_MARKER in page.text
    ]
    on_progress(f"found {len(spec_pages)} specification page(s) in the price list")

    extracted: list[ExtractedCaravan] = []
    for number, page_text in spec_pages:
        layouts, problems = parse_spec_page(page_text)
        for note in problems:
            on_progress(f"price list page {number}: {note}")
        if not layouts:
            continue

        for range_name, model, rows in layouts:
            product = EribaCaravan.from_rows(range_name, model, rows)
            if range_name not in wanted_labels:
                continue

            keep, reason = product.reconciles()
            if not keep:
                on_progress(f"dropping {product.label} — {reason}")
                continue

            corroboration: str | None = None
            floorplan: str | None = None
            match = site.get(product.label)
            if match is not None:
                other, site_url, floorplan = match
                agreed, disagreements = cross_check(product, other)
                if disagreements:
                    # Never silently resolved: see the module docstring on why the website
                    # verifies rather than overrules here.
                    on_progress(
                        f"{product.label}: the range page DISAGREES with the price list on "
                        f"{len(disagreements)} field(s) — {'; '.join(disagreements)}. "
                        f"Emitting the price list's figures; this needs a human"
                    )
                else:
                    corroboration = (
                        f"Corroborated by Eriba's own range page, which independently "
                        f"publishes the same {agreed} figures ({site_url})"
                    )

            layout = configurator.get(product.label)
            if layout is not None:
                # A third independent publication of the two masses and the berth count.
                # Reported, never resolved here, for the same reason the range page is:
                # the price list is the source of record and a disagreement is a question
                # for a human, not something to average away.
                differences = [
                    f"{name} price list {mine} vs configurator {theirs}"
                    for name, mine, theirs in (
                        ("berths", product.berths, layout.berths),
                        ("MTPLM", product.mtplm_kilograms, layout.mtplm_kilograms),
                        ("MRO", product.mro_kilograms, layout.mro_kilograms),
                    )
                    if mine is not None and theirs is not None and mine != theirs
                ]
                if differences:
                    on_progress(
                        f"{product.label}: the configurator DISAGREES with the price list "
                        f"on {len(differences)} field(s) — {'; '.join(differences)}. "
                        f"Emitting the price list's figures; this needs a human"
                    )

            extracted.append(
                build_extracted(
                    product,
                    price_list_url,
                    payload_basis=reason,
                    corroboration=corroboration,
                    floorplan_url=floorplan,
                    configurator=layout,
                )
            )

    if extracted:
        # Said once, every run, rather than left as a silent gap. A field the adapter never
        # attempts is invisible to the pipeline, so the only place this can be explained is
        # here — see the constant for the two independent reasons it is not collected.
        on_progress(_HEATING_NOT_COLLECTED)

    without_plan = [
        item.caravan.model
        for item in extracted
        if not any(
            provenance.reviewer_reference for provenance in item.provenance.values()
        )
    ]
    if without_plan:
        on_progress(
            f"{len(without_plan)} layout(s) have no floorplan to link, so their sleeping, "
            f"kitchen, lounge and bathroom positions carry no reviewer pointer: "
            f"{', '.join(without_plan)}"
        )

    on_progress(f"{len(extracted)} product(s) collected")
    return extracted
