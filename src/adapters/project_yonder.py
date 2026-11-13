"""Project Yonder — three 4x4 Mercedes Sprinter campervans, read from a CMS payload.

`docs/adapters/project-yonder.md` is the survey; this is what it decided.

**The site looks like it publishes nothing and in fact publishes a typed record of
everything it shows.** Every page is Remix-rendered over a Storyblok CMS and ships its
whole content tree inline as `window.__remixContext`, so the figures that appear on screen
as styled tiles arrive as `{"big_text": "4.1T", "small_text": "GVW"}`. Nothing needs a
browser, nothing needs OCR, and there is no PDF anywhere on the site to want one.

Four things make this adapter unlike the others.

* **The FAQ page is a data source, and its answers are invisible without the payload.**
  They sit in collapsed accordions that render empty, so a fetch that reads the rendered
  text finds fourteen questions and not one answer. The payload has them, and they are the
  only place Project Yonder publish a **width or a height at all** — see `parse_faq`.

* **The one cross-check available is the length, held by two pages that are edited
  separately.** No mass in running order and no payload is published for anything, so the
  `payload == MTPLM - MRO` reconciliation that guards most adapters does not exist here.
  What does exist is a model page saying `6.0M LENGTH` and an FAQ answer saying "Our MWB
  campervan is 6m long", maintained months apart. `_reconciles` requires them to agree,
  which is what licenses taking the width and height off the FAQ for a model whose page
  never mentions either.

* **Project Yonder's own two pages disagree about the gross weight and about the price**,
  and the model page wins both — a model page sells a vehicle so somebody maintains it,
  where an FAQ is written once and left. Settled by Francis on 13 November 2026 and now a
  cross-manufacturer rule; see `docs/adapters/README.md`. Both are still narrated on every
  run, as applied rather than as questions, so that a *new* disagreement surfaces the same
  way. See `_narrate_conflicts`.

* **The prose is marketing and has to be cut before it is read.** Project Yonder write
  their options in running sentences — "Optional belted passenger seats, cosy kids bunk
  beds or even an elevating pop-top roof" — which the shared `habitation._OPTION` filter
  cannot see, because it keys on a price or on `option:` with a colon. Read whole, that one
  sentence asserts fixed bunks on a van that has none. `_standard_prose` truncates each
  sentence at the word that turns it into an offer; everything before that word is a
  fitting, everything after is a catalogue.

**No mass in running order, no payload and no berth or belt count above the published
minimum is ever emitted**, because none of it is published. Project Yonder are not in FMLV
at all, so there is no baseline here to protect — but there is also nothing to fall back
on, and a figure this adapter invents is a figure nobody will ever catch.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from . import gearbox, habitation
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

__all__ = [
    "BASE_URL",
    "DEFAULT_RANGES",
    "EXPECTED_PRODUCTS",
    "FAQ_URL",
    "HOME_URL",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "Faq",
    "RosterCard",
    "YonderProduct",
    "collect",
    "parse_faq",
    "parse_model_page",
    "parse_roster",
    "remix_story",
    "spec_tiles",
]

BASE_URL = "https://www.projectyonder.co.uk"
HOME_URL = f"{BASE_URL}/"
FAQ_URL = f"{BASE_URL}/faqs-and-contact"

#: **Chosen, not confirmed.** Project Yonder have no row in any FMLV export, so unlike
#: every other adapter there is no `manufacturer` string to match byte-for-byte — this is
#: the name the first upload will create. It is their own name for themselves, used
#: throughout their site and in the Mercedes-Benz Vans quotation on their homepage.
#:
#: **Check it against the NCC supplier dropdown before the first upload**, the way
#: `landseer` had to: the NCC spell that company `Landseer Leisure` where FMLV holds
#: `Landseer`, and the two keys must not be crossed.
MANUFACTURER = "Project Yonder"
MANUFACTURER_DISPLAY_NAME = "Project Yonder"

#: Three campervans. Their homepage shows four cards and the fourth is the Gear Shop.
EXPECTED_PRODUCTS = 3

#: The settled campervan threshold, shared with `aura`, `auto_sleepers`, `auto_trail` and
#: `landseer`. Project Yonder clear it by 600mm.
HIGH_TOP_ABOVE_MM = 2300


# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #

#: Each model's slug mapped to `(range, model, what the homepage card must say)`.
#:
#: **The range names are the prose spelling, not the nav's.** Project Yonder style their
#: navigation in capitals — `NOMAD`, `FREEDOM 4X`, `UTILITY` — and the Storyblok story
#: names copy that styling, but their own writing does not: the blog post is "Freedom 4X
#: Utility: From Workday to Wilderness" and the slug is `freedom-4x-utility`. `UTILITY`
#: alone would file a Freedom 4X variant as an unrelated range and lose the only thing
#: that explains what it is.
#:
#: **The model is the wheelbase**, following `landseer`, because the alternative is a
#: product whose range and model are the same word — the doubling Nova forces, which
#: Francis then unpicks by hand after every upload. The inch figure Project Yonder print
#: beside it (`140"`, `170"`) stays out of the value and goes in the provenance: a
#: straight double-quote in a CSV cell is a needless hazard for one digit of information.
MODELS: dict[str, tuple[str, str, str]] = {
    "nomad": ("Nomad", "MWB", "NOMAD"),
    "freedom-4x": ("Freedom 4X", "LWB", "FREEDOM 4X"),
    "freedom-4x-utility": ("Freedom 4X Utility", "LWB", "UTILITY"),
}

#: `(key, label)` for `--range`, in the order the homepage lists them.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = tuple(
    (slug, names[0]) for slug, names in MODELS.items()
)

#: Which FAQ dimension row belongs to which model, by the wheelbase used as the model
#: name. `parse_faq` returns the rows keyed this way, and `_reconciles` proves the join.
_WHEELBASE_OF_FAQ_ROW = {"MWB": "MWB", "LWB": "LWB"}

#: Homepage cards that sell something other than a campervan. Watched every run, so that
#: one disappearing is noticed rather than silently treated as a missing model.
NOT_A_MODEL: dict[str, str] = {
    "GEAR SHOP": (
        "the accessories shop at shop.projectyonder.co.uk — awnings, racks and storage, "
        "no vehicle. It is the only homepage card whose link is an external URL rather "
        "than a Storyblok story, which is how it is told from a model without naming it"
    ),
}

#: **The Nomad page has not finished being renamed, and says so in its own payload.** Its
#: SEO title is still `Freedom 4X - The Ultimate AWD Motorhome`, its hero image is
#: `20250205_py_freedom-4x_mwb_417_web_v1.jpg` and its body copy opens "Freedom knows no
#: limits"; only the story name, the slug and the nav say `NOMAD`. Narrated every run
#: because it is the evidence that the Nomad IS the renamed 140" Freedom 4X rather than a
#: fourth vehicle — which is also what the FAQ, written before the rename, still calls it.
_RENAMED_FROM = {"nomad": "Freedom 4X 140\" (MWB)"}


# --------------------------------------------------------------------------- #
# Reading the payload
# --------------------------------------------------------------------------- #

#: The assignment that opens the inlined CMS payload. Everything the page renders is in
#: the JSON object that follows it, so the adapter decodes from here rather than matching
#: the page's markup — a styled tile has no stable class, and its content does.
_REMIX_CONTEXT = re.compile(r"window\.__remixContext\s*=\s*", re.I)

#: Where the page's own story sits in the payload. A content page uses the catch-all
#: route; the homepage has a route of its own and puts its story one level up.
_STORY_ROUTES = ("routes/$", "routes/index")


def _read(path: Path) -> str:
    """The page's text.

    Project Yonder serve `charset=utf-8` and mean it — unlike `dreamer`, whose pages
    declare `iso-8859-1` and carry real high bytes. Decoded strictly so that a site that
    changes its mind fails loudly here instead of writing U+FFFD into a snippet, which
    then kills the run on a Windows console rather than where the problem is.
    """
    return path.read_bytes().decode("utf-8")


def remix_story(page: str) -> dict:
    """The Storyblok story this page renders, out of the inlined payload.

    Raises `ValueError` when the payload is absent or holds no story: that means Project
    Yonder have moved off Remix or off Storyblok, and every figure in this adapter comes
    from here, so there is nothing to carry on with.
    """
    match = _REMIX_CONTEXT.search(page)
    if match is None:
        raise ValueError("the page carries no window.__remixContext payload")
    try:
        payload, _end = json.JSONDecoder().raw_decode(page, match.end())
    except ValueError as error:  # pragma: no cover - defensive
        raise ValueError(f"the __remixContext payload would not decode: {error}") from error

    loaded = payload.get("state", {}).get("loaderData", {})
    if not isinstance(loaded, dict):
        raise ValueError("the payload carries no loaderData")

    for route in _STORY_ROUTES:
        entry = loaded.get(route)
        if isinstance(entry, dict) and isinstance(entry.get("story"), dict):
            return entry["story"]
        # The homepage's story is the route's own content, with the page body at `root`.
        if route == "routes/index" and isinstance(entry, dict) and entry.get("body"):
            return {"name": "", "slug": "", "published_at": "", "content": entry}
    raise ValueError(f"the payload holds no story under any of {_STORY_ROUTES}")


def _blocks(node: object, component: str) -> list[dict]:
    """Every block of one component type, anywhere in the story's content tree.

    Walked rather than indexed because the CMS lets an editor reorder, nest or duplicate
    a block freely — the Freedom 4X page carries two separate `callout_specs` groups, and
    which one holds the weight is not fixed.
    """
    found: list[dict] = []
    if isinstance(node, dict):
        if node.get("component") == component:
            found.append(node)
        for value in node.values():
            found.extend(_blocks(value, component))
    elif isinstance(node, list):
        for value in node:
            found.extend(_blocks(value, component))
    return found


def _rich_text(node: object, out: list[str] | None = None) -> str:
    """The readable text of a Storyblok rich-text field, in document order."""
    collected: list[str] = [] if out is None else out
    if isinstance(node, dict):
        if node.get("type") == "text" and isinstance(node.get("text"), str):
            collected.append(node["text"])
        for value in node.values():
            _rich_text(value, collected)
    elif isinstance(node, list):
        for value in node:
            _rich_text(value, collected)
    return " ".join(" ".join(collected).split()) if out is None else ""


def spec_tiles(story: dict) -> dict[str, str]:
    """`{"GVW": "4.1T", "LENGTH": "7.0M", ...}` — every `callout_spec` on the page.

    Keyed on the label rather than on position, because the Freedom 4X and Utility pages
    carry eight tiles in two groups and the Nomad carries four, and a positional read
    would hand the Nomad's GVW to whatever sat fourth that week.
    """
    tiles: dict[str, str] = {}
    for tile in _blocks(story.get("content", {}), "callout_spec"):
        label = str(tile.get("small_text") or "").strip().upper()
        value = str(tile.get("big_text") or "").strip()
        if label and value:
            tiles.setdefault(label, value)
    return tiles


# --------------------------------------------------------------------------- #
# Cutting the marketing prose down to a specification
# --------------------------------------------------------------------------- #

#: The word that turns the rest of a sentence into a catalogue.
#:
#: **This exists because the shared filter cannot catch prose.** `habitation._OPTION` keys
#: on a price or on `option:` with a colon, which is how a spec sheet writes an extra.
#: Project Yonder have no spec sheet; they have paragraphs, and they put the standard
#: fitting and the paid upgrade in one sentence:
#:
#:     "...a two ring induction hob plus a 90L fridge freezer & a variety of additional
#:     cooking options such as air fryer, microwave & coffee machine..."
#:
#: The fridge is fitted and the microwave is a price list. Read whole, the sentence asserts
#: a microwave in every van. Read to the marker and no further, it asserts the fridge and
#: says nothing about a microwave, which is the truth of it.
#:
#: `or even` is here for one sentence and earns its place: "Optional belted passenger
#: seats, cosy kids bunk beds or even an elevating pop-top roof". Without it that sentence
#: put `fixed_bunks` on all three vans — the same trap as `robeta`'s factory-only pages,
#: where a fridge came out of a sentence about other manufacturers' vans.
_OPTION_MARKER = re.compile(
    r"\b(?:optional(?:ly)?|options? such as|additional [a-z ]{0,24}options?"
    r"|or even|upgrade[sd]?|add[- ]ons?|extras?|available as|can be added)\b",
    re.I,
)

#: A sentence boundary. Deliberately crude: these are marketing paragraphs, not prose that
#: needs parsing, and the cost of splitting one sentence in two is nothing.
_SENTENCE = re.compile(r"(?<=[.!?])\s+")

#: Below this, what survives the truncation is a fragment rather than a statement — "Our
#: family friendly" is what is left of a sentence that was entirely about upgrades.
_MINIMUM_WORDS = 4


def _standard_prose(text: str) -> list[str]:
    """The part of each sentence that describes the van as built.

    Each sentence is cut at the first `_OPTION_MARKER` and whatever precedes it is kept.
    A sentence whose marker is at the start therefore disappears, which is correct: it was
    an offer from the first word.
    """
    kept: list[str] = []
    for sentence in _SENTENCE.split(text):
        marker = _OPTION_MARKER.search(sentence)
        trimmed = (sentence[: marker.start()] if marker else sentence).strip(" ,;&-—")
        if len(trimmed.split()) >= _MINIMUM_WORDS:
            kept.append(trimmed)
    return kept


#: The blocks that carry prose about the vehicle. `specs_section` is the Freedom 4X's
#: eight-part feature list and `key_info_block` the full-width panels; the rest of the
#: page is headings, galleries and a colour picker.
_PROSE_BLOCKS = ("specs_section", "key_info_block", "two_column_copy_block")


def _prose_lines(story: dict) -> list[str]:
    """Every standard-equipment statement on the page, options already cut away."""
    lines: list[str] = []
    content = story.get("content", {})
    for component in _PROSE_BLOCKS:
        for block in _blocks(content, component):
            for key in ("details", "copy", "text"):
                text = _rich_text(block.get(key)) if block.get(key) else ""
                if text:
                    lines.extend(_standard_prose(text))
    return lines


# --------------------------------------------------------------------------- #
# The roster
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RosterCard:
    """One campervan the homepage offers, with the wheelbase it prints beneath it."""

    slug: str
    title: str
    subtitle: str


#: `MEDIUM WHEEL BASE 140"` -> `MWB`; `LONG WHEEL BASE 170"` -> `LWB`. The inch figure is
#: captured so the provenance can quote it.
_WHEELBASE = re.compile(r"\b(MEDIUM|LONG|SHORT)\s+WHEEL\s*BASE\s*(\d{2,3})?", re.I)

_WHEELBASE_ABBREVIATION = {"short": "SWB", "medium": "MWB", "long": "LWB"}


def parse_roster(home: str) -> tuple[list[RosterCard], list[str]]:
    """`(the campervan cards, the other cards)` from the homepage.

    A card linking to a Storyblok story is a model page; the Gear Shop links to an
    external URL, which is what separates them without hardcoding its name. Both halves
    are returned so `collect` can narrate a card it has never seen before — a fourth
    campervan would appear here first, and nowhere else on the site.
    """
    story = remix_story(home)
    models: list[RosterCard] = []
    others: list[str] = []
    for card in _blocks(story.get("content", {}), "cta_image_block"):
        title = str(card.get("title") or "").strip()
        subtitle = str(card.get("subtitle") or "").strip()
        link = card.get("link") if isinstance(card.get("link"), dict) else {}
        slug = str(link.get("cached_url") or "").strip().strip("/")
        if link.get("linktype") == "story" and slug:
            models.append(RosterCard(slug=slug, title=title, subtitle=subtitle))
        elif title:
            others.append(title)
    return models, others


def wheelbase_of(card: RosterCard) -> tuple[str | None, str | None]:
    """`(MWB|LWB, the inch figure)` read off a card's subtitle."""
    match = _WHEELBASE.search(card.subtitle)
    if match is None:
        return None, None
    return _WHEELBASE_ABBREVIATION.get(match.group(1).lower()), match.group(2)


# --------------------------------------------------------------------------- #
# The FAQ, which is the only place a width or a height is published
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Faq:
    """What the FAQ page answers, insofar as it answers anything about a vehicle."""

    #: `{"MWB": (6000, 2100, 2900), ...}` — length, width, height in millimetres.
    dimensions: dict[str, tuple[int, int, int]] = field(default_factory=dict)
    #: The gross weight in kilograms, as the FAQ states it for the whole range.
    gross_weight_kilograms: int | None = None
    #: The prices the FAQ lists, verbatim, which do NOT match the model pages.
    price_lines: list[str] = field(default_factory=list)
    #: The make the FAQ names for every van.
    base_vehicle: str | None = None
    #: The answer that settles the gearbox for the whole range.
    automatic_line: str | None = None
    #: Each answer kept whole, for quoting.
    answers: dict[str, str] = field(default_factory=dict)
    published: str = ""

    def prices_for(self, wheelbase: str) -> list[str]:
        """The FAQ's priced lines for one wheelbase, by the heading they sit under.

        A heading that names no wheelbase matches nothing rather than everything: quoting
        the long van's price against the short one would turn a real conflict into a
        wrong one.
        """
        marker = f"({wheelbase.upper()})"
        return [line for line in self.price_lines if marker in line.upper()]


#: "Our MWB campervan is 6m long x 2.1m wide x 2.9m high."
_DIMENSION_ROW = re.compile(
    r"\b(MWB|LWB|SWB)\b[^.]*?([\d.]+)\s*m\s*long\s*x\s*([\d.]+)\s*m\s*wide"
    r"\s*x\s*([\d.]+)\s*m\s*high",
    re.I,
)

#: "Our vans have a Gross Vehicle Weight of 4.4T".
_FAQ_GROSS_WEIGHT = re.compile(r"gross vehicle weight of\s*([\d.]+)\s*(T|kg)\b", re.I)

#: The cost answer is a heading per wheelbase followed by a priced line per drivetrain.
#: Both halves are needed: `AWD model from £169,725 OTR` on its own does not say which van
#: it prices, and the headings are the only place the FAQ still uses the old names.
_FAQ_PRICE_HEADING = re.compile(r"Starting price\s+([^:]{3,60}):", re.I)
_FAQ_PRICE_LINE = re.compile(r"((?:RWD|AWD)\s+model from\s*£\s?[\d,]{4,}(?:\s*OTR)?)", re.I)


def _faq_prices(answer: str) -> list[str]:
    """`["Freedom 4X 140\" (MWB) — RWD model from £152,775 OTR", ...]`.

    Each priced line is attached to the heading above it, because the headings are what
    make the conflict legible: they still name the 140" van `Freedom 4X`, which is the
    Nomad, and they price an RWD variant that has no model page at all.
    """
    marks = [(m.start(), "heading", m.group(1)) for m in _FAQ_PRICE_HEADING.finditer(answer)]
    marks += [(m.start(), "price", m.group(1)) for m in _FAQ_PRICE_LINE.finditer(answer)]
    lines: list[str] = []
    heading = ""
    for _position, kind, value in sorted(marks):
        tidied = " ".join(value.split())
        if kind == "heading":
            heading = tidied
        else:
            lines.append(f"{heading} — {tidied}" if heading else tidied)
    return lines

_FAQ_MAKE = re.compile(r"\b(Mercedes-Benz|Mercedes)\b", re.I)


def _metres_to_mm(value: str) -> int:
    return round(float(value) * 1000)


def parse_faq(page: str) -> Faq:
    """The vehicle facts buried in the FAQ accordions.

    **Nothing here renders.** The answers are collapsed panels whose text is supplied by
    the CMS payload and written into the DOM only when a visitor clicks, so a reader —
    human or otherwise — who works from the rendered page finds fourteen headings and no
    answers at all. This is where the width and the height come from, and they are
    published nowhere else on the site.
    """
    story = remix_story(page)
    answers: dict[str, str] = {}
    for item in _blocks(story.get("content", {}), "accordion_item"):
        title = str(item.get("title") or "").strip()
        body = _rich_text(item.get("content"))
        if title and body:
            answers[title] = body

    dimensions: dict[str, tuple[int, int, int]] = {}
    gross: int | None = None
    prices: list[str] = []
    make: str | None = None
    automatic: str | None = None

    for title, body in answers.items():
        for row in _DIMENSION_ROW.finditer(body):
            wheelbase = row.group(1).upper()
            dimensions[wheelbase] = (
                _metres_to_mm(row.group(2)),
                _metres_to_mm(row.group(3)),
                _metres_to_mm(row.group(4)),
            )
        if gross is None and (weight := _FAQ_GROSS_WEIGHT.search(body)):
            figure = float(weight.group(1))
            gross = round(figure * 1000) if weight.group(2).lower() == "t" else round(figure)
        if "cost" in title.lower():
            prices = _faq_prices(body)
        if make is None and (named := _FAQ_MAKE.search(body)) and "convert" in title.lower():
            make = named.group(1)
        if automatic is None and "automatic" in title.lower() and "automatic" in body.lower():
            automatic = body

    return Faq(
        dimensions=dimensions,
        gross_weight_kilograms=gross,
        price_lines=prices,
        base_vehicle=make,
        automatic_line=automatic,
        answers=answers,
        published=str(story.get("published_at") or ""),
    )


# --------------------------------------------------------------------------- #
# A model page
# --------------------------------------------------------------------------- #


@dataclass
class YonderProduct:
    """One campervan, as its own page and the FAQ between them describe it."""

    slug: str
    manufacturer_range: str
    model: str
    source_url: str
    story_name: str
    published: str
    seo_title: str
    wheelbase_inches: str | None = None

    rrp_pounds: int | None = None
    price_title: str = ""
    price_text: str = ""

    berths: int | None = None
    berths_text: str = ""
    travel_seats: int | None = None
    belts_text: str = ""

    mh_length_mm: int | None = None
    length_text: str = ""
    mh_width_mm: int | None = None
    mh_height_mm: int | None = None
    dimensions_from_faq: str = ""

    mtplm_kilograms: int | None = None
    gross_weight_text: str = ""

    base_vehicle: str | None = None
    base_vehicle_line: str = ""
    automatic_line: str = ""

    prose: list[str] = field(default_factory=list)
    body_type: BodyType | None = None

    @property
    def label(self) -> str:
        return f"{self.manufacturer_range} {self.model}"


#: `6.0M` -> 6000. Project Yonder publish one decimal and no more.
_TILE_METRES = re.compile(r"^([\d.]+)\s*M$", re.I)

#: `4.1T` -> 4100.
_TILE_TONNES = re.compile(r"^([\d.]+)\s*T$", re.I)

#: `2-4` -> 2. See `_lower_of_range`.
_TILE_RANGE = re.compile(r"^(\d+)\s*(?:[-–]\s*(\d+))?$")

#: `£192,625` or `£194,775*`.
_PRICE = re.compile(r"£\s?([\d,]{4,})")


def _lower_of_range(value: str) -> int | None:
    """The lower end of `2-4`.

    The settled rule for berths — "Sleeps 2-4" is a 2-berth van whose other two berths
    need options — and the same arithmetic happens to be right for the belts here for a
    different reason: Project Yonder's own feature list says "Optional belted passenger
    seats", so two is the pair in the Sprinter's cab and the rest are a price list.
    """
    match = _TILE_RANGE.match(value.strip())
    return int(match.group(1)) if match else None


def parse_model_page(page: str, slug: str, url: str) -> YonderProduct:
    """One model page's figures, from its tiles, its pricing block and its prose."""
    story = remix_story(page)
    manufacturer_range, model, _card = MODELS[slug]
    tiles = spec_tiles(story)

    seo = story.get("content", {}).get("seo") or {}
    product = YonderProduct(
        slug=slug,
        manufacturer_range=manufacturer_range,
        model=model,
        source_url=url,
        story_name=str(story.get("name") or ""),
        published=str(story.get("published_at") or ""),
        seo_title=str(seo.get("title") or "") if isinstance(seo, dict) else "",
    )

    if (berths := tiles.get("BERTHS")) is not None:
        product.berths = _lower_of_range(berths)
        product.berths_text = berths
    if (belts := tiles.get("BELTS")) is not None:
        product.travel_seats = _lower_of_range(belts)
        product.belts_text = belts
    if (length := tiles.get("LENGTH")) is not None:
        product.length_text = length
        if metres := _TILE_METRES.match(length.strip()):
            product.mh_length_mm = _metres_to_mm(metres.group(1))
    if (gross := tiles.get("GVW")) is not None:
        product.gross_weight_text = gross
        if tonnes := _TILE_TONNES.match(gross.strip()):
            product.mtplm_kilograms = round(float(tonnes.group(1)) * 1000)

    for block in _blocks(story.get("content", {}), "pricing_block"):
        text = str(block.get("price") or "")
        if found := _PRICE.search(text):
            product.rrp_pounds = int(found.group(1).replace(",", ""))
            product.price_title = str(block.get("title") or "").strip()
            product.price_text = text.strip()
            break

    product.prose = _prose_lines(story)
    if make := _FAQ_MAKE.search(" ".join(product.prose)):
        product.base_vehicle = make.group(1)
        product.base_vehicle_line = next(
            (line for line in product.prose if _FAQ_MAKE.search(line)), ""
        )
    if found := gearbox.automatic_available_from(product.prose):
        product.automatic_line = found[1]
    return product


# --------------------------------------------------------------------------- #
# The self-check
# --------------------------------------------------------------------------- #


def _reconciles(product: YonderProduct, faq: Faq) -> tuple[bool, str]:
    """Whether the model page's length and the FAQ's agree for this wheelbase.

    **This is the only cross-check the source offers**, and it is weaker than the mass
    arithmetic most adapters get. It is worth having anyway for one specific reason: the
    width and the height are taken from an FAQ row chosen by wheelbase, and nothing else
    proves that row belongs to this vehicle. If the LWB row were read for the Nomad, this
    is what would catch it — the Nomad's tile says 6.0M and the LWB row says 7m.

    The two pages are edited months apart (the Freedom 4X page in April 2026, the FAQ in
    July, the Nomad and Utility pages in September), so their agreeing is not a tautology.
    """
    row = _WHEELBASE_OF_FAQ_ROW.get(product.model)
    if row is None or row not in faq.dimensions:
        return True, (
            f"the FAQ publishes no dimensions for a {product.model}, so there is nothing "
            f"to check the {product.length_text or 'length'} tile against"
        )
    faq_length, _width, _height = faq.dimensions[row]
    if product.mh_length_mm is None:
        return True, f"no length tile to check against the FAQ's {faq_length:,}mm"
    if product.mh_length_mm != faq_length:
        return False, (
            f"the page tile says {product.mh_length_mm:,}mm and the FAQ's {row} row says "
            f"{faq_length:,}mm — one of the two pages is out of date and the width and "
            f"height would be taken from the wrong row"
        )
    return True, (
        f"{product.mh_length_mm:,}mm on the tile matches the FAQ's {row} row, which is "
        f"what licenses taking the width and height from it"
    )


# --------------------------------------------------------------------------- #
# Building the product
# --------------------------------------------------------------------------- #

#: Project Yonder convert panel vans that "roll straight off Mercedes-Benz production line"
#: — their FAQ's words — and the Caravan and Motorhome Club awarded the Freedom 4X in the
#: category "Van Conversions with a fixed roof over 6 metres". A fixed-roof panel van
#: conversion 2,900mm tall is a campervan high top under the settled 2,300mm rule, and
#: nothing about that reading depends on the exact height being right.
_BODY_TYPE_REASON = (
    "a fixed-roof Mercedes-Benz Sprinter panel-van conversion at {height:,}mm, which "
    "clears the settled {threshold:,}mm campervan high-top threshold by {margin:,}mm. "
    "The pop-top roof Project Yonder mention is an option, so it does not make this an "
    "elevating-roof campervan"
)


def _build_extracted_motorhome(product: YonderProduct, faq: Faq) -> ExtractedMotorhome:
    """One product as a `Motorhome`, with the provenance a reviewer reads beside each field.

    Fields deliberately left with **no provenance, and so never proposed**:

    * `mro_kilograms` and `mh_payload_kilograms` — Project Yonder publish neither, for any
      model, anywhere on the site. They publish one gross weight and nothing to divide it,
      which is also why this adapter has no mass arithmetic to check itself against.
    * `sleeping_area`, `kitchen_location`, `lounge_location`, `bathroom_layout` and
      `bed_types` — settled only by a drawing, and Project Yonder publish no floorplan for
      any model, so there is not even a reviewer pointer to offer.
    * `microwave` — named once, inside "a variety of additional cooking options such as
      air fryer, microwave & coffee machine", which is a price list. Offering one is not
      fitting one.
    * `heating`, `refrigeration` and `shower_toilet_separated` on the **Nomad and the
      Utility**, whose pages carry no equipment prose at all. The Freedom 4X page names a
      Truma D6 E and a 90L fridge freezer; the other two name nothing, and the homepage's
      range-wide "gas-free habitation as standard" panel names no appliance. Asserting the
      Freedom 4X's kit on its siblings is the `robeta` mistake exactly.
    """
    features = habitation.features_from(product.prose)

    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.manufacturer_range,
        model=product.model,
        base_vehicle_manufacturer=fmlv_base_vehicle(product.base_vehicle or faq.base_vehicle),
        rrp_pounds=product.rrp_pounds,
        berths=product.berths,
        mh_passenger_seats_inc_driver=product.travel_seats,
        mtplm_kilograms=product.mtplm_kilograms,
        mh_length_mm=product.mh_length_mm,
        mh_width_mm=product.mh_width_mm,
        mh_height_mm=product.mh_height_mm,
        body_type=product.body_type,
        automatic_available=True if product.automatic_line or faq.automatic_line else None,
        # Habitation: findings, never proposals — see `docs/adapters/README.md`.
        heating=features["heating"].value if "heating" in features else None,
        refrigeration=(
            features["refrigeration"].value if "refrigeration" in features else None
        ),
        shower_toilet_separated=(
            features["shower_toilet_separated"].value
            if "shower_toilet_separated" in features
            else None
        ),
    )

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str, *, url: str | None = None) -> None:
        provenance[field_name] = Provenance(
            source_url=url or product.source_url,
            snippet=f"{product.label} — {snippet}",
        )

    wheelbase = (
        f'{product.model} {product.wheelbase_inches}"'
        if product.wheelbase_inches
        else product.model
    )
    record(
        "manufacturer_range",
        f"the CMS names this story {product.story_name!r} and the homepage card calls it "
        f"{MODELS[product.slug][2]!r}, at {wheelbase}. Recorded as "
        f"{product.manufacturer_range!r} because that is the spelling Project Yonder use "
        f"in their own writing rather than in their styled navigation",
    )
    record(
        "model",
        f"the homepage card prints {product.model} beneath the name; the wheelbase is the "
        f"model so that the product is not filed as "
        f"{product.manufacturer_range} {product.manufacturer_range}",
    )

    if motorhome.base_vehicle_manufacturer is not None:
        line = product.base_vehicle_line or (faq.answers.get("What vans do you convert?", ""))
        record(
            "base_vehicle_manufacturer",
            f"{line.strip()!r}. Recorded as {motorhome.base_vehicle_manufacturer!r}, the "
            f"abbreviated form FMLV uses for a base-vehicle maker",
        )

    if product.rrp_pounds is not None:
        record(
            "rrp_pounds",
            f"the model page's own pricing panel, {product.price_title!r} "
            f"{product.price_text!r}. Project Yonder sell direct with no importer and no "
            f"dealer network, so their headline figure is the guide price. "
            f"THE FAQ DISAGREES — it still prices this van as "
            f"{'; '.join(faq.prices_for(product.model)) or 'no figure'} — on a page last "
            f"published {faq.published[:10] or 'unknown'} against this one's "
            f"{product.published[:10] or 'unknown'}. SETTLED: the model page beats the "
            f"standing page (Francis, 13 November 2026)",
        )

    if product.berths is not None:
        record(
            "berths",
            f"the BERTHS tile reads {product.berths_text!r}. The lower figure is recorded "
            f"under the settled berth-range rule: the feature list on Project Yonder's "
            f"Freedom 4X page offers \"cosy kids bunk beds or even an elevating pop-top "
            f"roof\" as upgrades, so the berths above two need options",
        )
    if product.travel_seats is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"the BELTS tile reads {product.belts_text!r} and the Freedom 4X page's feature "
            f"list offers \"Optional belted passenger seats\", so two is the standard — the "
            f"Sprinter's cab pair. PROJECT YONDER NEVER SAY WHAT KIND OF BELT the optional "
            f"seats carry, and only three-point belts count as travel seats",
        )

    if product.mh_length_mm is not None:
        record(
            "mh_length_mm",
            f"the LENGTH tile reads {product.length_text!r}, and the FAQ independently says "
            f"\"Our {product.model} campervan is {product.mh_length_mm / 1000:g}m long\". "
            f"BOTH ARE ROUNDED to the nearest 0.1m — this is the only length Project Yonder "
            f"publish and it is not a measurement",
        )
    for name, value, axis in (
        ("mh_width_mm", product.mh_width_mm, "width"),
        ("mh_height_mm", product.mh_height_mm, "height"),
    ):
        if value is not None:
            record(
                name,
                f"{product.dimensions_from_faq!r} — the FAQ answer \"How big are your "
                f"vans?\", which is the ONLY place Project Yonder publish a width or a "
                f"height at all. It gives the SAME {axis} for every van they build, "
                f"rounded to 0.1m, on a page that still calls this model by its old name",
                url=FAQ_URL,
            )

    if product.mtplm_kilograms is not None:
        record(
            "mtplm_kilograms",
            f"the GVW tile reads {product.gross_weight_text!r}. Gross vehicle weight is the "
            f"MTPLM. THE FAQ SAYS SOMETHING ELSE — \"Our vans have a Gross Vehicle Weight "
            f"of {(faq.gross_weight_kilograms or 0) / 1000:g}T\" — and the two have never "
            f"agreed. SETTLED: a model page beats a standing page like an FAQ, because only "
            f"the model page is maintained (Francis, 13 November 2026). This figure is also "
            f"what will turn a mass in running order into a payload once Project Yonder "
            f"supply one, which is why it had to be settled rather than left open",
        )

    if product.body_type is not None and product.mh_height_mm is not None:
        record(
            "body_type",
            _BODY_TYPE_REASON.format(
                height=product.mh_height_mm,
                threshold=HIGH_TOP_ABOVE_MM,
                margin=product.mh_height_mm - HIGH_TOP_ABOVE_MM,
            ),
        )

    if motorhome.automatic_available is not None:
        line = product.automatic_line or (faq.automatic_line or "")
        record(
            "automatic_available",
            f"{line.strip()!r}. Project Yonder offer no manual at all, so this is the only "
            f"gearbox rather than an option — no separate automatic price exists to record",
        )

    for name in ("heating", "refrigeration", "shower_toilet_separated"):
        if name in features:
            found = features[name]
            record(name, f"{found.note or 'from'} {found.snippet.strip()!r}")

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


# --------------------------------------------------------------------------- #
# Narration
# --------------------------------------------------------------------------- #


def _narrate_conflicts(faq: Faq, products: Iterable[YonderProduct], on_progress) -> None:
    """Where the two pages disagree, which rule settled it, and what is still missing.

    **The conflicts are settled, not open.** Francis ruled on 13 November 2026 that a model
    page beats a standing page like an FAQ, because only the model page is maintained — see
    `docs/adapters/README.md`. They are still said out loud every run, because a rule that
    is applied silently cannot be seen to be wrong, and because a *new* disagreement needs
    to surface the same way. But they are stated as applied, not asked.

    Only the masses remain a question, and only one of the two: a mass in running order
    yields the payload through the gross weight the model pages publish.
    """
    gross_tiles = {product.gross_weight_text for product in products if product.gross_weight_text}
    if faq.gross_weight_kilograms is not None and gross_tiles:
        tile = ", ".join(sorted(gross_tiles))
        if {f"{faq.gross_weight_kilograms / 1000:g}T"} != gross_tiles:
            on_progress(
                f"SETTLED BY RULE — THE GROSS WEIGHT: every model page tile says {tile}, "
                f"while the FAQ says \"a Gross Vehicle Weight of "
                f"{faq.gross_weight_kilograms / 1000:g}T\". The model page wins, so the "
                f"tile is recorded. Nothing to decide"
            )

    if faq.price_lines:
        on_progress(
            "SETTLED BY RULE — THE PRICE: the FAQ's cost answer still lists "
            + "; ".join(faq.price_lines)
            + ". Those are £25,000-£28,000 below the model pages' own figures, they are "
            "labelled OTR where the model pages are not, and they price RWD variants with "
            "no model page at all. The model page wins, so its figure is recorded. "
            "Nothing to decide"
        )

    on_progress(
        "ASK PROJECT YONDER — THE MASS IN RUNNING ORDER: this is the ONE outstanding "
        "request, made 13 November 2026 along with a floorplan per model. It is not "
        "published for anything, so none is proposed. THE PAYLOAD DOES NOT NEED ASKING "
        "FOR: once a MIRO arrives it is the published gross weight less that figure, which "
        "is why the gross-weight rule above had to be settled first"
    )
    on_progress(
        "NOT ASKED FOR, DELIBERATELY: every length, width and height is rounded to 0.1m, "
        "and the width and height come from one FAQ answer covering the whole range. The "
        "FAQ is the only source for either, so the rule above does not displace it"
    )


def _narrate_habitation(product: YonderProduct, extracted: ExtractedMotorhome, on_progress) -> None:
    """What the page settled about the habitation, and what it left alone."""
    found = []
    for name in ("heating", "refrigeration", "shower_toilet_separated"):
        value = getattr(extracted.motorhome, name)
        if value is not None:
            rendered = value.value if hasattr(value, "value") else value
            found.append(f"{name}={rendered}")
    if found:
        on_progress(f"{product.label}: habitation findings — {', '.join(found)}")
    else:
        on_progress(
            f"{product.label}: NO habitation finding. This page carries no equipment prose "
            f"at all — the heater, the fridge and the washroom are described only on the "
            f"Freedom 4X page, and claiming them here would assert one model's kit on "
            f"another"
        )

    if habitation.microwave_offered(product.prose):
        on_progress(
            f"{product.label}: a microwave is named among \"additional cooking options\", "
            f"so it is OFFERED rather than fitted and no microwave is recorded"
        )


# --------------------------------------------------------------------------- #
# collect
# --------------------------------------------------------------------------- #


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 - the CMS payload is in the served HTML
    snapshot_dir: Path,  # noqa: ARG001 - `Fetcher` already snapshots every request
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every Project Yonder campervan, from the three model pages and the FAQ."""
    wanted = {entry[-1] for entry in ranges}

    home = http.fetch(HOME_URL)
    if home.status_code != 200:
        raise RuntimeError(
            f"the homepage returned HTTP {home.status_code} from {HOME_URL}, and it is the "
            f"only index this site has — there is no models page and no sitemap of models"
        )
    cards, others = parse_roster(_read(home.file_path))
    on_progress(
        f"the homepage offers {len(cards)} campervan cards: "
        + ", ".join(f"{card.title!r} ({card.subtitle})" for card in cards)
    )
    for title in others:
        known = NOT_A_MODEL.get(title)
        on_progress(
            f"homepage card {title!r} is not a vehicle: {known}"
            if known
            else f"UNKNOWN homepage card {title!r} links off-site — check whether it sells "
            f"a campervan"
        )
    for card in cards:
        if card.slug not in MODELS:
            on_progress(
                f"NEW MODEL on the homepage: {card.title!r} at /{card.slug} ({card.subtitle}), "
                f"which this adapter does not know. Add it to project_yonder.MODELS"
            )
    for slug in MODELS:
        if slug not in {card.slug for card in cards}:
            on_progress(
                f"GONE from the homepage: /{slug}, which this adapter expects. Its page may "
                f"still resolve; the card no longer offers it"
            )

    faq_page = http.fetch(FAQ_URL)
    if faq_page.status_code != 200:
        raise RuntimeError(
            f"the FAQ returned HTTP {faq_page.status_code} from {FAQ_URL}, and it is the "
            f"only page on this site publishing a width or a height"
        )
    faq = parse_faq(_read(faq_page.file_path))
    on_progress(
        f"the FAQ (published {faq.published[:10] or 'unknown'}) answers "
        f"{len(faq.answers)} questions and gives dimensions for "
        + (", ".join(sorted(faq.dimensions)) or "nothing")
    )

    by_slug = {card.slug: card for card in cards}
    products: list[YonderProduct] = []
    for slug, (manufacturer_range, model, _card) in MODELS.items():
        if manufacturer_range not in wanted:
            continue
        url = f"{BASE_URL}/{slug}"
        page = http.fetch(url)
        if page.status_code != 200:
            on_progress(f"SKIPPED /{slug}: HTTP {page.status_code}")
            continue
        product = parse_model_page(_read(page.file_path), slug, url)

        if card := by_slug.get(slug):
            wheelbase, inches = wheelbase_of(card)
            product.wheelbase_inches = inches
            if wheelbase is not None and wheelbase != model:
                on_progress(
                    f"{product.label}: the homepage card now says {card.subtitle!r}, which "
                    f"is a {wheelbase} where this adapter expects {model} — the model name "
                    f"is NOT updated automatically"
                )

        row = _WHEELBASE_OF_FAQ_ROW.get(model)
        if row in faq.dimensions:
            length, width, height = faq.dimensions[row]
            product.mh_width_mm = width
            product.mh_height_mm = height
            product.dimensions_from_faq = (
                f"Our {row} campervan is {length / 1000:g}m long x {width / 1000:g}m wide "
                f"x {height / 1000:g}m high."
            )
            if height > HIGH_TOP_ABOVE_MM:
                product.body_type = BodyType.CAMPERVAN_HIGH_TOP

        products.append(product)

    extracted: list[ExtractedMotorhome] = []
    for product in products:
        reconciles, note = _reconciles(product, faq)
        if not reconciles:
            on_progress(f"DROPPED {product.label}: {note}")
            continue
        on_progress(f"{product.label}: the length reconciles — {note}")

        built = _build_extracted_motorhome(product, faq)
        extracted.append(built)

        price = f"£{product.rrp_pounds:,}" if product.rrp_pounds else "no price"
        on_progress(
            f"{product.label}: {price}, {product.berths_text or '?'} berths recorded as "
            f"{product.berths}, {product.belts_text or '?'} belts recorded as "
            f"{product.travel_seats}, MTPLM {product.mtplm_kilograms or '?'}kg, "
            f"NO mass in running order and NO payload published"
        )
        if was := _RENAMED_FROM.get(product.slug):
            on_progress(
                f"{product.label}: THIS IS A RENAME IN PROGRESS, not a new vehicle. The "
                f"page's own SEO title is still {product.seo_title!r}, its hero image is "
                f"filed under freedom-4x, and the FAQ still calls it {was!r}. Project "
                f"Yonder have renamed the model and not finished renaming the page"
            )
        _narrate_habitation(product, built, on_progress)

    _narrate_conflicts(faq, products, on_progress)

    if len(extracted) != EXPECTED_PRODUCTS and wanted == {label for _, label in DEFAULT_RANGES}:
        on_progress(
            f"collected {len(extracted)} products where Project Yonder offer "
            f"{EXPECTED_PRODUCTS}"
        )
    return extracted
