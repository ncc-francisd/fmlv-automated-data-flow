"""Roller Team — a WordPress roster, a brochure for the numbers, a price list for the price.

Roller Team is Trigano, which makes it a sister brand to Auto-Trail, Chausson and Adria.
It does not follow Auto-Trail's shape, and the reason is structural rather than
cosmetic: **`rollerteammotorhomes.co.uk` is not a UK build.** It is site 4 of the Italian
WordPress multisite — every upload path is `/wp-content/uploads/sites/4/…` — translated
into English with the Italian information architecture left in place. The post type is
`modello`; the taxonomies are `gamma` (range), `tipologia` (body type), `posti-letto`
(berths) and `posti-omologati` (homologated seats).

That decides the design. **Three sources, each answering a different question, none of
them overlapping on a field we record:**

| source | answers |
|---|---|
| `/wp-json/wp/v2/modello` | which models exist, their range, their body type |
| the 2027 brochure PDF | every number: berths, belts, dimensions, both masses, chassis |
| the 2027 UK price list PDF | the price, and the chassis again |

The website publishes **no price at all**, so the price list is the only price source and
the website-overrules-PDF rule never has to arbitrate anything here.

**The self-check is the external length**, published independently by all three for all
twenty models and agreeing to the centimetre. It is not a decoration. The brochure's
masses are read out of a flattened columnar PDF, which is the highest-risk parse in this
repo — one column out and you get plausible, internally consistent motorhomes carrying
each other's weights, and nothing downstream catches it. Length sits in the same column
block as `Gross vehicle weight` and `Mass in running order`, so if the length in column 2
matches what two other documents say about that model, column 2 *is* that model's column
and the masses beside it are its own. `_reconciles` enforces it and drops anything that
fails rather than proposing it.

Four traps, all of them live:

* **The slug lies.** `/tipologia/low-profile/zefiro-647/` is titled `Zefiro 747`, and the
  747 is what both PDFs list. There is no 647 anywhere except that slug. `parse_roster`
  reads the **title**; keying on the slug would invent a phantom `Zefiro 647` every run
  and report the real 747 as disappeared.
* **The taxonomies look like data and are partly wrong.** All three Kronos carry no
  `posti-letto` term at all, and Zefiro 746 and 747 are tagged `4-berths` where their own
  page tiles and the brochure both say 6. Only `gamma-` and `tipologia-` are read here.
* **The page slugs are stale too.** The 2027 brochure sits behind `/catalog-2025/`, and
  neither that page nor `/price-list/` states a model year a customer can see. Both PDF
  URLs are date-stamped upload paths, so they are rediscovered from the two pages every
  run and never hardcoded.
* **The site 403s a bare user agent.** `Fetcher`'s own `USER_AGENT` gets a 200 and
  `robots.txt` excludes nothing, so no action is needed — but a future "the site is
  blocking us" should check what was actually sent before concluding anything.

**The Kronos Compact 665 tile says `2` berths and is wrong.** Settled by the requester on
13 November 2026 from the floorplan — *"there's a fixed bed and there's also a drop-down
bed at the front, both of them are doubles, so that's four berth… I think it's just a typo
on the website."* That is a typo, not a source conflict, and the distinction decides what
this module does with it: `_KNOWN_TILE_FAULTS` names it once so it is narrated as a known
fault rather than put to a reviewer every run.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from ..fetch.http import Fetcher
from ..fetch.pdf import extract_text
from ..product_model.enums import BodyType, Heating, Refrigeration
from ..product_model.model import Motorhome
from . import gearbox, habitation
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

BASE_URL = "https://www.rollerteammotorhomes.co.uk"

#: The WordPress REST roster. `per_page=100` covers a range four times this size, and the
#: response's `x-wp-total` header is a count the site itself asserts.
ROSTER_URL = (
    f"{BASE_URL}/wp-json/wp/v2/modello?per_page=100&_fields=id,slug,link,title,class_list"
)

#: The two pages that *link* the documents. The PDFs themselves live at date-stamped
#: upload paths (`…/2026/09/…`, `…/2026/11/…`) which change with every reissue, so they
#: are discovered here rather than written down.
PRICE_LIST_PAGE_URL = f"{BASE_URL}/price-list/"
BROCHURE_PAGE_URL = f"{BASE_URL}/catalog-2025/"

MANUFACTURER = "Roller Team"
MANUFACTURER_DISPLAY_NAME = "Roller Team"

#: Twenty, asserted three ways: the price list's rows, the brochure's spec-table columns,
#: and the roster's own `x-wp-total`.
EXPECTED_PRODUCTS = 20

#: `type_campervan_high_top` above this, plain `type_campervan` below. The settled rule,
#: and the only place a dimension is allowed to decide a body type.
HIGH_TOP_ABOVE_MM = 2300

#: What the price list adds to the ex-works figure to reach on-the-road: *"number plates,
#: twelve months Vehicle Excise Duty and first registration fee (as set by H.M.
#: Government) – total £435."* Checked per model, as a second arithmetic check on the
#: price parse.
ON_THE_ROAD_CHARGES_POUNDS = 435

#: `gamma-<slug>` to the range name. An unknown slug is narrated rather than guessed at,
#: because a new range is exactly the thing a run should not pass over quietly.
RANGE_OF_GAMMA: dict[str, str] = {
    "livingstone": "Livingstone",
    "kronos-compact": "Kronos Compact",
    "zefiro": "Zefiro",
    "t-line": "T-Line",
    "pegaso": "Pegaso",
}

#: The brochure names its range in the page's first line, which is shorter than the one
#: the website and the price list use for the Kronos.
RANGE_OF_BROCHURE_HEADING: dict[str, str] = {
    "Livingstone": "Livingstone",
    "Kronos": "Kronos Compact",
    "Zefiro": "Zefiro",
    "T-Line": "T-Line",
    "Pegaso": "Pegaso",
}

#: `tipologia-<slug>` to body type. Roller Team publish their own body type as a
#: taxonomy, so nothing here is derived — except the campervan high-top split, which the
#: height decides under the settled rule.
_BODY_OF_TIPOLOGIA: dict[str, BodyType | None] = {
    "low-profile": BodyType.COACH_BUILT_LOW_PROFILE,
    "over-cab": BodyType.COACH_BUILT_OVER_CAB_BED,
    "a-class": BodyType.A_CLASS,
    "campervan": None,  # decided by height, below
}

#: `(gamma slug, range name)`. The slug is the site's own taxonomy term, which is what
#: `RANGE_OF_GAMMA` keys on; the label is what a reviewer picks with `--range`.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = tuple(
    (gamma, name) for gamma, name in RANGE_OF_GAMMA.items()
)

#: Site `(range, model)` -> what FMLV still holds. `Auto-Roller` was Roller Team's older
#: UK brand name, and FMLV files three layouts under it as a *range*.
#:
#: **Evidenced on the mass, never on the name.** Each pair's mass in running order is
#: identical to the kilogram, and the length with it:
#:
#: | site | FMLV | MRO | length |
#: |---|---|---|---|
#: | `Zefiro 707` | `Auto-Roller 707` | 2,915kg | 7,120mm |
#: | `Zefiro 746` | `Auto-Roller 746` | 2,935kg | 7,240mm |
#: | `Zefiro 747` | `Auto-Roller 747` | 2,925kg | 7,240mm |
#:
#: Without this the first run reported three new products beside three disappearance
#: notices for the rows they duplicate, which is the shape the README warns is *"almost
#: always"* a rename. A range-wide entry would be wrong here: the other four Zefiros are
#: already filed as `Zefiro`, and rewriting them all would orphan every one of them.
RENAMED_MODELS: dict[tuple[str, str], tuple[str, str]] = {
    ("Zefiro", "707"): ("Auto-Roller", "707"),
    ("Zefiro", "746"): ("Auto-Roller", "746"),
    ("Zefiro", "747"): ("Auto-Roller", "747"),
}

#: Where a model page's headline tile is known to be wrong, so that it is reported as a
#: fault rather than raised as a question. The value is what the tile says; the brochure
#: is recorded regardless. See the module docstring for the ruling.
_KNOWN_TILE_FAULTS: dict[str, tuple[str, str]] = {
    "Kronos Compact 665": (
        "berths",
        "the tile says 2 and the brochure says 4 (+1 optional). Settled 13 November 2026 "
        "from the floorplan — a fixed double plus a front drop-down double — as a typo on "
        "the website, not a disagreement between sources. 4 is recorded",
    ),
}

#: `pdfminer` splits a run after a capital T in this document's display face, so the price
#: list arrives carrying `Ford T ransit` and `T - Line 590`. Repaired before anything is
#: matched, because every model name and every chassis would otherwise miss.
_PDF_T_SPLIT = (
    ("T - Line", "T-Line"),
    ("T -Line", "T-Line"),
    ("T ransit", "Transit"),
    ("T ransverse", "Transverse"),
)

#: One price-list row: name, length, chassis, then four money columns ending in
#: on-the-road. The trailing descriptors (`Hi-Line (over cab bed)`, `A-Class (drop down
#: bed)`) are the body type restated and are stripped — `tipologia` already said it.
_PRICE_ROW = re.compile(
    r"^(?P<name>[A-Za-z][A-Za-z0-9 \-]*?)"
    r"(?:\s+(?:Hi-Line|Lo-Line|A-Class)\b[^£]*?)?"
    r"\s+(?P<length>\d\.\d{2})m\s*\([^)]*\)\s+"
    r"(?P<chassis>[A-Za-z]+ [A-Za-z]+)\s+\d+\s*bhp\s+"
    r"(?P<money>(?:£\s?[\d,]+\s*){4})$"
)

_POUNDS = re.compile(r"£\s?([\d,]+)")

#: Longest first, so `Kronos Compact 590` does not match as the range `Kronos Compact`
#: with an empty model, and nothing starting `T-Line` is read as a `Zefiro`.
_RANGE_PREFIXES: tuple[str, ...] = (
    "Kronos Compact",
    "Livingstone",
    "T-Line",
    "Pegaso",
    "Zefiro",
)

#: A berth or belted-seat cell: a base figure, optionally `2 + 1`, optionally with a
#: parenthesised extra (`4 (+1 optional)`, `4 (5 optional)`). The **base** figure is what
#: is recorded — the extras are the £290 fifth seat, which is an option.
_COUNT_CELL = re.compile(
    r"(\d+)(?:\s*\+\s*\d+)?(?:\s*\(\s*\+?\s*\d+\s*(?:optional)?\s*\))?"
)
_METRES_CELL = re.compile(r"(\d+\.\d+)\s*m\b")
_KILOGRAMS_CELL = re.compile(r"([\d,]+)\s*kg\b")

#: One heating appliance as the brochure writes it, once per column. Counted rather than
#: positioned: the row wraps onto two lines per column on every range but Livingstone.
_HEATING_CELL = re.compile(
    r"Combi\s*\d+\s*kW\s*(?:Gas|Diesel)\s*\+\s*Electric"
    r"|Webasto\s+Air\s+Top\s+Evo\s*\d+\s*Diesel",
    re.I | re.S,
)

_FRIDGE_ROW = re.compile(r"^\s*(?:Compressor|Automatic three-way)\s+refrigerator\b", re.I)
_HEATING_ROW = re.compile(r"^\s*Heating\b", re.I)

#: The rows the weights block is read from, and the only rows read positionally anywhere
#: in this module. Each must yield exactly one cell per column or it is discarded — see
#: `_cells`.
_SPEC_ROWS: dict[str, tuple[str, re.Pattern[str]]] = {
    "berths": ("Berths", _COUNT_CELL),
    "belted_seats": ("Belted seats", _COUNT_CELL),
    "length_m": ("External length", _METRES_CELL),
    "width_m": ("External width", _METRES_CELL),
    "height_m": ("External height", _METRES_CELL),
    "internal_height_m": ("Internal height", _METRES_CELL),
    "gross_vehicle_weight_kg": ("Gross vehicle weight", _KILOGRAMS_CELL),
    "mass_in_running_order_kg": ("Mass in running order", _KILOGRAMS_CELL),
}

#: A PDF link on one of the two document pages.
_PDF_HREF = re.compile(r'href="(https://[^"]+\.pdf)"', re.I)


def _repair(text: str) -> str:
    """Undo the extractor's split after a capital T, which breaks every model name."""
    for broken, whole in _PDF_T_SPLIT:
        text = text.replace(broken, whole)
    return text


def _tidy(raw: str) -> str:
    return " ".join(raw.split())


def _pounds(raw: str) -> int:
    return int(raw.replace(",", "").strip())


def _metres_to_millimetres(raw: str) -> int:
    return round(float(raw) * 1000)


def split_range_and_model(full_name: str) -> tuple[str, str] | None:
    """`"Kronos Compact 665"` -> `("Kronos Compact", "665")`.

    FMLV holds the range and the layout in separate columns, and Roller Team's own
    documents write them as one string. Returns `None` for a name that starts with no
    known range, which is how a new range reaches `on_progress` instead of being filed
    under a wrong one.
    """
    tidied = _tidy(full_name)
    for prefix in _RANGE_PREFIXES:
        if tidied.lower().startswith(prefix.lower()):
            model = tidied[len(prefix) :].strip()
            if model:
                return prefix, model
    return None


@dataclass(frozen=True)
class RosterEntry:
    """One `modello` record: what exists, what range it is in, and its body type."""

    model_name: str
    slug: str
    link: str
    manufacturer_range: str | None
    tipologia: str | None

    @property
    def key(self) -> str:
        return _tidy(self.model_name).upper()


def parse_roster(payload: str) -> tuple[list[RosterEntry], list[str]]:
    """Every model the REST roster lists, and a note for anything not understood.

    **The title is the name, never the slug.** `zefiro-647` is titled `Zefiro 747`, which
    is what both PDFs call it and what FMLV must hold.

    Only `gamma-` and `tipologia-` are read off `class_list`. The berth and seat
    taxonomies beside them are stale — all three Kronos carry no `posti-letto` term, and
    Zefiro 746 and 747 are tagged `4-berths` against their own tiles' 6 — and
    `posti-omologati`'s slugs are WordPress term ids (`43`, `44`, `45`) rather than seat
    counts.
    """
    records = json.loads(payload)
    entries: list[RosterEntry] = []
    notes: list[str] = []

    for record in records:
        title = _tidy(str(record.get("title", {}).get("rendered", "")))
        slug = str(record.get("slug", ""))
        if not title:
            notes.append(f"a roster record with slug {slug!r} has no title, so it is skipped")
            continue

        classes = [str(entry) for entry in record.get("class_list", [])]
        gamma = next((c[len("gamma-") :] for c in classes if c.startswith("gamma-")), None)
        tipologia = next(
            (
                c[len("tipologia-") :]
                for c in classes
                if c.startswith("tipologia-") and not c.startswith("tipologia-letto-")
            ),
            None,
        )

        range_name = RANGE_OF_GAMMA.get(gamma or "")
        if gamma and range_name is None:
            notes.append(
                f"{title}: an unrecognised range taxonomy {gamma!r} — a new Roller Team "
                f"range would look exactly like this"
            )
        if tipologia and tipologia not in _BODY_OF_TIPOLOGIA:
            notes.append(
                f"{title}: an unrecognised body taxonomy {tipologia!r}, so no body type "
                f"is recorded for it"
            )
        if slug and title.lower().replace(" ", "-") != slug:
            notes.append(
                f"{title}: served under the slug {slug!r}, which does not match the title. "
                f"The title is what is recorded"
            )

        entries.append(
            RosterEntry(
                model_name=title,
                slug=slug,
                link=str(record.get("link", "")),
                manufacturer_range=range_name,
                tipologia=tipologia,
            )
        )
    return entries, notes


@dataclass(frozen=True)
class PriceRow:
    """One row of the 2027 UK price list."""

    full_name: str
    length_m: float
    chassis: str
    ex_works_pounds: int
    on_the_road_pounds: int
    line: str

    @property
    def key(self) -> str:
        return _tidy(self.full_name).upper()

    @property
    def charges_reconcile(self) -> bool:
        """On-the-road is ex-works plus the £435 the list itself names."""
        return self.on_the_road_pounds - self.ex_works_pounds == ON_THE_ROAD_CHARGES_POUNDS


def parse_price_list(text: str) -> list[PriceRow]:
    """Every priced model, with its length, chassis and on-the-road price.

    **On the road is the price recorded.** It is the basis FMLV's guide price asks for,
    and the only price Roller Team publish anywhere — their website carries none at all.
    """
    rows: list[PriceRow] = []
    for raw in _repair(text).split("\n"):
        match = _PRICE_ROW.match(_tidy(raw))
        if match is None:
            continue
        money = _POUNDS.findall(match.group("money"))
        if len(money) != 4:
            continue
        rows.append(
            PriceRow(
                full_name=_tidy(match.group("name")),
                length_m=float(match.group("length")),
                chassis=_tidy(match.group("chassis")),
                ex_works_pounds=_pounds(money[2]),
                on_the_road_pounds=_pounds(money[3]),
                line=_tidy(raw),
            )
        )
    return rows


def _cells(block: str, label: str, cell: re.Pattern[str], columns: int) -> list[str] | None:
    """One spec row's values, or `None` where it does not yield exactly one per column.

    A row that yields the wrong number of cells is **discarded, not guessed at**. The
    brochure's bed-dimension rows are ragged in exactly this way — `Rear bed (cm)` gives
    one value for the Kronos's three columns — and reading them positionally is what
    produced a wrong inference about the Kronos Compact 665 during the survey.
    """
    for line in block.split("\n"):
        stripped = line.strip()
        if not stripped.startswith(label):
            continue
        found = cell.findall(stripped[len(label) :])
        return found if len(found) == columns else None
    return None


@dataclass(frozen=True)
class SpecColumn:
    """One model's column of the brochure's `Technical Specifications` table."""

    manufacturer_range: str
    model: str
    berths: int | None = None
    belted_seats: int | None = None
    length_m: float | None = None
    width_m: float | None = None
    height_m: float | None = None
    internal_height_m: float | None = None
    gross_vehicle_weight_kg: int | None = None
    mass_in_running_order_kg: int | None = None
    heating: tuple[Heating, str] | None = None
    refrigeration: tuple[Refrigeration, str] | None = None
    berths_line: str = ""

    @property
    def full_name(self) -> str:
        return f"{self.manufacturer_range} {self.model}"

    @property
    def key(self) -> str:
        return self.full_name.upper()


def _column_names(header: str, candidates: Iterable[str]) -> list[str] | None:
    """The models this table's columns describe, in the order the header puts them.

    The header is not split into columns, because it cannot be: the Kronos writes
    `Kronos Compact 590 Kronos Compact 665 Kronos Compact 670` — nine tokens for three
    columns — while the Zefiro writes `675 685 696 Sport`. Instead each candidate model's
    own distinguishing suffix is located in the header and the columns are ordered by
    where they were found, which works on both shapes and on anything between them.
    """
    positions: dict[str, int] = {}
    for model in candidates:
        found = re.search(rf"(?<![\w-]){re.escape(model)}(?![\w-])", header, re.I)
        if found is None:
            continue
        positions[model] = found.start()
    if not positions or len(set(positions.values())) != len(positions):
        return None
    return sorted(positions, key=lambda model: positions[model])


def parse_brochure(
    pages: list[str], models_by_range: dict[str, list[str]]
) -> tuple[dict[str, SpecColumn], list[str]]:
    """Every model's numbers, from the brochure's per-range specification tables.

    Each range gets two facing tables under one header: a weights-and-dimensions page and
    an equipment page. They are read together, so heating and the fridge land on the same
    columns the masses did.
    """
    weights: dict[str, SpecColumn] = {}
    equipment: dict[str, tuple[tuple[Heating, str] | None, tuple[Refrigeration, str] | None]] = {}
    notes: list[str] = []

    for page in pages:
        lines = [line for line in page.split("\n") if line.strip()]
        if not lines:
            continue
        heading = _tidy(lines[0])
        range_name = RANGE_OF_BROCHURE_HEADING.get(heading)
        header_line = next(
            (line for line in lines if line.strip().startswith("Technical Specifications")),
            None,
        )
        if range_name is None or header_line is None:
            continue

        candidates = models_by_range.get(range_name, [])
        header = header_line.strip()[len("Technical Specifications") :]
        names = _column_names(header, candidates)
        if names is None:
            notes.append(
                f"{range_name}: a specification table headed {_tidy(header)!r} could not be "
                f"matched to the price list's models for that range, so it is skipped"
            )
            continue

        if "External length" in page:
            values: dict[str, list[str] | None] = {
                attribute: _cells(page, label, cell, len(names))
                for attribute, (label, cell) in _SPEC_ROWS.items()
            }
            for dropped in sorted(name for name, got in values.items() if got is None):
                label = _SPEC_ROWS[dropped][0]
                notes.append(
                    f"{range_name}: the {label!r} row does not give one value per column, "
                    f"so {dropped} is not read for any of {', '.join(names)}"
                )
            berth_line = next(
                (line.strip() for line in lines if line.strip().startswith("Berths")), ""
            )
            for index, model in enumerate(names):
                column = SpecColumn(
                    manufacturer_range=range_name,
                    model=model,
                    berths=_maybe_int(values["berths"], index),
                    belted_seats=_maybe_int(values["belted_seats"], index),
                    length_m=_maybe_float(values["length_m"], index),
                    width_m=_maybe_float(values["width_m"], index),
                    height_m=_maybe_float(values["height_m"], index),
                    internal_height_m=_maybe_float(values["internal_height_m"], index),
                    gross_vehicle_weight_kg=_maybe_int(values["gross_vehicle_weight_kg"], index),
                    mass_in_running_order_kg=_maybe_int(
                        values["mass_in_running_order_kg"], index
                    ),
                    berths_line=_tidy(berth_line),
                )
                weights[column.key] = column
        else:
            found = _equipment(page, len(names))
            for index, model in enumerate(names):
                heat, fridge = found
                equipment[f"{range_name} {model}".upper()] = (
                    heat[index] if heat else None,
                    fridge,
                )
            if found[0] is None:
                notes.append(
                    f"{range_name}: the heating row does not give one appliance per column, "
                    f"so no heating is recorded for {', '.join(names)}"
                )

    merged = {
        key: SpecColumn(
            **{
                **column.__dict__,
                "heating": equipment.get(key, (None, None))[0],
                "refrigeration": equipment.get(key, (None, None))[1],
            }
        )
        for key, column in weights.items()
    }
    return merged, notes


def _equipment(
    page: str, columns: int
) -> tuple[list[tuple[Heating, str]] | None, tuple[Refrigeration, str] | None]:
    """Heating per column, and the fridge, from one equipment page.

    Heating is **counted rather than positioned**: every range but the Livingstone wraps
    each column's appliance onto two lines, so the row cannot be split on whitespace. One
    appliance per column, or nothing.

    The fridge is one appliance named once for the whole table — only its litres differ by
    column — so it is read from the row's own wording and applies to every model on it.
    """
    lines = page.split("\n")

    heating: list[tuple[Heating, str]] | None = None
    for index, line in enumerate(lines):
        if not _HEATING_ROW.match(line):
            continue
        block = "\n".join(lines[index : index + 2 * columns + 2])
        appliances = [_tidy(found) for found in _HEATING_CELL.findall(block)]
        if len(appliances) == columns:
            read = [habitation.heating_from([appliance]) for appliance in appliances]
            if all(entry is not None for entry in read):
                heating = [entry for entry in read if entry is not None]
        break

    fridge: tuple[Refrigeration, str] | None = None
    for line in lines:
        if not _FRIDGE_ROW.match(line):
            continue
        found = habitation.refrigeration_from([_tidy(line)])
        if found is not None:
            fridge = (found.value, found.snippet)
        break

    return heating, fridge


def _maybe_int(values: list[str] | None, index: int) -> int | None:
    if values is None:
        return None
    return int(values[index].replace(",", ""))


def _maybe_float(values: list[str] | None, index: int) -> float | None:
    return None if values is None else float(values[index])


@dataclass
class RollerTeamProduct:
    """One model, joined across the roster, the price list and the brochure."""

    roster: RosterEntry
    price: PriceRow
    spec: SpecColumn
    tile_length_m: float | None = None
    tile_berths: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        """The vehicle under the name it is recorded as, so narration and FMLV agree."""
        return f"{self.spec.manufacturer_range} {self.model}"

    @property
    def model(self) -> str:
        """The model string as FMLV holds it, which is the **title's** spelling.

        The join across the three sources is case-insensitive, so either document's
        spelling would match — but only one of them is the one to record. FMLV holds the
        Zefiro as model `SPORT`, which is how the model page titles it and not how the
        price list writes it, and `docs/adapters/README.md` is explicit that the export
        decides these strings. Taking the price list's `Sport` proposed a rename that was
        nothing but a change of case.
        """
        split = split_range_and_model(self.roster.model_name)
        return split[1] if split else self.spec.model

    @property
    def payload_kilograms(self) -> int | None:
        gross = self.spec.gross_vehicle_weight_kg
        mro = self.spec.mass_in_running_order_kg
        return None if gross is None or mro is None else gross - mro

    @property
    def body_type(self) -> BodyType | None:
        tipologia = self.roster.tipologia
        if tipologia is None or tipologia not in _BODY_OF_TIPOLOGIA:
            return None
        published = _BODY_OF_TIPOLOGIA[tipologia]
        if published is not None:
            return published
        height = self.spec.height_m
        if height is None:
            return None
        return (
            BodyType.CAMPERVAN_HIGH_TOP
            if _metres_to_millimetres(str(height)) > HIGH_TOP_ABOVE_MM
            else BodyType.CAMPERVAN
        )


def _reconciles(product: RollerTeamProduct) -> tuple[bool, str]:
    """The length, as published by each of the three sources, must be the same length.

    This is the whole guard on the columnar parse. The brochure's masses have no
    arithmetic of their own to check — no payload is published anywhere — so the only
    evidence that column *n* belongs to this model is that its length agrees with two
    documents that were written separately.
    """
    brochure = product.spec.length_m
    if brochure is None:
        return False, "the brochure's specification table gives no external length"
    if abs(brochure - product.price.length_m) > 0.001:
        return False, (
            f"the brochure says {brochure}m and the price list says "
            f"{product.price.length_m}m, so the specification column may not be this "
            f"model's and no figure beside it can be trusted"
        )
    tile = product.tile_length_m
    if tile is not None and abs(brochure - tile) > 0.001:
        return False, (
            f"the brochure and the price list agree at {brochure}m but the model page "
            f"says {tile}m"
        )
    agreed = "all three sources" if tile is not None else "both documents"
    return True, f"{agreed} give {brochure}m"


def _build_extracted_motorhome(product: RollerTeamProduct) -> ExtractedMotorhome:
    """One product as a `Motorhome`, with the provenance a reviewer reads beside it.

    Fields deliberately left with **no provenance, and so never proposed**:

    * `bed_types` — the brochure's bed-dimension rows are ragged, giving one value for
      three columns on the Kronos, so nothing can be assigned from them. They are narrated
      instead, with their own figures, for a person to read against the drawing.
    * `sleeping_area`, `kitchen_location`, `lounge_location`, `bathroom_layout` — only a
      floorplan settles those.
    * the four `automatic_*` figure columns — Roller Team price the automatic as an
      **uplift** (£1,860 Ford, £3,840 Fiat), not as a price, so there is no published
      automatic price to record. `automatic_available` is a plain Yes, which the citation
      rule gives directly.
    """
    spec = product.spec
    automatic = gearbox.automatic_available_from([product.price.line])

    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=spec.manufacturer_range,
        model=product.model,
        base_vehicle_manufacturer=fmlv_base_vehicle(product.price.chassis.split()[0]),
        berths=spec.berths,
        mh_passenger_seats_inc_driver=spec.belted_seats,
        rrp_pounds=product.price.on_the_road_pounds,
        mtplm_kilograms=spec.gross_vehicle_weight_kg,
        mro_kilograms=spec.mass_in_running_order_kg,
        mh_payload_kilograms=product.payload_kilograms,
        mh_length_mm=_mm(spec.length_m),
        mh_width_mm=_mm(spec.width_m),
        mh_height_mm=_mm(spec.height_m),
        body_type=product.body_type,
        automatic_available=automatic[0] if automatic else None,
        heating=spec.heating[0] if spec.heating else None,
        refrigeration=spec.refrigeration[0] if spec.refrigeration else None,
    )

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, url: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=url, snippet=f"{product.label} — {snippet}"
        )

    brochure_table = (
        f"the 2027 brochure's {spec.manufacturer_range} 'Technical Specifications' table"
    )
    price_line = f"the 2027 UK price list: {product.price.line!r}"

    renamed = RENAMED_MODELS.get((spec.manufacturer_range, product.model))
    moved = (
        f'; FMLV holds this layout as "{renamed[0]} {renamed[1]}", under Roller Team\'s '
        f"older UK brand name, and the identical mass in running order and length confirm "
        f"it is the same vehicle"
        if renamed
        else ""
    )
    record(
        "manufacturer_range",
        product.roster.link,
        f"range {spec.manufacturer_range!r}, from the site's own gamma taxonomy{moved} — "
        f"accept with the model, they are one name",
    )
    record(
        "model",
        product.roster.link,
        f"model {product.model!r}, from the page title. Roller Team serve some models under "
        f"a slug that disagrees with the title, so the title is what is read — accept "
        f"with the range, they are one name",
    )
    record(
        "rrp_pounds",
        PRICE_LIST_PAGE_URL,
        f"£{product.price.on_the_road_pounds:,} on the road, from {price_line}. Roller "
        f"Team publish no price on their website at all, so this is the only price they "
        f"publish anywhere. On the road is their ex-works figure plus the £435 they name "
        f"as number plates, twelve months VED and first registration",
    )
    record(
        "base_vehicle_manufacturer",
        PRICE_LIST_PAGE_URL,
        f"the chassis is given as {product.price.chassis!r} by both the price list and "
        f"{brochure_table}",
    )
    if spec.berths is not None:
        fault = _KNOWN_TILE_FAULTS.get(product.label)
        caveat = f". NOTE: {fault[1]}" if fault and fault[0] == "berths" else ""
        record(
            "berths",
            BROCHURE_PAGE_URL,
            f"{spec.berths_line!r} in {brochure_table}. The base figure is recorded; a "
            f"parenthesised extra is the £290 fifth berth, which is an option{caveat}",
        )
    if spec.belted_seats is not None:
        record(
            "mh_passenger_seats_inc_driver",
            BROCHURE_PAGE_URL,
            f"{spec.belted_seats} belted seats, from {brochure_table}. Roller Team do not "
            f"state the belt type, so this is their count as published",
        )
    if spec.gross_vehicle_weight_kg is not None:
        record(
            "mtplm_kilograms",
            BROCHURE_PAGE_URL,
            f"gross vehicle weight {spec.gross_vehicle_weight_kg:,}kg, from "
            f"{brochure_table}. A free upgrade to 3,650kg (Fiat) or 3,550kg (Ford) is "
            f"offered; the base vehicle's figure is the one recorded",
        )
    if spec.mass_in_running_order_kg is not None:
        record(
            "mro_kilograms",
            BROCHURE_PAGE_URL,
            f"mass in running order {spec.mass_in_running_order_kg:,}kg, from "
            f"{brochure_table}",
        )
    if product.payload_kilograms is not None:
        record(
            "mh_payload_kilograms",
            BROCHURE_PAGE_URL,
            f"{product.payload_kilograms:,}kg, DERIVED as the gross vehicle weight "
            f"{spec.gross_vehicle_weight_kg:,}kg less the mass in running order "
            f"{spec.mass_in_running_order_kg:,}kg. Roller Team publish no payload "
            f"anywhere, in either document",
        )
    for field_name, metres, what in (
        ("mh_length_mm", spec.length_m, "external length"),
        ("mh_width_mm", spec.width_m, "external width"),
        ("mh_height_mm", spec.height_m, "external height"),
    ):
        if metres is None:
            continue
        extra = ""
        if field_name == "mh_length_mm":
            extra = (
                f". The price list and the model page give the same {metres}m, which is "
                f"what proves this is the right column of the brochure's table"
            )
        record(
            field_name,
            BROCHURE_PAGE_URL,
            f"{what} {metres}m, from {brochure_table}{extra}",
        )
    if motorhome.body_type is not None:
        if _BODY_OF_TIPOLOGIA.get(product.roster.tipologia or "") is None:
            detail = (
                f"the site files it under tipologia/{product.roster.tipologia}, and at "
                f"{_mm(spec.height_m):,}mm it is above the 2,300mm high-top line"
            )
        else:
            detail = (
                f"the site files it under tipologia/{product.roster.tipologia}, which is "
                f"Roller Team publishing their own body type rather than us deriving one"
            )
        record("body_type", product.roster.link, detail)
    if motorhome.automatic_available is not None:
        record(
            "automatic_available",
            PRICE_LIST_PAGE_URL,
            f"{automatic[1]!r} in the price list. The automatic is priced as an UPLIFT "
            f"rather than as a price of its own, so the automatic_* figure columns stay "
            f"blank",
        )
    if spec.heating is not None:
        record("heating", BROCHURE_PAGE_URL, f"{spec.heating[1]!r}, from {brochure_table}")
    if spec.refrigeration is not None:
        record(
            "refrigeration",
            BROCHURE_PAGE_URL,
            f"{spec.refrigeration[1]!r}, from {brochure_table}",
        )

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


def _mm(metres: float | None) -> int | None:
    return None if metres is None else _metres_to_millimetres(str(metres))


def find_document(page_html: str) -> str | None:
    """The one PDF a document page links, or `None`.

    Both pages link exactly one, which is why no "which edition is this" disambiguation is
    needed — and why a page that suddenly links two is worth narrating rather than
    guessing at.
    """
    found = sorted(set(_PDF_HREF.findall(page_html)))
    return found[0] if len(found) == 1 else None


def _tiles(page_html: str) -> dict[str, str]:
    """The model page's four headline tiles, read by label and never by position."""
    pattern = re.compile(
        r'<div class="number">([^<]*)</div>\s*<div class="value">([^<]*)</div>'
    )
    return {_tidy(label): _tidy(number) for number, label in pattern.findall(page_html)}


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 - nothing on this site needs rendering
    snapshot_dir: Path,  # noqa: ARG001 - `Fetcher` already snapshots every request
    *,
    ranges: tuple[tuple[str, ...], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every current Roller Team motorhome and campervan."""
    wanted = {entry[-1] for entry in ranges}

    roster_result = http.fetch(ROSTER_URL)
    if roster_result.status_code != 200:
        raise RuntimeError(
            f"the model roster returned HTTP {roster_result.status_code} from "
            f"{ROSTER_URL}; the site's own model finder renders no links without "
            f"JavaScript, so there is no other way in"
        )
    entries, roster_notes = parse_roster(
        roster_result.file_path.read_text(encoding="utf-8", errors="replace")
    )
    for note in roster_notes:
        on_progress(note)
    on_progress(f"the roster lists {len(entries)} models")

    price_text = _read_linked_pdf(http, PRICE_LIST_PAGE_URL, "price list", on_progress)
    brochure_pages = _read_linked_pdf(
        http, BROCHURE_PAGE_URL, "brochure", on_progress, pages=True
    )

    price_rows = {row.key: row for row in parse_price_list(price_text)}
    on_progress(f"the price list prices {len(price_rows)} models")
    unreconciled = [row.full_name for row in price_rows.values() if not row.charges_reconcile]
    if unreconciled:
        on_progress(
            "on-the-road is NOT ex-works plus the £435 the list names, on: "
            + ", ".join(sorted(unreconciled))
        )

    models_by_range: dict[str, list[str]] = {}
    for row in price_rows.values():
        split = split_range_and_model(row.full_name)
        if split is None:
            on_progress(
                f"the price list names {row.full_name!r}, which starts with no range this "
                f"adapter knows, so it is skipped"
            )
            continue
        models_by_range.setdefault(split[0], []).append(split[1])

    specs, brochure_notes = parse_brochure(brochure_pages, models_by_range)
    for note in brochure_notes:
        on_progress(note)
    on_progress(f"the brochure specifies {len(specs)} models")

    extracted: list[ExtractedMotorhome] = []
    for entry in sorted(entries, key=lambda item: item.model_name):
        if entry.manufacturer_range is not None and entry.manufacturer_range not in wanted:
            continue

        price = price_rows.get(entry.key)
        spec = specs.get(entry.key)
        if price is None:
            on_progress(
                f"SKIPPED {entry.model_name}: on the website but not in the 2027 price "
                f"list, so there is no UK price and no chassis for it"
            )
            continue
        if spec is None:
            on_progress(
                f"SKIPPED {entry.model_name}: priced in the 2027 price list but absent "
                f"from the brochure's specification tables, so it has no masses"
            )
            continue

        tiles = _tiles(_fetch_text(http, entry.link))
        tile_length = _tile_metres(tiles.get("Length"))
        product = RollerTeamProduct(
            roster=entry,
            price=price,
            spec=spec,
            tile_length_m=tile_length,
            tile_berths=tiles.get("Berths"),
        )

        reconciles, note = _reconciles(product)
        if not reconciles:
            on_progress(f"DROPPED {product.label}: {note}")
            continue

        extracted.append(_build_extracted_motorhome(product))
        _narrate(product, note, on_progress)

    if len(extracted) != EXPECTED_PRODUCTS and wanted == {
        entry[-1] for entry in DEFAULT_RANGES
    }:
        on_progress(
            f"collected {len(extracted)} products where Roller Team publish "
            f"{EXPECTED_PRODUCTS}"
        )
    return extracted


def _tile_metres(raw: str | None) -> float | None:
    """`'7,12'` -> `7.12`. The tiles carry Italian decimal commas."""
    if not raw:
        return None
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return None


def _narrate(
    product: RollerTeamProduct, length_note: str, on_progress: Callable[[str], None]
) -> None:
    """Say what was found, what disagreed, and what a person still has to read off a plan."""
    spec = product.spec
    on_progress(
        f"{product.label}: £{product.price.on_the_road_pounds:,} on the road, "
        f"MTPLM {spec.gross_vehicle_weight_kg:,}kg, MRO {spec.mass_in_running_order_kg:,}kg, "
        f"payload {product.payload_kilograms:,}kg DERIVED (none published), "
        f"{spec.berths} berths, {spec.belted_seats} belted seats — length checks out, "
        f"{length_note}"
    )

    fault = _KNOWN_TILE_FAULTS.get(product.label)
    if fault is not None:
        on_progress(f"{product.label} — KNOWN WEBSITE FAULT, not a question: {fault[1]}")
    elif product.tile_berths and spec.berths is not None:
        tile_base = _COUNT_CELL.match(product.tile_berths)
        if tile_base and int(tile_base.group(1)) != spec.berths:
            on_progress(
                f"{product.label} — the model page's berth tile says "
                f"{product.tile_berths!r} and the brochure's table says {spec.berths}. The "
                f"table is recorded. A NEW disagreement, worth a look at the floorplan"
            )

    on_progress(
        f"{product.label} — HABITATION FINDINGS, for a person to type in: "
        f"heating {spec.heating[1] if spec.heating else 'NOT READ'}; "
        f"fridge {spec.refrigeration[1] if spec.refrigeration else 'NOT READ'}. "
        f"No bed type is proposed — the brochure's bed-dimension rows give fewer values "
        f"than there are columns, so they cannot be assigned. Read them off the "
        f"floorplan at {product.roster.link}"
    )


def _fetch_text(http: Fetcher, url: str) -> str:
    result = http.fetch(url)
    if result.status_code != 200:
        return ""
    return result.file_path.read_text(encoding="utf-8", errors="replace")


def _read_linked_pdf(
    http: Fetcher,
    page_url: str,
    what: str,
    on_progress: Callable[[str], None],
    *,
    pages: bool = False,
) -> str | list[str]:
    """Discover the PDF one document page links, fetch it, and return its text.

    Neither page states a model year a customer can see, so the year is read from inside
    the document and narrated. The URLs are date-stamped upload paths and change on every
    reissue, which is why they are never written down here.
    """
    page = _fetch_text(http, page_url)
    if not page:
        raise RuntimeError(f"the {what} page returned nothing from {page_url}")
    url = find_document(page)
    if url is None:
        raise RuntimeError(
            f"the {what} page at {page_url} does not link exactly one PDF, so which "
            f"document is current cannot be established"
        )
    on_progress(f"the {what} page links {url}")
    result = http.fetch(url)
    if result.status_code != 200:
        raise RuntimeError(f"the {what} returned HTTP {result.status_code} from {url}")
    document = extract_text(result.file_path)
    if pages:
        return [page.text for page in document.pages]
    return document.text
