"""AURA touring caravans, the second product area on the same manufacturer row.

Sits beside `aura.py` the way `adria_caravan.py` sits beside `adria.py`. The page shape is
identical — a run of `Label value` cells inside separate elements with no table — so
`visible_text` and `lower_of_a_range` are imported unchanged.

**Three things do not come across, and each is the reason this is a separate module.**

* **The units are metres, not centimetres.** `Overall Length 5.68m` here against the
  motorhome pages' `Length 676cm`.
* **There are two lengths**, and they are different FMLV fields: `Overall Length` is the
  shipping length including the hitch and `Body Length` is the exterior body. One DeLuxe
  layout spells the second **`Boby Length`**, so both spellings are matched — a parser
  keying on the correct one loses that layout's body length and says nothing about it.
* **There is no payload, and so no self-check.** The motorhome pages publish MTPLM, MIRO
  *and* payload; these publish only the first two. That is stated plainly rather than
  papered over: a misread mass here cannot be caught by arithmetic, only by a reviewer.

**The masses here are NOT proposed.** The requester ruled on 7 October 2026 that Mike
Lake's spreadsheets are the authority for AURA, because they are defensible — and FMLV
matches them field for field. This site disagrees with them on every caravan layout and is
demonstrably behind: its footer reads 2026 where Hobby's own site is on 2027. So the
caravans are collected for their **identity and their roster** — which is the real value,
since the site is where a new or withdrawn layout shows up first — and the figures are
narrated for comparison without being proposed over good data.

**That makes this a deliberately partial adapter**, in the same shape as the Edition half
of `bespoke.py`: emitting the identity claims the FMLV row, so a run cannot report a
caravan AURA still sell as missing from the site.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from src.adapters.aura import (
    AURA_HEADING,
    BASE_URL,
    columns_of,
    MANUFACTURER,
    MANUFACTURER_DISPLAY_NAME,
    lower_of_a_range,
    visible_text,
)
from src.adapters.base import ExtractedCaravan, Provenance
from src.fetch.browser import BrowserFetcher
from src.fetch.http import Fetcher
from src.product_model.caravan import Caravan
from src.product_model.enums import CaravanBodyType
from src.vehicle_class import VehicleClass

__all__ = [
    "DEFAULT_RANGES",
    "EXPECTED_LAYOUTS",
    "PAGES",
    "VEHICLE_CLASS",
    "AuraCaravanLayout",
    "CaravanSpecification",
    "FMLV_MODEL_NAMES",
    "collect",
    "parse_caravan_layouts",
]

#: What makes this the caravan adapter rather than a second motorhome one.
VEHICLE_CLASS = VehicleClass.CARAVAN


@dataclass(frozen=True)
class _Page:
    path: str
    fmlv_range: str


PAGES: tuple[_Page, ...] = (
    _Page("aura-caravans-deluxe-layouts.php", "DeLuxe"),
    _Page("aura-caravans-prestige-layouts.php", "Prestige"),
    _Page("aura-caravans-beachy-layouts.php", "Beachy"),
)

#: Eleven on the site against FMLV's eight. The three FMLV does not hold are a Prestige
#: `560 FC` — which Hobby's own site confirms is real — and two further Beachys.
EXPECTED_LAYOUTS = 11

DEFAULT_RANGES: tuple[tuple[str, str], ...] = tuple(
    (page.path, page.fmlv_range) for page in PAGES
)


@dataclass(frozen=True)
class CaravanSpecification:
    """One layout block. **Narrated, never proposed** — see the module docstring."""

    berths: int | None = None
    shipping_length_mm: int | None = None
    exterior_body_length_mm: int | None = None
    overall_width_mm: int | None = None
    height_mm: int | None = None
    mtplm_kilograms: int | None = None
    mro_kilograms: int | None = None


def _metres(value: str) -> int | None:
    match = re.match(r"\s*([\d.]+)\s*m\b", value)
    return round(float(match.group(1)) * 1000) if match else None


def _kilograms(value: str) -> int | None:
    """`1000kg (option to increase 1200kg)` is a thousand. The settled base-vehicle rule
    takes the standard chassis, never the upgrade."""
    match = re.match(r"\s*([\d,]+)\s*kg", value)
    return int(match.group(1).replace(",", "")) if match else None


#: `Boby Length` is a real typo on one DeLuxe layout, not a defensive guess.
_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("berths", r"Berths", "range"),
    ("shipping_length_mm", r"Overall Length", "m"),
    ("exterior_body_length_mm", r"Bo(?:d|b)y Length", "m"),
    ("overall_width_mm", r"Width", "m"),
    ("height_mm", r"Height", "m"),
    ("mtplm_kilograms", r"MTPLM", "kg"),
    ("mro_kilograms", r"MIRO", "kg"),
)

#: **FMLV's spelling, where the site's differs.** The rule is to file products as FMLV
#: files them; the site shouts `400 SFE` and abbreviates `420 Plus` to `420+`, and the
#: second matters more than cosmetics — `420+` and `420` both reduce to the single token
#: `420`, so without this the two Beachys collide on one FMLV row.
FMLV_MODEL_NAMES: dict[str, str] = {
    "400 SFE": "400 SFe",
    "420+": "420 Plus",
}


@dataclass(frozen=True)
class AuraCaravanLayout:
    """One caravan layout: how the page heads it, and the figures beside it."""

    fmlv_range: str
    fmlv_model: str
    spec: CaravanSpecification

    @property
    def label(self) -> str:
        return f"{self.fmlv_range} {self.fmlv_model}"


def parse_caravan_layouts(page_html: str, fmlv_range: str) -> list[AuraCaravanLayout]:
    """Every distinct caravan layout on one page, read column by column.

    Shares `columns_of` with `aura.py`: these pages are the same two-layouts-side-by-side
    tables, so reading them as a stream pairs the second layout's name with the first
    one's figures.
    """
    found: dict[str, AuraCaravanLayout] = {}
    for heading, figures in columns_of(page_html):
        match = AURA_HEADING.search(heading)
        if match is None:
            continue
        model = re.sub(r"\s+", " ", match.group("model")).strip()
        model = FMLV_MODEL_NAMES.get(model.upper(), FMLV_MODEL_NAMES.get(model, model))
        if not model or model in found:
            continue
        values: dict[str, int] = {}
        for field, label, kind in _FIELDS:
            cell = re.search(rf"(?:^|\|)\s*{label}\s+([^|]+?)\s*(?:\||$)", figures)
            if cell:
                raw = cell.group(1)
                value = (
                    lower_of_a_range(raw)
                    if kind == "range"
                    else _metres(raw)
                    if kind == "m"
                    else _kilograms(raw)
                )
                if value is not None:
                    values[field] = value
        if not values:
            continue
        found[model] = AuraCaravanLayout(fmlv_range, model, CaravanSpecification(**values))
    return list(found.values())


def build_extracted(layout: AuraCaravanLayout, page: _Page) -> ExtractedCaravan:
    """One AURA caravan, **by identity alone**.

    Nothing is proposed. The identity claims the FMLV row so a run cannot report a caravan
    AURA still sell as missing from the site, and the figures reach the reviewer through
    `on_progress` instead — where they can be compared with the importer's spreadsheet
    without overwriting it.
    """
    return ExtractedCaravan(
        caravan=Caravan(
            manufacturer=MANUFACTURER,
            manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
            manufacturer_range=layout.fmlv_range,
            model=layout.fmlv_model,
            body_type=CaravanBodyType.RIGID,
        ),
        provenance={},
    )


def collect(
    http: Fetcher,
    browser: BrowserFetcher,  # noqa: ARG001
    snapshot_dir: Path,  # noqa: ARG001
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedCaravan]:
    """Every AURA caravan, one fetch per range page."""
    wanted = {label for _path, label in ranges}
    pages = [page for page in PAGES if page.fmlv_range in wanted]

    results: list[ExtractedCaravan] = []
    for page in pages:
        url = f"{BASE_URL}/{page.path}"
        result = http.fetch(url)
        if result.status_code != 200:
            on_progress(f"[{page.fmlv_range}] SKIPPED: {url} returned {result.status_code}")
            continue
        html = result.file_path.read_text(encoding="utf-8", errors="replace")

        layouts = parse_caravan_layouts(html, page.fmlv_range)
        if not layouts:
            on_progress(
                f"[{page.fmlv_range}] SKIPPED: no layout block found on {url} — the page "
                f"shape has changed"
            )
            continue
        for layout in layouts:
            spec = layout.spec
            results.append(build_extracted(layout, page))
            on_progress(
                f"[{page.fmlv_range}] {layout.fmlv_model} — the site says: "
                f"MTPLM {spec.mtplm_kilograms}kg, MIRO {spec.mro_kilograms}kg, "
                f"{spec.shipping_length_mm}mm over the hitch, "
                f"{spec.exterior_body_length_mm}mm body, {spec.berths} berth. "
                f"Not proposed — see below."
            )

    on_progress(
        "NOTHING IS PROPOSED FOR THE CARAVANS, DELIBERATELY. The requester ruled on "
        "7 October 2026 that the importer's own spreadsheets are the authority for AURA, "
        "because they are defensible, and FMLV matches them field for field. This site "
        "disagrees with them on every caravan layout and is demonstrably behind — its "
        "footer reads 2026 where Hobby's own site is already on 2027. The figures above "
        "are for comparison only. What the run IS for here is the roster: a layout that "
        "appears or disappears shows up on the site first."
    )
    on_progress(
        "THERE IS NO SELF-CHECK ON THE CARAVAN SIDE. These pages publish MTPLM and MIRO "
        "but no payload, so there is no arithmetic to test a parse against — unlike the "
        "motorhome pages, where MTPLM minus MIRO equals the published payload on all "
        "thirteen. That is the second reason nothing here is proposed."
    )
    if len(pages) == len(PAGES) and len(results) != EXPECTED_LAYOUTS:
        on_progress(
            f"expected {EXPECTED_LAYOUTS} layouts and collected {len(results)} — check "
            f"whether the range has changed"
        )
    on_progress(f"collected {len(results)} AURA caravan(s)")
    return results
