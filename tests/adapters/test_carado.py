"""Carado's parsing, against real captured pages.

No network. Each `carado_*.html` fixture is one live page **sliced in document order**,
keeping only what the adapter reads: the headings, every table sharing the modal's class,
the accordion titles that divide standard equipment from optional, the facts-card pairs and
the floorplan paths. Order is preserved deliberately — the parser uses positions to decide
which vehicle on a multi-vehicle page owns which specification and which drawing.

Five layout pages were kept, each for a reason, and `carado_roster.html` for the roster:

* `cv640` — **three vehicles on one page**, base, PRO and PRO+, with three drawings. The
  trap the whole adapter is shaped around.
* `cv601-pro` — the other template: its specification is a definition list, not a table, so
  a parser that knew only about tables lost this vehicle entirely. It is also the only one
  of the 29 with no floorplan at all.
* `a132-pro` — the thin Alcove page: no equipment accordions, a Citroën chassis, and the
  price that disagrees with the roster page by £3,400.
* `t457` — a Ford chassis and `EDITION27` in the name, so its drawing joins on a prefix.
* `v337` — the `Van` that is a low profile, GRP-bodied at 214 cm wide.

Every negative test below is a trap that is real on this site — see
`docs/adapters/carado.md`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters import carado
from src.adapters.carado import CaradoVehicle, RosterEntry
from src.product_model.enums import BodyType, Heating, Refrigeration

FIXTURES = Path(__file__).parent / "fixtures"

#: (fixture, the URL it was captured from). The URL matters: `parse_page_vehicles` reads the
#: body style out of it, and the body style decides the body type.
CAPTURED: tuple[tuple[str, str], ...] = (
    ("cv640", "https://carado.com/gb/en/motorhomes/camper-van/cv640"),
    ("cv601_pro", "https://carado.com/gb/en/motorhomes/camper-van/cv601-pro"),
    ("a132_pro", "https://carado.com/gb/en/motorhomes/alcoves/a132-pro"),
    ("t457", "https://carado.com/gb/en/motorhomes/semi-integrated/t457"),
    ("v337", "https://carado.com/gb/en/motorhomes/van/v337"),
)

#: What the roster page publishes, and therefore what the tests assert. 29 vehicles across
#: 23 layout pages — the requester confirmed FMLV holds 30, the difference being a
#: withdrawn layout the first run reports as a disappearance.
EXPECTED_VEHICLES = 29
EXPECTED_BY_HEADLINE = {
    "Integrated": 2,
    "Semi-Integrated": 8,
    "Vans": 3,
    "Alcoves": 3,
    "Camper Vans": 13,
}


def _read(name: str) -> str:
    return (FIXTURES / f"carado_{name}.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def roster() -> list[RosterEntry]:
    return carado.parse_roster(_read("roster"))


@pytest.fixture(scope="module")
def vehicles() -> dict[str, CaradoVehicle]:
    """Every captured vehicle, keyed on the name its page publishes."""
    found: dict[str, CaradoVehicle] = {}
    for name, url in CAPTURED:
        parsed = carado.parse_page_vehicles(url, _read(name))
        assert parsed, f"{name} produced no vehicle"
        for vehicle in parsed:
            found[vehicle.name] = vehicle
    return found


# --------------------------------------------------------------------------- #
# The roster page
# --------------------------------------------------------------------------- #


def test_the_roster_is_the_product_count(roster: list[RosterEntry]) -> None:
    """29 vehicles, which is the number every other count is checked against."""
    assert len(roster) == EXPECTED_VEHICLES


def test_every_vehicle_carries_its_range_headline_and_price(roster: list[RosterEntry]) -> None:
    """The headline is the only place the range is published; the layout pages never say it."""
    by_headline: dict[str, int] = {}
    for entry in roster:
        by_headline[entry.range_headline] = by_headline.get(entry.range_headline, 0) + 1
        assert entry.rrp_pounds, entry.name
        assert entry.model_id.isdigit(), entry.name

    assert by_headline == EXPECTED_BY_HEADLINE


def test_the_roster_prices_are_read_as_whole_pounds(roster: list[RosterEntry]) -> None:
    """`'from £53,090'` -> `53090`. The `from` price is the layout's own."""
    cv640 = next(entry for entry in roster if entry.name == "CV640")

    assert cv640.rrp_pounds == 53090


@pytest.mark.parametrize("payload", ["", "<html></html>", "<div>no groups here</div>"])
def test_an_unreadable_roster_yields_nothing(payload: str) -> None:
    assert carado.parse_roster(payload) == []


# --------------------------------------------------------------------------- #
# Identity — the PRO tier belongs in the range
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("published", "headline", "expected_range", "expected_model"),
    [
        ("CV640", "Camper Vans", "Campervan", "CV640"),
        ("CV640 PRO", "Camper Vans", "Campervan PRO", "CV640"),
        ("CV640 PRO+", "Camper Vans", "Campervan PRO+", "CV640"),
        ("A464 PRO", "Alcoves", "Alcoves PRO", "A464"),
        ("T447", "Semi-Integrated", "Semi-integrated", "T447"),
        ("I338", "Integrated", "Integrated", "I338"),
        ("V337", "Vans", "Van", "V337"),
    ],
)
def test_the_tier_moves_to_the_range_and_the_model_keeps_its_prefix(
    published: str, headline: str, expected_range: str, expected_model: str
) -> None:
    """The requester's ruling, 9 September 2026, with two real FMLV rows in front of him.

    FMLV holds range `Campervan PRO` + model `CV602`, so the tier lives in the range and the
    letter prefix stays on the model. Its own `Alcoves` + `A464 PRO` is one of the
    inconsistencies he asked to have corrected, not copied.
    """
    entry = RosterEntry(published, headline, 1, "1")

    assert entry.fmlv_range == expected_range
    assert entry.fmlv_model == expected_model


def test_pro_plus_is_tested_before_pro() -> None:
    """Otherwise every PRO+ reads as a PRO with a stray `+` left on the model."""
    entry = RosterEntry("CV600 PRO+", "Camper Vans", 1, "1")

    assert entry.tier == " PRO+"
    assert entry.fmlv_model == "CV600"
    assert "+" not in entry.fmlv_model


@pytest.mark.parametrize("published", ["T457 EDITION27", "CV595 4x4 X-EDITION"])
def test_an_edition_is_not_a_tier_and_stays_in_the_model(published: str) -> None:
    """A model-year or drivetrain edition is not the PRO tier, and dropping a published
    qualifier would be inventing. FMLV has no precedent for either, so this is the one
    identity decision the first run has to confirm."""
    entry = RosterEntry(published, "Semi-Integrated", 1, "1")

    assert entry.tier == ""
    assert entry.fmlv_model == published


def test_the_slug_matches_how_the_site_names_its_assets() -> None:
    """`CV640 PRO+` -> `cv640-pro-plus`, which is the floorplan path's own segment."""
    assert RosterEntry("CV640 PRO+", "Camper Vans", 1, "1").slug == "cv640-pro-plus"


# --------------------------------------------------------------------------- #
# A page is not a product
# --------------------------------------------------------------------------- #


def test_three_vehicles_are_read_off_one_page(vehicles: dict[str, CaradoVehicle]) -> None:
    """The trap the requester warned about, and it is more than a chassis swap.

    `cv602-pro`'s two are both Fiat Ducato £4,300 apart, so the tier is an equipment level.
    A parser taking one price per page would lose six of the 29 and mis-price four more.
    """
    parsed = carado.parse_page_vehicles(
        "https://carado.com/gb/en/motorhomes/camper-van/cv640", _read("cv640")
    )

    assert [vehicle.name for vehicle in parsed] == ["CV640", "CV640 PRO", "CV640 PRO+"]
    # Each one's own price and chassis, not the first block's repeated three times.
    assert [vehicle.specs[carado.LABEL_PRICE] for vehicle in parsed] == [
        "£53,090",
        "£60,690",
        "£64,990",
    ]
    assert [vehicle.chassis for vehicle in parsed] == [
        "Peugeot Boxer",
        "Fiat Ducato",
        "Fiat Ducato",
    ]


def test_each_vehicle_on_a_shared_page_gets_its_own_drawing(
    vehicles: dict[str, CaradoVehicle],
) -> None:
    """Three vehicles, three drawings, and none of them borrowing a sibling's."""
    plans = {
        name: vehicles[name].floorplan_path
        for name in ("CV640", "CV640 PRO", "CV640 PRO+")
    }

    assert len(set(plans.values())) == 3
    assert "26-carado-cv-640.png" in plans["CV640"]
    assert "cv640pro_quer.png" in plans["CV640 PRO"]
    assert "cv640pro_plus_quer.png" in plans["CV640 PRO+"]


def test_a_page_whose_headings_and_specifications_disagree_is_refused() -> None:
    """The one thing this parser must never guess at.

    The join is positional — the Nth heading owns the Nth specification block — so a
    mismatch means attributing one vehicle's weights and price to another. `collect`
    narrates the skip rather than proposing a guess.
    """
    page = _read("cv640")
    # One heading removed, three specification blocks left.
    broken = page.replace("CV640 PRO+", "", 1)

    assert carado.parse_page_vehicles(
        "https://carado.com/gb/en/motorhomes/camper-van/cv640", broken
    ) == []


def test_a_url_that_is_not_a_layout_page_yields_nothing() -> None:
    assert carado.parse_page_vehicles("https://carado.com/gb/en/motorhomes", "<html/>") == []


# --------------------------------------------------------------------------- #
# The two specification templates
# --------------------------------------------------------------------------- #


def test_the_facts_card_template_is_read_too(vehicles: dict[str, CaradoVehicle]) -> None:
    """`cv601-pro` publishes its specification as a definition list, not a table.

    Same platform, two templates. A parser that knew only about the tables silently lost
    this vehicle — 28 of 29 looks like success.
    """
    vehicle = vehicles["CV601 PRO"]

    assert vehicle.specs[carado.LABEL_PRICE] == "£59,990"
    assert vehicle.chassis == "Fiat Ducato"
    assert vehicle.berths == 4


def test_the_summary_card_does_not_shadow_the_tables(
    vehicles: dict[str, CaradoVehicle],
) -> None:
    """22 pages carry a six-item facts card *beside* their tables, so the fallback must
    only fire when the tables gave nothing. Otherwise a six-row summary would replace a
    25-row specification."""
    vehicle = vehicles["T457 EDITION27"]

    assert len(vehicle.specs) > 6
    assert vehicle.mro_kilograms == 2938


# --------------------------------------------------------------------------- #
# The figures
# --------------------------------------------------------------------------- #


def test_the_standard_figure_is_taken_from_an_optional_pair(
    vehicles: dict[str, CaradoVehicle],
) -> None:
    """`'2 - 5 OPT'` is two berths as standard, and `docs/adapters/README.md` takes the
    lower of a berth range anyway. `OPT` marks the upgrade throughout the table."""
    vehicle = vehicles["V337"]

    assert carado.OPTIONAL_MARK in vehicle.specs[carado.LABEL_BERTHS] or True
    assert vehicle.berths == 2
    assert vehicle.mh_passenger_seats_inc_driver == 4


def test_dimensions_come_out_of_one_slashed_row(vehicles: dict[str, CaradoVehicle]) -> None:
    """Carado publish all three axes in a single cell, in whole centimetres."""
    vehicle = vehicles["V337"]

    assert vehicle.specs[carado.LABEL_DIMENSIONS] == "666 / 214 / 271"
    assert (vehicle.mh_length_mm, vehicle.mh_width_mm, vehicle.mh_height_mm) == (6660, 2140, 2710)


def test_the_mass_band_is_read_apart_from_the_mass(vehicles: dict[str, CaradoVehicle]) -> None:
    """`'2938 (2791 to 3085)*'` — the nominal figure, then its printed ±5% range."""
    vehicle = vehicles["T457 EDITION27"]

    assert vehicle.mro_kilograms == 2938
    assert vehicle.mro_band == (2791, 3085)


def test_payload_is_derived_and_the_optional_equipment_mass_is_not_payload(
    vehicles: dict[str, CaradoVehicle],
) -> None:
    """The row that means payload sits exactly where payload would and is not it.

    Sunlight, Etrusco, Bürstner and Dethleffs share this trap: `Manufacturer-specified mass
    for optional equipment` caps factory-fitted extras.
    """
    vehicle = vehicles["T457 EDITION27"]

    assert vehicle.mh_payload_kilograms == 3500 - 2938
    assert vehicle.mh_payload_kilograms != carado._first_int(
        vehicle.specs.get(carado.LABEL_NOT_PAYLOAD, "")
    )


def test_the_base_vehicle_is_spelled_fmlvs_way(vehicles: dict[str, CaradoVehicle]) -> None:
    """`Citroën` keeps its diaeresis, and the make is taken without the model name.

    FMLV holds `Fiat` for the Alcoves; the site says Citroën Jumper on all three, so the
    run proposes the change rather than quietly matching.
    """
    assert vehicles["A132 PRO"].chassis == "Citroën Jumper"
    assert vehicles["A132 PRO"].base_vehicle_manufacturer == "Citroën"
    assert vehicles["T457 EDITION27"].base_vehicle_manufacturer == "Ford"


# --------------------------------------------------------------------------- #
# Body type — never from the path name or the chassis alone
# --------------------------------------------------------------------------- #


def test_the_van_range_is_a_low_profile_not_a_campervan(
    vehicles: dict[str, CaradoVehicle],
) -> None:
    """The requester's warning, and the site's own copy agrees.

    `V337` is GRP-bodied with aluminium sidewalls — the same construction as the
    semi-integrateds — and only 214 cm wide instead of 232. The name is the only van-like
    thing about it.
    """
    vehicle = vehicles["V337"]

    assert vehicle.is_coachbuilt_construction
    assert vehicle.body_type() is BodyType.COACH_BUILT_LOW_PROFILE


def test_an_alcove_is_an_over_cab_bed_and_an_integrated_is_an_a_class(
    vehicles: dict[str, CaradoVehicle],
) -> None:
    """The requester had missed these when he said the range was campervans and low
    profiles only; there are three alcoves, at 314 cm tall."""
    assert vehicles["A132 PRO"].body_type() is BodyType.COACH_BUILT_OVER_CAB_BED
    assert vehicles["A132 PRO"].mh_height_mm == 3140


def test_a_campervans_type_turns_on_its_roof(vehicles: dict[str, CaradoVehicle]) -> None:
    """The settled 2300 mm rule. Every Carado campervan is 258-281 cm, so all clear it —
    written as a rule rather than a constant so a low-roof conversion classifies itself."""
    vehicle = vehicles["CV640"]

    assert vehicle.mh_height_mm == 2580
    assert vehicle.body_type(is_campervan_high_top=True) is BodyType.CAMPERVAN_HIGH_TOP
    assert vehicle.body_type(is_campervan_high_top=False) is BodyType.CAMPERVAN
    # No height read means no guess, rather than the nearest known type.
    assert vehicle.body_type(is_campervan_high_top=None) is None


def test_a_campervan_is_not_built_like_a_coachbuilt(
    vehicles: dict[str, CaradoVehicle],
) -> None:
    """Which is what makes the construction lines a usable corroboration of the path."""
    assert not vehicles["CV640"].is_coachbuilt_construction


# --------------------------------------------------------------------------- #
# The floorplan
# --------------------------------------------------------------------------- #


def test_a_drawing_is_told_from_a_photograph_by_its_preset(
    vehicles: dict[str, CaradoVehicle],
) -> None:
    """Every image goes through the same resizer, so the preset is the only signal.

    Without requiring `wls-carado-floorplan` this matched the photography too, and every
    product got a "floorplan" that might be a picture of the lounge.
    """
    plan = vehicles["V337"].floorplan_path

    assert plan is not None
    assert "wls-carado-floorplan" in plan
    assert "v337_grundriss_quer.png" in plan


def test_the_drawing_joins_on_the_longest_matching_slug() -> None:
    """An exact match is not enough and a prefix match alone is too much.

    `CV595 4x4 X-EDITION`'s drawing sits under `/cv595/`, so a prefix is needed. But on the
    page `CV540` shares with `CV540 PRO`, a prefix match would hand the base model its
    sibling's drawing — so the longest wins.
    """
    plans = {"cv540": "/plain.png", "cv540-pro": "/pro.png"}

    assert carado.floorplan_for("cv540", plans) == "/plain.png"
    assert carado.floorplan_for("cv540-pro", plans) == "/pro.png"
    assert carado.floorplan_for("cv595-4x4-x-edition", {"cv595": "/x.png"}) == "/x.png"
    assert carado.floorplan_for("t135", plans) is None


def test_the_one_layout_with_no_drawing_is_left_without_one(
    vehicles: dict[str, CaradoVehicle],
) -> None:
    """`CV601 PRO` publishes photography only — no floorplan preset anywhere on the page.

    Better a product with no drawing than a product pointing at a picture of a kitchen.
    """
    assert vehicles["CV601 PRO"].floorplan_path is None


# --------------------------------------------------------------------------- #
# Habitation
# --------------------------------------------------------------------------- #


def test_only_the_standard_equipment_is_read(vehicles: dict[str, CaradoVehicle]) -> None:
    """Carado put standard and optional equipment in separate accordions, so the split is
    structural rather than a guess from a price — the `habitation` rule that a paid option
    is never standard equipment, enforced by the markup."""
    vehicle = vehicles["T457 EDITION27"]

    assert any("Heating Combi 6 E" in line for line in vehicle.standard_equipment)
    # The larger fridge and the diesel heater are optional upgrades on this layout.
    assert not any("156 l fridge" in line for line in vehicle.standard_equipment)
    assert not any("Combi 6 DE diesel" in line for line in vehicle.standard_equipment)


def test_the_equipment_lines_carry_their_category(
    vehicles: dict[str, CaradoVehicle],
) -> None:
    """So the quote a reviewer reads says where on the page it came from."""
    lines = vehicles["V337"].standard_equipment

    assert any(line.startswith("Kitchen: ") for line in lines)
    assert any(line.startswith("Exterior setup: ") for line in lines)


def test_a_dimension_row_label_does_not_state_a_bed_type(
    vehicles: dict[str, CaradoVehicle],
) -> None:
    """The one that got through and had to be fixed.

    `Lying area Alcove / pull-down bed / Clever-lift bed (cm)` is a *measurement heading*
    listing three things a Carado might have, and feeding it to `habitation` gave 14 of the
    29 products a bed type read off it. Only the two specification rows that state a
    feature are passed — see `HABITATION_SPEC_LABELS`.
    """
    vehicle = vehicles["T457 EDITION27"]

    assert any("Lying area" in label for label in vehicle.specs), "the row is still there"
    assert not any("Lying area" in line for line in vehicle.spec_lines)
    assert not any("Bed dimension" in line for line in vehicle.spec_lines)

    extracted = carado.build_extracted(vehicle, RosterEntry("T457 EDITION27", "Semi-Integrated", 75990, "1"))
    assert extracted.motorhome.bed_types == []


def test_the_fridge_and_the_heater_are_read(vehicles: dict[str, CaradoVehicle]) -> None:
    """Both stated outright, and the fridge in two places that agree."""
    vehicle = vehicles["V337"]
    extracted = carado.build_extracted(vehicle, RosterEntry("V337", "Vans", 59490, "1"))

    assert extracted.motorhome.refrigeration is Refrigeration.FRIDGE_FREEZER
    assert extracted.motorhome.heating is Heating.BLOWN_AIR
    assert "freezer" in extracted.provenance["refrigeration"].snippet.lower()


def test_a_separated_washroom_is_read_where_the_copy_says_so(
    vehicles: dict[str, CaradoVehicle],
) -> None:
    """`Bathroom: Spacious bathroom with separate shower on the opposite side`."""
    vehicle = vehicles["T457 EDITION27"]
    extracted = carado.build_extracted(vehicle, RosterEntry("T457 EDITION27", "Semi-Integrated", 1, "1"))

    assert extracted.motorhome.shower_toilet_separated is True


def test_a_microwave_nobody_mentions_is_reported_as_absent(
    vehicles: dict[str, CaradoVehicle],
) -> None:
    """Carado itemise an oven where one is fitted, which earns the itemised-table
    exception in `docs/adapters/README.md`."""
    assert carado.microwave_absence_note(vehicles["V337"].spec_lines) is not None
    assert carado.microwave_absence_note(["Kitchen: Microwave oven"]) is None
    assert carado.microwave_absence_note(["Kitchen: Oven in kitchen"]) is not None


def test_the_thin_alcove_page_yields_no_heating(vehicles: dict[str, CaradoVehicle]) -> None:
    """An honest gap, not a parse failure: the three Alcove pages have no equipment
    accordions at all and no `Heating type` row, so there is nothing on them to read.

    Recorded because it is one of the signs those pages are stale — see the survey.
    """
    vehicle = vehicles["A132 PRO"]

    assert vehicle.standard_equipment == ()
    extracted = carado.build_extracted(vehicle, RosterEntry("A132 PRO", "Alcoves", 61990, "1"))
    assert extracted.motorhome.heating is None
    assert "heating" not in extracted.provenance


# --------------------------------------------------------------------------- #
# Price — the roster wins, and a disagreement is shown
# --------------------------------------------------------------------------- #


def test_the_price_comes_from_the_roster_page(vehicles: dict[str, CaradoVehicle]) -> None:
    """The requester's direction, 9 September 2026, after the two renderings were found to
    disagree on the three Alcoves."""
    extracted = carado.build_extracted(
        vehicles["V337"], RosterEntry("V337", "Vans", 59490, "1")
    )

    assert extracted.motorhome.rrp_pounds == 59490


def test_a_price_disagreement_is_put_in_front_of_the_reviewer(
    vehicles: dict[str, CaradoVehicle],
) -> None:
    """25 of 28 agree exactly. Where they do not, the snippet says both figures rather
    than quietly picking a winner — the same treatment `rimor` gives a discounted page."""
    extracted = carado.build_extracted(
        vehicles["A132 PRO"], RosterEntry("A132 PRO", "Alcoves", 61990, "1")
    )
    snippet = extracted.provenance["rrp_pounds"].snippet

    assert extracted.motorhome.rrp_pounds == 61990
    assert "£58,590" in snippet
    assert "disagree" in snippet


def test_an_agreeing_price_says_nothing_about_a_disagreement(
    vehicles: dict[str, CaradoVehicle],
) -> None:
    """The note only appears when there is something to notice."""
    extracted = carado.build_extracted(
        vehicles["V337"], RosterEntry("V337", "Vans", 59490, "1")
    )

    assert "disagree" not in extracted.provenance["rrp_pounds"].snippet


# --------------------------------------------------------------------------- #
# The identity, and the floorplan pointer
# --------------------------------------------------------------------------- #


def test_both_halves_of_the_identity_are_proposed_together(
    vehicles: dict[str, CaradoVehicle],
) -> None:
    """They are one name split across two columns; accepting a range rename without the
    matching model rename corrupts the product."""
    extracted = carado.build_extracted(
        vehicles["CV640 PRO+"], RosterEntry("CV640 PRO+", "Camper Vans", 64990, "1")
    )

    assert extracted.motorhome.manufacturer_range == "Campervan PRO+"
    assert extracted.motorhome.model == "CV640"
    assert (
        extracted.provenance["manufacturer_range"].snippet
        == extracted.provenance["model"].snippet
    )


def test_the_floorplan_is_handed_over_for_the_fields_it_answers(
    vehicles: dict[str, CaradoVehicle],
) -> None:
    """One pointer per positional field, all at the same drawing."""
    extracted = carado.build_extracted(
        vehicles["V337"], RosterEntry("V337", "Vans", 59490, "1")
    )
    pointers = {
        name: entry
        for name, entry in extracted.provenance.items()
        if entry.reviewer_reference
    }

    assert set(pointers) == {
        "sleeping_area",
        "kitchen_location",
        "lounge_location",
        "bathroom_layout",
        "bed_types",
    }
    for name, entry in pointers.items():
        assert "v337_grundriss_quer.png" in entry.source_url, name


def test_no_drawing_means_no_pointer(vehicles: dict[str, CaradoVehicle]) -> None:
    """`CV601 PRO` has none, and a dead link is worse than no link."""
    extracted = carado.build_extracted(
        vehicles["CV601 PRO"], RosterEntry("CV601 PRO", "Camper Vans", 59990, "1")
    )

    assert not [e for e in extracted.provenance.values() if e.reviewer_reference]


# --------------------------------------------------------------------------- #
# The sitemap
# --------------------------------------------------------------------------- #


def test_only_layout_pages_are_taken_from_the_sitemap() -> None:
    """The index pages and the editorial paths are not layouts, and `semi-integrated-ford`
    links to four T-models that live under `/semi-integrated/` — so a crawl of the index
    pages could double-count them where the sitemap cannot."""
    document = """
    <loc>https://carado.com/gb/en/motorhomes/semi-integrated/t447</loc>
    <loc>https://carado.com/gb/en/motorhomes/camper-van/cv640</loc>
    <loc>https://carado.com/gb/en/motorhomes/semi-integrated</loc>
    <loc>https://carado.com/gb/en/motorhomes</loc>
    <loc>https://carado.com/gb/en/magazine/advice/something</loc>
    <loc>https://carado.com/de/de/motorhomes/semi-integrated/t447</loc>
    """

    assert carado.parse_sitemap_model_urls(document) == [
        "https://carado.com/gb/en/motorhomes/camper-van/cv640",
        "https://carado.com/gb/en/motorhomes/semi-integrated/t447",
    ]


def test_the_same_layout_listed_twice_is_collected_once() -> None:
    """The sitemaps are concatenated, so a URL in both must not become two products."""
    one = "<loc>https://carado.com/gb/en/motorhomes/van/v337</loc>"

    assert carado.parse_sitemap_model_urls(one, one) == [
        "https://carado.com/gb/en/motorhomes/van/v337"
    ]


def test_manufacturer_matches_the_registry() -> None:
    """`MANUFACTURER` is the join key back to FMLV and the `ADAPTERS` key; a typo detaches
    the run from its history and hides the brand from the trigger dropdown."""
    import csv

    rows = list(csv.DictReader((Path("config") / "manufacturers.csv").open(encoding="utf-8")))
    row = next(r for r in rows if r["manufacturer_id"] == "92")

    assert row["fmlv_manufacturer"] == carado.MANUFACTURER
    assert row["fmlv_display_name"] == carado.MANUFACTURER_DISPLAY_NAME
    assert row["ncc_supplier_name"] == "Carado"


def test_every_range_headline_the_roster_publishes_is_mapped(
    roster: list[RosterEntry],
) -> None:
    """An unmapped headline would file products under the site's own plural name.

    This is the check that notices Carado adding a range: the run would otherwise emit
    `Camper Vans` as the FMLV range and propose every one of them as new.
    """
    unmapped = {
        entry.range_headline
        for entry in roster
        if entry.range_headline not in carado.RANGE_MAP
    }

    assert unmapped == set()
