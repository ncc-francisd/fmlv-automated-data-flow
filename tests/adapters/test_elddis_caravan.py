"""Elddis touring caravans, from the configurator API.

The fixture is the live `Riviera` models response of 26 November 2026, trimmed to the
fields the module reads. It is kept **with the unpublished flags on**, because that is the
state the range is actually in and the adapter's behaviour there is the point.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.adapters import elddis_caravan
from src.adapters.elddis_caravan import (
    BED_TYPES_BY_CONFIGURATOR_NAME,
    DEFAULT_RANGES,
    EXPECTED_LAYOUTS,
    MANUFACTURER,
    VEHICLE_CLASS,
    ElddisCaravanLayout,
    build_extracted,
    parse_layouts,
    sleeping_area_from,
)
from src.product_model.enums import BedType, CaravanBodyType, CaravanSleepingArea
from src.vehicle_class import VehicleClass

FIXTURES = Path(__file__).parent / "fixtures"
MODELS = "elddis_caravan_riviera_models.json"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def riviera() -> list[ElddisCaravanLayout]:
    return parse_layouts(_fixture(MODELS), "Riviera")


def _by_model(layouts: list[ElddisCaravanLayout], model: str) -> ElddisCaravanLayout:
    return next(layout for layout in layouts if layout.model == model)


# --- registration ---------------------------------------------------------------------


def test_this_is_the_caravan_half_of_an_existing_manufacturer() -> None:
    """Same registry row as `elddis.py`, different product area.

    The pair is what keeps the two apart: one catalogue carries motorhomes, campervans
    and caravans, and `vehicleType` is the only field that separates them.
    """
    assert VEHICLE_CLASS is VehicleClass.CARAVAN
    assert MANUFACTURER == "Elddis (EHG UK)"
    assert DEFAULT_RANGES == (("Riviera", "Riviera"),)


# --- the roster -----------------------------------------------------------------------


def test_every_layout_is_read(riviera: list[ElddisCaravanLayout]) -> None:
    assert len(riviera) == EXPECTED_LAYOUTS
    assert [layout.model for layout in riviera] == [
        "580 FL",
        "590 SDW",
        "600 FDB",
        "640 LS",
        "660 IU",
    ]


def test_the_series_name_is_stripped_from_the_model() -> None:
    """`Riviera 580 FL` in series `Riviera` is the model `580 FL`."""
    assert elddis_caravan.model_name("Riviera 580 FL", "Riviera") == "580 FL"
    assert elddis_caravan.model_name("Elddis Riviera 580 FL", "Riviera") == "580 FL"
    assert elddis_caravan.model_name("580 FL", "Riviera") == "580 FL"


def test_a_layout_with_no_name_is_skipped_rather_than_guessed_at() -> None:
    payload = json.dumps([{"id": 1, "marketingName": ""}, {"id": 2, "marketingName": "  "}])
    assert parse_layouts(payload, "Riviera") == []


@pytest.mark.parametrize("payload", ["", "not json", "{}", '"a string"'])
def test_an_unusable_payload_yields_nothing(payload: str) -> None:
    assert parse_layouts(payload, "Riviera") == []


# --- the figures ----------------------------------------------------------------------


def test_the_masses_and_dimensions_are_read(riviera: list[ElddisCaravanLayout]) -> None:
    layout = _by_model(riviera, "580 FL")

    assert layout.berths == 4
    assert layout.mtplm_kilograms == 1800
    assert layout.mro_kilograms == 1265
    assert layout.payload_kilograms == 535
    assert layout.shipping_length_mm == 7170
    assert layout.overall_width_mm == 2300
    assert layout.height_mm == 2650
    assert layout.headroom_mm == 1980


def test_the_api_publishes_lengths_in_centimetres(riviera: list[ElddisCaravanLayout]) -> None:
    """`717` is 7170mm, not 717mm. The one conversion the whole module turns on."""
    raw = json.loads(_fixture(MODELS))[0]
    assert raw["technicalData"]["lengthOverall"]["value"] == "717"
    assert raw["technicalData"]["lengthOverall"]["unit"] == "cm"
    assert _by_model(riviera, "580 FL").shipping_length_mm == 7170


def test_the_overall_length_is_the_shipping_length_not_the_internal_one() -> None:
    """**The trap `docs/adapters/README.md` names for caravan adapters.**

    A caravan has four lengths and they are not interchangeable. Mapping `lengthOverall`
    to `internal_length_mm` would overstate every caravan's habitable space by well over a
    metre while looking plausible on any one product. Settled against Eriba — the same
    API, whose caravans FMLV already holds — where it matches FMLV's own shipping length
    on 17 of 18 layouts.
    """
    extracted = build_extracted(
        ElddisCaravanLayout(
            manufacturer_range="Riviera",
            model="580 FL",
            mtplm_kilograms=1800,
            mro_kilograms=1265,
            shipping_length_mm=7170,
        )
    )

    assert extracted.caravan.shipping_length_mm == 7170
    assert extracted.caravan.internal_length_mm is None
    assert extracted.caravan.exterior_body_length_mm is None
    assert "SHIPPING length" in extracted.provenance["shipping_length_mm"].snippet


def test_the_payload_is_derived_because_elddis_publish_none(
    riviera: list[ElddisCaravanLayout],
) -> None:
    extracted = build_extracted(_by_model(riviera, "660 IU"))

    assert extracted.caravan.personal_effects_payload_kilograms == 620
    snippet = extracted.provenance["personal_effects_payload_kilograms"].snippet
    assert "2000 − 1380 = 620kg" in snippet
    assert "publish no payload row" in snippet


def test_the_optional_equipment_allowance_is_not_recorded_as_the_payload(
    riviera: list[ElddisCaravanLayout],
) -> None:
    """438kg against a 535kg payload on the 580 FL — different quantities.

    Recording the allowance would understate what the caravan can carry, and it is the
    kind of plausible wrong number nothing downstream would question.
    """
    layout = _by_model(riviera, "580 FL")

    assert layout.optional_equipment_allowance_kilograms == 438
    extracted = build_extracted(layout)

    assert extracted.caravan.personal_effects_payload_kilograms == 535
    assert "438kg allowance" in extracted.provenance[
        "personal_effects_payload_kilograms"
    ].snippet


# --- the self-check -------------------------------------------------------------------


def test_all_five_layouts_reconcile(riviera: list[ElddisCaravanLayout]) -> None:
    for layout in riviera:
        ok, basis = elddis_caravan._reconciles(layout)
        assert ok, f"{layout.label}: {basis}"


def test_a_running_order_above_the_maximum_is_refused() -> None:
    ok, basis = elddis_caravan._reconciles(
        ElddisCaravanLayout(
            manufacturer_range="Riviera", model="X", mtplm_kilograms=1800, mro_kilograms=1900
        )
    )
    assert not ok
    assert "zero or negative" in basis


def test_an_implausible_payload_is_refused() -> None:
    """A mass read out of the wrong field lands here."""
    ok, basis = elddis_caravan._reconciles(
        ElddisCaravanLayout(
            manufacturer_range="Riviera", model="X", mtplm_kilograms=1800, mro_kilograms=100
        )
    )
    assert not ok
    assert "credibly carry" in basis


def test_a_missing_mass_is_refused_rather_than_assumed() -> None:
    ok, _ = elddis_caravan._reconciles(
        ElddisCaravanLayout(manufacturer_range="Riviera", model="X", mtplm_kilograms=1800)
    )
    assert not ok


# --- what is deliberately not set -----------------------------------------------------


def test_twin_axle_is_not_proposed_because_the_api_states_no_axle_count(
    riviera: list[ElddisCaravanLayout],
) -> None:
    """**The difference between "we did not look" and "the answer is no".**

    `twin_axle` is a `bool` defaulting to `False`, so letting it through would assert a
    single axle on a 2000kg caravan this module knows nothing about. `diff.compare` walks
    the provenance rather than the product, so recording none keeps it out of the diff.
    """
    extracted = build_extracted(_by_model(riviera, "660 IU"))

    assert "twin_axle" not in extracted.provenance


def test_a_caravan_is_rigid_on_the_settled_rule_not_on_what_elddis_say(
    riviera: list[ElddisCaravanLayout],
) -> None:
    """Elddis publish `bodyType: null` for every caravan layout."""
    raw = json.loads(_fixture(MODELS))[0]
    assert raw["bodyType"] is None

    extracted = build_extracted(_by_model(riviera, "580 FL"))

    assert extracted.caravan.body_type is CaravanBodyType.RIGID
    assert "WALLS fold or rise" in extracted.provenance["body_type"].snippet


def test_no_price_is_invented(riviera: list[ElddisCaravanLayout]) -> None:
    for layout in riviera:
        extracted = build_extracted(layout)
        assert extracted.caravan.rrp_pounds is None
        assert "rrp_pounds" not in extracted.provenance


# --- not yet published ----------------------------------------------------------------


def test_every_layout_is_flagged_unpublished(riviera: list[ElddisCaravanLayout]) -> None:
    """Which is why the range is on social media and not on elddis.co.uk."""
    assert [layout.published for layout in riviera] == [False] * EXPECTED_LAYOUTS


def test_an_unpublished_layout_is_still_collected() -> None:
    """The requester's instruction, 26 November 2026: enter them now, activate later.

    FMLV's staging state is an inactive product, not an absent one, so the right place
    for an unlaunched model is a row somebody has created and not yet switched on.
    """
    said: list[str] = []
    layouts = parse_layouts(_fixture(MODELS), "Riviera")
    kept = [layout for layout in layouts if elddis_caravan._reconciles(layout)[0]]

    assert len(kept) == EXPECTED_LAYOUTS
    assert "INACTIVE" in elddis_caravan.UNPUBLISHED_WARNING
    assert "availableForWebsite" in elddis_caravan.UNPUBLISHED_WARNING
    said.append(elddis_caravan.UNPUBLISHED_WARNING)
    assert said


# --- findings -------------------------------------------------------------------------


def test_bed_types_come_from_the_configurators_own_bed_table(
    riviera: list[ElddisCaravanLayout],
) -> None:
    extracted = build_extracted(_by_model(riviera, "600 FDB"))

    assert set(extracted.caravan.bed_types) == {
        BedType.FIXED,  # front double
        BedType.MAKE_UP,  # middle seating group
        BedType.FIXED_BUNKS,  # rear bunks
    }
    assert "double-bed front" in extracted.provenance["bed_types"].snippet


def test_an_optional_bed_is_not_a_standard_one(riviera: list[ElddisCaravanLayout]) -> None:
    """The 640 LS offers a `single-to-double-bed` infill, `isOptional: yes`.

    Counting it would make a twin-single layout read as having a fixed double, the same
    way counting an optional berth would overstate how many it sleeps.
    """
    layout = _by_model(riviera, "640 LS")
    optional = [
        values for values in layout.beds if str(values.get("isOptional")).lower() == "yes"
    ]
    assert optional, "fixture no longer carries an optional bed"

    extracted = build_extracted(layout)

    assert BedType.FIXED_SEPARATE in extracted.caravan.bed_types
    assert BedType.FIXED not in extracted.caravan.bed_types


def test_a_middle_bed_is_not_an_end_of_the_caravan(
    riviera: list[ElddisCaravanLayout],
) -> None:
    """The 590 SDW sleeps at the front, plus a mid-lounge seating group.

    `sleeping_area` is only ever front, rear or both, and a mid lounge is neither end —
    reading it as `both` would put a bed at the back of a caravan that has none.
    """
    layout = _by_model(riviera, "590 SDW")
    ends = {str(values.get("installedIn")) for values in layout.beds}
    assert "middle" in ends and "rear" not in ends

    assert sleeping_area_from(layout) is CaravanSleepingArea.FRONT


def test_beds_at_both_ends_read_as_both(riviera: list[ElddisCaravanLayout]) -> None:
    assert sleeping_area_from(_by_model(riviera, "580 FL")) is CaravanSleepingArea.BOTH


def test_a_layout_with_no_beds_has_no_sleeping_area() -> None:
    assert sleeping_area_from(ElddisCaravanLayout(manufacturer_range="R", model="X")) is None


def test_an_unknown_bed_type_is_named_rather_than_guessed() -> None:
    """A wrong bed type is worse than a gap, and this is a finding typed in by hand."""
    layout = ElddisCaravanLayout(
        manufacturer_range="Riviera",
        model="X",
        beds=[{"bedType": "hammock", "isOptional": "no", "installedIn": "rear"}],
    )

    beds, _quotes = elddis_caravan.beds_from(layout)

    assert beds == []
    assert elddis_caravan.unknown_bed_types(layout) == ["hammock"]


def test_the_bed_vocabulary_agrees_with_eribas_where_they_overlap() -> None:
    """Both read the same API. A silent disagreement would be two readings of one word."""
    from src.adapters.eriba_caravan import BED_TYPES_BY_CONFIGURATOR_NAME as eriba

    shared = set(eriba) & set(BED_TYPES_BY_CONFIGURATOR_NAME)

    assert shared
    for name in shared:
        assert BED_TYPES_BY_CONFIGURATOR_NAME[name] is eriba[name], name
