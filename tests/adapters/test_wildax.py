"""Wildax parsing, against the real range pages captured in `fixtures/`.

Pure parsing only — no network. The fixtures are the visible text of five range pages,
chosen because each carries a trap the others do not: Aurora has the Leisure trims and two
sleeping areas, Constellation has the `Rear Side` positions and the 3496 typo, Solaris has
the mass that looks copied, Equinox has the elevating roof, Altair has MAN and the
automatic-only price.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from src.adapters import wildax
from src.adapters.wildax import (
    EXPECTED_MODELS,
    MODELS,
    WildaxCampervan,
    _reconciles,
    base_vehicle_make,
    bathroom_layout_for,
    bed_types_for,
    body_type_for,
    build_extracted,
    kitchen_location_for,
    lounge_location_for,
    parse_price_list,
    resolve_price,
    sleeping_area_for,
    spec_panels,
    suspect_copied_figures,
    visible_lines,
)
from src.product_model.enums import (
    BathroomLayout,
    BedType,
    BodyType,
    KitchenLocation,
    LoungeLocation,
    SleepingArea,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _lines(slug: str) -> list[str]:
    return (FIXTURES / f"wildax_{slug}_text.txt").read_text(encoding="utf-8").splitlines()


@pytest.fixture
def aurora() -> list[str]:
    return _lines("aurora")


@pytest.fixture
def constellation() -> list[str]:
    return _lines("constellation")


@pytest.fixture
def solaris() -> list[str]:
    return _lines("solaris")


@pytest.fixture
def equinox() -> list[str]:
    return _lines("equinox")


@pytest.fixture
def altair() -> list[str]:
    return _lines("altair")


def _panel(lines: list[str], range_name: str, model: str):
    return next(p for p in spec_panels(lines) if p.identity == (range_name, model))


def _spec(range_name: str, model: str):
    return next(m for m in MODELS if (m.panel_range, m.panel_model) == (range_name, model))


# --- identity and roster --------------------------------------------------------------


def test_the_manufacturer_is_the_ncc_lists_spelling() -> None:
    """`Wildax` here and `WildAx Motorhomes` in the supplier list. Both are right."""
    assert wildax.MANUFACTURER == "Wildax"
    assert wildax.MANUFACTURER_DISPLAY_NAME == "Wildax"


def test_eighteen_models_across_eight_ranges() -> None:
    assert len(MODELS) == EXPECTED_MODELS == 18
    assert len({m.slug for m in MODELS}) == 8


def test_fmlv_range_names_are_preserved_as_held() -> None:
    """FMLV shouts some names and title-cases others, inconsistently. Re-casing 15 live
    rows is churn nobody asked for, so the roster carries FMLV's own strings."""
    held = {(m.panel_range, m.panel_model): (m.manufacturer_range, m.model) for m in MODELS}

    assert held[("Aurora", "Aurora")] == ("AURORA", "AURORA")
    assert held[("Solaris", "6m")] == ("SOLARIS", "SOLARIS")
    assert held[("Europa", "Europa")] == ("Europa", "EUROPA")
    assert held[("Constellation", "3")] == ("Constellation", "3")


def test_the_solaris_xl_is_its_own_range_in_fmlv() -> None:
    """Every other XL is a model inside its base range; this one is not, and pretending
    otherwise would propose a range change on a live row."""
    assert _spec("Solaris", "XL").manufacturer_range == "SOLARIS XL"
    assert _spec("Aurora", "XL").manufacturer_range == "AURORA"


# --- reading the page -----------------------------------------------------------------


def test_visible_lines_drops_scripts_and_splits_on_tags() -> None:
    """A value and its unit share one text node separated by a long whitespace run, and
    the `<script>` holds a decoy MTPLM that must never be read."""
    got = visible_lines(
        (FIXTURES / "wildax_panel_fragment.html").read_text(encoding="utf-8")
    )

    assert got == [
        "MTPLM",
        "3500 kg",
        "Bed",
        "type",
        "Lounge Conversion",
        "Est Payload",
    ]
    assert "9999" not in " ".join(got)


def test_every_model_on_a_page_gets_its_own_panel(constellation) -> None:
    assert [p.identity for p in spec_panels(constellation)] == [
        ("Constellation", "3"),
        ("Constellation", "4"),
        ("Constellation", "3 XL"),
        ("Constellation", "4 XL"),
    ]


def test_a_wrapped_two_word_label_is_still_matched(constellation) -> None:
    """`Bed type`, `Est Payload` and `Length (m)` all arrive as two lines because the
    markup wraps them. Matching one token at a time reads the label as the value."""
    panel = _panel(constellation, "Constellation", "3")

    assert panel.fields["Bed type"] == "Lounge Conversion"
    assert panel.fields["Est Payload"] == "460 kg"
    assert panel.fields["Length (m)"] == "6 m"


def test_the_equipment_stops_before_the_options(aurora) -> None:
    """An option is not a specification. `Optional Extras` sits inside the same block and
    would otherwise have the adapter assert an awning as standard fit."""
    panel = _panel(aurora, "Aurora", "Aurora")

    assert panel.equipment[0] == "General Features"
    assert "Optional Extras" not in panel.equipment
    assert any("solar panel" in line for line in panel.equipment)


# --- the price list -------------------------------------------------------------------


def test_the_price_list_is_in_every_page(constellation, altair) -> None:
    """It is an off-canvas nav panel, not a page of its own, so it costs no extra fetch."""
    assert len(parse_price_list(constellation)) == 38
    assert len(parse_price_list(altair)) == 38


def test_an_option_is_not_a_priced_vehicle(constellation) -> None:
    """The options list below the vehicles prints a name and a price but no chassis, which
    is what keeps `Awning 4m` from becoming a product."""
    labels = {row.label for row in parse_price_list(constellation)}

    assert "Awning 4m (XL vans)" not in labels
    assert "Wi-Fi 5G" not in labels


def test_gearbox_engine_and_paint_are_stripped_to_a_base_name(constellation) -> None:
    rows = {row.label: row.base_name for row in parse_price_list(constellation)}

    assert rows["Constellation XL Manual"] == "Constellation XL"
    assert rows["Meteor (Blue) 165 Auto"] == "Meteor"
    assert rows["Equinox 4x4 (Grey) 130 Manual"] == "Equinox 4x4"
    assert rows["Altair RS Auto"] == "Altair RS"


def test_the_cheapest_in_a_group_is_the_base_vehicle(constellation) -> None:
    """Manual over automatic, cheaper paint over dearer — the settled rule."""
    rows = parse_price_list(constellation)

    pounds, reason, _ = resolve_price(rows, _spec("Constellation", "3"))

    assert pounds == 73_495
    assert "Constellation Manual" in reason
    assert "base vehicle rather than the optioned one" in reason


def test_two_models_can_share_one_price_row(constellation) -> None:
    """The list knows `Constellation`, not `Constellation 3`. The 3 and the 4 differ by
    belt count, not money."""
    rows = parse_price_list(constellation)

    assert resolve_price(rows, _spec("Constellation", "3"))[0] == 73_495
    assert resolve_price(rows, _spec("Constellation", "4"))[0] == 73_495
    assert resolve_price(rows, _spec("Constellation", "3 XL"))[0] == 74_495


def test_the_meteor_takes_its_own_engines_price(constellation) -> None:
    """The cheapest Meteor is a 130 at GBP72,495, but FMLV holds the model as `165` and
    the requester chose the 165's price on 23 September 2026."""
    pounds, reason, _ = resolve_price(parse_price_list(constellation), _spec("Meteor", "165"))

    assert pounds == 73_995
    assert "the cheaper 130 is a different vehicle" in reason


def test_an_automatic_only_price_says_so(constellation) -> None:
    """Pulsar and both Altairs publish no manual price at all, although every one of their
    spec panels states a 6-speed manual."""
    _, reason, _ = resolve_price(parse_price_list(constellation), _spec("Pulsar", "Pulsar"))

    assert "AUTOMATIC price and the only one published" in reason


def test_a_model_with_no_price_row_proposes_nothing(constellation) -> None:
    orphan = dataclasses.replace(_spec("Pulsar", "Pulsar"), price_key="Nebula")

    pounds, reason, _ = resolve_price(parse_price_list(constellation), orphan)

    assert pounds is None
    assert "no price list row matches" in reason


# --- the self-check -------------------------------------------------------------------


def _product(lines: list[str], range_name: str, model: str) -> WildaxCampervan:
    return WildaxCampervan(
        spec=_spec(range_name, model),
        panel=_panel(lines, range_name, model),
        rrp_pounds=None,
        price_reason="",
    )


def test_a_coherent_panel_reconciles(constellation) -> None:
    ok, reason = _reconciles(_product(constellation, "Constellation", "4 XL"))

    assert ok is True
    assert "which is the payload WildAx publish" in reason


def test_the_constellation_3xl_mtplm_is_caught(constellation) -> None:
    """It publishes 3496 where its own payload and its 4 XL sibling both say 3500."""
    product = _product(constellation, "Constellation", "3 XL")
    ok, reason = _reconciles(product)

    assert product.mtplm_kilograms == 3496
    assert ok is False
    assert "a difference of 4kg" in reason


def test_a_failed_self_check_proposes_no_mass_at_all(constellation) -> None:
    """The point of the check. One of the three figures is a typo and nothing says which,
    so FMLV's own 3500/3058/442 stand rather than be overwritten by 3496/3058/438."""
    product = _product(constellation, "Constellation", "3 XL")

    extracted = build_extracted(
        dataclasses.replace(product, reconciles=False), payload_basis=""
    )

    assert "mtplm_kilograms" not in extracted.provenance
    assert "mro_kilograms" not in extracted.provenance
    assert "mh_payload_kilograms" not in extracted.provenance
    # **The values have to go too.** The pipeline derives payload from whatever MTPLM and
    # MRO the product carries, so dropping only the provenance still proposed 442 -> 438
    # off the back of the 3496 typo.
    assert extracted.motorhome.mtplm_kilograms is None
    assert extracted.motorhome.mro_kilograms is None
    assert extracted.motorhome.mh_payload_kilograms is None


def test_a_passing_self_check_proposes_all_three(constellation) -> None:
    product = _product(constellation, "Constellation", "4 XL")

    extracted = build_extracted(product, payload_basis="")

    assert extracted.motorhome.mtplm_kilograms == 3500
    assert extracted.motorhome.mh_payload_kilograms == 442
    assert "mh_payload_kilograms" in extracted.provenance


def test_the_payload_is_derived_not_read(constellation) -> None:
    """The settled rule. WildAx's own figure is only ever the check."""
    product = _product(constellation, "Constellation", "4 XL")

    assert product.derived_payload_kilograms == 3500 - 3058


# --- the copied mass, which the self-check cannot see ---------------------------------


def test_an_xl_weighing_exactly_what_the_short_one_does_is_flagged(solaris) -> None:
    """The Solaris XL publishes the 6m's 3040 although it is 370mm longer, and 3500 less
    3040 is the 460 WildAx print — so the figures are consistent and wrong together.
    FMLV holds 3134. Only the sibling comparison shows it."""
    pairs = [
        (_spec("Solaris", model), _product(solaris, "Solaris", model))
        for model in ("6m", "XL")
    ]

    suspect = suspect_copied_figures(pairs)

    assert len(suspect) == 1
    assert "3040kg" in suspect[0]
    assert "5990mm to 6360mm" in suspect[0]


def test_an_xl_no_longer_than_its_base_is_flagged(constellation) -> None:
    """The real case is the Europa, whose base model publishes the XL's 6.36m. Built here
    from the Constellation fixture by giving the 3 the 3 XL's length, because the name is
    the evidence: an XL that is not longer is not an XL."""
    base = _product(constellation, "Constellation", "3")
    base.panel.fields["Length (m)"] = "6.36 m"
    pairs = [
        (_spec("Constellation", "3"), base),
        (_spec("Constellation", "3 XL"), _product(constellation, "Constellation", "3 XL")),
    ]

    suspect = suspect_copied_figures(pairs)

    assert any("an XL that is not longer is not an XL" in line for line in suspect)


def test_sharing_a_wheelbase_is_not_reported(altair) -> None:
    """**The Globecar lesson.** The Altair RS and RL are one 6840mm van with two
    interiors, so they share a length and differ by 145kg entirely legitimately. Treating
    that as a copied cell was the false positive the first run threw."""
    pairs = [
        (_spec("Altair", model), _product(altair, "Altair", model)) for model in ("RS", "RL")
    ]

    assert suspect_copied_figures(pairs) == []


def test_models_of_the_same_length_and_mass_are_not_flagged(constellation) -> None:
    """Constellation 3 and 4 share both legitimately — they differ by a seatbelt.
    Flagging them would bury the Solaris in noise."""
    pairs = [
        (_spec("Constellation", model), _product(constellation, "Constellation", model))
        for model in ("3", "4")
    ]

    assert suspect_copied_figures(pairs) == []


# --- the base vehicle -----------------------------------------------------------------


def test_the_chassis_is_reduced_to_the_make() -> None:
    """FMLV holds `Fiat`, not `Fiat Ducato`, under the settled abbreviation rule."""
    assert base_vehicle_make("Fiat Ducato") == "Fiat"
    assert base_vehicle_make("MAN TGE") == "MAN"
    assert base_vehicle_make("Ford") == "Ford"
    assert base_vehicle_make(None) is None


def test_the_make_reaches_the_product(altair) -> None:
    extracted = build_extracted(_product(altair, "Altair", "RS"), payload_basis="")

    assert extracted.motorhome.base_vehicle_manufacturer == "MAN"


# --- body type ------------------------------------------------------------------------


def test_a_high_top_over_the_threshold() -> None:
    body_type, reason = body_type_for("High Top", 2700)

    assert body_type is BodyType.CAMPERVAN_HIGH_TOP
    assert "2300mm threshold" in reason


def test_an_elevating_roof_on_a_high_top_is_both(equinox) -> None:
    """The Equinox states `Elevating Roof` at 2.8m, which is a high top in its own right
    with a roof bed above it — and is what FMLV already holds for it."""
    extracted = build_extracted(_product(equinox, "Equinox", "Equinox"), payload_basis="")

    assert extracted.motorhome.body_type is BodyType.CAMPERVAN_HIGH_TOP_ELEVATING_ROOF


def test_an_elevating_roof_under_the_threshold_is_not_a_high_top() -> None:
    assert body_type_for("Elevating Roof", 2100)[0] is BodyType.CAMPERVAN_ELEVATING_ROOF


def test_an_unreadable_bodystyle_proposes_nothing() -> None:
    """Better blank than guessed, across eight mutually exclusive columns."""
    assert body_type_for("Coupe", 2700)[0] is None
    assert body_type_for(None, 2700)[0] is None


# --- habitation -----------------------------------------------------------------------


def test_the_positions_that_map_do() -> None:
    assert lounge_location_for("Front Conversion") is LoungeLocation.FRONT
    assert lounge_location_for("Rear") is LoungeLocation.REAR
    assert kitchen_location_for("Side") is KitchenLocation.SIDE
    assert bathroom_layout_for("Rear") == [BathroomLayout.REAR_SHOWER_TOILET]


def test_front_side_is_a_side_washroom() -> None:
    """The enum has no front, and nothing in `Front Side` claims the rear."""
    assert bathroom_layout_for("Front Side") == [BathroomLayout.SIDE_SHOWER_TOILET]


def test_rear_side_maps_to_nothing() -> None:
    """WildAx call it both; FMLV makes them exclusive. A guess across an exclusive group
    is worse than a gap, because the gap blocks the upload until a person looks."""
    assert kitchen_location_for("Rear Side") is None
    assert bathroom_layout_for("Rear Side") == []


def test_two_sleeping_areas_make_both(aurora) -> None:
    area, reason = sleeping_area_for(_panel(aurora, "Aurora", "Aurora").sleeping_areas)

    assert area is SleepingArea.BOTH
    assert "Rear and Front" in reason


def test_one_sleeping_area_is_that_one(constellation) -> None:
    panel = _panel(constellation, "Constellation", "3")

    assert sleeping_area_for(panel.sleeping_areas)[0] is SleepingArea.FRONT


def test_a_roof_bed_is_neither_front_nor_rear(equinox) -> None:
    """The Equinox names `Rear Lounge` and `Elevating Roof`. Reducing that to `rear` would
    quietly drop a berth's worth of information."""
    panel = _panel(equinox, "Equinox", "Equinox")
    area, reason = sleeping_area_for(panel.sleeping_areas)

    assert area is None
    assert "Elevating Roof" in reason


def test_no_sleeping_area_named_proposes_nothing() -> None:
    assert sleeping_area_for(())[0] is None


def test_the_bed_type_is_read_from_the_panel() -> None:
    assert bed_types_for("Transverse Bed") == [BedType.TRANSVERSE]
    assert bed_types_for("Bunk Beds") == [BedType.FIXED_BUNKS]
    assert bed_types_for("Twin Beds") == [BedType.FIXED_SEPARATE]
    assert bed_types_for("Lounge Conversion") == [BedType.MAKE_UP]
    assert bed_types_for("Front Conversion") == [BedType.MAKE_UP]
    assert bed_types_for(None) == []


# --- the whole product ----------------------------------------------------------------


def test_a_model_carries_every_field_fmlv_holds(aurora) -> None:
    """The Aurora, against what FMLV holds for product 8186 on 23 September 2026 — the
    masses and the belt count match to the unit, which is the strongest signal the parse
    is right."""
    extracted = build_extracted(_product(aurora, "Aurora", "Aurora"), payload_basis="")
    m = extracted.motorhome

    assert (m.manufacturer_range, m.model) == ("AURORA", "AURORA")
    assert m.mro_kilograms == 2958
    assert m.mtplm_kilograms == 3500
    assert m.mh_payload_kilograms == 542
    assert m.mh_passenger_seats_inc_driver == 3
    assert m.berths == 3
    assert m.base_vehicle_manufacturer == "Fiat"


def test_both_halves_of_the_identity_always_carry_provenance(aurora) -> None:
    """`compare_fields` walks only fields carrying provenance, and accepting a range
    change without its model corrupts the name."""
    provenance = build_extracted(
        _product(aurora, "Aurora", "Aurora"), payload_basis=""
    ).provenance

    assert "manufacturer_range" in provenance
    assert "model" in provenance
    assert "they are one name" in provenance["model"].snippet


def test_the_dimension_provenance_admits_its_own_precision(aurora) -> None:
    """The site publishes to two decimal places in metres; FMLV holds millimetres. A
    reviewer needs to see that `5.99 m` against `6000` is precision, not a change."""
    provenance = build_extracted(
        _product(aurora, "Aurora", "Aurora"), payload_basis=""
    ).provenance

    assert "accurate to the centimetre" in provenance["mh_length_mm"].snippet
    assert "5.99 m" in provenance["mh_length_mm"].snippet
