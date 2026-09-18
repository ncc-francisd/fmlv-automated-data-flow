"""VANTourer panel vans, from `vantourer.de`.

Surveyed and built 18 September 2026. See `docs/adapters/vantourer.md`. FMLV manufacturer
id **250**, name and display name **`VANTourer`**, NCC supplier name **`VANTourer`**.
**Campervans only.** **Eight products: four floorplans, each sold standard and as the
special edition GO!**

German brand, English-language site — and the source here is neither the site nor the
catalogue but a **UK market edition of the price list**, which is the document
`docs/adapters/README.md` tells you to look for before planning any currency conversion.

## One document holds everything

`eurocaravaning-vantourer-pricelist-01-2027-uk-web.pdf`, headed *"TECHNICAL DATA / PRICE
LIST … UK | EDITION 1/2027"*. A column per floorplan and a labelled row per field:

    TECHNICAL DATA          540 D  600 D  600 L  630 L
    Length in cm             541    599    599    636
    Width in cm (exterior/interior) 205/187 …
    Height in cm (exterior/interior) 258/190 …
    Seats with 3-point seatbelts  4  4  4  4
    Maximum authorised laden mass (kg) 1/2  3,500 …
    Mass in running order (kg) 1/3
      Standard model | Special edition GO!
      2,660 (2,527 – 2,793) | 2,738 (2,601 – 2,875) …

**The website publishes no mass at all** — neither a mass in running order nor a payload —
which is what made this look like a brand whose weights would have to be carried over. They
are all here.

## No currency conversion, because VANTourer do it themselves

The prices in this document are **sterling**, and the document says what they are:

> *"All prices in pounds, valid for the UK market are converted at a monthly assessed
> guidance rate and all prices include UK VAT at the current rate of 20%"*

with *"preliminary freight, certificate of title, gas test in Germany and UK RFL … already
included in the base retail price"*. So this is a real UK on-the-road figure and none of
the exchange-rate trouble that makes Morelo's price data the worst in the project applies —
`morelo.EUR_TO_GBP_RATE` has no counterpart here and must not gain one.

**Corroborated per model by the website**, which prints both currencies: the 600 D's page
reads `from €66,427 (£68,790)` against this document's `68,790`. Two independently written
sources agreeing on every one of the eight.

## A real four-way self-check

The price list publishes four masses that constrain each other, and the identity holds
**exactly, to the tenth of a kilogram, on all eight**:

    MTPLM - MRO == (3 x 75kg) + maximum mass of the additional equipment + minimum payload

    540 D      3500-2660 = 840.0    225+520.9+94.1  = 840.0
    600 D      3500-2815 = 685.0    225+360.1+99.9  = 685.0
    630 L GO!  3500-3073 = 427.0    225+ 98.4+103.6 = 427.0

The 225 kg is three passengers at the statutory 75 kg; the driver's 75 kg is already inside
the mass in running order. This is the strongest check in the project after `ace.py`'s, and
it is what catches the failure this source is most exposed to — see below.

**`Minimum payload` is not the payload.** It is the legal minimum a converter must leave
free, 94.1 kg on a van that carries 840. An adapter matching on the word "payload" records
a tenth of the real figure, and the arithmetic above is what would notice.

## The column-alignment risk, which is this source's real danger

Four model columns, values laid out across the row, and **the masses interleave the two
variants** — `520.9 | 442.9 360.1 | 282.1 …` is (540 D standard, 540 D GO!, 600 D standard,
600 D GO!, …). Read one value out of step and every vehicle carries its neighbour's weights,
plausibly and consistently, which is exactly the failure `docs/adapters/README.md` opens
with. Two defences:

* the **column count is asserted** against the header row, and a row whose value count is
  not four (or eight, for an interleaved one) is dropped rather than zipped short;
* the **self-check above runs per product**, and a one-column shift breaks it immediately,
  because the additional-equipment figures differ by 150 kg or more between neighbours.

**Footnote markers sit between the label and the values** — `Maximum authorised laden mass
(kg) 1/2 3,500 …` and `Minimum payload (kg) 1 94.1 …`. That `1/2` is not a value. Every
pattern therefore anchors on the unit in brackets and skips a run of footnote digits before
the first real figure.

## Identity: the range is the number, the model is the letters

FMLV holds `manufacturer_range` `540`/`600`/`630` and `model` `D`/`L`, with the special
edition as **`D GO! Edition`** — which is neither what the price list's technical table says
(`540 D`) nor what its price table says (`GO! 540 D`). So `_identity` splits the column
heading and appends FMLV's own wording; the mapping is a constant because no document
writes it that way.

The requester flagged the naming before the survey — *"the ranges are numbers so five forty
six hundred etc and some of the names are quite unusual for example this one L GO!
Edition"*.

## The 600 Ds is on the website and is not ours yet

The model index links a fifth floorplan, the **600 Ds**, with its own 2027 folder in German,
English, Italian, Swedish, Austrian and Swiss editions — and **no UK edition of anything**,
nor a single line in the UK price list. Under `docs/adapters/README.md`'s rule that the UK
importer defines the range, that reads as not sold here yet, so it is **excluded and
narrated every run** rather than silently missing: the day a UK price appears it should be
collected.

## Body type is not emitted, and FMLV's values are right

Every one of these is 2,580 mm tall, so the roof class is not in doubt — they are all high
tops. **The pop-up roof is fitted per variant**, and FMLV records exactly that:

| | 540 D | 600 D | 600 L | 630 L |
| --- | --- | --- | --- | --- |
| standard | elevating | high top | high top | high top |
| GO! | elevating | high top | **elevating** | high top |

The survey read that pattern as an inconsistency — the 600 L held both ways across its two
trims — and proposed that the roof being "optional" made all eight plain high tops. **The
requester checked the photographs on 18 September 2026 and it is neither.** The 600 L and
the 600 L GO! are both high tops and only the GO! has the elevating roof; the 540 D has it
in both trims and the 600 D and 630 L in neither. So the roof follows the individual
variant, not the floorplan and not the trim.

Nothing in the price list says which variants carry it, so **nothing here can derive it and
the field is left alone**. That was the right call for the wrong reason, and the reason is
worth correcting in place: an apparent inconsistency in the baseline is not evidence the
baseline is wrong.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..fetch.http import Fetcher
from ..fetch.pdf import extract_text
from ..product_model.model import Motorhome
from ..vehicle_class import VehicleClass
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

__all__ = [
    "BASE_URL",
    "EXPECTED_LAYOUTS",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "VEHICLE_CLASS",
    "VantourerProduct",
    "collect",
]

BASE_URL = "https://www.vantourer.de"
MANUFACTURER = "VANTourer"
MANUFACTURER_DISPLAY_NAME = "VANTourer"

VEHICLE_CLASS = VehicleClass.MOTORHOME

#: Where the price lists are listed. Rediscovered per run rather than hardcoded, because
#: the URL carries the model year (`.../2027/...pricelist-01-2027-uk-web.pdf`) and will
#: move — the trap `swift.py` hit when a brochure was retired under it.
DOWNLOADS_URL = f"{BASE_URL}/en/downloads/"

#: The **UK** edition, and only that. The same page offers `-de-`, `-at-`, `-ch-de-`,
#: `-en-`, `-it-` and `-se-` price lists; `-en-` is the international English edition and
#: quotes euro. Taking it would put euro figures in `rrp_pounds` while looking right.
_UK_PRICE_LIST = re.compile(r'href="([^"]*pricelist-\d+-(\d{4})-uk-web\.pdf)"', re.IGNORECASE)

#: Four floorplans, each sold standard and as the GO!, is eight products. VANTourer
#: publish no count of their own.
EXPECTED_LAYOUTS = 8

#: One range, so `--range` has nothing to narrow.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (("VANTourer", "VANTourer"),)

#: The technical table's header, which gives the column order every other row is read
#: against. Everything downstream is zipped to this, so a column added or dropped is
#: caught here rather than shifting every figure by one.
_COLUMNS = re.compile(r"TECHNICAL DATA\s+((?:\d{3}\s+\w+\s*)+)")

#: A floorplan heading: `540 D`, `600 Ds`, `630 L`. The digits are the range and the
#: letters the model — see the module docstring.
_FLOORPLAN = re.compile(r"(\d{3})\s+([A-Za-z]{1,3})")

#: FMLV's wording for the special edition, which no VANTourer document uses: the technical
#: table heads it `540 D` and the price table `GO! 540 D`.
GO_EDITION_SUFFIX = " GO! Edition"

#: The statutory allowance per passenger, and the reason the self-check needs it: the
#: driver's 75kg is already inside the mass in running order, so only the other three
#: count. See the module docstring.
PASSENGER_ALLOWANCE_KG = 75

#: A labelled row's values: the label, an optional unit in brackets, an optional run of
#: **footnote markers**, then the figures.
#:
#: Two things this has to get right, and the first version got neither.
#:
#: **The unit is optional and must not be allowed to swallow the values.** `Length in cm
#: 541 599 599 636` has no bracket at all, and a permissive `[^\n(]*` between label and
#: values consumed the whole row — every count assertion failed and all eight vehicles
#: were dropped.
#:
#: **The footnote marker only follows a bracket**, as in `(kg) 1/2 3,500` and `(kg) 1
#: 94.1`, and is at most three characters. Allowing it unconditionally would eat the first
#: value of `Seats with 3-point seatbelts 4 4 4 4`; allowing it to run longer would eat the
#: `205/187` of a width.
_ROW = r"{label}\s*(?:\([^)]*\)\s*(?:[\d/]{{1,3}}\s+)?)?(?P<values>[^\n]*)"

_MARKUP = re.compile(r"<[^>]+>")


def _number(value: str) -> float | None:
    """`'2,660'` to `2660.0`, `'520.9'` to `520.9`, `'–'` to `None`.

    The thousands separator is a comma throughout this document and the decimal point a
    full stop, which is the English convention — the German edition inverts both, and is
    not read.
    """
    cleaned = value.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _values(text: str, label: str, *, count: int | None = None) -> list[float]:
    """Every figure on the row beginning `label`, left to right.

    `count` asserts how many there should be — four for a per-column row, eight for one
    that interleaves the standard and GO! variants. **A row that yields the wrong number
    is returned empty rather than zipped short**, because a short row silently shifts every
    column and that is this source's characteristic failure.
    """
    match = re.search(_ROW.format(label=re.escape(label)), text, re.IGNORECASE)
    if match is None:
        return []
    found = [
        number
        for token in re.findall(r"-?\d[\d,]*\.?\d*", match.group("values"))
        if (number := _number(token)) is not None
    ]
    if count is not None and len(found) != count:
        return []
    return found


@dataclass(frozen=True)
class Floorplan:
    """One column of the technical table: a floorplan, before the GO! split."""

    heading: str
    manufacturer_range: str
    model: str



#: Where the technical table ends. Everything after it is prices, options and legal text.
_TECHNICAL_BLOCK_END = "Recommended retail price"


def technical_block(text: str) -> str:
    """Just the technical-data table, from its header row to the price table.

    **Every row pattern is scoped to this, and that is not tidiness.** The price list
    explains itself in prose both before and after the table, in the same words the rows
    use: page 2's footnote reads *"The stated weight is the maximum authorised laden
    mass"*, and page 10's legal section is headed *"2. Mass in running order"*. Searching
    the whole document finds the sentence rather than the row, comes back with no figures,
    and drops every vehicle — which is exactly what the first version did, silently and
    for all eight.
    """
    match = _COLUMNS.search(text)
    if match is None:
        return ""
    end = text.find(_TECHNICAL_BLOCK_END, match.start())
    return text[match.start() : end if end > 0 else len(text)]


def parse_columns(text: str) -> list[Floorplan]:
    """The technical table's column headings, in order.

    Everything else is read against this, so an added or withdrawn floorplan changes the
    roster here instead of shifting the figures under the old one.
    """
    match = _COLUMNS.search(text)
    if match is None:
        return []
    return [
        Floorplan(
            heading=f"{number} {letters}", manufacturer_range=number, model=letters
        )
        for number, letters in _FLOORPLAN.findall(match.group(1))
    ]



#: The last label of the berth block, after which its figures begin.
_BERTH_BLOCK_START = "Bed in the pop-up roof"

#: How many rows the berth block holds per column: the berth count itself, then the three
#: additional berths (guest bed, extra bed, pop-up bed).
_BERTH_ROWS = 4

#: One position in the berth run: a figure, or the dash meaning "not available on this
#: floorplan". The dash is an en dash in the document and a hyphen is accepted too.
_BERTH_VALUE = re.compile("[0-9]+|[\u2013-]")


def parse_berths(block: str, width: int) -> list[int]:
    """The berth count per column, from the one row that is not laid out as a row.

    Four labels are printed as a stack and their figures follow in a single run, **column
    by column** rather than row by row:

        Berths
        Additional berths:
        Guest bed at the seating area
        Extra bed in combination with fold-down bed in the rear
        Bed in the pop-up roof
        2 / 1 / 2 / 2      <- 540 D: berths, guest, extra, pop-up
        2 / 1 / 2 / 2      <- 600 D
        2 / 1 / 2 / 2      <- 600 L
        2 / 1 / 2 / EN-DASH  <- 630 L, which cannot take the pop-up roof

    So the berth count is the first of each group of four. The en dash on the 630 L counts
    as a position: dropping it would shift the last column by one.

    **The run is read a line at a time and stops at the first line that is neither a
    figure nor a dash**, which is the chassis description immediately below. A fixed
    character window instead ran straight into it and collected sixty tokens.

    **The total is then required to be exactly `width * 4`.** There is no label beside
    these figures to check them against, so the count is the only thing between a re-laid
    out block and four wrong berth counts — and a wrong berth count is not the sort of
    error a reviewer spots.
    """
    at = block.find(_BERTH_BLOCK_START)
    if at < 0:
        return []
    tokens: list[str] = []
    for line in block[at + len(_BERTH_BLOCK_START) :].splitlines():
        value = line.strip()
        if not value:
            continue
        if not _BERTH_VALUE.fullmatch(value):
            break
        tokens.append(value)
    if len(tokens) != width * _BERTH_ROWS:
        return []
    firsts = [tokens[index * _BERTH_ROWS] for index in range(width)]
    if not all(value.isdigit() for value in firsts):
        return []
    return [int(value) for value in firsts]


def parse_masses_in_running_order(text: str) -> list[float]:
    """The eight masses in running order, standard and GO! interleaved per column.

    They are not on the label's own line — the row reads `Mass in running order (kg) 1/3`
    and the figures follow on their own, each with its tolerance band in brackets
    (`2,660 (2,527 – 2,793)`). So they are taken as **the figures that carry a band**,
    which is what distinguishes them from the band's own contents.
    """
    start = text.find("Mass in running order")
    if start < 0:
        return []
    block = text[start : start + 700]
    return [
        number
        for token in re.findall(r"(\d[\d,]*)\s*\(", block)
        if (number := _number(token)) is not None
    ]


@dataclass(frozen=True)
class VantourerProduct:
    """One vehicle: a floorplan in one of its two trims."""

    manufacturer_range: str
    model: str
    is_go_edition: bool
    mh_length_mm: int | None = None
    mh_width_mm: int | None = None
    mh_height_mm: int | None = None
    travel_seats: int | None = None
    berths: int | None = None
    mtplm_kilograms: int | None = None
    mro_kilograms: int | None = None
    rrp_pounds: int | None = None
    #: The two figures the self-check needs, kept so the reason can quote them.
    additional_equipment_kg: float | None = None
    minimum_payload_kg: float | None = None

    @property
    def label(self) -> str:
        return f"{self.manufacturer_range} {self.model}"

    @property
    def payload_kilograms(self) -> int | None:
        """`MTPLM - MRO`. **Not** the price list's `Minimum payload`, which is a legal
        floor of about 95kg — see the module docstring."""
        if self.mtplm_kilograms is None or self.mro_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mro_kilograms


def read_price_list(text: str) -> list[VantourerProduct]:
    """Every vehicle in the UK price list: each column once standard and once as the GO!."""
    columns = parse_columns(text)
    if not columns:
        return []
    width = len(columns)
    # Scoped, because the document's own prose uses these labels as sentences — see
    # `technical_block`.
    block = technical_block(text)

    lengths = _values(block, "Length in cm", count=width)
    widths = _values(block, "Width in cm", count=width * 2)
    heights = _values(block, "Height in cm", count=width * 2)
    seats = _values(block, "Seats with 3-point seatbelts", count=width)
    mtplms = _values(block, "Maximum authorised laden mass", count=width)
    equipment = _values(block, "Maximum mass of the additional equipment", count=width * 2)
    minimums = _values(block, "Minimum payload", count=width)
    masses = parse_masses_in_running_order(block)
    berths = parse_berths(block, width)
    standard_prices = _price_row(text, "Recommended retail price")
    go_prices = _price_row(text, f"GO! {columns[0].heading}")

    products: list[VantourerProduct] = []
    for index, column in enumerate(columns):
        for go in (False, True):
            at = index * 2 + (1 if go else 0)
            prices = go_prices if go else standard_prices
            products.append(
                VantourerProduct(
                    manufacturer_range=column.manufacturer_range,
                    model=column.model + (GO_EDITION_SUFFIX if go else ""),
                    is_go_edition=go,
                    # Width and height print as `exterior/interior`; the exterior is the
                    # first of each pair and the only one FMLV records.
                    mh_length_mm=_cm(lengths, index),
                    mh_width_mm=_cm(widths, index * 2),
                    mh_height_mm=_cm(heights, index * 2),
                    travel_seats=_int(seats, index),
                    # Both trims of a floorplan share its berth count; the GO! adds
                    # equipment, not beds.
                    berths=berths[index] if index < len(berths) else None,
                    mtplm_kilograms=_int(mtplms, index),
                    mro_kilograms=_int(masses, at),
                    rrp_pounds=_int(prices, index),
                    additional_equipment_kg=_at(equipment, at),
                    minimum_payload_kg=_at(minimums, index),
                )
            )
    return products


def _price_row(text: str, after: str) -> list[float]:
    """The right-hand-drive price row following a heading.

    Anchored on `Right Hand Drive` rather than on the price heading alone, because the
    same block carries `Surcharges for motorization` immediately below it — a row of
    2,750s that is an engine upgrade, not a vehicle price.
    """
    start = text.find(after)
    if start < 0:
        return []
    block = text[start : start + 400]
    match = re.search(r"Right Hand Drive\s+([^\n]+)", block, re.IGNORECASE)
    if match is None:
        return []
    return [
        number
        for token in re.findall(r"\d[\d,]*", match.group(1))
        if (number := _number(token)) is not None
    ]


def _at(values: list[float], index: int) -> float | None:
    return values[index] if 0 <= index < len(values) else None


def _int(values: list[float], index: int) -> int | None:
    found = _at(values, index)
    return round(found) if found is not None else None


def _cm(values: list[float], index: int) -> int | None:
    """Centimetres to millimetres — the price list's unit for every dimension."""
    found = _at(values, index)
    return round(found * 10) if found is not None else None


def _reconciles(product: VantourerProduct) -> tuple[bool, str]:
    """The four-way mass check — see the module docstring.

    This is what catches a column shift, which is the failure this source is most exposed
    to and the one that would otherwise produce a full set of plausible, internally
    consistent vehicles carrying each other's weights.
    """
    missing = [
        name
        for name, value in (
            ("maximum laden mass", product.mtplm_kilograms),
            ("mass in running order", product.mro_kilograms),
            ("travel-seat count", product.travel_seats),
            ("additional-equipment mass", product.additional_equipment_kg),
            ("minimum payload", product.minimum_payload_kg),
        )
        if value is None
    ]
    if missing:
        return False, f"the price list gives no {', no '.join(missing)} for it"

    payload = product.mtplm_kilograms - product.mro_kilograms
    passengers = (product.travel_seats - 1) * PASSENGER_ALLOWANCE_KG
    expected = passengers + product.additional_equipment_kg + product.minimum_payload_kg
    if abs(payload - expected) > 0.6:
        return False, (
            f"maximum laden mass {product.mtplm_kilograms}kg less a mass in running order "
            f"of {product.mro_kilograms}kg leaves {payload}kg, but "
            f"{product.travel_seats - 1} passengers at {PASSENGER_ALLOWANCE_KG}kg plus "
            f"{product.additional_equipment_kg}kg of additional equipment plus a "
            f"{product.minimum_payload_kg}kg minimum payload comes to {expected:.1f}kg — "
            f"a column is out of step"
        )
    return True, (
        f"{payload}kg = {product.travel_seats - 1} passengers at "
        f"{PASSENGER_ALLOWANCE_KG}kg + {product.additional_equipment_kg}kg additional "
        f"equipment + {product.minimum_payload_kg}kg minimum payload"
    )


def build_extracted(
    product: VantourerProduct, source_url: str, *, basis: str
) -> ExtractedMotorhome:
    """One parsed vehicle as a `Motorhome` plus the provenance a reviewer sees beside it."""
    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.manufacturer_range,
        model=product.model,
        mh_length_mm=product.mh_length_mm,
        mh_width_mm=product.mh_width_mm,
        mh_height_mm=product.mh_height_mm,
        berths=product.berths,
        mh_passenger_seats_inc_driver=product.travel_seats,
        mtplm_kilograms=product.mtplm_kilograms,
        mro_kilograms=product.mro_kilograms,
        mh_payload_kilograms=product.payload_kilograms,
        rrp_pounds=product.rrp_pounds,
        base_vehicle_manufacturer=fmlv_base_vehicle("Fiat"),
    )

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=source_url, snippet=f"{product.label} — {snippet}"
        )

    record(
        "manufacturer_range",
        f'range "{product.manufacturer_range}", which is the floorplan number — VANTourer '
        f"head the column \"{product.manufacturer_range} "
        f'{product.model.replace(GO_EDITION_SUFFIX, "")}" — accept with the model, they '
        f"are one name",
    )
    record(
        "model",
        f'model "{product.model}"'
        + (
            f', spelt as FMLV spells it: the price list writes "GO! '
            f'{product.manufacturer_range} {product.model.replace(GO_EDITION_SUFFIX, "")}"'
            if product.is_go_edition
            else ""
        )
        + " — accept with the range, they are one name",
    )

    if product.mh_length_mm is not None:
        record("mh_length_mm", f"Length in cm: {product.mh_length_mm / 10:g}")
    if product.mh_width_mm is not None:
        record(
            "mh_width_mm",
            f"Width in cm (exterior/interior): {product.mh_width_mm / 10:g} exterior — the "
            f"first of the pair; the second is the interior width",
        )
    if product.mh_height_mm is not None:
        record(
            "mh_height_mm",
            f"Height in cm (exterior/interior): {product.mh_height_mm / 10:g} exterior",
        )
    if product.berths is not None:
        record(
            "berths",
            f"Berths: {product.berths} — the base count. The price list lists a guest bed, "
            f"an extra bed and a pop-up roof bed separately under 'Additional berths', and "
            f"those need options",
        )
    if product.travel_seats is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"Seats with 3-point seatbelts: {product.travel_seats} — the price list states "
            f"the belt type, so no lap belt is counted",
        )
    if product.mtplm_kilograms is not None:
        record(
            "mtplm_kilograms",
            f"Maximum authorised laden mass (kg): {product.mtplm_kilograms}",
        )
    if product.mro_kilograms is not None:
        record(
            "mro_kilograms",
            f"Mass in running order (kg): {product.mro_kilograms}, the "
            f"{'GO! special edition' if product.is_go_edition else 'standard model'} "
            f"figure. The price list prints a +/-5% production tolerance beside it; the "
            f"central figure is the one recorded",
        )
    if product.payload_kilograms is not None:
        record(
            "mh_payload_kilograms",
            f"{product.payload_kilograms}kg, derived as the maximum laden mass less the "
            f"mass in running order. NOT the price list's 'Minimum payload' of "
            f"{product.minimum_payload_kg}kg, which is the legal floor rather than the "
            f"capacity. Checked: {basis}",
        )
    if product.rrp_pounds is not None:
        record(
            "rrp_pounds",
            f"£{product.rrp_pounds:,} — the UK edition's right-hand-drive retail price. "
            f"VANTourer convert it themselves at a monthly guidance rate, and it includes "
            f"UK VAT at 20%, delivery freight, certificate of title, gas test and UK RFL",
        )
    record(
        "base_vehicle_manufacturer",
        "Fiat Ducato 2,2 l Multijet3 — the only chassis the price list offers",
    )

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


def find_price_list_url(downloads_html: str) -> tuple[str, str] | None:
    """The newest UK price list linked from the downloads page, as `(url, year)`.

    Newest by the model year in the filename rather than by position, since the page keeps
    several seasons. **Only `-uk-`**: see `_UK_PRICE_LIST` on why the `-en-` edition is the
    wrong document despite also being English.
    """
    found = _UK_PRICE_LIST.findall(downloads_html)
    if not found:
        return None
    path, year = max(found, key=lambda pair: pair[1])
    return (path if path.startswith("http") else f"{BASE_URL}{path}"), year


def collect(
    http: Fetcher,
    browser: object = None,  # noqa: ARG001
    snapshot_dir: Path | None = None,  # noqa: ARG001
    *,
    ranges: tuple[tuple[str, str], ...] | None = None,  # noqa: ARG001
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Fetch and parse every VANTourer sold in the UK.

    `browser` and `snapshot_dir` are unused; `ranges` is accepted and ignored, there being
    one range.
    """
    on_progress(f"fetching the downloads page: {DOWNLOADS_URL}")
    downloads = http.fetch(DOWNLOADS_URL).file_path.read_text(
        encoding="utf-8", errors="replace"
    )

    found = find_price_list_url(downloads)
    if found is None:
        # Said loudly: the international `-en-` edition is on the same page and quotes
        # euro, so falling back to it would fill `rrp_pounds` with the wrong currency.
        on_progress(
            f"no UK price list (…-uk-web.pdf) linked from {DOWNLOADS_URL} — the "
            f"international English edition is NOT a substitute, it quotes euro. Nothing "
            f"can be collected until a UK edition is published or this adapter is updated."
        )
        return []

    url, year = found
    on_progress(f"reading the {year} UK price list: {url}")
    document = extract_text(http.fetch(url).file_path)
    if document.is_empty():
        on_progress(f"{url} holds no extractable text — nothing can be collected")
        return []

    products = read_price_list(document.text)
    if not products:
        on_progress(
            f"no technical-data columns found in {url} — the table's shape has changed"
        )
        return []

    on_progress(
        f"{len(products)} vehicle(s) in the price list: "
        + ", ".join(sorted({product.manufacturer_range for product in products}))
        + " each standard and as the GO! special edition"
    )
    if len(products) != EXPECTED_LAYOUTS:
        on_progress(
            f"expected {EXPECTED_LAYOUTS} and the price list gives {len(products)} — "
            f"VANTourer publish no count of their own, so check this is a real change"
        )

    extracted: list[ExtractedMotorhome] = []
    for product in products:
        reconciles, reason = _reconciles(product)
        if not reconciles:
            on_progress(f"dropping {product.label} — {reason}")
            continue
        extracted.append(build_extracted(product, url, basis=reason))
        on_progress(
            f"read {product.label}: {product.mh_length_mm}mm, "
            f"{product.mro_kilograms}kg in running order, {product.payload_kilograms}kg "
            f"payload, £{product.rrp_pounds:,}"
        )

    # Said once per run, not per product. Both are judgements for a person, and neither is
    # something this adapter should quietly decide — see the module docstring.
    on_progress(
        "BODY TYPE NOT PROPOSED, and FMLV's values are right: every one of these is a high "
        "top, and the pop-up roof is fitted to particular variants rather than to a whole "
        "floorplan or a whole trim — the 540 D has it in both trims, the 600 L only as the "
        "GO!, and the 600 D and 630 L in neither. The price list does not say which "
        "variants carry it, so nothing here can derive it. Leave the stored values alone."
    )
    on_progress(
        "the website also lists a 600 Ds, which appears in NO UK document — no UK price "
        "list line and no UK folder — so it is not collected. Check for a UK price at "
        "model-year changeover."
    )
    on_progress(f"collected {len(extracted)} VANTourer(s)")
    return extracted
