"""SUN LIVING, Adria Mobil's sub-brand, on Adria's own machinery.

The site is Adria's: the same Laravel+Livewire range pages, the same scroll-triggered
`/livewire/update` call, the same per-configuration technical-data PDF. So
`parse_livewire_products`, `technical_data_pdf_url`, `parse_technical_data_pdf`,
`pdf_title`, `pdf_describes_layout` and `parse_base_vehicle_manufacturer` are all
imported unchanged, and this module is mostly a roster and a naming rule.

**One change was needed in `adria.py` to make it work at all.**
`technical_data_pdf_url` derived the market and period from each product's
`configuratorURL` but hardcoded the host as `configure.adria-mobil.com`. SUN LIVING's
configurator is at `configure.sun-living.com`, so every one of the ten PDFs returned 404
— and the C 70DL, whose price is also `£0.00`, looked convincingly like a model still in
transition with no technical data published. It has a full document. The host now comes
from the same URL as everything else.

## The trim belongs in the model only when it says something

The V Series trims are `StdF RHD` and `StdF RHD TentTop`, and the motorhome trims are all
`SL_Ford_RHD`. Only one of those carries information: the **TentTop**, an elevating tent
roof that adds two berths and £4,000, and which Sun Living sell as a second configuration
of the same layout.

So the model is the layout label plus whatever the trim says beyond the standard
right-hand-drive boilerplate — `V 55SP` for one and `V 55SP TentTop` for the other. The
requester chose this on 22 September 2026, the alternative being two products FMLV could
never tell apart.

**FMLV holds both already**, as two rows both called `V 55SP` differing only in their
berth count. That pair has to be separated by hand before a run, because
`_dedupe_baseline` collapses identically-named rows *before* matching: left alone it
discards the 2-berth row entirely and hands the 4-berth row's id to the base caravan.
See `docs/adapters/sun_living.md`.

## The weights are the base ones

Every PDF states `Mass in running order (MIRO-min, kg) 3002 (WITHOUT ALL INC' PACK)`, and
that without-the-pack figure is what FMLV holds — the S 72DC's 3002 matches to the
kilogram. The requester's ruling, 22 September 2026: *"use the weights quoted which say
excluding the supplementary all-inclusive pack … we're doing the base level"*. Payload is
`MTPLM − MiRO`, which reconciles with FMLV on seven of its eight live rows.

## Two configurations publish no price

The C 70DL publishes `£0.00` and the S 75SL publishes nothing at all. **A zero is not a
price**, so neither is recorded and FMLV's own figures stand; inventing one is what the
settled "never invent a POA" rule forbids.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..fetch.browser import BrowserFetcher
from ..fetch.http import Fetcher
from ..fetch.pdf import extract_text
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from . import habitation
from .adria import (
    _LIVEWIRE_UPDATE_MARKER,
    LivewireProduct,
    RangeConfig,
    cross_source_disagreements,
    fitted_equipment,
    parse_base_vehicle_manufacturer,
    parse_livewire_products,
    parse_technical_data_pdf,
    pdf_describes_layout,
    pdf_title,
    technical_data_pdf_url,
)
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

__all__ = [
    "BASE_URL",
    "DEFAULT_RANGES",
    "EXPECTED_LAYOUTS",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "RANGES",
    "SunLivingMotorhome",
    "body_type_for",
    "collect",
    "model_name",
    "range_config",
]

BASE_URL = "https://www.sun-living.co.uk"

#: Capitals in both, which is how the NCC list and the brand's own site spell it. Only
#: one candidate row exists, so unlike Weinsberg or Mink there is nothing to disambiguate.
MANUFACTURER = "SUN LIVING"
MANUFACTURER_DISPLAY_NAME = "SUN LIVING"

#: Four ranges: three motorhome series and the V Series campervans. Read off
#: `/motorhomes` and `/campervans`, which between them link exactly these.
RANGES: tuple[RangeConfig, ...] = (
    RangeConfig("motorhomes/a-series", "A Series", "A Series", model_includes_trim=False),
    RangeConfig("motorhomes/c-series", "C Series", "C Series", model_includes_trim=False),
    RangeConfig("motorhomes/s-series", "S Series", "S Series", model_includes_trim=False),
    RangeConfig("campervans/v-series", "V Series", "V Series", model_includes_trim=False),
)

DEFAULT_RANGES: tuple[tuple[str, str], ...] = tuple(
    (config.path, config.label) for config in RANGES
)

_RANGE_BY_LABEL: dict[str, RangeConfig] = {config.label: config for config in RANGES}

#: Ten configurations across the four ranges.
EXPECTED_LAYOUTS = 10

#: Trim tokens that describe the market and the base build rather than the vehicle:
#: `SL_Ford_RHD`, `StdF RHD`. Anything a trim says *beyond* these belongs in the model —
#: see `model_name`.
_BOILERPLATE_TRIM_TOKENS: frozenset[str] = frozenset(
    {"sl", "ford", "fiat", "rhd", "lhd", "stdf", "std", "gb", "uk"}
)

#: The body style each range is built as. **Derived per range rather than asserted as one
#: constant**, which is the `wingamm_caravan.py` lesson: a constant is right until it is
#: not, and the brand that breaks it does not announce itself.
#:
#: Every range is internally consistent in FMLV across live *and* archived rows — A Series
#: over-cab on all three, C and S Series low profile, V Series high top — and the
#: requester confirmed the A Series on 22 September 2026. The letters say the same thing:
#: A for alcove, S for semi-integrated, V for van.
_BODY_TYPE_BY_RANGE: dict[str, BodyType] = {
    "A Series": BodyType.COACH_BUILT_OVER_CAB_BED,
    "C Series": BodyType.COACH_BUILT_LOW_PROFILE,
    "S Series": BodyType.COACH_BUILT_LOW_PROFILE,
    "V Series": BodyType.CAMPERVAN_HIGH_TOP,
}

#: A trim word that means a bed in the roof. Only `TentTop` appears today, on the second
#: V 55SP configuration, and it is what takes that campervan from two berths to four.
_ROOF_BED = re.compile(r"tent\s*top|pop\s*top|elevating", re.IGNORECASE)


def body_type_for(range_name: str, model: str) -> tuple[BodyType | None, str]:
    """The body style, and why — derived, never asserted.

    **The V 55SP pair is the interesting case, and FMLV holds it the wrong way round.**
    Sun Living sell that layout twice, and the `TentTop` configuration is the one with the
    roof bed: its own name says so and it sleeps four where the base sleeps two. FMLV has
    `campervan_high_top` on the TentTop and `campervan_high_top_elevating_roof` on the
    base — the opposite — which is exactly what happens when two rows share a name and an
    edit lands on whichever one the editor happened to open. Until 22 September 2026 they
    were indistinguishable.

    So this proposes a swap on that pair, and says so rather than letting it look like two
    unrelated corrections.
    """
    base = _BODY_TYPE_BY_RANGE.get(range_name)
    if base is None:
        return None, f"no body style is known for the {range_name!r} range"
    if base is BodyType.CAMPERVAN_HIGH_TOP and _ROOF_BED.search(model):
        return BodyType.CAMPERVAN_HIGH_TOP_ELEVATING_ROOF, (
            f"a high-top campervan WITH A ROOF BED: this is the TentTop configuration, "
            f"which Sun Living sell alongside the plain one and which sleeps four where "
            f"the base sleeps two. NOTE FMLV currently holds this pair the other way "
            f"round — plain high top on the TentTop and elevating roof on the base — which "
            f"looks like a transposition from when the two rows shared one model name and "
            f"could not be told apart"
        )
    return base, (
        f"{base.value.removeprefix('type_').replace('_', ' ')}: every {range_name} row "
        f"FMLV holds is one, live and archived alike"
    )


def range_config(path: str, label: str) -> RangeConfig:
    """The `RangeConfig` for one `--range` selector, or a bare one if it is unknown."""
    known = _RANGE_BY_LABEL.get(label)
    if known is not None:
        return known
    return RangeConfig(path, label, label, model_includes_trim=False)


def model_name(product: LivewireProduct) -> str | None:
    """FMLV's model: the layout label, plus anything the trim adds beyond boilerplate.

    Sun Living sell the V 55SP twice, as `StdF RHD` and `StdF RHD TentTop`, and the
    second is an elevating tent roof that adds two berths and £4,000. Dropping the trim
    entirely would file two different campervans under one name, which is exactly the
    state FMLV is in and which `_dedupe_baseline` then makes invisible.

    So the boilerplate is removed and any remainder is kept: `StdF RHD` adds nothing and
    `StdF RHD TentTop` adds `TentTop`. A future `Elevating Roof` or `Sport` would carry
    across on its own without a code change, which is the point of subtracting the known
    words rather than listing the interesting ones.
    """
    if not product.layout_label:
        return None
    layout = product.layout_label.strip()
    extra = [
        token
        for token in re.split(r"[\s_]+", (product.trim_label or "").strip())
        if token and token.casefold() not in _BOILERPLATE_TRIM_TOKENS
    ]
    return f"{layout} {' '.join(extra)}" if extra else layout


@dataclass
class SunLivingMotorhome:
    """One configuration, as read from the Livewire payload and its PDF."""

    config: RangeConfig
    product: LivewireProduct
    model: str
    pdf_url: str
    specs: dict
    base_vehicle: str | None = None

    @property
    def label(self) -> str:
        return f"{self.config.fmlv_range} {self.model}"

    def value(self, field_name: str) -> int | None:
        match = self.specs.get(field_name)
        return match.value if match is not None else None

    @property
    def rrp_pounds(self) -> int | None:
        """The published price, treating `£0.00` as no price at all.

        The C 70DL publishes zero and the S 75SL publishes nothing. Recording a zero
        would wipe a real figure FMLV already holds.
        """
        price = self.product.price_pounds
        return price if price else None

    @property
    def derived_payload_kilograms(self) -> int | None:
        mtplm, mro = self.value("mtplm_kilograms"), self.value("mro_kilograms")
        if mtplm is None or mro is None:
            return None
        return mtplm - mro


def _reconciles(product: SunLivingMotorhome, text: str) -> tuple[bool, str]:
    """The two checks `adria.py` uses, and for the same reason.

    This adapter *constructs* a PDF URL out of an id, so the failure to defend against is
    a whole spec sheet belonging to the wrong vehicle — plausible, internally consistent
    and invisible downstream. Hence the title check.
    """
    if pdf_describes_layout(text, product.product.layout_label) is False:
        return False, (
            f"the PDF titles itself {pdf_title(text)!r}, which does not name "
            f"{product.product.layout_label!r} — the constructed URL fetched another "
            f"vehicle's document"
        )
    mtplm, mro = product.value("mtplm_kilograms"), product.value("mro_kilograms")
    missing = [
        name
        for name, value in (("max authorised weight", mtplm), ("mass in running order", mro))
        if value is None
    ]
    if missing:
        return False, f"its PDF states no {', '.join(missing)}"
    if mro >= mtplm:
        return False, (
            f"a mass in running order of {mro}kg at or above the {mtplm}kg authorised "
            f"weight, which would make the payload zero or negative"
        )
    return True, (
        f"max authorised weight {mtplm}kg minus mass in running order {mro}kg, with the "
        f"PDF titled {pdf_title(text)!r} confirming it is this vehicle's document"
    )


_FEATURE_NOTES: dict[str, str] = {
    "heating": "the heating in the PDF's fitted-equipment list",
    "refrigeration": "the refrigeration in the PDF's fitted-equipment list",
    "microwave": "a microwave in the PDF's fitted-equipment list",
    "shower_toilet_separated": "the washroom as the fitted-equipment list describes it",
}


def build_extracted(
    product: SunLivingMotorhome, *, basis: str, fitted: tuple[str, ...] = ()
) -> ExtractedMotorhome:
    """One configuration as a `Motorhome` plus the provenance a reviewer sees beside it."""
    features = habitation.features_from(fitted)
    features.pop("bed_types", None)

    body_type, body_reason = body_type_for(product.config.fmlv_range, product.model)

    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.config.fmlv_range,
        model=product.model,
        mh_length_mm=product.value("mh_length_mm"),
        mh_width_mm=product.value("mh_width_mm"),
        mh_height_mm=product.value("mh_height_mm"),
        berths=product.value("berths"),
        mh_passenger_seats_inc_driver=product.value("mh_passenger_seats_inc_driver"),
        mtplm_kilograms=product.value("mtplm_kilograms"),
        mro_kilograms=product.value("mro_kilograms"),
        mh_payload_kilograms=product.derived_payload_kilograms,
        base_vehicle_manufacturer=product.base_vehicle,
        rrp_pounds=product.rrp_pounds,
        body_type=body_type,
    )
    for name, feature in features.items():
        setattr(motorhome, name, feature.value)

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=product.pdf_url, snippet=f"{product.label} — {snippet}"
        )

    trim_note = (
        f'; the trim is "{product.product.trim_label}", and what it adds beyond the '
        f"right-hand-drive boilerplate is kept in the model because Sun Living sell this "
        f"layout twice and FMLV could not otherwise tell the two apart"
        if product.model != (product.product.layout_label or "").strip()
        else ""
    )
    record(
        "manufacturer_range",
        f'range "{product.config.fmlv_range}" from the site\'s own index — accept with '
        f"the model, they are one name",
    )
    record(
        "model",
        f'model "{product.model}", from the configuration\'s layout label{trim_note} — '
        f"accept with the range, they are one name",
    )

    for field_name in (
        "mh_length_mm",
        "mh_width_mm",
        "mh_height_mm",
        "berths",
        "mh_passenger_seats_inc_driver",
        "mtplm_kilograms",
    ):
        match = product.specs.get(field_name)
        if match is not None:
            record(field_name, match.snippet.strip())

    mro = product.specs.get("mro_kilograms")
    if mro is not None:
        record(
            "mro_kilograms",
            f"{mro.snippet.strip()} — the WITHOUT ALL INC' PACK figure, which is the base "
            f"vehicle and what FMLV already holds. {basis}",
        )
    if product.derived_payload_kilograms is not None:
        record(
            "mh_payload_kilograms",
            f"{product.derived_payload_kilograms}kg, derived as the max authorised weight "
            f"minus the mass in running order. Sun Living publish no payload of their own",
        )
    if product.base_vehicle is not None:
        record(
            "base_vehicle_manufacturer",
            f"{product.base_vehicle}, from the PDF's own chassis section heading",
        )
    if product.rrp_pounds is not None:
        record(
            "rrp_pounds",
            f"{product.product.price_string or product.rrp_pounds} for this configuration, "
            f"from the site's own layout selector",
        )
    if body_type is not None:
        record("body_type", body_reason)

    for name, feature in features.items():
        note = feature.note or _FEATURE_NOTES.get(name, "from the fitted-equipment list")
        record(name, f"{note}: {feature.snippet}")

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


def collect(
    http: Fetcher,
    browser: BrowserFetcher,
    snapshot_dir: Path,  # noqa: ARG001
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every Sun Living configuration across the four ranges."""
    results: list[ExtractedMotorhome] = []
    unpriced: list[str] = []

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
                f"{_LIVEWIRE_UPDATE_MARKER} call, so it yielded no configurations"
            )

        for response in captured:
            products = parse_livewire_products(response.file_path.read_bytes())
            on_progress(f"[{config.label}] {len(products)} configuration(s) found")
            for index, live in enumerate(products, start=1):
                label = " / ".join(
                    part for part in (live.layout_label, live.trim_label) if part
                ) or live.product_id
                prefix = f"[{config.label}] ({index}/{len(products)}) {label}"

                pdf_url = technical_data_pdf_url(live)
                if pdf_url is None:
                    on_progress(f"{prefix} — SKIPPED: no configuratorURL to build a PDF URL")
                    continue
                result = http.fetch(pdf_url)
                if result.status_code != 200:
                    on_progress(f"{prefix} — SKIPPED: PDF returned {result.status_code}")
                    continue

                text = extract_text(result.file_path).text
                model = model_name(live)
                if model is None:
                    on_progress(f"{prefix} — SKIPPED: the configuration has no layout label")
                    continue

                product = SunLivingMotorhome(
                    config=config,
                    product=live,
                    model=model,
                    pdf_url=pdf_url,
                    specs=parse_technical_data_pdf(text),
                    base_vehicle=fmlv_base_vehicle(parse_base_vehicle_manufacturer(text)),
                )
                reconciles, basis = _reconciles(product, text)
                if not reconciles:
                    on_progress(f"{prefix} — DROPPED: {basis}")
                    continue

                for note in cross_source_disagreements(live, product.specs):
                    on_progress(f"{prefix} — {note}")

                if product.rrp_pounds is None:
                    unpriced.append(product.label)

                fitted, _not_fitted = fitted_equipment(text)
                results.append(build_extracted(product, basis=basis, fitted=fitted))
                on_progress(
                    f"{prefix} — read as {product.label}: "
                    f"{product.value('mh_length_mm')}mm, "
                    f"{product.value('mtplm_kilograms')}kg, "
                    f"{product.value('berths')} berth, payload "
                    f"{product.derived_payload_kilograms}kg, "
                    + (f"GBP {product.rrp_pounds:,}" if product.rrp_pounds else "no price")
                )

    if unpriced:
        on_progress(
            f"NO PRICE PROPOSED for {', '.join(unpriced)}: the site publishes GBP0.00 for "
            f"one and nothing at all for the other. A ZERO IS NOT A PRICE, and recording "
            f"it would wipe a real figure FMLV already holds. Consistent with the range "
            f"being mid-transition, which the requester noticed independently."
        )
    on_progress(
        "THE MASSES ARE THE BASE ONES. Every PDF states the mass in running order as "
        "\"... (WITHOUT ALL INC' PACK)\", and that is the figure recorded, on the "
        "requester's ruling that the all-inclusive pack is a conversation for the "
        "customer and FMLV holds the base level. FMLV's own figures confirm it: the S "
        "72DC's 3002kg matches to the kilogram. Payload is the max authorised weight "
        "minus that mass."
    )
    on_progress(
        "THE TENTTOP IS IN THE MODEL NAME. Sun Living sell the V 55SP twice, as 'StdF "
        "RHD' and 'StdF RHD TentTop' — an elevating tent roof adding two berths and "
        "GBP4,000 — so the model carries whatever the trim says beyond the "
        "right-hand-drive boilerplate. FMLV holds both as 'V 55SP', and that pair must be "
        "separated by hand: _dedupe_baseline collapses identically-named rows BEFORE "
        "matching, so left alone it discards the 2-berth row and hands the 4-berth row's "
        "id to the base campervan."
    )

    if len(results) != EXPECTED_LAYOUTS:
        on_progress(
            f"expected {EXPECTED_LAYOUTS} configurations and collected {len(results)}"
        )
    on_progress(f"collected {len(results)} SUN LIVING configuration(s)")
    return results
