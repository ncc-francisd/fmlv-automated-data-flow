"""Reading a Marquis Leisure range page, which four Trigano brands share.

Marquis are the sole UK importer for Benimar, Elnagh, Mobilvetta and Panama, and they
publish the same page for each: a **range** page carrying one `Weights and Dimensions`
block per layout, with the UK specification and the on-the-road price. So by the settled
importer rule in `docs/adapters/README.md`, one Marquis page answers what exists, what it
weighs and what it costs — and the European parent sites are never fetched.

This module holds what is genuinely common. Each brand's own adapter supplies the things
that are not: its range prefixes, its body types, its base vehicle, and any page that has
to be excluded.

**Three traps live here rather than in any one adapter**, because all four brands have
them and each was found the hard way:

* the first block on a page has the page's own banner welded to its front, so the **last**
  occurrence of a range prefix wins — see `range_and_model`;
* a block must run to the **next heading** rather than a fixed window, because the price
  sits at its end — see `LAYOUT_BLOCK`;
* only a figure followed by **`OTR`** is a price; the pages also carry offer amounts.
"""

from __future__ import annotations

import html
import re
from collections.abc import Iterable

from . import habitation

BASE_URL = "https://www.marquisleisure.co.uk"

#: The importer's index for one brand, which links its current range pages.
def index_url(brand: str) -> str:
    """`/new-motorhomes/<brand>`, the page that lists a brand's ranges.

    Not a stock listing: the requester's standing warning about this site is *"you have to
    avoid the used stock for sale pages"*, and `RANGE_HREF` only admits `…-range` slugs.
    """
    return f"{BASE_URL}/new-motorhomes/{brand}"


#: A current range page on the importer's site. The `-range` suffix is what keeps stock
#: listings out; `for-sale` slugs cannot match it.
RANGE_HREF = re.compile(rf'href="(?:{re.escape(BASE_URL)})?/(?P<slug>[a-z0-9-]+-range)"', re.I)

#: The phrase that begins every layout's specification.
#:
#: **Marquis publish two templates and are mid-redesign**, so this admits both: the older
#: heads its table `Weights and Dimensions`, the newer just `Dimensions`. The lookahead is
#: what keeps the shorter form honest — the older template also contains `GARAGE APERTURE
#: DIMENSIONS (mm)`, which would otherwise open a second, empty block for every layout.
LAYOUT_MARKER = re.compile(r"(?:Weights and )?Dimensions\s+(?=Berths\b)", re.I)

#: How far back from the marker a layout's name is taken.
#:
#: Wide enough for a banner plus a name — `COACHBUILT MOTORHOME RANGE Primero 201` — and
#: `range_and_model` then takes the **last** range prefix inside it, so whatever else the
#: window caught is discarded rather than parsed.
HEADING_LOOKBACK = 70


def layout_blocks(text: str) -> list[tuple[str, str]]:
    """`(heading, body)` for every layout on a range page, in page order.

    Anchored on the marker rather than on a pattern for the heading, because **the brands
    do not agree on case**: Mobilvetta shouts `K.YACHT 59` and Benimar writes `Primero
    201`. A first version required upper case and collected **zero** of Benimar's sixteen
    layouts — caught by the roster check rather than reaching a review.

    **A body runs all the way to the next marker**, because the price is the last thing in
    a block, immediately before the next layout's name. Two earlier attempts lost prices by
    stopping short: a fixed 700-character window lost two of the four K-Yacht prices, and
    stopping a lookback early lost three of Benimar's four Primero prices. The next
    layout's name is therefore inside this body, which is harmless — every field pattern
    names its own label, and the next block's price is beyond it.
    """
    marks = list(LAYOUT_MARKER.finditer(text))
    blocks: list[tuple[str, str]] = []
    for index, mark in enumerate(marks):
        heading = text[max(0, mark.start() - HEADING_LOOKBACK) : mark.start()].strip()
        ends = marks[index + 1].start() if index + 1 < len(marks) else len(text)
        blocks.append((heading, text[mark.end() : ends]))
    return blocks

#: **Only a price followed by `OTR`.** The pages also carry offer amounts — Mobilvetta's
#: three motorhome pages each show a `£4,000` discount — which are not vehicle prices.
PRICE = re.compile(r"£\s*(?P<price>[\d,]{5,})\s*OTR", re.I)

#: The specification rows. **Two templates, one set of patterns.**
#:
#: The older template shouts its labels and pads them — `OVERALL LENGTH`, `OVERALL HEIGHT
#: (EXC TV AERIAL)` — while the newer writes `Length` and `Height`. Each pattern therefore
#: anchors on the word both templates share and makes the padding optional, rather than
#: the adapters having to know which template a page is on.
#:
#: `BELTS` is the belted-travel-seat count and `BERTHS` the sleeping count, named
#: unambiguously — unlike Pilote, where the word "Berth" meant a seat.
#:
#: **Every pattern takes the first figure it finds, and that is the settled base-vehicle
#: rule doing its work.** The newer template prints two weight columns, `Manual` then
#: `Auto`; the older prints two chassis, 3500 kg then 3650 kg; Benivan adds a `(Pop Top)`
#: row after the plain one. The first figure is the base in all three cases, and it is the
#: vehicle the quoted OTR price actually buys.
FIELDS: dict[str, re.Pattern[str]] = {
    "berths": re.compile(r"\bBERTHS\s+(\d+)", re.I),
    "seats": re.compile(r"\bBELTS\s+(\d+)", re.I),
    "length": re.compile(r"\bLENGTH\s+(\d+)\s*mm", re.I),
    "width": re.compile(r"\bWIDTH \(MIRRORS FOLDED\)\s+(\d+)\s*mm", re.I),
    "height": re.compile(r"\bHEIGHT\s*(?:\([^)]*\))?\s*(\d+)\s*mm", re.I),
    "mtplm": re.compile(r"\bMTPLM\s+(\d+)\s*kg", re.I),
    "mro": re.compile(r"\bMIRO\s+(\d+)\s*kg", re.I),
    "payload": re.compile(
        r"\bMAX USER PAYLOAD\s*(?:\([^)]*\))?\s*(?:Manual\s+)?(\d+)\s*kg", re.I
    ),
}

#: A payload row that names the chassis it belongs to, in the older template.
#:
#: `MAX USER PAYLOAD (3500KG CHASSIS) Manual 764kg / Auto 724kg` — one row per chassis
#: option. Two rows mean two independent routes to the same mass in running order, which
#: is the only self-check the older template offers. See `implied_mro`.
CHASSIS_PAYLOAD = re.compile(
    r"\bMAX USER PAYLOAD \((?P<chassis>\d+)\s*KG CHASSIS\)\s*(?:Manual\s+)?"
    r"(?P<payload>\d+)\s*kg",
    re.I,
)

_TAGS = re.compile(r"(?is)<(script|style)\b.*?</\1>")


def plain_text(page: str) -> str:
    """The page as one line, tags replaced by a single space and entities resolved."""
    stripped = re.sub(r"<[^>]+>", " ", _TAGS.sub(" ", page))
    return re.sub(r"\s+", " ", html.unescape(html.unescape(stripped))).strip()


def field(body: str, key: str) -> int | None:
    """One specification figure from a layout block, or `None` where it is absent."""
    match = FIELDS[key].search(body)
    return int(match.group(1)) if match else None


def price(body: str) -> int | None:
    """The on-the-road price from a layout block. Marquis set it, being the seller."""
    match = PRICE.search(body)
    return int(match.group("price").replace(",", "")) if match else None


#: How far two routes to the same mass may differ before it stops being a rounding.
#:
#: **Chosen from what a misread would look like, not from the vehicle's tolerance.** The
#: fault worth catching is a figure taken from the wrong column, and the two columns are
#: the manual and the automatic, which sit exactly 40 kg apart in MIRO on every Benimar
#: layout that prints both. So the band has to be comfortably under 40. It is not the
#: ±5% the pages themselves quote: that is a manufacturing tolerance on a real vehicle,
#: not a licence for two printed figures to disagree.
TOLERANCE_KG = 10


def base_mro_routes(body: str) -> list[int]:
    """The mass in running order as the **recorded** figures imply it, by every route.

    **This is the self-check the Mobilvetta survey concluded did not exist**, and it does
    — it was only absent from the one template that survey saw. The newer template prints
    MIRO outright beside MTPLM and payload, so `MTPLM - payload` is a second, independent
    route to a printed figure, and a value read out of the automatic column instead of the
    manual one fails to close by about 40 kg.

    Only the base column, because these are the figures that reach FMLV. What the other
    chassis and the automatic column say is corroboration — see `chassis_mro_routes`.
    """
    values: list[int] = []
    published = field(body, "mro")
    if published is not None:
        values.append(published)
    mtplm, payload = field(body, "mtplm"), field(body, "payload")
    if mtplm is not None and payload is not None:
        values.append(mtplm - payload)
    return values


def chassis_mro_routes(body: str) -> list[int]:
    """The same mass as each **chassis option's** payload row implies it, older template.

    `MAX USER PAYLOAD (3500KG CHASSIS) Manual 764kg` and its 3650 kg sibling are two routes
    to one number, and on the Primero page they are the only check there is — nothing else
    on it prints a MIRO.

    These corroborate rather than decide. Benimar's own Primero 282 row disagrees with
    itself by 50 kg, in the 3650 kg chassis figure, which is **not a figure this pipeline
    records**: the payload it publishes for the heavier chassis rises 100 kg where the
    chassis rises 150, while every other Primero moves both together. So a disagreement
    here is narrated for a human and never used to drop a real vehicle.
    """
    return [
        int(match.group("chassis")) - int(match.group("payload"))
        for match in CHASSIS_PAYLOAD.finditer(body)
    ]


def find_range_urls(
    index_html: str,
    *,
    brand: str,
    wanted: tuple[str, ...],
    excluded: frozenset[str] = frozenset(),
) -> list[str]:
    """Every current range page for one brand, in index order, minus the excluded ones.

    `wanted` are range keys from the adapter's `DEFAULT_RANGES`, matched against the slug
    so `--range` can select one; `excluded` are whole pages a brand has ruled out.
    """
    urls: list[str] = []
    for match in RANGE_HREF.finditer(index_html):
        slug = match.group("slug").lower()
        if not slug.startswith(f"{brand}-") or slug in excluded:
            continue
        if wanted and not any(f"{brand}-{key}-" in slug for key in wanted):
            continue
        url = f"{BASE_URL}/{slug}"
        if url not in urls:
            urls.append(url)
    return urls


#: A layout's `Bed Sizes` list, which runs to the footnote or the engine-and-price line.
BED_SECTION = re.compile(r"Bed Sizes\s+(?P<beds>.*?)(?=#|[A-Z][A-Z\s.]*ENGINE|$)", re.S)

#: One bed in that list: a name, then the size that ends it.
#:
#: The entries are run together, so the split is on the size rather than on any separator.
#: The name may not contain a digit or a quote mark, which is what stops the previous
#: entry's imperial measurement being read as part of the next bed's name.
#:
#: **The size has to be taken loosely, because the brands write it four ways:**
#:
#: | | |
#: |---|---|
#: | `Double Drop Down Bed 1400mm × 1900mm` | Benimar, both figures suffixed |
#: | `Single Rear Bed 2 x 800mm × 2100mm` | Benimar, a count in front |
#: | `DROP DOWN BED 1900 x 810mm` | Elnagh, only the last figure suffixed |
#: | `DOUBLE REAR BED 1300 x 1100 x 1900mm` | Elnagh, three dimensions |
#:
#: So everything up to the first `mm` is swallowed. Requiring `<digits>mm` immediately
#: after the name found none of Elnagh's four.
#:
#: **The letter `x` is deliberately allowed in a name** even though it separates the
#: figures: excluding it turned `FIXED REAR BED` into `ED REAR BED`. The digits separate.
BED_ENTRY = re.compile(r"""(?P<name>[^|×#\d’'"]+?Bed)\s+[\dx×\s]*\d\s*mm""", re.I)

#: A parenthetical naming the layouts a line of equipment applies to.
#:
#: The content must be **nothing but layout codes** and the words that join them, so
#: `(579 and 573 only)` and `(excl 286)` match while `(MIRRORS FOLDED)`, `(3500KG CHASSIS)`
#: and `(230v socket)` do not. See `lines_for_layout`.
LAYOUT_QUALIFIER = re.compile(
    r"\(\s*(?P<qualifier>(?:excl\.?|only|and|or|[,/&\s]|\d{2,4})+?)\s*\)", re.I
)


def bed_lines(body: str) -> list[str]:
    """The beds one layout's block names, as lines `habitation` can read.

    **`Optional` beds are dropped.** Both Benivan layouts list an `Optional Elevating Roof
    Bed`, which is a pop-top the buyer may not have bought — the settled rule against
    reading a paid option as standard equipment. `habitation.usable_lines` does not catch
    this one because the page never prices it or writes `Option:`.
    """
    section = BED_SECTION.search(body)
    if section is None:
        return []
    names = [
        re.sub(r"\s+", " ", match.group("name")).strip()
        for match in BED_ENTRY.finditer(section.group("beds"))
    ]
    return [name for name in names if not name.lower().startswith("optional")]


def equipment_lines(page: str) -> list[str]:
    """The range's standard-equipment list, minus anything naming a bed.

    **A Marquis page is a range, not a layout**, so its equipment list describes up to six
    vehicles at once. That is fine for a fridge or a heater, which the whole range shares,
    and wrong for beds — so bed copy is excluded here and taken per layout from the block's
    own `Bed Sizes` list instead.
    """
    return [
        line
        for line in habitation.list_items(page)
        if "bed" not in line.lower() and "bunk" not in line.lower()
    ]


def lines_for_layout(lines: Iterable[str], model: str) -> list[str]:
    """The equipment lines that apply to one layout, by the list's own parentheses.

    **Not every line in a range's equipment list applies to every layout in it**, and on
    Elnagh's Baron page the qualifier decides the answer rather than shading it:

    ```
    Separate shower and toilet compartment (579 and 573 only)
    Combined shower and toilet compartment (530 and 560 only)
    ```

    Read range-wide, whichever line came first would settle `shower_toilet_separated` for
    all four. FMLV holds **No, No, Yes, Yes** across 530/560/573/579, which is the page read
    per layout — so this is not a refinement, it is the difference between right and wrong.

    Benimar qualifies the same way with `(excl 286)` and `(286)` on its two fridge sizes,
    where both happen to be fridge-freezers and the fault would have gone unnoticed.

    A line with no qualifier applies to everything, which is nearly all of them.
    """
    kept: list[str] = []
    for line in lines:
        match = LAYOUT_QUALIFIER.search(line)
        if match is None:
            kept.append(line)
            continue
        codes = re.findall(r"\d{2,4}", match.group("qualifier"))
        if not codes:
            kept.append(line)
            continue
        excluded = bool(re.search(r"\bexcl", match.group("qualifier"), re.I))
        if (model not in codes) if excluded else (model in codes):
            kept.append(line)
    return kept


def range_and_model(
    heading: str, prefixes: tuple[tuple[str, str], ...]
) -> tuple[str, str] | None:
    """The FMLV range and model from a block heading, or `None` if it names no known range.

    `prefixes` maps a heading prefix to an FMLV range name and must be ordered **longest
    first**, so `KEA KOMPAKT` is not read as `KEA`.

    **The last occurrence of the prefix wins, not the first.** The first block on every
    page has the page's own banner welded to its front:

    | captured heading | model |
    |---|---|
    | `MOBILVETTA K.YACHT A CLASS MOTORHOME RANGE K.YACHT 59` | `59` |
    | `MOBILVETTA ADMIRAL ADMIRAL K 6.3` | `K 6.3` |
    | `K.YACHT 86` | `86` |

    Taking the first match gave models like `A CLASS MOTORHOME RANGE K.YACHT 59`, which
    still *matched* their FMLV rows on token overlap — so the run looked almost right,
    with one product orphaned and three carrying nonsense as their model.
    """
    name = re.sub(r"\s+", " ", heading).strip()
    for prefix, fmlv_range in prefixes:
        matches = list(re.finditer(rf"\b{re.escape(prefix)}\s+(?=\S)", name, re.I))
        if not matches:
            continue
        model = re.sub(r"\s+", " ", name[matches[-1].end() :]).strip()
        if model:
            return fmlv_range, model
    return None
