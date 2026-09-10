"""Joa by Pilote (joabypilote.fr) — motorhomes and panel vans, from the ten model pages.

See `docs/adapters/joa.md` for the full write-up. Structurally this is the best case in
the project: **one URL is one vehicle**, plain server-rendered WordPress, no JavaScript,
no PDF, no login. There are no columns anywhere, so none of the alignment defences that
dominate `morelo.py`, `burstner.py` or `knaus.py` are needed here.

Ten products: seven motorhomes (`60F`, `70Q`, `70T`, `75Q`, `75T`, `75QB`, `75TB`) and
three panel vans (`54G`, `60G`, `63T`). FMLV holds all ten under ranges **`Motorhome`**
and **`Van`**, which is where those two strings come from — not from the site, which
navigates by body type ("Our motorhomes", "Our panel vans"), and not from Pilote's
Technical Book, which says "Motorhomes" and "Panelvans".

Two blocks on each page carry everything, and **both are needed**:

    starting from £68,400
    7,45 m long     2,30 m wide     4 seats     2 berths     <- the summary strip

    Width / Length              230 cm / 285 cm              <- the technical panel
    Type of heating             4,000 W Truma® Combi D4 hot water/heating
    Refrigerator                Automatic fridge with vent covers: 133-litres
    Payload capacity            470 kg

**`Width / Length` IS MISLABELLED — its second value is the HEIGHT.** 285 cm on every
motorhome and 267 cm on every van, against real lengths of 5.41m to 7.45m. The length is
in the summary strip. An adapter that trusted the label would record a 5.99m vehicle as
285cm long, on all ten.

**The value and its unit sit in separate elements**, so the page's text has to be
flattened with tags becoming a single **space**. Replacing a tag with any marker splits
`5,99` from `m long` and the strip stops parsing — the mistake that made four of the ten
pages look as though they had no summary strip at all.

**Two figures are constants, because the documents that carry them are not published.**
The whole WordPress media library holds two PDFs, both from 2021 and both irrelevant;
Pilote send the Technical Book and the UK price list by email, so no run can rediscover
either. See `MTPLM_KILOGRAMS` and `PRICES_NOT_ON_THE_SITE`.

**The self-check is the model code**, which is the length in decimetres: `54G` is 5.41m,
`63T` 6.36m, `70Q` 6.99m, `75TB` 7.45m. It holds to within 0.11m on all ten and it earns
its place immediately — the 63T's own page states 5,99m, which is the **60G's** length,
and misses by 0.31m. `payload == MTPLM - MRO` is unavailable: Joa publish no MRO, so it
has to be derived from the other two and the identity becomes true by construction.

**Habitation costs nothing here.** Each page carries a "View all equipment" overlay
holding that model's whole standard-equipment list, one model to one list, so the
findings need no column reading at all — the opposite of every other brand in this
project. The heating and the fridge are taken from the technical panel's own labelled
rows rather than from the overlay, because the overlay's chassis section on the
motorhomes carries a stray "90-litre high compression refrigerator" where the Technical
Book has "90-litre diesel tank"; the labelled row says 133 litres and agrees with the
book.

**Formerly Joa Camp**, which is still a separate NCC id (103) and still owns the domain
the configurator runs on. All ten FMLV products sit under 261.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from html import unescape
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from . import habitation
from .base import ExtractedMotorhome, Provenance, floorplan_provenance, fmlv_base_vehicle

BASE_URL = "https://www.joabypilote.fr"
MANUFACTURER = "Joa by Pilote"
MANUFACTURER_DISPLAY_NAME = "Joa by Pilote"

#: The roster. **Not the in-page links**, which give fifteen URLs for ten vehicles:
#: `60f`, `motorhome70t` (no hyphen), `van-54g`, `panel-van-60g-en` and
#: `panel-van-63t-en` are aliases that redirect to a canonical page. The sitemap lists
#: exactly the ten canonical pages plus the index, which is the stated roster
#: `docs/adapters/README.md` asks for.
SITEMAP_URL = f"{BASE_URL}/vehicle-sitemap.xml"

#: (slug prefix, label) for `--range`. The prefix is what the page URL carries; the FMLV
#: range it maps to is in `_FMLV_RANGES` and is a different string.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (
    ("motorhome", "Motorhomes"),
    ("panel-van", "Panel vans"),
)

#: URL slug prefix -> the `manufacturer_range` FMLV actually holds. Read off the real
#: export for id 261, where seven products are `Motorhome` and three are `Van`.
_FMLV_RANGES: dict[str, str] = {"motorhome": "Motorhome", "panel-van": "Van"}

#: Every Joa is a Fiat, stated as "Fiat CCS" for the motorhomes and "Fiat Chassis Cab"
#: for the vans in the Technical Book. The site never names it, so this is asserted
#: rather than read — and recorded with provenance saying so, per the Bürstner lesson
#: that a value set without provenance is invisible in both directions.
BASE_VEHICLE = "Fiat"

#: **A manually sourced constant.** The site publishes no maximum authorised mass at all.
#: Pilote's 2027 Technical Book gives 3500 kg for all ten base models and prices a 3.65T
#: derate as a £390 option, so 3500 is the base-vehicle figure by the rule in
#: `docs/adapters/README.md`. FMLV already holds 3500 on all ten, so this proposes
#: nothing today — but no run can refresh it, because the book is not on the website.
#: Re-verify at the model-year changeover.
MTPLM_KILOGRAMS = 3500

#: Read on 10 September 2026 from the Technical Book supplied by Pilote.
MTPLM_SOURCE = "the 2027 Technical Book (version 1.0, 25 May 2026)"

#: **Also manually sourced.** The seven motorhome pages carry `starting from £x`; the
#: three van pages carry no price at all. These come from the 2027 UK price list, which
#: is not on the website either. Its basis is "including 20% VAT **and transport**",
#: headed *Delivered* — note that Pilote's own list for the Pilote brand says *excluding*
#: transport, so nothing about price may be shared between the two adapters.
PRICES_NOT_ON_THE_SITE: dict[str, int] = {"54G": 58900, "60G": 59900, "63T": 61900}
PRICE_LIST_SOURCE = "the 2027 UK price list, valid from 1 June 2026"

#: A campervan taller than this is a high top. The shared NCC threshold, as used by
#: `auto_trail.py`, `bailey.py` and `elddis.py`. Every Joa van is 2670mm, so all three
#: clear it, and the lacquered pop-up roof is a £6,080 option — by the base-vehicle rule
#: an optional rising roof never changes what the vehicle is.
HIGH_TOP_ABOVE_MM = 2300

#: How far the length may sit from the one its model code implies. See `_reconciles`.
LENGTH_TOLERANCE_MM = 150

#: The model strip every page carries, which names nine of the ten vehicles with their
#: lengths — `Motorhome 70Q L6,99m`, `Panel van 63T L6,36m`. It is a **second length for
#: the same vehicle on the same page**, and where the two disagree the strip has been
#: right: the 63T's summary strip says `5.99 m long` while its own strip entry says
#: `L6,36m`, which is the figure the Technical Book and FMLV both carry. See
#: `strip_lengths_mm`. The 54G is absent from the strip, so this is a fallback and never
#: the primary source.
_STRIP_LENGTH = re.compile(
    r"(?:Motorhome|Panel van)\s+(?P<code>[0-9]{2}[A-Z]{1,2})\s+L(?P<m>\d+),(?P<cm>\d+)m"
)

# --- Reading one page ----------------------------------------------------------------

#: A canonical vehicle page in the sitemap. The bare `/en/vehicle/` index is excluded by
#: requiring a slug, and the French pages by requiring `/en/`.
_MODEL_URL = re.compile(
    rf'{re.escape(BASE_URL)}/en/vehicle/(?P<slug>(?:motorhome|panel-van)-[a-z0-9]+)/'
)

#: The summary strip beside the Configure button. Each figure and its unit sit in
#: separate elements, which is why `_text` joins tags with a space.
_LENGTH = re.compile(r"([\d]+[.,][\d]+) m long")
_WIDTH_STRIP = re.compile(r"([\d]+[.,][\d]+) m wide")
_SEATS = re.compile(r"(\d+) seats?\b")
_BERTHS = re.compile(r"(\d+) berths?\b")
_PRICE = re.compile(r"starting from £\s*([\d][\d, ]*)")

#: The technical panel's own rows. `Width / Length` is the mislabelled one — see the
#: module docstring — so its two values are read as width and height.
_WIDTH_HEIGHT = re.compile(r"Width / Length (\d+) cm / (\d+) cm")
_PAYLOAD = re.compile(r"Payload capacity ([\d ]+) kg")
_HEATING = re.compile(r"Type of heating (.+?) Refrigerator ")
_REFRIGERATOR = re.compile(r"Refrigerator (.+?) Fuel tank ")

#: The layout drawing — *implantation* is French for layout. Every page carries the whole
#: set in its nav strip, so the one for this model is picked out by its code.
_FLOORPLAN = re.compile(
    rf'{re.escape(BASE_URL)}/wp-content/uploads/[\d/]+/joa-site-implant-(?P<code>[a-z0-9]+)\.jpg'
)

#: An overlay's contents. Its items are `<br />`-separated inside a `<p>`, and its
#: section headings are separate `<p>`s, so both become lines once the breaks are turned
#: into newlines.
#:
#: **Every page has two of these and the first one is the navigation menu.** Taking the
#: first gave every model the site's own nav strip — "Panel van 63T / L6,36m - Twin
#: beds / Panel van 60G / L5,99m - Double bed" — which put twin beds on all ten,
#: including the two whose own nav entry says double.
_OVERLAY = re.compile(r'<div class="gb-overlay__content">', re.S)

#: What tells the equipment overlay from the navigation one. Both halves of the brand
#: have a kitchen section; they disagree on whether the first is `CHASSIS - ENGINE` or
#: `ENGINE - CHASSIS`, so that one is no use as an anchor.
_EQUIPMENT_SECTION = re.compile(r">\s*KITCHEN\s*<")


def _text(page: str) -> str:
    """The page's visible text as one line, tags replaced by a **single space**.

    The single space is load-bearing. Joa split a figure from its unit across two
    elements — `<p>7,45</p><p>m long</p>` — so any other separator breaks `7,45 m long`
    in half and the summary strip stops parsing.
    """
    body = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", page)
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", body)).split())


def _metres_to_mm(raw: str | None) -> int | None:
    """`'7,45'` or `'7.45'` -> `7450`. Joa mix the two decimal marks across the site."""
    if raw is None:
        return None
    return round(float(raw.replace(",", ".")) * 1000)


def _int(raw: str | None) -> int | None:
    if raw is None:
        return None
    digits = re.sub(r"[^\d]", "", raw)
    return int(digits) if digits else None


def find_model_urls(sitemap_xml: str) -> list[str]:
    """Every canonical model page in `vehicle-sitemap.xml`, in document order."""
    seen: dict[str, None] = {}
    for match in _MODEL_URL.finditer(sitemap_xml):
        seen.setdefault(match.group(0), None)
    return list(seen)


def parse_equipment(page: str) -> tuple[str, ...]:
    """This model's standard-equipment list, from the "View all equipment" overlay.

    One model, one list — there is nothing to attribute. Section headings come through
    as lines of their own and are harmless: `habitation` reads whole lines and no
    heading matches any of its vocabulary.

    The overlay is picked out by its **kitchen section**, not by position: the first
    overlay on every page is the navigation menu. See `_OVERLAY`.
    """
    starts = [match.start() for match in _OVERLAY.finditer(page)]
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(page)
        block = page[start:end]
        if not _EQUIPMENT_SECTION.search(block):
            continue
        broken = re.sub(r"<br\s*/?>", "\n", block)
        text = unescape(re.sub(r"<[^>]+>", "\n", broken))
        lines = [" ".join(line.split()) for line in text.split("\n")]
        return tuple(dict.fromkeys(line for line in lines if line))
    return ()


@dataclass(frozen=True)
class JoaProduct:
    """One model, as read from its own page."""

    slug: str
    manufacturer_range: str
    model: str
    mh_length_mm: int | None = None
    mh_width_mm: int | None = None
    mh_height_mm: int | None = None
    mh_passenger_seats_inc_driver: int | None = None
    berths: int | None = None
    mh_payload_kilograms: int | None = None
    rrp_pounds: int | None = None
    #: Whether `rrp_pounds` came from `PRICES_NOT_ON_THE_SITE` rather than the page.
    price_manually_sourced: bool = False
    heating_published: str | None = None
    refrigerator_published: str | None = None
    #: The width the summary strip states, where it states one. Read only as a check on
    #: the technical panel's own figure — see `_reconciles`.
    width_strip_mm: int | None = None
    #: This model's length as the page's own model strip states it — a second reading of
    #: the same figure, used to repair a summary strip that fails the code check. `None`
    #: for the 54G, which the strip omits. See `strip_lengths_mm`.
    strip_length_mm: int | None = None

    @property
    def label(self) -> str:
        return f"{self.manufacturer_range} {self.model}"

    @property
    def mtplm_kilograms(self) -> int:
        return MTPLM_KILOGRAMS

    @property
    def mro_kilograms(self) -> int | None:
        """Derived. Joa publish no mass in running order anywhere.

        The Technical Book's own note defines the payload as the difference between the
        maximum authorised mass and the mass in running order, so this is that identity
        rearranged rather than an estimate. It does mean `payload == MTPLM - MRO` cannot
        serve as a self-check — it is true by construction. See `_reconciles`.
        """
        if self.mh_payload_kilograms is None:
            return None
        return MTPLM_KILOGRAMS - self.mh_payload_kilograms

    @property
    def body_type(self) -> BodyType | None:
        """Low profile for a motorhome, high top for a van — neither is inferred loosely.

        Joa build no A-class and no over-cab bed: the Technical Book's only elevated bed
        is an optional electric drop-down over the **lounge**, and FMLV holds all seven
        motorhomes as low profile. The vans are 2670mm against the shared 2300mm
        threshold, and their pop-up roof is a £6,080 option, so it never changes the type.
        """
        if self.manufacturer_range == "Motorhome":
            return BodyType.COACH_BUILT_LOW_PROFILE
        if self.mh_height_mm is None:
            return None
        return (
            BodyType.CAMPERVAN_HIGH_TOP
            if self.mh_height_mm > HIGH_TOP_ABOVE_MM
            else BodyType.CAMPERVAN
        )

    @property
    def implied_length_mm(self) -> int:
        """The length this model's code claims, in mm. `75TB` -> 7500. See `_reconciles`."""
        return int(re.match(r"\d+", self.model).group(0)) * 100


def parse_model_page(page: str, slug: str) -> JoaProduct | None:
    """One model's data, from its own page. `None` if the page carries no model code.

    The code and the range both come from the slug, which the sitemap supplies:
    `motorhome-75tb` is `Motorhome` + `75TB`, `panel-van-54g` is `Van` + `54G`.
    """
    prefix, _, code = slug.partition("-") if slug.startswith("motorhome") else (
        "panel-van",
        "-",
        slug.removeprefix("panel-van-"),
    )
    manufacturer_range = _FMLV_RANGES.get(prefix)
    if manufacturer_range is None or not code:
        return None

    text = _text(page)
    width_height = _WIDTH_HEIGHT.search(text)

    def first(pattern: re.Pattern[str]) -> str | None:
        match = pattern.search(text)
        return match.group(1).strip() if match else None

    price = _int(first(_PRICE))
    model = code.upper()
    return JoaProduct(
        slug=slug,
        manufacturer_range=manufacturer_range,
        model=model,
        mh_length_mm=_metres_to_mm(first(_LENGTH)),
        mh_width_mm=int(width_height.group(1)) * 10 if width_height else None,
        mh_height_mm=int(width_height.group(2)) * 10 if width_height else None,
        width_strip_mm=_metres_to_mm(first(_WIDTH_STRIP)),
        strip_length_mm=strip_lengths_mm(page).get(model),
        mh_passenger_seats_inc_driver=_int(first(_SEATS)),
        berths=_int(first(_BERTHS)),
        mh_payload_kilograms=_int(first(_PAYLOAD)),
        rrp_pounds=price if price is not None else PRICES_NOT_ON_THE_SITE.get(model),
        price_manually_sourced=price is None and model in PRICES_NOT_ON_THE_SITE,
        heating_published=first(_HEATING),
        refrigerator_published=first(_REFRIGERATOR),
    )


def strip_lengths_mm(page: str) -> dict[str, int]:
    """Every length the page's model strip states, keyed by model code.

    The strip is navigation rather than specification, and it is on all ten pages, so
    each page states nine lengths besides the one in its own summary. That redundancy is
    what lets a bad summary be repaired instead of merely rejected — see `_reconciles`.
    """
    return {
        match.group("code").upper(): int(match.group("m")) * 1000
        + int(match.group("cm")) * 10
        for match in _STRIP_LENGTH.finditer(_text(page))
    }


def floorplan_for(page: str, model: str) -> str | None:
    """This model's layout drawing, from the set every page carries."""
    wanted = model.lower()
    for match in _FLOORPLAN.finditer(page):
        if match.group("code") == wanted:
            return match.group(0)
    return None


def _reconciles(product: JoaProduct) -> tuple[bool, str]:
    """`(ok, why not)` — whether the page's length agrees with the model's own code.

    Joa publish no mass in running order, so the usual `payload == MTPLM - MRO` is true
    by construction and checks nothing. What they do publish is a **naming convention**:
    the number in the code is the length in decimetres, and it holds to within 110mm on
    all ten. So a 150mm band passes every real vehicle and catches a misread.

    It is not theoretical. The 63T's own page states `5,99 m long`, which is the 60G's
    length — the Technical Book says 6.36m and FMLV holds 6360 — and it misses its
    implied 6300mm by 310mm.

    **A failure drops the length, not the product**, which is the opposite of what a
    columnar source does and is right for the same reason Moto-Trek keeps a page with
    one bad cell: one URL is one vehicle here, so there is no alignment to have gone
    wrong and no reason to distrust the other nine figures. The 63T's width, height and
    payload are all correct and all disagree with what FMLV holds, so dropping the
    product would lose two real corrections and make a live vehicle look discontinued.
    A blanked length arrives as a `MissingField`, which shows the reviewer FMLV's own
    figure beside "nothing scraped" and leaves it alone — `docs/adapters/README.md` on
    a figure that could not be found.

    A product with no length at all passes, having nothing to contradict; `collect`
    warns about that separately.
    """
    if product.mh_length_mm is None:
        return True, ""
    gap = abs(product.mh_length_mm - product.implied_length_mm)
    if gap <= LENGTH_TOLERANCE_MM:
        return True, ""
    return False, (
        f"the page states {product.mh_length_mm}mm but the model code implies about "
        f"{product.implied_length_mm}mm, a {gap}mm gap against a {LENGTH_TOLERANCE_MM}mm "
        f"tolerance — the length has probably been copied from a neighbouring model"
    )


def length_from_the_strip(product: JoaProduct) -> int | None:
    """The strip's length for this model, but only when it passes the same code check.

    The strip is the second reading of a figure the summary strip got wrong, so it earns
    its place only by satisfying the check the summary failed. Requiring that means a
    page whose strip is *also* wrong still ends with a blank length rather than with a
    different wrong one.
    """
    if product.strip_length_mm is None:
        return None
    if abs(product.strip_length_mm - product.implied_length_mm) > LENGTH_TOLERANCE_MM:
        return None
    return product.strip_length_mm


def width_disagreement(product: JoaProduct) -> str | None:
    """Where the summary strip's width contradicts the technical panel's, if it does.

    Only six of the ten pages print a width in the strip, so this is a cross-check that
    is available where it is available rather than a required one.
    """
    strip, panel = product.width_strip_mm, product.mh_width_mm
    if strip is None or panel is None or abs(strip - panel) <= 10:
        return None
    return (
        f"the summary strip says {strip}mm wide and the technical panel says {panel}mm; "
        f"the panel's figure is the one recorded"
    )


# --- What reaches the reviewer -------------------------------------------------------

#: How each habitation reading is introduced where `habitation` supplies no wording.
_FEATURE_NOTES: dict[str, str] = {
    "heating": "the page's own 'Type of heating' row",
    "refrigeration": "the page's own 'Refrigerator' row",
    "shower_toilet_separated": "the washroom in this model's equipment list",
    "bed_types": "the beds in this model's equipment list",
}


def _build_extracted_motorhome(
    product: JoaProduct,
    source_url: str,
    equipment: tuple[str, ...] = (),
    floorplan_url: str | None = None,
) -> ExtractedMotorhome:
    """One model as a `Motorhome`, plus the provenance a reviewer sees beside each field.

    The habitation fields reach the reviewer as **findings** rather than proposals; see
    `product_model.findings`. `heating` and `refrigeration` come from the technical
    panel's labelled rows rather than from `equipment`, because the overlay's chassis
    section carries a stray fridge line on the motorhomes — see the module docstring.
    """
    labelled = tuple(
        line
        for line in (product.heating_published, product.refrigerator_published)
        if line
    )
    features = habitation.features_from(labelled + equipment)

    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.manufacturer_range,
        model=product.model,
        base_vehicle_manufacturer=fmlv_base_vehicle(BASE_VEHICLE),
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
        # Habitation, from the page's own labelled rows and its equipment overlay —
        # reported as findings rather than proposed, so the pipeline never writes them.
        heating=features["heating"].value if "heating" in features else None,
        refrigeration=(
            features["refrigeration"].value if "refrigeration" in features else None
        ),
        shower_toilet_separated=(
            features["shower_toilet_separated"].value
            if "shower_toilet_separated" in features
            else None
        ),
        bed_types=features["bed_types"].value if "bed_types" in features else [],
        microwave=features["microwave"].value if "microwave" in features else None,
    )

    provenance: dict[str, Provenance] = {}

    def record(field: str, snippet: str) -> None:
        provenance[field] = Provenance(
            source_url=source_url, snippet=f"{product.label} — {snippet}"
        )

    if product.mh_length_mm is not None:
        record(
            "mh_length_mm",
            f"'{product.mh_length_mm / 1000:.2f} m long', from the summary strip beside "
            f"the Configure button. The technical panel's 'Width / Length' row is "
            f"mislabelled and its second figure is the height, not this",
        )
    if product.mh_width_mm is not None:
        record("mh_width_mm", f"technical panel, Width / Length: {product.mh_width_mm / 10:.0f} cm wide")
    if product.mh_height_mm is not None:
        record(
            "mh_height_mm",
            f"technical panel, Width / Length: {product.mh_height_mm / 10:.0f} cm — the "
            f"row's second figure, which is the height despite the label saying length",
        )
    if product.mh_passenger_seats_inc_driver is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"'{product.mh_passenger_seats_inc_driver} seats', the belted seats fitted as "
            f"standard. Pilote's Technical Book prints '●4 - ○5' on the 75s and prices a "
            f"fifth seatbelt at £1,240, so the upper figure is an option, not the base "
            f"vehicle",
        )
    if product.berths is not None:
        record(
            "berths",
            f"'{product.berths} berths'. The electric drop-down bed over the lounge is a "
            f"£1,760 option (and unavailable on the 60F), so the standard sleeping "
            f"capacity is what is recorded",
        )
    if product.mh_payload_kilograms is not None:
        record("mh_payload_kilograms", f"technical panel, Payload capacity: {product.mh_payload_kilograms} kg")
    record(
        "mtplm_kilograms",
        f"{MTPLM_KILOGRAMS}kg, MANUALLY SOURCED from {MTPLM_SOURCE}, because Joa publish "
        f"no maximum authorised mass on the website and the book is not hosted there. It "
        f"is the base figure: a 3.65T derate is priced separately as a £390 option. Not "
        f"machine-readable and not refreshed by later runs — re-verify at the next "
        f"model-year changeover",
    )
    if product.mro_kilograms is not None:
        record(
            "mro_kilograms",
            f"derived: {MTPLM_KILOGRAMS}kg maximum authorised mass - "
            f"{product.mh_payload_kilograms}kg payload = {product.mro_kilograms}kg. Joa "
            f"publish no mass in running order anywhere; their own note defines the "
            f"payload as exactly this difference",
        )
    if product.rrp_pounds is not None:
        record(
            "rrp_pounds",
            (
                f"£{product.rrp_pounds:,}, MANUALLY SOURCED from {PRICE_LIST_SOURCE}, "
                f"because the panel-van pages carry no price. Including 20% VAT and "
                f"transport — Joa's list is headed 'Delivered'"
                if product.price_manually_sourced
                else f"'starting from £{product.rrp_pounds:,}', the page's own headline "
                f"figure. Including 20% VAT and transport, the basis Joa's price list "
                f"heads 'Delivered'"
            ),
        )
    record(
        "base_vehicle_manufacturer",
        f"{BASE_VEHICLE}. Asserted, not read: the site names no chassis, and Pilote's "
        f"Technical Book gives 'Fiat CCS' for every motorhome and 'Fiat Chassis Cab' for "
        f"every van",
    )
    record(
        "body_type",
        (
            "Joa build no A-class and no over-cab bed — their only elevated bed is an "
            "optional electric drop-down over the lounge — so every motorhome is a low "
            "profile coachbuilt"
            if product.manufacturer_range == "Motorhome"
            else f"{product.mh_height_mm}mm tall, above the {HIGH_TOP_ABOVE_MM}mm high-top "
            f"threshold. The lacquered pop-up roof is a £6,080 option, so by the "
            f"base-vehicle rule it does not change the body type"
        ),
    )
    # Both halves of the identity, together. `compare_fields` only walks fields that have
    # provenance, so a model read but left unrecorded is neither compared nor reported.
    record(
        "manufacturer_range",
        f"'{product.manufacturer_range}', the range FMLV holds. The site groups these by "
        f"body type instead — 'Our motorhomes' and 'Our panel vans' — and Pilote's book "
        f"says 'Motorhomes' and 'Panelvans'; neither is what the export contains. Paired "
        f"with the model below, accept or reject both together",
    )
    record(
        "model",
        f"'{product.model}', the layout code from the page's own URL. Paired with the "
        f"range above: together they name this vehicle",
    )

    for name, feature in features.items():
        note = feature.note or _FEATURE_NOTES.get(name, "read from the page")
        record(name, f"{note}: {feature.snippet}")
    if equipment and "microwave" not in features:
        # Left unset, so `findings.SILENCE_MEANS` supplies the recommendation and its own
        # wording. This list is the model's complete standard specification, and the word
        # appears nowhere in Pilote's Technical Book either.
        record(
            "microwave",
            "no microwave in this model's equipment list, and none anywhere in Pilote's "
            "2027 Technical Book for the brand",
        )
    if unclear := habitation.heating_is_unclear(labelled + equipment):
        if "heating" not in features:
            record("heating", f"a heater is listed but its kind is not named: {unclear}")

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
    """Collect every current Joa model, or just the named body types.

    One fetch for the sitemap, then one per model page. A page that cannot be fetched or
    parsed is narrated and skipped rather than raised — one broken page should not cost
    the other nine.
    """
    on_progress(f"fetching the vehicle sitemap: {SITEMAP_URL}")
    sitemap = http.fetch(SITEMAP_URL)
    if sitemap.status_code != 200:
        raise RuntimeError(
            f"{SITEMAP_URL} returned {sitemap.status_code}; the roster comes from the "
            f"sitemap because the in-page links carry five alias slugs"
        )
    sitemap_xml = sitemap.file_path.read_text(encoding="utf-8", errors="replace")

    wanted = {prefix for prefix, _label in ranges}
    urls = [
        url
        for url in find_model_urls(sitemap_xml)
        if any(f"/vehicle/{prefix}-" in url for prefix in wanted)
    ]
    on_progress(f"{len(urls)} model page(s) in the sitemap for {sorted(wanted)}")

    results: list[ExtractedMotorhome] = []
    for url in urls:
        page_result = http.fetch(url)
        if page_result.status_code != 200:
            on_progress(f"SKIPPED: {url} returned {page_result.status_code}")
            continue
        page = page_result.file_path.read_text(encoding="utf-8", errors="replace")
        slug = url.rstrip("/").rsplit("/", 1)[-1]

        product = parse_model_page(page, slug)
        if product is None:
            on_progress(f"SKIPPED: {url} carries no recognisable model code")
            continue

        reconciles, why_not = _reconciles(product)
        if not reconciles:
            # The page states the length twice. Where the summary strip fails the code
            # check, the model strip's own figure is tried before the length is given
            # up — see `length_from_the_strip`. Everything else on the page stands
            # either way, so the product is still worth proposing.
            if (repaired := length_from_the_strip(product)) is not None:
                on_progress(
                    f"[{product.label}] LENGTH TAKEN FROM THE MODEL STRIP "
                    f"({repaired}mm) because {why_not}"
                )
                product = replace(product, mh_length_mm=repaired)
            else:
                on_progress(
                    f"[{product.label}] LENGTH DISCARDED and left for FMLV's own "
                    f"figure: {why_not}"
                )
                product = replace(product, mh_length_mm=None)
        elif product.mh_length_mm is None:
            on_progress(
                f"[{product.label}] WARNING: no length in the summary strip, so it could "
                f"not be checked against the model code and is left blank"
            )

        if disagreement := width_disagreement(product):
            on_progress(f"[{product.label}] WARNING: {disagreement}")
        if product.price_manually_sourced:
            on_progress(
                f"[{product.label}] price £{product.rrp_pounds:,} taken from "
                f"{PRICE_LIST_SOURCE}: the panel-van pages carry none"
            )

        equipment = parse_equipment(page)
        if not equipment:
            on_progress(
                f"[{product.label}] WARNING: no 'View all equipment' overlay found, so "
                f"this model gets no habitation findings"
            )
        floorplan_url = floorplan_for(page, product.model)
        if floorplan_url is None:
            on_progress(f"[{product.label}] WARNING: no layout drawing found on {url}")

        results.append(
            _build_extracted_motorhome(product, url, equipment, floorplan_url)
        )

    on_progress(
        f"{len(results)} product(s) collected. Maximum authorised mass is "
        f"{MTPLM_KILOGRAMS}kg on every one, from {MTPLM_SOURCE} rather than the website — "
        f"re-verify it at the model-year changeover"
    )
    return results
