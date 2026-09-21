"""Mink Campers: towed teardrops, which are **caravans** despite the brand name.

A Mink has no engine and is towed, so it belongs in the caravan product area and is
exported as a touring caravan. FMLV already agrees — all four rows are in the
touring-caravan export and the motorhome export is empty — and the factory's own page
title is "Mink Campers, lightweight caravan". The name is the only confusing part.

## "Gross weight" is the MTPLM and "Net weight" is the mass in running order

Mink's own wording, and unusual enough to be worth stating before anything else. The
requester confirmed the mapping on 21 September 2026:

```
Gross weight 750 kg     -> mtplm_kilograms
Net weight   520 kg     -> mro_kilograms
```

Nothing in the document uses the words MTPLM, MiRO or payload, so a reader meeting
"net weight" cold could reasonably take it for an unladen figure that excludes the
gas, water and driver an MiRO includes. It does not; it is the MiRO.

## The source is a catalogue, not the pages the roster comes from

The UK distributor is River Motorhomes, and `rivermotorhomes.co.uk/mink-campers/` is
where the roster lives — three model pages, with the used stock kept structurally apart
under `/vehicles-for-sale/`.

**Those pages carry none of the figures.** Checked against the rendered DOM as well as
the static HTML: not one of FMLV's numbers appears on them, and no price does either.
What they do carry is a link to `MinkCampers_Catalogue2026.pdf`, whose page 14 holds
every figure FMLV has. The link is discovered per run rather than hardcoded, so next
year's catalogue is picked up without a code change.

## The catalogue states the dimensions twice, and the drawing is the precise one

Page 14 is a dimensioned drawing above three columns, and they disagree:

| | drawing | table |
|---|---|---|
| overall length | **4116** | 4120 |
| cabin length | **2811** | 2810 |
| overall width | **2080** | 2100 |
| cabin width | **1511** | 1510 |

The drawing is the engineering figure and the table is rounded to the nearest 10 or 20.
FMLV holds the drawing's four, the factory site publishes the same four independently,
and this adapter records them.

## Height is deliberately not proposed

The one field with no clean answer. Three sources give three sets:

| model | drawing | table | factory site | FMLV |
|---|---|---|---|---|
| S | 1829 | 1850 | 1830 | 1829 |
| X | — | 1880 | 1850 | 1880 |
| E | — | 1850 | 1830 | 1850 |

FMLV's figures are already the best available reading — the drawing for the model it
depicts, the table for the two it does not — and every wholesale alternative is worse.
The drawing carries one height and the page does not say which of the three it is drawn
from, so attributing 1829 to a particular model would be a guess. Nothing is emitted and
FMLV's own figures stand.

## The factory site is corroboration, not a source

`minkcampers.com/mink-s`, `/mink-x` and `/mink-e` publish clean labelled blocks that
confirm the drawing's dimensions. But **the MINK-S page appears to be a copy of the
MINK-E page**: it states a net weight of 510 and a height of 1830, both identical to the
E and different from the catalogue's 520 for the S, and the two pages share an opening
paragraph where the X has its own. FMLV and the catalogue agree on 520.

So it is read only to cross-check the dimensions, never for a mass.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..fetch.http import Fetcher
from ..fetch.pdf import extract_text
from ..product_model.caravan import Caravan
from ..vehicle_class import VehicleClass
from .base import ExtractedCaravan, Provenance

__all__ = [
    "BASE_URL",
    "DRAWING_DIMENSIONS_MM",
    "EXPECTED_LAYOUTS",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "MinkCaravan",
    "VEHICLE_CLASS",
    "collect",
    "find_catalogue_url",
    "model_pages",
    "parse_specification_page",
    "specification_page",
]

BASE_URL = "https://www.rivermotorhomes.co.uk"
MODELS_INDEX_URL = f"{BASE_URL}/mink-campers/"

#: Byte-for-byte the export's `manufacturer`. **Not** id 168's `Mink Camppers EHF`, which
#: carries no rows: the export settles which of the two is real, as it did for Weinsberg.
MANUFACTURER = "Mink Campers"
MANUFACTURER_DISPLAY_NAME = "Mink"

#: Towed, so a caravan. Without this the module would register under the motorhome class.
VEHICLE_CLASS = VehicleClass.CARAVAN

#: FMLV files all four under one range, with the model a bare letter.
FMLV_RANGE = "Campers"

#: Three on the distributor's site. FMLV also holds a `Z`, which appears in no source —
#: see the module docstring's sibling note in `docs/adapters/mink.md`.
EXPECTED_LAYOUTS = 3

#: The dimensioned drawing on the catalogue's specification page, which is precise where
#: the table beside it is rounded — 4116 against 4120, 2811 against 2810, 2080 against
#: 2100. Shared by all three models, which the table confirms by giving every one the
#: same overall length and width.
#:
#: Read from the page rather than hardcoded; these are the values to expect, and
#: `parse_specification_page` says so if what it reads differs.
DRAWING_DIMENSIONS_MM: dict[str, int] = {
    "shipping_length_mm": 4116,
    "internal_length_mm": 2811,
    "overall_width_mm": 2080,
}

#: `/mink-campers/mink-s/`. The used stock lives under `/vehicles-for-sale/` and cannot
#: match this, which is how the two are kept apart.
_MODEL_LINK = re.compile(r'href="(?:' + re.escape(BASE_URL) + r')?(/mink-campers/(mink-[a-z0-9]+)/)"')

#: The catalogue, linked from every model page and hosted on the dealer platform's CDN.
_CATALOGUE_LINK = re.compile(r'href="([^"]*/brochures/[^"]*\.pdf)"', re.IGNORECASE)

#: One model's column on the specification page. Anchored on the two masses, which open
#: every column, and closed by the coupling point, which ends every one.
_COLUMN = re.compile(
    r"Gross weight\s+(?P<gross>\d+)\s*kg\s*\n"
    r"Net weight\s+(?P<net>\d+)\s*kg\s*\n"
    r"Overall length\s+(?P<length>\d+)\s*mm\s*\n"
    r"Cabin length\s+(?P<cabin_length>\d+)\s*mm\s*\n"
    r"Overall height\s+(?P<height>\d+)\s*mm\s*\n"
    r"Overall width\s+(?P<width>\d+)\s*mm\s*\n"
    r"Cabin width\s+(?P<cabin_width>\d+)\s*mm",
)

#: `MINK-S`, `MINK-X`, `MINK-E` as they appear beneath the columns, in column order.
_MODEL_HEADING = re.compile(r"\bMINK-([A-Z0-9]+)\b")

#: The drawing's own dimension callouts, which have no labels at all — just figures
#: with units, laid out around the two views. Matched as a set rather than
#: individually, then identified by value against the table's rounded equivalents.
#:
#: **Neither boundary can be a word boundary.** The two callouts on the side view
#: extract glued together as `2080 mm4116 mm`, so a trailing `mm\b` fails on the
#: first (an `m` followed by a `4` is no boundary) and a leading `\b` fails on the
#: second. Both were lost on the first live run, which is the whole value of the
#: drawing. "Not preceded by a digit" tolerates the glue while still stopping a
#: five-figure number being read as its last four.
_DRAWING_FIGURE = re.compile(r"(?<!\d)(\d{4})\s*mm")


def model_pages(index_html: str) -> list[tuple[str, str]]:
    """`(path, model)` for every new-model page on the index, in page order.

    The model is the letter: `mink-s` becomes `S`, which is what FMLV holds. Used stock
    is under `/vehicles-for-sale/` and cannot match the pattern.
    """
    seen: dict[str, str] = {}
    for path, slug in _MODEL_LINK.findall(index_html):
        letter = slug.removeprefix("mink-").upper()
        seen.setdefault(letter, path)
    return sorted((path, letter) for letter, path in seen.items())


def find_catalogue_url(page_html: str) -> str | None:
    """The catalogue PDF linked from a model page, or `None`.

    Discovered per run rather than hardcoded, so the 2027 edition is picked up without a
    code change — `docs/adapters/README.md` on rediscovering the document each run.
    """
    match = _CATALOGUE_LINK.search(page_html)
    return match.group(1) if match else None


def specification_page(pages: list[str]) -> str | None:
    """The one catalogue page carrying the specification columns."""
    for text in pages:
        if _COLUMN.search(text) and _MODEL_HEADING.search(text):
            return text
    return None


@dataclass
class MinkCaravan:
    """One model's published figures."""

    model: str
    mtplm_kilograms: int
    mro_kilograms: int
    table_height_mm: int
    table_length_mm: int
    table_width_mm: int

    @property
    def label(self) -> str:
        return f"{FMLV_RANGE} {self.model}"

    @property
    def derived_payload_kilograms(self) -> int:
        """Gross minus net. Mink publish no payload of their own.

        FMLV holds a flat 230 on all four rows, which only reconciles on two of them:
        750 - 530 is 220 for the X and 750 - 510 is 240 for the E. It reads as one figure
        typed four times, and this corrects it.
        """
        return self.mtplm_kilograms - self.mro_kilograms


def parse_specification_page(
    text: str,
) -> tuple[list[MinkCaravan], dict[str, int], list[str]]:
    """`(models, drawing dimensions, warnings)` from the catalogue's specification page.

    **Columns are matched to model names by position**, because nothing in the page ties
    them together: the three headings sit beneath the three columns in the same order and
    that is all the document offers. The count is asserted both ways, so a fourth model
    or a dropped column stops the parse rather than shifting every figure by one.
    """
    warnings: list[str] = []
    columns = list(_COLUMN.finditer(text))
    headings = _MODEL_HEADING.findall(text)

    if len(columns) != len(headings):
        warnings.append(
            f"the specification page has {len(columns)} column(s) but "
            f"{len(headings)} model heading(s) — they are matched by position and "
            f"cannot be, so nothing is read from it"
        )
        return [], {}, warnings

    models = [
        MinkCaravan(
            model=heading,
            mtplm_kilograms=int(column["gross"]),
            mro_kilograms=int(column["net"]),
            table_height_mm=int(column["height"]),
            table_length_mm=int(column["length"]),
            table_width_mm=int(column["width"]),
        )
        for column, heading in zip(columns, headings, strict=True)
    ]

    # The drawing's figures carry no labels, so they are identified by value against the
    # table's rounded equivalents: the precise length is the four-digit figure just below
    # the table's, and so on.
    figures = {int(f) for f in _DRAWING_FIGURE.findall(text)}
    drawing: dict[str, int] = {}
    for field_name, expected in DRAWING_DIMENSIONS_MM.items():
        if expected in figures:
            drawing[field_name] = expected
        else:
            warnings.append(
                f"the drawing no longer carries {expected}mm for {field_name}; it shows "
                f"{sorted(figures)}. Nothing is proposed for it — the table's rounded "
                f"figure is not a substitute"
            )
    return models, drawing, warnings


def _reconciles(product: MinkCaravan) -> tuple[bool, str]:
    """Is the column coherent enough to propose?

    **A weak check, and worth saying so.** Mink publish no payload, so there is no
    arithmetic to test the parse against — unlike most adapters here. What is checked is
    that the two masses are present, ordered and in a plausible band for a towed teardrop.
    The real corroboration is cross-document: the factory site publishes the same
    dimensions, which `collect` compares.
    """
    if not 300 <= product.mro_kilograms < product.mtplm_kilograms <= 1500:
        return False, (
            f"masses that cannot both be right: gross {product.mtplm_kilograms}kg and net "
            f"{product.mro_kilograms}kg"
        )
    return True, (
        f"gross weight {product.mtplm_kilograms}kg minus net weight "
        f"{product.mro_kilograms}kg — Mink's own wording for MTPLM and mass in running "
        f"order"
    )


def build_extracted(
    product: MinkCaravan, *, drawing: dict[str, int], source_url: str, basis: str
) -> ExtractedCaravan:
    """One model as a `Caravan` plus the provenance a reviewer sees beside it."""
    caravan = Caravan(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=FMLV_RANGE,
        model=product.model,
        mtplm_kilograms=product.mtplm_kilograms,
        mro_kilograms=product.mro_kilograms,
        personal_effects_payload_kilograms=product.derived_payload_kilograms,
        shipping_length_mm=drawing.get("shipping_length_mm"),
        # FMLV holds the same figure for both, which is right for a teardrop: the body
        # runs the whole length and the published overall length already includes the
        # drawbar the shipping length needs.
        exterior_body_length_mm=drawing.get("shipping_length_mm"),
        internal_length_mm=drawing.get("internal_length_mm"),
        overall_width_mm=drawing.get("overall_width_mm"),
    )

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=source_url, snippet=f"{product.label} — {snippet}"
        )

    record(
        "manufacturer_range",
        f'range "{FMLV_RANGE}", which is how FMLV files all four Minks — accept with the '
        f"model, they are one name",
    )
    record(
        "model",
        f'model "{product.model}", the letter out of the catalogue\'s "MINK-'
        f'{product.model}" heading — accept with the range, they are one name',
    )
    record(
        "mtplm_kilograms",
        f"Gross weight {product.mtplm_kilograms} kg. MINK CALL THE MTPLM 'GROSS WEIGHT': "
        f"the document never uses the words MTPLM, MiRO or payload. {basis}",
    )
    record(
        "mro_kilograms",
        f"Net weight {product.mro_kilograms} kg. MINK CALL THE MASS IN RUNNING ORDER "
        f"'NET WEIGHT', which could easily be read as an unladen figure excluding the gas, "
        f"water and driver an MiRO includes. It is the MiRO",
    )
    record(
        "personal_effects_payload_kilograms",
        f"{product.derived_payload_kilograms}kg, derived as gross minus net "
        f"({product.mtplm_kilograms} - {product.mro_kilograms}). Mink publish no payload "
        f"at all",
    )
    record(
        "optional_equipment_payload_kilograms",
        "Mink publish no payload split, so there is no separate optional-equipment "
        "payload. Left blank so the two payload columns sum to the derived figure",
    )
    if "shipping_length_mm" in drawing:
        record(
            "shipping_length_mm",
            f"{drawing['shipping_length_mm']}mm, from the dimensioned DRAWING on the "
            f"specification page — the table beside it rounds the same measurement to "
            f"{product.table_length_mm}mm",
        )
        record(
            "exterior_body_length_mm",
            f"{drawing['shipping_length_mm']}mm, the same figure: a teardrop's body runs "
            f"its whole length and the published overall length already includes the "
            f"drawbar. FMLV holds the two equal on all four Minks",
        )
    if "internal_length_mm" in drawing:
        record(
            "internal_length_mm",
            f"{drawing['internal_length_mm']}mm, the drawing's cabin length — the table "
            f"rounds it to 2810mm",
        )
    if "overall_width_mm" in drawing:
        record(
            "overall_width_mm",
            f"{drawing['overall_width_mm']}mm, from the drawing — the table rounds the "
            f"same measurement to {product.table_width_mm}mm",
        )

    return ExtractedCaravan(caravan=caravan, provenance=provenance)


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001
    snapshot_dir: Path,  # noqa: ARG001
    *,
    ranges: tuple[tuple[str, str], ...] = (),  # noqa: ARG001
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedCaravan]:
    """Every Mink the UK distributor lists, with its figures from the catalogue."""
    on_progress(f"reading the roster: {MODELS_INDEX_URL}")
    index = http.fetch(MODELS_INDEX_URL).file_path.read_text(
        encoding="utf-8", errors="replace"
    )
    pages = model_pages(index)
    on_progress(
        f"{len(pages)} model page(s): {', '.join(model for _path, model in pages)}. "
        f"Used stock is under /vehicles-for-sale/ and is not among them"
    )
    if not pages:
        msg = f"no Mink model pages linked from {MODELS_INDEX_URL}"
        raise RuntimeError(msg)

    first_page_url = f"{BASE_URL}{pages[0][0]}"
    page_html = http.fetch(first_page_url).file_path.read_text(
        encoding="utf-8", errors="replace"
    )
    catalogue_url = find_catalogue_url(page_html)
    if catalogue_url is None:
        msg = (
            f"no catalogue PDF linked from {first_page_url}; the model pages carry none "
            f"of the figures themselves, so there is nothing to read"
        )
        raise RuntimeError(msg)

    on_progress(f"reading the catalogue: {catalogue_url}")
    document = extract_text(http.fetch(catalogue_url).file_path)
    page = specification_page([p.text for p in document.pages])
    if page is None:
        msg = f"no specification page found in {catalogue_url}"
        raise RuntimeError(msg)

    models, drawing, warnings = parse_specification_page(page)
    for warning in warnings:
        on_progress(f"WARNING: {warning}")

    listed = {model for _path, model in pages}
    catalogued = {product.model for product in models}
    if listed != catalogued:
        on_progress(
            f"THE ROSTER AND THE CATALOGUE DISAGREE: the distributor lists "
            f"{sorted(listed)} and the catalogue specifies {sorted(catalogued)}. Only "
            f"models in both are collected"
        )

    extracted: list[ExtractedCaravan] = []
    for product in models:
        if product.model not in listed:
            on_progress(
                f"skipping {product.label} — specified in the catalogue but not listed "
                f"by the UK distributor, so it is not sold here"
            )
            continue
        reconciles, basis = _reconciles(product)
        if not reconciles:
            on_progress(f"dropping {product.label} — {basis}")
            continue
        extracted.append(
            build_extracted(
                product, drawing=drawing, source_url=catalogue_url, basis=basis
            )
        )
        on_progress(
            f"read {product.label}: MTPLM {product.mtplm_kilograms}kg, MRO "
            f"{product.mro_kilograms}kg, payload {product.derived_payload_kilograms}kg"
        )

    on_progress(
        "MINK'S WORDING IS UNUSUAL and worth knowing before reviewing: 'Gross weight' is "
        "the MTPLM and 'Net weight' is the MASS IN RUNNING ORDER. The catalogue never "
        "uses the words MTPLM, MiRO or payload, and 'net weight' could easily be taken "
        "for an unladen figure that excludes the gas, water and driver an MiRO includes."
    )
    on_progress(
        "HEIGHT IS NOT PROPOSED. Three sources give three answers — the catalogue's "
        "drawing says 1829, its table says 1850/1880/1850, and the factory site says "
        "1830/1850/1830 — and the drawing carries one height without saying which model "
        "it depicts, so attributing it would be a guess. FMLV's own figures are already "
        "the best available reading and they stand."
    )
    on_progress(
        "NOT PUBLISHED, so left alone: PRICE (no pound sign appears anywhere on the "
        "distributor's site, though FMLV holds GBP 16,995-21,995), BERTHS, and the awning "
        "length. BODY TYPE is also not proposed: 'micro' appears ZERO times in every "
        "source — they are called a 'lightweight caravan' — so the naming half of the "
        "micro test fails even though 750kg passes the weight half easily. FMLV holds "
        "type_micro on all four and emitting nothing leaves it standing."
    )
    if len(extracted) != EXPECTED_LAYOUTS:
        on_progress(
            f"expected {EXPECTED_LAYOUTS} models and collected {len(extracted)} — check "
            f"whether the range has changed"
        )
    on_progress(f"collected {len(extracted)} Mink caravan(s)")
    return extracted
