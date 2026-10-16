"""Elddis (elddis.co.uk) — motorhomes and campervans, on the Erwin Hymer Group platform.

**Rebuilt 10 October 2026, because Elddis replaced their website and their whole range on
the same day.** Elddis had told the requester that FMLV was showing models no longer in the
2027 range; it was worse than that. The previous adapter read `sitemap.xml`, which now
**404s**, so a run collected *zero* products and would have reported all 29 of FMLV's
Elddis rows as disappeared.

Three things changed at once:

* every page moved under **`/en/`**;
* the **sitemap went**, taking the old roster source with it;
* the range was replaced outright — Apex, Avalon and every Evolve variant are gone, the
  old numbering (105, 115, 120, …) has become layout codes (70 DS, 74 DI, …), and **not one
  model name carries over**.

## The source is now the EHG configurator API

Elddis has moved onto the Erwin Hymer Group platform, so `ehg_configurator` — already read
for Bürstner, Carado, Eriba and Niesmann-Bischoff — serves here too, under
`brandKey=elddis`. Two kinds of request and no browser:

```
/configurator-api/brand/elddis/series        -> the ranges, each with its model year
/configurator-api/series/<id>/models         -> its layouts, with technical data and price
```

It is the manufacturer's own product database rather than a menu, which makes it a better
roster than anything the old site offered: the series list carries `modelYear`, so "what is
in the 2027 range" is answered rather than inferred. **Always filter by model year** — see
`ehg_configurator`, where a cumulative list has caught other brands out.

## What it gives, and the two units to watch

Everything FMLV requires arrives in one response per range: both masses, all three
dimensions, berths, seats, the price in sterling and the chassis make.

* **Dimensions are centimetres**, not millimetres — `lengthOverall` of `741` is 7410mm.
  Only `wheelbase` is already in millimetres, and it is not recorded.
* **Width is `widthOverallwithoutMirrors`.** `widthOverall` exists and is empty on every
  layout, so the body width is the only figure published and there is no mirrors question
  to settle.

## The price is the one beside the vehicle, German footnote and all

Each layout page prints its price with a footnote reading *"This is a recommended retail
price based on German retail prices"*. The requester's instruction, 10 October 2026, is to
**mirror what sits next to the vehicle on the website**, which is what `grossPrice` is.

The old site's £1,690 on-the-road charge is **gone** — no page carries it any more — so the
provenance no longer mentions it.

## An optional pop-top does not change the body type

Every campervan is 258cm tall and therefore a high top. Three of the Autoquest GTVs offer a
pop-top roof, and their own pages mark it `(○) Optional`, printing `258 / 280 (○)` for the
height and 358 for the roof open. Per the base-vehicle rule it is not part of the vehicle as
standard, so the body type stays `campervan_high_top` and the height recorded is 258.
"""

from __future__ import annotations

import html as htmllib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import ehg_configurator as ehg
from . import habitation
from ..fetch.http import Fetcher
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

__all__ = [
    "BASE_URL",
    "BRAND_KEY",
    "DEFAULT_RANGES",
    "EXPECTED_LAYOUTS",
    "HIGH_TOP_ABOVE_MM",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "ElddisLayout",
    "body_type_for",
    "collect",
    "model_name",
    "parse_layouts",
]

BASE_URL = "https://elddis.co.uk"
MANUFACTURER = "Elddis (EHG UK)"
MANUFACTURER_DISPLAY_NAME = "Elddis"

#: The key the configurator API knows this brand by. Lower case exactly — `ELDDIS` answers
#: `There is no brand for brandKey ELDDIS`.
BRAND_KEY = "elddis"

#: The 2027 range: six series, eighteen layouts. Kept so `--range` can name one, and
#: **reconciled against the API on every full sweep** rather than trusted — a hardcoded
#: roster is the one way this adapter can be badly wrong while looking healthy, which is
#: the lesson `bailey.py` learned the hard way.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (
    ("Autoquest GT", "Autoquest GT"),
    ("Autoquest GTS", "Autoquest GTS"),
    ("Autoquest GTV", "Autoquest GTV"),
    ("Whirlwind GT", "Whirlwind GT"),
    ("Whirlwind GTS", "Whirlwind GTS"),
    ("Whirlwind GTV", "Whirlwind GTV"),
)

EXPECTED_LAYOUTS = 18

#: A campervan taller than this is a high top. The same threshold as every other adapter
#: that needs it, set by the NCC side from FMLV's own data.
HIGH_TOP_ABOVE_MM = 2300

#: The API's own body-type vocabulary, mapped to FMLV's. `partially-integrated` is the
#: German term for a low-profile coachbuilt, which is what FMLV holds for every Elddis
#: motorhome. A value not listed here is **left unset and narrated**, never guessed.
_BODY_TYPES: dict[str, BodyType] = {
    "partially-integrated": BodyType.COACH_BUILT_LOW_PROFILE,
}


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
    """`Elddis Autoquest GT 70 DS` in series `Autoquest GT` is the model `70 DS`.

    The brand prefixes its motorhomes and not its vans — `Whirlwind GTV 554` has no
    `Elddis` — so both shapes are handled.

    **Stripped against this layout's own series**, never against a list of names, because
    `Autoquest GT` is a prefix of `Autoquest GTS`: matching by the longest name that fits
    would file every GTS layout under GT.
    """
    name = " ".join(marketing_name.split())
    for prefix in (f"{MANUFACTURER_DISPLAY_NAME} {series_name}", series_name):
        if name.lower().startswith(prefix.lower()):
            remainder = name[len(prefix) :].strip()
            return remainder or None
    if name.lower().startswith(f"{MANUFACTURER_DISPLAY_NAME} "):
        return name[len(MANUFACTURER_DISPLAY_NAME) + 1 :].strip() or None
    return name or None


def body_type_for(
    api_body_type: str | None, height_mm: int | None
) -> tuple[BodyType | None, str]:
    """FMLV's body type from the API's own word for it, and the height where it needs one.

    A campervan's half of the rule is decided on height; **an optional pop-top is ignored**,
    because the base-vehicle rule records the vehicle as standard. Elddis's own pages mark
    theirs `(○) Optional` and print the standard height beside it.
    """
    key = (api_body_type or "").strip().lower()
    if key in _BODY_TYPES:
        return _BODY_TYPES[key], (
            f"{_BODY_TYPES[key].value}, from the configurator's own {key!r}"
        )
    if key == "campervan":
        if height_mm is None:
            return None, "a campervan, but no height is published to tell a high top from a low one"
        if height_mm > HIGH_TOP_ABOVE_MM:
            return BodyType.CAMPERVAN_HIGH_TOP, (
                f"a high-top campervan: {height_mm}mm is above the {HIGH_TOP_ABOVE_MM}mm "
                f"threshold. Where a pop-top is offered Elddis mark it optional, so it does "
                f"not change the body of the vehicle as standard"
            )
        return BodyType.CAMPERVAN, (
            f"a campervan: {height_mm}mm is at or below the {HIGH_TOP_ABOVE_MM}mm high-top "
            f"threshold"
        )
    return None, (
        f"no body type proposed — the configurator calls this {api_body_type!r}, which is "
        f"not a value this adapter has been taught, and a wrong body type is worse than a "
        f"visible gap"
    )


@dataclass(frozen=True)
class ElddisLayout:
    """One layout, as the configurator describes it."""

    manufacturer_range: str
    model: str
    base_vehicle_manufacturer: str | None = None
    rrp_pounds: int | None = None
    berths: int | None = None
    seats: int | None = None
    optional_seats: int | None = None
    mtplm_kilograms: int | None = None
    mro_kilograms: int | None = None
    mh_length_mm: int | None = None
    mh_width_mm: int | None = None
    mh_height_mm: int | None = None
    body_type: BodyType | None = None
    body_type_reason: str = ""

    @property
    def label(self) -> str:
        return f"{self.manufacturer_range} {self.model}"

    @property
    def payload_kilograms(self) -> int | None:
        """Elddis publish no payload row, so it is the two masses subtracted."""
        if self.mtplm_kilograms is None or self.mro_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mro_kilograms


def parse_layouts(payload: str, series_name: str) -> list[ElddisLayout]:
    """Every layout in one series' API response.

    A layout with no usable name is skipped rather than guessed at; everything else is
    carried through with whatever fields the response holds, and `_reconciles` decides
    whether the masses are believable.
    """
    try:
        entries = json.loads(payload)
    except ValueError:
        return []
    if not isinstance(entries, list):
        return []

    layouts: list[ElddisLayout] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        model = model_name(str(entry.get("marketingName") or ""), series_name)
        if not model:
            continue
        technical: dict[str, Any] = entry.get("technicalData") or {}
        read = lambda key: ehg.technical_value(technical, key)  # noqa: E731

        height = _centimetres(read("heightOverall"))
        body_type, reason = body_type_for(entry.get("bodyType"), height)
        price = entry.get("grossPrice")
        layouts.append(
            ElddisLayout(
                manufacturer_range=series_name,
                model=model,
                base_vehicle_manufacturer=fmlv_base_vehicle(
                    str(entry.get("mainChassisManufacturerName") or "") or None
                ),
                rrp_pounds=round(price) if isinstance(price, (int, float)) else None,
                berths=_count(read("sleepingBerths")),
                seats=_count(read("maxPersons")),
                optional_seats=_count(read("extraMaxPersons")),
                mtplm_kilograms=_kilograms(read("weightGrossVehicle")),
                mro_kilograms=_kilograms(read("weightRoadworthy")),
                mh_length_mm=_centimetres(read("lengthOverall")),
                mh_width_mm=_centimetres(read("widthOverallwithoutMirrors")),
                mh_height_mm=height,
                body_type=body_type,
                body_type_reason=reason,
            )
        )
    return layouts


# --- Equipment, for the habitation findings ------------------------------------------
#
# **The configurator API carries no equipment at all** — only engine and mass data — so
# the findings come from the brand's public site, one page per layout. That is why this
# costs around twenty-five extra fetches: a home page for the ranges, an index per range
# for its layouts, and then each layout page.
#
# The rebuild of 10 October 2026 moved this adapter onto the API and dropped the findings
# with the old site parser. This restores them against the site as it now stands, which is
# a different shape entirely: tables inside a named accordion rather than bulleted `<p>`
# blocks under `Highlights`.

#: One accordion section's title. Every layout page has exactly three — the layout's own
#: name, then `Standard equipment`, then `Optional equipment`.
_ACCORDION_TITLE = re.compile(r"o-accordion__title[^>]*>(?P<title>.*?)</", re.S)

#: The two sections worth reading, matched on the title rather than on the words
#: themselves. **The phrase "standard equipment" also appears in the legal boilerplate**
#: every page carries about what a mass in running order includes, and the first table
#: after that prose is the technical-data table — `Price (incl. VAT)`, `Standard chassis`.
#: Read as equipment it would put a price and a chassis name into the habitation findings.
_STANDARD_SECTION = re.compile(r"^\s*standard equipment\s*$", re.I)
_OPTIONAL_SECTION = re.compile(r"^\s*optional equipment\s*$", re.I)

#: Inside a section, each `<table>`'s `<th>` is a group name — `Fiat chassis features`,
#: `Exterior features` — and its `<td>`s are the items. Only the cells are equipment.
_TABLE_CELL = re.compile(r"<td[^>]*>(?P<cell>.*?)</td>", re.S)


def _plain(fragment: str) -> str:
    """One line of readable text out of a markup fragment."""
    return " ".join(htmllib.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def accordion_sections(page: str) -> dict[str, str]:
    """A layout page's accordion, as `{title: body markup}`.

    Each section runs from its own title to the next, and the last to the end of the
    document — which is safe here because the last section is always `Optional equipment`,
    whose contents are discarded anyway.
    """
    titles = list(_ACCORDION_TITLE.finditer(page))
    sections: dict[str, str] = {}
    for index, title in enumerate(titles):
        end = titles[index + 1].start() if index + 1 < len(titles) else len(page)
        sections.setdefault(_plain(title.group("title")), page[title.end() : end])
    return sections


def _cells(fragment: str) -> list[str]:
    """Every table cell in a fragment, as readable lines."""
    return [
        text for cell in _TABLE_CELL.finditer(fragment) if (text := _plain(cell.group("cell")))
    ]


def parse_equipment(page: str) -> habitation.Equipment:
    """One layout page's standard and optional equipment.

    **Only the two named sections are read.** A section is standard *because its title says
    `Standard equipment`*, not because it failed to say `Optional` — the page's first
    section is the technical-data table, and treating everything non-optional as equipment
    would sweep a price and a chassis name into it.
    """
    sections = accordion_sections(page)
    standard: list[str] = []
    optional: list[str] = []
    for title, body in sections.items():
        if _STANDARD_SECTION.match(title):
            standard.extend(_cells(body))
        elif _OPTIONAL_SECTION.match(title):
            optional.extend(_cells(body))
    return habitation.Equipment(
        tuple(dict.fromkeys(standard)), tuple(dict.fromkeys(optional))
    )


#: `/en/motorhomes/autoquest-gt`, `/en/campervans/autoquest-gtv`. The product area is part
#: of the path and differs across the range — GT and GTS are motorhomes, GTV campervans —
#: so both are matched and the range is identified by its slug rather than by the folder.
_RANGE_LINK = re.compile(r'href="(?P<path>/en/(?:motorhomes|campervans)/(?P<slug>[a-z0-9-]+))"')


def find_range_paths(home_html: str) -> dict[str, str]:
    """Every range's page, keyed by its normalised slug.

    **Rediscovered rather than written in.** The slug *is* derivable from the series name
    the API gives — `Autoquest GT` normalises to the same thing as `autoquest-gt` — which
    is what makes this possible without a hardcoded map. Only the layout codes beneath are
    inconsistent; see `layout_title`.
    """
    return {
        _normalise(match.group("slug")): match.group("path")
        for match in _RANGE_LINK.finditer(home_html)
    }


def find_layout_paths(index_html: str, range_path: str) -> list[str]:
    """Every layout page a range's index links, in order."""
    pattern = re.compile(rf'href="({re.escape(range_path)}/[a-z0-9-]+)"')
    seen: dict[str, None] = {}
    for match in pattern.finditer(index_html):
        seen.setdefault(match.group(1), None)
    return list(seen)


def layout_title(page: str) -> str | None:
    """The layout's own name, from the first accordion title.

    **Matched on this rather than on the slug, because the slugs disagree with each
    other.** Autoquest writes `aq-gt-74ds` and Whirlwind writes `ww-gt-74-ds` for the same
    layout code, and neither prefix is derivable from the series name the API gives. The
    page's own heading is.
    """
    first = _ACCORDION_TITLE.search(page)
    return _plain(first.group("title")) or None if first else None


def _normalise(value: str) -> str:
    """A name reduced to the letters and digits that identify it."""
    return re.sub(r"[^A-Za-z0-9]+", "", value).upper()


def titles_this_layout(title: str, *, manufacturer_range: str, model: str) -> bool:
    """Whether a page titled `title` is the layout `manufacturer_range` / `model`.

    The motorhome pages are titled with the bare code — `74 DS` — and the campervan pages
    with the whole name — `Autoquest GTV 560`. So the series name is removed if it is
    there and what remains must equal the model exactly. An equality test rather than a
    suffix one, because `560` is a suffix of plenty that is not it.
    """
    stripped = _normalise(title).removeprefix(_normalise(manufacturer_range))
    return stripped == _normalise(model)


#: The widest payload any Elddis could credibly carry. A 3499kg motorhome against a mass in
#: running order the parse has taken from the wrong field would land outside this.
_PAYLOAD_RANGE = (100, 1500)


def _reconciles(layout: ElddisLayout) -> tuple[bool, str]:
    """Whether the two masses make sense together.

    **Elddis publish no payload row**, so unlike Bailey there is no third figure to check
    the other two against; this tests the arithmetic those two imply. A mass in running
    order at or above the permissible maximum, or a payload outside what a 3.5t vehicle can
    carry, means a figure has come from the wrong field.
    """
    mtplm, mro = layout.mtplm_kilograms, layout.mro_kilograms
    if mtplm is None or mro is None:
        return False, "the configurator states no permissible maximum or no mass in running order"
    payload = mtplm - mro
    low, high = _PAYLOAD_RANGE
    if payload <= 0:
        return False, (
            f"a mass in running order of {mro}kg at or above the {mtplm}kg permissible "
            f"maximum, which would make the payload zero or negative"
        )
    if not low <= payload <= high:
        return False, (
            f"MTPLM {mtplm}kg less MRO {mro}kg is {payload}kg, outside the {low}-{high}kg a "
            f"vehicle of this size can credibly carry"
        )
    return True, (
        f"MTPLM {mtplm}kg less mass in running order {mro}kg, giving a payload of {payload}kg"
    )


#: How each habitation reading is introduced. Findings for a person to type in, with the
#: source named because these come from a different place to every other field here — the
#: public site, not the configurator API.
_FEATURE_NOTES: dict[str, str] = {
    "heating": "the heating in the page's Standard equipment",
    "refrigeration": "the refrigeration in the page's Standard equipment",
    "microwave": "a microwave in the page's Standard equipment",
    "shower_toilet_separated": "the washroom as the Standard equipment describes it",
}


def build_extracted(
    layout: ElddisLayout,
    *,
    basis: str,
    source_url: str,
    equipment: habitation.Equipment | None = None,
    equipment_url: str | None = None,
) -> ExtractedMotorhome:
    """One Elddis layout, with provenance on everything it proposes."""
    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=layout.manufacturer_range,
        model=layout.model,
        base_vehicle_manufacturer=layout.base_vehicle_manufacturer,
        berths=layout.berths,
        mh_passenger_seats_inc_driver=layout.seats,
        rrp_pounds=layout.rrp_pounds,
        mtplm_kilograms=layout.mtplm_kilograms,
        mro_kilograms=layout.mro_kilograms,
        mh_payload_kilograms=layout.payload_kilograms,
        mh_length_mm=layout.mh_length_mm,
        mh_width_mm=layout.mh_width_mm,
        mh_height_mm=layout.mh_height_mm,
        body_type=layout.body_type,
    )

    provenance: dict[str, Provenance] = {}

    def record(field: str, snippet: str) -> None:
        provenance[field] = Provenance(
            source_url=source_url, snippet=f"{layout.label} — {snippet}"
        )

    record(
        "manufacturer_range",
        f'range "{layout.manufacturer_range}", the series name in Elddis\'s own '
        f"configurator, filtered to the 2027 model year",
    )
    if layout.rrp_pounds is not None:
        record(
            "rrp_pounds",
            f"£{layout.rrp_pounds:,}, the price shown beside this layout on Elddis's own "
            f"page. Their footnote reads 'This is a recommended retail price based on "
            f"German retail prices'; the instruction of 10 October 2026 is to mirror what "
            f"sits next to the vehicle, which is this figure",
        )
    if layout.base_vehicle_manufacturer is not None:
        record(
            "base_vehicle_manufacturer",
            f"{layout.base_vehicle_manufacturer}, the configurator's own chassis make",
        )
    if layout.berths is not None:
        record("berths", f"{layout.berths} sleeping berths, as standard")
    if layout.seats is not None:
        optional = (
            f", with {layout.optional_seats} available as an option — the standard figure is "
            f"recorded, per the settled rule"
            if layout.optional_seats and layout.optional_seats != layout.seats
            else ""
        )
        record(
            "mh_passenger_seats_inc_driver",
            f"{layout.seats} seats including the driver{optional}",
        )
    if layout.mtplm_kilograms is not None:
        record("mtplm_kilograms", f"{layout.mtplm_kilograms}kg technically permissible maximum")
    if layout.mro_kilograms is not None:
        record("mro_kilograms", f"{layout.mro_kilograms}kg mass in running order")
    if layout.payload_kilograms is not None:
        record(
            "mh_payload_kilograms",
            f"{layout.payload_kilograms}kg — {basis}. Elddis publish no payload row, so it "
            f"is the two masses subtracted",
        )
    for field, value, label in (
        ("mh_length_mm", layout.mh_length_mm, "overall length"),
        ("mh_width_mm", layout.mh_width_mm, "overall width, excluding mirrors"),
        ("mh_height_mm", layout.mh_height_mm, "overall height"),
    ):
        if value is not None:
            record(field, f"{value}mm {label}, published in centimetres and converted")
    if layout.body_type is not None:
        record("body_type", layout.body_type_reason)

    # The habitation findings, from the public site rather than the API — which carries no
    # equipment at all. Absent where the layout's page could not be matched or read, which
    # `collect` narrates; a missing page costs the findings, never the product.
    if equipment is not None:
        features = habitation.features_from(equipment.standard)
        # Dropped as on every other adapter: the copy names beds without saying which are
        # built in and which are made up out of the seating.
        features.pop("bed_types", None)
        for name, feature in features.items():
            setattr(motorhome, name, feature.value)
            provenance[name] = Provenance(
                source_url=equipment_url or source_url,
                snippet=(
                    f"{layout.label} — {feature.note or _FEATURE_NOTES.get(name, name)}: "
                    f"{feature.snippet!r}"
                ),
            )
    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


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
) -> list[ExtractedMotorhome]:
    """Every current Elddis layout, from the brand's own configurator API."""
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
    on_progress(f"model year {model_year}: {len(series)} series — {', '.join(s.name for s in series)}")

    # **The roster is checked against the adapter's own list, both ways.** A series the
    # brand has added is swept and announced rather than waited for; one this adapter knows
    # that the API no longer lists is announced too, because that is a range being retired.
    known = {label for _key, label in DEFAULT_RANGES}
    if tuple(ranges) == DEFAULT_RANGES:
        for name in sorted({s.name for s in series} - known):
            on_progress(
                f"NEW RANGE: {name!r} is in Elddis's 2027 catalogue and not in this "
                f"adapter's list — collected anyway. Add it to DEFAULT_RANGES so `--range` "
                f"can select it"
            )
        for name in sorted(known - {s.name for s in series}):
            on_progress(
                f"RANGE RETIRED: {name!r} is in this adapter's list and no longer in the "
                f"{model_year} catalogue, so nothing is collected for it"
            )
    else:
        wanted = {label for _key, label in ranges}
        series = [s for s in series if s.name in wanted]
        on_progress(f"limited to {len(series)} series: {', '.join(s.name for s in series)}")

    # The equipment the API does not carry. One fetch for the range links, then an index
    # and a page per layout — around twenty-five in all, which is the price of the
    # habitation findings and is paid once per run.
    range_paths: dict[str, str] = {}
    home = http.fetch(f"{BASE_URL}/")
    if home.status_code == 200:
        range_paths = find_range_paths(
            home.file_path.read_text(encoding="utf-8", errors="replace")
        )
        on_progress(f"the home page links {len(range_paths)} range page(s) for equipment")
    else:
        on_progress(
            f"WARNING: {BASE_URL}/ returned {home.status_code}, so no range pages could be "
            f"found and NO HABITATION FINDINGS will be reported this run. Every other "
            f"field comes from the configurator API and is unaffected"
        )

    results: list[ExtractedMotorhome] = []
    for entry in series:
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
        if not layouts:
            on_progress(
                f"[{entry.name}] NO LAYOUTS read from a response that returned 200 — the "
                f"API's shape has changed rather than the range being empty"
            )
            continue
        on_progress(f"[{entry.name}] {len(layouts)} layout(s)")

        # Each layout's equipment, read from the brand's own site and keyed by the title
        # the page gives itself. Built per range so a range whose index is missing costs
        # only its own findings.
        equipment_pages: list[tuple[str, str, habitation.Equipment]] = []
        range_path = range_paths.get(_normalise(entry.name))
        if range_path is None:
            if range_paths:
                on_progress(
                    f"[{entry.name}] NO EQUIPMENT PAGE: nothing on the home page links a "
                    f"range whose slug matches {entry.name!r}, so its habitation findings "
                    f"are not reported. Every other field is unaffected"
                )
        else:
            index_response = http.fetch(f"{BASE_URL}{range_path}")
            if index_response.status_code != 200:
                on_progress(
                    f"[{entry.name}] its range index returned "
                    f"{index_response.status_code}, so no habitation findings this run"
                )
            else:
                for layout_path in find_layout_paths(
                    index_response.file_path.read_text(encoding="utf-8", errors="replace"),
                    range_path,
                ):
                    layout_url = f"{BASE_URL}{layout_path}"
                    layout_page = http.fetch(layout_url)
                    if layout_page.status_code != 200:
                        on_progress(
                            f"[{entry.name}] {layout_path} returned "
                            f"{layout_page.status_code}; skipped for equipment"
                        )
                        continue
                    body = layout_page.file_path.read_text(encoding="utf-8", errors="replace")
                    title = layout_title(body)
                    if title is None:
                        on_progress(f"[{entry.name}] {layout_path} names no layout; skipped")
                        continue
                    equipment_pages.append((title, layout_url, parse_equipment(body)))

        for layout in layouts:
            reconciles, basis = _reconciles(layout)
            if not reconciles:
                on_progress(f"[{layout.label}] DROPPED: {basis}")
                continue
            if layout.rrp_pounds is None:
                on_progress(f"[{layout.label}] WARNING: no price published, left blank")
            if layout.body_type is None:
                on_progress(f"[{layout.label}] WARNING: {layout.body_type_reason}")

            matched = next(
                (
                    (page_url, equipment)
                    for title, page_url, equipment in equipment_pages
                    if titles_this_layout(
                        title, manufacturer_range=entry.name, model=layout.model
                    )
                ),
                None,
            )
            if matched is None and equipment_pages:
                on_progress(
                    f"[{layout.label}] NO EQUIPMENT PAGE MATCHED: the range's pages are "
                    f"titled {[title for title, _u, _e in equipment_pages]}, none of which "
                    f"reads as this layout. Its habitation findings are not reported"
                )
            equipment_url, equipment = matched or (None, None)
            results.append(
                build_extracted(
                    layout,
                    basis=basis,
                    source_url=url,
                    equipment=equipment,
                    equipment_url=equipment_url,
                )
            )
            on_progress(
                f"[{layout.label}] read: £{layout.rrp_pounds or 0:,}, "
                f"{layout.berths} berth, {layout.seats} seats, "
                f"{layout.mtplm_kilograms}kg, {layout.mh_length_mm}mm long"
            )

    on_progress(
        "NO FLOORPLAN AND NO PHOTOGRAPH IS PUBLISHED by the configurator for any Elddis "
        "layout, so the positional habitation fields cannot be pointed at a drawing."
    )
    if len(results) != EXPECTED_LAYOUTS:
        on_progress(
            f"expected {EXPECTED_LAYOUTS} layouts and collected {len(results)} — check "
            f"whether the range has really changed"
        )
    on_progress(f"collected {len(results)} Elddis product(s)")
    return results
