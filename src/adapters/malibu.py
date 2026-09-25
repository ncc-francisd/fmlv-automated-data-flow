"""Malibu motorhomes and camper vans, from malibu-carthago.com/en/.

Part of the Carthago Group — but **not the Carthago website**. None of `carthago.py`'s
markers exist here: no `cgrb__data`, no `data-compare-brand-icon`, no `cgrb_return`. What
is shared is the configurator (`MPL_PREISLISTE=GB`, so the prices are sterling) and the
general shape of a product page. This is a sibling in structure and a rewrite in detail.

Four motorhome ranges and six van ranges, **48 products**, all one FMLV product area.

## The roster is in two shapes, and one of them is at the site root

A motorhome product sits at **either** `/en/motorhome/a-class-motorhome/malibu-i-430-…/`
**or** `/en/malibu-i-441-…/`. Ten of the A-Class 19 are under the range path and nine are
not, so a reader scoped to the range path finds 10 and reports the range as halved.
Matching `malibu-(i|t|edition)[-0-9]` anywhere in the href finds all 19, which is the
count the range page itself claims.

Vans use a different shape again, under their range, and **two of the six are misspelt on
Malibu's side**: relax lives at `/en/camper-vans/crelax-camper-van/` — plural `vans`, and a
stray `c` — so its range page is the only place it is linked correctly.

## A product is a layout, a trim and a chassis

`I 430 KB-LE lightweight 3.5 t` and `I 430 KB-LE comfort 4.2 t` are two products on two
chassis, so four vehicles per layout. The requester settled it on 25 September 2026:
*"there are different models and different layouts named comfort and lightweight on the
website, so to be consistent we treat them as two models as they do."* They are different
homologated weight classes, 3500 kg against 4250 kg, not an options bundle.

**FMLV does not split them yet** — it holds `I430 KB-LE` per chassis and nothing else — so
this run proposes roughly twenty new products, and the trim word has to reach FMLV in a
form that still matches the row it extends. See `model_name`.

## `Van Charming` is an option package, not a range

FMLV holds ten `Van Charming` rows — `600 DB Coupe`, `640 LE K GT` and so on. Malibu sell
no such range. Their own words: *"the charming exclusive line, **which is available as an
optional extra**"*, and `'GT skyview' … optionally available for`. No product page exists
for any Coupe or GT.

So those ten are the same vans FMLV already holds under Comfort, Compact, Diversity and
First Class, recorded again with their options in the name. The requester ruled on
25 September 2026 that they should be deactivated. **This adapter does not collect them**,
so they will appear as disappeared — which is correct here, and the run says so rather
than leaving a reviewer to guess.

## Where each fact lives

The **range page** gives the roster, the model name and the price; the **product page**
gives the specification. Both are needed, and neither has the other's data.

Prices are three separate runs of text — `ab`, `92.170`, `GBP` — with a dot for thousands
and the currency as a word, not a symbol. Searching for `£` finds only the range's headline
"from" price, which is what makes this look priceless at first glance.

## What a product page publishes

```
Vehicle data
Basic vehicle                                              Fiat Ducato
Total length (mm)                                          6850
Total width (mm)                                           2170**
Total height (mm)                                          2970
Rear garage interior height (mm)                           1200
Technically permissible gross vehicle weight (kg           4250
Weight in running order (kg) | Legal tolerance of -/+ 5 %  3.013 (2.862 - 3.164)
Max. weight of additional equipment in series production…  869
Max. number of seats with 3-point / 2-point safety belt…   4
Standard sleeping places                                   4
Optional sleeping places                                   5
```

Better than Carthago in two ways: the three dimensions are separate labels **already in
millimetres**, and standard and optional berths are separate rows rather than a `4 / 5`
string. `Vehicle data` anchors the block, so the labels are never read from the navigation.

`Max. weight of additional equipment in series production` is **not** the payload — the
same trap as Carthago's and Frankia's `Nutzlast`. Payload is `MTPLM − MRO`.

## The self-check, which Malibu label themselves

`Weight in running order (kg) | Legal tolerance of -/+ 5 %` → `3.013 (2.862 - 3.164)`.
3013 × 0.95 = 2862 and × 1.05 = 3164, to the kilogram. Carthago publish the same band and
leave it to be inferred; Malibu name it.

## The seat label names two kinds of belt and means one

`Max. number of seats with 3-point / 2-point safety belt while driving`, where Carthago's
says three-point only and the settled rule is that a lap belt is not a travel seat.

It is boilerplate. All 19 A-Class products carry the identical label with the value 4, and
**no page mentions a two-point belt, a lap belt, or any belt at all outside that one
line**. Carthago, same group and same chassis, states three-point-only and also says 4.
The requester ruled on 25 September 2026 to record the published figure.

**`lap_belt_warning` keeps that honest**: if any page ever names a two-point or lap belt,
the run says so instead of counting it silently.
"""

from __future__ import annotations

import html as htmllib
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from . import habitation
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

__all__ = [
    "BASE_URL",
    "EXPECTED_PRODUCTS",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "RANGES",
    "MalibuProduct",
    "collect",
    "lap_belt_warning",
    "hero_berths",
    "model_name",
    "range_for",
    "parse_technical_data",
    "roster_from",
    "visible_lines",
]

BASE_URL = "https://www.malibu-carthago.com"

MANUFACTURER = "Malibu"
MANUFACTURER_DISPLAY_NAME = "Malibu"

#: 39 motorhomes and 8 vans. The motorhome figure is Malibu's own: the A-Class range page
#: claims `19 layouts`, `9 layouts on a Fiat Ducato chassis` and `10 layouts on a Mercedes
#: Benz`, and 19 is what the roster finds.
#:
#: **FMLV holds a ninth van this cannot reach**: `Genius 641 LE performance 4x4`. Malibu
#: give the 4x4 a section page of its own but no product page, so there is nothing to read
#: and it falls out unmatched. It is a live vehicle, not a discontinued one.
EXPECTED_PRODUCTS = 47


@dataclass(frozen=True)
class _Range:
    """One range page, and the identity FMLV files its products under."""

    path: str
    #: What FMLV holds, exactly.
    fmlv_range: str
    body_type: BodyType
    #: `True` for the four motorhome ranges, whose products are found by slug anywhere on
    #: the page; `False` for a van range, whose products sit under its own path.
    is_motorhome: bool


RANGES: tuple[_Range, ...] = (
    _Range("/en/motorhome/a-class-motorhome/", "A-Class", BodyType.A_CLASS, True),
    _Range(
        "/en/motorhome/a-class-motorhome-edition-plus/",
        "A-Class Edition +",
        BodyType.A_CLASS,
        True,
    ),
    _Range(
        "/en/motorhome/coachbuilt-motorhome/",
        "Coachbuilt",
        BodyType.COACH_BUILT_LOW_PROFILE,
        True,
    ),
    _Range(
        "/en/motorhome/coachbuilt-motorhome-edition-plus/",
        "Coachbuilt Edition +",
        BodyType.COACH_BUILT_LOW_PROFILE,
        True,
    ),
    _Range(
        "/en/camper-van/compact-camper-van/",
        "Van Compact",
        BodyType.CAMPERVAN_HIGH_TOP,
        False,
    ),
    _Range(
        "/en/camper-van/comfort-camper-van/",
        "Van Comfort",
        BodyType.CAMPERVAN_HIGH_TOP,
        False,
    ),
    _Range(
        "/en/camper-van/diversity-camper-van/",
        "Van Diversity",
        BodyType.CAMPERVAN_HIGH_TOP,
        False,
    ),
    _Range(
        "/en/camper-van/first-class-two-rooms-camper-van/",
        "Van First Class",
        BodyType.CAMPERVAN_HIGH_TOP,
        False,
    ),
    # **Malibu's own misspelling**: plural `camper-vans` and a stray `c` on `crelax`. The
    # range page is the only place the product is linked, so the path has to be wrong here
    # too or the Relax is lost.
    _Range(
        "/en/camper-van/relax-camper-van/",
        "Van Relax",
        BodyType.CAMPERVAN_HIGH_TOP,
        False,
    ),
    _Range("/en/malibu-genius/", "Genius", BodyType.CAMPERVAN_HIGH_TOP, False),
)

_DROP = re.compile(r"<(script|style|noscript|svg)\b.*?</\1>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")


def visible_lines(page_html: str) -> list[str]:
    """Every non-empty run of visible text, in document order."""
    text = _TAG.sub("\n", _DROP.sub(" ", page_html))
    out: list[str] = []
    for raw in text.split("\n"):
        line = re.sub(r"\s+", " ", htmllib.unescape(raw)).strip()
        if line:
            out.append(line)
    return out


# --- the roster -----------------------------------------------------------------------

#: A motorhome product, wherever it sits — under its range or at the site root.
_MOTORHOME = re.compile(r'href="(?:' + re.escape(BASE_URL) + r')?(/en/[^"#?]*malibu-(?:i|t|edition)[-0-9][^"#?]*/)"')

#: A van product, which always sits under a camper-van path. `camper-vans?` and the stray
#: `c` on `crelax` are Malibu's misspellings, not a pattern that needs to be general.
_VAN = re.compile(
    r'href="(?:' + re.escape(BASE_URL) + r')?(/en/camper-vans?/[a-z0-9-]*/?'
    r"(?:compact|comfort|diversity|first-class-two-rooms|relax|genius)[a-z-]*-\d{3}[a-z0-9-]*/)\""
)


def roster_from(page_html: str, config: _Range) -> list[str]:
    """Every product page this range links.

    **A motorhome range is matched by slug anywhere on the page**, because nine of the
    A-Class nineteen sit at the site root rather than under the range. The motorhome pages
    carry the whole roster in a shared navigation, so `collect` scopes each range's share
    by the letter its products use rather than by the path.

    A van range links only its own, so its products are matched under a camper-van path.
    """
    pattern = _MOTORHOME if config.is_motorhome else _VAN
    found = {htmllib.unescape(link) for link in pattern.findall(page_html)}
    # `relax-640-le-r-2` is a second page for the same van; the shorter slug is the real
    # one and both carry identical data.
    return sorted(link for link in found if not link.rstrip("/").endswith("-2"))


# --- identity -------------------------------------------------------------------------

_TITLE_TAIL = re.compile(r"\s*-\s*Malibu.*$", re.IGNORECASE)
#: The weight class, which FMLV does not carry. See `model_name`.
_WEIGHT = re.compile(r"\s*\d[.,]\d\s*t\b", re.IGNORECASE)
#: `I 430` -> `I430`, which is how FMLV writes it.
_LETTER_NUMBER = re.compile(r"\b([IT])\s+(\d{3})\b")


def model_name(title: str, config: _Range) -> str | None:
    """FMLV's model name, from a product page's title.

    `Malibu I 430 KB-LE comfort 4.2 t` becomes **`I430 KB-LE comfort`**, and there are
    three deliberate choices in that:

    * **`I430`, not `I 430`.** FMLV closes the gap and the site does not.
    * **The trim word is kept**, because the requester ruled lightweight and comfort are
      two models.
    * **The weight class is dropped.** It is what makes the match work: FMLV holds
      `I430 KB-LE`, and `I430 KB-LE comfort` shares three tokens of four with it — 0.75,
      comfortably over the threshold — where `I430 KB-LE comfort 4.2 t` shares three of
      six and lands exactly *on* it. The weight is in the masses anyway.

    A van is simply its code: `Malibu Van compact 540 DB` becomes `540 DB`.
    """
    name = _TITLE_TAIL.sub("", htmllib.unescape(title)).strip()
    if not name:
        return None

    if not config.is_motorhome:
        code = re.search(r"\b(\d{3}\s+[A-Z][A-Z0-9 ]*)$", name)
        return code.group(1).strip() if code else None

    name = re.sub(r"^Malibu\s+", "", name, flags=re.IGNORECASE)
    name = _WEIGHT.sub("", name)
    name = _LETTER_NUMBER.sub(r"\1\2", name)
    name = re.sub(r"^Edition\s*\+\s*", "", name, flags=re.IGNORECASE).strip()
    # FMLV writes the variant letter bare: `I470 RB-LE K`, where the site quotes it.
    name = name.replace('"', "").replace("“", "").replace("”", "")
    return re.sub(r"\s{2,}", " ", name) or None


_CHASSIS: tuple[tuple[str, str], ...] = (
    ("mercedes", "Mercedes"),
    # `fiat-duacto` is Malibu's typo in one slug; matching `ducato` alone drops that
    # product's chassis and leaves it indistinguishable from its Mercedes sibling.
    ("ducato", "Fiat"),
    ("duacto", "Fiat"),
    ("fiat", "Fiat"),
    ("iveco", "IVECO"),
)


def chassis_from(text: str | None) -> str | None:
    """The base vehicle from a slug or from the `Basic vehicle` cell."""
    if not text:
        return None
    lowered = text.casefold()
    for needle, make in _CHASSIS:
        if needle in lowered:
            return make
    return None


def range_for(title: str, config: _Range) -> _Range:
    """The range a motorhome belongs to, from its own name rather than the page.

    **Only two products are Edition +**, and Malibu say so in their names:
    `Malibu Edition + I 490 RB-LE comfort` and `Malibu Edition + T 490 RB-LE comfort`.
    Nothing else carries it — not in its title, not on its page — and the four range pages
    all list the same 28 products, so the page proves nothing.

    **FMLV currently groups them differently**, putting `I450`, `I470 K`, `I480 K` and
    `I490` under `A-Class Edition +` and the matching `T` layouts under `Coachbuilt
    Edition +` — sixteen rows in all. Nothing on the site today supports that, so this
    follows the site and those twelve rows will be proposed as moving to the base range.
    If that grouping is to be kept instead, this is the one function to change.
    """
    if not config.is_motorhome:
        return config
    is_edition = re.search(r"Edition\s*\+", title, re.IGNORECASE) is not None
    letter = "T" if re.search(r"\bT\s?\d{3}", title) else "I"
    wanted = {
        (True, "I"): "A-Class Edition +",
        (True, "T"): "Coachbuilt Edition +",
        (False, "I"): "A-Class",
        (False, "T"): "Coachbuilt",
    }[(is_edition, letter)]
    return next(r for r in RANGES if r.fmlv_range == wanted)


# --- the technical block --------------------------------------------------------------

#: Anchors the block, so no label is ever read from the navigation above it.
_ANCHOR = "Vehicle data"

#: The fields wanted, each as the patterns Malibu actually print. **Patterns, not
#: literals**: the gross weight is `Tech. permissible gross vehicle weight (kg)` on most
#: pages and `Technically permissible gross vehicle weight (kg` on others, and exact-
#: matching one of them dropped 30 of 47 products. The long form also appears in the legal
#: explainer prose lower down every page, which is what `_ANCHOR` keeps out.
_LABELS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("base_vehicle", re.compile(r"^Basic vehicle$", re.I)),
    ("transmission", re.compile(r"^Transmission$", re.I)),
    ("length", re.compile(r"^Total length \(mm\)", re.I)),
    ("width", re.compile(r"^Total width \(mm\)", re.I)),
    ("height", re.compile(r"^Total height \(mm\)", re.I)),
    ("garage", re.compile(r"^Rear garage interior height \(mm\)", re.I)),
    ("mtplm", re.compile(r"^Tech(?:nically)?\.? permissible gross vehicle weight", re.I)),
    ("mro", re.compile(r"^Weight in running order \(kg\)", re.I)),
    # `numbers` is the Genius page; everything else is singular. Vans say "3-point
    # safety belt" and only the motorhomes say "3-point / 2-point".
    ("seats", re.compile(r"^Max\. numbers? of seats with .*belt", re.I)),
    ("berths", re.compile(r"^Standard sleeping places$", re.I)),
    ("berths_optional", re.compile(r"^Optional sleeping places$", re.I)),
    # Some pages print one combined row instead of the two above — `4 / 5 (standard /
    # optinal)`, their typo — so both layouts are read.
    ("berths_combined", re.compile(r"^Sleeping places$", re.I)),
    ("heating", re.compile(r"^Heating system$", re.I)),
)


def parse_technical_data(lines: list[str]) -> dict[str, str]:
    """The `Vehicle data` table, keyed by what each field *is* rather than what it is called.

    Anchored on `Vehicle data` so no label is read from the navigation above it or from the
    legal explainer below it — the phrase "technically permissible gross weight" appears
    in that prose on every page.
    """
    if _ANCHOR not in lines:
        return {}
    start = lines.index(_ANCHOR)
    block = lines[start : start + 80]

    found: dict[str, str] = {}
    for i, line in enumerate(block):
        if i + 1 >= len(block):
            break
        for key, pattern in _LABELS:
            if key not in found and pattern.match(line):
                found[key] = block[i + 1]
                break
    return found


_FOOTNOTE = re.compile(r"\*+")


def _number(value: str | None) -> int | None:
    """The first figure, dots stripped and footnote asterisks ignored.

    `2170**` is 2170, `4.250 / 4.500` is 4250 — the base vehicle, per the settled rule.
    """
    if not value:
        return None
    match = re.search(r"(\d[\d.]*)", _FOOTNOTE.sub("", value))
    return int(match.group(1).replace(".", "")) if match else None


#: A dimension, not a mass: `1050 x 1140` is a rear-garage door opening. Two Coachbuilt
#: Edition + pages offer one where the gross weight should be, because a blank cell higher
#: up their table shifts every value down a row.
_DIMENSION = re.compile(r"\d\s*[x\u00d7]\s*\d")


def _mass(value: str | None) -> int | None:
    """A mass in kilograms, or `None` if the cell does not hold one.

    Rejects anything shaped like a dimension, and anything outside 1500-8000kg. No Malibu
    weighs less than a tonne and a half or more than eight, so a figure outside that came
    from the wrong row.
    """
    if not value or _DIMENSION.search(value):
        return None
    kilograms = _number(value)
    if kilograms is None or not 1500 <= kilograms <= 8000:
        return None
    return kilograms


_MASS_BAND = re.compile(r"(\d[\d.]*)\s*\(\s*(\d[\d.]*)\s*[-–]\s*(\d[\d.]*)\s*\)")


def parse_running_order(value: str | None) -> tuple[int | None, tuple[int, int] | None]:
    """`3.013 (2.862 - 3.164)` -> `(3013, (2862, 3164))`."""
    if not value:
        return None, None
    band = _MASS_BAND.search(value)
    if band is None:
        return _number(value), None
    base, low, high = (int(x.replace(".", "")) for x in band.groups())
    return base, (low, high)


#: `ab` / `92.170` / `GBP` across three runs of text on the range page. A dot for
#: thousands, and the currency as a word — searching for a pound sign finds only the
#: range's headline "from" price.
_PRICE_VALUE = re.compile(r"^(\d[\d.]*)$")


def prices_from(lines: list[str]) -> dict[str, int]:
    """`{model title: pounds}` for every product card on a range page."""
    found: dict[str, int] = {}
    title: str | None = None
    for i, line in enumerate(lines):
        if line.lower().startswith("malibu ") and len(line) < 70:
            title = line
        elif (
            title
            and _PRICE_VALUE.match(line)
            and i + 1 < len(lines)
            and lines[i + 1].upper() == "GBP"
        ):
            found.setdefault(title, int(line.replace(".", "")))
            title = None
    return found


#: The range hero's berth figure, which is the only place a van states one. `up to 4`
#: means four *with the optional pop-up roof*; a bare `2` is the vehicle as built.
_UPPER_BOUND = re.compile(r"^up to\s+(\d+)$", re.IGNORECASE)
_DEFINITE = re.compile(r"^(\d+)$")


def hero_berths(lines: list[str]) -> tuple[int | None, str | None]:
    """`(berths, raw)` from a range page's hero strip.

    Malibu publish no sleeping places in a van's vehicle-data table and none on its card,
    but the range hero carries one: `up to 4` / `sleeping berths` on every van range, and
    a bare `2` / `Lengthways single beds` on the Genius.

    **`up to 4` is not four berths.** Those pages also say `Optional: Pop-up roof
    family-for-4`, so the fourth and third berths need an option bought — and the settled
    rule is that a berth range takes the lower figure, which these pages never state. So an
    upper bound returns `None` and is narrated; only a definite figure is recorded.

    FMLV holds 2 for every van and the Genius, and a high-top rather than an elevating-roof
    body, which is the same reading arrived at independently.
    """
    for i, line in enumerate(lines):
        if not re.search(r"sleeping berth|lengthways single beds", line, re.IGNORECASE):
            continue
        for candidate in (lines[i - 1] if i else "", lines[i + 1] if i + 1 < len(lines) else ""):
            if _UPPER_BOUND.match(candidate.strip()):
                return None, candidate.strip()
            if _DEFINITE.match(candidate.strip()):
                return int(candidate.strip()), candidate.strip()
    return None, None


_LAP_BELT = re.compile(r"2-point|two-point|lap belt", re.IGNORECASE)


def lap_belt_warning(lines: Iterable[str]) -> str | None:
    """Any line naming a two-point belt **other than the boilerplate seat label**.

    The seat figure is recorded on the reading that the label is generic — all 19 A-Class
    products carry it identically with the value 4 and nothing else on any page mentions a
    belt. This is what stops that reading being silent: the day a page really does name a
    lap belt, the run says so rather than keeping on counting it as a travel seat.
    """
    for line in lines:
        if _LAP_BELT.search(line) and not line.startswith("Max. number of seats"):
            return line
    return None


# --- the product ----------------------------------------------------------------------


@dataclass(frozen=True)
class MalibuProduct:
    """One product page, read."""

    config: _Range
    url: str
    model: str
    chassis: str | None
    rrp_pounds: int | None
    #: From the range hero, where a van states its only berth figure.
    hero_berths: int | None
    fields: dict[str, str]
    lines: list[str]

    @property
    def label(self) -> str:
        chassis = f" {self.chassis}" if self.chassis else ""
        return f"{self.config.fmlv_range} {self.model}{chassis}"

    @property
    def mtplm_kilograms(self) -> int | None:
        return _mass(self.fields.get("mtplm"))

    @property
    def mro_kilograms(self) -> int | None:
        return parse_running_order(
            self.fields.get("mro")
        )[0]

    @property
    def tolerance_band(self) -> tuple[int, int] | None:
        return parse_running_order(
            self.fields.get("mro")
        )[1]

    @property
    def derived_payload_kilograms(self) -> int | None:
        if self.mtplm_kilograms is None or self.mro_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mro_kilograms

    @property
    def berths(self) -> int | None:
        """The standard figure. Malibu print it two ways — as its own row, and on some
        pages as `4 / 5 (standard / optinal)`, their typo — so both are read."""
        standard = self.fields.get("berths")
        if standard:
            return _number(standard)
        combined = self.fields.get("berths_combined")
        if combined:
            return _number(combined)
        # Vans state none in their table; the range hero is the only place they do.
        return self.hero_berths

    @property
    def travel_seats(self) -> int | None:
        return _number(self.fields.get("seats"))


def _reconciles(product: MalibuProduct) -> tuple[bool, str]:
    """`(ok, reason)` — does Malibu's own ±5% band bracket the mass it is printed with?"""
    mro, band = product.mro_kilograms, product.tolerance_band
    if mro is None:
        return False, "the page states no weight in running order"
    # **A missing gross weight does not drop the product.** Two Coachbuilt Edition + pages
    # print `1050 x 1140` under `Technically permissible gross vehicle weight (kg)` - a
    # rear-garage door opening, because Malibu's own table has slipped a row. Everything
    # else on those pages is sound, so the product is kept and only the mass it cannot
    # state is withheld; `build_extracted` proposes no MTPLM and no payload without it.
    if product.mtplm_kilograms is None:
        return True, (
            f"mass in running order {mro}kg. NO GROSS WEIGHT IS PROPOSED: the page's "
            f"`technically permissible gross vehicle weight` cell holds "
            f"{product.fields.get('mtplm')!r}, which is a door opening rather than a mass "
            f"- their table has slipped a row. Payload cannot be derived either, so FMLV's "
            f"own figures stand"
        )
    if band is None:
        return True, (
            f"mass in running order {mro}kg; the page prints no tolerance band to check it"
        )
    if product.mtplm_kilograms is not None and product.mtplm_kilograms <= mro:
        return False, (
            f"the gross weight reads {product.mtplm_kilograms}kg against a mass in "
            f"running order of {mro}kg, which is impossible \u2014 the parse has taken a "
            f"figure from the wrong row"
        )
    low, high = band
    if abs(round(mro * 0.95) - low) <= 1 and abs(round(mro * 1.05) - high) <= 1:
        return True, (
            f"mass in running order {mro}kg, and Malibu's own ±5% legal tolerance "
            f"({low}-{high}kg) brackets it exactly"
        )
    return False, (
        f"mass in running order reads {mro}kg but the stated ±5% tolerance is "
        f"{low}-{high}kg, which brackets {round((low + high) / 2)}kg — the parse has "
        f"taken figures from different rows"
    )


def build_extracted(product: MalibuProduct, *, mass_basis: str) -> ExtractedMotorhome:
    """The product and a provenance line for every field it proposes."""
    features = habitation.features_from(product.lines)
    garage = product.fields.get("garage")

    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.config.fmlv_range,
        model=product.model,
        base_vehicle_manufacturer=fmlv_base_vehicle(product.chassis),
        mh_length_mm=_number(product.fields.get("length")),
        mh_width_mm=_number(product.fields.get("width")),
        mh_height_mm=_number(product.fields.get("height")),
        berths=product.berths,
        mh_passenger_seats_inc_driver=product.travel_seats,
        mtplm_kilograms=product.mtplm_kilograms,
        mro_kilograms=product.mro_kilograms,
        mh_payload_kilograms=product.derived_payload_kilograms,
        rrp_pounds=product.rrp_pounds,
        body_type=product.config.body_type,
        rear_garage=bool(garage) or None,
        heating=features["heating"].value if "heating" in features else None,
        refrigeration=features["refrigeration"].value if "refrigeration" in features else None,
        microwave=features["microwave"].value if "microwave" in features else None,
    )

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=product.url, snippet=f"{product.label} — {snippet}"
        )

    record(
        "manufacturer_range",
        f'range "{product.config.fmlv_range}", as the {product.config.path} page groups '
        f"this product — accept with the model, they are one name",
    )
    record(
        "model",
        f'model "{product.model}" — accept with the range, they are one name. Malibu '
        f"sell this layout as both a lightweight and a comfort, which are different "
        f"weight classes and so different vehicles",
    )
    if motorhome.base_vehicle_manufacturer is not None:
        record(
            "base_vehicle_manufacturer",
            f"{product.chassis}. **Part of the identity here**: Malibu sell this layout "
            f"on more than one chassis and the two are different vehicles",
        )
    for field_name, key, label in (
        ("mh_length_mm", "length", "Total length (mm)"),
        ("mh_width_mm", "width", "Total width (mm)"),
        ("mh_height_mm", "height", "Total height (mm)"),
    ):
        if getattr(motorhome, field_name) is not None:
            record(field_name, f"{label}: {product.fields.get(key)}")
    if motorhome.berths is not None:
        record(
            "berths",
            f"Standard sleeping places: {product.fields.get('berths') or product.fields.get('berths_combined')} "
            f"— the standard figure, per the settled rule that a berth range takes "
            f"the lower",
        )
    if motorhome.mh_passenger_seats_inc_driver is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"Max. number of seats with 3-point / 2-point safety belt: "
            f"{product.travel_seats}. Malibu's label names both kinds of belt, but it is "
            f"boilerplate — no page mentions a two-point or lap belt anywhere else, and "
            f"Carthago on the same chassis states three-point only and gives the same "
            f"figure",
        )
    if product.mtplm_kilograms is not None:
        record(
            "mtplm_kilograms",
            f"Technically permissible gross vehicle weight: {product.mtplm_kilograms}kg",
        )
    if product.mro_kilograms is not None:
        record("mro_kilograms", f"Weight in running order: {mass_basis}")
    if product.derived_payload_kilograms is not None:
        record(
            "mh_payload_kilograms",
            f"payload {product.derived_payload_kilograms}kg, derived as MTPLM less MRO. "
            f"Malibu publish no payload; their 'max. weight of additional equipment in "
            f"series production' is a different figure and is not recorded",
        )
    if product.rrp_pounds is not None:
        record(
            "rrp_pounds",
            f"the range page's price for this product, {product.rrp_pounds:,} GBP. "
            f"Sterling: the configurator carries MPL_PREISLISTE=GB and no euro sign "
            f"appears anywhere in the product area",
        )
    record(
        "body_type",
        f"{product.config.body_type.value.removeprefix('type_').replace('_', ' ')}: every "
        f"product on the {product.config.fmlv_range} page is one",
    )
    if motorhome.rear_garage:
        record("rear_garage", f"Rear garage interior height (mm): {garage}")
    for name, feature in features.items():
        record(name, f"{feature.note or 'read from the specification'}: {feature.snippet}")

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001
    snapshot_dir: Path,  # noqa: ARG001
    *,
    ranges: tuple[tuple[str, str], ...] = (),  # noqa: ARG001
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every Malibu the UK site publishes: 39 motorhomes and 9 vans."""
    roster: list[tuple[_Range, str]] = []
    prices: dict[str, int] = {}
    heroes: dict[str, tuple[int | None, str | None]] = {}
    claimed: set[str] = set()

    for config in RANGES:
        url = BASE_URL + config.path
        on_progress(f"fetching {url}")
        try:
            page = http.fetch(url).file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as error:  # noqa: BLE001
            on_progress(f"COULD NOT FETCH {url} ({type(error).__name__}) — its products are lost")
            continue

        page_lines = visible_lines(page)
        prices.update(prices_from(page_lines))
        heroes[config.fmlv_range] = hero_berths(page_lines)
        # **Every motorhome page lists every motorhome product.** The four range pages are
        # filtered views of one catalogue, not separate sets, so a product cannot be
        # assigned to a range by the page it was found on. It is assigned by its own name
        # instead — see `range_for` — and each page contributes only what no earlier page
        # has already claimed, which keeps the roster from being counted four times.
        links = [link for link in roster_from(page, config) if link not in claimed]
        if not links:
            on_progress(
                f"NO PRODUCTS on {url}. Nothing matched either roster pattern, which means "
                f"the template has changed rather than the range being empty"
            )
            continue
        claimed.update(links)
        on_progress(f"  {config.fmlv_range}: {len(links)} product(s)")
        roster.extend((config, link) for link in links)

    on_progress(f"roster: {len(roster)} products across {len(RANGES)} ranges")

    extracted: list[ExtractedMotorhome] = []
    unpriced: list[str] = []
    no_berths: list[str] = []
    no_mass: list[str] = []
    lap_belts: list[str] = []

    for config, link in roster:
        url = BASE_URL + link
        try:
            lines = visible_lines(
                http.fetch(url).file_path.read_text(encoding="utf-8", errors="replace")
            )
        except Exception as error:  # noqa: BLE001
            on_progress(f"dropping {link} — could not fetch it ({type(error).__name__})")
            continue

        title = lines[0] if lines else ""
        model = model_name(title, config)
        if model is None:
            on_progress(f"dropping {link} — no model name could be read from {title!r}")
            continue

        warning = lap_belt_warning(lines)
        if warning:
            lap_belts.append(f"{config.fmlv_range} {model}: {warning!r}")

        fields = parse_technical_data(lines)
        product = MalibuProduct(
            config=range_for(title, config),
            url=url,
            model=model,
            chassis=chassis_from(link) or chassis_from(fields.get("base_vehicle")),
            rrp_pounds=prices.get(_TITLE_TAIL.sub('', htmllib.unescape(title)).strip()),
            hero_berths=heroes.get(range_for(title, config).fmlv_range, (None, None))[0],
            fields=fields,
            lines=lines,
        )
        if product.rrp_pounds is None:
            unpriced.append(product.label)
        if product.berths is None:
            no_berths.append(product.label)
        if product.mtplm_kilograms is None:
            no_mass.append(product.label)

        reconciles, reason = _reconciles(product)
        if not reconciles:
            on_progress(f"dropping {product.label} — {reason}")
            continue

        extracted.append(build_extracted(product, mass_basis=reason))
        on_progress(
            f"read {product.label}: {product.mtplm_kilograms}kg, "
            f"{product.derived_payload_kilograms}kg payload, {product.berths} berth, "
            f"{product.travel_seats} belted seats, "
            + (f"GBP {product.rrp_pounds:,}" if product.rrp_pounds else "no price")
        )

    if lap_belts:
        on_progress(
            "A PAGE NAMES A TWO-POINT OR LAP BELT: "
            + "; ".join(lap_belts)
            + ". The seat figure is recorded on the reading that Malibu's "
            "'3-point / 2-point' label is boilerplate — no page had ever mentioned a belt "
            "outside it. That has changed, so CHECK THE SEAT COUNTS before accepting them: "
            "the settled rule is that a lap belt is not a travel seat"
        )
    if no_mass:
        on_progress(
            f"NO GROSS WEIGHT PUBLISHED for {', '.join(no_mass)}. Their pages print a "
            f"rear-garage door opening under the gross-weight label - Malibu's table has "
            f"slipped a row - so neither the mass nor the payload is proposed and FMLV's "
            f"own figures stand. Everything else on those pages reads normally"
        )

    if no_berths:
        on_progress(
            f"BERTHS NOT PROPOSED for {', '.join(no_berths)}. A van states none in its "
            f"vehicle-data table; its range hero says `up to 4` sleeping berths, and the "
            f"same page says `Optional: Pop-up roof family-for-4` — so four needs an "
            f"option bought, and the lower figure those pages never state is what the "
            f"settled rule asks for. FMLV holds 2 for every van, with a high-top rather "
            f"than an elevating-roof body, which is the same reading. Nothing is proposed "
            f"and those figures stand"
        )

    if unpriced:
        on_progress(
            f"NO PRICE PROPOSED for {', '.join(unpriced)} — no card on the range page "
            f"matched the product page's own title. FMLV's own figures stand"
        )

    on_progress(
        "DISAPPEARANCE NOTICE THAT IS FALSE — DO NOT DEACTIVATE: Genius 641 LE "
        "performance 4x4. Malibu give the 4x4 a section page of its own but no product "
        "page, so no figures can be read for it and it falls out unmatched. It is still on "
        "sale; FMLV's own figures stand"
    )
    on_progress(
        "VAN CHARMING IS NOT COLLECTED, deliberately. FMLV holds ten `Van Charming` rows "
        "(600 DB Coupe, 640 LE K GT and so on) but Malibu sell no such range: the charming "
        "exclusive line is 'available as an optional extra' in their own words, GT skyview "
        "is 'optionally available for', and no product page exists for any Coupe or GT. "
        "Those ten are vans FMLV already holds under Comfort, Compact, Diversity and First "
        "Class, recorded again with their options in the name. The requester ruled on "
        "2026-09-25 that they should be DEACTIVATED, so their disappearance notices are "
        "expected and correct"
    )
    on_progress(
        "LIGHTWEIGHT AND COMFORT ARE TWO MODELS, the requester's ruling of 2026-09-25 — "
        "different homologated weight classes, 3.5t against 4.25t, not an options bundle. "
        "FMLV does not split them yet, so this run proposes the comfort or lightweight "
        "half of each pair as new"
    )

    if len(extracted) != EXPECTED_PRODUCTS:
        on_progress(
            f"expected {EXPECTED_PRODUCTS} products and collected {len(extracted)} — check "
            f"whether the range has really changed"
        )
    on_progress(f"collected {len(extracted)} Malibu product(s)")
    return extracted
