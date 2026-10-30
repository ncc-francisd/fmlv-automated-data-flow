"""Tests for the Globe-Traveller adapter's pure parsing functions, against real pages.

Fixtures are real pages fetched 30 October 2026 with `<script>` and `<style>` removed —
see `docs/adapters/globe-traveller.md`. The index plus four of the twelve model pages,
chosen because each carries something the others do not:

* **Explorer X** — the plain case: Fiat, `2(3)` seats, two berths, a price from the UK
  list and no mass in running order anywhere.
* **Pathfinder Z** — `4(3)` seats and `2+2` berths, the two notations that are read the
  opposite way round from each other and that a berths-rule reflex gets wrong.
* **Falcon Z** — the VW, and the only model in the range with no 3 500 kg plate: its
  `Permissible Max. Mass (PMM)` is 3 820. It has a mass in running order and no price,
  which is the mirror image of every Fiat model.
* **Explorer Z EVO** — a separate shower rather than an integrated one, and a layout
  drawing named after a different model entirely.

No network here.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.adapters import adapter_for, globe_traveller
from src.adapters.globe_traveller import (
    EXPECTED_PRODUCTS,
    FALCON_MRO_KILOGRAMS,
    HIGH_TOP_ABOVE_MM,
    SPEC_LABELS,
    UK_PRICES,
    GlobeTravellerProduct,
    _build_extracted_motorhome,
    _reconciles,
    berths_from,
    find_model_urls,
    habitation_lines,
    layout_filename_warning,
    layout_images,
    measure,
    parse_model_page,
    seats_from,
    spec_cells,
    spec_rows,
)
from src.product_model.enums import BodyType, Refrigeration
from src.vehicle_class import VehicleClass

FIXTURES = Path(__file__).parent / "fixtures"

#: (fixture, series segment, slug, FMLV range) for the four model pages captured.
PAGES: dict[str, tuple[str, str, str]] = {
    "globe_traveller_explorer_x.html": ("explorer-series", "explorer-x", "Explorer"),
    "globe_traveller_explorer_z_evo.html": (
        "explorer-series",
        "explorer-z-evo",
        "Explorer",
    ),
    "globe_traveller_falcon_z.html": ("falcon-series", "falcon-z", "Falcon"),
    "globe_traveller_pathfinder_z.html": (
        "pathfinder-series",
        "pathfinder-z",
        "Pathfinder",
    ),
}


def page(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def product(name: str) -> GlobeTravellerProduct:
    series, slug, fmlv_range = PAGES[name]
    parsed = parse_model_page(page(name), series, slug, fmlv_range)
    assert parsed is not None, f"{name} did not parse"
    return parsed


# --- The roster ----------------------------------------------------------------------


def test_the_index_lists_exactly_the_twelve_models() -> None:
    """Twelve, which is the website's own count and the one the price list implies."""
    found = find_model_urls(page("globe_traveller_models_index.html"))
    assert len(found) == EXPECTED_PRODUCTS
    assert [slug for _url, _series, slug in found] == [
        "explorer-x",
        "explorer-xs",
        "explorer-z",
        "explorer-z-evo",
        "falcon-xs",
        "falcon-ys",
        "falcon-z",
        "pathfinder-x",
        "pathfinder-z",
        "voyager-x",
        "voyager-xs",
        "voyager-z",
    ]


def test_a_slug_linked_more_than_once_is_counted_once() -> None:
    """The index links each card once; a model page repeats its own URL several times.

    The same regex runs over whatever it is given, so a repeated link must not double a
    model — and document order has to survive the deduplication.
    """
    doubled = (
        '<a href="/models/explorer-series/explorer-x/">'
        '<a href="/models/falcon-series/falcon-z/">'
        '<a href="/models/explorer-series/explorer-x/">'
    )
    assert [slug for _url, _series, slug in find_model_urls(doubled)] == [
        "explorer-x",
        "falcon-z",
    ]


def test_the_two_bike_versions_are_not_on_the_site_at_all() -> None:
    """They are priced in the UK list, and they are options rather than models.

    The catalogue says so — *"The Explorer Z and Pathfinder Z can be ordered in Bike
    Version"* — and the uplift is £347 on both, which is one option at one price. If
    Globe-Traveller ever give them pages of their own this test fails, which is the
    moment to re-open the question rather than let two products appear unremarked.
    """
    slugs = {slug for _u, _s, slug in find_model_urls(page("globe_traveller_models_index.html"))}
    assert not any("bike" in slug for slug in slugs)
    assert not any("Bike" in key[1] for key in UK_PRICES)


# --- The specification table ---------------------------------------------------------


@pytest.mark.parametrize("name", sorted(PAGES))
def test_every_page_yields_the_whole_label_set(name: str) -> None:
    """All twenty-one labels, on all four pages. The table is identical across the range."""
    rows = spec_rows(spec_cells(page(name)))
    assert set(rows) == set(SPEC_LABELS)


def test_the_footer_navigation_is_outside_the_table() -> None:
    """The footer re-uses the same span class and lists all four series as headings.

    Unbounded, "Models" would be read as a label and the four series names would look
    like values — so the cells stop where the footer starts.
    """
    cells = spec_cells(page("globe_traveller_explorer_x.html"))
    assert cells[0] == "Model Series"
    assert "Models" not in cells
    assert "Falcon Series" not in cells


def test_the_extended_pmm_row_is_skipped_without_disturbing_its_neighbours() -> None:
    """Its six ragged cells sit between the PMM and the dimensions and are not read.

    `Extended PMM` arrives as `(*Fiat only)`, `3820`, `or`, `4200`, `kg` — the optional
    heavier plates, which the base-vehicle rule does not record. What matters is that
    skipping them leaves `Permissible Max. Mass (PMM)` and `Lenght` intact either side.
    """
    cells = spec_cells(page("globe_traveller_explorer_x.html"))
    assert "Extended PMM" in cells
    assert "4200" in cells
    rows = spec_rows(cells)
    assert "Extended PMM" not in rows
    assert rows["Permissible Max. Mass (PMM)"] == "3500 kg"
    assert rows["Lenght"] == "636 cm"


def test_their_spelling_of_length_is_not_corrected() -> None:
    """`Lenght` is what the page says, so it is what the label set must contain."""
    assert "Lenght" in SPEC_LABELS
    assert "Length" not in SPEC_LABELS


# --- Seats, which are the trap -------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [("2(3)", (2, 3)), ("4(3)", (4, 3)), ("2", (2, None)), ("4 (3)", (4, 3))],
)
def test_the_figure_outside_the_brackets_is_the_fitment(
    value: str, expected: tuple[int, int | None]
) -> None:
    """Both directions. `2(3)` is two with a third offered; `4(3)` is four with three.

    The catalogue settles it in prose — *"Four travel seats are standard, while an
    optional three seat configuration provides more room in the living area"* — so the
    bracket is the option whether it is the larger figure or the smaller.
    """
    assert seats_from(value) == expected


def test_the_lower_figure_rule_is_not_applied_to_seats() -> None:
    """Taking the lower would record three seats on the Pathfinder, against a stated four.

    This is the README's own warning made concrete: the berth-range rule is safe because
    that row is labelled `standard / max`, and it does not transfer here by analogy.
    """
    pathfinder = product("globe_traveller_pathfinder_z.html")
    assert pathfinder.mh_passenger_seats_inc_driver == 4
    assert pathfinder.seats_optional == 3
    assert pathfinder.mh_passenger_seats_inc_driver != min(4, 3)


def test_a_seats_cell_that_is_not_a_number_records_nothing() -> None:
    """A row that changes shape blanks the field rather than guessing at it."""
    assert seats_from("2 or 3 depending on layout") == (None, None)
    assert seats_from("") == (None, None)


# --- Berths --------------------------------------------------------------------------


def test_two_plus_two_is_four_berths() -> None:
    """A sum, not a range: the second pair is a bed the layout has.

    The page lists an `Additional bed` with a size where the two-berth models read
    `N/A`, and the catalogue describes it as part of the layout. The berth-range rule
    takes the lower figure where the upper needs options; this upper does not.
    """
    pathfinder = product("globe_traveller_pathfinder_z.html")
    assert pathfinder.berths == 4
    assert pathfinder.additional_bed == "187 cm x 134 cm"


def test_a_plain_berth_count_is_itself() -> None:
    explorer = product("globe_traveller_explorer_x.html")
    assert explorer.berths == 2
    assert explorer.additional_bed == "N/A"


@pytest.mark.parametrize("value", ["", "2-4", "up to 4", "N/A"])
def test_a_berths_cell_that_is_not_a_sum_records_nothing(value: str) -> None:
    """`2-4` especially: a range is not this notation and must not be read as one."""
    assert berths_from(value) is None


# --- Measurements --------------------------------------------------------------------


def test_centimetres_become_millimetres() -> None:
    assert measure("636 cm", "cm") == 6360
    assert measure("3500 kg", "kg") == 3500
    assert measure("90 l", "l") == 90


def test_a_figure_in_the_wrong_unit_is_refused() -> None:
    """A row restated as `6.36 m` would otherwise be recorded as a 6mm vehicle.

    Refusing it blanks the field, which reaches a reviewer as a gap beside FMLV's own
    figure rather than as a plausible wrong number.
    """
    assert measure("6.36 m", "cm") is None
    assert measure("3.5 t", "kg") is None
    assert measure("", "cm") is None


# --- One whole product ---------------------------------------------------------------


def test_the_explorer_x_reads_as_published() -> None:
    explorer = product("globe_traveller_explorer_x.html")
    assert (explorer.manufacturer_range, explorer.model) == ("Explorer", "X")
    assert explorer.mh_length_mm == 6360
    assert explorer.mh_width_mm == 2060
    assert explorer.mh_height_mm == 2800
    assert explorer.internal_height_mm == 1950
    assert explorer.mtplm_kilograms == 3500
    assert explorer.base_vehicle == "Fiat"
    assert explorer.body_type is BodyType.CAMPERVAN_HIGH_TOP


def test_the_model_name_drops_the_series_it_repeats() -> None:
    """The page's Model row says `Explorer Z EVO`; the range already says `Explorer`.

    Left alone, the display name would read "Globe-Traveller Explorer Explorer Z EVO".
    """
    evo = product("globe_traveller_explorer_z_evo.html")
    assert evo.published_model == "Explorer Z EVO"
    assert evo.model == "Z EVO"
    assert evo.manufacturer_range == "Explorer"


def test_the_falcon_is_a_vw_and_not_a_volkswagen() -> None:
    """The page says `Volkswagen`; FMLV's base-vehicle column says `VW`.

    The abbreviated form is the base vehicle and the full form is the manufacturer, and
    `fmlv_base_vehicle` deliberately does not map one onto the other — so the adapter
    translates the brand's own word before handing it over.
    """
    falcon = product("globe_traveller_falcon_z.html")
    assert falcon.base_vehicle_published == "Volkswagen"
    assert falcon.base_vehicle == "VW"


def test_the_fiat_peugeot_pair_is_one_uk_product() -> None:
    """Both EU chassis are named on the page; only the Fiat is sold here.

    The UK price list is headed `Fiat Ducato … RHD` and carries no Peugeot table, so the
    settled "a different base vehicle is a different product" rule does not double the
    roster — it never arises.
    """
    explorer = product("globe_traveller_explorer_x.html")
    assert explorer.base_vehicle_published == "Fiat/Peugeot"
    assert explorer.base_vehicle == "Fiat"


def test_the_falcon_z_has_no_three_and_a_half_tonne_plate() -> None:
    """3 820 kg where every other model is 3 500 — a C1 vehicle, the only one here."""
    falcon = product("globe_traveller_falcon_z.html")
    assert falcon.mtplm_kilograms == 3820


def test_every_model_is_a_high_top() -> None:
    """280–300cm against a 230cm threshold, and no elevating roof is offered anywhere."""
    for name in PAGES:
        parsed = product(name)
        assert parsed.mh_height_mm is not None
        assert parsed.mh_height_mm > HIGH_TOP_ABOVE_MM
        assert parsed.body_type is BodyType.CAMPERVAN_HIGH_TOP


# --- The two gaps, which are the point -----------------------------------------------


def test_a_fiat_model_has_a_price_and_no_mass_in_running_order() -> None:
    """The UK price list covers it; neither document publishes its mass.

    The per-series figure printed beside it is footnoted "the heaviest model variant in
    the series", which is a sibling's mass — so nothing is recorded rather than that.
    """
    explorer = product("globe_traveller_explorer_x.html")
    assert explorer.rrp_pounds == 95_671
    assert explorer.mro_kilograms is None
    assert explorer.mh_payload_kilograms is None


def test_a_falcon_has_a_mass_in_running_order_and_no_price() -> None:
    """The mirror image. The price list is titled "Voyager | Pathfinder | Explorer"."""
    falcon = product("globe_traveller_falcon_z.html")
    assert falcon.rrp_pounds is None
    assert falcon.mro_kilograms == 3300
    assert falcon.mh_payload_kilograms == 520


def test_no_model_has_both_a_price_and_a_mass() -> None:
    """Which is why none of the twelve is uploadable until the brand answers.

    The two documents cover opposite halves of the range. When this test starts failing,
    something has been supplied and the gap has closed.
    """
    for key in UK_PRICES:
        assert key[0] != "Falcon"
    assert set(FALCON_MRO_KILOGRAMS) == {"XS", "YS", "Z"}


def test_the_per_series_mass_is_nowhere_in_the_constants() -> None:
    """3 060, 3 160 and 3 170 are a sibling's figure and must not be spread.

    This is the Airstream unit-plate mistake in a different costume, and the only defence
    against it is that the numbers never enter the code.
    """
    assert 3060 not in FALCON_MRO_KILOGRAMS.values()
    assert 3160 not in FALCON_MRO_KILOGRAMS.values()
    assert 3170 not in FALCON_MRO_KILOGRAMS.values()


# --- The self-check ------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(PAGES))
def test_every_captured_page_identifies_itself_correctly(name: str) -> None:
    assert _reconciles(product(name)) == (True, "")


def test_a_page_served_for_another_model_is_caught() -> None:
    """The URL said `explorer-x`; the table says something else.

    With no arithmetic available, this agreement between the roster's URL and the page's
    own rows is the whole self-check.
    """
    wrong = replace(product("globe_traveller_explorer_x.html"), model="Z", published_model="Explorer Z")
    ok, why = _reconciles(wrong)
    assert not ok
    assert "explorer-x" in why


def test_a_page_from_the_wrong_series_is_caught() -> None:
    wrong = replace(
        product("globe_traveller_explorer_x.html"), published_series="Voyager Series"
    )
    ok, why = _reconciles(wrong)
    assert not ok
    assert "Voyager Series" in why


def test_an_internal_height_above_the_overall_height_is_caught() -> None:
    """The two rows sit next to each other, so reading them the wrong way round is easy."""
    swapped = replace(
        product("globe_traveller_explorer_x.html"),
        mh_height_mm=1950,
        internal_height_mm=2800,
    )
    ok, why = _reconciles(swapped)
    assert not ok
    assert "the wrong way round" in why


def test_a_page_missing_a_required_label_is_not_a_product() -> None:
    """A table that has changed shape is dropped rather than half-read."""
    broken = page("globe_traveller_explorer_x.html").replace("No. of berths", "Berths")
    assert parse_model_page(broken, "explorer-series", "explorer-x", "Explorer") is None


# --- Layout drawings -----------------------------------------------------------------


def test_the_drawing_is_taken_from_the_page_not_matched_by_name() -> None:
    """`explorer-z-evo` carries one image called `voyager_z_layout-3.png`.

    Matched by filename it would have no drawing at all; taken from the page it has the
    one Globe-Traveller publish for it, with a warning attached.
    """
    images = layout_images(page("globe_traveller_explorer_z_evo.html"))
    assert len(images) == 1
    assert images[0].endswith("voyager_z_layout-3.png")


def test_a_drawing_named_after_another_model_warns() -> None:
    evo = product("globe_traveller_explorer_z_evo.html")
    warning = layout_filename_warning(
        evo, layout_images(page("globe_traveller_explorer_z_evo.html"))
    )
    assert warning is not None
    assert "voyager_z_layout-3.png" in warning


def test_a_drawing_that_names_this_model_does_not_warn() -> None:
    pathfinder = product("globe_traveller_pathfinder_z.html")
    images = layout_images(page("globe_traveller_pathfinder_z.html"))
    assert images[0].endswith("pathfinder_z_layout-1.png")
    assert layout_filename_warning(pathfinder, images) is None


def test_a_shared_drawing_naming_both_models_does_not_warn() -> None:
    """`voyager_pathfinder_x_layout-1.png` serves two models that share a layout.

    It names both, so it is not evidence of a mix-up on either page.
    """
    pathfinder_x = replace(
        product("globe_traveller_pathfinder_z.html"), model="X", published_model="Pathfinder X"
    )
    shared = [
        "https://globe-traveller.eu/wp-content/uploads/2026/06/"
        "voyager_pathfinder_x_layout-1.png"
    ]
    assert layout_filename_warning(pathfinder_x, shared) is None


def test_a_single_letter_model_is_not_found_inside_its_own_range_name() -> None:
    """`explorer_z_layout-1.png` contains an `x` — in "e**x**plorer".

    Without stripping the range first, the Explorer Z's drawing would pass as the
    Explorer X's and the mix-up would go unreported.
    """
    explorer_x = product("globe_traveller_explorer_x.html")
    wrong = [
        "https://globe-traveller.eu/wp-content/uploads/2026/06/explorer_z_layout-1.png"
    ]
    assert layout_filename_warning(explorer_x, wrong) is not None


# --- Habitation findings -------------------------------------------------------------


def test_a_fridge_with_no_freezer_mentioned_is_a_fridge_freezer() -> None:
    """The settled rule: nearly all of these have a freezer compartment."""
    extracted = _build_extracted_motorhome(
        product("globe_traveller_explorer_x.html"), "https://example.invalid"
    )
    assert extracted.motorhome.refrigeration is Refrigeration.FRIDGE_FREEZER


def test_their_misspelled_separate_shower_is_still_a_separate_shower() -> None:
    """The page says `Seperate shower`, and the washroom really is divided."""
    evo = product("globe_traveller_explorer_z_evo.html")
    assert evo.bathroom == "Seperate shower"
    extracted = _build_extracted_motorhome(evo, "https://example.invalid")
    assert extracted.motorhome.shower_toilet_separated is True


def test_integrated_with_toilet_is_recorded_as_not_separated() -> None:
    """Their own opposite value, which the shared vocabulary has no phrase for.

    Left to `habitation` alone this would come back as "the page did not say", when the
    page says it plainly.
    """
    explorer = product("globe_traveller_explorer_x.html")
    assert explorer.bathroom == "Integrated with toilet"
    extracted = _build_extracted_motorhome(explorer, "https://example.invalid")
    assert extracted.motorhome.shower_toilet_separated is False
    assert "Integrated with toilet" in extracted.provenance["shower_toilet_separated"].snippet


def test_a_shape_word_is_not_a_bed_type() -> None:
    """`Bed type: French` describes a cut corner and says nothing about fixing.

    FMLV has no column for a French bed, and the only question it asks is built-in versus
    made up — which this row does not answer. So the field stays empty and the floorplan
    pointer does the asking.
    """
    explorer = product("globe_traveller_explorer_x.html")
    assert explorer.bed_type == "French"
    extracted = _build_extracted_motorhome(explorer, "https://example.invalid")
    assert extracted.motorhome.bed_types == []


def test_an_absent_additional_bed_is_not_handed_to_habitation() -> None:
    """`N/A` is the page saying there is no second bed, not a description of one."""
    lines = habitation_lines(product("globe_traveller_explorer_x.html"))
    assert not any("N/A" in line for line in lines)
    assert "Fridge 90 l" in lines


def test_no_heating_is_claimed_because_none_is_published() -> None:
    """The table has no heating row and the site has no equipment list.

    Recording nothing leaves `findings.SILENCE_MEANS` to say so, which is the honest
    answer; an absence note here would claim the page had been consulted on it.
    """
    extracted = _build_extracted_motorhome(
        product("globe_traveller_explorer_x.html"), "https://example.invalid"
    )
    assert extracted.motorhome.heating is None
    assert "heating" not in extracted.provenance


# --- Provenance ----------------------------------------------------------------------


def test_the_price_says_it_is_manually_sourced_and_why() -> None:
    extracted = _build_extracted_motorhome(
        product("globe_traveller_explorer_x.html"), "https://example.invalid"
    )
    snippet = extracted.provenance["rrp_pounds"].snippet
    assert "MANUALLY SOURCED" in snippet
    assert "on the road" in snippet.lower()
    assert "superseded" in snippet


def test_the_mass_says_it_is_manually_sourced_and_carries_the_tolerance() -> None:
    extracted = _build_extracted_motorhome(
        product("globe_traveller_falcon_z.html"), "https://example.invalid"
    )
    snippet = extracted.provenance["mro_kilograms"].snippet
    assert "MANUALLY SOURCED" in snippet
    assert "±5%" in snippet


def test_the_seats_provenance_names_the_figure_it_did_not_take() -> None:
    """A reviewer seeing `4` against a page printing `4(3)` is owed the reason."""
    extracted = _build_extracted_motorhome(
        product("globe_traveller_pathfinder_z.html"), "https://example.invalid"
    )
    snippet = extracted.provenance["mh_passenger_seats_inc_driver"].snippet
    assert "4(3)" in snippet
    assert "optional three seat configuration" in snippet


def test_both_halves_of_the_identity_carry_provenance() -> None:
    """Range and model are proposed together or not at all."""
    extracted = _build_extracted_motorhome(
        product("globe_traveller_explorer_x.html"), "https://example.invalid"
    )
    assert "manufacturer_range" in extracted.provenance
    assert "model" in extracted.provenance


def test_a_model_with_no_price_registers_none() -> None:
    """An unregistered field is neither compared nor reported — see `compare_fields`."""
    extracted = _build_extracted_motorhome(
        product("globe_traveller_falcon_z.html"), "https://example.invalid"
    )
    assert "rrp_pounds" not in extracted.provenance
    assert extracted.motorhome.rrp_pounds is None


def test_the_floorplan_is_offered_for_the_positions_nothing_settled() -> None:
    extracted = _build_extracted_motorhome(
        product("globe_traveller_pathfinder_z.html"),
        "https://example.invalid",
        "https://globe-traveller.eu/layout.png",
    )
    pointers = [
        name
        for name, entry in extracted.provenance.items()
        if entry.reviewer_reference
    ]
    assert pointers
    assert all(
        extracted.provenance[name].source_url == "https://globe-traveller.eu/layout.png"
        for name in pointers
    )


# --- Wiring --------------------------------------------------------------------------


def test_the_adapter_is_reachable_under_its_fmlv_name() -> None:
    """`GLOBE-TRAVELLER` in capitals with the hyphen and two Ls — the requester's ruling.

    The display name is the ordinary spelling, as KAKTUS/Kaktus is. Neither may be
    "corrected" into the other.
    """
    assert globe_traveller.MANUFACTURER == "GLOBE-TRAVELLER"
    assert globe_traveller.MANUFACTURER_DISPLAY_NAME == "Globe-Traveller"
    assert adapter_for("GLOBE-TRAVELLER", VehicleClass.MOTORHOME) is not None
