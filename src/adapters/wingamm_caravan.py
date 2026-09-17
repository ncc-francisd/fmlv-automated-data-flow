"""Wingamm's Rookie caravans, from `wingamm.com`.

Surveyed and built 17 September 2026. See `docs/adapters/wingamm.md`.

**The second module under `Wingamm`**, alongside `wingamm.py`'s eight motorhomes — the
same two-adapter shape Bailey and Eriba have, and registered `(Wingamm, Wingamm,
caravan)`. `wingamm.py` has excluded `rookie` and `rookie-l` by name since 26 August 2026
as *"caravans, out of scope for this review"*; this module is that scope arriving.

## The source is the model pages, because there is nothing else

Wingamm publish a catalogue PDF for every motorhome and **none for either caravan** — the
whole of `wingamm.py` reads those PDFs, and none of that applies here. What the Rookies
get instead is a short inline block partway down each model page:

    Rookie 3.5
    Frame: Alko Compact with Alko AKS repulsor brake
    Length: 4,990 mm with drawbar
    Travel seats: 4
    Sleeps: 2
    Total mass: 750 Kg - 1.000 Kg

**No width and no height are published anywhere** — not on the pages, not on the index,
and there is no document to fall back on. Both are emitted as nothing, so FMLV's own
figures stand; see `docs/adapters/README.md` on why an unfound figure is never guessed.

## The roster tells a caravan from a motorhome by its drawbar

Wingamm file both product areas in one `camper-caravan` taxonomy, and the caravan index
links **all twelve** vehicles, motorhomes included — the same global-nav trap `swift.py`
and `chausson.py` hit. Scoping by which index page led to a page therefore does *not*
work here, and a pattern matching the path would hand eight motorhomes to a caravan
parser.

The index's own cards give a structural tell instead. **Only a caravan's length is quoted
"with drawbar"**, and only a caravan's total mass is under 1500 kg where every motorhome
reads 3,500 kg:

| card | Length | Total mass |
| --- | --- | --- |
| `rookie` | 4,990 mm **with drawbar** | 750 Kg - 1.000 Kg |
| `rookie-l` | 6,000 mm **with drawbar** | 1,200 Kg |
| `oasi-610-st` | 6.103 mm | 3,500 kg |

So the roster is every index card whose length says so, which means **a third Wingamm
caravan is noticed rather than silently missed** — the failure a hardcoded pair of slugs
would have. `EXPECTED_LAYOUTS` guards the other direction.

Identity still comes from `_MODELS`, because it cannot be derived: FMLV holds the range
and model split as `Rookie` / `3.5` and `Rookie` / `L`, which no part of the page states.
A caravan found on the index but absent from that map is **narrated and skipped**, never
guessed at — the same call `wingamm.unmapped_slugs` makes for a new motorhome.

## The self-check: the index card against the model page

Wingamm write the figures **twice**, in two places and two renderings, and this adapter
reads both and compares them. That is a genuine cross-document check rather than the
arithmetic tautology a single source would have forced:

* the **model page** renders `<span>Travel seats: 4</span>` and calls the berth count
  **`Sleeps`**;
* the **index card** renders `<strong>Travel seats:</strong> 4<br />` and calls the same
  figure **`Berths`**.

`wingamm._page_figure` already handles both renderings — it was written for exactly this
split on the motorhome side — so the two are compared on length, berths and MTPLM. A
disagreement drops the layout rather than picking a side.

**The check is not symmetrical about the mass.** The Rookie L's card prints `Total mass:
1,200 Kg` where its page prints `940 Kg - 1,200 Kg`: the card gives the laden mass only.
So the card is required to *agree* where it speaks and is not required to speak — the same
asymmetry `swift_caravan.GuideSpecs.check` settles, and for the same reason. Losing a real
caravan over a card that abbreviates would be the worse error.

## `Total mass` is a range, and it is MRO to MTPLM

`750 Kg - 1.000 Kg` could be a mass range (empty to laden) or two plating options, and the
page never says. **FMLV settles it**: it holds `mro_kilograms=750` and
`mtplm_kilograms=1000` on the Rookie 3.5, and 950/1200 on the Rookie L. So the lower
figure is the mass in running order and the higher the maximum laden mass, confirmed
against real data rather than reasoned about. Read the other way it would have put a
750 kg MTPLM on a caravan that can carry 1000.

Payload is then `MTPLM - MRO` and goes to `personal_effects_payload_kilograms`, per the
requester's rule of 4 September 2026; `optional_equipment_payload_kilograms` is recorded
with no value so the two columns sum to the derived total. See `swift_caravan.py`.

**The thousands separator goes both ways inside one range** — `1.000 Kg` on the Rookie and
`1,200 Kg` on the Rookie L — so a naive parse reads the first as 1.0.
`wingamm._integer` already strips either, and only where it genuinely separates three
digits, so the model name `540.1` is never multiplied by a thousand.

## The first micros in the project, and FMLV caught it

`docs/adapters/README.md` says `type_micro` needs **both** the manufacturer's own naming
**and** an MTPLM of 1250kg or lower, and records that no surveyed brand had met it: every
caravan before these is rigid — 21 Eriba, 23 Bailey, 26 Swift — and weight alone would
have mislabelled thirteen of them, Bailey's 995kg Discovery D4-2 included.

**The Rookies meet both halves.** 1000kg and 1200kg, and Wingamm's own word throughout:
the index is titled *"Luxury Mini Caravan With Fiberglass Monocoque"* and its copy reads
*"Our mini caravans with fiberglass monocoque"*; the Rookie's page says *"Our Rookie
fiberglass monocoque mini-caravan"*. FMLV already holds both as `type_micro`, correctly.

This was **not** reasoned out in advance. The first version of this adapter asserted
`RIGID` unconditionally, the way `bailey_caravan.py` and `swift_caravan.py` do, and the
first dry run against the real export proposed downgrading two records FMLV had right —
the README's own lesson, *fetch the baseline before writing a rule about what a field
means*, arriving a second time. So the rule is applied per layout here rather than a
constant asserted, and a Rookie that gained weight past 1250kg would come back rigid
without anyone having to remember this.

**The naming is a property of the range, not of each page.** The Rookie L's own page never
says "mini caravan"; the index says it of both, in the plural. So the page is preferred
where it speaks and the index stands in where it does not, and the run says so if the
wording ever disappears — because that half of the test is the half a reviewer cannot
recompute from the figures.

## No price, exactly as on the motorhome side

Wingamm quote euro **ex works, VAT excluded** — the index cards say so in as many words
(`61.270 € (ex works and VAT excl.)`) — and FMLV holds a UK importer price in pounds,
£20,420 and £28,390. Those are different quantities, and converting one into the other
would be wrong by both VAT and transport while looking authoritative. Per
`docs/adapters/README.md` the UK importer defines the price, so **no price is collected**
and the run says so per layout. Settled with the requester, 17 September 2026, and
identical to the call `wingamm.py` already makes.

## Three corrections expected on the first run

FMLV holds both Rookies already, and three of its figures disagree with the site:

* **Rookie L berths 2 -> 4.** The page says `Sleeps: 4` and the card `Berths: 4`; FMLV
  holds 2 for both caravans.
* **Rookie L MRO 950 -> 940.**
* **Length.** FMLV holds **4460 mm for both**, which cannot be right for vehicles a metre
  apart; the published figures are 4990 and 6000.

## Not emitted, and why

* **`twin_axle`** — no axle count is published. The Alko Compact chassis quoted is a
  single-axle unit and both caravans plainly are, but "silence is not a negative" and
  FMLV's stored value is not worth disturbing on an inference. No provenance is recorded,
  so the field is never compared.
* **`overall_width_mm`, `height_mm`, `headroom_mm`** — not published anywhere.
* **Travel seats** — read, and used only for the cross-check. FMLV's caravan schema has
  no seat column; a caravan is towed.
* **`internal_length_mm`** — the only figure near it is the prose aside that the Rookie
  Cross measures "3.60 meters", which is a body length and not the habitable one. FMLV
  holds 3600 on the Rookie L, so guessing here would also be writing one caravan's figure
  onto the other.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.caravan import Caravan
from ..product_model.enums import CaravanBodyType
from ..vehicle_class import VehicleClass
from .base import ExtractedCaravan, Provenance
from .wingamm import (
    BASE_URL,
    MANUFACTURER,
    MANUFACTURER_DISPLAY_NAME,
    _integer,
    _page_figure,
)

__all__ = [
    "BASE_URL",
    "EXPECTED_LAYOUTS",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "VEHICLE_CLASS",
    "WingammCaravan",
    "collect",
]

#: What makes this the caravan adapter. Without it `ADAPTERS` would register the module
#: under `(Wingamm, Wingamm, motorhome)` and it would silently replace `wingamm.py`.
VEHICLE_CLASS = VehicleClass.CARAVAN

#: The caravan index. It links every motorhome too — see the module docstring — so this
#: is where the roster is *read*, not what scopes it.
CARAVAN_INDEX_URL = f"{BASE_URL}/en/mini-caravan-monocoque-glassfibre/"


@dataclass(frozen=True)
class _Model:
    """One caravan's page slug and the identity FMLV holds for it."""

    slug: str
    fmlv_range: str
    fmlv_model: str


#: Identity cannot be derived from the page: it titles itself "Rookie 3.5" and "Rookie L"
#: while FMLV splits those into a range and a model. A caravan on the index and not in
#: here is narrated and skipped rather than given a guessed name.
_MODELS: tuple[_Model, ...] = (
    _Model("rookie", "Rookie", "3.5"),
    _Model("rookie-l", "Rookie", "L"),
)
_BY_SLUG = {model.slug: model for model in _MODELS}

#: Wingamm publish no count of their own, so this is the only thing that would notice a
#: card being lost from the index — the failure that looks like a discontinuation.
EXPECTED_LAYOUTS = 2

#: There is one range, so `--range` has nothing to narrow. Present for the CLI's sake.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (("Rookie", "Rookie"),)

_SCRIPTS = re.compile(r"<(script|style)\b.*?</\1>", re.DOTALL | re.IGNORECASE)

#: A model page link on the index. Both the card image and its "find out" button carry
#: one, so the nearest link *after* a card's figures identifies that card.
_MODEL_HREF = re.compile(re.escape(BASE_URL) + r"/en/camper-caravan/([a-z0-9-]+)/")

#: What separates a caravan card from a motorhome card — see the module docstring. Matched
#: on the length's own text rather than on the vehicle, so it cannot be fooled by a
#: motorhome that happens to be light.
_DRAWBAR = re.compile(r"with\s+drawbar", re.IGNORECASE)

#: Wingamm's own word for the Rookies, which is half the `type_micro` test — see
#: `_body_type`. Hyphen optional and plural allowed, because the site writes all three
#: forms: `mini-caravan` on the Rookie's page, `Mini Caravan` in the index's title, and
#: `Our mini caravans` in the index's copy.
_MICRO_NAMING = re.compile(r"mini[\s-]?caravans?", re.IGNORECASE)

#: The other half: a micro should be towable by a very small car
#: (`docs/adapters/README.md`). Both Rookies clear it — 1000kg and 1200kg — but the
#: threshold is checked per layout rather than assumed for the range, so a heavier Rookie
#: would come back rigid without anyone having to remember to change this.
MICRO_MAX_MTPLM_KG = 1250

#: How far back from a card's `Total mass` its other figures can sit. Generous enough for
#: the longest card seen and short enough not to reach the previous card, whose own
#: `Total mass` would have ended this window.
_CARD_LOOKBACK = 1400


def _strip_scripts(html: str) -> str:
    return _SCRIPTS.sub(" ", html)


def _first_number(value: str | None) -> int | None:
    """The first figure in a labelled value, thousands separator either way.

    `'4,990 mm with drawbar'` -> `4990`; `'750 Kg - 1.000 Kg'` -> `750`.
    """
    if not value:
        return None
    match = re.search(r"\d[\d.,]*", value)
    return _integer(match.group(0)) if match else None


def _masses(value: str | None) -> tuple[int | None, int | None]:
    """`Total mass` as `(mass in running order, maximum laden mass)`.

    Two figures means the range the page prints, lower first — see the module docstring
    for why that reading is FMLV's and not a guess. **One figure is the laden mass**,
    which is what the Rookie L's index card gives, so the running order comes back `None`
    rather than the single figure being used for both.
    """
    if not value:
        return None, None
    numbers = [_integer(found) for found in re.findall(r"\d[\d.,]*", value)]
    numbers = [number for number in numbers if number is not None]
    if not numbers:
        return None, None
    if len(numbers) == 1:
        return None, numbers[0]
    return min(numbers), max(numbers)


@dataclass(frozen=True)
class _Figures:
    """One statement of a caravan's figures, from a model page or from an index card."""

    shipping_length_mm: int | None = None
    travel_seats: int | None = None
    berths: int | None = None
    mro_kilograms: int | None = None
    mtplm_kilograms: int | None = None

    @classmethod
    def read(cls, html: str) -> _Figures:
        """The figures in one block of markup, in either of the site's two renderings.

        The berth count is looked up under **both** names the site uses — `Sleeps` on a
        model page, `Berths` on an index card — so one function serves both sources.
        """
        mro, mtplm = _masses(_page_figure(html, "Total mass"))
        berths = _page_figure(html, "Sleeps") or _page_figure(html, "Berths")
        return cls(
            shipping_length_mm=_first_number(_page_figure(html, "Length")),
            travel_seats=_first_number(_page_figure(html, "Travel seats")),
            berths=_first_number(berths),
            mro_kilograms=mro,
            mtplm_kilograms=mtplm,
        )

    def is_empty(self) -> bool:
        return all(
            value is None
            for value in (
                self.shipping_length_mm,
                self.travel_seats,
                self.berths,
                self.mtplm_kilograms,
            )
        )


@dataclass(frozen=True)
class WingammCaravan:
    """One caravan: its identity, its page's figures and its index card's."""

    model: _Model
    page: _Figures
    card: _Figures
    #: Where Wingamm call this a mini caravan, quoted — `"the model page"` or `"the
    #: caravan index"`. `None` means neither does, which makes it rigid however light it
    #: is. See `_body_type`.
    micro_naming: str | None = None

    @property
    def label(self) -> str:
        return f"{self.model.fmlv_range} {self.model.fmlv_model}"

    @property
    def shipping_length_mm(self) -> int | None:
        return self.page.shipping_length_mm

    @property
    def berths(self) -> int | None:
        return self.page.berths

    @property
    def mtplm_kilograms(self) -> int | None:
        return self.page.mtplm_kilograms

    @property
    def mro_kilograms(self) -> int | None:
        return self.page.mro_kilograms

    @property
    def derived_payload_kilograms(self) -> int | None:
        """`MTPLM - MRO`, emitted as the personal-effects payload."""
        if self.mtplm_kilograms is None or self.mro_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mro_kilograms


def caravan_cards(index_html: str) -> dict[str, str]:
    """Every index card whose length is quoted "with drawbar", keyed on its page slug.

    This is the roster, and the discrimination the module docstring explains: the index
    links all twelve vehicles and only the caravans carry a drawbar. A card is located by
    its `Total mass` row and closed at the next model link, which is the card's own "find
    out" button — so a card missing that link contributes nothing rather than absorbing
    the next card's figures.
    """
    html = _strip_scripts(index_html)
    cards: dict[str, str] = {}
    for match in re.finditer(r"Total mass", html, re.IGNORECASE):
        link = _MODEL_HREF.search(html, match.start())
        if link is None:
            continue
        slug = link.group(1)
        if slug in cards:
            continue
        block = html[max(0, match.start() - _CARD_LOOKBACK) : link.end()]
        if _DRAWBAR.search(_page_figure(block, "Length") or ""):
            cards[slug] = block
    return cards


def micro_naming_in(html: str) -> str | None:
    """Wingamm's own "mini caravan" wording, quoted, or `None` where it is absent.

    Scripts are stripped **before** the search, not just tags: the index embeds a country
    list and other JSON that a bare tag-strip leaves in the text, and the first version of
    this quoted `"SE","SI","SK"],"wait_for_up` as its evidence for a body type. What a
    reviewer sees has to be a sentence Wingamm wrote.
    """
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", _strip_scripts(html)))
    match = _MICRO_NAMING.search(text)
    if match is None:
        return None
    # Widen to the surrounding words rather than a fixed character count, so the quote
    # starts and ends on a word.
    start = text.rfind(" ", 0, max(0, match.start() - 45)) + 1
    end = text.find(" ", match.end() + 25)
    return text[start : end if end != -1 else len(text)].strip()


def _body_type(product: WingammCaravan) -> tuple[CaravanBodyType, str]:
    """The caravan's body type and the sentence that justifies it.

    **`type_micro` needs both halves of `docs/adapters/README.md`'s test** — the
    manufacturer's own naming *and* an MTPLM of 1250kg or lower. These are the first
    products in the project to meet it: every caravan surveyed before (21 Eriba, 23
    Bailey, 26 Swift) is rigid, and weight alone would have mislabelled thirteen of them,
    Bailey's 995kg Discovery D4-2 included.

    Getting this wrong was caught by FMLV rather than by reasoning: an earlier version of
    this adapter asserted `RIGID` unconditionally, the way `bailey_caravan.py` and
    `swift_caravan.py` do, and the first dry run proposed downgrading two records FMLV
    already held as micro — correctly. Hence the rule is applied here rather than a
    constant asserted.
    """
    mtplm = product.mtplm_kilograms
    if product.micro_naming and mtplm is not None and mtplm <= MICRO_MAX_MTPLM_KG:
        return CaravanBodyType.MICRO, (
            f"Wingamm's own name for it and a maximum laden mass of {mtplm}kg, at or "
            f"under the {MICRO_MAX_MTPLM_KG}kg a micro has to be towable within (NCC "
            f'rule): "{product.micro_naming}"'
        )
    if product.micro_naming:
        return CaravanBodyType.RIGID, (
            f"Wingamm call it a mini caravan, but a micro needs a maximum laden mass of "
            f"{MICRO_MAX_MTPLM_KG}kg or lower and this is {mtplm}kg. The naming alone is "
            f"not enough — weight and the manufacturer's word are both required"
        )
    return CaravanBodyType.RIGID, (
        "A touring caravan is rigid unless its walls fold or rise — a lifting roof does "
        "not change the type, even where a manufacturer calls it a pop-up (NCC rule, "
        "7 September 2026). Wingamm's monocoque shell does neither, and nothing on the "
        "site calls this one a mini caravan"
    )


def _reconciles(product: WingammCaravan) -> tuple[bool, str]:
    """Whether the model page's figures agree with the index card's, and hold together.

    The card is required to **agree where it speaks** and is not required to speak: the
    Rookie L's card gives a laden mass and no running order. A disagreement drops the
    layout, because two Wingamm pages contradicting each other leaves nothing to say which
    is right.
    """
    page = product.page
    missing = [
        name
        for name, value in (
            ("a length", page.shipping_length_mm),
            ("a berth count", page.berths),
            ("a maximum laden mass", page.mtplm_kilograms),
        )
        if value is None
    ]
    if missing:
        return False, f"the model page publishes no {', no '.join(missing)}"

    if page.mro_kilograms is not None and page.mro_kilograms >= page.mtplm_kilograms:
        return False, (
            f"mass in running order {page.mro_kilograms}kg is not below the maximum "
            f"laden mass {page.mtplm_kilograms}kg"
        )

    card = product.card
    for name, mine, theirs in (
        ("length", page.shipping_length_mm, card.shipping_length_mm),
        ("berth count", page.berths, card.berths),
        ("maximum laden mass", page.mtplm_kilograms, card.mtplm_kilograms),
        ("travel seat count", page.travel_seats, card.travel_seats),
    ):
        if theirs is not None and mine != theirs:
            return False, (
                f"the model page gives a {name} of {mine} and the index card {theirs}"
            )

    return True, "the model page and the index card agree on every figure both publish"


def build_extracted(product: WingammCaravan, source_url: str, *, basis: str) -> ExtractedCaravan:
    """One parsed caravan as a `Caravan` plus the provenance a reviewer sees beside it."""
    body_type, body_reason = _body_type(product)
    caravan = Caravan(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.model.fmlv_range,
        model=product.model.fmlv_model,
        berths=product.berths,
        mtplm_kilograms=product.mtplm_kilograms,
        mro_kilograms=product.mro_kilograms,
        personal_effects_payload_kilograms=product.derived_payload_kilograms,
        shipping_length_mm=product.shipping_length_mm,
        body_type=body_type,
    )

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=source_url, snippet=f"{product.label} — {snippet}"
        )

    # Both halves of the identity, always. `compare_fields` walks only fields that have
    # provenance, and accepting a range change without its model corrupts the name.
    record(
        "manufacturer_range",
        f'range "{product.model.fmlv_range}" — accept with the model, they are one name',
    )
    record(
        "model",
        f'model "{product.model.fmlv_model}", from the page titled '
        f'"{product.label.replace(" ", " ")}" — accept with the range, they are one name',
    )

    if product.berths is not None:
        record("berths", f"Sleeps: {product.berths}; the index card says Berths: {product.berths}")
    if product.mtplm_kilograms is not None:
        record(
            "mtplm_kilograms",
            f"Total mass: {product.mro_kilograms or '?'} Kg - {product.mtplm_kilograms} Kg, "
            f"of which the higher figure is the maximum laden mass; {basis}",
        )
    if product.mro_kilograms is not None:
        record(
            "mro_kilograms",
            f"Total mass: {product.mro_kilograms} Kg - {product.mtplm_kilograms} Kg, "
            f"of which the lower figure is the mass in running order",
        )
    if product.derived_payload_kilograms is not None:
        record(
            "personal_effects_payload_kilograms",
            f"Payload: {product.derived_payload_kilograms}kg, derived as the maximum laden "
            f"mass minus the mass in running order ({product.mtplm_kilograms} - "
            f"{product.mro_kilograms}). Wingamm publish no payload of their own",
        )
        # Recorded with no value, which is the point: it says the adapter looked, so the
        # two payload columns sum to the derived total.
        record(
            "optional_equipment_payload_kilograms",
            "Wingamm publish one payload figure and no split, so there is no separate "
            "optional-equipment payload. Leave this blank so the two payload columns sum "
            f"to the derived {product.derived_payload_kilograms}kg",
        )
    if product.shipping_length_mm is not None:
        record(
            "shipping_length_mm",
            f"Length: {product.shipping_length_mm}mm with drawbar — the body plus the "
            f"towing hitch, which is the shipping length and not the internal one",
        )

    # Derived by rule rather than asserted, unlike the other caravan adapters — these are
    # the first products in the project to satisfy the micro test. The snippet carries
    # both halves of it, so a reviewer can check the reasoning and not just the answer.
    record("body_type", body_reason)

    return ExtractedCaravan(caravan=caravan, provenance=provenance)


def collect(
    http: Fetcher,
    browser: object = None,  # noqa: ARG001
    snapshot_dir: Path | None = None,  # noqa: ARG001
    *,
    ranges: tuple[tuple[str, str], ...] | None = None,  # noqa: ARG001
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedCaravan]:
    """Fetch and parse both Wingamm caravans.

    `browser` and `snapshot_dir` are unused — the pages are server-rendered and `http`
    snapshots every request itself — but stay in the signature because `cli.execute_run`
    passes them positionally. `ranges` is accepted and ignored: there is one range.
    """
    on_progress(f"fetching the Wingamm caravan index: {CARAVAN_INDEX_URL}")
    index_html = http.fetch(CARAVAN_INDEX_URL).file_path.read_text(
        encoding="utf-8", errors="replace"
    )

    cards = caravan_cards(index_html)
    if not cards:
        # Said loudly rather than reported as an empty range, which is what a discontinued
        # brand would look like. The index links every motorhome too, so "no cards" means
        # the page's shape changed, not that Wingamm stopped making caravans.
        on_progress(
            f"no caravan cards found on {CARAVAN_INDEX_URL} — every card there quotes a "
            f"length without a drawbar, so the page's shape has changed and nothing can "
            f"be collected until this adapter is updated"
        )
        return []

    index_naming = micro_naming_in(index_html)
    if index_naming is None:
        # Half the `type_micro` test, and the half a reviewer cannot recompute from the
        # figures. If Wingamm restyle the page away from "mini caravan" these stop being
        # micros by the rule, so it is said rather than quietly changing the answer.
        on_progress(
            "the caravan index no longer calls these mini caravans — without the "
            "manufacturer's own naming the micro test fails and they become rigid"
        )

    on_progress(f"{len(cards)} caravan(s) on the index: " + ", ".join(sorted(cards)))
    if len(cards) != EXPECTED_LAYOUTS:
        on_progress(
            f"expected {EXPECTED_LAYOUTS} caravans and the index publishes {len(cards)} — "
            f"Wingamm publish no count of their own, so check this is a real range change"
        )

    extracted: list[ExtractedCaravan] = []
    for slug, card_html in sorted(cards.items()):
        model = _BY_SLUG.get(slug)
        if model is None:
            # A new caravan. Its figures could be read, but FMLV's range/model split for
            # it cannot be, and a guessed identity matches the wrong baseline row.
            on_progress(
                f"the index lists a caravan at /en/camper-caravan/{slug}/ that this "
                f"adapter has no identity for — add it to _MODELS with the range and "
                f"model FMLV holds. No product proposed for it."
            )
            continue

        url = f"{BASE_URL}/en/camper-caravan/{slug}/"
        page_html = _strip_scripts(
            http.fetch(url).file_path.read_text(encoding="utf-8", errors="replace")
        )
        page = _Figures.read(page_html)
        if page.is_empty():
            on_progress(f"no technical figures on {url} — skipping {slug}")
            continue

        # The Rookie's own page calls it a mini-caravan; the Rookie L's does not, and the
        # index — titled "Luxury Mini Caravan With Fiberglass Monocoque" — says "Our mini
        # caravans" of both. So the naming is a property of the range, and the page is
        # only preferred because a per-layout statement is the better evidence when it
        # exists.
        naming = micro_naming_in(page_html) or index_naming
        product = WingammCaravan(
            model=model,
            page=page,
            card=_Figures.read(card_html),
            micro_naming=naming,
        )
        reconciles, reason = _reconciles(product)
        if not reconciles:
            on_progress(f"dropping {product.label} — {reason}")
            continue

        if product.card.mro_kilograms is None:
            on_progress(
                f"{product.label}: the index card gives only the laden mass, so the mass "
                f"in running order is checked by nothing but the page itself"
            )
        # Said every run, like `wingamm.py`'s: a reviewer seeing a blank price should see
        # why, rather than assuming nobody looked.
        on_progress(
            f"{product.label}: price NOT collected — Wingamm quote euro ex works, VAT "
            f"excluded, and FMLV holds a UK importer price in pounds"
        )

        extracted.append(build_extracted(product, url, basis=reason))
        on_progress(
            f"read {product.label}: {product.shipping_length_mm}mm with drawbar, "
            f"{product.mro_kilograms}-{product.mtplm_kilograms}kg, {product.berths} berths"
        )

    on_progress(f"collected {len(extracted)} Wingamm caravan(s)")
    return extracted
