"""Benimar — sixteen UK layouts across four ranges, from the importer's range pages.

`docs/adapters/benimar.md` is the survey; this is what it decided.

Fourth of six Trigano brands. Marquis Leisure are *"the exclusive distributor of Benimar
motorhomes in the UK"* in their own words, so the settled importer rule applies in full:
Marquis decide what exists and what it costs, and their range pages carry the numbers too.
`benimar.es` is never fetched.

**Nearly all of the reading is shared** — see `adapters/marquis.py`, which holds the block
reader, the field patterns, the OTR price rule and the last-occurrence range rule, each of
which was found the hard way on `mobilvetta.py`. What is specific to Benimar is only this:

* four ranges rather than one page's worth, and the roster comes from the brand index;
* **the base vehicle changes by range** — Tessoro is a Ford, the other three are Fiat —
  so it cannot be a brand constant the way it is for Mobilvetta and Panama;
* **Benivan is a campervan** and the other three are low-profile coachbuilts;
* a **`Bed Sizes` list per layout**, which no other Marquis brand publishes.

**Benimar disproved the conclusion the Mobilvetta survey drew for all four brands** — that
Marquis publish no arithmetic self-check. Marquis are mid-redesign and run two templates;
the newer one, on three of Benimar's four pages, prints MIRO beside MTPLM and payload, so
the three must close. Only the older Primero page is unchecked. See `_reconciles`.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from . import habitation, marquis
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

MANUFACTURER = "Benimar Ocarsa S.A.U."
MANUFACTURER_DISPLAY_NAME = "Benimar"

#: The importer's brand index, which links the four current range pages.
INDEX_URL = marquis.index_url("benimar")

#: Block-heading prefix -> FMLV `manufacturer_range`. FMLV holds these in title case while
#: the pages shout them, so the mapping is not an identity.
RANGE_PREFIXES: tuple[tuple[str, str], ...] = (
    ("PRIMERO", "Primero"),
    ("TESSORO", "Tessoro"),
    ("BENIVAN", "Benivan"),
    ("MILEO", "Mileo"),
)

#: **The base vehicle is per range, not per brand.** Benimar build the Tessoro on a Ford
#: and everything else on a Fiat, which is what FMLV holds across its sixteen rows.
BASE_VEHICLES: dict[str, str] = {
    "Primero": "Fiat",
    "Mileo": "Fiat",
    "Tessoro": "Ford",
    "Benivan": "Fiat",
}

#: Body type by range. Benivan is the campervan; the rest are low-profile coachbuilts, and
#: Benimar build no A-class and nothing with an over-cab bed for the UK.
BODY_TYPES: dict[str, BodyType] = {
    "Primero": BodyType.COACH_BUILT_LOW_PROFILE,
    "Mileo": BodyType.COACH_BUILT_LOW_PROFILE,
    "Tessoro": BodyType.COACH_BUILT_LOW_PROFILE,
    "Benivan": BodyType.CAMPERVAN_HIGH_TOP,
}

#: `(slug key, label)` for `--range`, matched against the page slug.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (
    ("primero", "Primero"),
    ("mileo", "Mileo"),
    ("tessoro", "Tessoro"),
    ("benivan", "Benivan"),
)

#: What the roster should come to: Primero 4, Mileo 4, Tessoro 6, Benivan 2.
#:
#: A change in it is narrated loudly. It is the only defence against a page quietly
#: dropping a layout, which no arithmetic can catch — and it is what caught the first
#: build of this adapter collecting **zero**, having required an upper-case heading that
#: only Mobilvetta writes.
EXPECTED_LAYOUTS = 16

plain_text = marquis.plain_text

#: A layout's `Bed Sizes` list, which runs to the footnote or the engine-and-price line.
BED_SECTION = re.compile(r"Bed Sizes\s+(?P<beds>.*?)(?=#|[A-Z][A-Z\s.]*ENGINE|$)", re.S)

#: One bed in that list: a name, then the size that ends it.
#:
#: The entries are run together — `Double Drop Down Bed 1400mm x 1900mm | 4'6'' x 6'2''
#: Double Rear Bed 1390mm x 2000mm` — so the split is on the size rather than on any
#: separator. The name may not contain a digit or a quote mark, which is what stops the
#: previous entry's imperial measurement being read as part of the next bed's name.
#:
#: **The letter `x` is deliberately allowed in a name** even though the older template
#: uses it between the two figures: excluding it turned `FIXED REAR BED` into `ED REAR
#: BED`. The digits do the separating instead.
BED_ENTRY = re.compile(r"""(?P<name>[^|\u00d7#\d\u2019'"]+?Bed)\s+(?:2\s*x\s*)?\d+\s*mm""", re.I)


def _bed_lines(body: str) -> list[str]:
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


def _equipment_lines(page: str) -> list[str]:
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


def find_range_urls(index_html: str, ranges: Iterable[str]) -> list[str]:
    """Every current Benimar range page the brand index links."""
    return marquis.find_range_urls(index_html, brand="benimar", wanted=tuple(ranges))


@dataclass(frozen=True)
class BenimarProduct:
    """One layout, from one block of an importer range page."""

    source_url: str
    manufacturer_range: str
    model: str
    mh_passenger_seats_inc_driver: int | None = None
    berths: int | None = None
    mh_length_mm: int | None = None
    mh_width_mm: int | None = None
    mh_height_mm: int | None = None
    mtplm_kilograms: int | None = None
    mh_payload_kilograms: int | None = None
    published_mro_kilograms: int | None = None
    rrp_pounds: int | None = None
    base_mro_routes: tuple[int, ...] = ()
    chassis_mro_routes: tuple[int, ...] = ()
    copy_lines: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        return f"{self.manufacturer_range} {self.model}"

    @property
    def base_vehicle(self) -> str | None:
        return BASE_VEHICLES.get(self.manufacturer_range)

    @property
    def body_type(self) -> BodyType | None:
        return BODY_TYPES.get(self.manufacturer_range)

    @property
    def recorded_width_mm(self) -> int | None:
        """The width, but **only where `mirrors folded` is the body width.**

        On a coachbuilt it is: the habitation body is 2300 mm and overhangs a Ducato's
        folded mirrors, so the figure measures the body. **On a panel van it is not.** A
        Ducato's body is about 2050 mm and its folded mirrors reach about 2260 mm, which
        is what Marquis print for both Benivan layouts — so that figure is the mirrors,
        and the settled rule is that a recorded width excludes them.

        The requester's ruling, 12 September 2026: *"if they don't have a figure excluding
        mirrors, we'll have to leave that blank as we don't have the correct figure, unless
        it's an existing model that appears to have the same height and length"*. Emitting
        nothing satisfies both halves — a layout FMLV already holds keeps the 2050 mm it
        has, and a new one goes in visibly blank rather than 210 mm too wide.

        **This applies to Mobilvetta's Admiral and possibly Panama too**, and neither
        adapter has been changed; see `docs/adapters/benimar.md`.
        """
        if self.body_type is BodyType.CAMPERVAN_HIGH_TOP:
            return None
        return self.mh_width_mm

    @property
    def mro_kilograms(self) -> int | None:
        """The published mass in running order, or MTPLM minus payload where it is not.

        Benimar's newer range pages print MIRO outright; the older Primero page does not.
        """
        if self.published_mro_kilograms is not None:
            return self.published_mro_kilograms
        if self.mtplm_kilograms is None or self.mh_payload_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mh_payload_kilograms


def layout_blocks(page: str, source_url: str) -> list[BenimarProduct]:
    """Every layout on one range page, in page order."""
    products: list[BenimarProduct] = []
    equipment = _equipment_lines(page)
    for heading, body in marquis.layout_blocks(marquis.plain_text(page)):
        identity = marquis.range_and_model(heading, RANGE_PREFIXES)
        if identity is None:
            continue
        manufacturer_range, model = identity
        products.append(
            BenimarProduct(
                source_url=source_url,
                manufacturer_range=manufacturer_range,
                model=model,
                mh_passenger_seats_inc_driver=marquis.field(body, "seats"),
                berths=marquis.field(body, "berths"),
                mh_length_mm=marquis.field(body, "length"),
                mh_width_mm=marquis.field(body, "width"),
                mh_height_mm=marquis.field(body, "height"),
                mtplm_kilograms=marquis.field(body, "mtplm"),
                mh_payload_kilograms=marquis.field(body, "payload"),
                published_mro_kilograms=marquis.field(body, "mro"),
                rrp_pounds=marquis.price(body),
                base_mro_routes=tuple(marquis.base_mro_routes(body)),
                chassis_mro_routes=tuple(marquis.chassis_mro_routes(body)),
                copy_lines=tuple(_bed_lines(body)) + tuple(equipment),
            )
        )
    return products


def _reconciles(product: BenimarProduct) -> tuple[bool, str]:
    """`(ok, why not)` — the block's own arithmetic, then a completeness floor.

    **Benimar do publish a self-check**, which the Mobilvetta survey concluded this source
    did not: twelve of the sixteen layouts print MIRO beside MTPLM and payload, so
    `MTPLM - payload` is a second route to a printed figure and the two must close. That
    is what catches a figure taken from the automatic column instead of the manual one.

    **It judges only the figures that reach FMLV.** What the other chassis says is
    corroboration, reported by `_discrepancies` and never grounds for dropping a vehicle
    Marquis really sell — see `marquis.chassis_mro_routes`.

    The four Primero layouts print no MIRO, so nothing checks them and the fallback is all
    that applies: a block that yields a heading and no figures at all, which is what a
    Marquis redesign would produce.
    """
    routes = product.base_mro_routes
    if routes and max(routes) - min(routes) > marquis.TOLERANCE_KG:
        return False, (
            f"its own figures imply {sorted(set(routes))} kg as the mass in running "
            f"order. A gap that wide is the size of the manual-to-automatic step, so a "
            f"figure has probably been read out of the wrong column"
        )

    figures = (
        product.mh_length_mm,
        product.mh_width_mm,
        product.mh_height_mm,
        product.mtplm_kilograms,
        product.mh_payload_kilograms,
    )
    if any(figure is not None for figure in figures):
        return True, ""
    return False, (
        "the block yielded a heading but not one figure, so the page's shape has probably "
        "changed"
    )


def _discrepancies(product: BenimarProduct) -> list[str]:
    """Where Benimar's own figures disagree by too little to be a misread.

    Two real cases, both verified against the pages by hand on 14 September 2026 and both
    Benimar's arithmetic rather than this parse:

    * **Mileo 294** prints MTPLM 3650 kg, MIRO 3254 kg and payload 400 kg, which do not
      close by 4 kg. The automatic column beside them closes exactly.
    * **Primero 282** gives the 3650 kg chassis 100 kg more payload than the 3500 kg one,
      where the chassis themselves are 150 kg apart.

    Neither is a reason to withhold a vehicle Marquis sell, and neither should pass in
    silence either, so both are said out loud and the product goes forward.
    """
    notes: list[str] = []
    routes = product.base_mro_routes
    if len(set(routes)) > 1:
        notes.append(
            f"MTPLM {product.mtplm_kilograms}kg minus payload "
            f"{product.mh_payload_kilograms}kg is "
            f"{product.mtplm_kilograms - product.mh_payload_kilograms}kg, but the page "
            f"prints MIRO {product.published_mro_kilograms}kg. Benimar's own rounding; "
            f"the printed MIRO is the one recorded"
        )
    chassis = set(product.chassis_mro_routes)
    if len(chassis) > 1:
        notes.append(
            f"its chassis options imply {sorted(chassis)} kg as the mass in running "
            f"order. Only the lighter chassis is recorded, that being the base vehicle "
            f"and the one the quoted price buys"
        )
    return notes


def _build_extracted_motorhome(product: BenimarProduct) -> ExtractedMotorhome:
    """One layout as a `Motorhome`, plus the provenance a reviewer sees beside each field."""
    source_url = product.source_url
    features = habitation.features_from(product.copy_lines)
    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.manufacturer_range,
        model=product.model,
        base_vehicle_manufacturer=fmlv_base_vehicle(product.base_vehicle),
        rrp_pounds=product.rrp_pounds,
        mro_kilograms=product.mro_kilograms,
        mtplm_kilograms=product.mtplm_kilograms,
        mh_payload_kilograms=product.mh_payload_kilograms,
        mh_length_mm=product.mh_length_mm,
        mh_width_mm=product.recorded_width_mm,
        mh_height_mm=product.mh_height_mm,
        mh_passenger_seats_inc_driver=product.mh_passenger_seats_inc_driver,
        berths=product.berths,
        body_type=product.body_type,
        # Habitation, from the range's equipment list and the layout's own bed list.
        # Findings, never proposals — see `docs/adapters/README.md`.
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
            source_url=source_url,
            snippet=f"{product.label} — Marquis Leisure's own range page, {snippet}",
        )

    if product.mh_length_mm is not None:
        record("mh_length_mm", f"'OVERALL LENGTH {product.mh_length_mm}mm'")
    if product.recorded_width_mm is not None:
        record(
            "mh_width_mm",
            f"'WIDTH (MIRRORS FOLDED) {product.recorded_width_mm}mm'. On a coachbuilt the "
            f"body overhangs the folded mirrors, so this measures the body",
        )
    if product.mh_height_mm is not None:
        record("mh_height_mm", f"'OVERALL HEIGHT (EXC TV AERIAL) {product.mh_height_mm}mm'")
    if product.mh_passenger_seats_inc_driver is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"'BELTS {product.mh_passenger_seats_inc_driver}', this page's word for a "
            f"belted travel seat",
        )
    if product.berths is not None:
        record("berths", f"'BERTHS {product.berths}'")
    if product.mtplm_kilograms is not None:
        record("mtplm_kilograms", f"'MTPLM {product.mtplm_kilograms}kg'")
    if product.mh_payload_kilograms is not None:
        record("mh_payload_kilograms", f"'MAX USER PAYLOAD {product.mh_payload_kilograms}kg'")
    if product.published_mro_kilograms is not None:
        record(
            "mro_kilograms",
            f"'MIRO {product.published_mro_kilograms}kg', the manual column. MTPLM "
            f"{product.mtplm_kilograms}kg minus payload {product.mh_payload_kilograms}kg "
            f"agrees with it",
        )
    elif product.mro_kilograms is not None:
        record(
            "mro_kilograms",
            f"derived as MTPLM {product.mtplm_kilograms}kg minus payload "
            f"{product.mh_payload_kilograms}kg. This page prints no MIRO, but its two "
            f"chassis both imply {product.mro_kilograms}kg",
        )
    if product.rrp_pounds is not None:
        record(
            "rrp_pounds",
            f"'£{product.rrp_pounds:,} OTR'. Marquis are the exclusive UK distributor, so "
            f"this is the price that counts",
        )
    if motorhome.body_type is not None:
        record("body_type", f"every layout in the {product.manufacturer_range} range shares it")
    if product.base_vehicle is not None:
        record(
            "base_vehicle_manufacturer",
            f"the {product.manufacturer_range} range is built on a {product.base_vehicle}; "
            f"Benimar use a Ford for the Tessoro and a Fiat for the rest",
        )

    for field_name, feature in features.items():
        detail = f" — {feature.note}" if feature.note else ""
        provenance[field_name] = Provenance(
            source_url=source_url,
            snippet=(
                f"{product.label} — the {product.manufacturer_range} range page says "
                f"{feature.snippet!r}{detail}"
            ),
        )

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 - plain HTTP throughout
    snapshot_dir: Path,  # noqa: ARG001 - `Fetcher` owns the snapshot directory
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every layout on the importer's current Benimar range pages."""
    on_progress(f"fetching the importer's brand index: {INDEX_URL}")
    index = http.fetch(INDEX_URL)
    if index.status_code != 200:
        message = f"{INDEX_URL} returned {index.status_code}; it is the roster"
        raise RuntimeError(message)

    urls = find_range_urls(
        index.file_path.read_text(encoding="utf-8", errors="replace"),
        (key for key, _label in ranges),
    )
    on_progress(f"{len(urls)} range page(s), each holding one or more layouts")

    results: list[ExtractedMotorhome] = []
    for url in urls:
        page_result = http.fetch(url)
        if page_result.status_code != 200:
            on_progress(f"SKIPPED: {url} returned {page_result.status_code}")
            continue
        page = page_result.file_path.read_text(encoding="utf-8", errors="replace")

        products = layout_blocks(page, url)
        if not products:
            on_progress(
                f"WARNING: {url} yielded no layout at all. A range page that stops "
                f"producing 'Weights and Dimensions' blocks is what a Marquis redesign "
                f"would break first"
            )
            continue
        on_progress(f"{url.rsplit('/', 1)[-1]}: {len(products)} layout(s)")

        for product in products:
            reconciles, why_not = _reconciles(product)
            if not reconciles:
                on_progress(f"SKIPPED [{product.label}]: {why_not}")
                continue
            for note in _discrepancies(product):
                on_progress(f"[{product.label}] NOTE: {note}")
            if product.rrp_pounds is None:
                on_progress(
                    f"[{product.label}] WARNING: no OTR price in its block, so FMLV's own "
                    f"figure is left alone"
                )
            results.append(_build_extracted_motorhome(product))

    if len(results) != EXPECTED_LAYOUTS:
        on_progress(
            f"WARNING: collected {len(results)} layout(s) where the survey found "
            f"{EXPECTED_LAYOUTS}. This source publishes no arithmetic self-check, so the "
            f"roster count is the main defence — check the range pages before accepting"
        )
    on_progress(f"collected {len(results)} product(s)")
    return results
