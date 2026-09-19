"""Westfalia campervans, from the UK price lists and brochures on `campersales.co.uk`.

Surveyed and built 18 September 2026. See `docs/adapters/westfalia.md`. FMLV manufacturer
id **266**, NCC supplier name **`Westfalia`**. **Campervans only.**

## FMLV spells the manufacturer wrongly, and this module has to as well

`fmlv_manufacturer` is **`Westfailia`** — a typo in FMLV — against a display name of
`Westfalia`. The export confirms it on all eight rows. That string is the join key, so
`MANUFACTURER` carries the misspelling deliberately: correcting it would find an empty
baseline and propose every product as new. The requester confirmed on 18 September 2026
that it cannot be changed on the FMLV side without disturbing other things, and that the
public sees only the display name.

The id is **266**. There is no manufacturer 124.

## Two documents per range, and each holds half of what FMLV needs

`campersales.co.uk/camper-guide/westfalia/` lists eleven ranges; FMLV holds five. Each
range page links up to three PDFs, and **the two that matter hold different fields**:

* the **price list** (`Columbus-Pricelist-MY26-UK-March-2026.pdf`) — dimensions,
  permissible total weight, and prices;
* the **brochure** (`CATALOGUE_WESTAFLIA_24P_COLOMBUS_EN_WEB_2026.pdf`) — the **mass in
  running order**, and nothing else this adapter reads.

Filenames follow no pattern between ranges, so both are discovered from the page rather
than constructed.

**Figures are taken from Columbus only.** The other four ranges FMLV holds are collected
**by name**, which is not the same as being skipped — see `RANGES`. Collecting four of
eight products would report the other four as discontinued, which is what `vantage.py` did
to two live campervans before it was caught.

## The mass in running order is in the brochure, and this survey nearly missed it

It is in neither the price list nor on the parent site. The price list *defines* it on its
last page without ever stating a figure, and `westfalia-mobil.com` publishes nothing at all
— checked in English and German, where `/de/downloads/` and `/de/preislisten/` hold no PDFs
and the only documents are the same brochure this site hosts.

**The survey first reported that it was published nowhere. That was wrong, and how it went
wrong is worth keeping.** The brochure's own label comes out of the text extraction broken
across a line — `Mass in running` newline `order` — so a search for the literal phrase
found nothing, and a window that stopped at the newline captured the label and no figures.
Both read exactly like a document with no masses in it. The requester found the panel by
eye and said so, which is the only reason it is here.

    Mass in running order / Permissible total weight
    COLUMBUS 540 D : 2.865 kg / 3.500 kg      COLUMBUS 600 D : 2.935 kg / 3.500 kg
    COLUMBUS 600 E : 2.975 kg / 3.500 kg      COLUMBUS 640 E : 3.030 kg / 3.500 kg

**This panel is the only figure here keyed by name rather than by column position**, which
matters more than it sounds: FMLV's stored Columbus masses turn out to hold exactly the
error that position-based reading causes. The **600 D and 600 E carry each other's mass**,
2,975 against 2,935, and the first run corrects both.

## A real cross-document self-check

The price list and the brochure are written separately and **both state the permissible
total weight**. `_reconciles` compares them and drops a layout where they disagree, which
is what would catch the column shift this source is otherwise exposed to — the brochure's
figures cannot shift, because they are labelled.

With the mass in hand the payload is derivable too (`MTPLM - MRO`), so the four Columbus
layouts carry a complete set of masses where before they carried none.

## The base price is the cheapest engine on the Light-Chassis

The price table is four engine rows deep and the wrong row is £9,000 out:

    Base Price                                    540 D    600 D    600 E    640 E
    Light-Chassis 3.500 kg
      88 kW/120 HP Manual                           -     £68.919  £68.473    -
      104 kW/140 HP Manual                          -     £70.586  £70.476  £70.856
      104 kW/140 HP Automatic                    £70.475  £74.089  £73.979  £74.359
      132 kW/180 HP Automatic                    £73.634  £76.766  £76.320  £77.963
    Maxi Chassis 3.500 kg (not for 540 D)
      132 kW/180 HP Automatic                       -     £77.133  £76.687  £78.329

**Each layout is priced on a different engine** — a dash means that engine is not offered —
so there is no single row to read. The rule is the base-vehicle rule: **the cheapest price
in the column**, which is the standard engine on the standard chassis. It reproduces FMLV's
four figures exactly.

Taking the minimum also disposes of the **Maxi Chassis** rows, which are a heavier chassis
sold as an upgrade and are strictly dearer. They are excluded twice over: they are never
cheaper, and their engine labels do not survive the text extraction attached to their
values, so `_PRICE_ROW` does not match them at all.

`MINIMUM_VEHICLE_PRICE` is what keeps the options out — the same document prices a £141
seat cover and a £12,818 roof package, and an unbounded minimum would take the £141.

## The dimensions are one row and one label

    L/W/H 5.413/2.050/2.600 5.998/2.050/2.600 5.998/2.050/2.600 6.363/2.050/2.600

Length, width and height together, in metres, with a **dot as the thousands separator** —
`5.413` is 5,413 mm, not 5.413 m. One label for three fields, as the requester noted.

## What the extraction does and does not survive

The PDF's text comes out with its section headings collected at the top of the document
and their content hundreds of lines below, and the equipment matrix interleaved with the
dimensions block. **The rows this adapter needs come out intact**, which is why line
parsing works at all — but nothing may be inferred from a row's *position*, only from its
label. Every pattern here is anchored on its label and asserts its own value count.

## The column count, and a row that runs into the next

Four columns, and every row of the price list is read against them. A row yielding **fewer**
than four values is refused rather than zipped short, because a short row shifts every
layout onto its neighbour's figures.

A row may yield **more**, and that is not an error: the extraction runs two rows together
where one is short, so the 140 HP Automatic row comes out with seven cells — its own four
followed by three belonging to the Maxi Chassis row below it. Only the first four are that
row's own. Demanding exactly four discarded the row entirely, and the 540 D then fell back
to the 180 HP price: **£73,634 against the correct £70,475**, which is the same class of
error as reading the Maxi Chassis line and just as plausible.
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
    "WestfaliaProduct",
    "collect",
]

BASE_URL = "https://www.campersales.co.uk"

#: **Misspelt on purpose** — see the module docstring. This is FMLV's own string and the
#: key every product is matched on.
MANUFACTURER = "Westfailia"
MANUFACTURER_DISPLAY_NAME = "Westfalia"

VEHICLE_CLASS = VehicleClass.MOTORHOME

GUIDE_URL = f"{BASE_URL}/camper-guide/westfalia/"

#: Four Columbus layouts plus the four single-layout ranges collected by name — the
#: eight products FMLV holds. Westfalia publish no count of their own.
EXPECTED_LAYOUTS = 8


@dataclass(frozen=True)
class Range:
    """One range, its page, and the layouts its price list columns are in order."""

    slug: str
    fmlv_range: str
    base_vehicle: str
    models: tuple[str, ...]
    #: Whether the **price list** is read for this range. `False` means the range has no
    #: usable one, and only the brochure is consulted.
    figures: bool = True
    #: Which fields the **range page's own specification table** may supply. Preferred to
    #: the brochure wherever both have a figure, because the page is per layout and
    #: carries no variants to choose between.
    from_page: tuple[str, ...] = ()
    #: Whether this range's price list is read for its **price** alone. A single-layout
    #: range has no columns to align, so the cheapest vehicle price in the document is its
    #: base price — see `parse_cheapest_price`.
    price_from_list: bool = False
    #: Which fields the **brochure** may supply, for a range whose price list is unusable.
    #: Named explicitly rather than "everything readable", because the brochures publish
    #: several variants of some fields and only one of the vehicle FMLV holds — see
    #: `RANGES`. A field not named here is left alone whatever the document says.
    from_brochure: tuple[str, ...] = ()


#: Every range FMLV holds. **Only Columbus carries figures**; the other four are here so
#: that they are *collected* rather than reported as having left the range.
#:
#: That distinction is the whole reason this tuple is not just Columbus. An adapter that
#: collects four of a manufacturer's eight products tells the reviewer the other four have
#: been discontinued — `vantage.py` did exactly that to Westfalia's equivalents, two live
#: campervans, before it was caught. Here it would retire the James Cook, the Jules Verne,
#: the Sven Hedin and the Club Joker Urban in one run.
#:
#: **Why the other four carry no figures**, when their brochures do state a mass:
#:
#: * **Sven Hedin** — `2 955 kg / 3 500 kg`, which matches FMLV. Readable, but the
#:   separator is a space where Columbus uses a dot;
#: * **Club Joker Urban** — `2.608 kg (Classic), Premium version from 2.715 kg / 3.300 kg`.
#:   The figure FMLV holds is the *Classic*, and the pair a naive reader finds is
#:   `2.715 / 3.300` — the Premium. Wrong by 107kg, and plausible;
#: * **James Cook** — `Classic : 3.075 kg, Premium : 2.930 kg / 3.500 kg`. FMLV holds
#:   2,930, which is the **Premium**; its price list heads two columns `600D CLASSIC` and
#:   `600D PREMIUM` where FMLV has one row. Which of the two FMLV means is a product
#:   decision, not a parsing one;
#: * **Jules Verne** — no mass panel and no price list at all.
#:
#: Each is narrated every run with what its brochure actually says, so the decision can be
#: made from the run rather than from a fresh survey.
RANGES: tuple[Range, ...] = (
    Range("columbus", "Columbus", "Fiat", ("540 D", "600 D", "600 E", "640 E")),
    Range(
        "james-cook", "James Cook", "Mercedes", ("600 D",), figures=False,
        from_page=("length", "width", "height", "seats", "mro", "mtplm"),
        price_from_list=True,
    ),
    Range(
        "jules-verne", "Jules Verne", "Mercedes", ("Jules Verne",), figures=False,
        from_page=("length", "width", "height", "seats", "mro", "mtplm"),
    ),
    Range(
        "sven-hedin", "Sven Hedin", "MAN", ("Sven Hedin",), figures=False,
        from_page=("length", "width", "height", "seats", "mro", "mtplm"),
    ),
    Range(
        "club-joker-urban", "Club Joker Urban", "Ford", ("Club Joker Urban",),
        figures=False,
        from_page=("length", "width", "height"),
        # Its page carries no mass at all; its brochure does, and names the Classic first.
        from_brochure=("mro", "mtplm"),
        price_from_list=True,
    ),
)

#: What each brochure says about the masses of a range this adapter does not take figures
#: from — quoted in the run so the gap is a decision waiting, not a silence.
UNREAD_MASSES: dict[str, str] = {
    "James Cook": "NOTE its mass: the page says 2,886kg where the brochure says Classic "
    "3,075 / Premium 2,930 and FMLV holds 2,930. The page is preferred because every "
    "dimension on it matches FMLV exactly, but the three disagree and a reviewer should "
    "look.",
    "Jules Verne": "Its page table is complete and agrees with FMLV on every figure read.",
    "Sven Hedin": "NOTE its mass: the page says 2,965kg against the brochure's 2,955 and "
    "FMLV's 2,955 — a 10kg difference worth a look.",
    "Club Joker Urban": "Its page carries no mass, so those come from its brochure "
    "(2,608kg Classic, not the 2,715kg Premium) and match FMLV. Its seat count is on "
    "neither document.",
}

#: **Berths are not read from anywhere**, and the reasoning went round twice before
#: landing — so it is set down in full.
#:
#: The range pages state **4**; FMLV holds **2**. The requester's rule, 18 September 2026:
#: *"if they have a roof, with a roof bed in them, an elevating roof, with a sleeping
#: area, and if that's standard, then the berths would be four, because you add the extra
#: two. That's the rule."*
#:
#: The rule is right and the premise was wrong. **Every brochure marks the extra two as
#: optional**, and says so in its own footnote:
#:
#: | range | icon strip | its own note |
#: | --- | --- | --- |
#: | Columbus | `2 + 2*` | `*optional pop-up roof bed` |
#: | Sven Hedin | `2 + 2*` | `*optional pop-up roof` |
#: | James Cook | `2 + 2` | `*optional pop-up roof bed` |
#: | Club Joker Urban | `2 + 2` | `*optional (Premium version)` |
#: | Jules Verne | `2+2` | — |
#:
#: Columbus settles it beyond doubt: its price list carries the pop-up roof as a priced
#: package, `Westfalia Pack Pop Up Roof Plus … £10.682`. An option does not change the base
#: vehicle, so the base is 2 and the pages' 4 is the roof raised.
#:
#: Berths were briefly proposed as 4 on three products before the brochures were read.
#: They are not proposed at all now, and FMLV's 2 stands — which the brochures agree with.
BERTHS_FROM_PAGE = (
    "BERTHS COME FROM THE BROCHURE'S ICON STRIP, which prints '2 + 2' and footnotes the "
    "second figure as an optional pop-up roof — priced at GBP10,682 in Columbus's own "
    "price list. The base figure is recorded, so these read 2 and not the range pages' 4, "
    "which is the roof raised. A standard roof bed would have counted; an optional one "
    "does not."
)

#: Ranges on the guide page that are deliberately not collected, so the roster check
#: reports only something genuinely new.
KNOWN_UNCOLLECTED: tuple[str, ...] = (
    "amundsen", "club-joker", "club-joker-city", "club-joker-urban", "james-cook",
    "jules-verne", "kelsey", "kepler", "kipling", "sven-hedin",
)

#: A price list linked from a range page. The filenames follow no pattern —
#: `Columbus-Pricelist-MY26-UK-March-2026.pdf` against `james-cook-pricelist-2026.pdf` —
#: so it is found by containing "price", never constructed.
_PRICE_LIST_HREF = re.compile(r'href="([^"]*price[^"]*\.pdf)"', re.IGNORECASE)

#: `L/W/H 5.413/2.050/2.600 …` — one label for three fields, one triple per column.
_DIMENSIONS = re.compile(r"L/W/H[^\n]*")
_TRIPLE = re.compile(r"(\d[\d.]*)/(\d[\d.]*)/(\d[\d.]*)")

#: `Permissible total weight 3.500 kg 3.500 kg …`
_WEIGHT_ROW = re.compile(r"Permissible total weight([^\n]*)")

#: One engine row of the base-price table, with a price or a dash per column. Anchored on
#: the engine description so that only rows carrying their own label are read — which is
#: what excludes the Maxi Chassis rows, whose labels do not survive the extraction beside
#: their values.
_PRICE_ROW = re.compile(
    r"^[\d,.]+\s*l\s*Multijet3[^\n]*?\s+((?:(?:£[\d.]+|-)\s*){2,8})$", re.MULTILINE
)

#: Below this a figure is an option, not a vehicle: the same document prices a £141 seat
#: cover and a £12,818 roof package, and an unbounded minimum would take the £141.
MINIMUM_VEHICLE_PRICE = 30_000


def _number(value: str) -> int | None:
    """`'5.413'` to `5413`, `'70.475'` to `70475`.

    The thousands separator is a **dot** throughout this document, German-fashion, and
    there are no decimals in any field read here.
    """
    cleaned = value.replace(".", "").replace(",", "").strip()
    return int(cleaned) if cleaned.isdigit() else None


def find_price_list_url(page_html: str) -> str | None:
    """The price list linked from a range page, or `None`."""
    match = _PRICE_LIST_HREF.search(page_html)
    if match is None:
        return None
    href = match.group(1)
    return href if href.startswith("http") else f"{BASE_URL}{href}"


def parse_dimensions(text: str, width: int) -> list[tuple[int, int, int]]:
    """`(length, width, height)` in millimetres per column, or nothing.

    Returns empty unless there is exactly one triple per column — a short row would put
    each layout on its neighbour's dimensions, and no arithmetic here would notice.
    """
    match = _DIMENSIONS.search(text)
    if match is None:
        return []
    found = [
        (length, wide, high)
        for raw in _TRIPLE.findall(match.group(0))
        if None not in (triple := tuple(_number(part) for part in raw))
        for length, wide, high in (triple,)
    ]
    return found if len(found) == width else []


def parse_weights(text: str, width: int) -> list[int]:
    """The permissible total mass per column, in kilograms."""
    match = _WEIGHT_ROW.search(text)
    if match is None:
        return []
    found = [
        value
        for token in re.findall(r"([\d.]+)\s*kg", match.group(1), re.IGNORECASE)
        if (value := _number(token)) is not None
    ]
    return found if len(found) == width else []


def parse_base_prices(text: str, width: int) -> list[int | None]:
    """The base price per column: **the cheapest engine offered on the base chassis.**

    Each layout is priced on a different engine and a dash means that engine is not
    offered, so there is no single row to read — see the module docstring. The minimum is
    the base-vehicle figure, and it also excludes the dearer Maxi Chassis rows.

    A row whose cell count does not match the columns is ignored rather than zipped short.
    """
    columns: list[list[int]] = [[] for _ in range(width)]
    for row in _PRICE_ROW.finditer(text):
        cells = re.findall(r"£([\d.]+)|(-)", row.group(1))
        # **At least** `width`, and only the first `width` are this row's own. The
        # extraction runs two rows together where one is short: the 140 HP Automatic row
        # comes out with seven cells, its own four followed by three from the Maxi Chassis
        # 4.250 kg row below it. Demanding exactly four discarded it, and the 540 D then
        # fell back to the 180 HP price — £73,634 against the correct £70,475.
        if len(cells) < width:
            continue
        for index, (price, _dash) in enumerate(cells[:width]):
            value = _number(price) if price else None
            if value is not None and value >= MINIMUM_VEHICLE_PRICE:
                columns[index].append(value)
    return [min(prices) if prices else None for prices in columns]



#: The brochure link on a range page — "Download brochure", and the document the price
#: list is not. It is where the **mass in running order** lives, which nothing else
#: publishes: not the price list, and not westfalia-mobil.com in either language.
_BROCHURE_HREF = re.compile(r'href="([^"]*CATALOGUE[^"]*\.pdf)"', re.IGNORECASE)

#: `Mass in running order / Permissible total weight COLUMBUS 540 D : 2.865 kg / 3.500 kg`
#:
#: **The label itself is broken across a line.** The text comes out as `Mass in running`
#: newline `order`, so `\s+` is needed between every word — and the window after it has
#: to cross newlines too. A single-line window matched the label and then captured
#: nothing at all, which reads exactly like a brochure with no masses in it. That is how
#: this survey first concluded, wrongly, that the figure was published nowhere.
_MASS_PANEL = re.compile(r"Mass\s+in\s+running\s+order.{0,700}", re.DOTALL)

#: One layout's entry inside that panel: `COLUMBUS 540 D : 2.865 kg / 3.500 kg`.
_MASS_ENTRY = re.compile(
    r"([A-Z][A-Z\s]{2,18}?\s+\d{3}\s*[A-Z])\s*:\s*([\d. ]+?)\s*kg\s*/\s*([\d. ]+?)\s*kg",
    re.IGNORECASE,
)


def parse_brochure_masses(text: str) -> dict[str, tuple[int, int]]:
    """`model -> (mass in running order, permissible total weight)` from the brochure.

    **This is the only place Westfalia publish a mass in running order.** The price list
    defines the term on its last page without ever stating a figure, and the parent site
    publishes nothing at all — so without the brochure `mro_kilograms` could not be
    refreshed and no payload could be derived.

    The panel keys each figure by the layout's own name (`COLUMBUS 540 D`), which is what
    makes it safe: unlike every other row in these documents it is **not positional**, so
    a layout cannot pick up its neighbour's mass. That matters here more than usual,
    because FMLV's stored Columbus masses turn out to be exactly that error — 600 D and
    600 E hold each other's figures.

    The thousands separator varies between brochures — Columbus writes `2.865`, Sven Hedin
    writes `2 955` — so both are stripped.
    """
    panel = _MASS_PANEL.search(text)
    if panel is None:
        return {}
    masses: dict[str, tuple[int, int]] = {}
    for name, running, total in _MASS_ENTRY.findall(panel.group(0)):
        mro, mtplm = _number(running), _number(total)
        if mro is None or mtplm is None:
            continue
        # "COLUMBUS 540 D" -> "540 D": the range name is already the range, and the layout
        # is what keys this. Everything before the first figure is dropped rather than one
        # leading word, because the capture can run back into the preceding text — the
        # first entry came out as "order  COLUMBUS 540 D" and keyed itself wrongly, so the
        # 540 D silently lost its mass while the other three kept theirs.
        model = re.sub(r"^.*?(?=\d)", "", name.strip(), flags=re.DOTALL)
        if model:
            masses[model.upper()] = (mro, mtplm)
    return masses



#: `B: Length 5.932 mm`, `C: Width 2.050 mm`, `Height 2.050 mm` — the brochure's own
#: dimensions panel, which is a different block from the mass panel and was missed on the
#: first pass.
#:
#: **The figures carry spaces inside them.** Sven Hedin's brochure extracts as
#: `A: Wheelbase 3 640 m m B: Length 5 986 mm C: Width 2 040 mm D: Height 2 67 0 mm`, so
#: `2 67 0` is 2,670 and even the unit is split. Every separator — space or dot — is
#: stripped before the figure is read.
_BROCHURE_DIMENSION = r"{label}\s*:?\s*([\d.\s]+?)\s*m\s*m"


def parse_brochure_dimension(text: str, label: str) -> int | None:
    """One labelled dimension from the brochure, in millimetres.

    **Only a label with a single figure after it can be read this way**, which is why
    `Range.from_brochure` names the fields rather than this function taking whatever it
    finds: James Cook's panel lists *five* heights (`Height Classic`, `Height Classic PR`,
    `Height Premium`, `Height Premium Offroad`, `Height Premium PR`) and Sven Hedin's two,
    one of them with the pop-up roof raised. Taking the first would put a variant's height
    on the base vehicle.
    """
    import re as _re

    match = _re.search(_BROCHURE_DIMENSION.format(label=label), text, _re.IGNORECASE)
    return _number(match.group(1)) if match else None


def parse_brochure_single_mass(text: str) -> tuple[int | None, int | None]:
    """`(mass in running order, permissible total weight)` where the panel gives one pair.

    The **first** mass and the one after the final slash, which is what the two usable
    shapes need:

        2 955 kg / 3 500 kg                                        -> (2955, 3500)
        2.608 kg (Classic), Premium version from 2.715 kg / 3.300 kg -> (2608, 3300)

    Club Joker Urban's is the reason it is the *first* rather than the last: FMLV holds the
    Classic, and the pair a naive reader finds is `2.715 / 3.300`, the Premium, 107kg out.

    James Cook's shape — `Classic : 3.075 kg, Premium : 2.930 kg / 3.500 kg` — would give
    the Classic here, and FMLV holds the **Premium**. So James Cook does not name `mro` in
    `from_brochure`, and this function is never asked about it.
    """
    import re as _re

    panel = _MASS_PANEL.search(text)
    if panel is None:
        return None, None
    block = panel.group(0)
    masses = _re.findall(r"([\d.\s]+?)\s*kg", block)
    if not masses:
        return None, None
    total = _re.search(r"/\s*([\d.\s]+?)\s*kg", block)
    return _number(masses[0]), (_number(total.group(1)) if total else None)



#: One row of a range page's own specification table, which is a far better source than
#: either PDF for a single-layout range — and, on the evidence, **the source FMLV was
#: populated from**: every length, width and height in it matches FMLV exactly across all
#: four ranges that have one.
#:
#:     James Cook 600 D Specification
#:     Length                 5932 mm
#:     Width                  2050 mm
#:     Height                 2850 mm
#:     Mass in Running Order  2886 kg
#:     Permissible Weight     3500 kg
#:     Seats                     4
#:     Berths                    4
#:
#: Per layout, one figure per field, no variants to choose between — none of which is true
#: of the brochure, whose James Cook panel offers five heights and two masses.
_SPEC_ROW = r"\|\s*{label}\s*\|\s*([\d,]+)\s*(?:mm|kg)?\s*\|"

#: Tags become pipes so a label and its value stay separable, the same treatment the
#: price-list rows get.
_TAGS = re.compile(r"<[^>]+>")
_SCRIPTS_HTML = re.compile(r"<(script|style)\b.*?</\1>", re.DOTALL | re.IGNORECASE)


def parse_specification_table(page_html: str, label: str) -> int | None:
    """One labelled figure from a range page's specification table.

    **The page disagrees with the brochure on the masses**, and that is a finding rather
    than a parsing problem: the page gives the James Cook 2,886kg where the brochure gives
    Classic 3,075 and Premium 2,930, and the Sven Hedin 2,965 against the brochure's
    2,955. FMLV holds the brochure's figures on both. Since every dimension here matches
    FMLV and the masses do not, the page looks like FMLV's original source with its masses
    since revised — so the difference is proposed, and a reviewer decides.
    """
    from html import unescape as _unescape

    text = _TAGS.sub("|", _SCRIPTS_HTML.sub(" ", page_html))
    text = re.sub(r"(\|\s*)+", "|", re.sub(r"\s+", " ", _unescape(text)))
    match = re.search(_SPEC_ROW.format(label=re.escape(label)), text, re.IGNORECASE)
    return _number(match.group(1)) if match else None



def parse_cheapest_price(text: str) -> int | None:
    """The base price of a single-layout range: the cheapest vehicle price in its list.

    The same base-vehicle rule Columbus needs, and for the same reason — a range is priced
    once per engine and trim, so there is no single row to read:

        2.0 L R4 150 BHP CLASSIC (Manual Transmission)       £ 95.637
        2.0 L R4 150 BHP CLASSIC (Automatic Transmission)    £ 98.542
        2.0 L R4 190 BHP PREMIUM (incl. All-Wheel Drive)     £114.731

    The cheapest is the standard engine on the standard trim, and it is what FMLV holds.
    `MINIMUM_VEHICLE_PRICE` keeps the options out: the same document prices a £278 trailer
    socket and a £2,026 set of headlights.
    """
    prices = [
        value
        for token in re.findall(r"£\s*([\d.]+)", text)
        if (value := _number(token)) is not None and value >= MINIMUM_VEHICLE_PRICE
    ]
    return min(prices) if prices else None



#: The berth figure in a brochure's icon strip: `2 + 2*`, base plus the optional pop-up
#: roof. Single digits, because these are berth counts and a wider pattern would match a
#: date or a dimension.
#:
#: **Two alternatives, because the strips extract with their icons run together** and the
#: tightest of them loses the spaces on both sides of the pair:
#:
#: - `clean` is the ordinary case, `2 + 2*` or `2+2`, standing on its own word boundaries.
#: - `glued` is the Club Joker Urban, whose whole strip comes out as
#:   `25 L2 + 24 / 6 Gaz` — berths `2 + 2` with the seats `4 / 6` welded to the second 2,
#:   and the first 2 welded to the litres before it. Neither boundary survives, so `clean`
#:   never fires and that model alone reported no berths at all.
#:
#: Read on its own, `2 + 24 / 6` is as consistent with "2 + 24" as with "2 + 2". The
#: **Jules Verne brochure settles it**, carrying both forms: the same glued `2+24 / 6`
#: *and* a labelled row, `Places couchage Berths Schlafplätze 2+2 2+2 2+2`. So the glued
#: form is berths followed by seats, and `glued` requires that trailing `4 / 6` seat pair
#: before it will read a pair whose left boundary is missing.
#:
#: That trailing requirement is what keeps `glued` narrow enough to be safe. The Columbus
#: brochure's strip throws off fragments like `90 L1 + 1 2*4` and `Gaz1 + 14 2*`, which
#: also have no left boundary; neither is followed by a seat pair, so neither matches, and
#: Columbus still reads a clean 2 rather than disagreeing with itself down to nothing.
_BERTH_ICON = re.compile(
    r"\b(?P<clean>\d)\s*\+\s*\d\b"
    r"|(?<!\d)(?P<glued>\d)\s*\+\s*\d(?=\d\s*/\s*\d)"
)


def parse_brochure_berths(text: str) -> int | None:
    """The **base** berth count from the brochure's icon strip, or `None`.

    Every Westfalia brochure prints `2 + 2` against a bed icon and footnotes the second
    figure as an optional pop-up roof — `*optional pop-up roof bed` on the Columbus and
    James Cook, `*optional pop-up roof` on the Sven Hedin, `*optional (Premium version)`
    on the Club Joker Urban. Columbus's price list prices that roof at £10,682. So the
    **first** figure is the vehicle as sold and the second needs an option, which is the
    berth rule in `docs/adapters/README.md`.

    **Every pair in the document must agree**, and `None` is returned otherwise. A
    brochure covers several layouts, each with its own strip, and a range whose layouts
    differ cannot be served by one figure — better to propose nothing than to put the
    540 D's berths on the 640 E. It also makes a stray digit pair harmless.

    This is read rather than withheld because the figure *is* published and a reviewer
    should see it confirmed. Not reading it left "could not be validated" against a field
    printed plainly in the brochure — which is what prompted the requester to ask, twice.
    """
    bases = {
        int(match["clean"] or match["glued"]) for match in _BERTH_ICON.finditer(text)
    }
    return bases.pop() if len(bases) == 1 else None


def find_brochure_url(page_html: str) -> str | None:
    """The brochure linked from a range page, or `None`."""
    match = _BROCHURE_HREF.search(page_html)
    if match is None:
        return None
    href = match.group(1)
    return href if href.startswith("http") else f"{BASE_URL}{href}"


@dataclass(frozen=True)
class WestfaliaProduct:
    """One Columbus layout."""

    manufacturer_range: str
    model: str
    base_vehicle: str
    mh_length_mm: int | None = None
    mh_width_mm: int | None = None
    mh_height_mm: int | None = None
    mtplm_kilograms: int | None = None
    rrp_pounds: int | None = None
    mro_kilograms: int | None = None
    travel_seats: int | None = None
    berths: int | None = None
    #: What the brochure said the permissible total weight was, kept so the two documents
    #: can be compared — see `_reconciles`.
    brochure_mtplm_kilograms: int | None = None

    @property
    def label(self) -> str:
        return f"{self.manufacturer_range} {self.model}"

    @property
    def payload_kilograms(self) -> int | None:
        """`MTPLM - MRO`. Derivable only because the brochure supplies the mass."""
        if self.mtplm_kilograms is None or self.mro_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mro_kilograms


def read_price_list(
    text: str,
    entry: Range,
    masses: dict[str, tuple[int, int]] | None = None,
    brochure_text: str = "",
    page_html: str = "",
) -> list[WestfaliaProduct]:
    """Every layout of one range, read against its configured columns."""
    width = len(entry.models)
    if not entry.figures:
        # No usable price list. The range page's own specification table is preferred where
        # it has a figure; the brochure fills what it does not. Anything neither names is
        # left `None`, so nothing is proposed for it and FMLV's value stands.
        take = set(entry.from_page)
        page_of = {
            "length": "Length", "width": "Width", "height": "Height",
            "seats": "Seats", "berths": "Berths", "mro": "Mass in Running Order",
            "mtplm": "Permissible Weight",
        }
        figures = {
            field: parse_specification_table(page_html, page_of[field])
            for field in take
            if field in page_of
        }
        # The brochure fills what the page does not carry — never the other way round. The
        # page is preferred because its dimensions match FMLV exactly where the brochure's
        # do not always, but a field the page simply omits is better taken than left blank.
        wanted = set(entry.from_brochure)
        if wanted:
            brochure_mro, brochure_mtplm = parse_brochure_single_mass(brochure_text)
            if "mro" in wanted and figures.get("mro") is None:
                figures["mro"] = brochure_mro
            if "mtplm" in wanted and figures.get("mtplm") is None:
                figures["mtplm"] = brochure_mtplm
        return [
            WestfaliaProduct(
                manufacturer_range=entry.fmlv_range,
                model=model,
                base_vehicle=entry.base_vehicle,
                mh_length_mm=figures.get("length"),
                mh_width_mm=figures.get("width"),
                mh_height_mm=figures.get("height"),
                travel_seats=figures.get("seats"),
                berths=parse_brochure_berths(brochure_text),
                mro_kilograms=figures.get("mro"),
                mtplm_kilograms=figures.get("mtplm"),
                rrp_pounds=parse_cheapest_price(text) if entry.price_from_list else None,
            )
            for model in entry.models
        ]
    dimensions = parse_dimensions(text, width)
    weights = parse_weights(text, width)
    prices = parse_base_prices(text, width)
    if not dimensions:
        return []
    return [
        WestfaliaProduct(
            manufacturer_range=entry.fmlv_range,
            model=model,
            base_vehicle=entry.base_vehicle,
            mh_length_mm=dimensions[index][0],
            mh_width_mm=dimensions[index][1],
            mh_height_mm=dimensions[index][2],
            mtplm_kilograms=weights[index] if index < len(weights) else None,
            rrp_pounds=prices[index] if index < len(prices) else None,
            berths=parse_brochure_berths(brochure_text),
            mro_kilograms=(masses or {}).get(model.upper(), (None, None))[0],
            brochure_mtplm_kilograms=(masses or {}).get(model.upper(), (None, None))[1],
        )
        for index, model in enumerate(entry.models)
    ]


def _reconciles(product: WestfaliaProduct) -> tuple[bool, str]:
    """Whether a layout's figures are present, plausible and agreed between documents.

    **A missing field never drops a layout.** Every source here publishes a different
    subset — the Club Joker Urban's page gives dimensions and no masses, the Jules Verne's
    gives everything, Columbus's price list gives no seat count — and dropping a product
    for a field its documents do not carry retires a live vehicle. It cost the Club Joker
    Urban exactly that once: it was dropped for want of a permissible total weight its page
    has never stated, and came back in the diff as discontinued.

    What is checked is what is *present*: that each figure is plausible, that the two
    documents agree where both speak, and that the mass in running order sits below the
    permissible total weight.
    """
    if product.mh_length_mm is not None and not 4_000 <= product.mh_length_mm <= 8_000:
        return False, f"a length of {product.mh_length_mm}mm is not a panel van"

    if product.mtplm_kilograms is not None and not 2_500 <= product.mtplm_kilograms <= 5_000:
        return False, (
            f"a permissible total weight of {product.mtplm_kilograms}kg is implausible"
        )

    # The one genuinely independent check: the price list and the brochure are written
    # separately and both state the permissible total weight.
    if (
        product.brochure_mtplm_kilograms is not None
        and product.mtplm_kilograms is not None
        and product.brochure_mtplm_kilograms != product.mtplm_kilograms
    ):
        return False, (
            f"the price list gives a permissible total weight of "
            f"{product.mtplm_kilograms}kg and the brochure "
            f"{product.brochure_mtplm_kilograms}kg"
        )

    if (
        product.mro_kilograms is not None
        and product.mtplm_kilograms is not None
        and product.mro_kilograms >= product.mtplm_kilograms
    ):
        return False, (
            f"a mass in running order of {product.mro_kilograms}kg is not below the "
            f"permissible total weight of {product.mtplm_kilograms}kg"
        )

    if product.payload_kilograms is not None:
        return True, (
            f"{product.mtplm_kilograms}kg less {product.mro_kilograms}kg in running order "
            f"leaves {product.payload_kilograms}kg"
        )
    return True, "every figure its documents publish, and nothing inferred beyond them"


def build_extracted(
    product: WestfaliaProduct, source_url: str, *, basis: str
) -> ExtractedMotorhome:
    """One layout as a `Motorhome` plus the provenance a reviewer sees beside it."""
    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.manufacturer_range,
        model=product.model,
        mh_length_mm=product.mh_length_mm,
        mh_width_mm=product.mh_width_mm,
        mh_height_mm=product.mh_height_mm,
        mtplm_kilograms=product.mtplm_kilograms,
        mro_kilograms=product.mro_kilograms,
        berths=product.berths,
        mh_passenger_seats_inc_driver=product.travel_seats,
        mh_payload_kilograms=product.payload_kilograms,
        rrp_pounds=product.rrp_pounds,
        base_vehicle_manufacturer=fmlv_base_vehicle(product.base_vehicle),
    )

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=source_url, snippet=f"{product.label} — {snippet}"
        )

    record(
        "manufacturer_range",
        f'range "{product.manufacturer_range}" — accept with the model, they are one name',
    )
    record(
        "model",
        f'model "{product.model}", the price list\'s own column heading — accept with the '
        f"range, they are one name",
    )
    if product.mh_length_mm is not None:
        record(
            "mh_length_mm",
            f"L/W/H {product.mh_length_mm / 1000:.3f}/{(product.mh_width_mm or 0) / 1000:.3f}/"
            f"{(product.mh_height_mm or 0) / 1000:.3f} — one row labelled only 'L/W/H', in "
            f"metres with a dot as the thousands separator",
        )
    if product.mh_width_mm is not None:
        record("mh_width_mm", f"{product.mh_width_mm}mm, the W of the L/W/H row")
    if product.mh_height_mm is not None:
        record("mh_height_mm", f"{product.mh_height_mm}mm, the H of the L/W/H row")
    if product.mtplm_kilograms is not None:
        record(
            "mtplm_kilograms",
            f"Permissible total weight: {product.mtplm_kilograms}kg, on the Light-Chassis. "
            f"A Maxi Chassis is offered as an upgrade and is not the base vehicle",
        )
    if product.berths is not None:
        record(
            "berths",
            f"Berths: {product.berths}, from the range page's own specification table. "
            f"These campervans have an elevating roof with a bed in it as standard, and "
            f"the rule is that a standard roof bed counts — so the roof's two berths are "
            f"part of the figure",
        )
    if product.travel_seats is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"Seats: {product.travel_seats}, from the range page's own specification table",
        )
    if product.mro_kilograms is not None:
        record(
            "mro_kilograms",
            f"Mass in running order: {product.mro_kilograms}kg, from the brochure's "
            f"'Mass in running order / Permissible total weight' panel, which keys each "
            f"figure by the layout's own name. The price list does not state it anywhere",
        )
    if product.payload_kilograms is not None:
        record(
            "mh_payload_kilograms",
            f"{product.payload_kilograms}kg, derived as the permissible total weight less "
            f"the mass in running order ({product.mtplm_kilograms} - "
            f"{product.mro_kilograms}). Westfalia publish no payload of their own",
        )
    if product.rrp_pounds is not None:
        record(
            "rrp_pounds",
            f"£{product.rrp_pounds:,} — the cheapest engine offered on the Light-Chassis, "
            f"which is the base vehicle. Each layout is priced on a different engine and "
            f"the dearer Maxi Chassis rows are excluded. Prices include statutory VAT, "
            f"plus handover inspection and transfer costs",
        )
    record(
        "base_vehicle_manufacturer",
        f"{product.base_vehicle} — the only chassis this range is offered on",
    )
    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


def collect(
    http: Fetcher,
    browser: object = None,  # noqa: ARG001
    snapshot_dir: Path | None = None,  # noqa: ARG001
    *,
    ranges: tuple[tuple[str, str], ...] | None = None,  # noqa: ARG001
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Fetch and parse every Westfalia layout with a usable UK price list."""
    extracted: list[ExtractedMotorhome] = []

    for entry in RANGES:
        if not entry.figures:
            page_url = f"{GUIDE_URL}{entry.slug}/"
            page = http.fetch(page_url).file_path.read_text(encoding="utf-8", errors="replace")
            brochure_url = find_brochure_url(page)
            brochure_text = (
                extract_text(http.fetch(brochure_url).file_path).text if brochure_url else ""
            )
            price_text = ""
            if entry.price_from_list:
                price_url = find_price_list_url(page)
                if price_url is None:
                    on_progress(
                        f"{entry.fmlv_range}: no price list linked, so no price is proposed"
                    )
                else:
                    price_text = extract_text(http.fetch(price_url).file_path).text
            for product in read_price_list(price_text, entry, None, brochure_text, page):
                reconciles, reason = _reconciles(product)
                if not reconciles:
                    on_progress(f"dropping {product.label} — {reason}")
                    continue
                extracted.append(
                    build_extracted(product, brochure_url or GUIDE_URL, basis=reason)
                )
            on_progress(
                f"{entry.fmlv_range}: no usable price list, so it is read from its own "
                f"page's specification table for "
                f"{', '.join(entry.from_page) or 'nothing'}. "
                f"{UNREAD_MASSES.get(entry.fmlv_range, '')}"
            )
            continue

        page_url = f"{GUIDE_URL}{entry.slug}/"
        on_progress(f"fetching the {entry.fmlv_range} page: {page_url}")
        page = http.fetch(page_url).file_path.read_text(encoding="utf-8", errors="replace")

        url = find_price_list_url(page)
        if url is None:
            on_progress(
                f"no price list linked from {page_url} — {entry.fmlv_range} cannot be "
                f"collected this run and FMLV's figures stand"
            )
            continue

        on_progress(f"reading {url}")
        document = extract_text(http.fetch(url).file_path)
        if document.is_empty():
            on_progress(f"{url} holds no extractable text — skipping {entry.fmlv_range}")
            continue

        masses: dict[str, tuple[int, int]] = {}
        brochure_text = ""
        brochure_url = find_brochure_url(page)
        if brochure_url is None:
            on_progress(
                f"no brochure linked from {page_url} — no mass in running order can be "
                f"read, so FMLV's own figures stand"
            )
        else:
            brochure = extract_text(http.fetch(brochure_url).file_path)
            brochure_text = brochure.text
            masses = parse_brochure_masses(brochure_text)
            on_progress(
                f"read {len(masses)} mass(es) in running order from {brochure_url}"
                if masses
                else f"no per-layout masses read from {brochure_url} — the panel's shape may have "
                    f"changed; FMLV's figures stand"
            )

        # The brochure is already in hand for the masses; it carries the berth icon
        # too, and Columbus's four layouts have no berth row anywhere else.
        products = read_price_list(document.text, entry, masses, brochure_text)
        if not products:
            on_progress(
                f"no L/W/H row with {len(entry.models)} columns in {url} — the table's "
                f"shape has changed, so nothing is collected rather than guessed at"
            )
            continue

        for product in products:
            reconciles, reason = _reconciles(product)
            if not reconciles:
                on_progress(f"dropping {product.label} — {reason}")
                continue
            if product.rrp_pounds is None:
                on_progress(
                    f"{product.label}: no price above £{MINIMUM_VEHICLE_PRICE:,} in its "
                    f"column, so none is proposed and FMLV's own figure stands"
                )
            extracted.append(build_extracted(product, url, basis=reason))
            on_progress(
                f"read {product.label}: {product.mh_length_mm}mm, "
                f"{product.mtplm_kilograms}kg, £{product.rrp_pounds or 0:,}"
            )

    # Said every run: these are real Westfalia ranges FMLV either holds or could hold, and
    # their absence here is a property of the documents rather than of the range.
    on_progress(
        "NOT COLLECTED, and why: Jules Verne has no price list; Sven Hedin's is a "
        "colours-and-equipment sheet with no figures; Club Joker Urban's gives a price and "
        "nothing else; James Cook's has 600D CLASSIC and 600D PREMIUM variants that FMLV "
        "holds as one row and which need a product decision first. Amundsen, Club Joker, "
        "Club Joker City, Kelsey, Kepler and Kipling have no price list either. FMLV's "
        "figures for all of them stand untouched."
    )
    on_progress(
        "THE MASS IN RUNNING ORDER COMES FROM THE BROCHURE, not the price list, which "
        "defines the term on its last page without ever stating a figure. The brochure "
        "keys each mass by the layout's own name rather than by column position, so it is "
        "the one figure here that cannot pick up a neighbour's value."
    )
    if len(extracted) != EXPECTED_LAYOUTS:
        on_progress(
            f"expected {EXPECTED_LAYOUTS} layouts and collected {len(extracted)} — check "
            f"whether the Columbus range has really changed"
        )
    on_progress(
        "NOT READ, and so left alone: the Columbus and Club Joker Urban seat counts, and "
        "a price for the Jules Verne and the Sven Hedin. Neither of those two has a price "
        "list carrying one — Sven Hedin's two 'price lists' are colour and equipment "
        "sheets. The seat counts are printed in the brochures' icon strips but extract "
        "garbled: Columbus's comes out as '90 L1 + 1 2*4 100 L' on one page and "
        "'90 L Gaz1 + 14 2*' on another, with the figures in a different order each time, "
        "and Club Joker Urban's gives '4 / 6' without saying which applies. Reading a "
        "number out of either would be guesswork. FMLV's own figures stand for every one."
    )
    on_progress(BERTHS_FROM_PAGE)
    on_progress(f"collected {len(extracted)} Westfalia layout(s)")
    return extracted
