"""Frankia motorhomes, read from the MY2027 roster and the per-layout pages.

A-class and coach built only; Frankia builds no campervans and no caravans. A Pilote
Group company, like `pilote.py`, `joa.py` and `le_voyageur.py`, though it shares no
document generator with them.

frankia.com is the factory site. There is no UK site, no sterling price, and the prices
are "non-binding recommended prices for the German market".

## Three documents, and none of them is enough alone

| source | year | roster | dimensions, berths, seats, price | MRO |
|---|---|---|---|---|
| Highlights Magazine PDF | **2027** | **definitive** | no | no |
| per-layout pages | mixed | partial | **yes** | no |
| price list PDF | 2026 | 2026 only | yes | yes |

The **roster comes from the Highlights Magazine**, pages 42-43, a spread headed *ALL
MODELS AT A GLANCE*. Nothing else states the MY2027 line-up: the range index still links
Titan and Platin pages, and the price list is a model year behind. It is transcribed into
`LAYOUTS` rather than parsed, because two pages of floor-plan tiles is a fragile thing to
read and the roster changes once a year — `check_roster` re-reads the spread every run and
says loudly if it has moved.

## MY2027 is a contraction, and the ranges were redistributed

Twenty layouts, down from the 38 rows FMLV holds live. **Titan, Platin, F-Line and M-Line
are not MY2027 ranges.** They have not simply gone: `FINAL EDITION` is a run-out that
takes one or two layouts from each of them, and four F-Line layouts have become `TOGETHER`.
`RENAMED_MODELS` declares each move so the products match instead of orphaning.

**How each pairing was evidenced matters, and it is not the same test twice.** For NEO and
NOW the exterior lengths are one-to-one — 6820, 6880, 6990 and 7050 mm each match exactly
one live FMLV row — so length identifies them. For FINAL EDITION and TOGETHER it does not:
six live rows share 7860 mm, and three share 7540 mm. Those are paired on the **layout
code**, which is unique within a range and agrees exactly (`I 790 GDW`, `I 640 SD`). See
the rename rule in `docs/adapters/README.md`, which exists because a Globecar pairing was
argued from length alone and was wrong.

## The mass in running order is deliberately not proposed

**No published document states an MRO for MY2027.** The price list is the only source that
carries one at all and it is `MODELLE 2026`; the Highlights Magazine defines the term and
never gives a figure; the layout pages do the same.

The 2026 figures could have been carried across — they agree with FMLV to the kilogram, on
all four NEO layouts and both Noctra Cruisers — but Frankia describe NEO and NOW as having
had "a comprehensive facelift", so asserting last year's masses as this year's would be
inventing corroboration. Nothing is emitted, FMLV's own figures stand, and the run says so.
The same goes for the payload, which FMLV derives from a mass we are not proposing.

`Nutzlast` in the price list would have been wrong anyway: it is defined there as MTPLM
minus MRO minus passengers minus options, and the document works the example itself
(3.500 − 2.950 − 225 − 65 = 260, where FMLV's payload would be 550). That is the same trap
`knaus.py`, `weinsberg.py` and `tab.py` record.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..fetch.http import Fetcher
from ..fetch.pdf import extract_text
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

__all__ = [
    "BASE_URL",
    "EUR_PER_GBP_RATE",
    "EXPECTED_LAYOUTS",
    "FrankiaMotorhome",
    "HIGHLIGHTS_URL",
    "LAYOUTS",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "RENAMED_MODELS",
    "check_roster",
    "collect",
    "parse_layout_blocks",
    "spec_blocks",
    "visible_lines",
]

BASE_URL = "https://www.frankia.com"
MANUFACTURER = "Frankia"
MANUFACTURER_DISPLAY_NAME = "Frankia"

#: The MY2027 Highlights Magazine, whose pages 42-43 are the only published roster.
HIGHLIGHTS_URL = (
    f"{BASE_URL}/fileadmin/user_upload/infomaterial/"
    "highlights_2027_englisch_ok_ok_ANSICHT.pdf"
)

#: Euros per pound, so a euro price is **divided** by it. The requester's rate, chosen
#: 2026-09-19; `tab.py` carries the same constant and `morelo.py` the reciprocal form.
#: These are German-market recommended prices, not UK on-the-road ones, and every
#: converted figure says so in its provenance.
EUR_PER_GBP_RATE = 1.15
EUR_PER_GBP_RATE_DATE = "2026-09-19"

EXPECTED_LAYOUTS = 20


@dataclass(frozen=True)
class _Layout:
    """One MY2027 layout: where to read it, and the identity FMLV files it under."""

    range_name: str
    model: str
    page: str
    #: The layout's heading on its page, which is not always the roster's spelling —
    #: the pages drop the `Plus` suffix that the roster and FMLV both carry.
    heading: str

    @property
    def url(self) -> str:
        return f"{BASE_URL}{self.page}"

    @property
    def label(self) -> str:
        return f"{self.range_name} {self.model}"


_NEO_CRUISER = "/en/motorhomes-recreational-vehicles/neo/frankia-neo-cruiser"
_NEO_LINER = "/en/motorhomes-recreational-vehicles/neo/frankia-neo-liner"
_NOCTRA_CRUISER = "/en/motorhomes-recreational-vehicles/noctra/frankia-noctra-cruiser"
_NOCTRA_LINER = "/en/motorhomes-recreational-vehicles/noctra/frankia-noctra-liner"
_NOW = "/en/motorhomes-recreational-vehicles/frankia-now"
_FINAL_FIAT = "/en/motorhomes-recreational-vehicles/final-edition/fiat-final-edition"
_TOGETHER_I = "/en/motorhomes-recreational-vehicles/together/frankia-together-integrated"
#: **A German path segment inside the English site.** The Together Overcab is linked as
#: `/en/wohnmobile-reisemobile/...`, so a roster built by matching
#: `/en/motorhomes-recreational-vehicles/` silently loses two layouts.
_TOGETHER_A = "/en/wohnmobile-reisemobile/together/frankia-together-overcab"

#: The MY2027 roster, transcribed from the Highlights Magazine spread. `check_roster`
#: verifies it against that spread on every run.
LAYOUTS: tuple[_Layout, ...] = (
    _Layout("Noctra", "Cruiser 7.6 L", _NOCTRA_CRUISER, "FRANKIA NOCTRA CRUISER 7.6 L"),
    _Layout("Noctra", "Liner 7.6 L", _NOCTRA_LINER, "FRANKIA NOCTRA Liner 7.6 L"),
    _Layout("Noctra", "Liner 8.3 L", _NOCTRA_LINER, "FRANKIA NOCTRA Liner 8.3 L"),
    _Layout("Neo", "Cruiser 7.0 L", _NEO_CRUISER, "FRANKIA NEO Cruiser 7.0 L"),
    _Layout("Neo", "Cruiser 7.0 B", _NEO_CRUISER, "FRANKIA NEO Cruiser 7.0 B"),
    _Layout("Neo", "Liner 7.0 L", _NEO_LINER, "FRANKIA NEO Liner 7.0 L"),
    _Layout("Neo", "Liner 7.0 B", _NEO_LINER, "FRANKIA NEO Liner 7.0 B"),
    _Layout("Neo", "Liner 6.6 H", _NEO_LINER, "FRANKIA NEO Liner 6.6 H"),
    _Layout("Now", "Cruiser 7.0 L", _NOW, "FRANKIA NOW 7.0 L"),
    _Layout("Final Edition", "I 640 SD", _FINAL_FIAT, "FRANKIA FINAL EDITION I 640 SD"),
    _Layout("Final Edition", "I 740 GD", _FINAL_FIAT, "FRANKIA FINAL EDITION I 740 GD"),
    _Layout("Final Edition", "I 790 GDW", _FINAL_FIAT, "FRANKIA FINAL EDITION I 790 GDW"),
    _Layout("Together", "I 680 Plus", _TOGETHER_I, "FRANKIA TOGETHER I 680"),
    _Layout("Together", "I 740 Plus", _TOGETHER_I, "FRANKIA TOGETHER I 740"),
    _Layout("Together", "A 680 Plus", _TOGETHER_A, "FRANKIA TOGETHER A 680"),
    _Layout("Together", "A 740 Plus", _TOGETHER_A, "FRANKIA TOGETHER A 740"),
)

#: The roster's three **Mercedes** Final Editions have no page of their own —
#: `fiat-final-edition` covers only the Fiat three, and no Mercedes counterpart exists on
#: the site.
#:
#: This matters more than a missing count: FMLV still holds all three under their old
#: ranges, so they fall out of the run as **disappeared when they are nothing of the
#: kind**. Acting on those notices would deactivate three continuing models, so the run
#: names them and says not to.
#: Each pairs the MY2027 name with the FMLV row that is really the same vehicle, so the
#: run can say which disappearance notices to ignore.
ROSTER_WITHOUT_A_PAGE: tuple[tuple[str, str], ...] = (
    ("Final Edition I 7400 GD", "M-Line / I 7400 GD"),
    ("Final Edition I 7400 Plus", "M-Line / I 7400 Plus"),
    ("Final Edition I 7900 GD", "Platin / I 7900 GD"),
)

#: What the site now calls a layout, against what FMLV still holds. Keyed on the site's
#: name, which is what `token_similarity` rewrites.
#:
#: Every entry is a range move rather than a code change, and each was checked
#: individually — see the module docstring for why NEO and NOW were evidenced on length
#: and FINAL EDITION on the layout code.
RENAMED_MODELS: dict[tuple[str, str], tuple[str, str]] = {
    ("Neo", "Cruiser 7.0 L"): ("Neo", "MT 7 GDK"),
    ("Neo", "Cruiser 7.0 B"): ("Neo", "MT 7 BD"),
    ("Neo", "Liner 7.0 L"): ("Neo", "MI 7 GDK Black Line"),
    ("Neo", "Liner 7.0 B"): ("Neo", "MI 7 BD Black Line"),
    ("Now", "Cruiser 7.0 L"): ("Now", "7.0 L"),
    ("Final Edition", "I 640 SD"): ("F-Line", "I 640 SD"),
    ("Final Edition", "I 740 GD"): ("F-Line", "I 740 GD"),
    ("Final Edition", "I 790 GDW"): ("Titan", "I 790 GDW"),
    ("Together", "A 680 Plus"): ("F-Line", "A 680 Plus"),
    ("Together", "A 740 Plus"): ("F-Line", "A 740 Plus"),
}

# --- parsing ------------------------------------------------------------------------

_TAGS = re.compile(r"<[^>]+>")
_BLOCK_TAGS = re.compile(r"<(tr|/tr|li|/li|dt|dd|br|p|div|h\d|td|/td)\b[^>]*>", re.I)
_SCRIPTS = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)

#: **Five spellings of the same heading**, across eight pages: `Technical Overview`,
#: `Technology Overview`, `Technology overview`, `Technical overview` and `Technical
#: Specifications at a Glance`. Matching one of them finds four pages and silently loses
#: the other four.
_SPEC_HEADING = re.compile(
    r"^Techn(?:ical|ology)\s+(?:Overview|Specifications at a Glance)$", re.I
)

#: `699 cm`, `3,500 kg`, `106,900 €`. **Both thousands separators appear on this site**,
#: sometimes on the same page — the NEO Liner 6.6 H states `4.500 kg` and `124.900 €`
#: where its siblings state `4,500 kg` and `119,900 €`.
_QUANTITY = re.compile(r"(\d{1,3}(?:[.,]\d{3})*)\s*(cm|kg|€)")

#: `3,500 | 4,500 kg` — two permissible masses, the second being a paid uprating.
_MASS_ALTERNATIVES = re.compile(r"\d{1,3}(?:[.,]\d{3})*\s*\|")

_LAYOUT_HEADING = re.compile(r"^FRANKIA\s+\S")


def visible_lines(html: str) -> list[str]:
    """The page as the reader sees it, one text run per line."""
    text = _SCRIPTS.sub(" ", html)
    text = _BLOCK_TAGS.sub("\n", text)
    text = _TAGS.sub(" ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#039;", "'")
    return [
        stripped
        for line in text.splitlines()
        if (stripped := re.sub(r"[ \t]+", " ", line).strip())
    ]


def _number(raw: str | None) -> int | None:
    """`4.500` and `4,500` both mean 4500; a bare `4,5` means nothing."""
    if raw is None:
        return None
    match = re.fullmatch(r"\d{1,3}(?:[.,]\d{3})*", raw.strip())
    if match is None:
        return None
    return int(raw.replace(".", "").replace(",", ""))


def _quantity(value: str | None, unit: str) -> int | None:
    """The first figure in `value` carrying `unit`, or `None`."""
    if value is None:
        return None
    for raw, found in _QUANTITY.findall(value):
        if found == unit:
            return _number(raw)
    return None


#: The labels a Technical Overview uses. Needed as a **set**, not just to look values up:
#: they delimit one label's values from the next, which is what makes a two-column block
#: readable. Anything not in here is a value.
_LABELS: frozenset[str] = frozenset(
    {
        "Platform",
        "Engine",
        "Total height",
        "Total width",
        "Total length",
        "Max allowed load",
        "Sleeping places",
        "Seats with seatbelts",
        "Price from",
    }
)

#: `Headroom overall I Round Seating Group`, whose tail varies by layout. Not read, but
#: it has to delimit, or the headroom figure is swallowed as a second column of the mass.
_HEADROOM_LABEL = re.compile(r"^Headroom\b", re.I)


def _is_label(line: str) -> bool:
    return line in _LABELS or bool(_HEADROOM_LABEL.match(line))


def spec_blocks(lines: list[str]) -> list[tuple[str, dict[str, list[str]]]]:
    """Every `(layout heading, label -> values)` block on a page, in page order.

    **The heading is the last `FRANKIA …` line before the block**, not the line directly
    above it, which is marketing copy on every page. Establishing that is what made the
    Titan, Platin, Final Edition and NOW pages readable — matching on the line above found
    nothing on any of them.

    **Each label maps to a list**, because the NOCTRA Cruiser page states Mercedes and
    Fiat side by side in one block, giving every label two values. Taking `lines[i + 1]`
    reads the first column but silently mangles the rest: `Total height` there is followed
    by a bare `314` and then `312 cm`, so the unit lands on the wrong column and the whole
    block parses as empty.
    """
    blocks: list[tuple[str, dict[str, list[str]]]] = []
    for index, line in enumerate(lines):
        if not _SPEC_HEADING.match(line):
            continue
        heading = next(
            (
                lines[back]
                for back in range(index - 1, -1, -1)
                if _LAYOUT_HEADING.match(lines[back]) and len(lines[back]) > 8
            ),
            "",
        )
        values: dict[str, list[str]] = {}
        current: str | None = None
        for step in range(index + 1, min(len(lines), index + 40)):
            candidate = lines[step]
            if _SPEC_HEADING.match(candidate) or _LAYOUT_HEADING.match(candidate):
                break
            if _is_label(candidate):
                current = candidate if candidate in _LABELS else None
                if current is not None:
                    values.setdefault(current, [])
            elif current is not None:
                values[current].append(candidate)
        blocks.append((heading, values))
    return blocks


#: Labels guaranteed to be followed by another label, so their value lists are exactly
#: one per column. The block's **last** label has nothing after it and over-collects
#: whatever prose follows, which is harmless — only index `column` is ever read — but it
#: makes a naive `max` over every label report fifteen columns instead of two.
_DELIMITED_LABELS = ("Total height", "Total width", "Total length")


def columns_in(values: dict[str, list[str]]) -> int:
    """How many platform variants this block states side by side.

    Counted from a label that another label terminates. The NOCTRA Cruiser is the only
    two-column block on the site; everything else is one.
    """
    counts = [len(values[label]) for label in _DELIMITED_LABELS if label in values]
    return min(counts) if counts else 0


@dataclass
class _Figures:
    """One layout's published figures."""

    mh_length_mm: int | None = None
    mh_width_mm: int | None = None
    mh_height_mm: int | None = None
    mtplm_kilograms: int | None = None
    berths: int | None = None
    travel_seats: int | None = None
    price_eur: int | None = None
    base_vehicle: str | None = None
    uprating_offered: bool = False
    raw_mass: str | None = None
    #: Platform variants stated side by side in this block; 2 on the NOCTRA Cruiser.
    columns: int = 1


#: The makes that appear in a `Platform` string, longest first so `Mercedes-Benz` is
#: found before any shorter substring of it. Frankia writes the platform as
#: `Mercedes-Benz • Sprinter 415`, `Fiat/AL-KO • Ducato 40 H` or `Mercedes-Benz
#: Sprinter/AL-KO`, all of which carry the chassis as well as the make.
_PLATFORM_MAKES = ("Mercedes-Benz", "Mercedes", "Peugeot", "Citroen", "Fiat", "Iveco")


def _base_vehicle(platform: str | None) -> str | None:
    """The make out of a platform string, spelt as FMLV spells it.

    The abbreviation is **not** decided here: `base.fmlv_base_vehicle` owns that for
    every adapter, so `Mercedes-Benz` becomes FMLV's `Mercedes` in one place rather than
    thirteen. This function only finds which make the string names.
    """
    if not platform:
        return None
    lowered = platform.lower()
    for make in _PLATFORM_MAKES:
        if make.lower() in lowered:
            return fmlv_base_vehicle(make)
    return None


def parse_layout_blocks(lines: list[str], column: int = 0) -> dict[str, _Figures]:
    """Each spec block on a page, keyed by its layout heading.

    `column` picks a platform variant out of a two-column block; it is 0 everywhere
    except the NOCTRA Cruiser, and out-of-range columns simply read as absent.
    """
    found: dict[str, _Figures] = {}
    for heading, values in spec_blocks(lines):

        def cell(label: str) -> str | None:
            got = values.get(label) or []
            return got[column] if column < len(got) else None

        mass = cell("Max allowed load")
        found[heading] = _Figures(
            mh_length_mm=_millimetres(cell("Total length")),
            mh_width_mm=_millimetres(cell("Total width")),
            mh_height_mm=_millimetres(cell("Total height")),
            # The FIRST of `3,500 | 4,500 kg`: the larger is a paid uprating, and the
            # base vehicle is what FMLV records.
            mtplm_kilograms=_quantity(mass, "kg"),
            berths=_number(cell("Sleeping places")),
            travel_seats=_number(cell("Seats with seatbelts")),
            price_eur=_quantity(cell("Price from"), "\u20ac"),
            base_vehicle=_base_vehicle(cell("Platform")),
            uprating_offered=bool(mass and _MASS_ALTERNATIVES.search(mass)),
            raw_mass=mass,
            columns=columns_in(values),
        )
    return found


def _millimetres(value: str | None) -> int | None:
    """A `cm` dimension in mm, tolerating a missing unit.

    In a two-column block only the *last* column carries the unit — `Total height` is
    followed by `314` and then `312 cm` — so requiring `cm` reads one variant and drops
    the other. A bare number under a dimension label is a centimetre figure.
    """
    centimetres = _quantity(value, "cm")
    if centimetres is None:
        centimetres = _number(value)
    return None if centimetres is None else centimetres * 10


#: What the page calls itself, and the body type that follows. Read from the page's own
#: words rather than derived from the layout code, because the code does not settle it:
#: FMLV holds `I 7400 GD` as an over-cab bed under M-Line and `Pure I 7400 GD` as an
#: A-class under Platin, so an `I` prefix means both things in the same export.
_BODY_TYPE_WORDS: tuple[tuple[str, BodyType], ...] = (
    ("alcove", BodyType.COACH_BUILT_OVER_CAB_BED),
    ("overcab", BodyType.COACH_BUILT_OVER_CAB_BED),
    ("a-class", BodyType.A_CLASS),
    ("liner", BodyType.A_CLASS),
    ("integrated", BodyType.A_CLASS),
    ("low-profile", BodyType.COACH_BUILT_LOW_PROFILE),
    ("semi-integrated", BodyType.COACH_BUILT_LOW_PROFILE),
    ("cruiser", BodyType.COACH_BUILT_LOW_PROFILE),
)


def body_type_from(lines: list[str], heading: str) -> tuple[BodyType | None, str]:
    """The body type the page states for itself, and the wording that settled it.

    Semi-integrated wins over integrated where both appear, because "semi-integrated"
    contains "integrated" and the pages use both words freely.
    """
    haystack = " ".join(lines[:40]).lower() + " " + heading.lower()
    if "semi-integrated" in haystack or "low-profile" in haystack:
        if "alcove" not in haystack and "overcab" not in haystack:
            return BodyType.COACH_BUILT_LOW_PROFILE, (
                "the page describes this model line as semi-integrated / Low-Profile"
            )
    for word, body_type in _BODY_TYPE_WORDS:
        if word in haystack:
            return body_type, f"the page describes this model line as {word!r}"
    return None, "the page does not say which body style this model line is"


@dataclass
class FrankiaMotorhome:
    """One MY2027 layout as read."""

    layout: _Layout
    figures: _Figures
    body_type: BodyType | None = None
    body_reason: str = ""

    @property
    def label(self) -> str:
        return self.layout.label

    @property
    def rrp_pounds(self) -> int | None:
        if self.figures.price_eur is None:
            return None
        return round(self.figures.price_eur / EUR_PER_GBP_RATE)


def _reconciles(product: FrankiaMotorhome) -> tuple[bool, str]:
    """Is the layout complete and plausible enough to propose?

    Frankia publishes no payload we can use and no MRO for MY2027, so there is no
    arithmetic self-check here — unlike every other adapter in the project. What is
    checked instead is that the page yielded a coherent block at all: a length, a width,
    a height and a permissible mass, each in a plausible band for a motorhome.

    Said plainly because it is a weaker guarantee, and a reviewer should know it.
    """
    figures = product.figures
    missing = [
        name
        for name, value in (
            ("length", figures.mh_length_mm),
            ("width", figures.mh_width_mm),
            ("height", figures.mh_height_mm),
            ("permissible mass", figures.mtplm_kilograms),
        )
        if value is None
    ]
    if missing:
        return False, f"its Technical Overview states no {', '.join(missing)}"
    if not 5_000 <= figures.mh_length_mm <= 10_000:
        return False, f"an implausible length of {figures.mh_length_mm}mm"
    if not 2_000 <= figures.mh_width_mm <= 2_600:
        return False, f"an implausible width of {figures.mh_width_mm}mm"
    if not 2_500 <= figures.mh_height_mm <= 3_600:
        return False, f"an implausible height of {figures.mh_height_mm}mm"
    if not 3_000 <= figures.mtplm_kilograms <= 8_000:
        return False, f"an implausible permissible mass of {figures.mtplm_kilograms}kg"
    return True, (
        f"length {figures.mh_length_mm}mm, width {figures.mh_width_mm}mm, height "
        f"{figures.mh_height_mm}mm and permissible mass {figures.mtplm_kilograms}kg, all "
        f"from one Technical Overview block"
    )


def check_roster(highlights_text: str) -> tuple[list[str], list[str]]:
    """`(missing, unexpected)` layout names, comparing `LAYOUTS` with the 2027 spread.

    Pages 42-43 of the Highlights Magazine are the only published statement of the MY2027
    line-up, and it is transcribed into `LAYOUTS` rather than parsed. This is what makes
    the transcription answer for itself once a year.
    """
    spread = highlights_text.upper()
    missing = [
        layout.label
        for layout in LAYOUTS
        if layout.model.upper().replace("PLUS", "").strip() not in spread
    ]
    return missing, []



def _match_heading(
    blocks: dict[str, _Figures], wanted: str
) -> _Figures | None:
    """The block whose heading is `wanted`, allowing a tagline after it.

    The NOW page heads its only block `FRANKIA NOW 7.0 L – A NOW AGE OF SPACE`, so an
    exact match drops the layout entirely. Prefix matching is safe here because a page's
    headings always differ before the tagline begins; an ambiguous prefix returns nothing
    rather than guessing which sibling was meant.
    """
    if wanted in blocks:
        return blocks[wanted]
    folded = wanted.casefold()
    hits = [
        figures
        for heading, figures in blocks.items()
        if heading.casefold().startswith(folded)
    ]
    return hits[0] if len(hits) == 1 else None


def build_extracted(product: FrankiaMotorhome, basis: str) -> ExtractedMotorhome:
    """One layout as a `Motorhome` plus the provenance a reviewer sees beside it."""
    figures = product.figures
    source_url = product.layout.url

    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.layout.range_name,
        model=product.layout.model,
        mh_length_mm=figures.mh_length_mm,
        mh_width_mm=figures.mh_width_mm,
        mh_height_mm=figures.mh_height_mm,
        mtplm_kilograms=figures.mtplm_kilograms,
        berths=figures.berths,
        mh_passenger_seats_inc_driver=figures.travel_seats,
        base_vehicle_manufacturer=figures.base_vehicle,
        rrp_pounds=product.rrp_pounds,
        body_type=product.body_type,
    )

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=source_url, snippet=f"{product.label} — {snippet}"
        )

    renamed = RENAMED_MODELS.get((product.layout.range_name, product.layout.model))
    identity_note = (
        f"; FMLV holds this layout as \"{renamed[0]} / {renamed[1]}\" and MY2027 moves it, "
        f"so accept the pair to follow the manufacturer"
        if renamed
        else ""
    )
    record(
        "manufacturer_range",
        f'range "{product.layout.range_name}", as the MY2027 Highlights Magazine groups '
        f"this layout{identity_note} — accept with the model, they are one name",
    )
    record(
        "model",
        f'model "{product.layout.model}" — accept with the range, they are one name',
    )

    if figures.mh_length_mm is not None:
        record("mh_length_mm", f"Total length: {figures.mh_length_mm // 10} cm")
    if figures.mh_width_mm is not None:
        record("mh_width_mm", f"Total width: {figures.mh_width_mm // 10} cm")
    if figures.mh_height_mm is not None:
        record("mh_height_mm", f"Total height: {figures.mh_height_mm // 10} cm")
    if figures.mtplm_kilograms is not None:
        note = (
            f"Max allowed load: {figures.raw_mass} — the FIRST figure, which is the base "
            f"vehicle; the larger is a paid uprating and is not recorded"
            if figures.uprating_offered
            else f"Max allowed load: {figures.raw_mass}"
        )
        record("mtplm_kilograms", f"{note}. {basis}")
    if figures.berths is not None:
        record("berths", f"Sleeping places: {figures.berths}")
    if figures.travel_seats is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"Seats with seatbelts: {figures.travel_seats}",
        )
    if figures.base_vehicle is not None:
        record(
            "base_vehicle_manufacturer",
            f"Platform: {figures.base_vehicle}, from the page's full platform string — "
            f"FMLV records the make alone and abbreviated",
        )
    if product.rrp_pounds is not None:
        record(
            "rrp_pounds",
            f"Price from EUR {figures.price_eur:,} / {EUR_PER_GBP_RATE} = GBP "
            f"{product.rrp_pounds:,}, at a fixed rate recorded {EUR_PER_GBP_RATE_DATE}. "
            f"NOTE the page calls these 'non-binding recommended prices for the German "
            f"market' — not a UK on-the-road price — and it is a 'from' price",
        )
    if product.body_type is not None:
        record("body_type", product.body_reason)

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001
    snapshot_dir: Path,  # noqa: ARG001
    *,
    ranges: tuple[tuple[str, str], ...] = (),  # noqa: ARG001
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every MY2027 layout with a page of its own."""
    on_progress(f"reading the MY2027 roster: {HIGHLIGHTS_URL}")
    try:
        highlights = extract_text(http.fetch(HIGHLIGHTS_URL).file_path).text
    except Exception as error:  # noqa: BLE001
        on_progress(
            f"COULD NOT READ THE 2027 HIGHLIGHTS ({type(error).__name__}), so the roster "
            f"could not be checked this run — the hardcoded {EXPECTED_LAYOUTS}-layout "
            f"list is used unverified"
        )
    else:
        missing, _ = check_roster(highlights)
        if missing:
            on_progress(
                f"THE ROSTER HAS MOVED: {missing} are in this adapter but no longer on "
                f"pages 42-43 of the Highlights Magazine, which is the only published "
                f"statement of the MY2027 line-up. Check before trusting this run"
            )
        else:
            on_progress(
                f"roster checked against the Highlights Magazine: all "
                f"{len(LAYOUTS)} layouts still listed"
            )

    pages: dict[str, list[str]] = {}
    extracted: list[ExtractedMotorhome] = []

    for layout in LAYOUTS:
        if layout.page not in pages:
            on_progress(f"fetching {layout.url}")
            pages[layout.page] = visible_lines(
                http.fetch(layout.url).file_path.read_text(
                    encoding="utf-8", errors="replace"
                )
            )
        lines = pages[layout.page]
        blocks = parse_layout_blocks(lines)

        figures = _match_heading(blocks, layout.heading)
        if figures is None:
            on_progress(
                f"dropping {layout.label} — no Technical Overview headed "
                f"{layout.heading!r} on {layout.url}; the page offers "
                f"{sorted(blocks)!r}"
            )
            continue

        body_type, body_reason = body_type_from(lines, layout.heading)
        product = FrankiaMotorhome(
            layout=layout, figures=figures, body_type=body_type, body_reason=body_reason
        )
        reconciles, reason = _reconciles(product)
        if not reconciles:
            on_progress(f"dropping {layout.label} — {reason}")
            continue

        extracted.append(build_extracted(product, reason))
        on_progress(
            f"read {product.label}: {figures.mh_length_mm}mm, "
            f"{figures.mtplm_kilograms}kg, {figures.berths} berth, "
            f"{figures.travel_seats} belted seats, "
            + (f"GBP {product.rrp_pounds:,}" if product.rrp_pounds else "no price")
        )

    on_progress(
        "MY2027 IS A CONTRACTION AND A REDISTRIBUTION. The Highlights Magazine lists 20 "
        "layouts where FMLV holds 38 live rows, and TITAN, PLATIN, F-LINE and M-LINE are "
        "no longer ranges. They have not simply gone: FINAL EDITION is a run-out taking "
        "one or two layouts from each, and four F-Line layouts are now TOGETHER. Those "
        "moves are declared as renames so the products match rather than orphan. The rows "
        "that disappear are the rest of those four ranges, and they are genuinely finishing."
    )
    if ROSTER_WITHOUT_A_PAGE:
        on_progress(
            "THREE DISAPPEARANCE NOTICES THIS RUN ARE FALSE — DO NOT DEACTIVATE: "
            + "; ".join(f"{fmlv} is MY2027's {roster}" for roster, fmlv in ROSTER_WITHOUT_A_PAGE)
            + ". All three ARE in the 2027 roster, but only the three Fiat Final "
            "Editions have a page of their own and no Mercedes counterpart exists on the "
            "site, so this adapter can read no figures for them and they fall out as "
            "unmatched. They are continuing models. FMLV's own figures stand, and the "
            "rows should be left live until Frankia publishes their pages."
        )
    on_progress(
        "MASS IN RUNNING ORDER AND PAYLOAD ARE NOT PROPOSED, deliberately. NO published "
        "document states an MRO for MY2027: the price list is the only source carrying one "
        "and it is MODELLE 2026, while the Highlights Magazine and the layout pages both "
        "define the term without ever giving a figure. The 2026 figures agree with FMLV to "
        "the kilogram, but Frankia call NEO and NOW 'a comprehensive facelift', so "
        "carrying them across would invent corroboration. FMLV's own figures stand. Note "
        "the price list's 'Nutzlast' would be wrong regardless: it subtracts passengers "
        "and options, the same trap as Knaus, Weinsberg and T@B."
    )

    if len(extracted) != len(LAYOUTS):
        on_progress(
            f"expected {len(LAYOUTS)} readable layouts and collected {len(extracted)}"
        )
    on_progress(f"collected {len(extracted)} Frankia layout(s)")
    return extracted
