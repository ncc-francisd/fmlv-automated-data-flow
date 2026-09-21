"""Adria touring caravans, the second product area on the same manufacturer row.

Sits beside `adria.py` the way `swift_caravan.py` sits beside `swift.py`. **The plumbing
is imported unchanged** — the caravan pages are the same Laravel+Livewire shape as the
motorhome ones, with the same scroll-triggered `/livewire/update` call and the same
per-configuration PDF at `configure.adria-mobil.com/<market>/<period>/<id>/pdf`. So
`parse_livewire_products`, `technical_data_pdf_url`, `pdf_title` and
`pdf_describes_layout` all come across as they are.

**The field mapping does not come across**, and that is the thing to know. `adria.py`'s
own spec reader takes `Body length` for the vehicle's length, which is right for a
motorhome and wrong for a caravan: FMLV's `shipping_length_mm` is the total *including
the tow bar*. On the Alpina 623 HT Rio Grande that is 8190 against a body length of 6890
— a 1.3 m error that looks entirely plausible in a review queue.

## FMLV records the MINIMUM permissible mass

Every caravan PDF states two:

```
Maximum technical permissable laden mass (MTPLM) ( kg ) 1800
Minimal technically permissible laden mass (MTPLM-min, kg) 1650
```

and FMLV holds the **second**. Verified on all eight readable products: the three Alteas
read 1650 where the maximum says 1800, the Adora Tiber 1800 against 1900, and the Alpina
Mississippi 1950 against 2000. Reading the maximum would record an uprated chassis as the
base vehicle on five of the eight — the settled base-vehicle rule, in the one place where
Adria makes it easy to get wrong.

`Mass in running order` is already published as `MIRO-min`, so it needs no such care.

## The payload is arithmetic, and Adria's own figure is not it

`Max loading weight (kg) with All Inclusive Pack weight deducted` reads 161 on the Rio
Grande where FMLV holds 215, because it subtracts a 48.2 kg option pack. FMLV's figure is
`MTPLM-min − MRO`, which matches on every comparable product.

That makes Adria the **second documented exception** to the caravan payload rule in
`docs/adapters/README.md`, after T@B: its `personal_effects_payload_kilograms` is the
whole arithmetic remainder, with `optional_equipment_payload_kilograms` empty on all 11
live rows.

## Height is proposed even though it disagrees with FMLV everywhere

The PDF's total height is **150 mm lower than FMLV's on all eight** comparable products —
2600 against 2750 on Alpina and Adora, 2580 against 2730 on Altea. A uniform offset across
two ranges is a definitional difference rather than eight errors, and Adria publish no
second height and no note about what theirs includes.

The requester's ruling, 21 September 2026: *"I would normally expect it to include any
fixtures … I think we should go with the height as expressed in the technical information
on the Adria site … simply because that's what the consumer is going to see. But there is
no explanation as to why it's different."* So it is proposed, and every height's
provenance says plainly that it disagrees with FMLV by 150 mm for no published reason.

## Trim labels are unreliable; the layout label is not

Altea's `622 DK AVON` carries the trim `Altea 622 DP Dart`, copied from its sibling, and
`612 DL TYNE` carries `Altea 612DL Tyne` with no space. The **layout** label matches
FMLV's model exactly on all eight matched products, so that is what the model is built
from and `model_includes_trim` is `False` throughout — the opposite of the motorhome
ranges.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from ..fetch.browser import BrowserFetcher
from ..fetch.http import Fetcher
from ..fetch.pdf import extract_text
from ..product_model.caravan import Caravan
from ..product_model.enums import CaravanBodyType
from ..vehicle_class import VehicleClass
from . import habitation
from .adria import (
    _LIVEWIRE_UPDATE_MARKER,
    BASE_URL,
    MANUFACTURER,
    MANUFACTURER_DISPLAY_NAME,
    LivewireProduct,
    RangeConfig,
    fitted_equipment,
    parse_livewire_products,
    pdf_describes_layout,
    pdf_title,
    technical_data_pdf_url,
)
from .base import ExtractedCaravan, Provenance

__all__ = [
    "BASE_URL",
    "DEFAULT_RANGES",
    "EXPECTED_LAYOUTS",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "RANGES",
    "RENAMED_MODELS",
    "VEHICLE_CLASS",
    "AdriaCaravan",
    "collect",
    "parse_caravan_pdf",
    "range_config",
]

#: What makes this the caravan adapter. Without it `ADAPTERS` would register the module
#: under `(Adria Mobil, Adria, motorhome)` and silently replace `adria.py`.
VEHICLE_CLASS = VehicleClass.CARAVAN

#: The four caravan ranges, read off `/caravans` and confirmed by the requester.
#: `model_includes_trim=False` on every one — see the module docstring.
RANGES: tuple[RangeConfig, ...] = (
    RangeConfig("caravans/alpina", "Alpina", "Alpina", model_includes_trim=False),
    RangeConfig("caravans/adora", "Adora", "Adora", model_includes_trim=False),
    RangeConfig("caravans/altea", "Altea", "Altea", model_includes_trim=False),
    RangeConfig("caravans/action", "Action", "Action", model_includes_trim=False),
)

DEFAULT_RANGES: tuple[tuple[str, str], ...] = tuple(
    (config.path, config.label) for config in RANGES
)

_RANGE_BY_LABEL: dict[str, RangeConfig] = {config.label: config for config in RANGES}

#: Ten configurations across the four ranges, against FMLV's eleven live rows.
EXPECTED_LAYOUTS = 10

#: What the site now calls a layout, against what FMLV still holds.
#:
#: **Evidenced on the mass, not the name.** `623 UL COLORADO` and FMLV's
#: `623 UC COLORADO` share a mass in running order of 1837 kg and a total length of
#: 8260 mm exactly — which is the test `docs/adapters/README.md` requires, and the one a
#: Globecar pairing failed by arguing from length alone.
RENAMED_MODELS: dict[tuple[str, str], tuple[str, str]] = {
    ("Alpina", "623 UL COLORADO"): ("Alpina", "623 UC COLORADO"),
}


def range_config(path: str, label: str) -> RangeConfig:
    """The `RangeConfig` for one `--range` selector, or a bare one if it is unknown."""
    known = _RANGE_BY_LABEL.get(label)
    if known is not None:
        return known
    return RangeConfig(path, label, label, model_includes_trim=False)


# --- reading the PDF ----------------------------------------------------------------

#: Every figure FMLV holds for an Adria caravan, and the line that states it.
#:
#: `shipping_length_mm` is the **total including the tow bar**, not the body length: see
#: the module docstring. `mtplm_kilograms` is the **minimum**, not the maximum.
_SPEC_PATTERNS: dict[str, re.Pattern[str]] = {
    "shipping_length_mm": re.compile(
        r"Total length \(including tow bar\) \(mm\)\s+(\d+)"
    ),
    "exterior_body_length_mm": re.compile(r"Body length \(mm\)\s+(\d+)"),
    "internal_length_mm": re.compile(r"Internal length \(mm\)\s+(\d+)"),
    "overall_width_mm": re.compile(r"Total width \(mm\)\s+(\d+)"),
    "height_mm": re.compile(r"Total height \(mm\)\s+(\d+)"),
    "headroom_mm": re.compile(r"Internal height \(mm\)\s+(\d+)"),
    "mro_kilograms": re.compile(r"Mass in running order \(MIRO-min, kg\)\s+(\d+)"),
    "mtplm_kilograms": re.compile(
        r"Minimal technically permissible laden mass \(MTPLM-min, kg\)\s+(\d+)"
    ),
}

#: `Awning perimeter dimensions (body/chassis, cm) 1083/638` — the **body** figure, in
#: centimetres, which is FMLV's `awning_length_mm` once multiplied by ten (10830 on the
#: Rio Grande, which is what FMLV holds).
_AWNING = re.compile(r"Awning perimeter dimensions \(body/chassis, cm\)\s+(\d+)/(\d+)")

#: `Number of axles 1`. FMLV's `twin_axle` is a proposal rather than a finding, and this
#: is the one place the document states it outright.
_AXLES = re.compile(r"Number of axles\s+(\d+)")

#: The maximum, deliberately read so a run can say it was seen and rejected. Recording it
#: would put an uprated chassis in `mtplm_kilograms` on five of eight products.
_MAX_LADEN = re.compile(r"Maximum technical permissable laden mass \(MTPLM\) \( kg \)\s+(\d+)")

#: `Max loading weight (kg) with All Inclusive Pack weight deducted 161` — Adria's own
#: payload, which is not FMLV's. Read only to name it in the provenance.
_MAX_LOADING = re.compile(r"Max loading weight \(kg\)[^\n]*?\s(\d+)\s*$", re.MULTILINE)

#: `CZ. Adria Vehicle Information` followed by `TBA` — an announced layout whose technical
#: data has not been published. Both Action configurations are in this state.
_TBA = re.compile(r"Adria Vehicle Information\s*\n\s*TBA", re.IGNORECASE)

#: A market code on the end of a layout label: `391 LH GB`. FMLV's own Action rows carry
#: no such suffix, so it is not part of the model.
_MARKET_SUFFIX = re.compile(r"\s+(?:GB|UK|DE|FR|IT|NL|PT|ES)$")


@dataclass
class _Figures:
    """One caravan's published figures, keyed by the FMLV field they land in."""

    values: dict[str, int]
    awning_length_mm: int | None = None
    axles: int | None = None
    maximum_laden_kilograms: int | None = None
    published_max_loading: int | None = None
    technical_data_is_tba: bool = False

    def get(self, field_name: str) -> int | None:
        return self.values.get(field_name)


def parse_caravan_pdf(text: str) -> _Figures:
    """Every figure FMLV holds, out of one technical-data PDF."""
    values: dict[str, int] = {}
    for field_name, pattern in _SPEC_PATTERNS.items():
        match = pattern.search(text)
        if match is not None:
            values[field_name] = int(match.group(1))

    awning = _AWNING.search(text)
    axles = _AXLES.search(text)
    maximum = _MAX_LADEN.search(text)
    loading = _MAX_LOADING.search(text)
    return _Figures(
        values=values,
        # The body figure, in cm; the chassis figure after the slash is not FMLV's.
        awning_length_mm=int(awning.group(1)) * 10 if awning else None,
        axles=int(axles.group(1)) if axles else None,
        maximum_laden_kilograms=int(maximum.group(1)) if maximum else None,
        published_max_loading=int(loading.group(1)) if loading else None,
        technical_data_is_tba=bool(_TBA.search(text)),
    )


def model_name(product: LivewireProduct) -> str | None:
    """FMLV's model for one configuration: the layout label, without its market code.

    The trim is deliberately not used. It is wrong on the Altea 622 DK Avon, which
    carries its sibling's `Altea 622 DP Dart`, and unspaced on the 612 DL Tyne. The
    layout label matches FMLV exactly on all eight matched products.
    """
    if not product.layout_label:
        return None
    return _MARKET_SUFFIX.sub("", product.layout_label.strip()) or None


#: Micros are named by their maker as well as being light — the settled two-part test.
#: Applied rather than asserted, because `wingamm_caravan.py` found the brand that breaks
#: the usual answer by asserting it.
MICRO_MAX_MTPLM_KG = 1250


def body_type_for(text: str, mtplm: int | None) -> tuple[CaravanBodyType, str]:
    """`type_rigid` unless Adria name the caravan a micro *and* it is light enough."""
    named = re.search(r"\bmicro[- ]?caravan\b|\bmini[- ]caravan\b", text, re.IGNORECASE)
    if named and mtplm is not None and mtplm <= MICRO_MAX_MTPLM_KG:
        return CaravanBodyType.MICRO, (
            f"a micro: Adria call it {named.group(0)!r} and its permissible mass is "
            f"{mtplm}kg, at or under the {MICRO_MAX_MTPLM_KG}kg the rule allows"
        )
    reason = "rigid-bodied"
    if named:
        reason += (
            f", despite Adria calling it {named.group(0)!r}: at {mtplm}kg it is over the "
            f"{MICRO_MAX_MTPLM_KG}kg a micro may weigh"
        )
    elif mtplm is not None and mtplm <= MICRO_MAX_MTPLM_KG:
        reason += (
            f": at {mtplm}kg it is light enough for a micro, but Adria never call it one "
            f"and the rule needs both"
        )
    else:
        reason += ": Adria name no micro in this range and it is far over the weight"
    return CaravanBodyType.RIGID, reason


@dataclass
class AdriaCaravan:
    """One configuration, as read from the Livewire payload and its PDF."""

    config: RangeConfig
    product: LivewireProduct
    figures: _Figures
    pdf_url: str

    @property
    def model(self) -> str | None:
        return model_name(self.product)

    @property
    def label(self) -> str:
        return f"{self.config.fmlv_range} {self.model or self.product.product_id}"

    @property
    def derived_payload_kilograms(self) -> int | None:
        """MTPLM-min minus MRO, which is what FMLV holds — not Adria's own figure."""
        mtplm = self.figures.get("mtplm_kilograms")
        mro = self.figures.get("mro_kilograms")
        if mtplm is None or mro is None:
            return None
        return mtplm - mro


def _reconciles(product: AdriaCaravan, text: str) -> tuple[bool, str]:
    """The two checks that drop a product, unchanged in spirit from `adria.py`.

    This adapter reaches its numbers by *constructing* a PDF URL out of an id, so the
    failure to defend against is a whole spec sheet belonging to the wrong caravan —
    plausible, internally consistent and invisible downstream. Hence the title check.
    """
    if product.figures.technical_data_is_tba:
        return False, (
            "its technical data reads TBA: the PDF's 'Dimensions and weights' section "
            "states no length, width, height or mass at all. Announced, not yet specified"
        )

    describes = pdf_describes_layout(text, product.product.layout_label)
    if describes is False:
        return False, (
            f"the PDF titles itself {pdf_title(text)!r}, which does not name "
            f"{product.product.layout_label!r} — the constructed URL fetched another "
            f"caravan's document"
        )

    mtplm = product.figures.get("mtplm_kilograms")
    mro = product.figures.get("mro_kilograms")
    if mro is None:
        return False, "its PDF states no mass in running order"

    # **A missing MTPLM-min does not drop the caravan.** The Alpina Colorado publishes a
    # maximum and no minimum, alone among the ten, and dropping it would report a live
    # FMLV row as disappeared when it is plainly on the site under a new layout code.
    # The mass and the payload are simply not proposed; everything else still is.
    if mtplm is None:
        return True, (
            f"NO PERMISSIBLE MASS PROPOSED: this PDF states a 'Maximum technical "
            f"permissable laden mass' of {product.figures.maximum_laden_kilograms}kg but "
            f"no 'MTPLM-min', alone among Adria's caravans. Every other layout publishes "
            f"both and FMLV records the minimum, so taking the maximum here would record "
            f"an uprated chassis as the base vehicle. The PDF titles itself "
            f"{pdf_title(text)!r}, which confirms it is this caravan's document"
        )

    if mro >= mtplm:
        return False, (
            f"a mass in running order of {mro}kg at or above the {mtplm}kg permissible "
            f"mass, which would make the payload zero or negative"
        )
    return True, (
        f"MTPLM-min {mtplm}kg minus mass in running order {mro}kg, with the PDF titled "
        f"{pdf_title(text)!r} confirming it is this caravan's document"
    )


#: How each habitation reading is introduced. Findings for a person to type in.
_FEATURE_NOTES: dict[str, str] = {
    "heating": "the heating in the PDF's fitted-equipment list",
    "refrigeration": "the refrigeration in the PDF's fitted-equipment list",
    "microwave": "a microwave in the PDF's fitted-equipment list",
    "shower_toilet_separated": "the washroom as the fitted-equipment list describes it",
}


def build_extracted(
    product: AdriaCaravan, *, basis: str, fitted: Iterable[str] = ()
) -> ExtractedCaravan:
    """One configuration as a `Caravan` plus the provenance a reviewer sees beside it."""
    features = habitation.features_from(fitted)
    # Dropped for the same reason as on every other caravan adapter: the bed rows give
    # dimensions without saying whether a bed is built in or made up from the seating.
    features.pop("bed_types", None)

    figures = product.figures
    mtplm = figures.get("mtplm_kilograms")
    body_type, body_reason = body_type_for("", mtplm)

    caravan = Caravan(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.config.fmlv_range,
        model=product.model,
        berths=product.product.berths,
        rrp_pounds=product.product.price_pounds,
        mtplm_kilograms=mtplm,
        mro_kilograms=figures.get("mro_kilograms"),
        personal_effects_payload_kilograms=product.derived_payload_kilograms,
        shipping_length_mm=figures.get("shipping_length_mm"),
        exterior_body_length_mm=figures.get("exterior_body_length_mm"),
        internal_length_mm=figures.get("internal_length_mm"),
        awning_length_mm=figures.awning_length_mm,
        overall_width_mm=figures.get("overall_width_mm"),
        height_mm=figures.get("height_mm"),
        headroom_mm=figures.get("headroom_mm"),
        twin_axle=figures.axles == 2 if figures.axles is not None else False,
        body_type=body_type,
    )
    for name, feature in features.items():
        setattr(caravan, name, feature.value)

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=product.pdf_url, snippet=f"{product.label} — {snippet}"
        )

    renamed = RENAMED_MODELS.get((product.config.fmlv_range, product.model or ""))
    moved = (
        f'; FMLV holds this layout as "{renamed[1]}" and Adria have changed the code, '
        f"which the identical mass in running order and total length confirm is the same "
        f"caravan"
        if renamed
        else ""
    )
    record(
        "manufacturer_range",
        f'range "{product.config.fmlv_range}" from the /caravans index — accept with the '
        f"model, they are one name",
    )
    record(
        "model",
        f'model "{product.model}" from the configuration\'s own layout label{moved} — '
        f"accept with the range, they are one name",
    )

    if product.product.berths is not None:
        record("berths", f"{product.product.berths} berths, from the layout selector")
    if product.product.price_pounds is not None:
        record(
            "rrp_pounds",
            f"{product.product.price_string or product.product.price_pounds} for this "
            f"configuration, from the site's own layout selector",
        )
    if mtplm is not None:
        record(
            "mtplm_kilograms",
            f"Minimal technically permissible laden mass (MTPLM-min, kg): {mtplm}. "
            f"NOT the 'Maximum technical permissable laden mass' of "
            f"{figures.maximum_laden_kilograms}kg on the line above it, which is the "
            f"uprated chassis — FMLV records the base vehicle. {basis}",
        )
    if figures.get("mro_kilograms") is not None:
        record(
            "mro_kilograms",
            f"Mass in running order (MIRO-min, kg): {figures.get('mro_kilograms')}",
        )
    if product.derived_payload_kilograms is not None:
        record(
            "personal_effects_payload_kilograms",
            f"{product.derived_payload_kilograms}kg, derived as MTPLM-min minus the mass "
            f"in running order. Adria's own 'Max loading weight' of "
            f"{figures.published_max_loading}kg is NOT this figure — it further deducts "
            f"the All Inclusive Pack — and is deliberately not recorded",
        )
        record(
            "optional_equipment_payload_kilograms",
            "Adria publish no payload split, so there is no separate optional-equipment "
            "payload. Left blank so the two payload columns sum to the derived figure",
        )
    if figures.get("shipping_length_mm") is not None:
        record(
            "shipping_length_mm",
            f"Total length (including tow bar) (mm): {figures.get('shipping_length_mm')} "
            f"— NOT the body length of {figures.get('exterior_body_length_mm')}mm on the "
            f"line below it",
        )
    for field_name, label in (
        ("exterior_body_length_mm", "Body length (mm)"),
        ("internal_length_mm", "Internal length (mm)"),
        ("overall_width_mm", "Total width (mm)"),
        ("headroom_mm", "Internal height (mm)"),
    ):
        if figures.get(field_name) is not None:
            record(field_name, f"{label}: {figures.get(field_name)}")
    if figures.get("height_mm") is not None:
        record(
            "height_mm",
            f"Total height (mm): {figures.get('height_mm')}. NOTE this is about 150mm "
            f"BELOW what FMLV holds, and it is so on every Adria caravan — Adria publish "
            f"no second height and no note of what theirs includes. Recorded on the "
            f"requester's ruling (21 September 2026) that the manufacturer's own "
            f"published figure is what the consumer sees",
        )
    if figures.awning_length_mm is not None:
        record(
            "awning_length_mm",
            f"Awning perimeter dimensions (body/chassis, cm): "
            f"{figures.awning_length_mm // 10} for the body, so "
            f"{figures.awning_length_mm}mm — the chassis figure after the slash is not "
            f"this",
        )
    if figures.axles is not None:
        record("twin_axle", f"Number of axles: {figures.axles}")
    record("body_type", body_reason)

    for name, feature in features.items():
        note = feature.note or _FEATURE_NOTES.get(name, "from the fitted-equipment list")
        record(name, f"{note}: {feature.snippet}")

    return ExtractedCaravan(caravan=caravan, provenance=provenance)


def collect(
    http: Fetcher,
    browser: BrowserFetcher,
    snapshot_dir: Path,  # noqa: ARG001
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedCaravan]:
    """Every Adria caravan configuration across the four ranges."""
    results: list[ExtractedCaravan] = []
    tba: list[str] = []
    seen = 0
    seen_models: dict[tuple[str, str], str] = {}

    for range_path, range_label in ranges:
        config = range_config(range_path, range_label)
        range_url = f"{BASE_URL}/{config.path}"
        on_progress(f"[{config.label}] loading range page...")
        _page, captured = browser.fetch_with_capture(
            range_url, capture_url_contains=_LIVEWIRE_UPDATE_MARKER, scroll=True
        )
        if not captured:
            on_progress(
                f"[{config.label}] WARNING: the range page made no "
                f"{_LIVEWIRE_UPDATE_MARKER} call, so it yielded no configurations — the "
                f"layout selector may have moved, or never scrolled into view"
            )

        for response in captured:
            products = parse_livewire_products(response.file_path.read_bytes())
            on_progress(f"[{config.label}] {len(products)} configuration(s) found")
            for index, live in enumerate(products, start=1):
                label = " / ".join(
                    part for part in (live.layout_label, live.trim_label) if part
                ) or live.product_id
                prefix = f"[{config.label}] ({index}/{len(products)}) {label}"
                seen += 1

                pdf_url = technical_data_pdf_url(live)
                if pdf_url is None:
                    on_progress(f"{prefix} — SKIPPED: no configuratorURL to build a PDF URL")
                    continue
                result = http.fetch(pdf_url)
                if result.status_code != 200:
                    on_progress(f"{prefix} — SKIPPED: PDF returned {result.status_code}")
                    continue

                text = extract_text(result.file_path).text
                caravan = AdriaCaravan(
                    config=config,
                    product=live,
                    figures=parse_caravan_pdf(text),
                    pdf_url=pdf_url,
                )
                reconciles, reason = _reconciles(caravan, text)
                if not reconciles:
                    if caravan.figures.technical_data_is_tba:
                        tba.append(f"{live.trim_label or caravan.model}")
                    on_progress(f"{prefix} — DROPPED: {reason}")
                    continue

                key = (config.fmlv_range, caravan.model or "")
                if key in seen_models:
                    on_progress(
                        f"{prefix} — DROPPED: its layout label gives the model "
                        f"{caravan.model!r}, which {seen_models[key]} already claimed in "
                        f"this range. Two configurations cannot share one FMLV identity, "
                        f"and the trim labels are not reliable enough to tell them apart"
                    )
                    continue
                seen_models[key] = label

                fitted, _not_fitted = fitted_equipment(text)
                results.append(build_extracted(caravan, basis=reason, fitted=fitted))
                on_progress(
                    f"{prefix} — read: {caravan.figures.get('shipping_length_mm')}mm, "
                    f"{caravan.figures.get('mtplm_kilograms')}kg, "
                    f"{live.berths} berths, "
                    f"payload {caravan.derived_payload_kilograms}kg"
                )

    if tba:
        on_progress(
            f"ANNOUNCED BUT NOT YET SPECIFIED, so not collected: {', '.join(tba)}. Their "
            f"PDFs carry a 'Dimensions and weights' section holding nothing but an option "
            f"pack weight, followed by 'Adria Vehicle Information: TBA'. If FMLV's own "
            f"Action layout disappears this run, this is why — the range has moved on and "
            f"its replacement has no published figures yet, so it is not a withdrawal."
        )
    on_progress(
        "HEIGHT IS PROPOSED THOUGH IT DISAGREES WITH FMLV EVERYWHERE, by about 150mm on "
        "every Adria caravan. Adria publish no second height and no note of what theirs "
        "includes, so the offset is unexplained rather than understood. Recorded on the "
        "requester's ruling that the manufacturer's own published figure is what the "
        "consumer sees. Worth a reviewer's eye, once."
    )
    on_progress(
        "PAYLOAD IS DERIVED as MTPLM-min minus the mass in running order, which is what "
        "FMLV holds. Adria's own 'Max loading weight' further deducts the All Inclusive "
        "Pack and is never recorded. Note also that the permissible mass read is the "
        "MINIMUM, not the maximum on the line above it: FMLV records the base vehicle, "
        "and the two differ on five of the eight readable layouts."
    )

    if seen != EXPECTED_LAYOUTS:
        on_progress(
            f"expected {EXPECTED_LAYOUTS} configurations across the four ranges and the "
            f"site offered {seen} — check whether the range has changed"
        )
    on_progress(f"collected {len(results)} Adria caravan(s)")
    return results
