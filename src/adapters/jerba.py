"""Jerba Campervans (jerbacampervans.co.uk) — campervans on three base vehicles.

See `docs/adapters/jerba.md` for the survey. **This adapter is shaped by one fact: the
website publishes no numbers at all.** All eleven pages were searched and there is no
price, no weight and no dimension on any of them; the only `kg` figures anywhere are roof
load limits. So the figures are constants here, supplied by the requester as a layout
brochure and three price lists, exactly as in `joa.py`.

What the site *is* good for is **existence**. Every product has a live model page, and a
run fetches each one. A page that stops resolving is narrated loudly, because for this
manufacturer it is the only evidence a run can gather on its own.

**The two document types are each incomplete, in opposite directions**, which is why
`PRODUCTS` is the union of them rather than either one:

* The **Jura** has a model page and a full column in the layout brochure, and appears in
  **neither** price list. It is collected with **no price at all** — never an invented POA,
  and never a blank, which would wipe what FMLV holds.
* The **MWB Harris** is priced in the Crafter list at GBP83,500 beside the long-wheelbase
  Harris at GBP88,500, and has **no column in the layout brochure**. It is collected with
  its price, roof and wheelbase, and nothing else; its length is not recorded, because
  "probably 5986 mm like the other mediums" is an inference and not a published figure.

**There are no weights.** Jerba were asked for them on 1 October 2026 and did not reply,
and the requester ruled that the build proceeds without. `mtplm_kilograms`,
`mro_kilograms` and `mh_payload_kilograms` are therefore **not emitted at all** — omitted,
not blanked, so FMLV's own figures stand.

**The self-check is weak and this should be said plainly.** `payload = MTPLM - MRO` is
unavailable because none of the three is published. What the documents do give is two
independent statements of the same facts, and both are checked every run by
`document_disagreements`:

* the **roof and wheelbase** are stated by the layout brochure *and* by the price list;
* every **VW T7 price is exactly GBP2,000 above its Ford twin** across all four shared
  layouts.

The first has already earned its place: the T7 list calls the Taransay a *front* elevating
roof where the Ford list and the brochure both say *rear*. That disagreement is reported
on every run rather than resolved here, because one of the two documents is wrong and this
adapter is not the thing that should guess which.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

__all__ = [
    "BASE_URL",
    "EXPECTED_PRODUCTS",
    "HIGH_TOP_ABOVE_MM",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "PRICE_LIST_SOURCE",
    "PRODUCTS",
    "JerbaProduct",
    "body_type_for",
    "collect",
    "document_disagreements",
]

BASE_URL = "https://www.jerbacampervans.co.uk"

#: NCC id 11. The supplier list spells it the same as the manufacturer list.
MANUFACTURER = "Jerba Campervans"
MANUFACTURER_DISPLAY_NAME = "Jerba"

#: A campervan taller than this is a high top. The shared NCC threshold, as used by
#: `auto_trail.py`, `bailey.py`, `elddis.py`, `joa.py` and `wildax.py`.
HIGH_TOP_ABOVE_MM = 2300

#: Named in every provenance snippet so a reviewer can see which document a figure came
#: from without opening this file. Move it on when a new set arrives.
PRICE_LIST_SOURCE = (
    "the 2026 Jerba layout brochure and factory-options price lists, supplied 1 October 2026"
)

#: Fourteen: five layouts on each of the two panel vans, plus four Crafters. See the module
#: docstring for why this is the union of two documents that disagree about its edges.
EXPECTED_PRODUCTS = 14


@dataclass(frozen=True)
class JerbaProduct:
    """One campervan, as the supplied documents describe it.

    Every field is `None` where the documents do not state it, and a `None` is **emitted
    as nothing** rather than as a blank — see `_build_extracted`.
    """

    #: The layout name, which is what FMLV holds in **`manufacturer_range`**.
    #:
    #: **Not the base vehicle, which is the natural guess and is wrong.** FMLV files these
    #: the other way up: range `Tiree`, model `T7`. Built the obvious way round — range
    #: `VW T7`, model `Tiree` — not one of the five existing products matched, and a run
    #: would have added fourteen new ones beside them. Confirmed against the export,
    #: 5 October 2026.
    layout: str
    #: The base vehicle as FMLV writes it in **`model`**: `T7`, `Transit Custom`,
    #: `Crafter`. Not the make — that is `base_vehicle`, which FMLV holds separately as
    #: `VW` or `Ford`.
    model: str
    #: The make, routed through `fmlv_base_vehicle`. `VW` for the T7 and the Crafter.
    base_vehicle: str
    #: Path under `BASE_URL`. Fetched every run purely to confirm the product still exists.
    page: str
    #: How the **layout brochure** describes the roof, or `None` where it draws no column.
    brochure_roof: str | None
    #: How the **price list** describes the roof, or `None` where it does not price it.
    price_list_roof: str | None
    wheelbase: str
    length_mm: int | None
    width_mm: int
    height_mm: int
    #: The lower figure of a "sleeps 2 / 4" range — the berths available without options.
    berths: int | None
    #: The brochure's `BELTED TRAVEL SEATS` row. Quoted verbatim in the provenance,
    #: because only three-point belts count and nobody has confirmed these are.
    belted_travel_seats: int | None
    price_pounds: int | None

    @property
    def label(self) -> str:
        return f"{self.layout} {self.model}"

    @property
    def url(self) -> str:
        return f"{BASE_URL}{self.page}"


#: The two panel vans share one layout brochure and one set of five names, so the
#: dimensions and habitation figures below are the same on both; only the base vehicle and
#: the price change. Body width is the figure that **excludes mirrors** (2062 mm, against
#: 2276 mm including them) — the rule in `docs/adapters/README.md`.
_PANEL_VAN_WIDTH_MM = 2062
_PANEL_VAN_HEIGHT_MM = 2068
_PANEL_VAN_HIGH_TOP_HEIGHT_MM = 2488

#: The Crafter's own key: 2040 mm excluding mirrors against 2427 mm including them, and
#: 2590 mm tall, so every Crafter clears the high-top threshold.
_CRAFTER_WIDTH_MM = 2040
_CRAFTER_HEIGHT_MM = 2590

PRODUCTS: tuple[JerbaProduct, ...] = (
    # --- VW T7 -------------------------------------------------------------------------
    JerbaProduct(
        layout="Tiree", model="T7", base_vehicle="VW",
        page="/tiree-swb-campervan-layout/",
        brochure_roof="front elevating", price_list_roof="front elevating",
        wheelbase="short", length_mm=5050,
        width_mm=_PANEL_VAN_WIDTH_MM, height_mm=_PANEL_VAN_HEIGHT_MM,
        berths=2, belted_travel_seats=5, price_pounds=71000,
    ),
    JerbaProduct(
        layout="Cromarty", model="T7", base_vehicle="VW",
        page="/cromarty-lwb-campervan-layout",
        brochure_roof="front elevating", price_list_roof="front elevating",
        wheelbase="long", length_mm=5450,
        width_mm=_PANEL_VAN_WIDTH_MM, height_mm=_PANEL_VAN_HEIGHT_MM,
        berths=2, belted_travel_seats=5, price_pounds=74000,
    ),
    JerbaProduct(
        layout="Sanna", model="T7", base_vehicle="VW",
        page="/sanna-lwb-campervan-layout",
        brochure_roof="rear elevating", price_list_roof="rear elevating",
        wheelbase="long", length_mm=5450,
        width_mm=_PANEL_VAN_WIDTH_MM, height_mm=_PANEL_VAN_HEIGHT_MM,
        berths=2, belted_travel_seats=4, price_pounds=75000,
    ),
    # The one product the two documents describe differently — see `document_disagreements`.
    JerbaProduct(
        layout="Taransay", model="T7", base_vehicle="VW",
        page="/taransay-campervan/",
        brochure_roof="rear elevating", price_list_roof="front elevating",
        wheelbase="short", length_mm=5050,
        width_mm=_PANEL_VAN_WIDTH_MM, height_mm=_PANEL_VAN_HEIGHT_MM,
        berths=2, belted_travel_seats=4, price_pounds=73000,
    ),
    JerbaProduct(
        layout="Jura", model="T7", base_vehicle="VW",
        page="/jura-campervan/",
        brochure_roof="fixed high top", price_list_roof=None,
        wheelbase="long", length_mm=5450,
        width_mm=_PANEL_VAN_WIDTH_MM, height_mm=_PANEL_VAN_HIGH_TOP_HEIGHT_MM,
        berths=2, belted_travel_seats=4, price_pounds=None,
    ),
    # --- Ford Transit Custom -----------------------------------------------------------
    JerbaProduct(
        layout="Tiree", model="Transit Custom", base_vehicle="Ford",
        page="/tiree-swb-campervan-layout/",
        brochure_roof="front elevating", price_list_roof="front elevating",
        wheelbase="short", length_mm=5050,
        width_mm=_PANEL_VAN_WIDTH_MM, height_mm=_PANEL_VAN_HEIGHT_MM,
        berths=2, belted_travel_seats=5, price_pounds=69000,
    ),
    JerbaProduct(
        layout="Cromarty", model="Transit Custom", base_vehicle="Ford",
        page="/cromarty-lwb-campervan-layout",
        brochure_roof="front elevating", price_list_roof="front elevating",
        wheelbase="long", length_mm=5450,
        width_mm=_PANEL_VAN_WIDTH_MM, height_mm=_PANEL_VAN_HEIGHT_MM,
        berths=2, belted_travel_seats=5, price_pounds=72000,
    ),
    JerbaProduct(
        layout="Sanna", model="Transit Custom", base_vehicle="Ford",
        page="/sanna-lwb-campervan-layout",
        brochure_roof="rear elevating", price_list_roof="rear elevating",
        wheelbase="long", length_mm=5450,
        width_mm=_PANEL_VAN_WIDTH_MM, height_mm=_PANEL_VAN_HEIGHT_MM,
        berths=2, belted_travel_seats=4, price_pounds=73000,
    ),
    JerbaProduct(
        layout="Taransay", model="Transit Custom", base_vehicle="Ford",
        page="/taransay-campervan/",
        brochure_roof="rear elevating", price_list_roof="rear elevating",
        wheelbase="short", length_mm=5050,
        width_mm=_PANEL_VAN_WIDTH_MM, height_mm=_PANEL_VAN_HEIGHT_MM,
        berths=2, belted_travel_seats=4, price_pounds=71000,
    ),
    JerbaProduct(
        layout="Jura", model="Transit Custom", base_vehicle="Ford",
        page="/jura-campervan/",
        brochure_roof="fixed high top", price_list_roof=None,
        wheelbase="long", length_mm=5450,
        width_mm=_PANEL_VAN_WIDTH_MM, height_mm=_PANEL_VAN_HIGH_TOP_HEIGHT_MM,
        berths=2, belted_travel_seats=4, price_pounds=None,
    ),
    # --- VW Crafter --------------------------------------------------------------------
    JerbaProduct(
        layout="Mull", model="Crafter", base_vehicle="VW",
        page="/mull-crafter-layout/",
        brochure_roof="fixed high roof", price_list_roof="fixed high roof",
        wheelbase="medium", length_mm=5986,
        width_mm=_CRAFTER_WIDTH_MM, height_mm=_CRAFTER_HEIGHT_MM,
        berths=2, belted_travel_seats=4, price_pounds=85500,
    ),
    JerbaProduct(
        layout="Barra", model="Crafter", base_vehicle="VW",
        page="/barra-campervan-layout/",
        brochure_roof="fixed high roof", price_list_roof="fixed high roof",
        wheelbase="medium", length_mm=5986,
        width_mm=_CRAFTER_WIDTH_MM, height_mm=_CRAFTER_HEIGHT_MM,
        berths=2, belted_travel_seats=5, price_pounds=77500,
    ),
    JerbaProduct(
        layout="Harris", model="Crafter", base_vehicle="VW",
        page="/harris-campervan-layout/",
        brochure_roof="fixed high roof", price_list_roof="fixed high roof",
        wheelbase="long", length_mm=6836,
        width_mm=_CRAFTER_WIDTH_MM, height_mm=_CRAFTER_HEIGHT_MM,
        berths=4, belted_travel_seats=4, price_pounds=88500,
    ),
    # Priced but never drawn. Length is deliberately `None`: the other mediums are 5986 mm
    # but nobody has published this one's, and an inferred dimension is not a figure.
    JerbaProduct(
        layout="Harris MWB", model="Crafter", base_vehicle="VW",
        page="/harris-campervan-layout/",
        brochure_roof=None, price_list_roof="fixed high roof",
        wheelbase="medium", length_mm=None,
        width_mm=_CRAFTER_WIDTH_MM, height_mm=_CRAFTER_HEIGHT_MM,
        berths=None, belted_travel_seats=None, price_pounds=83500,
    ),
)


def body_type_for(product: JerbaProduct) -> tuple[BodyType | None, str]:
    """The body style, from the roof the documents describe and the published height.

    Every Jerba is a van conversion, so the only question is the roof:

    * a **fixed high roof or high top** clears the 2300 mm threshold on both platforms —
      2488 mm on the Jura, 2590 mm on every Crafter;
    * an **elevating roof** at 2068 mm does not, so those are elevating-roof campervans
      and not high tops.

    The Crafters offer an *optional* ATEC elevating roof. It is deliberately ignored: an
    optional rising roof never changes what the vehicle is, which is the base-vehicle rule
    in `docs/adapters/README.md` and the same call `joa.py` makes about its pop-up.
    """
    roof = product.brochure_roof or product.price_list_roof
    if not roof:
        return None, "neither document describes the roof"

    over_threshold = product.height_mm > HIGH_TOP_ABOVE_MM
    if "elevating" in roof and not over_threshold:
        return BodyType.CAMPERVAN_ELEVATING_ROOF, (
            f"an elevating-roof campervan: the documents describe a {roof} roof and the "
            f"published height of {product.height_mm}mm does not reach the "
            f"{HIGH_TOP_ABOVE_MM}mm high-top threshold"
        )
    if "high" in roof and over_threshold:
        return BodyType.CAMPERVAN_HIGH_TOP, (
            f"a high top campervan: the documents describe a {roof} roof and the published "
            f"height of {product.height_mm}mm is over the {HIGH_TOP_ABOVE_MM}mm threshold"
        )
    return None, (
        f'no body style can be derived from a "{roof}" roof at {product.height_mm}mm'
    )


def document_disagreements() -> list[str]:
    """Every place the layout brochure and the price lists contradict each other.

    **The nearest thing this manufacturer has to a self-check.** With no masses there is no
    arithmetic to reconcile, so what is checked instead is that two independently written
    documents agree about the same vehicles — the roof each one describes, and the GBP2,000
    step between a VW T7 and its Ford twin.

    Reported on every run rather than resolved: where two supplied documents disagree, one
    of them is wrong, and picking a winner silently is how a wrong figure becomes a fact.
    """
    found: list[str] = []

    for product in PRODUCTS:
        if (
            product.brochure_roof is not None
            and product.price_list_roof is not None
            and product.brochure_roof != product.price_list_roof
        ):
            found.append(
                f"{product.label}: the layout brochure calls it a "
                f"{product.brochure_roof} roof, the price list a "
                f"{product.price_list_roof} one. One of the two documents is wrong — ask "
                f"Jerba. The body type is derived from the brochure, which agrees with "
                f"its own drawing"
            )

    by_layout = {(p.layout, p.model): p for p in PRODUCTS}
    for (layout, model), vw in by_layout.items():
        if model != "T7":
            continue
        ford = by_layout.get((layout, "Transit Custom"))
        if ford is None or vw.price_pounds is None or ford.price_pounds is None:
            continue
        step = vw.price_pounds - ford.price_pounds
        if step != 2000:
            found.append(
                f"{layout}: the VW T7 is GBP{step:,} above the Ford Transit Custom, where "
                f"every other shared layout is GBP2,000 apart. One of the two prices has "
                f"been misread or the lists have moved apart"
            )
    return found


def _build_extracted(product: JerbaProduct) -> ExtractedMotorhome:
    """One product as a `Motorhome`, with the provenance naming its document.

    **A figure the documents do not state is left `None` and gets no provenance**, so the
    pipeline emits nothing for it and FMLV's own value stands. That is how all three masses
    behave on every product, and how the price behaves on the two Juras.
    """
    body_type, body_reason = body_type_for(product)

    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.layout,
        model=product.model,
        base_vehicle_manufacturer=fmlv_base_vehicle(product.base_vehicle),
        berths=product.berths,
        mh_passenger_seats_inc_driver=product.belted_travel_seats,
        rrp_pounds=product.price_pounds,
        mh_length_mm=product.length_mm,
        mh_width_mm=product.width_mm,
        mh_height_mm=product.height_mm,
        body_type=body_type,
        # No masses anywhere: see the module docstring. Omitted, never blanked.
        mtplm_kilograms=None,
        mro_kilograms=None,
        mh_payload_kilograms=None,
    )

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(source_url=product.url, snippet=snippet)

    # **The two identity fields are recorded deliberately.** `compare_fields` only looks
    # at fields the adapter gives provenance for, so without these a wrong name in FMLV can
    # never be corrected by a run — which is exactly the state the Mull was in, filed as
    # `Mull / Mull` where every sibling carries the base vehicle in the model.
    record(
        "manufacturer_range",
        f"the layout name as {PRICE_LIST_SOURCE} and the model page both give it. FMLV "
        f"files these by layout, not by base vehicle: range {product.layout!r}, model "
        f"{product.model!r}",
    )
    record(
        "model",
        f"{product.model!r}, the base vehicle. FMLV holds the marque separately in "
        f"base_vehicle_manufacturer ({product.base_vehicle!r}), so this column carries the "
        f"range designation rather than the make",
    )
    record(
        "base_vehicle_manufacturer",
        f"{product.layout} on the {product.model}, {product.wheelbase} wheel base, from "
        f"{PRICE_LIST_SOURCE}",
    )
    if product.price_pounds is not None:
        record(
            "rrp_pounds",
            f"{product.label}: GBP{product.price_pounds:,} inc VAT, the starting price in "
            f"{PRICE_LIST_SOURCE}. It includes the listed factory features, a full tank of "
            f"fuel, number plates and all charges; every transmission, paint and equipment "
            f"line in the same document is an option and is not recorded",
        )
    if product.berths is not None:
        record(
            "berths",
            f"the layout brochure states "
            f"{'sleeps 4 / 6' if product.berths == 4 else 'sleeps 2 / 4'} for the "
            f"{product.model}; the lower figure is recorded, being the berths available "
            f"without options",
        )
    if product.belted_travel_seats is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"the layout brochure's BELTED TRAVEL SEATS row states "
            f"{product.belted_travel_seats} for the {product.model}. **It does not say "
            f"whether all of them are three-point** — only three-point belts count, so if "
            f"any of these is a lap belt the figure is lower",
        )
    if product.length_mm is not None:
        record(
            "mh_length_mm",
            f"{product.length_mm}mm, the overall length the layout brochure prints beneath "
            f"the {product.model}'s side elevation ({product.wheelbase} wheel base)",
        )
    record(
        "mh_width_mm",
        f"{product.width_mm}mm, the body width in the brochure's dimensions key. The key "
        f"also gives a wider figure that includes the mirrors, which is not what FMLV holds",
    )
    record(
        "mh_height_mm",
        f"{product.height_mm}mm, the overall height in the brochure's dimensions key "
        f"({product.brochure_roof or product.price_list_roof} roof)",
    )
    if body_type is not None:
        record("body_type", body_reason)

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001
    snapshot_dir: Path,  # noqa: ARG001
    *,
    ranges: tuple[tuple[str, str], ...] = (),  # noqa: ARG001
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every campervan Jerba sell, from the supplied documents.

    **Eleven fetches**, one per distinct model page. They contribute no figures — the site
    has none — and exist only to confirm each product still has a page. A page that stops
    resolving is narrated as a warning and the product is **still collected**, because the
    price list is the more recent document and a missing page is not the same as a
    withdrawal; see the Carthago note in `docs/adapters/README.md` about what a silent drop
    costs.
    """
    for message in document_disagreements():
        on_progress(f"DOCUMENTS DISAGREE — {message}")

    checked: dict[str, bool] = {}
    for page in dict.fromkeys(product.page for product in PRODUCTS):
        url = f"{BASE_URL}{page}"
        try:
            http.fetch(url)
            checked[page] = True
        except Exception as error:  # noqa: BLE001
            checked[page] = False
            on_progress(
                f"WARNING: {url} did not resolve ({type(error).__name__}). Jerba publish "
                f"no figures on their pages, so this costs no data — but it is the only "
                f"sign a run can get that a model has been withdrawn. Its product is still "
                f"collected from the price list; check whether it is still on sale"
            )

    extracted: list[ExtractedMotorhome] = []
    for product in PRODUCTS:
        extracted.append(_build_extracted(product))
        missing = [
            name
            for name, value in (
                ("price", product.price_pounds),
                ("berths", product.berths),
                ("belted travel seats", product.belted_travel_seats),
                ("length", product.length_mm),
            )
            if value is None
        ]
        note = f" — no {', '.join(missing)} in any document" if missing else ""
        on_progress(
            f"read {product.label}"
            f"{'' if checked.get(product.page, True) else ' (its page did not resolve)'}"
            f"{note}"
        )

    on_progress(
        f"{len(extracted)} product(s) collected. No mass is emitted for any of them: "
        f"Jerba publish none and did not supply any when asked, so FMLV's own MTPLM, MRO "
        f"and payload stand"
    )
    if len(extracted) != EXPECTED_PRODUCTS:
        on_progress(
            f"expected {EXPECTED_PRODUCTS} products and built {len(extracted)} — PRODUCTS "
            f"has been edited without its count being updated"
        )
    return extracted
