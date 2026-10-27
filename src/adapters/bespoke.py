"""Bespoke (bespokeleisure.co.uk) — campervans converted in Ballymena.

See `docs/adapters/bespoke.md` for the survey. **Rebuilt 27 October 2026**, because Bespoke
replaced both their website and their range.

## What changed, and why the old adapter had to go

The old one read three model pages and a price leaflet. All three pages now return **404**
and the leaflet with them, and the failure was silent: the adapter fell back on hardcoded
variant names, collected nine products with no price, and reported *"9 collected, expected
9"* — a passing count check over a roster that no longer exists. That is the fault
`docs/adapters/README.md` warns about, and it is why nothing here is hardcoded except the
identity split.

The range changed at the same time. FMLV holds **eight** products on three base vehicles;
Bespoke now sell **five**, all Volkswagen — the Ford Transit Custom is gone entirely.

## The source is WordPress, and it is structured

The new site exposes its own content types, which is a far better source than the prose it
replaced:

```
/wp-json/wp/v2/bl_range   → VW Transporter, VW Crafter
/wp-json/wp/v2/bl_model   → Explore 4, Explore 4 Hybrid, Explore 5, Explore 5 Hybrid,
                            Crafter Edition
```

Each model carries an `acf` block with `model_berths`, `model_travel_seats`,
`model_toilet`, `model_shower`, `model_hot_water`, the equipment prose, and paths to its
day and night floorplans and its exterior photograph.

## Four fields are published nowhere, and three of them were never published

**No price.** The leaflet was the only price source and it is gone. The only £ figures on
the site are `bl_stock_item` listings — individual vehicles with a registration, which is a
fact about one van and not about the model.

**No mass of any kind.** Bespoke have never published one: not a payload, a gross vehicle
weight, a kerb weight, an MiRO or an MTPLM, on any page or in any document. FMLV's figures
came from elsewhere and carry through untouched.

**No dimension.** This one *is* a loss. The old pages stated `Explore Length 5.05m` and a
height of `1.98m`, which is where FMLV's 5050 and 1980 came from. The new site states no
vehicle length, width or height anywhere — the ACF fields for them exist and are empty, and
the only measurements left in the copy are bed sizes and an awning.

**No body type.** It needs a height, and there is none. The requester reads it off the
photographs instead (27 October 2026), so `collect` points him at them rather than guessing
— and the pop-top that would otherwise settle it is ambiguous, appearing under an
`Optional` column on one model and in marketing copy on another.

## The identity split is this adapter's own choice, and a reviewer should confirm it

All five are **new** products, so there is no FMLV row whose strings to follow — the rule
to let the export decide cannot apply where the export holds nothing. `IDENTITY` therefore
carries a deliberate reading of Bespoke's own naming, and the run says so.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..fetch.http import Fetcher
from ..product_model.model import Motorhome
from . import habitation
from .base import ExtractedMotorhome, Provenance, floorplan_provenance, fmlv_base_vehicle

__all__ = [
    "BASE_URL",
    "EXPECTED_PRODUCTS",
    "IDENTITY",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "MODELS_URL",
    "RANGES_URL",
    "SEAT_CEILING",
    "BespokeModel",
    "build_extracted",
    "collect",
    "equipment_lines",
    "identity_for",
    "parse_models",
    "parse_ranges",
    "seats_from",
]

BASE_URL = "https://bespokeleisure.co.uk"

#: NCC id 68. The supplier list and the manufacturer list both say `Bespoke NI`; the
#: display name is the shorter `Bespoke`, which is how the site brands itself.
MANUFACTURER = "Bespoke NI"
MANUFACTURER_DISPLAY_NAME = "Bespoke"

#: WordPress serves both content types without authentication. `per_page` is set high
#: enough that a growing range still arrives in one response.
MODELS_URL = f"{BASE_URL}/wp-json/wp/v2/bl_model?per_page=100"
RANGES_URL = f"{BASE_URL}/wp-json/wp/v2/bl_range?per_page=100"

#: Five models as of 27 October 2026. Compared against what the API returns so a model
#: added or withdrawn is announced rather than passing unnoticed — which is exactly how
#: the previous adapter went wrong.
EXPECTED_PRODUCTS = 5

#: `Up to 4` on the Crafter Edition. A ceiling rather than a fitment, so it is **not
#: recorded** — the Bürstner rule, which is in `docs/adapters/README.md`: a "permitted" or
#: "up to" seat count is a type-approval maximum and FMLV holds the belted seats fitted as
#: standard. FMLV already files the two Edition rows as 2 seats and 4.
SEAT_CEILING = ("up to", "maximum", "max")

#: How each model's name splits into FMLV's range and model columns.
#:
#: **This adapter's own choice, deliberately.** All five are new products, so the settled
#: rule that the export decides the identity strings has nothing to decide from. The split
#: follows Bespoke's own naming — an `Explore` family with a variant, and the Crafter
#: Edition as a single name carried twice because Nova will not take a blank.
#:
#: A reviewer should confirm it on the first run; changing it later is a rename, which is
#: the one edit that can corrupt a product's identity.
IDENTITY: dict[str, tuple[str, str]] = {
    "Explore 4": ("Explore", "4"),
    "Explore 4 Hybrid": ("Explore", "4 Hybrid"),
    "Explore 5": ("Explore", "5"),
    "Explore 5 Hybrid": ("Explore", "5 Hybrid"),
    "Crafter Edition": ("Crafter Edition", "Crafter Edition"),
}

#: The ACF fields carrying equipment prose. `model_spec_conversion_interior` is the
#: conversion's own kit and `model_spec_base_interior` the base vehicle's; `model_benefits`
#: is the headline list. Each is a newline-separated block.
_EQUIPMENT_FIELDS = (
    "model_benefits",
    "model_spec_conversion_interior",
    "model_spec_conversion_exterior",
    "model_spec_conversion_other",
    "model_spec_base_interior",
)

#: An appliance that heats **water**, not the van. Bespoke's Crafter Edition lists a "10L
#: electric water heating system", which `habitation`'s "is the heating unclear" check
#: matches because it contains the word — and reporting that as heating of an undetermined
#: kind sends a reviewer hunting for a system that is not there.
_WATER_HEATER = re.compile(r"\bwater heat(?:er|ing)\b|\bboiler\b|\bhot water\b", re.I)

#: How each habitation reading is introduced. Findings for a person to type in.
_FEATURE_NOTES: dict[str, str] = {
    "heating": "the heating in the model's own specification",
    "refrigeration": "the refrigeration in the model's own specification",
    "microwave": "a microwave in the model's own specification",
    "shower_toilet_separated": "the washroom as the specification describes it",
}


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def parse_ranges(payload: str) -> dict[int, str]:
    """`{id: name}` for the site's own ranges — `VW Transporter`, `VW Crafter`.

    These name the **base vehicle**, not an FMLV range, which is why they are used to
    derive `base_vehicle_manufacturer` and never `manufacturer_range`.
    """
    try:
        entries = json.loads(payload)
    except ValueError:
        return {}
    if not isinstance(entries, list):
        return {}
    found: dict[int, str] = {}
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("id"), int):
            found[entry["id"]] = _text((entry.get("title") or {}).get("rendered")).strip()
    return found


@dataclass
class BespokeModel:
    """One model as the site's own API describes it."""

    name: str
    slug: str
    url: str
    range_name: str = ""
    berths: int | None = None
    seats_raw: str = ""
    floorplan_url: str | None = None
    hero_url: str | None = None
    equipment: list[str] = field(default_factory=list)
    toilet: str = ""
    shower: str = ""

    @property
    def identity(self) -> tuple[str, str]:
        return identity_for(self.name)

    @property
    def label(self) -> str:
        return self.name


def identity_for(name: str) -> tuple[str, str]:
    """`(range, model)` as FMLV will file this product.

    A name this adapter has not seen falls back on the single-name convention, carrying
    the name twice — so a sixth model still gets a usable identity and the run's count
    check is what flags it.
    """
    if name in IDENTITY:
        return IDENTITY[name]
    return name, name


def _absolute(path: Any) -> str | None:
    text = _text(path).strip()
    if not text:
        return None
    return text if text.startswith("http") else f"{BASE_URL}{text}"


def equipment_lines(acf: dict[str, Any]) -> list[str]:
    """Every specification line a model publishes, as one list.

    The blocks are newline-separated prose. `habitation.usable_lines` drops anything that
    marks itself as a priced extra, which is the only defence available — Bespoke publish
    no standard-against-optional split that can be read structurally.
    """
    lines: list[str] = []
    for key in _EQUIPMENT_FIELDS:
        block = _text(acf.get(key))
        lines.extend(line.strip() for line in block.splitlines() if line.strip())
    return habitation.usable_lines(lines)


def parse_models(payload: str, ranges: dict[int, str]) -> list[BespokeModel]:
    """Every model in the API response, in the order it lists them."""
    try:
        entries = json.loads(payload)
    except ValueError:
        return []
    if not isinstance(entries, list):
        return []

    models: list[BespokeModel] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = _text((entry.get("title") or {}).get("rendered")).strip()
        if not name:
            continue
        acf: dict[str, Any] = entry.get("acf") or {}
        berths = acf.get("model_berths")
        models.append(
            BespokeModel(
                name=name,
                slug=_text(entry.get("slug")),
                url=_text(entry.get("link")) or f"{BASE_URL}/models/{entry.get('slug')}/",
                range_name=ranges.get(acf.get("model_range"), ""),
                berths=berths if isinstance(berths, int) else None,
                seats_raw=str(acf.get("model_travel_seats") or "").strip(),
                floorplan_url=_absolute(acf.get("model_floorplan_path")),
                hero_url=_absolute(acf.get("model_hero_path")),
                equipment=equipment_lines(acf),
                toilet=_text(acf.get("model_toilet")),
                shower=_text(acf.get("model_shower")),
            )
        )
    return models


def seats_from(raw: str) -> tuple[int | None, str]:
    """The belted seats fitted as standard, where the site states a plain figure.

    **`Up to 4` is not recorded.** It is a ceiling, and the settled rule is that a
    "permitted" or "up to" seat count is a type-approval maximum rather than a fitment
    claim — FMLV holds the belts fitted as standard, and already files Bespoke's two
    Edition rows as 2 seats and 4.
    """
    text = raw.strip()
    if not text:
        return None, "the model states no seat count"
    if any(word in text.lower() for word in SEAT_CEILING):
        return None, (
            f"the model states {text!r}, which is a ceiling rather than the belts fitted "
            f"as standard — not recorded, per the settled rule"
        )
    digits = "".join(character for character in text if character.isdigit())
    if not digits:
        return None, f"the model states {text!r}, which is not a seat count"
    return int(digits), f"{int(digits)} travel seats, from the model's own specification"


def _reconciles(model: BespokeModel) -> tuple[bool, str]:
    """**Structural, because Bespoke publish no figure that checks another.**

    No mass, no dimension and no price means there is no arithmetic anywhere — not even
    the two-of-three the weaker adapters here manage. What can be verified is that the
    API returned a model with a name and a range behind it, which is what the previous
    adapter failed to notice it had stopped getting.
    """
    if not model.name:
        return False, "the API returned a model with no name"
    if not model.range_name:
        return False, (
            f"{model.name} names no range, so its base vehicle cannot be derived and "
            f"nothing identifies which van it is built on"
        )
    return True, (
        f"{model.name} on the {model.range_name}, from the site's own model API"
    )


def build_extracted(model: BespokeModel, *, basis: str) -> ExtractedMotorhome:
    """One Bespoke campervan, with provenance on everything it proposes."""
    features = habitation.features_from(model.equipment)
    features.pop("bed_types", None)

    manufacturer_range, model_name = model.identity
    seats, seats_basis = seats_from(model.seats_raw)
    base_vehicle = (
        fmlv_base_vehicle("VW") if "volkswagen" in model.range_name.lower()
        or model.range_name.upper().startswith("VW") else None
    )
    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=manufacturer_range,
        model=model_name,
        base_vehicle_manufacturer=base_vehicle,
        berths=model.berths,
        mh_passenger_seats_inc_driver=seats,
        # **Deliberately absent, all of them.** Bespoke publish no price, no mass of any
        # kind and no vehicle dimension — see the module docstring. FMLV's own figures
        # carry through untouched, and the body type is read off the photographs by a
        # person because there is no height to apply the rule to.
        rrp_pounds=None,
        mro_kilograms=None,
        mtplm_kilograms=None,
        mh_payload_kilograms=None,
        mh_length_mm=None,
        mh_width_mm=None,
        mh_height_mm=None,
        body_type=None,
    )
    for name, feature in features.items():
        setattr(motorhome, name, feature.value)

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=model.url, snippet=f"{model.label} — {snippet}"
        )

    record(
        "manufacturer_range",
        f'range "{manufacturer_range}", split from Bespoke\'s own name {model.name!r}. '
        f"THIS PRODUCT IS NEW TO FMLV, so the split is this adapter's reading rather than "
        f"the export's — worth confirming now, because changing it later is a rename",
    )
    record("model", f'model "{model_name}", the variant within {manufacturer_range}')
    if model.berths is not None:
        record("berths", f"{model.berths} berths, from the model's own specification")
    if seats is not None:
        record("mh_passenger_seats_inc_driver", seats_basis)
    if base_vehicle is not None:
        record(
            "base_vehicle_manufacturer",
            f"{base_vehicle}, from the site's own range for this model: "
            f"{model.range_name!r}",
        )
    for name, feature in features.items():
        provenance[name] = Provenance(
            source_url=model.url,
            snippet=(
                f"{model.label} — {feature.note or _FEATURE_NOTES.get(name, name)}: "
                f"{feature.snippet!r}"
            ),
        )

    # Two pointers, at two different pictures. The floorplan answers where things are; the
    # exterior photograph is what the requester reads the body type off, there being no
    # height published to apply the high-top rule to.
    if model.floorplan_url:
        provenance.update(
            floorplan_provenance(
                motorhome,
                model.floorplan_url,
                model.label,
                drawing="the day and night floorplans on the model's own page",
            )
        )
    if model.hero_url and motorhome.body_type is None:
        # **Not through `floorplan_provenance`.** That helper answers the five positional
        # questions it knows, and the body type is not one of them — teaching it this one
        # would put a pointer on every other adapter's products too. The need is Bespoke's
        # alone, because they are the only brand here publishing no height at all.
        provenance["body_type"] = Provenance(
            source_url=model.hero_url,
            snippet=(
                f"{model.label} — read the body type off the exterior photograph. Bespoke "
                f"publish no height, so the high-top rule cannot be applied, and the "
                f"pop-top that would otherwise settle it is listed under an 'Optional' "
                f"column on one model and in marketing copy on another"
            ),
        )
    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


def _notes(model: BespokeModel) -> Iterable[str]:
    """What the model published that is reported rather than recorded."""
    _seats, seats_basis = seats_from(model.seats_raw)
    if _seats is None and model.seats_raw:
        yield f"[{model.label}] SEATS NOT PROPOSED: {seats_basis}"
    if model.toilet or model.shower:
        yield (
            f"[{model.label}] washroom, for the habitation fields: toilet "
            f"{model.toilet or 'not stated'!r}, shower {model.shower or 'not stated'!r}"
        )
    features = habitation.features_from(model.equipment)
    if "heating" not in features:
        unclear = habitation.heating_is_unclear(model.equipment)
        if unclear is None:
            yield f"[{model.label}] NO HEATING IS MENTIONED at all in its specification"
        elif _WATER_HEATER.search(unclear):
            # A water heater is not space heating, and calling it heating of an
            # undetermined kind sends a reviewer looking for a system that is not there.
            yield (
                f"[{model.label}] NO SPACE HEATING IS STATED. The only line mentioning "
                f"heating is {unclear!r}, which heats water"
            )
        else:
            # **The vehicle has heating; what it has not got is a named kind.** Saying
            # "none" here would be worse than saying nothing — the Explores list a
            # "Propex Gas Fired Heating System", which is a real heater whose type the
            # shared vocabulary does not settle.
            yield (
                f"[{model.label}] HEATING IS FITTED BUT ITS KIND IS NOT NAMED: "
                f"{unclear!r}. Nothing is proposed — blown air against wet central has to "
                f"be entered by hand"
            )


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 — the API is plain JSON
    snapshot_dir: Path,  # noqa: ARG001 — `http` already snapshots into it
    *,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every current Bespoke campervan, from the site's own model API."""
    ranges_response = http.fetch(RANGES_URL)
    if ranges_response.status_code != 200:
        msg = f"{RANGES_URL} returned {ranges_response.status_code}"
        raise RuntimeError(msg)
    ranges = parse_ranges(
        ranges_response.file_path.read_text(encoding="utf-8", errors="replace")
    )

    models_response = http.fetch(MODELS_URL)
    if models_response.status_code != 200:
        msg = f"{MODELS_URL} returned {models_response.status_code}"
        raise RuntimeError(msg)
    models = parse_models(
        models_response.file_path.read_text(encoding="utf-8", errors="replace"), ranges
    )
    if not models:
        msg = (
            f"{MODELS_URL} returned 200 and no models — the API's shape has changed "
            f"rather than Bespoke having stopped making campervans"
        )
        raise RuntimeError(msg)
    on_progress(
        f"the site's API lists {len(models)} model(s) across {len(ranges)} range(s): "
        f"{', '.join(sorted(ranges.values()))}"
    )

    results: list[ExtractedMotorhome] = []
    for model in models:
        reconciles, basis = _reconciles(model)
        if not reconciles:
            on_progress(f"[{model.label}] DROPPED: {basis}")
            continue
        results.append(build_extracted(model, basis=basis))
        manufacturer_range, model_name = model.identity
        on_progress(
            f"[{model.label}] read as {manufacturer_range} / {model_name}: "
            f"{model.berths} berths, {model.seats_raw or 'no'} seats, on the "
            f"{model.range_name}"
        )
        for note in _notes(model):
            on_progress(note)

    on_progress(
        "NO PRICE, NO MASS AND NO DIMENSION IS PROPOSED. Bespoke publish none of them: "
        "the price leaflet the old adapter read is gone and the only figures on the site "
        "are stock listings for individual vans; no mass of any kind has ever been "
        "published; and the dimension fields on the new site are empty, where the old "
        "pages stated a length and a height. FMLV's own figures carry through untouched."
    )
    on_progress(
        "NO BODY TYPE IS PROPOSED. It needs a height and there is none, so each product "
        "carries a pointer at its own exterior photograph for a person to read it off."
    )
    on_progress(
        "THE RANGE HAS CHANGED, not just the website. These five are all Volkswagen; the "
        "Ford Transit Custom that three of FMLV's rows are built on is gone from the "
        "line-up, so those will be reported as disappeared."
    )
    if len(results) != EXPECTED_PRODUCTS:
        on_progress(
            f"expected {EXPECTED_PRODUCTS} models and collected {len(results)} — check "
            f"whether Bespoke have added or withdrawn one"
        )
    on_progress(f"collected {len(results)} Bespoke campervan(s)")
    return results
