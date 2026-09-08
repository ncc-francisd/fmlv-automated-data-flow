"""The Erwin Hymer Group configurator API, shared by Eriba, Dethleffs, Bürstner and Carado.

Fixtures were saved from Bürstner's live API on 9 September 2026 and trimmed to the fields
the module reads. The series index is deliberately kept **with its duplicates**: `Signature
SFT` and `Lyseo TD` each appear for more than one model year, and that is the trap the
module exists to make unmissable.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from src.adapters import ehg_configurator as ehg

FIXTURES = Path(__file__).parent / "fixtures"
SERIES_INDEX = "ehg_brand_series_index.json"
SERIES_MODELS = "ehg_series_models_lyseo_td.json"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _page(**config: object) -> str:
    """A configurator page's mount point, which is all the module reads off the HTML."""
    blob = base64.b64encode(json.dumps(config).encode()).decode()
    return f"""<div id="configurator" data-config='{blob}'></div>"""


# --------------------------------------------------------------------------- #
# The page's own parameters
# --------------------------------------------------------------------------- #


def test_the_series_id_and_brand_key_are_read_from_the_page() -> None:
    """Read, never hardcoded, so a renumbered series cannot serve another's layouts."""
    page = _page(seriesId=3827417, brandKey="buerstner", seriesName="Signature SFT")

    assert ehg.parse_series_id(page) == 3827417
    assert ehg.parse_brand_key(page) == "buerstner"


@pytest.mark.parametrize(
    "page",
    [
        "<div id='configurator'></div>",
        """<div data-config='not base64 at all'></div>""",
    ],
)
def test_an_unreadable_page_yields_nothing(page: str) -> None:
    assert ehg.parse_series_id(page) is None
    assert ehg.parse_brand_key(page) is None
    assert ehg.parse_config_blob(page) == {}


def test_a_non_integer_series_id_is_refused() -> None:
    """It goes into a URL path, so a string is not one to trust."""
    assert ehg.parse_series_id(_page(seriesId="3827417")) is None


# --------------------------------------------------------------------------- #
# The series index, and the model year that makes it usable
# --------------------------------------------------------------------------- #


def test_the_series_index_is_cumulative_and_reuses_its_names() -> None:
    """Which is why nothing may take a series by name alone.

    Bürstner's live index carries 44 series back to 2023, and `Signature SFT` is two of
    them. Taking the name without the year collects last season's roster.
    """
    series = ehg.parse_series_index(_read(SERIES_INDEX))

    signatures = [entry for entry in series if entry.name == "Signature SFT"]
    assert len(signatures) > 1
    assert len({entry.model_year for entry in signatures}) == len(signatures)


def test_filtering_by_model_year_leaves_one_of_each() -> None:
    payload = _read(SERIES_INDEX)

    current = ehg.parse_series_index(payload, model_year=ehg.latest_model_year(payload))

    assert [entry.name for entry in current].count("Signature SFT") == 1
    assert all(entry.model_year == ehg.latest_model_year(payload) for entry in current)


def test_the_latest_model_year_is_the_newest_published() -> None:
    assert ehg.latest_model_year(_read(SERIES_INDEX)) == 2027


@pytest.mark.parametrize("payload", ["", "not json", "{}", '[{"id": 1}]', '[{"name": "X"}]'])
def test_an_unusable_index_yields_no_series(payload: str) -> None:
    assert ehg.parse_series_index(payload) == []
    assert ehg.latest_model_year(payload) is None


# --------------------------------------------------------------------------- #
# The layouts
# --------------------------------------------------------------------------- #


def test_every_layout_carries_a_name_and_a_drawing() -> None:
    models = ehg.parse_models(_read(SERIES_MODELS))

    assert len(models) == 5
    assert all(model.floorplan_url for model in models)
    assert {model.marketing_name for model in models} == {
        "Lyseo TD 594",
        "Lyseo TD 644 G",
        "Lyseo TD 684 G",
        "Lyseo TD 690 G",
        "Lyseo TD 744",
    }


def test_the_series_name_is_not_the_uk_range() -> None:
    """The API is the German product structure; UK sites rename freely.

    `Lyseo TD 644 G` is Bürstner UK's `B66 644 TD`, and its own drawing says so. Anything
    joining on the series name would fail on five of eight B66 layouts.
    """
    models = {model.marketing_name: model for model in ehg.parse_models(_read(SERIES_MODELS))}

    assert models["Lyseo TD 644 G"].floorplan_url is not None
    assert "b66-644-td" in models["Lyseo TD 644 G"].floorplan_url


def test_technical_data_is_handed_over_raw_and_unwrapped_on_demand() -> None:
    """Each entry is `{key, value, unit, unitLong}`, and what matters differs by body type."""
    model = next(
        m for m in ehg.parse_models(_read(SERIES_MODELS)) if m.marketing_name == "Lyseo TD 594"
    )

    assert ehg.technical_value(model.technical_data, "sleepingBerths") is not None
    assert ehg.technical_value(model.technical_data, "no_such_row") is None


@pytest.mark.parametrize("payload", ["", "not json", "{}", '[{"id": 1}]'])
def test_an_unusable_models_response_yields_no_layouts(payload: str) -> None:
    assert ehg.parse_models(payload) == []
