"""Eriba's campervans, against the real captured model page.

No network. `eriba_car.html` is `/gb/en/models/camper-vans/eriba-car` sliced in document
order, keeping only what the adapter reads: the layout headings, the `Pricing information`
markers that divide one layout's specification from the next, and every table sharing the
modal class. **All four specification blocks are kept** — the page renders each layout
twice, byte for byte, and collapsing that is the parser's job rather than the fixture's.

This is the motorhome half of a brand that also builds caravans; `test_eriba_caravan.py` is
the other. Two adapter modules, one manufacturer, keyed apart by `VehicleClass`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters import eriba
from src.adapters.eriba import EribaCampervan
from src.product_model.enums import BodyType, Heating, Refrigeration

FIXTURES = Path(__file__).parent / "fixtures"

#: What the UK model page publishes. The configurator lists a third, `ERIBA Car 601`, which
#: is not sold here — the requester confirmed his GB configurator offers only these two.
EXPECTED_LAYOUTS = ("ERIBA Car 600", "ERIBA Car 602")


def _page() -> str:
    return (FIXTURES / "eriba_car.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def layouts() -> dict[str, EribaCampervan]:
    parsed = eriba.parse_layouts(_page())
    assert parsed, "the fixture must parse"
    return {layout.title: layout for layout in parsed}


# --------------------------------------------------------------------------- #
# The page renders every layout twice
# --------------------------------------------------------------------------- #


def test_the_duplicate_rendering_is_collapsed() -> None:
    """Four blocks, two vehicles. The page prints each layout's specification twice, byte
    for byte, and a parser that trusted the count would invent two products."""
    page = _page()

    assert page.count(eriba.BLOCK_MARKER) == 4
    assert len(eriba.parse_spec_blocks(page)) == 2
    assert len(eriba.parse_layouts(page)) == 2


def test_a_block_that_differs_is_not_treated_as_a_duplicate() -> None:
    """Only an exact repeat is dropped. A block that differs is a different vehicle — or a
    parse going wrong — and either way it must survive to be counted."""
    one = {"Price": "£1", "Berths": "2"}
    other = {"Price": "£2", "Berths": "2"}

    assert [one, other] == [one, other]  # sanity: the two are not equal
    assert eriba.parse_spec_blocks(
        f"{eriba.BLOCK_MARKER}<table class='has-columns--1+'>"
        "<tr><td>Price</td><td>£1</td></tr></table>"
        f"{eriba.BLOCK_MARKER}<table class='has-columns--1+'>"
        "<tr><td>Price</td><td>£2</td></tr></table>"
    ) == [{"Price": "£1"}, {"Price": "£2"}]


def test_the_layout_headings_are_deduplicated_too(layouts: dict[str, EribaCampervan]) -> None:
    assert tuple(layouts) == EXPECTED_LAYOUTS


def test_a_page_whose_headings_and_blocks_disagree_is_refused() -> None:
    """The join is positional, so a mismatch would attribute one vehicle's price and
    weights to another. `collect` raises rather than guessing."""
    page = _page().replace("ERIBA Car 602", "ERIBA Car 602 </h2><h2> ERIBA Car 604", 1)

    assert eriba.parse_layouts(page) == []


# --------------------------------------------------------------------------- #
# The figures
# --------------------------------------------------------------------------- #


def test_the_two_layouts_are_genuinely_different_vehicles(
    layouts: dict[str, EribaCampervan],
) -> None:
    """Worth asserting because they share a price and every dimension, so a parser that
    silently read one block twice would look right."""
    six_hundred, six_oh_two = layouts["ERIBA Car 600"], layouts["ERIBA Car 602"]

    assert six_hundred.mro_kilograms == 2880
    assert six_oh_two.mro_kilograms == 2826
    assert six_hundred.mh_passenger_seats_inc_driver == 4
    assert six_oh_two.mh_passenger_seats_inc_driver == 2


def test_dimensions_come_out_of_one_slashed_row(layouts: dict[str, EribaCampervan]) -> None:
    """`'599 / 207 / 270'` in whole centimetres."""
    layout = layouts["ERIBA Car 600"]

    assert (layout.mh_length_mm, layout.mh_width_mm, layout.mh_height_mm) == (5990, 2070, 2700)


def test_the_lower_berth_figure_is_the_standard_one(
    layouts: dict[str, EribaCampervan],
) -> None:
    """`'2 - 4 (○)'` — the circle marks a paid upgrade, and FMLV holds 2."""
    layout = layouts["ERIBA Car 600"]

    assert eriba.OPTIONAL_MARK in (layout.berths_published or "")
    assert layout.berths == 2


def test_the_mass_band_is_read_apart_from_the_mass(
    layouts: dict[str, EribaCampervan],
) -> None:
    layout = layouts["ERIBA Car 600"]

    assert layout.mro_kilograms == 2880
    assert layout.mro_band == (2736, 3024)


def test_payload_is_derived_and_the_optional_equipment_mass_is_not_payload(
    layouts: dict[str, EribaCampervan],
) -> None:
    """The row that means payload sits beside the two masses and is not it — the trap
    Dethleffs, Etrusco, Bürstner, Sunlight, Carado and Niesmann all share."""
    layout = layouts["ERIBA Car 600"]

    assert layout.mh_payload_kilograms == 3500 - 2880
    assert layout.specs[eriba.LABEL_NOT_PAYLOAD] == "275"


def test_the_base_vehicle_is_spelled_fmlvs_way(layouts: dict[str, EribaCampervan]) -> None:
    """`VW Crafter 35` is FMLV's `VW`, never `Volkswagen` — the base vehicle takes the
    abbreviated form so the filters hold one name per company per role."""
    assert layouts["ERIBA Car 600"].chassis == "VW Crafter 35"
    assert layouts["ERIBA Car 600"].base_vehicle_manufacturer == "VW"


# --------------------------------------------------------------------------- #
# Body type, derived from the published roof
# --------------------------------------------------------------------------- #


def test_a_fixed_roof_above_the_threshold_is_a_high_top(
    layouts: dict[str, EribaCampervan],
) -> None:
    """The roof type is **published**, so this is derived rather than assumed. The
    requester expected high tops with no elevating roof, and the page agrees."""
    layout = layouts["ERIBA Car 600"]

    assert layout.roof_published == "Fix roof"
    assert not layout.has_standard_elevating_roof
    assert layout.body_type is BodyType.CAMPERVAN_HIGH_TOP


@pytest.mark.parametrize(
    ("roof", "height", "expected"),
    [
        ("Fix roof", "599 / 207 / 270", BodyType.CAMPERVAN_HIGH_TOP),
        ("Fix roof", "599 / 207 / 220", BodyType.CAMPERVAN),
        ("Pop-up roof", "599 / 207 / 270", BodyType.CAMPERVAN_HIGH_TOP_ELEVATING_ROOF),
        ("Pop-up roof", "599 / 207 / 220", BodyType.CAMPERVAN_ELEVATING_ROOF),
    ],
)
def test_the_roof_and_the_height_together_decide_the_type(
    roof: str, height: str, expected: BodyType
) -> None:
    """Written as a rule rather than a constant so a pop-top classifies itself if Eriba
    ever fits one as standard. An *optional* rising roof would not change what the vehicle
    is, which is why only the standard-fit row is read."""
    layout = EribaCampervan(
        model="600",
        title="ERIBA Car 600",
        specs={eriba.LABEL_ROOF: roof, eriba.LABEL_DIMENSIONS: height},
    )

    assert layout.body_type is expected


def test_no_height_means_no_body_type() -> None:
    """A blank beats the nearest known type."""
    layout = EribaCampervan("600", "ERIBA Car 600", {eriba.LABEL_ROOF: "Fix roof"})

    assert layout.body_type is None


# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #


def test_the_range_is_emitted_as_fmlv_spells_it(layouts: dict[str, EribaCampervan]) -> None:
    """FMLV holds `ERIBA CAR` in capitals, so a product reads back as "Eriba ERIBA CAR 600".

    Untidy, and deliberately not tidied: the export decides these strings, and renaming
    risks two rows for one vehicle. Raised with the requester as a data-quality question
    instead.
    """
    extracted = eriba.build_extracted(layouts["ERIBA Car 600"])

    assert extracted.motorhome.manufacturer_range == "ERIBA CAR"
    assert extracted.motorhome.model == "600"


def test_both_halves_of_the_identity_are_proposed_together(
    layouts: dict[str, EribaCampervan],
) -> None:
    extracted = eriba.build_extracted(layouts["ERIBA Car 602"])

    assert (
        extracted.provenance["manufacturer_range"].snippet
        == extracted.provenance["model"].snippet
    )


# --------------------------------------------------------------------------- #
# Habitation
# --------------------------------------------------------------------------- #


def test_the_heating_and_the_fridge_are_read(layouts: dict[str, EribaCampervan]) -> None:
    """And they differ between the two layouts, which is a check in itself: the 600 has a
    4 kW gas heater and a 90-litre fridge, the 602 a 6 kW diesel one and a 70-litre fridge."""
    six_hundred = eriba.build_extracted(layouts["ERIBA Car 600"]).motorhome
    six_oh_two = eriba.build_extracted(layouts["ERIBA Car 602"]).motorhome

    assert six_hundred.heating is Heating.BLOWN_AIR
    assert six_oh_two.heating is Heating.BLOWN_AIR
    assert six_hundred.refrigeration is Refrigeration.FRIDGE_FREEZER
    assert layouts["ERIBA Car 600"].specs[eriba.LABEL_REFRIGERATION] == "90 (7)"
    assert layouts["ERIBA Car 602"].specs[eriba.LABEL_REFRIGERATION] == "70 (7)"


def test_a_bed_dimension_row_does_not_state_a_bed_type(
    layouts: dict[str, EribaCampervan],
) -> None:
    """The lesson Carado taught: a measurement heading enumerates the beds a vehicle might
    have rather than stating what is fitted, so only the two rows that state a feature are
    passed to `habitation`."""
    layout = layouts["ERIBA Car 600"]

    assert any("Bed dimension" in label for label in layout.specs)
    assert not any("Bed dimension" in line for line in layout.spec_lines)
    assert eriba.build_extracted(layout).motorhome.bed_types == []


def test_a_microwave_nobody_mentions_is_reported_as_absent(
    layouts: dict[str, EribaCampervan],
) -> None:
    """The page itemises the kitchen down to the fridge's freezer volume and the socket
    count, so a microwave missing from it is the document saying there is none."""
    extracted = eriba.build_extracted(layouts["ERIBA Car 600"])

    assert extracted.motorhome.microwave is False
    assert "microwave" in extracted.provenance["microwave"].snippet.lower()


# --------------------------------------------------------------------------- #
# The self-check
# --------------------------------------------------------------------------- #


def test_the_printed_band_really_is_five_per_cent(layouts: dict[str, EribaCampervan]) -> None:
    for title, layout in layouts.items():
        assert eriba._reconciles(layout), title


def test_a_band_that_is_not_five_per_cent_is_refused() -> None:
    """It would mean the mass and the band came from different rows."""
    layout = EribaCampervan("600", "ERIBA Car 600", {eriba.LABEL_MRO: "2880 (1000 - 9000)*"})

    assert not eriba._reconciles(layout)


# --------------------------------------------------------------------------- #
# Wiring
# --------------------------------------------------------------------------- #


def test_the_two_eriba_adapters_are_keyed_apart() -> None:
    """One manufacturer, two product areas, two modules — never one with a flag."""
    from src.adapters import adapter_for
    from src.vehicle_class import VehicleClass

    assert adapter_for("Eriba", VehicleClass.MOTORHOME) is eriba
    assert adapter_for("Eriba", VehicleClass.CARAVAN).__name__.endswith("eriba_caravan")


def test_manufacturer_matches_the_registry() -> None:
    import csv

    rows = list(csv.DictReader((Path("config") / "manufacturers.csv").open(encoding="utf-8")))
    row = next(r for r in rows if r["manufacturer_id"] == "196")

    assert row["fmlv_manufacturer"] == eriba.MANUFACTURER
    assert row["ncc_supplier_name"] == "Eriba"
    assert "motorhome" in row["categories"], "the campervans need the motorhome category"
    assert "caravan" in row["categories"]
