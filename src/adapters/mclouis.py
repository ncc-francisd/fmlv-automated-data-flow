"""McLouis — four UK layouts, one page each, from the brand's own UK site.

`docs/adapters/mclouis.md` is the survey; this is what it decided.

Last of the six Trigano brands, and **the only one that is not a Marquis page**, so none of
`adapters/marquis.py` applies here. Marquis do sell McLouis but not exclusively, and the
brand is absent from `marquisleisure.co.uk` altogether — no brand index, no range page. The
UK operation runs its own site instead, `mclouisfusion.co.uk`, published by Auto-Sleepers
Limited of Willersey, which is why the wording echoes `auto_sleepers.py` and `elnagh.py`.

**One page per layout**, unlike every Marquis brand, and each carries the lot: the belted
seat count, the berths, the dimensions, three chassis' worth of weights, the price and the
full standard-equipment list.

Three things are worth knowing:

* **the weights come in threes** — `3500kg | 3650kg | 4400kg` — and each column closes
  against its own MIRO and payload, which makes this the strongest self-check of the six;
* **the equipment list qualifies lines per layout**, in the same house style as Elnagh but
  spelling it `(exc 330)` rather than `(excl …)`. See `habitation.lines_for_layout`;
* **the brochure's price list disagrees with the site** on three of the four layouts, and
  the site wins by the settled rule. See `PRICE`.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from . import habitation
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

MANUFACTURER = "Trigano S A McLouis"
MANUFACTURER_DISPLAY_NAME = "McLouis"

BASE_URL = "https://www.mclouisfusion.co.uk"

#: The roster page, which links one page per layout.
INDEX_URL = f"{BASE_URL}/explore-the-range"

#: A layout's own page. The slug carries the model code, so the roster needs no parsing of
#: prose — `/explore-the-range/fusion-330`.
MODEL_HREF = re.compile(
    rf"href=\"(?:{re.escape(BASE_URL)})?(/explore-the-range/fusion-(?P<model>\d+))\"", re.I
)

#: FMLV's `manufacturer_range` for every current layout.
#:
#: FMLV also holds older rows under `Fusion 1`, and four 2025 `Baron` rows that moved to
#: Elnagh for 2026. `cli._is_current_model_year` drops all of them from the baseline.
RANGE = "Fusion"

#: Every layout is a `FIAT DUCATO 140BHP MANUAL ENGINE`, per the site's own price line.
BASE_VEHICLE = "Fiat"

#: Every layout is a low-profile coachbuilt — the site's word is `Coachbuilt`, each has an
#: electric drop-down bed rather than a fixed over-cab one, and FMLV holds
#: `type_coach_built_low_profile` for all fifteen of its McLouis rows.
BODY_TYPE = BodyType.COACH_BUILT_LOW_PROFILE

#: `(slug key, label)` for `--range`, matched against the model code.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (
    ("330", "Fusion 330"),
    ("360", "Fusion 360"),
    ("373", "Fusion 373"),
    ("379", "Fusion 379"),
)

#: What the roster should come to.
#:
#: The brochure's cover states it independently — *"4 BERTHS MODEL RANGE 4 | 4 - 5
#: SEATBELTS"* — and the range page's own copy says *"4 coachbuilt models"*.
EXPECTED_LAYOUTS = 4

_TAGS = re.compile(r"(?is)<(script|style)\b.*?</\1>")


def plain_text(page: str) -> str:
    """The page as one line, tags replaced by a single space and entities resolved."""
    stripped = re.sub(r"<[^>]+>", " ", _TAGS.sub(" ", page))
    return re.sub(r"\s+", " ", html.unescape(html.unescape(stripped))).strip()


#: The counts, which the site labels unambiguously.
#:
#: **`Designated Passenger Seats` is a belted count**, not a seating capacity: the
#: brochure's cover reads *"4 - 5 SEATBELTS"* across the range, and the equipment list
#: explains the difference as a *"5th Homologated seat in running order (exc 330)"*. So the
#: settled rule to count three-point belts only is satisfied — nothing here is a lap belt.
COUNTS: dict[str, re.Pattern[str]] = {
    "seats": re.compile(r"Designated Passenger Seats\s+(\d+)", re.I),
    "berths": re.compile(r"Berths \(sleeping positions\)\s+(\d+)", re.I),
}

#: The dimensions, **published in metres to two decimals** rather than millimetres.
#:
#: `Overall length 6.59m`. The case is not consistent — the 360 page capitalises `Length`
#: where the other three do not — so every pattern is case-insensitive.
DIMENSIONS: dict[str, re.Pattern[str]] = {
    "length": re.compile(r"Overall length\s+(\d+(?:\.\d+)?)\s*m\b", re.I),
    "width": re.compile(r"Overall width \(mirrors folded\)\s+(\d+(?:\.\d+)?)\s*m\b", re.I),
    "height": re.compile(r"Overall height\s+(\d+(?:\.\d+)?)\s*m\b", re.I),
}

#: One weights row and every chassis column in it.
#:
#: `MTPLM (a)* 3500kg | 3650kg | 4400kg`, and the same shape for the other two rows. The
#: asterisk count varies between pages, hence `[*+]*`.
WEIGHTS: dict[str, re.Pattern[str]] = {
    "mtplm": re.compile(r"MTPLM \(a\)[*+]*\s+(?P<figures>[\d\s|kg]+)", re.I),
    "mro": re.compile(r"Mass in running order \(b\)[*+]*\s+(?P<figures>[\d\s|kg]+)", re.I),
    "payload": re.compile(
        r"Maximum user payload[*+]* \(a-b\)[*+]*\s+(?P<figures>[\d\s|kg]+)", re.I
    ),
}

#: The headline price. **The site's, not the brochure's.**
#:
#: The 2026 brochure price list says £74,995 for the 360 and £76,995 for the 373 and 379,
#: where the site says £77,495 and £79,495 — £2,500 apart on three of the four. The settled
#: rule is that the website over-rules a document unless the site can be shown wrong, and
#: FMLV's own figures match the site, so the site it is.
PRICE = re.compile(r"OTR Price From\s+£\s*(?P<price>[\d,]{5,})", re.I)

#: The page states a rear garage per layout, with its aperture and its load limit.
REAR_GARAGE = re.compile(r"Rear Garage Max Load (?:Capacity|Limit)\s+(\d+)\s*kg", re.I)

#: A layout's bed list, between its garage figures and the small print.
BED_SECTION = re.compile(r"Bed Sizes\s+(?P<beds>.*?)(?=IMPORTANT INFORMATION|$)", re.S)

#: A bed's size, which has to swallow the whole thing including any repeated `mm`.
#:
#: McLouis are inconsistent about where the unit goes, within a single page:
#:
#: | | |
#: |---|---|
#: | `1300 x1100x1900mm` | suffixed once, at the end |
#: | `1300mm x 2070mm` | suffixed on every figure |
#: | `1230mm x 1030mm x 1900mm` | three figures, each suffixed |
#: | `1500mm x 1900m` | and a typo, one `m` |
#:
#: Stopping at the first `mm` left `x 2070mm` behind, which the next iteration then read as
#: a bed named `x`.
_BED_SIZE = r"[\dx×\s]*\d\s*m{1,2}(?:\s*[x×]\s*[\d\s]*\d\s*m{0,2})*"

#: One bed in that list: a name, then the size that ends it.
#:
#: **The name carries no `Bed`**, unlike every Marquis brand — `Rear Drop Down Double`,
#: `Front Single` — so the split keys on the size alone and the word is appended after.
BED_ENTRY = re.compile(rf"(?P<name>[A-Za-z][A-Za-z\s]*?)\s+{_BED_SIZE}", re.I)


def find_model_urls(index_html: str, wanted: Iterable[str]) -> list[tuple[str, str]]:
    """`(model, url)` for every layout the roster page links, in page order."""
    keys = tuple(wanted)
    found: list[tuple[str, str]] = []
    for match in MODEL_HREF.finditer(index_html):
        model, url = match.group("model"), f"{BASE_URL}{match.group(1)}"
        if keys and model not in keys:
            continue
        if all(url != seen for _model, seen in found):
            found.append((model, url))
    return found


def _millimetres(text: str, key: str) -> int | None:
    """One dimension, converted from the site's metres to FMLV's millimetres."""
    match = DIMENSIONS[key].search(text)
    return round(float(match.group(1)) * 1000) if match else None


def _weights(text: str, key: str) -> list[int]:
    """Every chassis column of one weights row, in the page's order.

    The first is the base vehicle — the 3500 kg manual the quoted price buys — and the
    settled rule takes it. The rest are the uprated chassis and the automatic.
    """
    match = WEIGHTS[key].search(text)
    if match is None:
        return []
    return [int(figure) for figure in re.findall(r"(\d+)\s*kg", match.group("figures"))]


def _bed_lines(text: str) -> list[str]:
    """The beds one layout's page names, as lines `habitation` can read."""
    section = BED_SECTION.search(text)
    if section is None:
        return []
    names = [
        re.sub(r"\s+", " ", match.group("name")).strip()
        for match in BED_ENTRY.finditer(section.group("beds"))
    ]
    return [f"{name} bed" for name in names if name]


@dataclass(frozen=True)
class McLouisProduct:
    """One layout, from its own page."""

    source_url: str
    model: str
    mh_passenger_seats_inc_driver: int | None = None
    berths: int | None = None
    mh_length_mm: int | None = None
    mh_width_mm: int | None = None
    mh_height_mm: int | None = None
    mtplm_figures: tuple[int, ...] = ()
    mro_figures: tuple[int, ...] = ()
    payload_figures: tuple[int, ...] = ()
    rrp_pounds: int | None = None
    rear_garage: bool | None = None
    copy_lines: tuple[str, ...] = ()

    @property
    def manufacturer_range(self) -> str:
        return RANGE

    @property
    def label(self) -> str:
        return f"{RANGE} {self.model}"

    @property
    def mtplm_kilograms(self) -> int | None:
        return self.mtplm_figures[0] if self.mtplm_figures else None

    @property
    def mro_kilograms(self) -> int | None:
        return self.mro_figures[0] if self.mro_figures else None

    @property
    def mh_payload_kilograms(self) -> int | None:
        return self.payload_figures[0] if self.payload_figures else None


def read_model_page(page: str, model: str, source_url: str) -> McLouisProduct:
    """One layout, from its own page."""
    text = plain_text(page)
    garage = REAR_GARAGE.search(text)
    return McLouisProduct(
        source_url=source_url,
        model=model,
        mh_passenger_seats_inc_driver=(
            int(m.group(1)) if (m := COUNTS["seats"].search(text)) else None
        ),
        berths=int(m.group(1)) if (m := COUNTS["berths"].search(text)) else None,
        mh_length_mm=_millimetres(text, "length"),
        mh_width_mm=_millimetres(text, "width"),
        mh_height_mm=_millimetres(text, "height"),
        mtplm_figures=tuple(_weights(text, "mtplm")),
        mro_figures=tuple(_weights(text, "mro")),
        payload_figures=tuple(_weights(text, "payload")),
        rrp_pounds=(
            int(m.group("price").replace(",", "")) if (m := PRICE.search(text)) else None
        ),
        rear_garage=True if garage else None,
        copy_lines=tuple(_bed_lines(text))
        + tuple(habitation.lines_for_layout(habitation.list_items(page), model)),
    )


def _reconciles(product: McLouisProduct) -> tuple[bool, str]:
    """`(ok, why not)` — the page's own `(a-b)` arithmetic, on every chassis it publishes.

    **The strongest self-check of the six Trigano brands.** McLouis print three chassis
    columns and label the payload row `Maximum user payload+ (a-b)`, so each column is an
    independent statement that `MTPLM - MIRO = payload`:

    ```
    MTPLM (a)*                  3500kg | 3650kg | 4400kg
    Mass in running order (b)   2910kg | 2910kg | 2970kg
    Maximum user payload+ (a-b)  590kg |  740kg | 1430kg
    ```

    All three closed exactly on all four layouts at survey. A column read out of step with
    its neighbours — the fault this exists to catch — breaks the identity immediately.

    The three rows must also be the **same length**, because a row that yields fewer
    figures than its neighbours means the columns no longer line up, and pairing them by
    position would then compare a 3500 kg chassis against a 4400 kg one.
    """
    rows = (product.mtplm_figures, product.mro_figures, product.payload_figures)
    if not all(rows):
        return False, (
            "one of the three weights rows yielded nothing, so the page's shape has "
            "probably changed"
        )
    if len({len(row) for row in rows}) != 1:
        return False, (
            f"it publishes {len(product.mtplm_figures)} MTPLM figures, "
            f"{len(product.mro_figures)} masses in running order and "
            f"{len(product.payload_figures)} payloads. Those columns cannot be paired up"
        )
    for mtplm, mro, payload in zip(*rows, strict=True):
        if mtplm - mro != payload:
            return False, (
                f"the page states MTPLM {mtplm}kg, mass in running order {mro}kg and "
                f"payload {payload}kg, but its own (a-b) gives {mtplm - mro}kg"
            )
    return True, ""


def _build_extracted_motorhome(product: McLouisProduct) -> ExtractedMotorhome:
    """One layout as a `Motorhome`, plus the provenance a reviewer sees beside each field."""
    source_url = product.source_url
    features = habitation.features_from(product.copy_lines)
    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=RANGE,
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
        rear_garage=product.rear_garage,
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
            source_url=source_url, snippet=f"{product.label} — {snippet}"
        )

    if product.mh_length_mm is not None:
        record("mh_length_mm", f"'Overall length {product.mh_length_mm / 1000:.2f}m'")
    if product.mh_width_mm is not None:
        record(
            "mh_width_mm",
            f"'Overall width (mirrors folded) {product.mh_width_mm / 1000:.2f}m'. On a "
            f"coachbuilt the body overhangs the folded mirrors, so this measures the body",
        )
    if product.mh_height_mm is not None:
        record(
            "mh_height_mm",
            f"'Overall height {product.mh_height_mm / 1000:.2f}m'. The page adds that "
            f"heights are measured with the aerial in its lowest position, and the 2026 "
            f"brochure prints the same figure",
        )
    if product.mh_passenger_seats_inc_driver is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"'Designated Passenger Seats {product.mh_passenger_seats_inc_driver}'. The "
            f"brochure cover calls these seatbelts — '4 - 5 SEATBELTS' — and the equipment "
            f"list names a '5th Homologated seat in running order (exc 330)'",
        )
    if product.berths is not None:
        record("berths", f"'Berths (sleeping positions) {product.berths}'")
    if product.mtplm_kilograms is not None:
        record(
            "mtplm_kilograms",
            f"'MTPLM (a) {product.mtplm_kilograms}kg', the first of "
            f"{len(product.mtplm_figures)} chassis offered and the one the quoted price "
            f"buys",
        )
    if product.mro_kilograms is not None:
        record(
            "mro_kilograms",
            f"'Mass in running order (b) {product.mro_kilograms}kg', the same chassis "
            f"column as the MTPLM above",
        )
    if product.mh_payload_kilograms is not None:
        record(
            "mh_payload_kilograms",
            f"'Maximum user payload (a-b) {product.mh_payload_kilograms}kg' as printed, "
            f"and {product.mtplm_kilograms}kg minus {product.mro_kilograms}kg agrees",
        )
    if product.rrp_pounds is not None:
        record(
            "rrp_pounds",
            f"'2026 OTR Price From £{product.rrp_pounds:,}'. The brochure's price list "
            f"disagrees on three of the four layouts and the site is taken",
        )
    if product.rear_garage:
        record("rear_garage", "the page prints its aperture and its maximum load capacity")
    record("body_type", "the whole Fusion range is a low-profile coachbuilt")
    record("base_vehicle_manufacturer", "every layout is a Fiat Ducato")

    for field_name, feature in features.items():
        detail = f" — {feature.note}" if feature.note else ""
        provenance[field_name] = Provenance(
            source_url=source_url,
            snippet=f"{product.label} — its own page says {feature.snippet!r}{detail}",
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
    """Every current McLouis Fusion layout, one page each."""
    on_progress(f"fetching the range page: {INDEX_URL}")
    index = http.fetch(INDEX_URL)
    if index.status_code != 200:
        message = f"{INDEX_URL} returned {index.status_code}; it is the roster"
        raise RuntimeError(message)

    found = find_model_urls(
        index.file_path.read_text(encoding="utf-8", errors="replace"),
        (key for key, _label in ranges),
    )
    on_progress(f"{len(found)} layout page(s)")

    results: list[ExtractedMotorhome] = []
    for model, url in found:
        page_result = http.fetch(url)
        if page_result.status_code != 200:
            on_progress(f"SKIPPED [{RANGE} {model}]: {url} returned {page_result.status_code}")
            continue
        page = page_result.file_path.read_text(encoding="utf-8", errors="replace")

        product = read_model_page(page, model, url)
        reconciles, why_not = _reconciles(product)
        if not reconciles:
            on_progress(f"SKIPPED [{product.label}]: {why_not}")
            continue
        if product.rrp_pounds is None:
            on_progress(
                f"[{product.label}] WARNING: no OTR price on its page, so FMLV's own "
                f"figure is left alone"
            )
        results.append(_build_extracted_motorhome(product))

    if len(results) != EXPECTED_LAYOUTS:
        on_progress(
            f"WARNING: collected {len(results)} layout(s) where the survey found "
            f"{EXPECTED_LAYOUTS}. Check the range page before accepting"
        )
    on_progress(f"collected {len(results)} product(s)")
    return results
