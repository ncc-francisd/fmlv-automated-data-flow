"""Le Voyageur — 18 A-class layouts across two ranges, from the UK site's own pages.

`docs/adapters/le-voyageur.md` is the survey; this is what it decided.

**One URL is one vehicle**, and every page carries a summary block holding length, width,
both heights, four different occupancy counts, payload, MTPLM, chassis and hold volume
with no gaps on any of the 18. So there is no column to align and none of the defences
that dominate `morelo.py` or `burstner.py` are needed.

Four things about this source drive the whole module:

* **The roster comes from `/find-your-motorhome/` and nowhere else.** `sitemap.xml` on the
  `.uk` domain describes the *French* site, in the previous generation's naming, and lists
  a Liner range the UK does not sell. The `/find-your-motorhome/<range>` paths are
  client-side filter anchors that return HTTP 500. Take the hrefs from the index.
* **The model string is normalised, never taken verbatim.** The page's `<h1>` gives the
  code, but its spacing does not match FMLV's and the identity tokeniser is brutal about
  it: `LV7.0 GJF` and FMLV's `LV7.0GJF` score **0.25** against each other, so emitting the
  heading as printed would orphan that product. See `_fmlv_model`.
* **`Hertiage` is FMLV's spelling and this adapter reproduces it.** See `_FMLV_RANGES`.
* **Habitation comes from the 2027 handbook, not from the page.** The pages carry
  marketing prose, and on the Héritage 8.7s that prose advertises "ALDE heating" — which
  the handbook prices as a **£2,290 option** against a standard Truma Combi 6E. Reading
  the copy would report wet central heating on a blown-air vehicle. See `_HABITATION`.

The self-check is the model code: Le Voyageur name every layout after its own length, and
it holds to within 50mm on 16 of the 18. The two that fail are the LVXH7.6 pair, which
publish the LVXH7.9's 7.91 m — see `_reconciles`.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.enums import BodyType, Heating
from ..product_model.model import Motorhome
from .base import ExtractedMotorhome, Provenance, floorplan_provenance, fmlv_base_vehicle

BASE_URL = "https://www.levoyageur-motorhome.uk"
MANUFACTURER = "Le Voyageur"
MANUFACTURER_DISPLAY_NAME = "Le Voyageur"

#: The only page that lists the range. See the module docstring on why not the sitemap.
INDEX_URL = f"{BASE_URL}/find-your-motorhome/"

#: `(url path segment, FMLV manufacturer_range)`.
#:
#: **`Hertiage` is not a typo here — it is FMLV's own spelling**, transposed from
#: Heritage, on all four rows the export holds (10 September 2026). The adapter reproduces
#: it deliberately, because it cannot be corrected from here: the identity tokeniser
#: scores a same-layout pair whose range spelling differs at **0.600**, and two *different*
#: layouts in the same range also score 0.600 (`LVXH7.6 CF` against `LVXH7.9 CF`). No
#: threshold separates "this is the same vehicle, renamed" from "this is a different
#: vehicle", so proposing the fix risks pairing a new layout onto an existing row.
#:
#: Fixing the spelling is a hand edit in FMLV. When it is done, change this to `Heritage`
#: and the run after that will match at 1.000 again.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (
    ("eterna", "Eterna"),
    ("heritage", "Hertiage"),
)
_FMLV_RANGES = dict(DEFAULT_RANGES)

#: Distinct layouts in the same range score **0.600** against each other, because the
#: tokeniser splits `LVXH7.6 CF` into `{lvxh7, 6, cf}` and only the decimal differs. The
#: 0.5 default would let a *new* layout claim an existing row on tie-break order alone; at
#: 0.75 the true pairs (1.000) clear it and every false pair is excluded outright. This is
#: the per-manufacturer opt-in `docs/adapters/README.md` describes.
MATCH_THRESHOLD = 0.75

#: How far the published length may sit from the one the model code implies.
#:
#: 16 of the 18 agree to within 50mm and the two failures miss by 310mm, so a 100mm band
#: sits in clean air between the two groups. See `_reconciles`.
LENGTH_TOLERANCE_MM = 100

#: Base vehicle per range. `Fiat AL-KO` and `MERCEDES` are what the pages print; AL-KO is
#: the chassis maker rather than the base vehicle and must never reach FMLV, and Mercedes
#: is never written `Mercedes-Benz` in this role. Both go through `fmlv_base_vehicle`.
_BASE_VEHICLES = {"Eterna": "Fiat", "Hertiage": "Mercedes"}

#: **A manually sourced constant table.** No page carries a price — checked on all 18, on
#: the index, and in the catalogue — so these come from the 2027 UK retail price list,
#: which arrives by email and is on no website.
#:
#: **Prices are banded by size, not set per layout**: nine figures cover eighteen
#: vehicles, and the list carries no layout suffixes at all. So this is keyed on the size
#: prefix (`LV 7.8` prices all four 7.8 layouts) and `_price_for` does that lookup.
#:
#: Basis: "RETAIL PRICE INCLUDING TRANSPORT & TAXES". That matches Joa's list and *not*
#: Pilote's, which excludes transport — nothing here may be shared with either.
PRICES_BY_SIZE: dict[tuple[str, str], int] = {
    ("Eterna", "6.8"): 130_900,
    ("Eterna", "7.0"): 131_900,
    ("Eterna", "7.5"): 137_900,
    ("Eterna", "7.8"): 140_900,
    ("Eterna", "8.5"): 151_900,
    ("Hertiage", "6.9"): 151_000,
    ("Hertiage", "7.6"): 159_000,
    ("Hertiage", "7.9"): 162_000,
    ("Hertiage", "8.7"): 172_000,
}
PRICE_LIST_SOURCE = "the 2027 UK retail price list, valid from 1 July 2026"

#: **Also manually sourced, and for a reason worth stating.** The 2027 specifications and
#: dealer handbook carries per-layout `● standard ○ option - not available` tables, which
#: attribute a fitment to one vehicle. The website carries marketing prose, which does
#: not — and on the Héritage 8.7 pages that prose says "ALDE heating" while the handbook
#: prices the Alde boiler as a £2,290 option against a standard Truma Combi 6E. Reading
#: the page would report a wet system on a blown-air vehicle.
#:
#: So these four facts come from the handbook's tables and are stated as findings for a
#: person to type in, never proposed. All 18 share the heating and the refrigeration; only
#: the light-chassis 7.0 GJF differs on the washroom.
_HANDBOOK_SOURCE = (
    "the 2027 specifications and dealer handbook, which marks it standard on this layout"
)
_HEATING_NOTE = (
    "Truma Combi 6E hot water/heating (diesel), standard on all 18 layouts. The Alde "
    "diesel/230 V boiler is a £2,290 option and sits inside the Luxury and Excellence "
    "packs, so the standard fitment is blown air even where the page's own copy "
    "advertises Alde"
)

#: The one layout with a combined shower rather than a separate one, per the handbook's
#: bathroom rows. It is the only light vehicle in the range and differs on a dozen fields.
LIGHT_VEHICLE_MODEL = "LV7.0GJF"

# --- Reading the roster ----------------------------------------------------------------

#: A layout link on the index. Both absolute and root-relative forms appear.
_LAYOUT_HREF = re.compile(
    r'href="(?:https?://[^"/]*)?(/motorhome/(?P<range>[^"/]+)/(?P<slug>[^"/]+)/)"'
)

#: The model code, from the page's own `<h1>`: `LV7.8CF`, `LVXH 6.9 LF`, `LV7.0 GJF`.
_HEADING_CODE = re.compile(
    r"<h1[^>]*>\s*(?P<prefix>LVXH|LV)\s*(?P<size>\d\.\d)\s*(?P<suffix>[A-Z]{2,3})\s*</h1>",
    re.I,
)

_TAGS = re.compile(r"(?is)<(script|style)\b.*?</\1>")


def plain_text(html: str) -> str:
    """The page as one line of text, tags replaced by a single space.

    A single space and not a marker: this site splits a label from its value across
    elements, so anything else welds `Length` onto `7.85 m`.
    """
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", _TAGS.sub(" ", html))).strip()


def find_model_urls(index_html: str, ranges: Iterable[str]) -> list[str]:
    """Every layout page the index links, in index order, deduplicated.

    Restricted to the range segments asked for, so `--range eterna` reads ten pages
    rather than eighteen.
    """
    wanted = {segment.lower() for segment in ranges}
    urls: list[str] = []
    for match in _LAYOUT_HREF.finditer(index_html):
        if match.group("range").lower() not in wanted:
            continue
        url = f"{BASE_URL}{match.group(1)}"
        if url not in urls:
            urls.append(url)
    return urls


# --- Reading one page ------------------------------------------------------------------


#: Every label this adapter reads, from both blocks, exactly as the page spells them.
#:
#: The list is the mechanism, not documentation: `_labelled` slices a value from the end
#: of its label to the start of **the next known label**, so a label missing from here
#: does not merely go unread — it lets the value before it run on. Two spellings are
#: deliberate. `Exterior  height` carries a double space in the HTML, and `Side
#: compartement volume` is misspelled; both are consistent across all 18.
_SUMMARY_LABELS: tuple[str, ...] = (
    "Length",
    "Width",
    "Exterior  height",
    "Interior height",
    "Seated places",
    "Sleeping places",
    "Extra sleeping places",
    "Eating places",
    "Seat in",
    "Payload",
    "MTPLM (Gross Weight)",
    "Chassis",
    "Side compartement volume",
    "Rear storage hold - in litres (min / max)",
)

#: Whitespace inside a label matches any run of it. The survey recorded that `Exterior
#: height`'s double space must be matched as-is, but `plain_text` collapses runs of
#: whitespace before this ever sees them — so a literal double space matches nothing and
#: the height came back empty on all 18 in the first real run. Both spellings must work.
def _label_pattern(label: str) -> str:
    return r"\s+".join(re.escape(word) for word in label.split())


#: All known labels as one alternation, longest first so `Interior height` wins over
#: `Width` inside `Interior width` and `Extra sleeping places` over `Sleeping places`.
_ANY_LABEL = re.compile(
    r"(?<![A-Za-z])(?:"
    + "|".join(_label_pattern(label) for label in sorted(_SUMMARY_LABELS, key=len, reverse=True))
    + r")\s*:?"
)


def _labelled(text: str, label: str) -> str | None:
    """The value printed after `label`, stopping where the next known label begins.

    Both blocks are runs of `Label : value` pairs with no separators once the tags are
    gone, and rows go missing — so a probe that takes "everything after the label"
    silently returns the *next label* as its value.

    **Stopping at the next known label rather than at "the next capitalised word" is the
    whole point.** The obvious pattern — run until something that looks like a label —
    reads `Chassis : Fiat AL-KO` as `Fiat AL-` , because `KO Side compartement volume :`
    is itself label-shaped. Values here contain capitals, hyphens and parentheses, so
    only an explicit vocabulary is safe. That bug reached a real run.

    **The colon is optional.** The summary block writes `Label : value`; the detailed
    block writes `Label value` with no punctuation at all, so the hold cross-check reads
    nothing if a colon is required. Every caller takes the leading number or the whole
    slice, so a detailed-block value running into the next unlisted heading is harmless.
    """
    start = re.compile(_label_pattern(label) + r"\s*:?").search(text)
    if start is None:
        return None
    following = _ANY_LABEL.search(text, start.end())
    value = text[start.end() : following.start() if following else len(text)].strip()
    return value or None


def _metres_to_mm(value: str | None) -> int | None:
    """`7.85 m` -> 7850, `3 m` -> 3000. `None` where nothing was printed."""
    if value is None:
        return None
    match = re.search(r"(\d+(?:[.,]\d+)?)", value)
    if match is None:
        return None
    return round(float(match.group(1).replace(",", ".")) * 1000)


def _first_int(value: str | None) -> int | None:
    """The leading integer, so `4+1 optional` gives 4 and `1060 kg` gives 1060.

    Taking the first figure is the settled base-vehicle rule: the fifth seatbelt on the
    two `4+1 optional` layouts is an £880 option, so the standard count is 4.
    """
    if value is None:
        return None
    match = re.search(r"(\d+)", value)
    return int(match.group(1)) if match else None


def _fmlv_model(prefix: str, size: str, suffix: str, manufacturer_range: str) -> str:
    """The model string as FMLV writes it, which is not how the heading prints it.

    FMLV's two ranges use two conventions, and both must be reproduced exactly:

    | range | FMLV holds | the heading prints |
    |---|---|---|
    | Eterna | `LV7.0GJF` | `LV7.0 GJF` |
    | Hertiage | `LVXH7.9 CF` | `LVXH7.9 CF` |
    | Hertiage | `LVXH6.9 LF` | `LVXH 6.9 LF` |

    So Eterna closes up entirely and Héritage keeps exactly one space, before the layout
    letters. This is not cosmetic. The identity tokeniser splits on the decimal point and
    on spaces, so `LV7.0 GJF` becomes `{lv7, 0, gjf}` against FMLV's `{lv7, 0gjf}` — a
    similarity of **0.25**, far below any usable threshold. Emitting the heading verbatim
    would propose that product as new and archive the real one.

    Verified against all 13 layouts the export holds: every one matches exactly.
    """
    prefix, suffix = prefix.upper(), suffix.upper()
    separator = " " if manufacturer_range == _FMLV_RANGES["heritage"] else ""
    return f"{prefix}{size}{separator}{suffix}"


@dataclass(frozen=True)
class LeVoyageurProduct:
    """One layout, as its own page states it."""

    source_url: str
    manufacturer_range: str
    model: str
    #: The decimal in the model code — `7.8` — which is both the length claim and the
    #: price-list key. See `_reconciles` and `_price_for`.
    size: str
    #: The layout letters — `CF`, `GJL`, `LF`. Kept apart from `model` because the
    #: floorplan filenames close the space up regardless of the range's convention.
    suffix: str = ""
    mh_length_mm: int | None = None
    mh_width_mm: int | None = None
    mh_height_mm: int | None = None
    interior_height_mm: int | None = None
    mh_passenger_seats_inc_driver: int | None = None
    berths: int | None = None
    extra_berths: int | None = None
    eating_places: int | None = None
    mh_payload_kilograms: int | None = None
    mtplm_kilograms: int | None = None
    chassis_published: str | None = None
    #: The hold volume, printed in both blocks — a free cross-check that the two blocks
    #: were read off the same vehicle. See `hold_disagreement`.
    hold_litres_summary: int | None = None
    hold_litres_detail: int | None = None
    #: What the seats row literally said, so `4+1 optional` reaches the reviewer.
    seats_published: str | None = None

    @property
    def label(self) -> str:
        return f"{self.manufacturer_range} {self.model}"

    @property
    def mro_kilograms(self) -> int | None:
        """Derived: MTPLM minus payload. Le Voyageur publish no mass in running order.

        This is a derivation and **not** a self-check — the identity is true by
        construction, exactly as at Murvi and Joa. It is also what FMLV already holds:
        on all 15 live rows the stored MRO is precisely `MTPLM - published payload`, so
        the site is where FMLV's own figures came from and this reproduces them.
        """
        if self.mtplm_kilograms is None or self.mh_payload_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mh_payload_kilograms

    @property
    def body_type(self) -> BodyType:
        """A-class, for all 18. Every layout is an integrated coachbuilt 2.6-3.1 m tall.

        FMLV holds A-class on all 15 live rows and the range has no low-profile or van
        derivative, so this is a range fact rather than an inference from the height.
        """
        return BodyType.A_CLASS

    @property
    def implied_length_mm(self) -> int:
        """The length the model code claims: `LV7.8CF` -> 7800. See `_reconciles`."""
        return round(float(self.size) * 1000)


def parse_model_page(page: str, source_url: str) -> LeVoyageurProduct | None:
    """One layout from its own page, or `None` if the heading carries no model code."""
    segment = source_url.rstrip("/").split("/")[-2].lower()
    manufacturer_range = _FMLV_RANGES.get(segment)
    heading = _HEADING_CODE.search(page)
    if manufacturer_range is None or heading is None:
        return None

    text = plain_text(page)
    seats = _labelled(text, "Seated places")
    return LeVoyageurProduct(
        source_url=source_url,
        manufacturer_range=manufacturer_range,
        model=_fmlv_model(
            heading.group("prefix"),
            heading.group("size"),
            heading.group("suffix"),
            manufacturer_range,
        ),
        size=heading.group("size"),
        suffix=heading.group("suffix").upper(),
        mh_length_mm=_metres_to_mm(_labelled(text, "Length")),
        mh_width_mm=_metres_to_mm(_labelled(text, "Width")),
        # Matched with its double space, exactly as the page prints it.
        mh_height_mm=_metres_to_mm(_labelled(text, "Exterior  height")),
        interior_height_mm=_metres_to_mm(_labelled(text, "Interior height")),
        mh_passenger_seats_inc_driver=_first_int(seats),
        berths=_first_int(_labelled(text, "Sleeping places")),
        extra_berths=_first_int(_labelled(text, "Extra sleeping places")),
        eating_places=_first_int(_labelled(text, "Eating places")),
        mh_payload_kilograms=_first_int(_labelled(text, "Payload")),
        mtplm_kilograms=_first_int(_labelled(text, "MTPLM (Gross Weight)")),
        chassis_published=_labelled(text, "Chassis"),
        # Misspelled on the page, and consistently so.
        hold_litres_summary=_first_int(_labelled(text, "Side compartement volume")),
        hold_litres_detail=_first_int(
            _labelled(text, "Rear storage hold - in litres (min / max)")
        ),
        seats_published=seats,
    )


#: A layout drawing. *Implantation* is French for layout, and the files are named after
#: the model with the space closed up: `Implantations-LVXH-8.7GJF-1920x618.png`. Every
#: page carries several of them at several widths, so the join is a code match and the
#: largest rendering wins.
_FLOORPLAN = re.compile(
    r"https://[^\"' ]*/Implantations-(?P<prefix>LVXH|LV)-(?P<code>[0-9.]+[A-Z]*)"
    r"(?:-(?P<width>\d+)x\d+)?\.png",
    re.I,
)


def floorplan_for(page: str, product: LeVoyageurProduct) -> str | None:
    """This layout's drawing, from the set the page carries, at its largest rendering.

    Matched on prefix and code exactly. **Eight of the eighteen have no drawing in the
    rendered markup** (10 September 2026): LV6.8LF, LV7.5CF, LV7.5GJF, LV8.5CF, LVXH6.9
    LF, both LVXH7.6s and LVXH7.9 GJL. Two different causes, and neither is worth
    guessing around — some layouts simply have no file, and the LV6.8LF's is named
    `Implantations-LV-6.8.png` with its `LF` dropped.

    A bare-size fallback is deliberately not attempted: `7.5` alone is ambiguous between
    the CF and the GJF, and pointing a reviewer at the wrong layout's drawing is worse
    than pointing them at none. `collect` narrates every miss.
    """
    wanted = f"{product.size}{product.suffix}".upper()
    best: tuple[int, str] | None = None
    # Script and style bodies are removed first, as everywhere else in this module. A
    # drawing referenced only from a lazy-loader's JSON is not on the rendered page, and
    # matching it made the adapter behave differently against a captured fixture than
    # against the live site — which is the one thing a fixture exists to prevent.
    for match in _FLOORPLAN.finditer(_TAGS.sub(" ", page)):
        if match.group("code").upper() != wanted:
            continue
        width = int(match.group("width") or 0)
        if best is None or width > best[0]:
            best = (width, match.group(0))
    return best[1] if best else None


def _price_for(product: LeVoyageurProduct) -> int | None:
    """The price of this layout's **size band**, from the emailed 2027 list.

    Nine prices cover eighteen layouts and the list names no suffixes, so every 7.8
    Eterna is £140,900. A per-layout lookup would find nothing.
    """
    return PRICES_BY_SIZE.get((product.manufacturer_range, product.size))


# --- The self-checks -------------------------------------------------------------------


def _reconciles(product: LeVoyageurProduct) -> tuple[bool, str]:
    """`(ok, why not)` — whether the published length agrees with the model's own code.

    Le Voyageur name every layout after its overall length, and it is the strongest
    redundancy on the site because it is *positional*: it catches a length read off the
    wrong row or the wrong layout, which is the failure that otherwise yields plausible,
    internally consistent motorhomes carrying each other's dimensions.

    16 of the 18 agree to within 50mm. **The two that fail are the LVXH7.6 pair, both
    published as 7.91 m — byte-identical to the LVXH7.9 layouts beside them in the
    index**, and 310mm from their own implied 7.60 m. Three things say the site is wrong
    rather than the convention: the naming convention the other 16 follow exactly; the
    2027 handbook, which gives 766 cm for both; and the 7.9 pair's own identical figure,
    which is the tell of a copy between adjacent pages.

    **A failure drops the length, not the product.** One URL is one vehicle here, so
    there is no alignment to have gone wrong and no reason to distrust the other eleven
    figures on the page — the same reasoning as `joa.py`. A blanked length arrives as a
    missing field, which shows the reviewer FMLV's own figure beside "nothing scraped"
    rather than overwriting it.

    A product with no length at all passes, having nothing to contradict; `collect`
    warns about that separately.
    """
    if product.mh_length_mm is None:
        return True, ""
    gap = abs(product.mh_length_mm - product.implied_length_mm)
    if gap <= LENGTH_TOLERANCE_MM:
        return True, ""
    return False, (
        f"the page states {product.mh_length_mm}mm but the model code implies "
        f"{product.implied_length_mm}mm, a {gap}mm gap against a "
        f"{LENGTH_TOLERANCE_MM}mm tolerance — the length has probably been copied from "
        f"a neighbouring layout"
    )


def hold_disagreement(product: LeVoyageurProduct) -> str | None:
    """Where the two blocks disagree about the hold volume, if they do.

    The summary block's `Side compartement volume` and the detailed block's `Rear storage
    hold` carry the same number on all 18, under different labels in different sections.
    It corroborates no field FMLV records, but it checks that the two blocks were read
    off one vehicle — which is the thing a page-structure change would break first.
    """
    summary, detail = product.hold_litres_summary, product.hold_litres_detail
    if summary is None or detail is None or summary == detail:
        return None
    return (
        f"the summary block says {summary} l of hold and the detailed block says "
        f"{detail} l; the two blocks may not describe the same vehicle"
    )


def chassis_disagreement(product: LeVoyageurProduct) -> str | None:
    """Where the page's chassis contradicts the range's, if it does.

    Only two values exist across the 18 — `Fiat AL-KO` on every Eterna and `MERCEDES` on
    every Héritage — so a page saying anything else means the range mapping or the page
    itself has changed.
    """
    published = (product.chassis_published or "").upper()
    expected = _BASE_VEHICLES[product.manufacturer_range].upper()
    if not published or expected in published:
        return None
    return (
        f"the page's chassis reads {product.chassis_published!r}, which is not the "
        f"{_BASE_VEHICLES[product.manufacturer_range]} this range is built on"
    )


# --- What reaches the reviewer ---------------------------------------------------------


def _build_extracted_motorhome(
    product: LeVoyageurProduct,
    floorplan_url: str | None = None,
) -> ExtractedMotorhome:
    """One layout as a `Motorhome`, plus the provenance a reviewer sees beside each field.

    The habitation fields are **findings** rather than proposals, and they come from the
    2027 handbook rather than the page — see `_HANDBOOK_SOURCE` and the module docstring
    on why the page's own copy cannot be trusted for heating.
    """
    source_url = product.source_url
    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.manufacturer_range,
        model=product.model,
        base_vehicle_manufacturer=fmlv_base_vehicle(
            _BASE_VEHICLES[product.manufacturer_range]
        ),
        rrp_pounds=_price_for(product),
        mro_kilograms=product.mro_kilograms,
        mtplm_kilograms=product.mtplm_kilograms,
        mh_payload_kilograms=product.mh_payload_kilograms,
        mh_length_mm=product.mh_length_mm,
        mh_width_mm=product.mh_width_mm,
        mh_height_mm=product.mh_height_mm,
        mh_passenger_seats_inc_driver=product.mh_passenger_seats_inc_driver,
        berths=product.berths,
        body_type=product.body_type,
        # Findings, from the handbook's per-layout tables. Never written by the pipeline.
        #
        # `refrigeration` is deliberately absent. The handbook says "Compression
        # refrigerator" and gives its litres, but that is the cooling technology, not
        # what FMLV's field asks — which is fridge against fridge-freezer. Nothing in
        # either document mentions a freezer compartment, and silence is not a negative,
        # so there is no honest reading to report here.
        heating=Heating.BLOWN_AIR,
        shower_toilet_separated=product.model != LIGHT_VEHICLE_MODEL,
        microwave=False,
    )

    provenance: dict[str, Provenance] = {}

    def record(field: str, snippet: str) -> None:
        provenance[field] = Provenance(
            source_url=source_url, snippet=f"{product.label} — {snippet}"
        )

    if product.mh_length_mm is not None:
        record("mh_length_mm", f"summary block, 'Length : {product.mh_length_mm / 1000:g} m'")
    if product.mh_width_mm is not None:
        record("mh_width_mm", f"summary block, 'Width : {product.mh_width_mm / 1000:g} m'")
    if product.mh_height_mm is not None:
        record(
            "mh_height_mm",
            f"summary block, 'Exterior height : {product.mh_height_mm / 1000:g} m'",
        )
    if product.mh_passenger_seats_inc_driver is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"summary block, 'Seated places : {product.seats_published}'"
            + (
                " — the fifth belt is an £880 option, so the standard figure is recorded"
                if product.seats_published and "+" in product.seats_published
                else ""
            ),
        )
    if product.berths is not None:
        record(
            "berths",
            f"summary block, 'Sleeping places : {product.berths}'"
            + (
                f", with 'Extra sleeping places : {product.extra_berths}' left out as "
                f"the optional figure"
                if product.extra_berths
                else ""
            ),
        )
    if product.mtplm_kilograms is not None:
        record(
            "mtplm_kilograms",
            f"summary block, 'MTPLM (Gross Weight) : {product.mtplm_kilograms} kg'",
        )
    if product.mh_payload_kilograms is not None:
        record(
            "mh_payload_kilograms",
            f"summary block, 'Payload : {product.mh_payload_kilograms} kg'",
        )
    if product.mro_kilograms is not None:
        record(
            "mro_kilograms",
            f"derived as MTPLM {product.mtplm_kilograms} kg minus payload "
            f"{product.mh_payload_kilograms} kg = {product.mro_kilograms} kg. Le "
            f"Voyageur publish no mass in running order anywhere, and FMLV's own stored "
            f"MRO is this same arithmetic on all 15 rows it holds",
        )
    if motorhome.rrp_pounds is not None:
        provenance["rrp_pounds"] = Provenance(
            source_url=None,
            snippet=(
                f"{product.label} — £{motorhome.rrp_pounds:,} from {PRICE_LIST_SOURCE}. "
                f"No Le Voyageur page carries a price; the list is banded by size, so "
                f"this is the {product.manufacturer_range} {product.size} figure and "
                f"every layout of that size shares it"
            ),
        )
    record(
        "body_type",
        "A-class: every Le Voyageur layout is an integrated coachbuilt, and the range "
        "has no low-profile or van derivative",
    )

    for field, snippet in (
        ("heating", _HEATING_NOTE),
        (
            "shower_toilet_separated",
            "a separate shower with its own 400 x 400 mm skylight"
            if product.model != LIGHT_VEHICLE_MODEL
            else "a combined shower with a sliding curtain, not a separate one — this is "
            "the only layout in the range without one",
        ),
        (
            "microwave",
            "no microwave as standard: the handbook prices one at £440 as an option and "
            "marks it standard only inside the Excellence packs",
        ),
    ):
        provenance[field] = Provenance(
            source_url=None, snippet=f"{product.label} — {snippet}; {_HANDBOOK_SOURCE}"
        )

    if floorplan_url is not None:
        # One pointer per positional field still unanswered, so the drawing link sits
        # beside the question a person is actually being asked.
        provenance.update(
            floorplan_provenance(motorhome, floorplan_url, product.label)
        )

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


# --- The run ---------------------------------------------------------------------------


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 - plain HTTP throughout; no JavaScript on this site
    snapshot_dir: Path,  # noqa: ARG001 - `Fetcher` owns the snapshot directory
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every layout the index lists, for the ranges asked for."""
    on_progress(f"fetching the model index: {INDEX_URL}")
    index = http.fetch(INDEX_URL)
    if index.status_code != 200:
        message = (
            f"{INDEX_URL} returned {index.status_code}; it is the only page that lists "
            f"the range, and sitemap.xml describes the French site instead"
        )
        raise RuntimeError(message)

    index_html = index.file_path.read_text(encoding="utf-8", errors="replace")
    urls = find_model_urls(index_html, (segment for segment, _label in ranges))
    on_progress(f"{len(urls)} layout page(s) linked from the index")

    results: list[ExtractedMotorhome] = []
    for url in urls:
        page_result = http.fetch(url)
        if page_result.status_code != 200:
            on_progress(f"SKIPPED: {url} returned {page_result.status_code}")
            continue
        page = page_result.file_path.read_text(encoding="utf-8", errors="replace")

        product = parse_model_page(page, url)
        if product is None:
            on_progress(f"SKIPPED: {url} carries no recognisable model code in its <h1>")
            continue

        reconciles, why_not = _reconciles(product)
        if not reconciles:
            on_progress(
                f"[{product.label}] LENGTH DISCARDED and left for FMLV's own figure: "
                f"{why_not}"
            )
            product = replace(product, mh_length_mm=None)
        elif product.mh_length_mm is None:
            on_progress(
                f"[{product.label}] WARNING: no length in the summary block, so it "
                f"could not be checked against the model code and is left blank"
            )

        for disagreement in (hold_disagreement(product), chassis_disagreement(product)):
            if disagreement:
                on_progress(f"[{product.label}] WARNING: {disagreement}")

        if _price_for(product) is None:
            on_progress(
                f"[{product.label}] WARNING: no price — the 2027 list has no "
                f"{product.manufacturer_range} {product.size} band, so this is a new "
                f"size and {PRICE_LIST_SOURCE} needs re-reading"
            )

        floorplan_url = floorplan_for(page, product)
        if floorplan_url is None:
            on_progress(
                f"[{product.label}] no layout drawing in the page's markup, so the "
                f"habitation pack has no floorplan pointer for this one"
            )

        results.append(_build_extracted_motorhome(product, floorplan_url))

    on_progress(f"collected {len(results)} product(s)")
    return results
