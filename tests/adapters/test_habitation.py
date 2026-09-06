"""The shared habitation vocabulary, against wording taken from real spec pages.

Every phrase quoted here appears verbatim on a manufacturer's site. The negative tests
are all traps that would have fired on the 34 Rimor products: "Wet room" read as wet
central heating, "Oven" read as a microwave, a priced bed option read as standard, and a
`Tags` line read as specification.
"""

from __future__ import annotations

import pytest

from src.adapters import habitation
from src.product_model.enums import BathroomLayout, BedType, Heating, Refrigeration

# --------------------------------------------------------------------------- #
# Refrigeration
# --------------------------------------------------------------------------- #


def test_a_freezer_compartment_makes_it_a_fridge_freezer() -> None:
    found = habitation.refrigeration_from(
        ["Kitchen unit equipped with 3 burner hob, sink, and a 141L fridge with freezer compartment"]
    )
    assert found is not None
    assert found[0] is Refrigeration.FRIDGE_FREEZER
    assert "freezer compartment" in found[1]


def test_a_freezer_anywhere_on_the_page_wins() -> None:
    """The requester's ruling: the summary abbreviates, the specification does not.

    Rimor's Sarus 66 Plus says "141 L fridge" in its summary and "141L fridge with
    freezer compartment" in its specification list. Reading only the first line that
    mentions a fridge would downgrade it.
    """
    found = habitation.refrigeration_from(
        [
            "Kitchen unit equipped with 3 burner hob, sink, and 141 L fridge",
            "Kitchen unit equipped with 3 burner hob, sink, and a 141L fridge with freezer compartment",
        ]
    )
    assert found is not None
    assert found[0] is Refrigeration.FRIDGE_FREEZER


def test_a_plain_fridge_stays_a_fridge() -> None:
    found = habitation.refrigeration_from(
        ["Kitchen unit equipped with 2 burner hob, sink, and a 90 L compressor fridge"]
    )
    assert found is not None
    assert found[0] is Refrigeration.FRIDGE


def test_a_refrigerator_column_is_a_fridge() -> None:
    """Rimor's wording for a tall fridge, which never says "fridge"."""
    found = habitation.refrigeration_from(
        ["141 L refrigerator column, which can be opened from both sides"]
    )
    assert found is not None
    assert found[0] is Refrigeration.FRIDGE


def test_no_refrigeration_mentioned_is_not_a_guess() -> None:
    assert habitation.refrigeration_from(["Cab air conditioning", "Oven"]) is None


# --------------------------------------------------------------------------- #
# Heating
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "line",
    [
        "Combi C4 heating and hot water system",
        "Truma Combi C6 heating/water heating system",
        "Webasto AirTop heating",
        "Blown air heating throughout",
        "Warm air heating system",
    ],
)
def test_warm_air_wording_is_blown_air(line: str) -> None:
    """The requester: any mention of blown or warm air settles it, brand irrelevant.

    A Truma Combi is a warm-air heater with a water tank, not a wet system.
    """
    found = habitation.heating_from([line])
    assert found is not None
    assert found[0] is Heating.BLOWN_AIR
    assert found[1] == line


@pytest.mark.parametrize(
    "line",
    [
        "Alde wet central heating with radiators",
        "Wet central heating system",
        "Underfloor heating as standard",
    ],
)
def test_water_based_wording_is_wet_central(line: str) -> None:
    found = habitation.heating_from([line])
    assert found is not None
    assert found[0] is Heating.WET_CENTRAL


def test_a_wet_room_is_a_bathroom_not_a_heating_system() -> None:
    """The trap. Seven Rimor products say "Wet room", and all seven are blown air.

    Matching a bare "wet" would have called every one of them wet central heating.
    """
    lines = ["Wet room Shower and cassette toilet with washbasin", "Combi C4 heating and hot water system"]
    found = habitation.heating_from(lines)
    assert found is not None
    assert found[0] is Heating.BLOWN_AIR


def test_hot_water_alone_is_not_wet_central_heating() -> None:
    """"heating and hot water" describes a water tank, not water-borne space heating."""
    found = habitation.heating_from(["Whale hot water heating"])
    assert found is None or found[0] is not Heating.WET_CENTRAL


def test_heating_of_an_unnamed_kind_is_reported_not_guessed() -> None:
    lines = ["Underseat heating unit"]
    assert habitation.heating_from(lines) is None
    assert habitation.heating_is_unclear(lines) == "Underseat heating unit"


def test_heating_is_unclear_stays_quiet_once_the_kind_is_known() -> None:
    assert habitation.heating_is_unclear(["Combi C4 heating and hot water system"]) is None


# --------------------------------------------------------------------------- #
# Microwave
# --------------------------------------------------------------------------- #


def test_a_microwave_is_recorded_when_stated() -> None:
    found = habitation.microwave_from(["Microwave oven fitted above the hob"])
    assert found is not None
    assert found[0] is True


def test_an_oven_is_not_a_microwave() -> None:
    """Rimor lists "Oven" on 24 products and a microwave on none."""
    assert habitation.microwave_from(["Oven", "3 burner hob", "Grill"]) is None


def test_no_microwave_mentioned_never_asserts_there_is_none() -> None:
    """`microwave` defaults to False, so returning False here would invent a negative."""
    assert habitation.microwave_from(["Oven"]) is None


# --------------------------------------------------------------------------- #
# Bathroom
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "line",
    [
        "The new layout consists of a separate shower cubicle and cassette toilet with a washbasin",
        "Separate shower and a toilet",
        "The new layout consists of a Shower cubicle and separate cassette toilet with a washbasin",
    ],
)
def test_separated_shower_and_toilet_is_read_from_the_words(line: str) -> None:
    found = habitation.bathroom_from([line])
    assert found is not None
    assert found[0] is BathroomLayout.SEPARATE_SHOWER_TOILET


def test_a_wet_room_is_left_to_the_reviewer() -> None:
    """Combined, but `BathroomLayout` then wants rear or side and the prose cannot say."""
    assert habitation.bathroom_from(["Wet room Shower and cassette toilet with washbasin"]) is None


def test_a_combined_washroom_is_left_to_the_reviewer() -> None:
    assert (
        habitation.bathroom_from(
            ["Central washroom equipped with shower cubicle, washbasin, and a cassette toilet"]
        )
        is None
    )


def test_an_external_shower_says_nothing_about_the_bathroom() -> None:
    """Four Rimor products offer one, and it is not the vehicle's washroom."""
    assert habitation.bathroom_from(["External water supply with shower as standard"]) is None


# --------------------------------------------------------------------------- #
# Bed types
# --------------------------------------------------------------------------- #


def test_both_beds_are_recorded_when_the_copy_names_both() -> None:
    """The case that prompted the module — Sarus 66 Plus.

    FMLV holds island + drop-down; the adapter had been proposing island alone, because
    the factory publishes one word ("Central bed") for the whole layout.
    """
    beds, quotes = habitation.bed_types_from(
        ["Rear double island bed", "Electric drop-down double bed at the front."]
    )
    assert beds == [BedType.ISLAND, BedType.DROP_DOWN]
    assert len(quotes) == 2


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("Rear Fixed Transverse double bed", BedType.TRANSVERSE),
        ("Rear double island bed", BedType.ISLAND),
        ("Rear fixed bunk beds", BedType.FIXED_BUNKS),
        ("Rear Fixed twin single beds", BedType.FIXED_SEPARATE),
        ("Rear fixed bed", BedType.FIXED),
        ("XL Front Electric drop-down double bed", BedType.DROP_DOWN),
    ],
)
def test_each_bed_shape(line: str, expected: BedType) -> None:
    beds, _quotes = habitation.bed_types_from([line])
    assert beds == [expected]


def test_a_bed_is_never_recorded_twice_from_one_line() -> None:
    """"Rear Twin single beds" matches three phrases in the table; it is one bed type."""
    beds, _quotes = habitation.bed_types_from(["Rear Twin single beds"])
    assert beds == [BedType.FIXED_SEPARATE]


def test_seating_that_converts_is_a_make_up_bed_and_not_its_shape() -> None:
    """The singles exist only once the lounge is made up, so they are not fixed."""
    beds, _quotes = habitation.bed_types_from(["Rear lounge which converts into single beds"])
    assert beds == [BedType.MAKE_UP]


def test_a_fixed_bed_that_also_converts_is_both() -> None:
    """The twins are permanently there and join into a double. `bed_types` is multi-select."""
    beds, _quotes = habitation.bed_types_from(
        ["Rear Twin single beds, which can make a double bed"]
    )
    assert beds == [BedType.MAKE_UP, BedType.FIXED_SEPARATE]


def test_a_fold_away_bed_is_a_make_up_bed() -> None:
    """Horus 38: the factory calls this "Double bed", and MNC is the accurate one."""
    beds, _quotes = habitation.bed_types_from(["Rear fold-away double bed"])
    assert beds == [BedType.MAKE_UP]


def test_a_priced_bed_option_is_not_standard_equipment() -> None:
    beds, quotes = habitation.bed_types_from(
        ["Rear Adjustable Bed Option: £1,500", "Height Adjustable Rear Bed- £1,500"]
    )
    assert beds == []
    assert quotes == []


def test_a_bed_mentioned_as_a_landmark_is_not_a_bed_type() -> None:
    """Kilig's "Twin bed divider with steps […] a handy step for climbing into bed"."""
    beds, _quotes = habitation.bed_types_from(
        ["Twin bed divider with steps. By night, a handy step for climbing into bed"]
    )
    assert beds == []


def test_no_beds_named_returns_nothing() -> None:
    assert habitation.bed_types_from(["Cab swivel seats", "Oven"]) == ([], [])


# --------------------------------------------------------------------------- #
# Line filtering and the entry point
# --------------------------------------------------------------------------- #


def test_usable_lines_drops_priced_options() -> None:
    assert habitation.usable_lines(["Oven", "Alloy wheel option: £1,350"]) == ["Oven"]


def test_usable_lines_drops_the_tag_metadata() -> None:
    """"Tags 687TC, rimor, transverse bed" repeats feature words out of context."""
    kept = habitation.usable_lines(
        ["Tags 687TC , rimor , transverse bed", "Categories All Overcab , Super Brig", "Oven"]
    )
    assert kept == ["Oven"]


def test_features_from_returns_only_what_the_copy_settles() -> None:
    features = habitation.features_from(
        [
            "Combi C4 heating and hot water system",
            "Kitchen unit equipped with 3 burner hob, sink, and a 141L fridge with freezer compartment",
            "The new layout consists of a separate shower cubicle and cassette toilet with a washbasin",
            "Rear double island bed",
            "Electric drop-down double bed at the front.",
            "Oven",
        ]
    )
    assert features["heating"].value is Heating.BLOWN_AIR
    assert features["refrigeration"].value is Refrigeration.FRIDGE_FREEZER
    assert features["bathroom_layout"].value is BathroomLayout.SEPARATE_SHOWER_TOILET
    assert features["bed_types"].value == [BedType.ISLAND, BedType.DROP_DOWN]
    # No microwave on the page, so no key at all — not a False.
    assert "microwave" not in features


def test_features_from_quotes_the_manufacturers_own_wording() -> None:
    features = habitation.features_from(["Combi C4 heating and hot water system"])
    assert features["heating"].snippet == "Combi C4 heating and hot water system"


def test_features_from_an_empty_page_is_empty() -> None:
    assert habitation.features_from([]) == {}


def test_a_shape_word_never_implies_a_fixed_bed() -> None:
    """"French" and "double" describe a bed's shape and width, not its permanence.

    The requester, 6 September 2026, on Horus 12: *"A double bed is not a fixed bed […]
    French bed really has to do with the shape of it. It normally is fixed, but actually
    that's not relevant. It says it folds away."* FMLV has no column for a French bed and
    only asks built-in versus made up, so a shape word alone answers nothing and the
    layout falls through to its floorplan.
    """
    assert habitation.bed_types_from(["Rear double French bed"]) == ([], [])
    assert habitation.bed_types_from(["Rear double bed"]) == ([], [])


def test_an_explicit_word_still_gives_a_fixed_bed() -> None:
    beds, _quotes = habitation.bed_types_from(["Rear fixed double bed"])
    assert beds == [BedType.FIXED]


@pytest.mark.parametrize(
    "line",
    [
        "The Horus 12 offers a rear double French bed that also lifts to create more storage space",
        "Rear fold-away double bed",
        "Rear bed lifts for extra storage",
    ],
)
def test_a_bed_that_lifts_or_folds_is_made_up(line: str) -> None:
    """Lifting is the same claim as folding: the bed is not standing made up."""
    beds, _quotes = habitation.bed_types_from([line])
    assert BedType.MAKE_UP in beds
    assert BedType.FIXED not in beds
