"""Globecar campervans, read from the `TECHNICAL DATA` block on globecar.co.uk.

Eleven layouts across three ranges, all high top. Plain static WordPress HTML — no
JavaScript, and no PDF anywhere: `/brochure/` renders no document link and no layout page
references one. The `/range/` page is a grid of floorplan tiles, and each tile links a
per-layout page carrying the whole specification inline.

globecar.co.uk is the UK and Ireland importer's own site ("© 2019-2024 – Globecar
Motorhomes UK & Ireland"), which under the settled rule is what defines the range.

## Read the table, not the header card

Each layout page states its figures **twice**: a header card (`SLEEPS`, `SEATS`, `MPLM`,
`LENGTH`, `WIDTH`, `HEIGHT`) and a `TECHNICAL DATA` section. They do not always agree, and
where they differ the header is wrong:

| layout | header `MPLM` | `TECHNICAL DATA` | FMLV holds |
|---|---|---|---|
| Summit 540 | 3300 | **3500** | *(not in FMLV)* |
| Summit Shine 540 | 3000 | **3300** | **3300** |

Three things settle it. Only the table's figure reconciles with the page's own published
payload — 3500 − 2680 = 820, which is the stated number, where 3300 would give 620. The
table agrees with FMLV on all seven matched products. And 3000 kg is not a chassis Globecar
offers at all.

The header also folds options into its headline counts, saying `SEATS 4` where the table
says `3/3 (+1 optional)` and `SLEEPS 2 (+3 opt.)` where the table says `2 (+1 optional)`.

Both blocks are read anyway, and a disagreement is narrated rather than silently resolved,
because a header that starts agreeing again would mean the site had been corrected.

## The self-check

`Payload == MPLM − Mass in running order`, on 11 of 11. Globecar publishes all three
figures, so the parse is checkable without a second document — and a layout that fails is
dropped rather than proposed.

## Seats are ambiguous on seven layouts

The `Seats/Seatbelts` cell takes two forms:

| form | layouts | reading |
|---|---|---|
| `3/3 (+1 optional)` | Summit 540, 600, 640 | 3 belts |
| `4/4 (+1 optional)` | Summit 600L | 4 belts |
| `3/3 (+1 optional)/4 (+1 optional)` | all 7 Prime and Shine | **3 or 4** |

The third form is two configurations in one cell, and FMLV proves it is genuinely both:
against that identical string it holds 4 for Summit Prime 540 and 600, and 3 for the other
five. Nothing on the page says which layout gets which, so **no seat count is read from
it** — see `parse_seat_belts`. The four plain Summits, which are the layouts FMLV has no
figure for, all state one configuration and are read normally.

The figure recorded is the **belt** count, the second number, per the settled rule that
only three-point belts count as travel seats.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from . import habitation
from .base import ExtractedMotorhome, Provenance

__all__ = [
    "BASE_URL",
    "EXPECTED_LAYOUTS",
    "GlobecarCampervan",
    "LAYOUTS",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "collect",
    "parse_header_card",
    "parse_seat_belts",
    "parse_technical_data",
    "technical_block",
    "visible_lines",
]

BASE_URL = "https://globecar.co.uk"
MANUFACTURER = "Globecar"
MANUFACTURER_DISPLAY_NAME = "Globecar"

#: Every published layout. Eleven is what `/range/` lists under its "2026 Range" heading.
EXPECTED_LAYOUTS = 11


@dataclass(frozen=True)
class _Layout:
    """One layout page and the identity FMLV files it under."""

    slug: str
    manufacturer_range: str
    model: str

    @property
    def url(self) -> str:
        return f"{BASE_URL}/{self.slug}/"

    @property
    def label(self) -> str:
        return f"{self.manufacturer_range} {self.model}"


#: **Two slugs are misspelt on the site** — `sumit-prime-540` and `sumit-shine-640`, both
#: missing the second `m` — so the roster cannot be built by joining the range and model
#: names, and is hardcoded as published. `resolve_roster` checks the list against the
#: index every run, which is what catches a slug being corrected or a layout added.
#:
#: The range/model split follows FMLV's own 2027 convention: `Summit Prime` / `540`, not
#: `Summit` / `Prime 540`. FMLV's 2022 rows use the older `H - Line` / `Summit 540`
#: arrangement; those are dropped by the year filter and cannot be matched.
LAYOUTS: tuple[_Layout, ...] = (
    _Layout("summit-540", "Summit", "540"),
    _Layout("summit-600", "Summit", "600"),
    _Layout("summit-600l", "Summit", "600L"),
    _Layout("summit-640", "Summit", "640"),
    _Layout("sumit-prime-540", "Summit Prime", "540"),
    _Layout("summit-prime-600", "Summit Prime", "600"),
    _Layout("summit-prime-640", "Summit Prime", "640"),
    _Layout("summit-shine-540", "Summit Shine", "540"),
    _Layout("summit-shine-600", "Summit Shine", "600"),
    _Layout("summit-shine-600l", "Summit Shine", "600L"),
    _Layout("sumit-shine-640", "Summit Shine", "640"),
)

_TECHNICAL_DATA = "TECHNICAL DATA"

_TAGS = re.compile(r"<[^>]+>")
_BLOCK_TAGS = re.compile(r"<(tr|/tr|li|/li|dt|dd|br|p|div|h\d|td|/td)\b[^>]*>", re.I)
_SCRIPTS = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)

#: `5413mm`, `3500kg`, `2680kg`. Anchored at the start so a bed size such as
#: `1.960 x 1.200/1.410` cannot be read as a dimension.
_MEASUREMENT = re.compile(r"^(\d[\d,]*)\s*(mm|kg)\b", re.I)

#: `2 (+1 optional)` — the base count, with the optional extra left out. The optional
#: third berth is a factory-order extra seat, which the page says in words.
_LEADING_COUNT = re.compile(r"^\s*(\d+)")

#: `3/3 (+1 optional)` — seats over belts. The second number is what is recorded.
_SEATS_OVER_BELTS = re.compile(r"^\s*(\d+)\s*/\s*(\d+)")

#: `)/` marks a **second configuration** in the same cell, as in
#: `3/3 (+1 optional)/4 (+1 optional)`. It is the only thing distinguishing a layout with
#: one seating arrangement from one with two, and FMLV holds both 3 and 4 against that
#: identical string — so it means "unreadable", not "pick the first".
_SECOND_CONFIGURATION = re.compile(r"\)\s*/")

#: Layout links on the range index, which both misspelt slugs still match.
_LAYOUT_LINK = re.compile(rf'href="{re.escape(BASE_URL)}/(su[a-z0-9-]*\d[a-z0-9-]*)/"')


def visible_lines(html: str) -> list[str]:
    """The page as the reader sees it, one text run per line.

    Every figure sits on its own line below its label rather than beside it, so the parse
    is label-then-value throughout and the line split is what makes it possible.
    """
    text = _SCRIPTS.sub(" ", html)
    text = _BLOCK_TAGS.sub("\n", text)
    text = _TAGS.sub(" ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return [
        stripped
        for line in text.splitlines()
        if (stripped := re.sub(r"[ \t]+", " ", line).strip())
    ]


def technical_block(lines: list[str]) -> list[str]:
    """Everything from `TECHNICAL DATA` down, or `[]` if the page has no such block.

    Scoping matters: the header card above it repeats `MPLM`, `LENGTH`, `WIDTH`, `HEIGHT`
    and `SEATS` with figures that disagree on two layouts, and an unscoped read takes
    whichever comes first — which is the wrong one.
    """
    for index, line in enumerate(lines):
        if line.strip() == _TECHNICAL_DATA:
            return lines[index:]
    return []


def _value_after(lines: list[str], label: str) -> str | None:
    """The line following the one that *is* `label`, ignoring a trailing colon.

    Matched whole rather than by substring, because `Height:` and `Interior height:` are
    both on the page and a substring match on the former would take whichever came first.
    """
    wanted = label.rstrip(":").casefold()
    for index, line in enumerate(lines[:-1]):
        if line.strip().rstrip(":").casefold() == wanted:
            return lines[index + 1]
    return None


def _measurement(value: str | None, unit: str) -> int | None:
    if value is None:
        return None
    match = _MEASUREMENT.match(value)
    if match is None or match.group(2).lower() != unit:
        return None
    return int(match.group(1).replace(",", ""))


def parse_seat_belts(value: str | None) -> tuple[int | None, str]:
    """The belt count from `Seats/Seatbelts`, and why — `(None, reason)` when unreadable.

    Returns the **second** number, the belts, per the settled rule that only three-point
    belts count as travel seats. The optional extra seat in `(+1 optional)` is a
    factory-order item and is not added.

    `None` for a cell holding two configurations. See the module docstring: FMLV holds
    both 3 and 4 against `3/3 (+1 optional)/4 (+1 optional)`, so choosing either would be
    a guess, and the guess would be wrong on some layouts however it was made.
    """
    if value is None:
        return None, "the page states no Seats/Seatbelts row"
    if _SECOND_CONFIGURATION.search(value):
        return None, (
            f"NOT READ: 'Seats/Seatbelts {value}' states two seating configurations and "
            f"the page does not say which this layout is built as. FMLV holds 4 for two "
            f"of the seven layouts carrying this exact string and 3 for the other five, "
            f"so it is genuinely both and picking one would be a guess"
        )
    match = _SEATS_OVER_BELTS.match(value)
    if match is None:
        return None, f"NOT READ: 'Seats/Seatbelts {value}' is not seats over belts"
    return int(match.group(2)), (
        f"Seats/Seatbelts: {value} — the second figure is the three-point belts, which is "
        f"what counts as a travel seat; the optional extra seat is a factory order and is "
        f"not added"
    )


@dataclass
class _Figures:
    """What one page states, kept per block so the two can be compared."""

    mh_length_mm: int | None = None
    mh_width_mm: int | None = None
    mh_height_mm: int | None = None
    interior_height_mm: int | None = None
    mtplm_kilograms: int | None = None
    mro_kilograms: int | None = None
    payload_kilograms: int | None = None
    berths: int | None = None
    seats_raw: str | None = None
    sleeping_raw: str | None = None


def parse_technical_data(lines: list[str]) -> _Figures:
    """The `TECHNICAL DATA` block: the figures actually recorded."""
    block = technical_block(lines)
    if not block:
        return _Figures()

    sleeping = _value_after(block, "Sleeping places")
    return _Figures(
        mh_length_mm=_measurement(_value_after(block, "Length"), "mm"),
        mh_width_mm=_measurement(_value_after(block, "Width"), "mm"),
        mh_height_mm=_measurement(_value_after(block, "Height"), "mm"),
        interior_height_mm=_measurement(_value_after(block, "Interior height"), "mm"),
        # The site's label is MPLM, not MTPLM.
        mtplm_kilograms=_measurement(_value_after(block, "MPLM"), "kg"),
        mro_kilograms=_measurement(_value_after(block, "Mass in running order"), "kg"),
        payload_kilograms=_measurement(_value_after(block, "Payload"), "kg"),
        berths=_leading_count(sleeping),
        sleeping_raw=sleeping,
        seats_raw=_value_after(block, "Seats/Seatbelts"),
    )


def _leading_count(value: str | None) -> int | None:
    if value is None:
        return None
    match = _LEADING_COUNT.match(value)
    return int(match.group(1)) if match else None


def parse_header_card(lines: list[str]) -> _Figures:
    """The header card above the table, read **only** so it can be checked against it.

    Nothing from here is ever recorded. It exists so `collect` can say when the two blocks
    disagree, which on this site means the card is stale.
    """
    block = technical_block(lines)
    head = lines[: len(lines) - len(block)] if block else lines
    return _Figures(
        mh_length_mm=_measurement(_value_after(head, "LENGTH"), "mm"),
        mh_width_mm=_measurement(_value_after(head, "WIDTH"), "mm"),
        mh_height_mm=_measurement(_value_after(head, "HEIGHT"), "mm"),
        mtplm_kilograms=_measurement(_value_after(head, "MPLM"), "kg"),
        berths=_leading_count(_value_after(head, "SLEEPS")),
        seats_raw=_value_after(head, "SEATS"),
    )


@dataclass
class GlobecarCampervan:
    """One layout, as read from its own page."""

    layout: _Layout
    figures: _Figures
    travel_seats: int | None = None
    seats_reason: str = ""

    @property
    def label(self) -> str:
        return self.layout.label


def _reconciles(product: GlobecarCampervan) -> tuple[bool, str]:
    """Does the published payload equal MPLM minus the mass in running order?

    Globecar publishes all three, so this checks the parse against the manufacturer's own
    arithmetic. It holds on all eleven layouts; one that stops holding has been misread,
    and is dropped rather than proposed.
    """
    figures = product.figures
    mtplm, mro, payload = (
        figures.mtplm_kilograms,
        figures.mro_kilograms,
        figures.payload_kilograms,
    )
    missing = [
        name
        for name, value in (
            ("MPLM", mtplm),
            ("Mass in running order", mro),
            ("Payload", payload),
        )
        if value is None
    ]
    if missing:
        return False, f"the Weight & Load block states no {', '.join(missing)}"
    if mtplm - mro != payload:
        return False, (
            f"MPLM {mtplm} - MRO {mro} = {mtplm - mro}kg but the page publishes a payload "
            f"of {payload}kg — one of the three was misread"
        )
    return True, (
        f"MPLM {mtplm}kg minus mass in running order {mro}kg = {payload}kg, which is the "
        f"payload the page publishes — the three agree"
    )


def resolve_roster(index_html: str) -> tuple[list[str], list[str]]:
    """`(published, expected)` layout slugs, for comparing the index against `LAYOUTS`."""
    published = sorted(set(_LAYOUT_LINK.findall(index_html)))
    return published, sorted(layout.slug for layout in LAYOUTS)


#: How each habitation reading is introduced. These are findings for a person to type in,
#: not proposals, so the wording names the block they came from.
_FEATURE_NOTES: dict[str, str] = {
    "heating": "the heating named in the page's On Board Technology block",
    "refrigeration": "the refrigeration named in the page's On Board Technology block",
    "microwave": "a microwave named in the page's TECHNICAL DATA block",
    "shower_toilet_separated": "the washroom as the page's feature list describes it",
}


def build_extracted(
    product: GlobecarCampervan, *, payload_basis: str, equipment: tuple[str, ...] = ()
) -> ExtractedMotorhome:
    """One layout as a `Motorhome` plus the provenance a reviewer sees beside it."""
    features = habitation.features_from(equipment)
    # Dropped for the same reason as on the caravan adapters: the `Rear bed`/`Third bed`
    # rows give dimensions without saying whether a bed is built in or made up from the
    # seating, which is the distinction `BedType` exists to carry.
    features.pop("bed_types", None)

    figures = product.figures
    source_url = product.layout.url

    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.layout.manufacturer_range,
        model=product.layout.model,
        mh_length_mm=figures.mh_length_mm,
        mh_width_mm=figures.mh_width_mm,
        mh_height_mm=figures.mh_height_mm,
        berths=figures.berths,
        mh_passenger_seats_inc_driver=product.travel_seats,
        mtplm_kilograms=figures.mtplm_kilograms,
        mro_kilograms=figures.mro_kilograms,
        mh_payload_kilograms=figures.payload_kilograms,
        body_type=BodyType.CAMPERVAN_HIGH_TOP,
        heating=features["heating"].value if "heating" in features else None,
        refrigeration=features["refrigeration"].value if "refrigeration" in features else None,
        microwave=features["microwave"].value if "microwave" in features else None,
    )

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=source_url, snippet=f"{product.label} — {snippet}"
        )

    # Both halves of the identity, always: `compare_fields` walks only fields carrying
    # provenance, and accepting a range change without its model corrupts the name.
    record(
        "manufacturer_range",
        f'range "{product.layout.manufacturer_range}", as the range index groups this '
        f"layout — accept with the model, they are one name",
    )
    record(
        "model",
        f'model "{product.layout.model}" — accept with the range, they are one name',
    )

    if figures.mh_length_mm is not None:
        record("mh_length_mm", f"Length: {figures.mh_length_mm}mm")
    if figures.mh_width_mm is not None:
        record("mh_width_mm", f"Width: {figures.mh_width_mm}mm")
    if figures.mh_height_mm is not None:
        record(
            "mh_height_mm",
            f"Height: {figures.mh_height_mm}mm, the exterior figure — the page also "
            f"states an interior height of {figures.interior_height_mm}mm",
        )
    if figures.berths is not None:
        record(
            "berths",
            f"Sleeping places: {figures.sleeping_raw} — the base figure. The extra berth "
            f"is optional, so it does not count",
        )
    if product.travel_seats is not None:
        record("mh_passenger_seats_inc_driver", product.seats_reason)
    if figures.mtplm_kilograms is not None:
        record("mtplm_kilograms", f"MPLM: {figures.mtplm_kilograms}kg. {payload_basis}")
    if figures.mro_kilograms is not None:
        record("mro_kilograms", f"Mass in running order: {figures.mro_kilograms}kg")
    if figures.payload_kilograms is not None:
        record(
            "mh_payload_kilograms",
            f"Payload: {figures.payload_kilograms}kg, published by Globecar rather than "
            f"derived. {payload_basis}",
        )
    record(
        "body_type",
        f"high top campervan: every layout is a fixed high roof at "
        f"{figures.mh_height_mm}mm, well over the 2300mm threshold, and the page names no "
        f"elevating roof",
    )

    for name, feature in features.items():
        note = feature.note or _FEATURE_NOTES.get(name, "read from the TECHNICAL DATA block")
        record(name, f"{note}: {feature.snippet}")

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001
    snapshot_dir: Path,  # noqa: ARG001
    *,
    ranges: tuple[tuple[str, str], ...] = (),  # noqa: ARG001
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every Globecar campervan the UK site publishes.

    Twelve fetches: the range index, to check the roster, and eleven layout pages.
    """
    index_url = f"{BASE_URL}/range/"
    on_progress(f"fetching the range index: {index_url}")
    published, expected = resolve_roster(
        http.fetch(index_url).file_path.read_text(encoding="utf-8", errors="replace")
    )
    if published != expected:
        on_progress(
            f"THE ROSTER HAS MOVED: the range index links {published} where this adapter "
            f"expects {expected}. Layouts only on the site are not collected and layouts "
            f"only in the adapter are still fetched — check before trusting this run"
        )

    extracted: list[ExtractedMotorhome] = []
    unreadable_seats: list[str] = []
    card_disagreements: list[str] = []

    for layout in LAYOUTS:
        on_progress(f"fetching {layout.url}")
        lines = visible_lines(
            http.fetch(layout.url).file_path.read_text(encoding="utf-8", errors="replace")
        )
        if not technical_block(lines):
            on_progress(f"dropping {layout.label} — no TECHNICAL DATA block on its page")
            continue

        figures = parse_technical_data(lines)
        card = parse_header_card(lines)
        seats, seats_reason = parse_seat_belts(figures.seats_raw)

        if (
            card.mtplm_kilograms is not None
            and figures.mtplm_kilograms is not None
            and card.mtplm_kilograms != figures.mtplm_kilograms
        ):
            card_disagreements.append(
                f"{layout.label} (card {card.mtplm_kilograms}kg, table "
                f"{figures.mtplm_kilograms}kg)"
            )

        product = GlobecarCampervan(
            layout=layout, figures=figures, travel_seats=seats, seats_reason=seats_reason
        )
        reconciles, reason = _reconciles(product)
        if not reconciles:
            on_progress(f"dropping {layout.label} — {reason}")
            continue

        if seats is None:
            unreadable_seats.append(layout.label)

        extracted.append(
            build_extracted(product, payload_basis=reason, equipment=tuple(technical_block(lines)))
        )
        on_progress(
            f"read {layout.label}: {figures.mh_length_mm}mm, {figures.mtplm_kilograms}kg, "
            f"{figures.berths} berth, "
            + (f"{seats} belted seats" if seats is not None else "seats not readable")
        )

    if card_disagreements:
        on_progress(
            "THE HEADER CARD DISAGREES WITH THE TABLE on "
            f"{', '.join(card_disagreements)}. The table is recorded: only its figure "
            "reconciles with the page's own published payload, and it is what FMLV already "
            "holds. Narrated because the card agreeing again would mean the site had been "
            "corrected"
        )

    if unreadable_seats:
        on_progress(
            f"SEATS NOT PROPOSED for {', '.join(unreadable_seats)}: each states "
            f"'Seats/Seatbelts 3/3 (+1 optional)/4 (+1 optional)', which is two seating "
            f"configurations in one cell with nothing to say which this layout is built "
            f"as. FMLV holds 4 for two of them and 3 for the rest against that identical "
            f"string, so it is genuinely both and a guess would be wrong somewhere. "
            f"FMLV's own figures stand"
        )

    on_progress(
        "NOT PUBLISHED, and so left alone: PRICE — the pound sign appears nowhere on this "
        "site, not on a layout page, not on the range index and not in the configurator, "
        "so nothing is proposed and no POA is invented. Also the BASE VEHICLE: no page "
        "names Fiat, Citroen or Peugeot, or a chassis of any kind."
    )

    if len(extracted) != EXPECTED_LAYOUTS:
        on_progress(
            f"expected {EXPECTED_LAYOUTS} layouts and collected {len(extracted)} — check "
            f"whether the range has really changed"
        )
    on_progress(f"collected {len(extracted)} Globecar campervan(s)")
    return extracted
