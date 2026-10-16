"""Fifth Wheel Co (fifthwheelco.com) — British slide-out caravans, three ranges.

See `docs/adapters/fifth-wheel.md` for the survey. **The source is the brochures**, one
per range, rediscovered from each range page per run.

## The brochures are fetchable, despite the form

Each range page offers its brochure behind an email form. **The form is a gate on the
interface, not on the file**: every page also carries the PDF's own Squarespace `/s/` path
in its markup, and fetching that returns the document. Verified on all three, 16 October
2026. So this adapter needs no stored copy and no manual step.

## These are not conventional touring caravans, and the data shows it twice

**The body slides outwards when parked.** Every brochure publishes `Overall Width` and
`Width with Slide Out Extended`, and only the first is FMLV's — the Celtic Rambler's
extended width is 3.3m against a travelling 2.3m. The reading is anchored on the label, as
it must be: magnitude cannot tell them apart safely.

**The Celtic Rambler and Dreamseeker couple to a pickup's bed rather than a tow bar**, so
`Length Behind Tow Vehicle` is *shorter* than the body — the gooseneck overhangs the
truck. The INOS tows conventionally and its is longer. FMLV's own figures show both:

| | shipping | body |
|---|---|---|
| Celtic Rambler | 6500 | 8500 |
| Dreamseeker | 6400 | 7600 |
| INOS | 8200 | 7000 |

So `Length Behind Tow Vehicle` is the shipping length in both geometries, and nothing has
to know which kind of coupling a range uses.

## The self-check, and the one range that fails it

Every brochure publishes `Unit Weight`, `Payload` and `MTPLM`, and they add up:
3,300 + 1,000 = 4,300 on the Celtic Rambler, 2,800 + 1,500 = 4,300 on the Dreamseeker.

**The INOS is published three times with three different unit weights**, and only two of
the three reconcile:

| source | unit | payload | MTPLM | adds up |
|---|---|---|---|---|
| the brochure the email form sends | 2,400 | 400 | 2,800 | **yes** |
| the brochure the site links | 2,600 | 1,000 | 2,800 or 3,500 | **no — 3,600** |
| the range page itself | 2,500 | up to 1,000 | from 2,800 to 3,500 | yes, at 3,500 |

FMLV holds 2,400 / 400 / 2,800, which is the emailed brochure. `_reconciles` therefore
drops any range whose arithmetic does not close, which means the site's INOS brochure is
refused and FMLV's figures stand until Fifth Wheel Co say which is right. That is the
check earning its keep rather than a special case.

## The two mass rules both appear here, one per range

A manufacturer that shows the difference, which is worth stating:

* **Celtic Rambler and Dreamseeker** publish `MTPLM: 4,300kg (3,500kg if downplated for
  towing on standard licence)`. One chassis plated differently, so the band rule applies
  and the **upper** figure is the MTPLM.
* **INOS**'s larger figure needs an **upgraded chassis**, so the base-vehicle rule applies
  and the **base** is recorded.

The test is whether the bigger number needs a different chassis. `_primary_figure` takes
the figure before any bracket, which is the upper limit on the first pair and the base on
the second — both correct, for the same reason in each case: it is what the manufacturer
states plainly before qualifying it.

## The website's own figures are not read

Each range page repeats the masses, and on the INOS it disagrees with both brochures. The
brochure is the authority — it is what FMLV was built from — so the page is fetched only to
find the brochure link, never for a figure.
"""

from __future__ import annotations

import html as htmllib
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from ..fetch.http import Fetcher
from ..fetch.pdf import extract_text
from ..product_model.caravan import Caravan
from ..product_model.enums import CaravanBodyType
from ..vehicle_class import VehicleClass
from . import habitation
from .base import ExtractedCaravan, Provenance, floorplan_provenance

__all__ = [
    "BASE_URL",
    "EXPECTED_PRODUCTS",
    "KNOWN_BERTHS",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "MICRO_CARAVAN_CEILING_KG",
    "MANUFACTURER_SPELLING",
    "RANGE_PATHS",
    "RECORDED_LABELS",
    "VEHICLE_CLASS",
    "Brochure",
    "berths_from",
    "body_type_for",
    "build_extracted",
    "collect",
    "find_brochure_url",
    "parse_brochure",
    "parse_specification",
    "price_from",
]

BASE_URL = "https://fifthwheelco.com"
MANUFACTURER = "Fifth Wheel Co"
MANUFACTURER_DISPLAY_NAME = "Fifth Wheel Co"

#: Towed, so a caravan. Without this the module registers under the motorhome class.
VEHICLE_CLASS = VehicleClass.CARAVAN

#: The three ranges, each its own FMLV product. Written down because the home page links
#: them among twenty other pages with nothing to distinguish a range from `/about` — and
#: because FMLV files each as a one-name product whose range and model are both this name,
#: which no slug gives. `collect` warns if the site stops linking one.
#:
#: **The keys are FMLV's spelling, not the manufacturer's.** Fifth Wheel Co write
#: `Dreamseeker` throughout their site and brochure; FMLV holds `DreamSeeker`. The settled
#: rule is that the export decides the range and model strings, and a casing rename buys a
#: reviewer nothing while touching the identity, which is the one thing a rename can
#: corrupt. Their own spelling goes in the provenance instead.
RANGE_PATHS: dict[str, str] = {
    "Celtic Rambler": "/celtic-rambler",
    "DreamSeeker": "/dreamseeker",
    "INOS": "/inos",
}

#: How the manufacturer spells a range where that differs from FMLV, for the provenance.
MANUFACTURER_SPELLING: dict[str, str] = {"DreamSeeker": "Dreamseeker"}

#: A berth count the brochure does not state as a figure, settled by the requester.
#:
#: **The Celtic Rambler's brochure describes its beds and never counts them**: a *"fitted
#: island king-size bed (1.9m x 1.5m)"* in the master bedroom and a *"2.5m L-shaped
#: slide-out sofa (converts to double bed)"*. Two doubles is four berths, which the
#: requester confirmed on 16 October 2026 — *"it's designed to sleep four people, so that's
#: two double beds, so a four berth"* — and which is what FMLV already holds.
#:
#: Written down rather than counted off the furniture, because the settled rules do not
#: derive a berth figure from bed descriptions and one manufacturer's confirmed answer is
#: not a reason to teach every adapter to try. The provenance says where it came from.
KNOWN_BERTHS: dict[str, tuple[int, str]] = {
    "Celtic Rambler": (
        4,
        "the brochure describes an island king-size bed and a slide-out sofa that "
        "converts to a double, and states no count. Two doubles is four berths, confirmed "
        "by the requester on 16 October 2026",
    ),
}

EXPECTED_PRODUCTS = 3

#: A caravan is a micro only where the manufacturer calls it one **and** its MTPLM is at or
#: below this. The lightest here is 2,800kg, so the ceiling is never reached.
MICRO_CARAVAN_CEILING_KG = 1250

#: `/s/2026-Fifth-Wheel-Company-Celtic-Rambler-Brochure.pdf`. Squarespace serves `/s/`
#: paths directly, which is why the email form can be bypassed.
_BROCHURE_LINK = re.compile(r'["\'](/s/[^"\']*\.pdf)["\']', re.I)

#: A section heading inside the specification table — `EXTERNAL DIMENSIONS`, `MASSES &
#: PAYLOAD`. All capitals, which is what separates them from the labels beneath.
_SECTION_HEADING = re.compile(r"^[A-Z][A-Z &/]{3,}$")

#: A line carrying a measured figure, which is what tells the value column from the label
#: column — **not** whether it begins with a digit.
#:
#: Two of the INOS's three masses are written `up to 1000kg` and `from 2800kg to 3,500kg`,
#: so a pattern anchored on a leading digit misses them and folds them into the value
#: above, leaving fourteen labels against twelve values and the whole table refused. No
#: label on any of the three brochures contains a figure, so the test is safe.
#:
#: `1.6M` on the Celtic Rambler carries a capital `M` where every other line has a
#: lower-case one, so the unit is matched case-blind.
#:
#: **There is no word boundary after the unit, deliberately.** The slide-out areas are
#: given as `5.3m²`, and `²` is a word character in Unicode — so `m\b` fails on exactly
#: those rows, dropping one value and refusing the whole table for want of a pair. No
#: label on any brochure contains a digit, so nothing needs the boundary to stay out.
_HAS_FIGURE = re.compile(r"[\d,]+(?:\.\d+)?\s*(?:m|kg)", re.I)

#: A footnote, which ends the value column.
_FOOTNOTE = re.compile(r"^\s*\*")

#: `Prices from £95,000`. The pound sign does not survive extraction from these PDFs, so
#: it is optional and the figure carries the meaning.
_PRICE = re.compile(r"Prices?\s+from\s*[£]?\s*([\d][\d,\s]{4,})", re.I)

#: `Sleeps up to 5`, `Sleeps 4`. The Celtic Rambler states none.
_SLEEPS = re.compile(r"\bsleeps?\s+(?:up\s+to\s+)?(\d+)\b", re.I)

#: Which of the brochure's labels become FMLV fields. **Everything absent from this map is
#: read and discarded**, which is how `Width with Slide Out Extended` is kept out of the
#: width column — by the label, never by the magnitude.
#:
#: `Overall Length` and `Overall Body Length` are the same row: the INOS uses the longer
#: wording and the other two the shorter.
RECORDED_LABELS: dict[str, str] = {
    "overall length": "exterior_body_length_mm",
    "overall body length": "exterior_body_length_mm",
    "overall height": "height_mm",
    "overall width": "overall_width_mm",
    "length behind tow vehicle": "shipping_length_mm",
    "internal living area height": "headroom_mm",
    "unit weight": "mro_kilograms",
    "payload": "personal_effects_payload_kilograms",
    "mtplm": "mtplm_kilograms",
}


def _plain(fragment: str) -> str:
    return " ".join(htmllib.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def find_brochure_url(page_html: str) -> str | None:
    """The range's brochure, from the `/s/` path its own page carries."""
    match = _BROCHURE_LINK.search(page_html)
    return f"{BASE_URL}{match.group(1)}" if match else None


def _label(line: str) -> str:
    """A brochure label reduced to what identifies it — asterisks and case removed."""
    return re.sub(r"[*\s]+$", "", line.strip()).strip().lower()


def _primary_figure(value: str) -> str:
    """The figure a value states before any bracketed qualifier.

    `4,300kg (3,500kg if downplated…)` gives `4,300kg`, and `1,000kg (200kg if
    downplated)` gives `1,000kg` — the plain statement rather than the exception. That is
    the upper limit where a range offers a downplate and the base where it offers an
    upgraded chassis, which is correct in both cases for the same reason.
    """
    return value.split("(")[0].strip()


def _millimetres(value: str) -> int | None:
    """`8.5m (27'11")` → 8500. Metres to one decimal, so the precision is 100mm."""
    match = re.search(r"([\d.]+)\s*m\b", _primary_figure(value), re.I)
    if match is None:
        return None
    try:
        return round(float(match.group(1)) * 1000)
    except ValueError:
        return None


def _kilograms(value: str) -> int | None:
    match = re.search(r"([\d,]+)\s*kg", _primary_figure(value), re.I)
    return int(match.group(1).replace(",", "")) if match else None


def parse_specification(page_text: str) -> dict[str, str]:
    """The brochure's specification table, as `{label: value}`.

    **The table is columnar**: every label comes first, in order and grouped under its
    section heading, and then every value in the same order. So the two runs are collected
    separately and zipped, and a mismatch in their lengths means the layout has changed —
    which `parse_brochure` refuses rather than pairing a width with a weight.

    A value that wraps onto a second line — `4,300kg (3,500kg if downplated` / `for towing
    on standard licence)` — is joined back onto the one before it. The test for a wrap is
    that the line carries **no figure at all**, which is what separates a continuation from
    a value written in words like `up to 1000kg`.
    """
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    labels: list[str] = []
    values: list[str] = []
    for line in lines:
        if _FOOTNOTE.match(line):
            break
        if _HAS_FIGURE.search(line):
            values.append(line)
        elif values:
            # A continuation of the value above, not a new label.
            values[-1] = f"{values[-1]} {line}"
        elif not _SECTION_HEADING.match(line) and not line.startswith("www."):
            labels.append(line)
    if len(labels) != len(values):
        return {}
    return {_label(label): value for label, value in zip(labels, values, strict=True)}


@dataclass
class Brochure:
    """One range's brochure, as read."""

    manufacturer_range: str
    url: str
    specification: dict[str, str] = field(default_factory=dict)
    rrp_pounds: int | None = None
    berths: int | None = None
    berths_basis: str = ""
    equipment: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return self.manufacturer_range

    def figure(self, field_name: str) -> int | None:
        """The figure this brochure publishes for an FMLV field, or `None`."""
        for label, mapped in RECORDED_LABELS.items():
            if mapped != field_name or label not in self.specification:
                continue
            value = self.specification[label]
            return (
                _kilograms(value) if field_name.endswith("kilograms") else _millimetres(value)
            )
        return None

    @property
    def refused(self) -> dict[str, str]:
        """What the table published that FMLV does not hold, for the run to report."""
        return {
            label: value
            for label, value in self.specification.items()
            if label not in RECORDED_LABELS
        }


def price_from(page_text: str) -> int | None:
    """`Prices from £95,000` on the brochure's overview page."""
    match = _PRICE.search(page_text)
    if match is None:
        return None
    return int(re.sub(r"[\s,]", "", match.group(1)))


def berths_from(page_text: str, *, manufacturer_range: str = "") -> tuple[int | None, str]:
    """`Sleeps up to 5`, where the brochure states one — otherwise `KNOWN_BERTHS`.

    The brochure's own statement is preferred over the written-down answer, so that a
    range which starts stating a count is read from the document rather than from here.
    """
    match = _SLEEPS.search(page_text)
    if match is not None:
        berths = int(match.group(1))
        return berths, f"{berths} berths, from the brochure's own {match.group(0)!r}"
    if known := KNOWN_BERTHS.get(manufacturer_range):
        berths, basis = known
        return berths, f"{berths} berths — {basis}"
    return None, (
        "no sleeping capacity is stated in this brochure; its beds are described "
        "without a count, and a berth figure is not derived from furniture"
    )


def parse_brochure(text: str, *, manufacturer_range: str, url: str) -> Brochure:
    """One brochure: its specification table, price, berths and interior copy.

    The table is on its own page, so each page is tried and the first that yields a
    complete table is taken. The price and the sleeping capacity are elsewhere in the
    document, so those are searched across the whole of it.
    """
    brochure = Brochure(manufacturer_range=manufacturer_range, url=url)
    for page in text.split("\n\n"):
        if "MTPLM" not in page:
            continue
        specification = parse_specification(page)
        if specification:
            brochure.specification = specification
            break
    brochure.rrp_pounds = price_from(text)
    brochure.berths, brochure.berths_basis = berths_from(
        text, manufacturer_range=manufacturer_range
    )
    brochure.equipment = habitation.usable_lines(
        line.strip() for line in text.splitlines() if line.strip()
    )
    return brochure


def body_type_for(mtplm_kilograms: int | None) -> tuple[CaravanBodyType, str]:
    """`rigid` for every one, with the micro test stated rather than skipped.

    A slide-out does not make a caravan a folding one: the walls and roof are solid GRP
    throughout — the brochures describe a *"4-element vacuum bonded, wood-free GRP body"* —
    and a section of the side slides out on rails when parked. The settled rule that a
    lifting roof does not change a caravan's body type points the same way.
    """
    weight = (
        f", and at {mtplm_kilograms}kg it is far above the {MICRO_CARAVAN_CEILING_KG}kg a "
        f"micro has to sit under"
        if mtplm_kilograms is not None
        else ""
    )
    return CaravanBodyType.RIGID, (
        f"a rigid caravan: the body is vacuum-bonded GRP throughout with no canvas, and "
        f"the slide-out moves a section of the side rather than folding the vehicle"
        f"{weight}"
    )


def _reconciles(brochure: Brochure) -> tuple[bool, str]:
    """The manufacturer's own arithmetic: unit weight plus payload equals the MTPLM.

    **A real check, and one that has already caught a bad document.** The brochure the
    site links for the INOS publishes 2,600kg, 1,000kg and 2,800kg, which do not add up —
    while the one its email form sends publishes 2,400, 400 and 2,800, which do and which
    FMLV holds. A range whose figures contradict each other is refused outright rather
    than recorded and explained away.
    """
    if not brochure.specification:
        return False, (
            "no specification table could be read from this brochure — its label and "
            "value columns did not pair, so the layout has changed"
        )
    mro = brochure.figure("mro_kilograms")
    payload = brochure.figure("personal_effects_payload_kilograms")
    mtplm = brochure.figure("mtplm_kilograms")
    if mro is None or payload is None or mtplm is None:
        return False, (
            f"the brochure does not give all three masses — read unit weight {mro!r}, "
            f"payload {payload!r} and MTPLM {mtplm!r}"
        )
    if mro + payload != mtplm:
        return False, (
            f"the brochure's own arithmetic does not close: {mro}kg unit weight plus "
            f"{payload}kg payload is {mro + payload}kg, against an MTPLM of {mtplm}kg. "
            f"Nothing is recorded from a document that contradicts itself — ask Fifth "
            f"Wheel Co which figure is right"
        )
    return True, (
        f"{mro}kg + {payload}kg = {mtplm}kg, the brochure's own published arithmetic"
    )


#: Each range page's own floorplan section, which carries a DAY and a NIGHT drawing per
#: layout variant — `CR20-Day.png` and `U-Shape Night.png` on the Celtic Rambler.
#:
#: **Recorded as a reviewer pointer, not read.** The positional habitation fields — which
#: end the caravan the beds are at, where the kitchen sits, how the washroom is arranged —
#: can only be answered off a drawing by a person, and this is where that person should
#: look. The requester's own reading of these on 16 October 2026 is what settled the Celtic
#: Rambler's berths: *"nighttime layout has a double bed like an island bed at the front
#: and then in the bit that sticks out the side there's another double bed."*
_FLOORPLAN_ANCHOR = "#layout"

#: How each habitation reading is introduced.
_FEATURE_NOTES: dict[str, str] = {
    "heating": "the heating in the brochure's own specification",
    "refrigeration": "the refrigeration in the brochure's own specification",
    "microwave": "a microwave in the brochure's own specification",
    "shower_toilet_separated": "the washroom as the brochure describes it",
}


def build_extracted(brochure: Brochure, *, basis: str) -> ExtractedCaravan:
    """One Fifth Wheel caravan, with provenance on everything it proposes."""
    features = habitation.features_from(brochure.equipment)
    features.pop("bed_types", None)

    mtplm = brochure.figure("mtplm_kilograms")
    body_type, body_type_reason = body_type_for(mtplm)
    caravan = Caravan(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        # One name, carried twice, because Nova will not take a blank — the settled
        # convention and how FMLV already files all three.
        manufacturer_range=brochure.manufacturer_range,
        model=brochure.manufacturer_range,
        berths=brochure.berths,
        rrp_pounds=brochure.rrp_pounds,
        price_min_range_pounds=brochure.rrp_pounds,
        mtplm_kilograms=mtplm,
        mro_kilograms=brochure.figure("mro_kilograms"),
        personal_effects_payload_kilograms=brochure.figure(
            "personal_effects_payload_kilograms"
        ),
        shipping_length_mm=brochure.figure("shipping_length_mm"),
        exterior_body_length_mm=brochure.figure("exterior_body_length_mm"),
        overall_width_mm=brochure.figure("overall_width_mm"),
        height_mm=brochure.figure("height_mm"),
        headroom_mm=brochure.figure("headroom_mm"),
        # Not proposed: the brochures publish no internal length. FMLV's three look like a
        # typist's approximation — two equal the length behind the tow vehicle and one the
        # body length — so there is nothing here to confirm or correct.
        internal_length_mm=None,
        body_type=body_type,
    )
    for name, feature in features.items():
        setattr(caravan, name, feature.value)

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=brochure.url, snippet=f"{brochure.label} — {snippet}"
        )

    theirs = MANUFACTURER_SPELLING.get(brochure.manufacturer_range)
    record(
        "manufacturer_range",
        f'range "{brochure.manufacturer_range}". Fifth Wheel Co give these no model name '
        f"beneath the range, so the name is carried twice — Nova will not take a blank"
        + (
            f". NOTE: they spell it {theirs!r} throughout their site and brochure; FMLV's "
            f"spelling is kept, per the rule that the export decides the identity strings"
            if theirs
            else ""
        ),
    )
    if brochure.rrp_pounds is not None:
        record("rrp_pounds", f"£{brochure.rrp_pounds:,}, the brochure's own 'Prices from'")
        record(
            "price_min_range_pounds",
            f"£{brochure.rrp_pounds:,} — one price is published per range",
        )
    if brochure.berths is not None:
        record("berths", brochure.berths_basis)
    for field_name, label, note in (
        ("mtplm_kilograms", "MTPLM", "the figure stated before any downplating qualifier"),
        ("mro_kilograms", "Unit Weight", "which Fifth Wheel Co call the unit weight"),
        (
            "personal_effects_payload_kilograms",
            "Payload",
            "the figure stated before any downplating qualifier",
        ),
    ):
        value = brochure.figure(field_name)
        if value is not None:
            record(field_name, f"{label} {value}kg — {note}. {basis}")
    for field_name, label in (
        ("shipping_length_mm", "Length Behind Tow Vehicle"),
        ("exterior_body_length_mm", "Overall Length"),
        ("overall_width_mm", "Overall Width"),
        ("height_mm", "Overall Height"),
        ("headroom_mm", "Internal Living Area Height"),
    ):
        value = brochure.figure(field_name)
        if value is None:
            continue
        extra = ""
        if field_name == "overall_width_mm":
            extended = brochure.specification.get("width with slide out extended", "")
            extra = (
                f" THE TRAVELLING WIDTH: the same table gives {extended!r} with the "
                f"slide-out extended, which is not what FMLV records"
                if extended
                else ""
            )
        if field_name == "shipping_length_mm":
            extra = (
                " — the length behind the tow vehicle, which on a fifth-wheel is shorter "
                "than the body because the gooseneck overhangs the truck"
            )
        record(field_name, f"{label} {value}mm, published in metres.{extra}")
    record("body_type", body_type_reason)
    # A pointer at the range page's own DAY/NIGHT drawings, for every positional field
    # still unanswered. One entry per field, so the link sits beside the question it
    # answers rather than once per product.
    provenance.update(
        floorplan_provenance(
            caravan,
            f"{BASE_URL}{RANGE_PATHS.get(brochure.manufacturer_range, '')}{_FLOORPLAN_ANCHOR}",
            brochure.label,
            drawing="the DAY and NIGHT floorplans on the range's own page",
        )
    )
    for name, feature in features.items():
        provenance[name] = Provenance(
            source_url=brochure.url,
            snippet=(
                f"{brochure.label} — {feature.note or _FEATURE_NOTES.get(name, name)}: "
                f"{feature.snippet!r}"
            ),
        )
    return ExtractedCaravan(caravan=caravan, provenance=provenance)


def _notes(brochure: Brochure) -> Iterable[str]:
    """What the brochure published that is deliberately not recorded."""
    if extended := brochure.specification.get("width with slide out extended"):
        yield (
            f"{brochure.label} — THE EXTENDED WIDTH IS NOT PROPOSED. The table gives "
            f"{extended!r} with the slide-out out, against a travelling "
            f"{brochure.specification.get('overall width')!r}. FMLV records the travelling "
            f"width"
        )
    downplated = {
        label: value
        for label, value in brochure.specification.items()
        if "downplated" in value.lower()
    }
    if downplated:
        yield (
            f"{brochure.label} — a downplate is offered: {downplated}. The figure recorded "
            f"is the one stated before the bracket, per the settled rule that an MTPLM "
            f"band records its upper limit"
        )
    if brochure.berths is None:
        yield f"{brochure.label} — BERTHS NOT PROPOSED: {brochure.berths_basis}"


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 — plain HTML and plain PDFs throughout
    snapshot_dir: Path,  # noqa: ARG001 — `http` already snapshots into it
    *,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedCaravan]:
    """Every Fifth Wheel Co caravan, from the brochure each range page links."""
    results: list[ExtractedCaravan] = []
    for manufacturer_range, path in RANGE_PATHS.items():
        page = http.fetch(f"{BASE_URL}{path}")
        if page.status_code != 200:
            on_progress(
                f"[{manufacturer_range}] SKIPPED: {path} returned {page.status_code}"
            )
            continue
        page_html = page.file_path.read_text(encoding="utf-8", errors="replace")
        url = find_brochure_url(page_html)
        if url is None:
            on_progress(
                f"[{manufacturer_range}] SKIPPED: its page links no brochure PDF. The "
                f"figures are in the brochure and nowhere else this adapter reads — the "
                f"range page repeats them but disagrees with the brochure on the INOS"
            )
            continue

        document = http.fetch(url)
        if document.status_code != 200:
            on_progress(
                f"[{manufacturer_range}] SKIPPED: {url} returned {document.status_code}"
            )
            continue
        try:
            text = extract_text(document.file_path).text
        except Exception as error:  # noqa: BLE001 — a bad PDF costs one range, not the run
            on_progress(f"[{manufacturer_range}] SKIPPED: its brochure would not parse — {error}")
            continue

        brochure = parse_brochure(text, manufacturer_range=manufacturer_range, url=url)
        reconciles, basis = _reconciles(brochure)
        if not reconciles:
            # **Emitted for its identity alone, deliberately.** All three ranges are live
            # FMLV products, so collecting nothing would report this one as withdrawn and
            # invite a reviewer to deactivate a caravan that is still sold — a false
            # disappearance, which is worse than a missing figure. Nothing is proposed
            # from a document that contradicts itself; the product simply carries through.
            results.append(
                build_extracted(
                    Brochure(manufacturer_range=manufacturer_range, url=url), basis=basis
                )
            )
            on_progress(
                f"[{manufacturer_range}] NOTHING RECORDED FROM ITS BROCHURE: {basis}. It "
                f"is still collected for its identity, so it is NOT reported as "
                f"disappeared — every figure FMLV holds carries through untouched"
            )
            continue

        results.append(build_extracted(brochure, basis=basis))
        on_progress(
            f"[{manufacturer_range}] read: "
            + (f"£{brochure.rrp_pounds:,}" if brochure.rrp_pounds else "no price")
            + f", {brochure.berths} berth, {brochure.figure('mtplm_kilograms')}kg, "
            + f"{brochure.figure('exterior_body_length_mm')}mm body"
        )
        for note in _notes(brochure):
            on_progress(note)
        if brochure.refused:
            on_progress(
                f"[{manufacturer_range}] read and not recorded: "
                f"{sorted(brochure.refused)} — FMLV holds no column for these"
            )

    on_progress(
        "NO INTERNAL LENGTH IS PROPOSED. The brochures publish an internal width and "
        "several internal heights but no internal length, and FMLV's three look like a "
        "typist's approximation — two equal the length behind the tow vehicle and one the "
        "body length — so there is nothing to confirm or correct."
    )
    if len(results) != EXPECTED_PRODUCTS:
        on_progress(
            f"expected {EXPECTED_PRODUCTS} caravans and collected {len(results)} — check "
            f"whether a range has been added or withdrawn"
        )
    on_progress(f"collected {len(results)} Fifth Wheel Co caravan(s)")
    return results
