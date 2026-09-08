"""The Erwin Hymer Group configurator API, shared by every EHG brand.

Eriba, Dethleffs, Bürstner and Carado all run the same configurator, and it is backed by a
**public, unauthenticated JSON API** — no browser, no session, no key. That matters because
the pages themselves render nothing server-side: search a configurator page's HTML for a
layout or a drawing and you find neither, which is how three separate surveys concluded
that data was unavailable when it was one request away.

Three endpoints, named by the page's own JavaScript bundle:

```
/gb/configurator/<slug>                     -> data-config (base64) -> seriesId
/configurator-api/brand/<brandKey>/series   -> every series the brand has ever had
/configurator-api/series/<seriesId>/models  -> its layouts, drawings and technical data
```

**Always filter the series list by `modelYear`.** A brand's list is cumulative — Bürstner's
carries 44 series going back to 2023, with the same name reused across years (`Signature
SFT` appears for 2026 and 2027). Taking a name without a year is how you collect last
season's roster.

**Never take the series name as the range name.** The API is the German product structure
and the UK sites rename freely: Bürstner's UK `B66 644 TD` is filed under a series called
`Lyseo TD`, and its `B66 644 C` under `Eliseo C`. Join on the layout, not the series.

This module deliberately stops at the platform: it reads what the API says and leaves every
question of *interpretation* — which FMLV range this is, what a `bedType` of `french-bed`
should record — to the brand's own adapter, where the evidence for those decisions lives.
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass, field
from typing import Any

#: The base64 JSON a configurator page hands its own JavaScript. It carries the `seriesId`
#: the API is keyed on, so the id is **read rather than hardcoded** and a range the brand
#: renumbers cannot silently serve another range's layouts.
_CONFIG_BLOB = re.compile(r"data-config='([A-Za-z0-9+/=]+)'")

#: One brand's whole series history. `brandKey` comes from the same `data-config` blob.
BRAND_SERIES_PATH = "/configurator-api/brand/{brand_key}/series"

#: One series' layouts. The endpoint the bundle names `fetchModels`.
SERIES_MODELS_PATH = "/configurator-api/series/{series_id}/models"

#: Pins the UK edition, so prices come in sterling and marketing names in English.
UK_QUERY = "locale=en_GB&country=GB&currencyCode=GBP"


@dataclass(frozen=True)
class EhgSeries:
    """One series in a brand's catalogue — a range in the German product structure."""

    id: int
    name: str
    model_year: int | None = None


@dataclass(frozen=True)
class EhgModel:
    """One layout as the configurator describes it.

    `technical_data` is handed over raw, because what is worth reading out of it differs by
    body type: a caravan adapter wants `technicalDataBed` and the two masses, a motorhome
    adapter wants seats and a payload. `technical_value` unwraps a scalar entry.
    """

    id: int
    marketing_name: str
    floorplan_url: str | None = None
    technical_data: dict[str, Any] = field(default_factory=dict)


def parse_config_blob(page_html: str) -> dict[str, Any]:
    """The configurator page's own parameters, or `{}` if they cannot be read."""
    blob = _CONFIG_BLOB.search(page_html)
    if blob is None:
        return {}
    try:
        config = json.loads(base64.b64decode(blob.group(1)))
    except (ValueError, TypeError):
        return {}
    return config if isinstance(config, dict) else {}


def parse_series_id(page_html: str) -> int | None:
    """The `seriesId` a configurator page names, or `None`."""
    series_id = parse_config_blob(page_html).get("seriesId")
    return series_id if isinstance(series_id, int) else None


def parse_brand_key(page_html: str) -> str | None:
    """The `brandKey` the brand-level endpoint is keyed on, or `None`."""
    brand_key = parse_config_blob(page_html).get("brandKey")
    return brand_key if isinstance(brand_key, str) and brand_key else None


def parse_series_index(payload: str, *, model_year: int | None = None) -> list[EhgSeries]:
    """Every series in a brand's catalogue, optionally just one model year's.

    Pass `model_year`: without it you get the brand's whole history, and the duplicate
    names across years are indistinguishable — see the module docstring.
    """
    try:
        entries = json.loads(payload)
    except ValueError:
        return []
    if not isinstance(entries, list):
        return []

    series: list[EhgSeries] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        identifier, name = entry.get("id"), entry.get("name")
        if not isinstance(identifier, int) or not isinstance(name, str) or not name.strip():
            continue
        year = entry.get("modelYear")
        year = int(year) if str(year).isdigit() else None
        if model_year is not None and year != model_year:
            continue
        series.append(EhgSeries(id=identifier, name=" ".join(name.split()), model_year=year))
    return series


def latest_model_year(payload: str) -> int | None:
    """The newest model year the brand publishes, for filtering the index by."""
    years = [series.model_year for series in parse_series_index(payload) if series.model_year]
    return max(years) if years else None


def parse_models(payload: str) -> list[EhgModel]:
    """Every layout in one series' response."""
    try:
        entries = json.loads(payload)
    except ValueError:
        return []
    if not isinstance(entries, list):
        return []

    models: list[EhgModel] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        identifier = entry.get("id")
        name = " ".join(str(entry.get("marketingName") or "").split())
        if not isinstance(identifier, int) or not name:
            continue
        # The vertical rendering where there is one: it is the drawing a reviewer reads a
        # layout off, rather than the wide strip used as a page banner.
        plan = entry.get("layoutImageVertical") or entry.get("layoutImage") or {}
        source = plan.get("overlayImageSource") if isinstance(plan, dict) else None
        technical = entry.get("technicalData")
        models.append(
            EhgModel(
                id=identifier,
                marketing_name=name,
                floorplan_url=source if isinstance(source, str) and source else None,
                technical_data=technical if isinstance(technical, dict) else {},
            )
        )
    return models


def technical_value(technical_data: dict[str, Any], key: str) -> str | None:
    """One scalar `technicalData` entry, which the API wraps as `{key, value, unit, …}`."""
    entry = technical_data.get(key)
    if not isinstance(entry, dict):
        return None
    value = entry.get("value")
    return str(value) if value not in (None, "") else None
