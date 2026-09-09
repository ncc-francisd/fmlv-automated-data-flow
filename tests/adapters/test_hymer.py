"""Hymer's parsing, against real captured range pages.

No network. Each `hymer_*.html` fixture is a GB range page sliced in document order,
keeping only what the adapter reads: every heading, every table sharing the modal class,
and the floorplan paths. Order is preserved deliberately — the parser attributes a
specification to the nearest heading above it, so positions carry meaning.

Five pages were kept, each for a reason:

* `exsis_t` — the headings sit at `h4` with an `h3` teaser pair above them, so the *first*
  occurrence of a layout's name is the wrong one to anchor on.
* `b_ml_i` — each layout's specification rendered twice, and a drawing whose filename ends
  `_bis_2026` rather than in the layout's code.
* `venture_s` — a layout with **no numeric code at all**.
* `yellowstone` — five layouts but one numbered drawing, the other plans belonging to
  sibling models the page also shows.
* `grand_canyon_s` — `Roof type: Sleeping roof (○)`, which decides a campervan's body type.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters import hymer
from src.adapters.hymer import HymerLayout
from src.product_model.enums import BodyType, Heating, Refrigeration

FIXTURES = Path(__file__).parent / "fixtures"

#: (fixture, the `--range` label the page is read under).
CAPTURED: tuple[tuple[str, str], ...] = (
    ("exsis_t", "Exsis-t"),
    ("b_ml_i", "B-ML I"),
    ("venture_s", "Venture S"),
    ("yellowstone", "Yellowstone"),
    ("grand_canyon_s", "Grand Canyon S"),
)

#: What the GB site publishes, counted off the pages on 9 September 2026. FMLV still holds
#: 42, so the difference is withdrawals rather than pages this missed — see the survey.
EXPECTED_UK_LAYOUTS = 25


def _read(name: str) -> str:
    return (FIXTURES / f"hymer_{name}.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def layouts() -> dict[str, HymerLayout]:
    """Every captured layout, keyed on its title."""
    found: dict[str, HymerLayout] = {}
    for name, label in CAPTURED:
        parsed = hymer.parse_layouts(_read(name), label)
        assert parsed, f"{name} produced no layouts"
        for layout in parsed:
            found[layout.title] = layout
    return found


# --------------------------------------------------------------------------- #
# Attributing a specification to a layout
# --------------------------------------------------------------------------- #


def test_the_teaser_heading_is_not_mistaken_for_the_real_one() -> None:
    """On the Exsis-t page a layout's name appears twice — as a teaser near the top and
    again above its specification. Anchoring on the first gives a region with no tables in
    it, and the layout comes out empty."""
    parsed = hymer.parse_layouts(_read("exsis_t"), "Exsis-t")

    assert [x.code for x in parsed] == ["474", "580"]
    assert parsed[0].rrp_pounds == 96290
    assert parsed[0].mro_kilograms == 2824


def test_a_specification_rendered_twice_yields_one_layout() -> None:
    """The B-ML page prints each layout's tables twice. Duplicates re-state the same
    values inside the layout's own region, so nothing has to be deduplicated — but two
    layouts must not become four."""
    parsed = hymer.parse_layouts(_read("b_ml_i"), "B-ML I")

    assert [x.code for x in parsed] == ["780", "880"]
    assert parsed[0].rrp_pounds == 150570
    assert parsed[1].rrp_pounds == 161470


def test_a_layout_with_no_number_is_still_a_layout() -> None:
    """`Hymer Venture S`. The first sweep of this site used a pattern requiring digits and
    found 24 layouts instead of 25."""
    parsed = hymer.parse_layouts(_read("venture_s"), "Venture S")

    assert [x.code for x in parsed] == ["S"]
    assert parsed[0].fmlv_range == "Venture"
    assert parsed[0].fmlv_model == "S"


@pytest.mark.parametrize(
    ("heading", "label", "expected"),
    [
        ("Hymer Exsis-t 474", "Exsis-t", "474"),
        ("Hymer B-ML I 780", "B-ML I", "780"),
        ("Hymer Venture S", "Venture S", "S"),
        ("Hymer Grand Canyon S 600", "Grand Canyon S", "600"),
        ("Design your vehicle in our configurator", "Exsis-t", None),
        ("Hymer Exsis-t", "B-ML I", None),
    ],
)
def test_a_heading_is_read_as_a_layout_only_when_it_names_one(
    heading: str, label: str, expected: str | None
) -> None:
    assert hymer.layout_name(heading, label) == expected


def test_a_page_with_no_layout_heading_yields_nothing() -> None:
    """The category pages — `winterized-motorhomes` and its kin — must produce no products."""
    assert hymer.parse_layouts("<h2>Luxury motorhomes</h2>", "Exsis-t") == []


# --------------------------------------------------------------------------- #
# Identity — FMLV's conventions differ per range
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("label", "code", "expected_range", "expected_model"),
    [
        ("B-ML I", "780", "B-Class MasterLine", "I 780"),
        ("B-ML T", "780", "B-Class MasterLine", "T 780"),
        ("B-MC I", "600", "B-Class ModernComfort I", "I600"),
        ("B-MC T", "680", "B-Class ModernComfort T", "T680"),
        ("Exsis-t", "474", "Exsis-T", "474"),
        ("Venture S", "S", "Venture", "S"),
        ("Yellowstone", "640", "Yellowstone", "640"),
    ],
)
def test_the_model_template_is_per_range(
    label: str, code: str, expected_range: str, expected_model: str
) -> None:
    """FMLV is inconsistent about where the body letter sits and whether it is spaced —
    `B-Class MasterLine` / `I 780` against `B-Class ModernComfort I` / `I600`. Checked
    against the real export, so the template is per range rather than a rule."""
    layout = HymerLayout(range_label=label, code=code, title="")

    assert layout.fmlv_range == expected_range
    assert layout.fmlv_model == expected_model


def test_every_configured_range_has_a_mapping() -> None:
    """A range page added to `DEFAULT_RANGES` without a `RANGE_MAP` entry would emit the
    site's own label as the FMLV range and propose every layout on it as new."""
    assert {label for _path, label in hymer.DEFAULT_RANGES} == set(hymer.RANGE_MAP)


def test_both_halves_of_the_identity_are_proposed_together(
    layouts: dict[str, HymerLayout],
) -> None:
    extracted = hymer.build_extracted(layouts["Hymer B-ML I 780"])

    assert extracted.motorhome.manufacturer_range == "B-Class MasterLine"
    assert extracted.motorhome.model == "I 780"
    assert (
        extracted.provenance["manufacturer_range"].snippet
        == extracted.provenance["model"].snippet
    )


# --------------------------------------------------------------------------- #
# The figures
# --------------------------------------------------------------------------- #


def test_labels_carrying_a_non_breaking_space_are_still_found(
    layouts: dict[str, HymerLayout],
) -> None:
    """Hymer put `&nbsp;` inside their labels — `Price&nbsp;&nbsp;` and `Mass in running
    order (-/+ 5%)&nbsp;(kg)*` — so a lookup on the printed label misses without unescaping.
    None of the sibling EHG sites does this."""
    layout = layouts["Hymer Exsis-t 474"]

    assert hymer.LABEL_PRICE in layout.specs
    assert hymer.LABEL_MRO in layout.specs
    assert layout.rrp_pounds == 96290


def test_dimensions_come_out_of_one_slashed_row(layouts: dict[str, HymerLayout]) -> None:
    layout = layouts["Hymer Exsis-t 474"]

    assert layout.specs[hymer.LABEL_DIMENSIONS] == "659 / 222 / 279"
    assert (layout.mh_length_mm, layout.mh_width_mm, layout.mh_height_mm) == (6590, 2220, 2790)


def test_the_mass_band_is_read_apart_from_the_mass(layouts: dict[str, HymerLayout]) -> None:
    layout = layouts["Hymer Exsis-t 474"]

    assert layout.mro_kilograms == 2824
    assert layout.mro_band == (2683, 2965)


def test_payload_is_derived_and_the_optional_equipment_mass_is_not_payload(
    layouts: dict[str, HymerLayout],
) -> None:
    layout = layouts["Hymer Exsis-t 474"]

    assert layout.mh_payload_kilograms == 3500 - 2824
    assert layout.specs[hymer.LABEL_NOT_PAYLOAD] == "342"


def test_the_lower_berth_figure_is_the_standard_one(
    layouts: dict[str, HymerLayout],
) -> None:
    layout = layouts["Hymer Exsis-t 474"]

    assert hymer.OPTIONAL_MARK in (layout.berths_published or "")
    assert layout.berths == 2


def test_the_base_vehicle_is_spelled_fmlvs_way(layouts: dict[str, HymerLayout]) -> None:
    assert layouts["Hymer Exsis-t 474"].base_vehicle_manufacturer == "Fiat"
    assert layouts["Hymer B-ML I 780"].base_vehicle_manufacturer == "Mercedes"


def test_the_garage_is_answered_from_its_published_opening(
    layouts: dict[str, HymerLayout],
) -> None:
    assert layouts["Hymer Exsis-t 474"].rear_garage is True
    assert HymerLayout("Exsis-t", "474", "").rear_garage is False


# --------------------------------------------------------------------------- #
# Body type
# --------------------------------------------------------------------------- #


def test_a_motorhomes_body_comes_from_its_range(layouts: dict[str, HymerLayout]) -> None:
    """Hymer's motorhome ranges are cleanly one body each — the `I` ranges are A-class and
    the `T` ranges low profile — so the range decides it and no height rule is needed."""
    assert layouts["Hymer B-ML I 780"].body_type is BodyType.A_CLASS
    assert layouts["Hymer Venture S"].body_type is BodyType.COACH_BUILT_LOW_PROFILE


def test_an_optional_sleeping_roof_does_not_make_an_elevating_roof_body(
    layouts: dict[str, HymerLayout],
) -> None:
    """Both campervan ranges publish `Roof type: Sleeping roof (○)`, and the circle marks a
    paid upgrade. The settled rule is that an optional rising roof does not change what the
    vehicle is, so these are plain high tops.

    **FMLV currently disagrees on the Grand Canyon S**, holding it as an elevating-roof
    body, so the run proposes a correction there. Flagged in the survey.
    """
    layout = layouts["Hymer Grand Canyon S 600"]

    assert hymer.OPTIONAL_MARK in (layout.roof_published or "")
    assert not layout.has_standard_elevating_roof
    assert layout.body_type is BodyType.CAMPERVAN_HIGH_TOP


def test_a_standard_rising_roof_would_change_the_body() -> None:
    """Written as a rule so a future standard-fit roof classifies itself."""
    standard = HymerLayout(
        "Yellowstone", "540", "",
        {hymer.LABEL_ROOF: "Sleeping roof", hymer.LABEL_DIMENSIONS: "541 / 208 / 260"},
    )
    optional = HymerLayout(
        "Yellowstone", "540", "",
        {hymer.LABEL_ROOF: "Sleeping roof (○)", hymer.LABEL_DIMENSIONS: "541 / 208 / 260"},
    )

    assert standard.body_type is BodyType.CAMPERVAN_HIGH_TOP_ELEVATING_ROOF
    assert optional.body_type is BodyType.CAMPERVAN_HIGH_TOP


def test_a_campervan_with_no_height_gets_no_body_type() -> None:
    assert HymerLayout("Yellowstone", "540", "", {hymer.LABEL_ROOF: "Fix roof"}).body_type is None


# --------------------------------------------------------------------------- #
# Floorplans
# --------------------------------------------------------------------------- #


def test_the_drawing_joins_on_the_code_as_a_token_not_a_suffix() -> None:
    """Hymer name these three ways on three pages, and a rule anchored to the end of the
    stem finds only the first."""
    page = (
        '<img src="/a/image-thumb__1__wls-floorplan-large/hymer-exsis-t-474.jpg">'
        '<img src="/a/image-thumb__1__wls-floorplan-large/hymer-redwood-600-hoch.png">'
        '<img src="/a/image-thumb__1__wls-floorplan-large/hymer-b-ml-i-780_bis_2026.png">'
    )

    assert "hymer-exsis-t-474" in (hymer.floorplan_for("474", page) or "")
    assert "hymer-redwood-600-hoch" in (hymer.floorplan_for("600", page) or "")
    assert "hymer-b-ml-i-780_bis_2026" in (hymer.floorplan_for("780", page) or "")


def test_a_partial_number_is_not_a_match() -> None:
    """`600` must not take `6001`'s drawing, which a substring test would allow."""
    page = '<img src="/a/image-thumb__1__wls-floorplan-large/hymer-x-6001.png">'

    assert hymer.floorplan_for("600", page) is None


def test_the_photography_is_not_mistaken_for_a_drawing() -> None:
    """Every image goes through the same resizer, so the preset is the only signal — the
    Carado lesson. Without it a product gets a picture of the lounge behind a link labelled
    "Floorplan"."""
    page = '<img src="/a/image-thumb__1__wls-stage-large/hymer-exsis-t-474.jpg">'

    assert hymer.floorplan_for("474", page) is None


def test_a_layout_with_no_drawing_of_its_own_gets_none(
    layouts: dict[str, HymerLayout],
) -> None:
    """The Yellowstone page shows five layouts but only `601` has a numbered plan; the rest
    of its drawings belong to sibling models the page also displays. Better no drawing than
    a sibling's — the Laika lesson.
    """
    assert layouts["Hymer Yellowstone 601"].floorplan_path is not None
    for code in ("540", "600", "602", "640"):
        assert layouts[f"Hymer Yellowstone {code}"].floorplan_path is None


def test_no_drawing_means_no_pointer(layouts: dict[str, HymerLayout]) -> None:
    extracted = hymer.build_extracted(layouts["Hymer Yellowstone 540"])

    assert not [e for e in extracted.provenance.values() if e.reviewer_reference]


# --------------------------------------------------------------------------- #
# Habitation
# --------------------------------------------------------------------------- #


def test_the_heating_and_the_fridge_are_read(layouts: dict[str, HymerLayout]) -> None:
    extracted = hymer.build_extracted(layouts["Hymer Exsis-t 474"]).motorhome

    assert extracted.heating is Heating.BLOWN_AIR
    assert extracted.refrigeration is Refrigeration.FRIDGE_FREEZER


def test_a_bed_dimension_row_does_not_state_a_bed_type(
    layouts: dict[str, HymerLayout],
) -> None:
    """The Carado lesson: a measurement heading enumerates the beds a vehicle might have."""
    layout = layouts["Hymer Exsis-t 474"]

    assert any("Bed dimension" in label for label in layout.specs)
    assert not any("Bed dimension" in line for line in layout.spec_lines)
    assert hymer.build_extracted(layout).motorhome.bed_types == []


def test_a_microwave_nobody_mentions_is_reported_as_absent(
    layouts: dict[str, HymerLayout],
) -> None:
    extracted = hymer.build_extracted(layouts["Hymer Exsis-t 474"])

    assert extracted.motorhome.microwave is False
    assert "microwave" in extracted.provenance["microwave"].snippet.lower()


# --------------------------------------------------------------------------- #
# The self-check
# --------------------------------------------------------------------------- #


def test_the_printed_band_really_is_five_per_cent(layouts: dict[str, HymerLayout]) -> None:
    for title, layout in layouts.items():
        assert hymer._reconciles(layout), title


def test_a_band_that_is_not_five_per_cent_is_refused() -> None:
    layout = HymerLayout("Exsis-t", "474", "", {hymer.LABEL_MRO: "2824 (100 - 9000)*"})

    assert not hymer._reconciles(layout)


# --------------------------------------------------------------------------- #
# Wiring
# --------------------------------------------------------------------------- #


def test_manufacturer_matches_the_registry() -> None:
    """`HYMER` in capitals is the export's string and the `ADAPTERS` key; `Hymer` is only
    the display name and the NCC supplier label."""
    import csv

    rows = list(csv.DictReader((Path("config") / "manufacturers.csv").open(encoding="utf-8")))
    row = next(r for r in rows if r["manufacturer_id"] == "86")

    assert row["fmlv_manufacturer"] == hymer.MANUFACTURER == "HYMER"
    assert row["fmlv_display_name"] == hymer.MANUFACTURER_DISPLAY_NAME == "Hymer"
    assert row["ncc_supplier_name"] == "Hymer"


def test_the_uk_roster_is_the_number_the_survey_measured() -> None:
    """Eleven range pages, and the five captured here account for twelve of the 25. The
    figure is asserted so a page that stops publishing layouts is noticed."""
    captured = sum(
        len(hymer.parse_layouts(_read(name), label)) for name, label in CAPTURED
    )

    assert captured == 12
    assert len(hymer.DEFAULT_RANGES) == 11
