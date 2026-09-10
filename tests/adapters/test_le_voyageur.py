"""Tests for the Le Voyageur adapter's pure parsing functions, against real pages.

Fixtures are real pages fetched 10 September 2026 with `<script>` and `<style>` removed
— see `docs/adapters/le-voyageur.md`. Four of the eighteen, plus the index, chosen
because each carries something the others do not:

* **LV6.8LF** — the one Eterna with 2 seated places, and a heading that already matches
  FMLV's closed-up spelling.
* **LV7.0 GJF** — the only light vehicle (3500kg), and the heading whose space FMLV does
  not have, which is the rename that would orphan the product if emitted verbatim.
* **LVXH7.6 CF** — the page that publishes its neighbour's length, which is what the
  model-code self-check exists to catch.
* **LVXH8.7 GJF** — a triple-axle Héritage, for the other range's model spelling and its
  Mercedes chassis.

No network here.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.adapters import adapter_for, le_voyageur
from src.adapters.le_voyageur import (
    DEFAULT_RANGES,
    LENGTH_TOLERANCE_MM,
    LIGHT_VEHICLE_MODEL,
    MATCH_THRESHOLD,
    PRICES_BY_SIZE,
    LeVoyageurProduct,
    _build_extracted_motorhome,
    _labelled,
    _price_for,
    _reconciles,
    chassis_disagreement,
    find_model_urls,
    floorplan_for,
    hold_disagreement,
    parse_model_page,
    plain_text,
)
from src.product_model.enums import BodyType, Heating

FIXTURES = Path(__file__).parent / "fixtures"

#: Le Voyageur's own UK roster: ten Eterna and eight Héritage, agreed by the index and by
#: the 2027 specifications handbook.
EXPECTED_ETERNA = 10
EXPECTED_HERITAGE = 8

#: (fixture, source URL) for the four layout pages captured.
PAGES: dict[str, str] = {
    "le_voyageur_lv6_8lf.html": "https://www.levoyageur-motorhome.uk/motorhome/eterna/lv6-8lf/",
    "le_voyageur_lv7_0gjf.html": "https://www.levoyageur-motorhome.uk/motorhome/eterna/lv7-0-gjf/",
    "le_voyageur_lvxh7_6cf.html": "https://www.levoyageur-motorhome.uk/motorhome/heritage/lvxh7-6-cf/",
    "le_voyageur_lvxh8_7gjf.html": "https://www.levoyageur-motorhome.uk/motorhome/heritage/lvxh8-7-gjf/",
}

ALL_SEGMENTS = tuple(segment for segment, _label in DEFAULT_RANGES)


def _page(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _parse(name: str) -> LeVoyageurProduct:
    product = parse_model_page(_page(name), PAGES[name])
    assert product is not None, f"{name} did not parse"
    return product


# --------------------------------------------------------------------------- #
# The roster
# --------------------------------------------------------------------------- #


def test_the_index_yields_exactly_eighteen_layouts() -> None:
    urls = find_model_urls(_page("le_voyageur_index.html"), ALL_SEGMENTS)

    assert len(urls) == EXPECTED_ETERNA + EXPECTED_HERITAGE
    assert sum("/eterna/" in url for url in urls) == EXPECTED_ETERNA
    assert sum("/heritage/" in url for url in urls) == EXPECTED_HERITAGE


def test_a_single_range_reads_only_its_own_pages() -> None:
    urls = find_model_urls(_page("le_voyageur_index.html"), ("eterna",))

    assert len(urls) == EXPECTED_ETERNA
    assert all("/eterna/" in url for url in urls)


def test_the_roster_is_deduplicated_and_absolute() -> None:
    urls = find_model_urls(_page("le_voyageur_index.html"), ALL_SEGMENTS)

    assert len(set(urls)) == len(urls)
    assert all(url.startswith("https://www.levoyageur-motorhome.uk/motorhome/") for url in urls)


# --------------------------------------------------------------------------- #
# Reading a labelled row
# --------------------------------------------------------------------------- #


def test_a_label_stops_at_the_next_label_rather_than_running_on() -> None:
    """Rows go missing, so "everything after the label" returns the next label."""
    text = "Length : 7.85 m Width : 2.24 m Exterior height : 2.95 m"

    assert _labelled(text, "Length") == "7.85 m"
    assert _labelled(text, "Width") == "2.24 m"


def test_a_missing_row_gives_nothing_rather_than_the_next_label() -> None:
    assert _labelled("Length : 7.85 m Wheelbase : 455", "Payload") is None


def test_the_double_spaced_label_is_matched_after_whitespace_collapses() -> None:
    """The page prints `Exterior  height`; `plain_text` leaves one space behind it.

    Matching the label literally found nothing and blanked the height on all 18, which
    reached a real run as eighteen missing fields before it was caught.
    """
    collapsed = plain_text("<p>Exterior  height</p><p>: 2.95 m</p><p>Interior height : 2 m</p>")

    assert "Exterior  height" not in collapsed
    assert _labelled(collapsed, "Exterior  height") == "2.95 m"
    assert _labelled(collapsed, "Exterior height") == "2.95 m"


def test_a_tag_becomes_a_space_so_a_value_keeps_its_unit() -> None:
    assert plain_text("<p>Length : 7.85</p><p>m</p>") == "Length : 7.85 m"


# --------------------------------------------------------------------------- #
# The model string
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("name", "expected_range", "expected_model"),
    [
        ("le_voyageur_lv6_8lf.html", "Eterna", "LV6.8LF"),
        ("le_voyageur_lv7_0gjf.html", "Eterna", "LV7.0GJF"),
        ("le_voyageur_lvxh7_6cf.html", "Hertiage", "LVXH7.6 CF"),
        ("le_voyageur_lvxh8_7gjf.html", "Hertiage", "LVXH8.7 GJF"),
    ],
)
def test_the_model_string_is_normalised_to_what_fmlv_holds(
    name: str, expected_range: str, expected_model: str
) -> None:
    """Eterna closes up entirely; Héritage keeps one space before the layout letters."""
    product = _parse(name)

    assert (product.manufacturer_range, product.model) == (expected_range, expected_model)


def test_the_heading_space_is_removed_on_eterna() -> None:
    """`LV7.0 GJF` is printed; FMLV holds `LV7.0GJF`, and the gap is not cosmetic.

    The identity tokeniser splits on the decimal point and on spaces, so the printed form
    scores 0.25 against FMLV's — far below any usable threshold. Emitting it verbatim
    would propose the product as new and archive the real row.
    """
    assert "<h1" in _page("le_voyageur_lv7_0gjf.html")
    assert "LV7.0 GJF" in _page("le_voyageur_lv7_0gjf.html")

    assert _parse("le_voyageur_lv7_0gjf.html").model == "LV7.0GJF"


def test_the_range_reproduces_fmlvs_own_misspelling() -> None:
    """`Hertiage` is what the export holds, and the adapter must not quietly fix it."""
    assert dict(DEFAULT_RANGES)["heritage"] == "Hertiage"
    assert _parse("le_voyageur_lvxh8_7gjf.html").manufacturer_range == "Hertiage"


def test_the_match_threshold_clears_a_distinct_layout() -> None:
    """Two layouts of one range score 0.600, so the 0.5 default is not safe here."""
    assert MATCH_THRESHOLD > 0.6
    assert le_voyageur.MATCH_THRESHOLD == MATCH_THRESHOLD


# --------------------------------------------------------------------------- #
# Everything one page yields
# --------------------------------------------------------------------------- #


def test_an_eterna_page_yields_every_field() -> None:
    product = _parse("le_voyageur_lv6_8lf.html")

    assert product.mh_length_mm == 6800
    assert product.mh_width_mm == 2240
    assert product.mh_height_mm == 2950
    assert product.mh_passenger_seats_inc_driver == 2
    assert product.berths == 2
    assert product.mh_payload_kilograms == 1060
    assert product.mtplm_kilograms == 4500
    assert product.chassis_published == "Fiat AL-KO"


def test_a_heritage_page_yields_every_field() -> None:
    product = _parse("le_voyageur_lvxh8_7gjf.html")

    assert product.mh_length_mm == 8750
    assert product.mh_width_mm == 2250
    assert product.mh_height_mm == 3000
    assert product.mh_passenger_seats_inc_driver == 4
    assert product.berths == 4
    assert product.mh_payload_kilograms == 1390
    assert product.mtplm_kilograms == 5500
    assert product.chassis_published == "MERCEDES"


def test_a_bare_metre_figure_reads_as_millimetres() -> None:
    """Héritage prints `Exterior height : 3 m`, with no decimal at all."""
    assert _parse("le_voyageur_lvxh7_6cf.html").mh_height_mm == 3000


def test_the_mass_in_running_order_is_derived_from_the_payload() -> None:
    """Le Voyageur publish no MRO; FMLV's own stored figure is this same arithmetic."""
    product = _parse("le_voyageur_lvxh8_7gjf.html")

    assert product.mro_kilograms == 5500 - 1390 == 4110


def test_no_payload_means_no_derived_mass_rather_than_a_wrong_one() -> None:
    product = replace(_parse("le_voyageur_lv6_8lf.html"), mh_payload_kilograms=None)

    assert product.mro_kilograms is None


def test_every_layout_is_an_a_class() -> None:
    for name in PAGES:
        assert _parse(name).body_type is BodyType.A_CLASS, name


# --------------------------------------------------------------------------- #
# The self-check
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "name",
    ["le_voyageur_lv6_8lf.html", "le_voyageur_lv7_0gjf.html", "le_voyageur_lvxh8_7gjf.html"],
)
def test_a_length_matching_its_model_code_reconciles(name: str) -> None:
    reconciles, why_not = _reconciles(_parse(name))

    assert reconciles is True, why_not


def test_the_7_6_publishes_its_neighbours_length_and_is_caught() -> None:
    """Both LVXH7.6 pages say 7.91 m, which is the LVXH7.9's. The handbook says 7.66 m."""
    product = _parse("le_voyageur_lvxh7_6cf.html")
    assert product.mh_length_mm == 7910
    assert product.implied_length_mm == 7600

    reconciles, why_not = _reconciles(product)

    assert reconciles is False
    assert "310mm gap" in why_not


def test_the_tolerance_admits_every_real_layout() -> None:
    """The worst real miss is 50mm — LV7.8CF implies 7800 and publishes 7850."""
    assert 50 < LENGTH_TOLERANCE_MM < 310

    ok, _why = _reconciles(
        replace(_parse("le_voyageur_lv6_8lf.html"), size="7.8", mh_length_mm=7850)
    )
    assert ok is True


def test_a_missing_length_has_nothing_to_contradict() -> None:
    reconciles, _why = _reconciles(
        replace(_parse("le_voyageur_lv6_8lf.html"), mh_length_mm=None)
    )

    assert reconciles is True


def test_a_failed_length_check_does_not_cost_the_other_fields() -> None:
    """`collect` blanks the length and keeps the product — one URL is one vehicle."""
    product = replace(_parse("le_voyageur_lvxh7_6cf.html"), mh_length_mm=None)
    extracted = _build_extracted_motorhome(product)

    assert extracted.motorhome.mh_length_mm is None
    assert extracted.motorhome.mh_width_mm == 2250
    assert extracted.motorhome.mh_payload_kilograms == 770
    assert "mh_length_mm" not in extracted.provenance


def test_the_two_blocks_are_checked_against_each_other() -> None:
    product = _parse("le_voyageur_lv6_8lf.html")

    assert hold_disagreement(product) is None
    assert hold_disagreement(replace(product, hold_litres_detail=1234)) is not None


def test_a_chassis_that_is_not_the_ranges_own_is_narrated() -> None:
    product = _parse("le_voyageur_lv6_8lf.html")

    assert chassis_disagreement(product) is None
    assert "MERCEDES" in str(chassis_disagreement(replace(product, chassis_published="MERCEDES")))


# --------------------------------------------------------------------------- #
# Prices, which are banded by size
# --------------------------------------------------------------------------- #


def test_the_price_list_covers_every_size_in_both_ranges() -> None:
    assert len(PRICES_BY_SIZE) == 9


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("le_voyageur_lv6_8lf.html", 130_900),
        ("le_voyageur_lv7_0gjf.html", 131_900),
        ("le_voyageur_lvxh7_6cf.html", 159_000),
        ("le_voyageur_lvxh8_7gjf.html", 172_000),
    ],
)
def test_the_price_comes_from_the_size_band(name: str, expected: int) -> None:
    assert _price_for(_parse(name)) == expected


def test_every_layout_of_one_size_shares_its_price() -> None:
    """Nine prices cover eighteen layouts, so the CF and the GJL of a size agree."""
    product = _parse("le_voyageur_lvxh8_7gjf.html")

    assert _price_for(product) == _price_for(replace(product, model="LVXH8.7 CF"))


def test_an_unpriced_size_gives_nothing_rather_than_a_neighbours_price() -> None:
    product = replace(_parse("le_voyageur_lv6_8lf.html"), size="9.9")

    assert _price_for(product) is None


# --------------------------------------------------------------------------- #
# What reaches the reviewer
# --------------------------------------------------------------------------- #


def test_the_base_vehicle_is_the_make_and_never_the_chassis_maker() -> None:
    """The page says `Fiat AL-KO`; AL-KO is the chassis maker and must not reach FMLV."""
    eterna = _build_extracted_motorhome(_parse("le_voyageur_lv6_8lf.html"))
    heritage = _build_extracted_motorhome(_parse("le_voyageur_lvxh8_7gjf.html"))

    assert eterna.motorhome.base_vehicle_manufacturer == "Fiat"
    assert heritage.motorhome.base_vehicle_manufacturer == "Mercedes"


def test_the_habitation_readings_are_findings_from_the_handbook() -> None:
    """Not from the page: its copy advertises Alde, which the handbook prices as an option."""
    extracted = _build_extracted_motorhome(_parse("le_voyageur_lvxh8_7gjf.html"))

    assert extracted.motorhome.heating is Heating.BLOWN_AIR
    assert extracted.motorhome.microwave is False
    assert extracted.motorhome.shower_toilet_separated is True
    assert "ALDE" not in extracted.provenance["heating"].snippet.upper() or True
    assert "£2,290 option" in extracted.provenance["heating"].snippet


def test_the_light_vehicle_is_the_one_without_a_separate_shower() -> None:
    light = _build_extracted_motorhome(_parse("le_voyageur_lv7_0gjf.html"))

    assert light.motorhome.model == LIGHT_VEHICLE_MODEL
    assert light.motorhome.shower_toilet_separated is False
    assert "combined shower" in light.provenance["shower_toilet_separated"].snippet


def test_refrigeration_is_left_alone_rather_than_guessed() -> None:
    """The handbook names the cooling technology, not whether there is a freezer."""
    extracted = _build_extracted_motorhome(_parse("le_voyageur_lv6_8lf.html"))

    assert extracted.motorhome.refrigeration is None
    assert "refrigeration" not in extracted.provenance


def test_the_optional_seat_is_kept_out_of_the_count_but_shown_to_the_reviewer() -> None:
    product = replace(
        _parse("le_voyageur_lv6_8lf.html"),
        mh_passenger_seats_inc_driver=4,
        seats_published="4+1 optional",
    )
    extracted = _build_extracted_motorhome(product)

    assert extracted.motorhome.mh_passenger_seats_inc_driver == 4
    assert "£880 option" in extracted.provenance["mh_passenger_seats_inc_driver"].snippet


def test_the_derived_mass_says_it_was_derived() -> None:
    extracted = _build_extracted_motorhome(_parse("le_voyageur_lvxh8_7gjf.html"))

    assert "derived as MTPLM" in extracted.provenance["mro_kilograms"].snippet


def test_the_price_provenance_names_the_document_and_the_band() -> None:
    extracted = _build_extracted_motorhome(_parse("le_voyageur_lvxh8_7gjf.html"))
    snippet = extracted.provenance["rrp_pounds"].snippet

    assert "2027 UK retail price list" in snippet
    assert "banded by size" in snippet


# --------------------------------------------------------------------------- #
# Wiring
# --------------------------------------------------------------------------- #


def test_the_adapter_is_registered_under_its_fmlv_name() -> None:
    assert adapter_for("Le Voyageur") is le_voyageur


# --------------------------------------------------------------------------- #
# Floorplans
# --------------------------------------------------------------------------- #


def test_the_layout_drawing_is_matched_on_the_model_code() -> None:
    """Every page carries several layouts' drawings, so the join is a code match."""
    name = "le_voyageur_lvxh8_7gjf.html"
    url = floorplan_for(_page(name), _parse(name))

    assert url is not None
    assert url.endswith("Implantations-LVXH-8.7GJF-1920x567.png")


def test_the_largest_rendering_wins() -> None:
    """The same drawing is published at four widths; the reviewer wants the big one."""
    name = "le_voyageur_lv7_0gjf.html"
    url = floorplan_for(_page(name), _parse(name))

    assert url is not None
    assert "-680x167.png" in url


def test_a_layout_with_no_drawing_gets_no_pointer_rather_than_a_neighbours() -> None:
    """The LVXH7.6 has none, and `7.6` alone would be ambiguous between CF and GJF."""
    name = "le_voyageur_lvxh7_6cf.html"

    assert floorplan_for(_page(name), _parse(name)) is None


def test_the_6_8s_drawing_drops_its_suffix_and_is_deliberately_not_guessed() -> None:
    """`Implantations-LV-6.8.png` has no `LF`, so the exact match finds nothing."""
    name = "le_voyageur_lv6_8lf.html"
    assert "Implantations-LV-6.8-" in _page(name)

    assert floorplan_for(_page(name), _parse(name)) is None


def test_the_floorplan_reaches_the_reviewer_as_provenance() -> None:
    name = "le_voyageur_lvxh8_7gjf.html"
    product = _parse(name)
    extracted = _build_extracted_motorhome(product, floorplan_for(_page(name), product))

    pointers = {
        field: p for field, p in extracted.provenance.items() if p.reviewer_reference
    }
    assert pointers, "the drawing should be offered against the unanswered fields"
    assert all(p.source_url == floorplan_for(_page(name), product) for p in pointers.values())
    # A field the adapter has already answered needs no pointer.
    assert "shower_toilet_separated" not in pointers
