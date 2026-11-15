"""Tests for the Coachman touring caravan adapter.

Pure parsing only: no network, no browser. The fixtures are the live Acadia and VIP range
pages trimmed to the two regions the parsers read — the equipment sections and the
technical panels, in that order, because `coachman.parse_equipment` stops at the first
panel — plus the caravan half of the homepage and the two REST payloads.

Every negative test here is a trap this adapter actually hit while it was being written.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.adapters import coachman_caravan
from src.adapters.coachman import (
    _squash,
    parse_cards,
    parse_equipment,
    parse_range_counts,
    parse_ranges,
    parse_roster,
    parse_specification_panels,
)
from src.adapters.coachman_caravan import (
    EXPECTED_PRODUCTS,
    CoachmanCaravanProduct,
    CoachmanCaravanSpec,
    _agrees_with_card,
    _habitation_features,
    applies_to,
    build_extracted,
    spec_from_panel,
    unmatched_qualifiers,
)
from src.product_model.enums import CaravanBodyType, Heating, Refrigeration
from src.vehicle_class import VehicleClass

FIXTURES = Path(__file__).parent / "fixtures"
ACADIA = (FIXTURES / "coachman_caravan_acadia_panels.html").read_text(encoding="utf-8")
VIP = (FIXTURES / "coachman_caravan_vip_panels.html").read_text(encoding="utf-8")
HOMEPAGE = (FIXTURES / "coachman_caravan_homepage_cards.html").read_text(encoding="utf-8")
TAXONOMY = (FIXTURES / "coachman_caravan_model.json").read_text(encoding="utf-8")
ROSTER = (FIXTURES / "coachman_caravan.json").read_text(encoding="utf-8")

ACADIA_MODELS = frozenset({"545 Xtra", "575 Xtra", "655 Xtra", "660 Xtra"})


# --------------------------------------------------------------------------- #
# Registration
# --------------------------------------------------------------------------- #


def test_it_registers_as_the_caravan_adapter_not_a_second_motorhome_one() -> None:
    """Without `VEHICLE_CLASS` this module would silently replace `coachman.py`."""
    assert coachman_caravan.VEHICLE_CLASS is VehicleClass.CARAVAN
    assert coachman_caravan.MANUFACTURER == "Coachman"
    assert coachman_caravan.MANUFACTURER_DISPLAY_NAME == "Coachman"


# --------------------------------------------------------------------------- #
# Identity: the taxonomy and the roster
# --------------------------------------------------------------------------- #


def test_the_taxonomy_names_four_ranges_totalling_the_expected_products() -> None:
    """Coachman's own CMS counts its caravans per range — a free completeness check."""
    ranges = parse_ranges(TAXONOMY)
    counts = parse_range_counts(TAXONOMY)

    assert sorted(ranges.values()) == ["Acadia", "Laser", "Lusso", "VIP"]
    assert sum(counts.values()) == EXPECTED_PRODUCTS == 19


def test_the_roster_names_every_caravan_with_its_range_stripped_from_the_model() -> None:
    products = parse_roster(ROSTER, coachman_caravan.POST_TYPE, parse_ranges(TAXONOMY))

    assert len(products) == EXPECTED_PRODUCTS
    by_label = {f"{p.range_label} {p.model}" for p in products}
    assert "Acadia 545 Xtra" in by_label
    assert "Lusso IV" in by_label
    assert {p.model for p in products if p.range_label == "Lusso"} == {"I", "II", "III", "IV"}
    # The range comes off as a whole prefix, so no model keeps part of it.
    assert not any(p.model.startswith(p.range_label) for p in products)


# --------------------------------------------------------------------------- #
# The technical panel
# --------------------------------------------------------------------------- #


def test_every_model_of_a_range_has_its_own_panel() -> None:
    assert set(parse_specification_panels(ACADIA)) == ACADIA_MODELS
    assert set(parse_specification_panels(VIP)) == {"460", "520", "545", "565", "575"}


def test_a_panel_yields_every_figure_fmlv_records() -> None:
    spec = spec_from_panel(parse_specification_panels(VIP)["460"])

    assert spec.rrp_pounds == 35590
    assert spec.berths == 2
    assert spec.twin_axle is False
    assert spec.mtplm_kilograms == 1452
    assert spec.mro_kilograms == 1327
    assert spec.personal_effects_payload_kilograms == 125
    assert spec.total_payload_kilograms == 125
    assert spec.max_nose_weight_kilograms == 100
    assert spec.internal_length_mm == 4750
    assert spec.shipping_length_mm == 6380
    assert spec.overall_width_mm == 2310
    assert spec.height_mm == 2675
    assert spec.headroom_mm == 1955
    assert spec.awning_length_mm == 9130


def test_overall_length_is_the_shipping_length_not_the_interior_one() -> None:
    """The single most plausible way to get a caravan adapter wrong.

    Both are lengths, both are in the panel, and swapping them looks reasonable on any one
    product. FMLV's own row for this caravan holds 7390mm as `shipping_length_mm`.
    """
    spec = spec_from_panel(parse_specification_panels(ACADIA)["545 Xtra"])

    assert spec.shipping_length_mm == 7390
    assert spec.internal_length_mm == 5760
    assert spec.shipping_length_mm > spec.internal_length_mm


def test_the_air_conditioning_height_is_not_the_one_recorded() -> None:
    """Coachman publish 2675mm including the TV aerial and 2750mm including air
    conditioning. FMLV holds 2675 on all 19, so that is the one read."""
    spec = spec_from_panel(parse_specification_panels(ACADIA)["545 Xtra"])

    assert spec.height_mm == 2675


def test_the_optional_weight_plate_upgrade_is_not_the_mtplm() -> None:
    """`Upper MTPLM` is the optioned figure; the base vehicle rule takes the base."""
    pairs = parse_specification_panels(ACADIA)["545 Xtra"]

    assert "1750 kg" in pairs["Upper MTPLM (Optional weight plate upgrade"]
    assert spec_from_panel(pairs).mtplm_kilograms == 1679


@pytest.mark.parametrize("raw", ["1014 cm", "1062cm", "913cm"])
def test_the_awning_is_read_in_centimetres_with_or_without_a_space(raw: str) -> None:
    spec = spec_from_panel({"Awning Size (Approx. for reference only)": raw})

    assert spec.awning_length_mm == round(float(raw.replace("cm", "").strip()) * 10)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("Single axle", False), ("Twin axle", True), ("Twin Axle", True)],
)
def test_the_axle_count_survives_coachmans_inconsistent_capitals(
    raw: str, expected: bool
) -> None:
    """The Lusso IV writes `Twin Axle` where its three siblings write `Twin axle`."""
    assert spec_from_panel({"Axles": raw}).twin_axle is expected


# --------------------------------------------------------------------------- #
# `TBC`, which is Coachman's house style for an unsettled figure
# --------------------------------------------------------------------------- #


def test_tbc_masses_parse_to_absent_and_the_caravan_is_still_built() -> None:
    """VIP 520 publishes `TBC` in every mass field. Its price and dimensions are real, so
    dropping it would lose them over an unset weight."""
    spec = spec_from_panel(parse_specification_panels(VIP)["520"])

    assert spec.mtplm_kilograms is None
    assert spec.mro_kilograms is None
    assert spec.personal_effects_payload_kilograms is None
    assert spec.max_nose_weight_kilograms is None
    # Everything Coachman did publish is still there.
    assert spec.rrp_pounds == 37790
    assert spec.berths == 3
    assert spec.shipping_length_mm == 7050
    assert spec.overall_width_mm == 2310


def test_a_tbc_mass_is_never_read_as_zero() -> None:
    spec = spec_from_panel({"MTPLM": "TBC", "Mass in Running Order": "TBC"})

    assert spec.mtplm_kilograms is None
    assert spec.mro_kilograms is None


# --------------------------------------------------------------------------- #
# The self-check
# --------------------------------------------------------------------------- #


def test_both_payload_rows_equal_mtplm_minus_mro_on_every_weighed_model() -> None:
    for html in (ACADIA, VIP):
        for model, pairs in parse_specification_panels(html).items():
            spec = spec_from_panel(pairs)
            if spec.mtplm_kilograms is None:
                continue
            assert spec.payload_reconciles is True, model


def test_an_unweighed_model_cannot_fail_the_check_for_being_blank() -> None:
    spec = spec_from_panel(parse_specification_panels(VIP)["520"])

    assert spec.payload_reconciles is None


def test_a_payload_that_contradicts_the_two_masses_fails() -> None:
    spec = CoachmanCaravanSpec(
        mtplm_kilograms=1679,
        mro_kilograms=1519,
        personal_effects_payload_kilograms=160,
        total_payload_kilograms=175,
    )

    assert spec.payload_reconciles is False


# --------------------------------------------------------------------------- #
# The homepage card, read only to check the panel against
# --------------------------------------------------------------------------- #


def test_the_card_key_matches_the_rosters_model_once_squashed() -> None:
    """`CoachmanCard.key` squashes the heading to alphanumerics, so `545 Xtra` keys on
    `545XTRA`. Looking it up with the readable name finds nothing."""
    cards = parse_cards(HOMEPAGE)

    assert len(cards) == EXPECTED_PRODUCTS
    assert all(kind == "caravan" for kind, _term, _model in cards)
    assert any(model == "545XTRA" for _kind, _term, model in cards)
    assert ("caravan", 7, "545 Xtra") not in cards


def test_every_card_agrees_with_its_panel_on_the_masses() -> None:
    """The cross-check across all 19, which is what makes the join trustworthy."""
    cards = parse_cards(HOMEPAGE)
    checked = 0
    for html in (ACADIA, VIP):
        for model, pairs in parse_specification_panels(html).items():
            spec = spec_from_panel(pairs)
            card = next(
                (c for key, c in cards.items() if key[2] == _squash(model)),
                None,
            )
            assert card is not None, model
            assert card.mtplm_kilograms == spec.mtplm_kilograms, model
            assert card.mro_kilograms == spec.mro_kilograms, model
            assert card.berths == spec.berths, model
            checked += 1
    assert checked == 9


def test_a_panel_and_card_that_agree_pass_the_cross_check() -> None:
    product = CoachmanCaravanProduct(
        term_id=7,
        range_label="Acadia",
        range_slug="acadia",
        model="545 Xtra",
        title="Acadia 545 Xtra",
        spec=spec_from_panel(parse_specification_panels(ACADIA)["545 Xtra"]),
        card_mtplm_kilograms=1679,
        card_mro_kilograms=1519,
        card_berths=4,
    )

    assert _agrees_with_card(product) is None


def test_a_panel_carrying_another_caravans_weight_is_caught() -> None:
    """Two different joins over Coachman's own data. Disagreement means one has slipped,
    which produces entirely plausible caravans wearing each other's figures."""
    product = CoachmanCaravanProduct(
        term_id=7,
        range_label="Acadia",
        range_slug="acadia",
        model="545 Xtra",
        title="Acadia 545 Xtra",
        spec=spec_from_panel(parse_specification_panels(ACADIA)["545 Xtra"]),
        card_mtplm_kilograms=1835,
        card_mro_kilograms=1519,
        card_berths=4,
    )

    disagreement = _agrees_with_card(product)
    assert disagreement is not None
    assert "1679" in disagreement
    assert "1835" in disagreement


def test_a_blank_card_figure_is_not_a_disagreement() -> None:
    """The two `TBC` models have no mass on the card either. Absent is not a conflict."""
    product = CoachmanCaravanProduct(
        term_id=6,
        range_label="VIP",
        range_slug="vip",
        model="520",
        title="VIP 520",
        spec=spec_from_panel(parse_specification_panels(VIP)["520"]),
        card_mtplm_kilograms=None,
        card_mro_kilograms=None,
        card_berths=3,
    )

    assert _agrees_with_card(product) is None


# --------------------------------------------------------------------------- #
# Equipment qualifiers — the reason this adapter does not blanket a range
# --------------------------------------------------------------------------- #


def test_an_unqualified_line_applies_to_every_model_of_the_range() -> None:
    line = "Alde wet central heating and hot water system with 5 year Glycol"

    assert applies_to(line, "545 Xtra", twin_axle=False, models_in_range=ACADIA_MODELS)
    assert applies_to(line, "660 Xtra", twin_axle=True, models_in_range=ACADIA_MODELS)


def test_a_line_qualified_for_named_models_reaches_only_those() -> None:
    line = "Thetford N4090 91 litre electronic fridge freezer (545 Xtra and 575 Xtra)"

    assert applies_to(line, "545 Xtra", twin_axle=False, models_in_range=ACADIA_MODELS)
    assert applies_to(line, "575 Xtra", twin_axle=False, models_in_range=ACADIA_MODELS)
    assert not applies_to(line, "655 Xtra", twin_axle=True, models_in_range=ACADIA_MODELS)
    assert not applies_to(line, "660 Xtra", twin_axle=True, models_in_range=ACADIA_MODELS)


def test_an_excluding_qualifier_reaches_everyone_but_the_model_named() -> None:
    line = "Square shower cubicle with LED light and black pivot door (excluding 660 xtra)"

    assert applies_to(line, "545 Xtra", twin_axle=False, models_in_range=ACADIA_MODELS)
    assert not applies_to(line, "660 Xtra", twin_axle=True, models_in_range=ACADIA_MODELS)


@pytest.mark.parametrize(
    ("qualifier", "twin_axle", "expected"),
    [
        ("(Single axle models)", False, True),
        ("(Single axle models)", True, False),
        ("(Twin axle models)", True, True),
        ("(single axles)", False, True),
    ],
)
def test_an_axle_qualifier_selects_on_the_axle_count(
    qualifier: str, twin_axle: bool, expected: bool
) -> None:
    line = f"AL-KO secure wheel lock {qualifier}"

    assert (
        applies_to(line, "545 Xtra", twin_axle=twin_axle, models_in_range=ACADIA_MODELS)
        is expected
    )


def test_model_specific_applies_to_nobody() -> None:
    """Coachman are saying outright that the line does not hold for every model, and not
    saying which. Writing it onto all of them would assert what they just denied."""
    line = "Mini roof light in end bathroom models (model specific)"

    assert not applies_to(line, "545 Xtra", twin_axle=False, models_in_range=ACADIA_MODELS)


def test_the_i_inside_an_ordinary_word_is_not_the_lusso_i() -> None:
    """The regression that made 29 unrelated lines read as model qualifiers.

    A case-insensitive roman-numeral token matched the `i` in `specific`, `fixed` and
    `possible`, so every parenthetical in the range looked like a model name.
    """
    lusso = frozenset({"I", "II", "III", "IV"})
    line = "Deep, quality foam construction mattresses (fixed beds)"

    assert applies_to(line, "I", twin_axle=False, models_in_range=lusso)
    assert applies_to(line, "II", twin_axle=True, models_in_range=lusso)


def test_a_parenthetical_that_names_no_model_is_not_a_qualifier_at_all() -> None:
    """Most trailing parentheses are not about models. A rule that guessed at them would
    run silently on every line of every range forever."""
    for line in (
        "Mains connection lead (25m)",
        "Scorpion tracker S7 (Thatcham Approved) including 12 months subscription",
        "Alde wet central heating and hot water system (5 year Glycol)",
    ):
        assert applies_to(line, "545 Xtra", twin_axle=False, models_in_range=ACADIA_MODELS)


def test_a_qualifier_naming_a_layout_the_range_lacks_is_reported() -> None:
    """Coachman offer the Acadia's larger fridge freezer to `(665 Xtra and 660 Xtra)` in a
    range whose models are 545, 575, 655 and 660. `665` does not exist, and the 655 is left
    with no refrigeration line at all."""
    flagged = unmatched_qualifiers(tuple(parse_equipment(ACADIA).standard), ACADIA_MODELS)

    assert any("665 Xtra" in line and "fridge freezer" in line for line in flagged)


def test_a_qualifier_naming_only_real_models_is_not_reported() -> None:
    assert (
        unmatched_qualifiers(
            ("Thetford N4090 fridge freezer (545 Xtra and 575 Xtra)",), ACADIA_MODELS
        )
        == []
    )


def test_a_line_with_one_real_and_one_unknown_layout_is_still_reported() -> None:
    """A stricter test — every code unknown — would pass the Acadia's fridge line and
    leave the 655 quietly unserved."""
    flagged = unmatched_qualifiers(
        ("Thetford N4142 fridge freezer (665 Xtra and 660 Xtra)",), ACADIA_MODELS
    )

    assert len(flagged) == 1


# --------------------------------------------------------------------------- #
# Habitation findings
# --------------------------------------------------------------------------- #


def _product(model: str, html: str, models: frozenset[str], **kwargs) -> CoachmanCaravanProduct:
    return CoachmanCaravanProduct(
        term_id=7,
        range_label="Acadia",
        range_slug="acadia",
        model=model,
        title=f"Acadia {model}",
        models_in_range=models,
        spec=spec_from_panel(parse_specification_panels(html)[model]),
        equipment=parse_equipment(html),
        **kwargs,
    )


def test_the_range_wide_heating_and_microwave_reach_every_model() -> None:
    features = _habitation_features(_product("545 Xtra", ACADIA, ACADIA_MODELS))

    assert features["heating"].value is Heating.WET_CENTRAL
    assert features["microwave"].value is True


def test_a_qualified_fridge_reaches_only_the_models_it_names() -> None:
    both = _habitation_features(_product("545 Xtra", ACADIA, ACADIA_MODELS))
    assert both["refrigeration"].value is Refrigeration.FRIDGE_FREEZER

    # The 655 Xtra's only fridge line is the one qualified for a model that does not
    # exist, so it is left unanswered rather than given the other model's fridge.
    orphan = _habitation_features(_product("655 Xtra", ACADIA, ACADIA_MODELS))
    assert "refrigeration" not in orphan


def test_bed_types_are_dropped_however_the_equipment_reads() -> None:
    """The list is per range, so a bed named in it would be written onto every model. The
    per-model `Bed Sizes` row is the better source, and this adapter declines that too."""
    for model in sorted(ACADIA_MODELS):
        assert "bed_types" not in _habitation_features(_product(model, ACADIA, ACADIA_MODELS))


# --------------------------------------------------------------------------- #
# The built caravan
# --------------------------------------------------------------------------- #


def _built(model: str, html: str, models: frozenset[str]):
    return build_extracted(
        _product(model, html, models),
        panel_url="https://www.coachman.co.uk/acadia/",
        roster_url="https://www.coachman.co.uk/wp-json/wp/v2/caravan?per_page=100",
    )


def test_a_built_caravan_carries_every_figure_and_its_identity() -> None:
    caravan = _built("545 Xtra", ACADIA, ACADIA_MODELS).caravan

    assert caravan.manufacturer == "Coachman"
    assert caravan.manufacturer_range == "Acadia"
    assert caravan.model == "545 Xtra"
    assert caravan.rrp_pounds == 35500
    assert caravan.berths == 4
    assert caravan.mtplm_kilograms == 1679
    assert caravan.mro_kilograms == 1519
    assert caravan.personal_effects_payload_kilograms == 160
    assert caravan.max_nose_weight_kilograms == 100
    assert caravan.shipping_length_mm == 7390
    assert caravan.internal_length_mm == 5760
    assert caravan.overall_width_mm == 2440
    assert caravan.height_mm == 2675
    assert caravan.headroom_mm == 1955
    assert caravan.awning_length_mm == 10140
    assert caravan.twin_axle is False


def test_the_optional_payload_column_is_left_blank() -> None:
    """`Total / Maximum User Payload` equals `Personal Payload` on every model, so the
    optional half is nil — its normal state on all 92 real caravan products."""
    caravan = _built("545 Xtra", ACADIA, ACADIA_MODELS).caravan

    assert caravan.optional_equipment_payload_kilograms is None


def test_the_body_type_is_rigid_and_says_why() -> None:
    extracted = _built("545 Xtra", ACADIA, ACADIA_MODELS)

    assert extracted.caravan.body_type is CaravanBodyType.RIGID
    assert "walls fold or rise" in extracted.provenance["body_type"].snippet


def test_the_nose_weight_is_recorded_with_provenance_so_it_reaches_towcheck() -> None:
    """Without a provenance entry it is set on the caravan and reported to nobody."""
    extracted = _built("660 Xtra", ACADIA, ACADIA_MODELS)

    assert extracted.caravan.max_nose_weight_kilograms == 120
    assert "TowCheck" in extracted.provenance["max_nose_weight_kilograms"].snippet


def test_the_range_provenance_points_at_the_taxonomy_not_the_card() -> None:
    """The homepage card is headed `545 Xtra` alone, which is not unique across ranges."""
    provenance = _built("545 Xtra", ACADIA, ACADIA_MODELS).provenance["manufacturer_range"]

    assert "wp-json" in provenance.source_url
    assert "taxonomy term" in provenance.snippet


def test_no_layout_field_is_proposed_from_the_panel() -> None:
    """VIP 520 publishes `No Fixed Bed` and a front make-up only, and FMLV holds it as
    sleeping at both ends with fixed bunks. One model defeats the inference, so none of
    these are derived."""
    caravan = build_extracted(
        CoachmanCaravanProduct(
            term_id=6,
            range_label="VIP",
            range_slug="vip",
            model="520",
            title="VIP 520",
            models_in_range=frozenset({"460", "520", "545", "565", "575"}),
            spec=spec_from_panel(parse_specification_panels(VIP)["520"]),
            equipment=parse_equipment(VIP),
        ),
        panel_url="https://www.coachman.co.uk/vip/",
        roster_url="https://www.coachman.co.uk/wp-json/wp/v2/caravan?per_page=100",
    ).caravan

    assert caravan.sleeping_area is None
    assert caravan.bed_types == []
    assert caravan.kitchen_location is None
    assert caravan.bathroom_layout == []
    assert caravan.lounge_location is None


def test_an_unweighed_caravan_keeps_its_price_and_dimensions() -> None:
    caravan = build_extracted(
        CoachmanCaravanProduct(
            term_id=6,
            range_label="VIP",
            range_slug="vip",
            model="565",
            title="VIP 565",
            models_in_range=frozenset({"460", "520", "545", "565", "575"}),
            spec=spec_from_panel(parse_specification_panels(VIP)["565"]),
            equipment=parse_equipment(VIP),
        ),
        panel_url="https://www.coachman.co.uk/vip/",
        roster_url="https://www.coachman.co.uk/wp-json/wp/v2/caravan?per_page=100",
    ).caravan

    assert caravan.mtplm_kilograms is None
    assert caravan.rrp_pounds == 38430
    assert caravan.shipping_length_mm == 7370
    assert caravan.berths == 4


def test_the_fixtures_still_describe_the_range_the_taxonomy_counts() -> None:
    """A guard on the fixtures themselves: trimming the pages must not lose a panel."""
    counts = {
        name: parse_range_counts(TAXONOMY)[term]
        for term, name in parse_ranges(TAXONOMY).items()
    }

    assert len(parse_specification_panels(ACADIA)) == counts["Acadia"]
    assert len(parse_specification_panels(VIP)) == counts["VIP"]


def test_the_roster_and_the_taxonomy_agree_on_every_range(tmp_path: Path) -> None:
    ranges = parse_ranges(TAXONOMY)
    counts = parse_range_counts(TAXONOMY)
    products = parse_roster(ROSTER, coachman_caravan.POST_TYPE, ranges)

    for term, expected in counts.items():
        found = sum(1 for p in products if p.term_id == term)
        assert found == expected, ranges[term]
    assert json.loads(ROSTER)[0]["title"]["rendered"].startswith("Lusso")
