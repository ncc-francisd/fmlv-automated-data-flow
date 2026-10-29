"""Reading the Fleurette catalogue, which two brands share column for column.

Surveyed 14 October 2026, built 28 October 2026. See `docs/adapters/fleurette-florium.md`.
**Not an adapter** — `fleurette.py` and `florium.py` are, and both read through here, the
way four Trigano brands read through `marquis.py`.

## One company, two brands, and one technical table serving both

`Fleurette Constructeur` is the manufacturer; **Fleurette** and **Florium** are the brands,
and FMLV carries them as two suppliers on one `fmlv_manufacturer` — the `Swift Group Ltd`
arrangement, which is why `ADAPTERS` keys on the display name as well.

The catalogue's technical pages head every column with **both** names at once:

    MIGRA TEUR / BAXTER   MAGISTER / MA YFLOWER   ELISTER / BELIXTER   DISCOVER / WINCESTER
    60LG  64LDF  69LJG    67LO  70LMF  70LJG  74LMF   73LMF  73LJG     72LMF 72LJG 74LJG 75LMF

So **one column is two products** — a Fleurette and a Florium — differing in trim (walnut
against ash) and, on six layouts, in price. Thirteen shared columns plus four Black Pearl
vans, which Florium sell alone, is 13 + 17 = **30 products**.

The layout code alone is therefore ambiguous: `70LMF` is a Magister *and* a Mayflower, and
twelve of the thirteen codes are used twice. Nothing here may key on the code by itself —
that is the trap that halved the Malibu roster. The **range** is what separates them, and
it is unique to one brand, so range + model stays unique across all thirty.

## `Wellness` is not a range and not part of a model name

The catalogue's contents page advertises *"Gamme Wellness Profilés"* and *"Gamme Wellness
Intégraux"*, which reads like two more ranges. It is a trim: the technical table files
every layout under the four paired range names above, and Fleurette's own price list heads
its blocks `Profile MIGRATEUR`, `Profile MAGISTER` and `A-Class DISCOVER` with no Wellness
block anywhere. The two documents that carry the data agree; only the marketing section
does not, and it is the one with no figures in it.

It is priced, though, and that is worth knowing: Fleurette label six layouts `Wellness`
where Florium label none, and where neither brand does the two are priced **identically**
(60 LG £68,690 both, 64 LDF £70,990 both, 67 LO £74,390 both). So the catalogue's
"same vehicle, different veneer" is true of seven layouts and not of the other six.

## Where each figure comes from

* **the catalogue** (`/le-catalogue-camping-cars/`, rediscovered per run because the
  superseded 2026 edition sits beside the current one) — dimensions, mass in running
  order, berths, seats, heating, refrigeration;
* **four UK price lists emailed on 28 October 2026** — the prices, and nothing else.
  They are on no website and were in none of 7,252 sitemap URLs, so no run can rediscover
  them. This is the Pilote arrangement and `joa.py` is the pattern: a module constant, a
  provenance line saying it was manually sourced, re-verified at the model-year changeover.

Three things the catalogue gets right that usually have to be fought for: the width is
published **excluding mirrors**, the mass is a real mass in running order (*"Avec 1
conducteur, 90% d'eau propre…"* — with one driver, so no allowance to add back), and the
berths row marks what is optional as `3 (S) /4 (O)`.

## The checks, and what each one is actually worth

There is no published arithmetic here — the payload is not printed, so MTPLM minus MRO
cannot be checked against anything. Three weaker things stand in, and it matters which
does the work:

**The exact count, in both directions, is the real guard.** `split_row` takes the last
`count` tokens, requires every one to match the row's value shape, *and* requires the
token to their left not to. A row that lost a cell pulls a label word in and fails the
shape; a row that gained one would otherwise drop its first column silently and shift
every vehicle left a place, which the left-hand test is there to stop.

**The layout code is a length, to within 90mm** — the first two digits are decimetres:

    60LG 5,99   64LDF 6,47   69LJG 6,99   67LO 6,77   70LMF 6,97   74LMF 7,38
    73LMF 7,30  72LMF 7,19   75LMF 7,49   59LT 5,99   63LJ 6,36

`LENGTH_TOLERANCE_MM` is 150, as in `joa.py`. **This is corroboration and not a slip
detector**, and the difference is worth stating plainly: a simulated one-place shift of
the real figures is caught on only **seven of sixteen** columns, because neighbouring
layouts often share a length outright — `70LMF` and `70LJG` are both 6,97, `73LMF` and
`73LJG` both 7,30, and all three 63s are 6,36. It earns its place catching a roster read
in the wrong order; it would not catch a shifted row on its own.

**The fridge rows are complementary.** The 149-litre and 157-litre compression fridges are
printed as two rows carrying exactly one `S` per column between them, so a column with
both or neither is misaligned — an independent reading of the same thirteen columns.

## Reading the tables: one text run per line, not per cell

`extract_positioned_text` gives this document roughly **one run per visual line**, with
the label and all thirteen values glued together, so there are no per-cell x positions to
align on. Rows are therefore split on whitespace and the count must equal the layout
count or the row is dropped — which is the column-alignment guard, and why two repairs
have to happen first:

* **kerning splits decimals.** `7,19` extracts as `7,1 9`, so a naive split gives fifteen
  tokens for thirteen columns. `_MIS_KERNED` closes them before anything counts.
* **a berth cell contains spaces.** `3 (S) /4 (O)` is four tokens for one column, so it is
  reduced to its standard figure before the split, which is the berths rule applied at the
  only point where it can be.

## What is deliberately not read

**The seats row, wherever it is a band.** Its footnote reads *"Nombre de places carte
grise **maximum** … variable selon configuration"*, and `docs/adapters/README.md` is
explicit that a "permitted" figure is a type-approval ceiling rather than a fitment claim:
corroborate it or leave the field unset *and unregistered*. So a bare `4` is recorded —
one published figure, qualified, is still the figure — and `4/3 selon configuration` or
`3/2/4 selon configuration` is not. That leaves the four Elister/Belixter and the AL-KO
Discover/Wincester without a seat count until someone confirms one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path
from collections.abc import Callable

from ..fetch.http import Fetcher
from ..fetch.pdf import extract_text
from ..product_model.enums import BodyType, Heating, Refrigeration
from ..product_model.model import Motorhome
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

__all__ = [
    "BLACK_PEARL_CODES",
    "CATALOGUE_PAGE_URL",
    "Column",
    "LENGTH_TOLERANCE_MM",
    "RANGE_PAIRS",
    "catalogue_url",
    "collect_columns",
    "implied_length_mm",
    "lower_berths",
    "metres_to_mm",
    "reconciles",
    "split_row",
]

BASE_URL = "https://www.fleurette-florium.fr"

#: The catalogue's own page. The superseded 2026 edition is linked here beside the current
#: one, so the right PDF is rediscovered per run rather than written in — see
#: `catalogue_url`.
CATALOGUE_PAGE_URL = f"{BASE_URL}/le-catalogue-camping-cars/"

#: `(Fleurette range, Florium range, layout codes, body type)`, in the catalogue's own
#: column order. The pairing is the catalogue's, printed in its column headings as
#: `MIGRATEUR / BAXTER`.
#:
#: **The body type is read off the document, not inferred from a height.** Page 38 prints
#: `PROFILÉS` and `INTÉGRAUX` as two banners above the columns, and their x positions
#: centre over columns 1–9 and 10–13 exactly. Three further sources agree: the price lists
#: head their blocks `Profile MIGRATEUR` / `Profile MAGISTER` against `A-Class DISCOVER`
#: and `A-Class WINCESTER`, and the Elister and Belixter pages banner themselves "The
#: ultra-spacious low-profile" and "The prestigious XXL low-profile".
#:
#: That matters most for the Elister and Belixter, which are the tallest coachbuilts here
#: at 2.92m and carry a drop-down bed — so a height would have argued for an over-cab bed
#: and been wrong. `height-does-not-decide-coachbuilt-profile` is the rule; the
#: manufacturer's own section heading is better evidence than either.
RANGE_PAIRS: tuple[tuple[str, str, tuple[str, ...], BodyType], ...] = (
    ("Migrateur", "Baxter", ("60LG", "64LDF", "69LJG"), BodyType.COACH_BUILT_LOW_PROFILE),
    (
        "Magister",
        "Mayflower",
        ("67LO", "70LMF", "70LJG", "74LMF"),
        BodyType.COACH_BUILT_LOW_PROFILE,
    ),
    ("Elister", "Belixter", ("73LMF", "73LJG"), BodyType.COACH_BUILT_LOW_PROFILE),
    (
        "Discover",
        "Wincester",
        ("72LMF", "72LJG", "74LJG", "75LMF"),
        BodyType.A_CLASS,
    ),
)

#: The base vehicle each range is built on, as `fmlv_base_vehicle` spells it. Page 38's
#: chassis rows mark `FIAT Ducato` standard on every column but the Elister/Belixter pair,
#: where `MERCEDES-BENZ Sprinter` is standard instead and Fiat is unavailable — so this is
#: read from the document rather than assumed. The AL-KO chassis under the 74LJG and 75LMF
#: is a chassis variant, not another base vehicle: those are still Fiat.
BASE_VEHICLES: dict[str, str] = {
    "Migrateur": "Fiat",
    "Baxter": "Fiat",
    "Magister": "Fiat",
    "Mayflower": "Fiat",
    "Elister": "Mercedes",
    "Belixter": "Mercedes",
    "Discover": "Fiat",
    "Wincester": "Fiat",
    "Black Pearl": "Fiat",
}

#: Seat counts the catalogue publishes as a configuration band and the requester supplied
#: instead, keyed by layout code. Read on 28 October 2026 off the model pages' `3/4 Travel
#: places` tile, which is drawn as an image and so cannot be parsed; corroborated on the
#: 2027 Belixter pages, and 3 is the base figure by the settled base-vehicle rule.
#:
#: The catalogue's own row says `4/3 selon configuration`, which `docs/adapters/README.md`
#: forbids recording uncorroborated — this is that corroboration, and it is why these four
#: can be uploaded at all. Re-verify at the model-year changeover.
SUPPLIED_SEATS: dict[str, int] = {"73LMF": 3, "73LJG": 3}

#: Said in provenance wherever `SUPPLIED_SEATS` is used.
SUPPLIED_SEATS_SOURCE = (
    "MANUALLY SOURCED from the model pages' '3/4 Travel places' panel, read by the "
    "requester on 28 October 2026 and corroborated on the 2027 Belixter pages. 3 is the "
    "standard figure; the catalogue prints only the band '4/3 selon configuration', which "
    "is a type-approval ceiling. Not machine-readable and not refreshed by later runs"
)

#: Florium's van conversions, which Fleurette do not sell. Their own technical page, four
#: columns wide. The catalogue prints `59 LT` with a space and `63LJ` without; the price
#: list says `Model 59LT` throughout, which is the spelling FMLV holds.
BLACK_PEARL_CODES: tuple[str, ...] = ("59LT", "63LJ", "63LD", "63KS")

#: Every shared layout, flat, in column order — thirteen of them.
SHARED_CODES: tuple[str, ...] = tuple(
    code for _fleurette, _florium, codes, _body in RANGE_PAIRS for code in codes
)

#: Which range each shared layout belongs to, by column index. The code alone cannot say —
#: `70LMF` is a Magister *and* a Mayflower — so this is indexed, never looked up by name.
SHARED_RANGE_AT: tuple[tuple[str, str, BodyType], ...] = tuple(
    (fleurette, florium, body)
    for fleurette, florium, codes, body in RANGE_PAIRS
    for _code in codes
)

#: How far a length may sit from the one its layout code implies, before the row is treated
#: as misaligned. See the module docstring; `joa.py` uses the same figure for the same
#: reason.
LENGTH_TOLERANCE_MM = 150

#: Every layout's maximum authorised mass, in kilograms. The row publishes a list of
#: chassis options — `3500/3650/4250`, or `3500/4100` on the Mercedes — and the base
#: vehicle is the lightest by the settled rule, the heavier plates being upgrades. The
#: Black Pearl page prints a bare `3500`. One figure for all thirty, so it is asserted here
#: rather than parsed out of a row that extraction breaks across three lines.
#:
#: **The Mercedes pair's payload looks far too low and is correct anyway.** 3500 against
#: the Elister and Belixter's 3122 and 3161 kg leaves 378 and 339 kg on the range's
#: longest vehicles, and their price list prices an *"Upgrade from 4T1 GVW"* that reads as
#: 4100 already being the plate. Ruled 29 October 2026: 3500 is standard and 4100 is what
#: options buy, so recomputing these from 4100 would record an optioned variant. See
#: `docs/adapters/fleurette-florium.md`.
MTPLM_KILOGRAMS = 3500

#: Said in provenance wherever `MTPLM_KILOGRAMS` is recorded.
MTPLM_SOURCE = (
    "'Masse maximale en charge techniquement admissible VL ou PL', which lists the "
    "chassis options 3500/3650/4250 (3500/4100 on the Mercedes). 3500 is the base vehicle; "
    "the heavier plates are upgrades"
)

#: A campervan taller than this is a high top — the shared NCC threshold, as used by
#: `auto_trail.py`, `bailey.py` and `joa.py`. Every Black Pearl is 2590mm.
HIGH_TOP_ABOVE_MM = 2300

#: How each row of the dimensions table is found: the text it opens with, and a word that
#: must appear somewhere in it. The second half matters for the two mass rows, which both
#: open `Masse` — and the accented letter that would otherwise tell them apart does not
#: survive extraction, arriving as a replacement character.
LENGTH_ROW = ("Longueur hors tout", "")
WIDTH_ROW = ("Largeur hors tout", "")
HEIGHT_ROW = ("Hauteur hors tout", "")
MRO_ROW = ("Masse", "vide")
SEATS_ROW = ("Places carte grise", "")
BERTHS_ROW = ("Places couchage", "")

#: The equipment rows worth reading, as `(prefix, words that must also appear)`. Accented
#: letters do not survive extraction — `Réfrigérateur` arrives as `R�frig�rateur`
#: — so every one of these is matched on an unaccented fragment.
#:
#: The two heating rows are both `Chauffage air pulsé`, which is blown air whichever is
#: fitted, so they are read together. The `Combi 4 ED` and `Combi 6ED` rows beside them are
#: the electric-and-diesel **options** and are deliberately not matched: an option must
#: never set the base specification.
#:
#: **Alde is on this document too and is not standard on anything.** Page 39 prices it as
#: `OPTION INTEGRAUX FIAT : Pack Optimum : Chauffage Alde`, and the site gives it a whole
#: "our expertise" page, so it reads at a glance as though some of these were wet central
#: heating. Every one of the thirteen carries a Truma Combi as standard, so every one is
#: blown air; Alde is an upgrade and changes nothing recorded here.
HEATING_ROWS = (
    ("Chauffage air puls", ("Combi 4 D (",)),
    ("Chauffage air puls", ("Combi 6 D (",)),
)

#: The two fridge rows. Both are compression with a freezer compartment, so either one
#: means the same thing — but between them they carry **exactly one `S` per column**, which
#: is an independent reading of the same thirteen columns and so a free alignment check.
#: The vans' page spells it `compession`, their typo, which is why neither entry matches on
#: that word.
FRIDGE_ROWS = (
    ("R", ("frig", "157 L")),
    ("R", ("frig", "149 L")),
)

#: What a value in each row must look like, so that a row which lost a cell and pulled a
#: label word in from the left is rejected instead of silently shifting every vehicle's
#: figures one place. See `split_row`.
METRES_VALUE = re.compile(r"\d+,\d+")
MASS_VALUE = re.compile(r"\d{4}|NC")
BERTHS_VALUE = re.compile(r"[1-9]")

#: `S` standard, `O` optional, `-` unavailable. The hyphen arrives space-padded, so it is
#: its own token.
MARKER_VALUE = re.compile(r"[SO]|-")

#: *Non communiqué* — the catalogue's own marker for a figure it does not publish. It
#: stands against the whole Discover/Wincester mass row and the Black Pearl 63LD, and
#: nothing is emitted for those: an unfound figure is surfaced, never inferred.
_NOT_PUBLISHED = "NC"

#: `7,19` extracts as `7,1 9`. Closed before anything is counted, or a thirteen-column row
#: yields fifteen tokens and is dropped as misaligned. See the module docstring.
_MIS_KERNED = re.compile(r"(\d,\d)\s(\d)\b")

#: `3 (S) /4 (O)` — standard three berths, four with an option. Reduced to the standard
#: figure before the split, both because it is four tokens for one column and because the
#: lower figure is the one FMLV records.
_STANDARD_OF = re.compile(r"(\d)\s*\(S\)\s*/\s*\d\s*\(O\)")

#: `2/3 (O)` on the vans — the same thing said differently, standard first.
_STANDARD_SLASH = re.compile(r"(\d)/\d\s*\(O\)")

#: A seats cell the footnote makes a ceiling rather than a fitment claim. Left unread —
#: see the module docstring.
_BY_CONFIGURATION = re.compile(r"\bselon\b", re.I)

#: The first two digits of a layout code are its length in decimetres.
_CODE_LENGTH = re.compile(r"^(\d{2})")

#: The model year inside a catalogue's filename. **Not `\b(20\d{2})\b`**: these names
#: separate their parts with underscores, which are word characters, so a word boundary
#: never fires between `_` and `2027` and every filename reads as having no year at all.
#: Guarding on digits instead also keeps `297x210` from being misread as one.
_YEAR = re.compile(r"(?<!\d)(20\d{2})(?!\d)")


@dataclass(frozen=True)
class Column:
    """One column of a technical table: a layout, with the figures both brands share.

    A column is **not** a product. The thirteen shared columns each become two — one
    Fleurette, one Florium — and only the four Black Pearl columns become one apiece.
    `fleurette.py` and `florium.py` do that mapping; this module never names a brand.
    """

    code: str
    length_mm: int
    width_mm: int
    height_mm: int
    mro_kilograms: int | None
    berths: int
    #: `None` where the catalogue gives a band rather than a figure — see the docstring.
    seats: int | None
    body_type: BodyType
    heating_note: str
    fridge_note: str


def catalogue_url(html: str) -> str | None:
    """The current catalogue PDF, chosen by the model year in its filename.

    The downloads page links the superseded edition beside the current one —
    `Catalogue_Fleurette_FR_297x210_2026-13_BD.pdf` next to
    `Catalogue_Fleurette_297x210_2027_FR_BD-17.pdf` — and they differ in the position of
    the year as well as its value, so this takes the **largest four-digit year** found in
    any catalogue filename rather than matching a shape. A new edition is picked up without
    a code change, which is the whole point of not hardcoding it.
    """
    best: tuple[int, str] | None = None
    for url in re.findall(r'https?://[^"\'<>\s]+?\.pdf', html, re.I):
        name = url.rsplit("/", 1)[-1]
        if "catalogue" not in name.lower():
            continue
        years = [int(y) for y in _YEAR.findall(name)]
        if not years:
            continue
        year = max(years)
        if best is None or year > best[0]:
            best = (year, url)
    return best[1] if best else None


def split_row(line: str, label: str, count: int, *, value: re.Pattern[str]) -> tuple[str, ...] | None:
    """The `count` values of one table row, or `None` if they do not come out cleanly.

    **The `None` is the column-alignment guard**, and it is the only one available:
    extraction gives one run per line, so there are no per-cell positions to align against.
    A row that yields the wrong number of values has either picked up a stray token or lost
    one, and in both cases every figure after the fault belongs to the wrong vehicle.
    Dropping it loses one row; trusting it writes one vehicle's weight onto another, which
    nothing downstream would question.

    **Values are taken from the end, not from after the label**, because the labels carry
    qualifiers that cannot be stripped by length: `Largeur hors tout (sans rétroviseurs)`,
    and worse, `Hauteur hors tout (jantes 15'' Profilés et jantes 16'' Intégraux de
    série)`, whose parenthesis contains two numbers that would otherwise read as the first
    two columns. Taking the last `count` tokens sidesteps the qualifier entirely, and
    `value` is what stops that being reckless: every token must look like a figure, so a
    row that lost a value and pulled in a label word is rejected rather than silently
    shifted.

    The repairs in `_MIS_KERNED`, `_STANDARD_OF` and `_STANDARD_SLASH` happen before the
    count, because all three are cases where the document means one cell and the text gives
    several tokens.
    """
    if not line.startswith(label):
        return None
    remainder = _MIS_KERNED.sub(r"\1\2", line)
    remainder = _STANDARD_OF.sub(r"\1", remainder)
    remainder = _STANDARD_SLASH.sub(r"\1", remainder)
    # Footnote markers sit between the label and the first value, and an asterisk is not a
    # value. Dropped here rather than from the label, so the label stays the document's.
    tokens = remainder.replace("*", " ").split()
    if len(tokens) < count:
        return None
    values = tuple(tokens[-count:])
    if not all(value.fullmatch(token) for token in values):
        return None
    # **The token just before the values must not look like one.** Taking from the end
    # catches a row that *lost* a cell, because a label word is pulled in and fails the
    # pattern — but a row that gained one would quietly drop its first column and shift
    # every vehicle left a place, with thirteen plausible values still in hand. Requiring
    # a non-value immediately to the left is what makes the count exact in both
    # directions.
    preceding = tokens[-count - 1] if len(tokens) > count else None
    if preceding is not None and value.fullmatch(preceding):
        return None
    return values


def leading_seat_counts(region: str, count: int) -> tuple[int | None, ...]:
    """Seat counts for as many columns as the row states plainly, then `None`.

    The seats row is the one the extraction cannot lay out, because its awkward cells are
    phrases — `4/3 selon configuration` — that wrap onto their own lines and arrive out of
    column order. Reconstructing it would mean guessing, and a guessed seat count is the
    Bürstner mistake exactly.

    So this reads only the **leading run of bare integers** and leaves every column after
    it unset. On the motorhome page that is the seven columns printed as a plain `4`,
    stopping at the first `4/3`; on the vans' page it is all four. Columns left `None` are
    the ones the footnote makes a type-approval ceiling anyway, which
    `docs/adapters/README.md` says not to record without corroboration — so the cautious
    reading and the settled rule want the same thing here, and the two 72s lost along the
    way have no published mass either and cannot be uploaded regardless.
    """
    tokens = region.replace("*", " ").split()
    # The label itself holds no digits on either page, so the first digit found is the
    # first column — asserted by `test_neither_seats_label_contains_a_digit`.
    seats: list[int | None] = []
    for token in tokens:
        if token.isdigit():
            seats.append(int(token))
            if len(seats) == count:
                break
        elif seats:
            break
    return tuple(seats) + (None,) * (count - len(seats))


def metres_to_mm(text: str) -> int | None:
    """`5,99` to 5990. French decimal comma, three significant figures, metres."""
    cleaned = _MIS_KERNED.sub(r"\1\2", text.strip()).replace(",", ".")
    try:
        return round(float(cleaned) * 1000)
    except ValueError:
        return None


def lower_berths(text: str) -> int | None:
    """The standard berth count, never the optioned one.

    By the time a cell reaches here `split_row` has already reduced `3 (S) /4 (O)` to `3`,
    so this is mostly a parse. It keeps the lower-of-a-pair handling anyway for a cell
    written as a bare range, which the vans' page does as `2/3`.
    """
    cleaned = text.strip()
    figures = [int(n) for n in re.findall(r"\d+", cleaned)]
    return min(figures) if figures else None


def implied_length_mm(code: str) -> int | None:
    """The length a layout code claims, in millimetres: `60LG` to 6000."""
    match = _CODE_LENGTH.match(code)
    return int(match.group(1)) * 100 if match else None


def reconciles(code: str, length_mm: int | None) -> bool:
    """Whether a column's length agrees with the length its own name implies.

    The self-check. A column read one place out of step carries its neighbour's length,
    and neighbours here are 300–500mm apart while a code and its own length are never more
    than 90mm apart. See the module docstring.
    """
    implied = implied_length_mm(code)
    if implied is None or length_mm is None:
        return False
    return abs(length_mm - implied) <= LENGTH_TOLERANCE_MM


def seats_or_none(text: str) -> int | None:
    """A bare seat count, or `None` where the catalogue gives a configuration band.

    `4` is recorded: one published figure, footnoted as options-dependent, is still the
    figure. `4/3 selon configuration` is not, because the footnote makes the row a
    type-approval **maximum** and the README's Bürstner rule says a permitted figure is a
    ceiling rather than a fitment claim — corroborate it or leave the field unset.
    """
    cleaned = text.strip()
    if _BY_CONFIGURATION.search(cleaned) or "/" in cleaned:
        return None
    return int(cleaned) if cleaned.isdigit() else None


def fetch_catalogue_pages(
    http: Fetcher, *, on_progress: Callable[[str], None] = lambda message: None
) -> list[str]:
    """Every page of the current catalogue as text, having rediscovered which one it is."""
    on_progress(f"fetching the catalogue page: {CATALOGUE_PAGE_URL}")
    page = http.fetch(CATALOGUE_PAGE_URL)
    html = Path(page.file_path).read_text(encoding="utf-8", errors="replace")
    url = catalogue_url(html)
    if url is None:
        message = (
            f"no catalogue PDF found on {CATALOGUE_PAGE_URL} — the downloads page has "
            f"changed shape. Nothing can be read without it"
        )
        raise RuntimeError(message)
    on_progress(f"the current catalogue is {url.rsplit('/', 1)[-1]}")
    document = http.fetch(url)
    extracted = extract_text(Path(document.file_path))
    if extracted.is_empty():
        message = f"the catalogue at {url} extracted no text at all"
        raise RuntimeError(message)
    return [page.text for page in extracted.pages]


def find_row(lines: list[str], prefix: str, contains: tuple[str, ...] = ()) -> str | None:
    """The first line opening with `prefix` and holding every word in `contains`.

    Two mass rows both open `Masse`, and the accented letter that would tell them apart
    does not survive extraction, so the second half is how they are separated.
    """
    for line in lines:
        if line.startswith(prefix) and all(word in line for word in contains):
            return line
    return None


def _marker_row(
    lines: list[str], specs: tuple[tuple[str, tuple[str, ...]], ...], count: int
) -> tuple[tuple[str, ...], ...]:
    """Every `S`/`O`/`-` row among `specs` that reads cleanly, dropping those that do not."""
    found = []
    for prefix, contains in specs:
        # **Every** matching line, not the first. The motorhome and van tables repeat the
        # same equipment labels at different widths, and the motorhome row comes first in
        # the document — so taking the first match would hand the vans a thirteen-column
        # row, which `split_row` rightly refuses, and the vans would end up with no
        # equipment read at all rather than their own four-column row.
        for line in lines:
            if not line.startswith(prefix) or not all(word in line for word in contains):
                continue
            values = split_row(line, prefix, count, value=MARKER_VALUE)
            if values is not None:
                found.append(values)
                break
    return tuple(found)


def _standard_anywhere(rows: tuple[tuple[str, ...], ...], index: int) -> bool:
    """Whether any of these rows marks this column standard."""
    return any(row[index] == "S" for row in rows)


def find_table_page(pages: list[str], codes: tuple[str, ...]) -> tuple[int, tuple[str, ...]]:
    """`(index of the page holding this table, its length row)`.

    **The page is found rather than numbered.** The dimensions table is on page 38 for the
    motorhomes and 42 for the vans today, and a catalogue that gains a spread moves both.
    So this walks the pages looking for the one whose length row splits into exactly
    `len(codes)` values *and* whose text names every layout — two conditions a page of
    marketing prose cannot satisfy by accident.
    """
    for index, page in enumerate(pages):
        lines = page.splitlines()
        length_line = find_row(lines, LENGTH_ROW[0], (LENGTH_ROW[1],))
        if length_line is None:
            continue
        lengths = split_row(length_line, LENGTH_ROW[0], len(codes), value=METRES_VALUE)
        # **Whitespace-insensitive**, because the vans' page heads its first column
        # `59 LT` while the price list, the Black Pearl's own page and FMLV all spell it
        # `59LT`. The catalogue is inconsistent with itself here — `63LJ` beside it has no
        # space — so matching on the literal would have found the motorhome table and
        # declared the van one missing.
        squashed = re.sub(r"\s+", "", page)
        if lengths is None or not all(code in squashed for code in codes):
            continue
        return index, lengths

    message = (
        f"no catalogue page carries a dimensions table of {len(codes)} columns naming "
        f"{', '.join(codes)}. The catalogue has changed shape and nothing can be read "
        f"from it"
    )
    raise RuntimeError(message)


def read_table(
    lines: list[str],
    codes: tuple[str, ...],
    lengths: tuple[str, ...],
    equipment: list[str],
    *,
    on_progress: Callable[[str], None],
    what: str,
) -> tuple[Column, ...]:
    """Every column of one technical table, dropping any the checks cannot vouch for.

    `equipment` is the lines of **this table's own spread only**. The two tables repeat
    the same equipment labels at different widths — `Chauffage air pulsé Truma Combi 4 D`
    heads a thirteen-column row for the motorhomes and does not appear at all for the
    vans — so a search across the whole document hands the vans a row belonging to
    somebody else. It found one, too: before this was scoped, all four Black Pearls were
    credited with a heater read off the motorhome spread.
    """
    count = len(codes)

    def row(spec: tuple[str, str], value: re.Pattern[str]) -> tuple[str, ...] | None:
        line = find_row(lines, spec[0], (spec[1],))
        return split_row(line, spec[0], count, value=value) if line else None

    widths = row(WIDTH_ROW, METRES_VALUE)
    heights = row(HEIGHT_ROW, METRES_VALUE)
    masses = row(MRO_ROW, MASS_VALUE)
    berths = row(BERTHS_ROW, BERTHS_VALUE)
    for name, values in (("width", widths), ("height", heights), ("berths", berths)):
        if values is None:
            message = (
                f"the {what} table's {name} row did not read as {count} values. Every "
                f"product needs it, so nothing is collected rather than part of it"
            )
            raise RuntimeError(message)
    if masses is None:
        on_progress(
            f"the {what} table's mass row did not read as {count} values — no mass in "
            f"running order is proposed for any of them, and FMLV's own figures stand"
        )
        masses = (_NOT_PUBLISHED,) * count

    # The seats row wraps onto the lines after it and arrives out of column order, so its
    # whole region is handed over and only its leading plain integers are read. Four lines
    # is enough to reach the next labelled row on both pages.
    seats_line = find_row(lines, SEATS_ROW[0])
    if seats_line is None:
        seats: tuple[int | None, ...] = (None,) * count
    else:
        start = lines.index(seats_line)
        seats = leading_seat_counts(" ".join(lines[start : start + 4]), count)

    # The equipment rows run onto the pages after the dimensions, so they are searched for
    # across this table's whole spread — and no further. See the docstring.
    heating = _marker_row(equipment, HEATING_ROWS, count)
    fridges = _marker_row(equipment, FRIDGE_ROWS, count)
    if len(fridges) == 2:
        confused = [
            codes[i] for i in range(count) if sum(row[i] == "S" for row in fridges) != 1
        ]
        if confused:
            on_progress(
                f"the two {what} fridge rows should carry exactly one 'S' per column and "
                f"do not for {', '.join(confused)} — the equipment rows are misaligned, so "
                f"no refrigeration is stated for any of them"
            )
            fridges = ()

    columns = []
    for index, code in enumerate(codes):
        length_mm = metres_to_mm(lengths[index])
        if not reconciles(code, length_mm):
            on_progress(
                f"dropping {code}: its length reads {length_mm}mm where its own name "
                f"implies {implied_length_mm(code)}mm, more than {LENGTH_TOLERANCE_MM}mm "
                f"apart. A column has been read out of step"
            )
            continue
        width_mm = metres_to_mm(widths[index])
        height_mm = metres_to_mm(heights[index])
        berth_count = lower_berths(berths[index])
        if width_mm is None or height_mm is None or berth_count is None:
            on_progress(f"dropping {code}: a dimension or berth count did not parse")
            continue
        mass = masses[index]
        columns.append(
            Column(
                code=code,
                length_mm=length_mm,
                width_mm=width_mm,
                height_mm=height_mm,
                mro_kilograms=None if mass == _NOT_PUBLISHED else int(mass),
                berths=berth_count,
                seats=seats[index] if seats[index] is not None else SUPPLIED_SEATS.get(code),
                body_type=BodyType.CAMPERVAN_HIGH_TOP,  # replaced by the caller for shared columns
                heating_note=(
                    "'Chauffage air pulsé Truma Combi', standard"
                    if _standard_anywhere(heating, index)
                    else ""
                ),
                fridge_note=(
                    "'Réfrigérateur à compression … avec congélateur', standard"
                    if _standard_anywhere(fridges, index)
                    else ""
                ),
            )
        )
    return tuple(columns)


def build_product(
    column: Column,
    *,
    manufacturer: str,
    display_name: str,
    manufacturer_range: str,
    price: int | None,
    price_source: str,
) -> ExtractedMotorhome:
    """One column as one brand's product, with the provenance a reviewer reads beside it.

    The **heating and refrigeration are set from the rows this module verified**, not put
    through `habitation.features_from`. That vocabulary reads English spec prose and this
    catalogue is in French: `Chauffage air pulsé` and `Réfrigérateur à compression … avec
    congélateur` are unambiguous, already checked for alignment, and translating them into
    a matcher's idiom only to match them back would add a way to be wrong without adding
    anything. They still reach the reviewer as **findings** rather than proposals, which
    is the settled treatment of every habitation field.
    """
    payload = (
        MTPLM_KILOGRAMS - column.mro_kilograms if column.mro_kilograms is not None else None
    )
    motorhome = Motorhome(
        manufacturer=manufacturer,
        manufacturer_display_name=display_name,
        manufacturer_range=manufacturer_range,
        model=column.code,
        base_vehicle_manufacturer=fmlv_base_vehicle(BASE_VEHICLES[manufacturer_range]),
        rrp_pounds=price,
        mro_kilograms=column.mro_kilograms,
        mtplm_kilograms=MTPLM_KILOGRAMS,
        mh_payload_kilograms=payload,
        mh_length_mm=column.length_mm,
        mh_width_mm=column.width_mm,
        mh_height_mm=column.height_mm,
        mh_passenger_seats_inc_driver=column.seats,
        berths=column.berths,
        body_type=column.body_type,
        heating=Heating.BLOWN_AIR if column.heating_note else None,
        refrigeration=Refrigeration.FRIDGE_FREEZER if column.fridge_note else None,
    )

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(source_url=CATALOGUE_PAGE_URL, snippet=snippet)

    label = f"{manufacturer_range} {column.code}"
    record(
        "manufacturer_range",
        f"'{manufacturer_range}'. The catalogue heads this column with both brands at "
        f"once, and this is the half of that pair belonging to {display_name}. Paired "
        f"with the model below — accept or reject the two together",
    )
    record("model", f"'{column.code}', the layout code heading its column")
    record(
        "base_vehicle_manufacturer",
        f"{BASE_VEHICLES[manufacturer_range]}, from the chassis rows: "
        f"{'MERCEDES-BENZ Sprinter is standard and FIAT unavailable' if BASE_VEHICLES[manufacturer_range] == 'Mercedes' else 'FIAT Ducato is standard'} "
        f"on this column",
    )
    record("mh_length_mm", f"'Longueur hors tout' {column.length_mm / 1000:.2f}m")
    record(
        "mh_width_mm",
        f"'Largeur hors tout (sans rétroviseurs)' {column.width_mm / 1000:.2f}m — "
        f"published excluding mirrors, which is the figure FMLV wants",
    )
    record("mh_height_mm", f"'Hauteur hors tout' {column.height_mm / 1000:.2f}m")
    record("mtplm_kilograms", f"{MTPLM_KILOGRAMS}kg, from {MTPLM_SOURCE}")
    if column.mro_kilograms is not None:
        record(
            "mro_kilograms",
            f"'Masse à vide en ordre de marche' {column.mro_kilograms}kg. Their footnote "
            f"makes it a real mass in running order — 'Avec 1 conducteur, 90% d'eau "
            f"propre, 90% 1 bte gaz, 90% gasoil et outillage, sans options et sans "
            f"attelage' — so no driver allowance is added back",
        )
        record(
            "mh_payload_kilograms",
            f"derived: {MTPLM_KILOGRAMS}kg maximum authorised mass - "
            f"{column.mro_kilograms}kg mass in running order = {payload}kg. Fleurette "
            f"publish no payload of their own",
        )
    record("berths", f"'Places couchage' {column.berths}, the standard figure")
    if column.seats is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"'Places carte grise et nombre de ceinture' {column.seats}"
            if column.code not in SUPPLIED_SEATS
            else f"{column.seats}. {SUPPLIED_SEATS_SOURCE}",
        )
    if price is not None:
        record(
            "rrp_pounds",
            f"£{price:,}, MANUALLY SOURCED from {price_source}, because Fleurette publish "
            f"no price on any website. Their list is headed 'with VAT + Transport - OTR', "
            f"so it is a UK on-the-road price in sterling and nothing is converted. Not "
            f"machine-readable and not refreshed by later runs — re-verify at the next "
            f"model-year changeover",
        )
    record(
        "body_type",
        f"{column.body_type.value}. Page 38 banners its columns 'PROFILÉS' and "
        f"'INTÉGRAUX' and this column falls under "
        f"{'INTÉGRAUX' if column.body_type is BodyType.A_CLASS else 'PROFILÉS'}; the "
        f"price list agrees, heading its blocks 'Profile' and 'A-Class'"
        if manufacturer_range != "Black Pearl"
        else f"{column.height_mm}mm tall, above the {HIGH_TOP_ABOVE_MM}mm high-top "
        f"threshold, and a panel-van conversion",
    )
    if column.heating_note:
        record("heating", f"{label}: {column.heating_note} — blown air")
    if column.fridge_note:
        record("refrigeration", f"{label}: {column.fridge_note} — a compressor fridge")

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


def narrate_unpublished(
    products: list[ExtractedMotorhome], *, on_progress: Callable[[str], None]
) -> None:
    """Say which products are short a required field, and why, every run.

    These are collected deliberately rather than dropped — an adapter that returns nine of
    thirteen tells a reviewer the other four are discontinued — but a product with no mass
    cannot be uploaded, so the reason has to be in front of whoever is looking at the run
    rather than inferred from a blank cell.
    """
    no_mass = [
        p.motorhome for p in products if p.motorhome.mro_kilograms is None
    ]
    no_seats = [
        p.motorhome for p in products if p.motorhome.mh_passenger_seats_inc_driver is None
    ]
    if no_mass:
        names = ", ".join(f"{m.manufacturer_range} {m.model}" for m in no_mass)
        on_progress(
            f"NO MASS IN RUNNING ORDER, so no payload either and these cannot be "
            f"uploaded: {names}. The catalogue prints 'NC' against them and Fleurette "
            f"said on 28 October 2026 that the Discover and Wincester weights were still "
            f"being tested. The model pages do publish figures for some of them, but "
            f"every page that carries one is a previous model year's — do not use them"
        )
    if no_seats:
        names = ", ".join(f"{m.manufacturer_range} {m.model}" for m in no_seats)
        on_progress(
            f"NO SEAT COUNT, so these cannot be uploaded either: {names}. The catalogue "
            f"gives a band — '4/3 selon configuration' — under a footnote making the row "
            f"a type-approval maximum, which is a ceiling and not a fitment claim"
        )


def collect_columns(
    http: Fetcher, *, on_progress: Callable[[str], None] = lambda message: None
) -> tuple[tuple[Column, ...], tuple[Column, ...]]:
    """`(the thirteen shared columns, the four Black Pearl columns)`.

    The shared columns carry their range's body type; the vans are campervans, which their
    2590mm roof puts above `HIGH_TOP_ABOVE_MM` and so high tops.
    """
    pages = fetch_catalogue_pages(http, on_progress=on_progress)
    shared_at, shared_lengths = find_table_page(pages, SHARED_CODES)
    van_at, van_lengths = find_table_page(pages, BLACK_PEARL_CODES)
    on_progress(
        f"the motorhome table is on catalogue page {shared_at + 1} and the van table on "
        f"page {van_at + 1}"
    )

    # Each table's spread runs from its own page up to the next table's, so neither can
    # read the other's equipment rows. Computed from the two positions rather than written
    # down, so a catalogue that gains a spread between them still divides correctly.
    boundaries = sorted((shared_at, van_at)) + [len(pages)]
    spread = {
        start: [line for page in pages[start : boundaries[i + 1]] for line in page.splitlines()]
        for i, start in enumerate(boundaries[:-1])
    }

    shared = read_table(
        pages[shared_at].splitlines(),
        SHARED_CODES,
        shared_lengths,
        spread[shared_at],
        on_progress=on_progress,
        what="motorhome",
    )
    vans = read_table(
        pages[van_at].splitlines(),
        BLACK_PEARL_CODES,
        van_lengths,
        spread[van_at],
        on_progress=on_progress,
        what="van",
    )
    placed = tuple(
        replace(column, body_type=SHARED_RANGE_AT[SHARED_CODES.index(column.code)][2])
        for column in shared
    )
    return placed, vans
