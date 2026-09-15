"""Elnagh — four UK layouts on one range page, from the importer's site.

`docs/adapters/elnagh.md` is the survey; this is what it decided.

Fifth of six Trigano brands. Marquis Leisure are the sole UK importer, so the settled
importer rule applies in full and `elnagh.com` is never fetched. **The Italian parent sells
far more than four layouts**; Marquis sell the Baron and nothing else, which is the
requester's standing warning made concrete — *"ranges in the parent website may comprise
greater numbers of models than offered in the UK"*.

**Almost none of the reading is here** — see `adapters/marquis.py`, which holds the block
reader, the field patterns, the OTR price rule, the bed and equipment readers and the
last-occurrence range rule. Elnagh is the smallest of the four Marquis brands because it is
the most uniform: one range, one base vehicle, one body type, one page.

Two things are worth knowing about it:

* it is on Marquis's **older template** — `Weights and Dimensions`, shouted labels, no
  printed MIRO, and a payload row per chassis — so the mass in running order is derived;
* its equipment list **qualifies lines per layout**, and on the one field where that
  matters it decides the answer rather than shading it. See `habitation.lines_for_layout`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from . import habitation, marquis
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

MANUFACTURER = "Elnagh"
MANUFACTURER_DISPLAY_NAME = "Elnagh"

#: The importer's brand index, which links the single current range page.
INDEX_URL = marquis.index_url("elnagh")

#: Block-heading prefix -> FMLV `manufacturer_range`. FMLV writes it in title case and the
#: page shouts it, so the mapping is not an identity.
RANGE_PREFIXES: tuple[tuple[str, str], ...] = (("BARON", "Baron"),)

#: Every layout is a `FIAT DUCATO 140BHP MANUAL ENGINE`, per the price line on each block.
BASE_VEHICLE = "Fiat"

#: Every layout is a low-profile coachbuilt.
#:
#: Marquis head the page `COACHBUILT MOTORHOME RANGE`, every block's bed list names a
#: **drop-down** bed rather than a fixed over-cab one, and FMLV holds
#: `type_coach_built_low_profile` for all four. The 2950 mm height is no objection —
#: Mobilvetta's KEA 86 and 90 are low profiles at the same height.
BODY_TYPE = BodyType.COACH_BUILT_LOW_PROFILE

#: `(slug key, label)` for `--range`, matched against the page slug.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (("baron", "Baron"),)

#: What the roster should come to: Baron 530, 560, 573 and 579.
#:
#: The brand index corroborates it independently — it carries a `View our Stock` link per
#: layout, and there are exactly four. A change in this count is narrated loudly, because
#: no arithmetic can catch a page quietly dropping a layout.
EXPECTED_LAYOUTS = 4

plain_text = marquis.plain_text


def find_range_urls(index_html: str, ranges: Iterable[str]) -> list[str]:
    """Every current Elnagh range page the brand index links, which is one."""
    return marquis.find_range_urls(index_html, brand="elnagh", wanted=tuple(ranges))


@dataclass(frozen=True)
class ElnaghProduct:
    """One layout, from one block of the importer's range page."""

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
    rrp_pounds: int | None = None
    chassis_mro_routes: tuple[int, ...] = ()
    copy_lines: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        return f"{self.manufacturer_range} {self.model}"

    @property
    def mro_kilograms(self) -> int | None:
        """Derived: MTPLM minus payload. The older template prints no MIRO.

        Both chassis rows imply the same figure on all four layouts, which is the closest
        this page comes to corroborating it — see `_reconciles`.
        """
        if self.mtplm_kilograms is None or self.mh_payload_kilograms is None:
            return None
        return self.mtplm_kilograms - self.mh_payload_kilograms


def layout_blocks(page: str, source_url: str) -> list[ElnaghProduct]:
    """Every layout on the range page, in page order."""
    products: list[ElnaghProduct] = []
    equipment = marquis.equipment_lines(page)
    for heading, body in marquis.layout_blocks(marquis.plain_text(page)):
        identity = marquis.range_and_model(heading, RANGE_PREFIXES)
        if identity is None:
            continue
        manufacturer_range, model = identity
        products.append(
            ElnaghProduct(
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
                rrp_pounds=marquis.price(body),
                chassis_mro_routes=tuple(marquis.chassis_mro_routes(body)),
                copy_lines=tuple(marquis.bed_lines(body))
                + tuple(habitation.lines_for_layout(equipment, model)),
            )
        )
    return products


def _reconciles(product: ElnaghProduct) -> tuple[bool, str]:
    """`(ok, why not)` — the two chassis rows, then a completeness floor.

    The older template prints no MIRO, so `MTPLM - payload` cannot be checked against
    anything published. What it does print is **a payload per chassis**, and the two are
    independent routes to one mass in running order:

    ```
    MTPLM 3500kg / 3650kg
    MAX USER PAYLOAD (3500KG CHASSIS) Manual 590kg
    MAX USER PAYLOAD (3650KG CHASSIS) Manual 740kg
    ```

    Both give 2910 kg, and all four layouts agree with themselves this way — unlike
    Benimar's Primero 282, whose two rows are 50 kg apart. **A disagreement is therefore
    reported rather than fatal**, by the same reasoning as there: the figure at fault would
    be in the heavier chassis row, which this pipeline does not record.

    So what is left as a drop rule is noticing a block that yielded a heading and no figures
    at all, which is what a Marquis redesign would produce.
    """
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


def _discrepancies(product: ElnaghProduct) -> list[str]:
    """Where the layout's two chassis rows do not imply the same mass in running order."""
    chassis = set(product.chassis_mro_routes)
    if len(chassis) <= 1:
        return []
    return [
        f"its chassis options imply {sorted(chassis)} kg as the mass in running order. "
        f"Only the lighter chassis is recorded, that being the base vehicle and the one "
        f"the quoted price buys"
    ]


def _build_extracted_motorhome(product: ElnaghProduct) -> ExtractedMotorhome:
    """One layout as a `Motorhome`, plus the provenance a reviewer sees beside each field."""
    source_url = product.source_url
    features = habitation.features_from(product.copy_lines)
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
        body_type=BODY_TYPE,
        # Habitation, from the layout's bed list and the equipment lines that apply to it.
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
    if product.mh_width_mm is not None:
        record(
            "mh_width_mm",
            f"'OVERALL WIDTH (MIRRORS FOLDED) {product.mh_width_mm}mm'. On a coachbuilt "
            f"the body overhangs the folded mirrors, so this measures the body",
        )
    if product.mh_height_mm is not None:
        record("mh_height_mm", f"'OVERALL HEIGHT {product.mh_height_mm}mm'")
    if product.mh_passenger_seats_inc_driver is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"'BELTS {product.mh_passenger_seats_inc_driver}', this page's word for a "
            f"belted travel seat",
        )
    if product.berths is not None:
        record("berths", f"'BERTHS {product.berths}'")
    if product.mtplm_kilograms is not None:
        record(
            "mtplm_kilograms",
            f"'MTPLM {product.mtplm_kilograms}kg', the lighter of the two chassis offered "
            f"and the one the quoted price buys",
        )
    if product.mh_payload_kilograms is not None:
        record(
            "mh_payload_kilograms",
            f"'MAX USER PAYLOAD ({product.mtplm_kilograms}KG CHASSIS) Manual "
            f"{product.mh_payload_kilograms}kg'",
        )
    if product.mro_kilograms is not None:
        record(
            "mro_kilograms",
            f"derived as MTPLM {product.mtplm_kilograms}kg minus payload "
            f"{product.mh_payload_kilograms}kg. This page prints no MIRO, but its two "
            f"chassis both imply {product.mro_kilograms}kg",
        )
    if product.rrp_pounds is not None:
        record(
            "rrp_pounds",
            f"'£{product.rrp_pounds:,} OTR'. Marquis are the sole UK importer, so this is "
            f"the price that counts",
        )
    record("body_type", "the whole Baron range is a low-profile coachbuilt")
    record("base_vehicle_manufacturer", "every layout is a Fiat Ducato")

    for field_name, feature in features.items():
        detail = f" — {feature.note}" if feature.note else ""
        provenance[field_name] = Provenance(
            source_url=source_url,
            snippet=(
                f"{product.label} — the Baron range page says {feature.snippet!r}{detail}"
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
    """Every layout on the importer's current Elnagh range page."""
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
            f"{EXPECTED_LAYOUTS}. This page prints no MIRO, so the roster count is the "
            f"main defence — check the range page before accepting"
        )
    on_progress(f"collected {len(results)} product(s)")
    return results
