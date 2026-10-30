"""Globe-Traveller (globe-traveller.eu) — twelve high-top campervans, from the model pages.

See `docs/adapters/globe-traveller.md` for the survey and the two corrections appended to
it. Structurally this is close to `joa.py`: **one URL is one vehicle**, plain
server-rendered HTML, no JavaScript, no configurator, and the root of the site is already
English. What makes it different is that the page is a *complete specification with two
numbers missing*, and both of those numbers live in documents a run cannot read.

**Twelve products, not fourteen.** The UK price list prices `Explorer Z Bike` and
`Pathfinder Z Bike` as lines of their own, which read at first like two more models. They
are not. The catalogue says so outright — *"The Explorer Z and Pathfinder Z can be ordered
in Bike Version, with the garage adapted to carry two bicycles inside the vehicle"* — and
the prices corroborate it: the uplift is **£347 on both**, and one option costs one price
wherever it is fitted. Neither has a page on the website or a spec block in the catalogue.
So a Bike is the base model with a box ticked, and by the base-vehicle rule in
`docs/adapters/README.md` what gets recorded is the base.

**The seats notation is the opposite of what it looks like, and getting it backwards costs
two seats on half the range.** Every page states `No. of seats` as a plain figure with a
second in brackets — `2(3)` on the Explorers, `4(3)` on the Pathfinders and Voyagers. The
instinct from the berths rule is to take the lower, and on the Explorers that happens to be
right. On the Pathfinders and Voyagers it is wrong, because **the plain figure is the
standard fitment and the bracket is the option**, in both directions. The catalogue says it
three separate times in prose:

    Four travel seats are standard, while an optional three seat configuration provides
    more room in the living area without reducing the number of berths

So `2(3)` is two seats with a third available and `4(3)` is four seats with a three-seat
layout available, and the figure recorded is the one outside the brackets either way. See
`seats_from`. The README's own warning applies and is what sent me to the catalogue: the
lower-figure rule is safe for berths because that row is labelled `standard / max`, and it
does not transfer to a seats row by analogy.

**`2+2` berths is four, and the second two are not optional.** Six layouts state
`No. of berths 2+2` and those same six carry an `Additional bed` with a size where the
others read `N/A`. The catalogue describes the extra bed as part of the layout — *"an
additional pull-down folding bed"*, *"providing four berths without giving up the use of
the seating"* — and the optional three-seat configuration is explicitly *"without reducing
the number of berths"*. The berth-range rule takes the lower figure where the upper needs
options; here it does not, so these are four-berth vehicles.

**Two figures are constants, and that is deliberate rather than a shortcut.** Both of the
documents carrying them are FlipHTML5 flipbooks whose config hands over a downloadable PDF,
so an adapter *could* fetch them every run. It must not, because that download has
`"type":"originalFiles"` — the file **first uploaded** — and on the price list it is
already serving a superseded euro edition while the pages on screen are sterling. A fetch
that looks live but silently returns last season's document is worse than a constant that
says what it is. See `UK_PRICES` and `FALCON_MRO_KILOGRAMS`, and the flipbook section of
`docs/adapters/README.md`.

**What is missing is missing on purpose.** The nine Fiat models have a price and no mass in
running order; the three Falcons have a mass and no price. Nothing is invented to fill
either gap, and in particular the per-series mass printed in both documents is **not**
spread across the models beside it: it is footnoted *"the heaviest model variant in the
series"*, which makes it a sibling's figure — the Airstream unit-plate mistake. Those
fields are simply not recorded, so they reach a reviewer as blanks rather than as plausible
wrong numbers. See `collect`, which narrates both gaps on every run.

**The self-check is structural, because the arithmetic is unavailable.** `payload == MTPLM
- MRO` needs an MRO that nine of the twelve do not have. What the pages do support is an
identity check: the roster comes from `/models/`, and each page restates its own series and
model in the table, so a page served for the wrong vehicle is caught by comparing those
against the URL it was fetched from. See `_reconciles`.

**The layout filenames lie, so the drawing is taken from the page and never matched by
name.** `explorer-z-evo` carries one image called `voyager_z_layout-3.png`; `falcon-ys`
carries `falcon_2XS_SE_layout-3.png`; `pathfinder-x` and `voyager-x` share
`voyager_pathfinder_x_layout-1.png`. One URL is one vehicle here, so the page is the
attribution — but a filename naming a different model is still worth narrating, because it
may mean the wrong drawing was uploaded.

**No NCC id yet.** `GLOBE-TRAVELLER` sits on the provisional 9003, outside the NCC range,
because the brand is in no NCC list. Repoint when one is allocated.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from html import unescape
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from . import habitation
from .base import ExtractedMotorhome, Provenance, floorplan_provenance, fmlv_base_vehicle

BASE_URL = "https://globe-traveller.eu"
MANUFACTURER = "GLOBE-TRAVELLER"
MANUFACTURER_DISPLAY_NAME = "Globe-Traveller"

#: The stated roster. Every model has a card here and nothing else does, so the twelve
#: come from one fetch rather than from a hardcoded list — `docs/adapters/README.md` on
#: rediscovering the roster per run.
MODELS_URL = f"{BASE_URL}/models/"

#: (URL series segment, FMLV `manufacturer_range`) for `--range`. The site's own
#: `Model Series` row says "Explorer Series"; FMLV holds no Globe-Traveller products at
#: all, so the range strings are chosen here rather than read off an export, and the
#: trailing "Series" is dropped so the display name does not read
#: "Globe-Traveller Explorer Series Explorer X".
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (
    ("explorer-series", "Explorer"),
    ("falcon-series", "Falcon"),
    ("pathfinder-series", "Pathfinder"),
    ("voyager-series", "Voyager"),
)

#: What the brand's own index claims and what a run must match. Twelve, not the fourteen
#: lines in the price list — see the module docstring on the two Bike Versions.
EXPECTED_PRODUCTS = 12

#: **Manually sourced.** The website publishes no price anywhere: its footer's
#: "Catalogues and prices" link has no `href` at all. These are the GBP figures on page 3
#: of the UK price list flipbook, read off the live viewer on 30 October 2026 and
#: confirmed by the requester, under the heading `Fiat Ducato | 180 Hp | 2.2 l | AT8 |
#: RHD`. Its own footer gives the basis and it is exactly FMLV's: *"Prices are on the
#: road, collected from dealer premises. They include — Full UK specification, righthand
#: drive, transport to dealer premises, VAT @ 20% and 1st registration and road fund
#: licence."* No conversion and no caveat.
#:
#: **The three Falcons are absent** — the list is titled "Voyager | Pathfinder | Explorer"
#: and omits the VW range entirely, so those three carry no price until the brand supplies
#: one. Keyed on `(range, model)` because `Z` is a model name in three of the four ranges.
#:
#: Not refreshed by any later run: the flipbook's download link serves a superseded
#: edition. Re-verify at the model-year changeover.
UK_PRICES: dict[tuple[str, str], int] = {
    ("Explorer", "XS"): 95_119,
    ("Explorer", "X"): 95_671,
    ("Explorer", "Z"): 95_671,
    ("Explorer", "Z EVO"): 104_013,
    ("Pathfinder", "X"): 101_580,
    ("Pathfinder", "Z"): 101_580,
    ("Voyager", "XS"): 110_181,
    ("Voyager", "X"): 110_733,
    ("Voyager", "Z"): 110_733,
}
PRICE_SOURCE = (
    "the UK price list, page 3, 'Fiat Ducato | 180 Hp | 2.2 l | AT8 | RHD' "
    "(public.globe-traveller.eu/books/pyci/, 2026/2027 edition)"
)

#: **Also manually sourced, and only the Falcons have one.** The catalogue states
#: `Weight in running order ±5%` for the three VW models and for nothing else; the
#: Explorer, Pathfinder and Voyager spec blocks carry no mass at all.
#:
#: The per-series figures printed in both documents — Explorer 3 060, Pathfinder 3 160,
#: Voyager 3 170 — are **deliberately not here**. They are footnoted *"the heaviest model
#: variant in the series"*, which makes each one a statement about one sibling rather than
#: about the models beside it. Recording it on all four Explorers would put a heavier
#: vehicle's mass on three lighter ones, which is the Airstream unit-plate mistake with a
#: different cover on it.
FALCON_MRO_KILOGRAMS: dict[str, int] = {"XS": 2_980, "YS": 3_000, "Z": 3_300}
MRO_SOURCE = (
    "the Globe-Traveller 2026/2027 catalogue, 'Weight in running order ±5%' "
    "(public.globe-traveller.eu/books/cect/)"
)

#: A campervan taller than this is a high top — the shared NCC threshold, as used by
#: `auto_trail.py`, `bailey.py`, `elddis.py` and `joa.py`. Every Globe-Traveller is
#: 280–300cm and the brand calls the body a "Super-High roof" itself, so all twelve clear
#: it comfortably and none of them offers an elevating roof.
HIGH_TOP_ABOVE_MM = 2300

#: The UK takes the **Fiat** only. Every Fiat-based page states its base as
#: `Fiat/Peugeot`, which in the EU is genuinely two products priced ~€4,300 apart — but
#: the UK price list is headed `Fiat Ducato … RHD` and carries no Peugeot table, so the
#: Boxer never reaches this market and the roster is not doubled. The Falcons are VW and
#: have no such pair.
UK_BASE_VEHICLE: dict[str, str] = {"Fiat/Peugeot": "Fiat", "Volkswagen": "VW"}

# --- Reading one page ----------------------------------------------------------------

#: A model card on `/models/`. The same pair appears several times per card (image link,
#: title link, "find out more"), so the result is deduplicated in document order.
_MODEL_LINK = re.compile(r"/models/(?P<series>[a-z]+-series)/(?P<slug>[a-z0-9-]+)/")

#: Every cell of the specification table. The theme wraps each label and each value in
#: its own `x-text-content-text-primary` span, which is why this adapter pairs *cells*
#: rather than flattening the page to one line: `Extended PMM` arrives as six separate
#: cells — `(*Fiat only)`, `3820`, `or`, `4200`, `kg` — and in a flattened line there is
#: nothing to say where it ends and `Dimensions` begins.
_CELL = re.compile(r'<span class="x-text-content-text-primary">(.*?)</span>', re.S)

#: Where the table starts and where the page's footer navigation begins. The footer uses
#: the same span class for its own headings ("Models", "Social Media"), so the cells are
#: bounded rather than filtered.
_TABLE_STARTS = "Model Series"
_TABLE_ENDS = "Models"

#: The labels read off the table, and the only ones. **`Extended PMM` is excluded on
#: purpose**: it states the optional heavier plates (`3820 or 4200 kg`) and the
#: base-vehicle rule records the standard one, which is `Permissible Max. Mass (PMM)`.
#: `Lenght` is the brand's own spelling and must not be corrected.
SPEC_LABELS: tuple[str, ...] = (
    "Model Series",
    "Model",
    "Base vehicle",
    "No. of seats",
    "Bed type",
    "No. of berths",
    "Base model",
    "Engine power",
    "Automatic gearbox",
    "Permissible Max. Mass (PMM)",
    "Lenght",
    "Width",
    "Height",
    "Internal Height",
    "Main bed size",
    "Additional bed",
    "Fridge",
    "Bathroom",
    "Shower tray",
    "Toilet",
    "Double floor",
)

#: Without these there is no product worth proposing. Everything else is a finding or a
#: nicety; a page missing one of these has not been understood and is dropped.
REQUIRED_LABELS: frozenset[str] = frozenset(
    {"Model Series", "Model", "No. of seats", "No. of berths", "Lenght", "Width", "Height"}
)

#: `2(3)` and `4(3)` — the standard fitment first, the option in brackets. See
#: `seats_from` and the module docstring.
_SEATS = re.compile(r"^\s*(?P<standard>\d+)\s*(?:\(\s*(?P<option>\d+)\s*\))?\s*$")

#: `2` or `2+2`. Added rather than ranged: the second pair is a bed the layout has, not a
#: higher bound reached with options.
_BERTHS = re.compile(r"^\s*\d+(?:\s*\+\s*\d+)*\s*$")

#: `636 cm`, `3500 kg`, `90 l` — a figure with its unit, where the unit is checked rather
#: than assumed so a changed row does not quietly become a different quantity.
_MEASURE = re.compile(r"^\s*(?P<value>[\d ]+(?:[.,]\d+)?)\s*(?P<unit>cm|mm|m|kg|l)\b", re.I)

#: This model's layout drawings, in page order. **Never matched by filename** — see the
#: module docstring; `explorer-z-evo` carries one called `voyager_z_layout-3.png`.
_LAYOUT_IMAGE = re.compile(
    r'https://globe-traveller\.eu/wp-content/uploads/[\d/]+/'
    r'(?P<name>[A-Za-z0-9_-]*layout[A-Za-z0-9_-]*\.(?:png|jpg|webp))'
)

#: The brand's own value for a washroom in which the shower is not divided off. Their
#: other value is `Seperate shower` — their spelling, which `habitation` already handles.
_INTEGRATED_BATHROOM = re.compile(r"integrated with (?:the )?toilet", re.I)


def _text(fragment: str) -> str:
    """One cell's visible text: inner tags dropped, entities resolved, spaces collapsed."""
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def find_model_urls(index_html: str) -> list[tuple[str, str, str]]:
    """`(url, series, slug)` for every model card on `/models/`, in document order.

    Each card links to the same page three times, so the slugs are deduplicated. The
    series segment is carried alongside because `_reconciles` checks the page's own
    `Model Series` row against it.
    """
    seen: dict[str, tuple[str, str, str]] = {}
    for match in _MODEL_LINK.finditer(index_html):
        series, slug = match.group("series"), match.group("slug")
        seen.setdefault(slug, (f"{MODELS_URL}{series}/{slug}/", series, slug))
    return list(seen.values())


def spec_cells(page: str) -> list[str]:
    """The specification table's cells, in order, with the footer's own cells excluded.

    Bounded rather than filtered: the footer navigation uses the same span class, and its
    headings include the four series names, which would otherwise look like values.
    """
    cells = [_text(match.group(1)) for match in _CELL.finditer(page)]
    try:
        start = cells.index(_TABLE_STARTS)
    except ValueError:
        return []
    rest = cells[start:]
    end = rest.index(_TABLE_ENDS) if _TABLE_ENDS in rest else len(rest)
    return rest[:end]


def spec_rows(cells: Iterable[str]) -> dict[str, str]:
    """`{label: value}` for the labels in `SPEC_LABELS`, each taking the cell after it.

    A cell consumed as a value is never also read as a label, which is what keeps a value
    that happens to spell a label from opening a second row. Labels outside the set are
    skipped along with their values, so `Extended PMM`'s six ragged cells pass through
    without disturbing the rows either side of them.
    """
    rows: dict[str, str] = {}
    cells = list(cells)
    index = 0
    while index < len(cells) - 1:
        label = cells[index]
        if label in SPEC_LABELS and label not in rows:
            rows[label] = cells[index + 1]
            index += 2
            continue
        index += 1
    return rows


def seats_from(value: str) -> tuple[int | None, int | None]:
    """`'4(3)'` -> `(4, 3)`: the standard fitment, then the configuration offered beside it.

    **The bracket is the option in both directions and the plain figure is what FMLV
    records.** `2(3)` is two belted travel seats with a third available; `4(3)` is four as
    standard with a three-seat layout available instead. Reading it as a range and taking
    the lower would record three seats on the six Pathfinders and Voyagers, against a
    catalogue that says in three places that *"Four travel seats are standard"*.

    The second figure is returned so the provenance can name it: a reviewer seeing `4`
    against a page that prints `4(3)` deserves to be told which one was taken and why.
    """
    match = _SEATS.match(value)
    if match is None:
        return None, None
    option = match.group("option")
    return int(match.group("standard")), int(option) if option else None


def berths_from(value: str) -> int | None:
    """`'2+2'` -> `4`, `'2'` -> `2`. A sum, not a range — see the module docstring."""
    if not _BERTHS.match(value):
        return None
    return sum(int(part) for part in value.split("+"))


def measure(value: str, unit: str) -> int | None:
    """A figure in `cm`, `kg` or `l`, with its unit checked. `cm` is returned as mm.

    Returning `None` on a unit that is not the expected one is the point: it means a row
    that changes from `636 cm` to `6.36 m` blanks the length and reaches a reviewer as a
    gap, rather than recording 6mm.
    """
    match = _MEASURE.match(value)
    if match is None or match.group("unit").lower() != unit:
        return None
    figure = float(match.group("value").replace(" ", "").replace(",", "."))
    return round(figure * 10) if unit == "cm" else round(figure)


def layout_images(page: str) -> list[str]:
    """Every layout drawing on this page, in order and deduplicated."""
    return list(dict.fromkeys(match.group(0) for match in _LAYOUT_IMAGE.finditer(page)))


@dataclass(frozen=True)
class GlobeTravellerProduct:
    """One model, as read from its own page plus the two manually sourced constants."""

    slug: str
    series_segment: str
    manufacturer_range: str
    model: str
    published_series: str
    published_model: str
    mh_length_mm: int | None = None
    mh_width_mm: int | None = None
    mh_height_mm: int | None = None
    internal_height_mm: int | None = None
    mh_passenger_seats_inc_driver: int | None = None
    #: The bracketed figure beside the seats, where the page prints one. Recorded so the
    #: provenance can say what was offered and rejected — never emitted as a value.
    seats_optional: int | None = None
    berths: int | None = None
    mtplm_kilograms: int | None = None
    base_vehicle_published: str | None = None
    bed_type: str | None = None
    main_bed: str | None = None
    additional_bed: str | None = None
    fridge: str | None = None
    bathroom: str | None = None
    shower_tray: str | None = None
    toilet: str | None = None

    @property
    def label(self) -> str:
        return f"{self.manufacturer_range} {self.model}"

    @property
    def rrp_pounds(self) -> int | None:
        """The UK on-the-road price, for the nine models the price list covers."""
        return UK_PRICES.get((self.manufacturer_range, self.model))

    @property
    def mro_kilograms(self) -> int | None:
        """Published for the three Falcons and for nothing else. See `FALCON_MRO_KILOGRAMS`."""
        if self.manufacturer_range != "Falcon":
            return None
        return FALCON_MRO_KILOGRAMS.get(self.model)

    @property
    def mh_payload_kilograms(self) -> int | None:
        """Derived, and only where both masses exist — so only on the three Falcons.

        Globe-Traveller publish no payload for anything. This is `MTPLM - MRO` and is
        recorded with provenance saying so, including the catalogue's own ±5% tolerance
        on the mass it rests on.
        """
        if self.mtplm_kilograms is None or self.mro_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mro_kilograms

    @property
    def base_vehicle(self) -> str | None:
        """`Fiat` or `VW`, from the page's own `Base vehicle` row. See `UK_BASE_VEHICLE`."""
        if self.base_vehicle_published is None:
            return None
        return fmlv_base_vehicle(
            UK_BASE_VEHICLE.get(self.base_vehicle_published, self.base_vehicle_published)
        )

    @property
    def body_type(self) -> BodyType | None:
        """High top on all twelve: the shortest is 280cm against a 230cm threshold.

        No Globe-Traveller offers an elevating roof, so the high-top-with-elevating-roof
        value never applies here and nothing turns on an option.
        """
        if self.mh_height_mm is None:
            return None
        return (
            BodyType.CAMPERVAN_HIGH_TOP
            if self.mh_height_mm > HIGH_TOP_ABOVE_MM
            else BodyType.CAMPERVAN
        )


def parse_model_page(
    page: str, series_segment: str, slug: str, manufacturer_range: str
) -> GlobeTravellerProduct | None:
    """One model's data from its own page, or `None` if the table is not there at all.

    The model name comes from the page's own `Model` row with the series stripped off the
    front — `Explorer Z EVO` under `Explorer Series` is the model `Z EVO` — rather than
    from the URL slug, so that `_reconciles` has two independent readings to compare.
    """
    rows = spec_rows(spec_cells(page))
    if not REQUIRED_LABELS.issubset(rows):
        return None

    published_series = rows["Model Series"]
    published_model = rows["Model"]
    series_word = published_series.removesuffix(" Series").strip()
    model = published_model.removeprefix(series_word).strip() or published_model
    standard_seats, optional_seats = seats_from(rows["No. of seats"])

    return GlobeTravellerProduct(
        slug=slug,
        series_segment=series_segment,
        manufacturer_range=manufacturer_range,
        model=model,
        published_series=published_series,
        published_model=published_model,
        mh_length_mm=measure(rows["Lenght"], "cm"),
        mh_width_mm=measure(rows["Width"], "cm"),
        mh_height_mm=measure(rows["Height"], "cm"),
        internal_height_mm=measure(rows.get("Internal Height", ""), "cm"),
        mh_passenger_seats_inc_driver=standard_seats,
        seats_optional=optional_seats,
        berths=berths_from(rows["No. of berths"]),
        mtplm_kilograms=measure(rows.get("Permissible Max. Mass (PMM)", ""), "kg"),
        base_vehicle_published=rows.get("Base vehicle"),
        bed_type=rows.get("Bed type"),
        main_bed=rows.get("Main bed size"),
        additional_bed=rows.get("Additional bed"),
        fridge=rows.get("Fridge"),
        bathroom=rows.get("Bathroom"),
        shower_tray=rows.get("Shower tray"),
        toilet=rows.get("Toilet"),
    )


def _slug_tokens(text: str) -> str:
    """`'Z EVO'` and `'z-evo'` both -> `'zevo'`, for comparing a name against a URL."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _reconciles(product: GlobeTravellerProduct) -> tuple[bool, str]:
    """`(ok, why not)` — whether the page identifies itself as the vehicle we asked for.

    There is no arithmetic to lean on: `payload == MTPLM - MRO` needs a mass in running
    order that nine of the twelve do not publish, and on the three Falcons that do, the
    payload is derived from that identity and so cannot also test it.

    What the pages give instead is **the identity stated twice** — once in the URL the
    roster supplied, once in the table's own `Model Series` and `Model` rows. A CMS that
    serves the wrong page, or an index whose card points at a neighbour, breaks that
    agreement; a correctly served page cannot. It is the same class of check as Joa's
    model code and it costs one comparison.

    A failure **drops the product**, unlike Joa's length check, which drops one field. The
    disagreement here is about *which vehicle this is*, so nothing on the page can be
    trusted to belong to the model it was requested for.
    """
    expected_series = product.series_segment.removesuffix("-series")
    if _slug_tokens(product.published_series.removesuffix(" Series")) != _slug_tokens(
        expected_series
    ):
        return False, (
            f"the page is headed '{product.published_series}' but was fetched from "
            f"/{product.series_segment}/ — the index card and the page disagree about "
            f"which series this is"
        )
    slug_model = product.slug.removeprefix(f"{expected_series}-")
    if _slug_tokens(product.model) != _slug_tokens(slug_model):
        return False, (
            f"the page's own Model row says '{product.published_model}' but the URL slug "
            f"is '{product.slug}' — the page served is not the model that was requested"
        )
    if (
        product.internal_height_mm is not None
        and product.mh_height_mm is not None
        and product.internal_height_mm >= product.mh_height_mm
    ):
        return False, (
            f"the internal height ({product.internal_height_mm}mm) is not less than the "
            f"overall height ({product.mh_height_mm}mm), so the two rows have been read "
            f"the wrong way round"
        )
    return True, ""


def habitation_lines(product: GlobeTravellerProduct) -> tuple[str, ...]:
    """The spec rows worth handing to `habitation`, each kept with its own label.

    The labels are carried through because `habitation` reads whole lines and its
    vocabulary wants the noun: `90 l` says nothing, `Fridge 90 l` is a refrigerator.
    """
    pairs = (
        ("Bed type", product.bed_type),
        ("Main bed size", product.main_bed),
        ("Additional bed", product.additional_bed),
        ("Fridge", product.fridge),
        ("Bathroom", product.bathroom),
        ("Shower tray", product.shower_tray),
        ("Toilet", product.toilet),
    )
    return tuple(
        f"{label} {value}"
        for label, value in pairs
        if value and value.upper() not in {"N/A", "-"}
    )


def layout_filename_warning(product: GlobeTravellerProduct, images: list[str]) -> str | None:
    """Where this page's drawing is named after a different model, if it is.

    Not a reason to reject it — one URL is one vehicle, so the page is the attribution —
    but a filename naming another model may mean the wrong drawing was uploaded, and a
    reviewer opening it should be told before they trust what they see.

    The range name is removed before the model is looked for, because a single-letter
    model would otherwise be found inside it: `explorer_z_layout-1.png` contains an `x`,
    and without the removal it would pass as the Explorer **X**'s drawing.

    Globe-Traveller's own naming is loose and most of it is innocent — `falcon_2XS`
    carries a version digit, and `voyager_pathfinder_x` is one drawing serving two models
    that share a layout. Both of those still name the model, so neither warns. What warns
    is a filename that names a different one: `explorer-z-evo` carries
    `voyager_z_layout-3.png`, and `falcon-ys` carries `falcon_2XS_SE_layout-3.png`.
    """
    if not images:
        return None
    name = images[0].rsplit("/", 1)[-1]
    normalised = _slug_tokens(name)
    without_range = normalised.replace(_slug_tokens(product.manufacturer_range), "", 1)
    if normalised != without_range and _slug_tokens(product.model) in without_range:
        return None
    return (
        f"the layout drawing on this page is called '{name}', which names a different "
        f"model — it is still the drawing Globe-Traveller publish on this page, but check "
        f"it is the right one before reading a layout off it"
    )


# --- What reaches the reviewer -------------------------------------------------------

#: How each habitation reading is introduced where `habitation` supplies no wording.
_FEATURE_NOTES: dict[str, str] = {
    "refrigeration": "the page's own 'Fridge' row",
    "shower_toilet_separated": "the page's own 'Bathroom' row",
    "bed_types": "the beds this page lists",
}


def _build_extracted_motorhome(
    product: GlobeTravellerProduct,
    source_url: str,
    floorplan_url: str | None = None,
) -> ExtractedMotorhome:
    """One model as a `Motorhome`, with the provenance a reviewer reads beside each field.

    The habitation fields reach the reviewer as **findings** rather than proposals; see
    `product_model.findings`. `shower_toilet_separated` is settled here rather than left
    to `habitation` for the negative case only: `habitation` reads "Seperate shower" —
    their spelling — as separated, but has no phrase for Globe-Traveller's own opposite
    value, `Integrated with toilet`, which plainly says the shower is not divided off.
    """
    lines = habitation_lines(product)
    features = habitation.features_from(lines)

    separated = features["shower_toilet_separated"].value if "shower_toilet_separated" in features else None
    integrated = product.bathroom is not None and _INTEGRATED_BATHROOM.search(product.bathroom)
    if separated is None and integrated:
        separated = False

    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.manufacturer_range,
        model=product.model,
        base_vehicle_manufacturer=product.base_vehicle,
        rrp_pounds=product.rrp_pounds,
        mro_kilograms=product.mro_kilograms,
        mtplm_kilograms=product.mtplm_kilograms,
        mh_payload_kilograms=product.mh_payload_kilograms,
        mh_length_mm=product.mh_length_mm,
        mh_width_mm=product.mh_width_mm,
        mh_height_mm=product.mh_height_mm,
        mh_passenger_seats_inc_driver=product.mh_passenger_seats_inc_driver,
        berths=product.berths,
        body_type=product.body_type,
        # Habitation, from the specification table's own rows — reported as findings
        # rather than proposed, so the pipeline never writes them.
        refrigeration=features["refrigeration"].value if "refrigeration" in features else None,
        shower_toilet_separated=separated,
        bed_types=features["bed_types"].value if "bed_types" in features else [],
    )

    provenance: dict[str, Provenance] = {}

    def record(field: str, snippet: str) -> None:
        provenance[field] = Provenance(
            source_url=source_url, snippet=f"{product.label} — {snippet}"
        )

    record(
        "manufacturer_range",
        f"'{product.manufacturer_range}', from the page's own Model Series row "
        f"('{product.published_series}') with 'Series' dropped. FMLV holds no "
        f"Globe-Traveller products, so this convention is being set rather than matched — "
        f"paired with the model below, accept or reject both together",
    )
    record(
        "model",
        f"'{product.model}', the page's Model row ('{product.published_model}') with the "
        f"series name removed so it is not repeated in the display name. Paired with the "
        f"range above: together they name this vehicle",
    )
    if product.mh_length_mm is not None:
        record("mh_length_mm", f"Dimensions, 'Lenght' (their spelling): {product.mh_length_mm / 10:.0f} cm")
    if product.mh_width_mm is not None:
        record(
            "mh_width_mm",
            f"Dimensions, Width: {product.mh_width_mm / 10:.0f} cm. The body width — "
            f"Globe-Traveller publish no over-mirrors figure",
        )
    if product.mh_height_mm is not None:
        record(
            "mh_height_mm",
            f"Dimensions, Height: {product.mh_height_mm / 10:.0f} cm. The separate "
            f"'Internal Height' row is the headroom inside, not this",
        )
    if product.mh_passenger_seats_inc_driver is not None:
        record(
            "mh_passenger_seats_inc_driver",
            (
                f"'No. of seats {product.mh_passenger_seats_inc_driver}"
                f"({product.seats_optional})' — the figure outside the brackets, which is "
                f"the fitment. The bracketed {product.seats_optional} is the alternative "
                f"configuration: the catalogue says 'Four travel seats are standard, while "
                f"an optional three seat configuration provides more room in the living "
                f"area', so the bracket is the option in both directions and is not a "
                f"range to take the lower of"
                if product.seats_optional is not None
                else f"'No. of seats {product.mh_passenger_seats_inc_driver}', stated "
                f"plainly with no alternative configuration offered"
            ),
        )
    if product.berths is not None:
        record(
            "berths",
            (
                f"'No. of berths 2+2' = {product.berths}. The second pair is the "
                f"'Additional bed {product.additional_bed}' this page lists as "
                f"specification, and the catalogue describes it as part of the layout — "
                f"'providing four berths without giving up the use of the seating'. The "
                f"berth-range rule takes the lower figure where the upper needs options; "
                f"this one does not"
                if product.berths > 2 and product.additional_bed
                else f"'No. of berths {product.berths}', with 'Additional bed' stated as "
                f"N/A"
            ),
        )
    if product.mtplm_kilograms is not None:
        record(
            "mtplm_kilograms",
            f"'Permissible Max. Mass (PMM) {product.mtplm_kilograms} kg'. The separate "
            f"'Extended PMM' row states the heavier plates available as options, which by "
            f"the base-vehicle rule are not what is recorded",
        )
    if product.mro_kilograms is not None:
        record(
            "mro_kilograms",
            f"{product.mro_kilograms}kg, MANUALLY SOURCED from {MRO_SOURCE}, stated there "
            f"with the brand's own ±5% tolerance. The website publishes no mass in running "
            f"order for anything, and the catalogue publishes one only for the three "
            f"Falcons. Not machine-readable and not refreshed by later runs — re-verify at "
            f"the model-year changeover",
        )
    if product.mh_payload_kilograms is not None:
        record(
            "mh_payload_kilograms",
            f"derived: {product.mtplm_kilograms}kg permissible maximum mass - "
            f"{product.mro_kilograms}kg mass in running order = "
            f"{product.mh_payload_kilograms}kg. Globe-Traveller publish no payload "
            f"anywhere, and the mass it rests on carries their ±5% tolerance",
        )
    if product.rrp_pounds is not None:
        record(
            "rrp_pounds",
            f"£{product.rrp_pounds:,}, MANUALLY SOURCED from {PRICE_SOURCE}, because the "
            f"website publishes no price at all — its 'Catalogues and prices' link has no "
            f"destination. On the road, collected from dealer premises, including full UK "
            f"specification, right-hand drive, transport to the dealer, VAT at 20% and "
            f"first registration and road fund licence. Not refreshed by later runs: the "
            f"flipbook's download link serves a superseded euro edition",
        )
    if product.base_vehicle is not None:
        record(
            "base_vehicle_manufacturer",
            (
                f"'Base vehicle {product.base_vehicle_published}', recorded as "
                f"{product.base_vehicle}: the UK price list is headed 'Fiat Ducato … RHD' "
                f"and carries no Peugeot table, so the Boxer is not offered here and this "
                f"is one product rather than two"
                if product.base_vehicle_published == "Fiat/Peugeot"
                else f"'Base vehicle {product.base_vehicle_published}', recorded as "
                f"{product.base_vehicle} — the abbreviated form FMLV uses for a base "
                f"vehicle, as against 'Volkswagen' the manufacturer"
            ),
        )
    if product.body_type is not None:
        record(
            "body_type",
            f"{product.mh_height_mm}mm tall, above the {HIGH_TOP_ABOVE_MM}mm high-top "
            f"threshold — Globe-Traveller call the body a 'Super-High roof' themselves, "
            f"and offer no elevating roof on any model",
        )

    for name, feature in features.items():
        note = feature.note or _FEATURE_NOTES.get(name, "read from the page")
        record(name, f"{note}: {feature.snippet}")
    if "shower_toilet_separated" not in features and separated is False:
        record(
            "shower_toilet_separated",
            f"the page's own 'Bathroom' row says '{product.bathroom}', so the shower is "
            f"not divided off from the toilet",
        )

    if floorplan_url:
        provenance.update(floorplan_provenance(motorhome, floorplan_url, product.label))

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 — server-rendered throughout; see the module docstring
    snapshot_dir: Path,  # noqa: ARG001 — `http` already snapshots into it
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Collect every current Globe-Traveller model, or just the named series.

    One fetch for `/models/`, then one per model page. A page that cannot be fetched,
    parsed or identified is narrated and skipped; only an unreachable index raises, since
    without it there is no roster at all.

    The two gaps are reported at the end of **every** run rather than once at build time,
    because they are the whole reason nothing here is uploadable yet and a run that said
    nothing would look complete.
    """
    on_progress(f"fetching the model index: {MODELS_URL}")
    index = http.fetch(MODELS_URL)
    if index.status_code != 200:
        raise RuntimeError(
            f"{MODELS_URL} returned {index.status_code}; it is the stated roster and "
            f"there is no second list of the models"
        )
    index_html = index.file_path.read_text(encoding="utf-8", errors="replace")

    wanted = dict(ranges)
    found = find_model_urls(index_html)
    if len(found) != EXPECTED_PRODUCTS:
        on_progress(
            f"WARNING: the index lists {len(found)} model(s) where {EXPECTED_PRODUCTS} "
            f"are expected — the range has changed, or the cards have"
        )
    targets = [entry for entry in found if entry[1] in wanted]
    on_progress(f"{len(targets)} model page(s) for {sorted(wanted.values())}")

    results: list[ExtractedMotorhome] = []
    for url, series_segment, slug in targets:
        page_result = http.fetch(url)
        if page_result.status_code != 200:
            on_progress(f"SKIPPED: {url} returned {page_result.status_code}")
            continue
        page = page_result.file_path.read_text(encoding="utf-8", errors="replace")

        product = parse_model_page(page, series_segment, slug, wanted[series_segment])
        if product is None:
            on_progress(
                f"SKIPPED: {url} has no specification table, or it is missing one of "
                f"{sorted(REQUIRED_LABELS)}"
            )
            continue

        reconciles, why_not = _reconciles(product)
        if not reconciles:
            on_progress(f"DROPPED {slug}: {why_not}")
            continue

        images = layout_images(page)
        if not images:
            on_progress(f"[{product.label}] WARNING: no layout drawing found on {url}")
        elif warning := layout_filename_warning(product, images):
            on_progress(f"[{product.label}] WARNING: {warning}")

        if product.rrp_pounds is None:
            on_progress(
                f"[{product.label}] NO PRICE: the UK price list is titled 'Voyager | "
                f"Pathfinder | Explorer' and omits the Falcon range, and the website "
                f"publishes none. Left blank rather than guessed"
            )
        if product.mro_kilograms is None:
            on_progress(
                f"[{product.label}] NO MASS IN RUNNING ORDER: neither document publishes "
                f"one for this model. The per-series figure printed beside it is "
                f"footnoted 'the heaviest model variant in the series', which is a "
                f"sibling's mass — left blank rather than spread across the range"
            )

        results.append(
            _build_extracted_motorhome(product, url, images[0] if images else None)
        )

    priced = sum(1 for item in results if item.motorhome.rrp_pounds is not None)
    weighed = sum(1 for item in results if item.motorhome.mro_kilograms is not None)
    on_progress(
        f"{len(results)} product(s) collected: {priced} with a price and {weighed} with a "
        f"mass in running order. The two documents cover opposite halves of the range, so "
        f"NO PRODUCT YET HAS BOTH — the nine Fiat models need a per-model mass and the "
        f"three Falcons need a UK price before any of this is uploadable. Both figures are "
        f"constants here, not fetched: the flipbook download serves whichever edition was "
        f"uploaded first. Re-verify at the model-year changeover"
    )
    return results
