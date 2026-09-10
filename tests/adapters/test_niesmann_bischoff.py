"""Niesmann + Bischoff's parsing, against real captured API responses.

No network. The three `*_grundriss.json` fixtures are exactly what
`konfigurator.niesmann-bischoff.com/backend/data/grundriss?modell=<range>&lang=en` returned
on 9 September 2026, byte for byte — including the trailing output the PHP backend appends
after the JSON document, which is the thing a plain `json.loads` chokes on.

`niesmann_bischoff_configurator.html` is the page trimmed to its script tags, and
`niesmann_bischoff_bundle_snippet.js` an 800-character window of the React bundle around
the backend declaration. Between them they cover the discovery chain: the page names the
bundle, the bundle names the API, and neither is hardcoded because the bundle's filename
carries a build hash.

Every figure asserted below was cross-checked against FMLV's own export for manufacturer
13, which agrees on all six existing products' dimensions and maximum laden mass.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters import niesmann_bischoff as nb
from src.adapters.niesmann_bischoff import NbLayout
from src.product_model.enums import BodyType, Heating

FIXTURES = Path(__file__).parent / "fixtures"

#: What the configurator publishes: seven layouts across three ranges. FMLV holds six of
#: them — `Arto 88` is the new one, and the requester confirmed it is sold in the UK.
EXPECTED_LAYOUTS = {"Arto": 3, "Flair": 2, "iSmove": 2}
EXPECTED_TOTAL = 7


def _read(name: str) -> str:
    return (FIXTURES / f"niesmann_bischoff_{name}").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def layouts() -> dict[str, NbLayout]:
    """Every captured layout, keyed on the title the API publishes."""
    found: dict[str, NbLayout] = {}
    for range_name in EXPECTED_LAYOUTS:
        parsed = nb.parse_layouts(range_name, _read(f"{range_name.lower()}_grundriss.json"))
        assert parsed, f"{range_name} produced no layouts"
        for layout in parsed:
            found[layout.title] = layout
    return found


# --------------------------------------------------------------------------- #
# Discovery — nothing about the API's address is remembered
# --------------------------------------------------------------------------- #


def test_the_bundle_is_found_on_the_configurator_page() -> None:
    """Its filename carries a build hash, so it cannot be hardcoded."""
    src = nb.parse_bundle_src(_read("configurator.html"))

    assert src is not None
    assert src.startswith("/static/js/main.")
    assert src.endswith(".js")


def test_the_api_address_is_read_out_of_the_bundle() -> None:
    """And the host differs from the page's by one letter — configurator vs konfigurator,
    which is exactly the sort of thing not to type from memory."""
    base = nb.parse_backend_base(_read("bundle_snippet.js"))

    assert base == "https://konfigurator.niesmann-bischoff.com/backend"


def test_a_staging_host_is_not_mistaken_for_the_api() -> None:
    """The real bundle also carries the developers' own hosts, so the pattern is anchored
    to the live domain rather than taking the first `/backend` it finds."""
    js = 'const a="http://nibi-konfigurator.alpha.3st-dev.de/backend",b=1'

    assert nb.parse_backend_base(js) is None


@pytest.mark.parametrize("page", ["", "<html></html>", "<script src='/static/js/other.js'>"])
def test_an_unreadable_page_names_no_bundle(page: str) -> None:
    assert nb.parse_bundle_src(page) is None


# --------------------------------------------------------------------------- #
# The roster
# --------------------------------------------------------------------------- #


def test_the_api_publishes_seven_layouts(layouts: dict[str, NbLayout]) -> None:
    assert len(layouts) == EXPECTED_TOTAL
    for range_name, count in EXPECTED_LAYOUTS.items():
        assert sum(1 for x in layouts.values() if x.range_name == range_name) == count


def test_php_output_around_the_json_does_not_stop_the_parse() -> None:
    """The backend wraps its JSON in PHP output when it feels like it, and a plain
    `json.loads` fails on a response that is otherwise perfectly good.

    Seen live on 9 September 2026: a notice ahead of the document
    (`<br /><b>Notice</b>: Uninitialized string offset: 0 in …grundriss.php`) when a
    parameter is missing, and trailing output after it. The captured fixtures happen to be
    clean, so the two cases are constructed here rather than left untested.
    """
    body = _read("arto_grundriss.json")
    assert len(nb.parse_layouts("Arto", body)) == 3

    notice = "<br /><b>Notice</b>:  Uninitialized string offset: 0 in <b>grundriss.php</b>"
    assert len(nb.parse_layouts("Arto", notice + body)) == 3
    assert len(nb.parse_layouts("Arto", body + notice)) == 3
    assert len(nb.parse_layouts("Arto", notice + body + notice)) == 3


@pytest.mark.parametrize("payload", ["", "not json", "[]", '{"items": "not a list"}'])
def test_an_unusable_response_yields_no_layouts(payload: str) -> None:
    assert nb.parse_layouts("Arto", payload) == []


# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("title", "range_name", "expected"),
    [
        ("Arto 78", "Arto", "78"),
        ("Arto 88", "Arto", "88"),
        ("Flair 920", "Flair", "920"),
        ("iSmove 6.9 E", "iSmove", "6.9E"),
        ("iSmove 7.3 F", "iSmove", "7.3F"),
    ],
)
def test_the_range_is_the_first_word_and_the_model_the_rest(
    title: str, range_name: str, expected: str
) -> None:
    """FMLV holds `6.9E` where the API says `6.9 E`, and that single space is the only
    difference between the two spellings — confirmed against the real export."""
    assert NbLayout(range_name=range_name, title=title).fmlv_model == expected


def test_only_a_number_and_a_trailing_letter_are_closed_up() -> None:
    """A blanket space-strip would mangle any future multi-word model."""
    assert NbLayout("Arto", "Arto 78 Special Edition").fmlv_model == "78 Special Edition"


# --------------------------------------------------------------------------- #
# The figures, all cross-checked against FMLV's export
# --------------------------------------------------------------------------- #


def test_the_headline_figures_match_what_fmlv_holds(layouts: dict[str, NbLayout]) -> None:
    """Dimensions and maximum laden mass agree with FMLV on all six existing products,
    which is the strongest evidence the parse is reading the right fields."""
    arto78 = layouts["Arto 78"]

    assert (arto78.mh_length_mm, arto78.mh_width_mm, arto78.mh_height_mm) == (7820, 2405, 3030)
    assert arto78.mtplm_kilograms == 4500
    assert arto78.rrp_pounds == 164800
    assert arto78.mro_kilograms == 3507


def test_payload_is_derived_and_the_optional_equipment_mass_is_not_payload(
    layouts: dict[str, NbLayout],
) -> None:
    """`Manufacturer-specified mass for optional equipment` is published and is not payload
    — the trap Dethleffs, Etrusco, Bürstner, Sunlight and Carado all share."""
    layout = layouts["iSmove 7.3 F"]

    assert layout.mh_payload_kilograms == 3500 - 2983
    optional_mass = layout._detail("mass for optional equipment")
    assert optional_mass is not None
    assert layout.mh_payload_kilograms != nb._number(optional_mass)


def test_thousands_commas_do_not_survive_into_a_figure(layouts: dict[str, NbLayout]) -> None:
    """Every dimension arrives as `7,820`."""
    assert layouts["Arto 88"].mh_length_mm == 9069


def test_only_the_standard_three_point_belts_are_counted(
    layouts: dict[str, NbLayout],
) -> None:
    """Two settled rules meet here and agree: count three-point belts only, and take the
    base vehicle's figure rather than an optioned variant's.

    FMLV holds 4 for these products, so this proposes a correction on every one — flagged
    in the survey because it changes every listing.
    """
    layout = layouts["Flair 880"]

    assert layout.seats_published is not None
    assert "opt" in layout.seats_published.lower(), "the row must still show the options"
    assert layout.mh_passenger_seats_inc_driver == 2


def test_the_base_vehicle_is_spelled_fmlvs_way(layouts: dict[str, NbLayout]) -> None:
    """`Mercedes Benz 415 CDI, Euro VI E` is FMLV's `Mercedes`, never `Mercedes-Benz`."""
    assert layouts["Arto 78"].base_vehicle_manufacturer == "Mercedes"
    assert layouts["iSmove 6.9 E"].base_vehicle_manufacturer == "Fiat"
    assert layouts["Flair 880"].base_vehicle_manufacturer == "IVECO"


def test_every_layout_is_an_a_class(layouts: dict[str, NbLayout]) -> None:
    """Niesmann + Bischoff build nothing else, and FMLV holds all six as `type_a_class`."""
    assert {x.body_type for x in layouts.values()} == {BodyType.A_CLASS}


def test_an_unknown_range_gets_no_body_type() -> None:
    """A range that is not one of the three classifies itself as unknown rather than being
    labelled A-class on the strength of its siblings."""
    assert NbLayout("Something New", "Something New 1").body_type is None


# --------------------------------------------------------------------------- #
# Berths, counted off the bed sizes
# --------------------------------------------------------------------------- #


def test_every_layout_sleeps_four(layouts: dict[str, NbLayout]) -> None:
    """The requester's ruling, 9 September 2026: *"the fact that there are two double beds
    is our best guidance on the berths, so that would be four."*

    The API states bed dimensions and never a berth count. This reproduces FMLV's 4 on all
    six existing products, which is what makes the derivation trustworthy.
    """
    assert {x.berths for x in layouts.values()} == {4}


def test_two_singles_count_as_two_and_a_double_as_two() -> None:
    """The iSmove 6.9 E is the case that proves it: its rear is twin singles of 735 and
    730 mm where every other layout's is one wide double."""
    twin_singles = [
        ("BedsOverhead front bed (length × width) (in mm)", "1,870 x 1,300"),
        ("BedsRear bed(s) (length × width) (in mm)", "2,065 × 735 / 1,975 × 730"),
    ]
    one_double = [
        ("BedsOverhead front bed (length × width) (in mm)", "1,870 x 1,300"),
        ("BedsRear bed(s) (length × width) (in mm)", "2,000 × 1,380"),
    ]

    assert nb.berths_from(twin_singles) == 4
    assert nb.berths_from(one_double) == 4


def test_no_bed_row_means_no_berth_count() -> None:
    """A confident zero would be worse than a blank."""
    assert nb.berths_from([("Base vehicle", "Fiat Ducato")]) is None


def test_both_multiplication_signs_are_read() -> None:
    """The site uses `×` on some rows and a plain `x` on others, in the same record."""
    assert nb.berths_from([("Beds Rear bed", "2,000 x 1,380")]) == 2
    assert nb.berths_from([("Beds Rear bed", "2,000 × 1,380")]) == 2


# --------------------------------------------------------------------------- #
# The rest of the record
# --------------------------------------------------------------------------- #


def test_the_garage_is_answered_from_its_published_dimensions(
    layouts: dict[str, NbLayout],
) -> None:
    """A proposed value rather than a finding, as the requester directed for rear garage."""
    assert layouts["Arto 78"].rear_garage is True
    assert NbLayout("Arto", "Arto 78").rear_garage is False  # no details at all


def test_the_floorplan_comes_from_the_gallery_image_not_the_thumbnail(
    layouts: dict[str, NbLayout],
) -> None:
    """`thumbFilename` is **not** per-layout — Flair 880 and 920 share
    `cart_flair_2022.png`, and both iSmoves share `cart_ismove.png`. Joining on it would
    give two products the same drawing."""
    flair880 = layouts["Flair 880"].floorplan_path
    flair920 = layouts["Flair 920"].floorplan_path

    assert flair880 != flair920
    assert flair880 is not None and flair880.startswith(nb.FLOORPLAN_PATH)
    assert layouts["Flair 880"].raw["thumbFilename"] == layouts["Flair 920"].raw["thumbFilename"]


def test_details_survive_being_a_python_literal_inside_a_json_string(
    layouts: dict[str, NbLayout],
) -> None:
    """`details` arrives single-quoted, so `json.loads` will not read it."""
    pairs = layouts["Arto 78"].pairs

    assert pairs, "the details block must parse"
    assert any("Base vehicle" in label for label, _value in pairs)


def test_unparseable_details_yield_nothing_rather_than_raising() -> None:
    assert nb.detail_pairs("not a literal at all") == []
    assert nb.detail_pairs(None) == []


# --------------------------------------------------------------------------- #
# The self-check
# --------------------------------------------------------------------------- #


def test_every_key_figure_is_stated_twice_and_the_two_agree(
    layouts: dict[str, NbLayout],
) -> None:
    """The structured fields and the `details` prose rows are two renderings of one record,
    which is what lets a parse be checked without a second source."""
    for title, layout in layouts.items():
        assert nb._reconciles(layout) == [], title


def test_a_record_whose_two_renderings_disagree_is_reported() -> None:
    """Such a product is dropped by `collect` rather than proposed — a mass read from the
    wrong field is exactly the failure that produces plausible, wrong motorhomes."""
    layout = NbLayout(
        range_name="Arto",
        title="Arto 78",
        raw={
            "weight": "3507",
            "details": str(
                [{"dt": "Mass in running order (in kg approx.)*", "dd": "9,999 (1 - 2)"}]
            ),
        },
    )

    assert nb._reconciles(layout) == ["Mass in running order (3507 vs 9999)"]


# --------------------------------------------------------------------------- #
# The product
# --------------------------------------------------------------------------- #


def test_both_halves_of_the_identity_are_proposed_together(
    layouts: dict[str, NbLayout],
) -> None:
    extracted = nb.build_extracted(layouts["iSmove 6.9 E"])

    assert extracted.motorhome.manufacturer_range == "iSmove"
    assert extracted.motorhome.model == "6.9E"
    assert (
        extracted.provenance["manufacturer_range"].snippet
        == extracted.provenance["model"].snippet
    )


def test_the_price_says_why_it_is_not_the_importers(layouts: dict[str, NbLayout]) -> None:
    """The requester's ruling on Travelworld, carried into the provenance so a reviewer
    reading the row knows the price is the model's and not one stock vehicle's."""
    snippet = nb.build_extracted(layouts["Arto 84"]).provenance["rrp_pounds"].snippet

    assert "stock" in snippet.lower()
    assert "£179,100" in snippet


def test_the_berth_count_shows_its_working(layouts: dict[str, NbLayout]) -> None:
    """It is a derivation, so the reviewer gets the bed sizes it was derived from."""
    snippet = nb.build_extracted(layouts["iSmove 6.9 E"]).provenance["berths"].snippet

    assert "735" in snippet and "730" in snippet


def test_the_floorplan_is_handed_over_for_the_fields_it_answers(
    layouts: dict[str, NbLayout],
) -> None:
    extracted = nb.build_extracted(layouts["Arto 78"])
    pointers = {
        name for name, entry in extracted.provenance.items() if entry.reviewer_reference
    }

    assert pointers == {
        "sleeping_area",
        "kitchen_location",
        "lounge_location",
        "bathroom_layout",
        "bed_types",
    }


def test_manufacturer_matches_the_registry() -> None:
    """`MANUFACTURER` is the join key back to FMLV and the `ADAPTERS` key; a typo detaches
    the run from its history and hides the brand from the trigger dropdown."""
    import csv

    rows = list(csv.DictReader((Path("config") / "manufacturers.csv").open(encoding="utf-8")))
    row = next(r for r in rows if r["manufacturer_id"] == "13")

    assert row["fmlv_manufacturer"] == nb.MANUFACTURER
    assert row["fmlv_display_name"] == nb.MANUFACTURER_DISPLAY_NAME
    assert row["ncc_supplier_name"] == "Niesmann + Bischoff shown by Travelworld"


def test_every_default_range_is_one_the_body_type_map_knows() -> None:
    """A new range added to `DEFAULT_RANGES` without a body type would ship blank."""
    assert {label for _name, label in nb.DEFAULT_RANGES} <= set(nb.BODY_TYPES)


# --------------------------------------------------------------------------- #
# Standard equipment, and the flag that keeps an option out of it
# --------------------------------------------------------------------------- #


def test_only_the_standard_equipment_is_read() -> None:
    """The configurator is an options catalogue, so `serie` is what makes it usable.

    Arto 78 marks 7 of its 34 technology items `serie: True` at price 0; the other 27 are
    priced upgrades.
    """
    lines = nb.parse_standard_equipment(_read("arto_78_technik.json"))

    assert len(lines) == 7
    assert any("Warm water heating" in line for line in lines)
    assert not any("Roof air conditioner" in line for line in lines)


def test_the_category_stays_on_the_line() -> None:
    """So the quote a reviewer reads says where on the page it came from."""
    lines = nb.parse_standard_equipment(_read("arto_78_technik.json"))

    assert any(line.startswith("Heating, Air Conditioning System: ") for line in lines)


def test_a_range_that_publishes_no_standard_equipment_yields_none() -> None:
    """**The reading that would have been wrong.** Every one of iSmove 6.9 E's 44
    technology items is `serie: False` — including `Warm water heating with thermostat
    control (Alde 3030+)` at £3,186. Without the flag the adapter would report iSmove as
    wet central heating when the wet system is an upgrade, and its standard heating is
    something the endpoint does not publish at all.
    """
    body = _read("ismove_69e_technik.json")

    assert "Alde 3030+" in body, "the fixture must still contain the tempting option"
    assert nb.parse_standard_equipment(body) == []


def test_the_arto_heating_is_read_as_wet() -> None:
    """`Warm water heating with thermostat. control, heating cartridge …(independent
    heating circuit in the rear bedroom)` — and `warm water heating` had to be added to the
    shared vocabulary beside Dethleffs' `hot-water heating` to see it."""
    from src.adapters import habitation

    lines = nb.parse_standard_equipment(_read("arto_78_technik.json"))
    found = habitation.heating_from(lines)

    assert found is not None
    assert found[0] is Heating.WET_CENTRAL


def test_an_optional_microwave_is_not_reported_as_fitted() -> None:
    """Niesmann sell a microwave as a priced extra in `/data/interieur`, which has **no**
    standard items at all. Only the standard list reaches `habitation`, so the option
    neither asserts a microwave nor suppresses the note — and the note says which."""
    lines = nb.parse_standard_equipment(_read("arto_78_technik.json"))
    extracted = nb.build_extracted(
        NbLayout("Arto", "Arto 78", {"title": "Arto 78"}), lines
    )

    assert extracted.motorhome.microwave is False
    assert "priced option" in extracted.provenance["microwave"].snippet


@pytest.mark.parametrize("payload", ["", "not json", "{}", '{"items": "not a list"}'])
def test_an_unusable_equipment_response_yields_nothing(payload: str) -> None:
    assert nb.parse_standard_equipment(payload) == []
