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
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ..fetch.http import Fetcher
from ..fetch.pdf import extract_text
from ..product_model.enums import BodyType

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

#: `(Fleurette range, Florium range, layout codes)`, in the catalogue's own column order.
#: The pairing is the catalogue's, printed in its column headings as `MIGRATEUR / BAXTER`.
RANGE_PAIRS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("Migrateur", "Baxter", ("60LG", "64LDF", "69LJG")),
    ("Magister", "Mayflower", ("67LO", "70LMF", "70LJG", "74LMF")),
    ("Elister", "Belixter", ("73LMF", "73LJG")),
    ("Discover", "Wincester", ("72LMF", "72LJG", "74LJG", "75LMF")),
)

#: Florium's van conversions, which Fleurette do not sell. Their own technical page, four
#: columns wide. The catalogue prints `59 LT` with a space and `63LJ` without; the price
#: list says `Model 59LT` throughout, which is the spelling FMLV holds.
BLACK_PEARL_CODES: tuple[str, ...] = ("59LT", "63LJ", "63LD", "63KS")

#: Every shared layout, flat, in column order — thirteen of them.
SHARED_CODES: tuple[str, ...] = tuple(
    code for _fleurette, _florium, codes in RANGE_PAIRS for code in codes
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

#: What a value in each row must look like, so that a row which lost a cell and pulled a
#: label word in from the left is rejected instead of silently shifting every vehicle's
#: figures one place. See `split_row`.
METRES_VALUE = re.compile(r"\d+,\d+")
MASS_VALUE = re.compile(r"\d{4}|NC")
BERTHS_VALUE = re.compile(r"[1-9]")

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
