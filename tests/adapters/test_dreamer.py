"""Dreamer's parsing, against the pages the site served on 11 November 2026.

Pure parsing only: no network, no browser. The fixtures are kept as **bytes**, because
half of what this adapter has to get right is that the site is `iso-8859-1` and a single
`0xA0` byte in Cap Easy Select's heater is what took the first run down.

The negative tests are the traps this site actually laid: a `New` badge that hides a
model's only published length, a seat count that is a chassis ceiling rather than a
figure, a cruise-control caveat that reads as an automatic being ruled out, and a van
whose roof the pages do not mention and whose berth count says it has one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters import dreamer
from src.product_model.enums import BodyType

FIXTURES = Path(__file__).parent / "fixtures"


def _page(name: str) -> str:
    return dreamer._read(FIXTURES / name)


def _model(model: str, manufacturer_range: str) -> dreamer._Model:
    for candidate in dreamer.MODELS:
        if candidate.model == model and candidate.manufacturer_range == manufacturer_range:
            return candidate
    raise AssertionError(f"no model {model!r} in range {manufacturer_range!r}")


@pytest.fixture
def home() -> str:
    return _page("dreamer-home.html")


@pytest.fixture
def tiles(home: str) -> dict[str, int]:
    return dreamer.parse_tiles(home)


# --------------------------------------------------------------------------- #
# The roster
# --------------------------------------------------------------------------- #


def test_the_adapter_knows_every_model_dreamer_sell() -> None:
    assert len(dreamer.MODELS) == dreamer.EXPECTED_PRODUCTS == 19


def test_the_two_ranges_are_spelled_as_fmlv_spells_them() -> None:
    assert dreamer.FUN == "Fun"
    assert dreamer.SELECT == "Select"
    assert {model.manufacturer_range for model in dreamer.MODELS} == {"Fun", "Select"}


def test_eight_models_are_fun_and_eleven_are_select() -> None:
    fun = [m for m in dreamer.MODELS if m.manufacturer_range == dreamer.FUN]
    select = [m for m in dreamer.MODELS if m.manufacturer_range == dreamer.SELECT]
    assert (len(fun), len(select)) == (8, 11)


def test_a_model_name_alone_does_not_identify_a_product() -> None:
    """`D55` and `D68` exist in both ranges, which is why `--range` takes the range."""
    names = [m.model for m in dreamer.MODELS]
    assert names.count("D55") == 2
    assert names.count("D68") == 2
    assert len(set(names)) < len(names)


def test_no_model_name_keeps_the_select_suffix() -> None:
    """The website suffixes every Select model with ` Select`; that is the range."""
    assert not [m for m in dreamer.MODELS if "SELECT" in m.model.upper()]


def test_every_model_page_path_is_distinct() -> None:
    paths = [m.path for m in dreamer.MODELS]
    assert len(set(paths)) == len(paths)


# --------------------------------------------------------------------------- #
# The tiles, which carry the only published length
# --------------------------------------------------------------------------- #


def test_every_model_has_a_tile_on_the_home_page(tiles: dict[str, int]) -> None:
    assert len(tiles) == dreamer.EXPECTED_PRODUCTS
    for model in dreamer.MODELS:
        assert model.path.lower() in tiles, model.model


def test_tile_lengths_match_what_dreamer_print_on_them(tiles: dict[str, int]) -> None:
    assert tiles["fourgon-dreamer-d43.php"] == 5410
    assert tiles["fourgon-dreamer-d55.php"] == 5990
    assert tiles["fourgon-dreamer-campersport.php"] == 5980
    assert tiles["fourgon-dreamer-citycamp-select.php"] == 5050
    assert tiles["fourgon-dreamer-capeasy-select.php"] == 5480
    assert tiles["fourgon-dreamer-capland-select.php"] == 5450


def test_a_new_badge_does_not_swallow_the_length(tiles: dict[str, int]) -> None:
    """The trap that lost six lengths on the first attempt.

    A model badged `New` carries an extra `<span class="nouveau">New</span>` inside the
    `dim` span and *before* the figure, so a parser that stops at the first `</span>` loses
    the length on exactly the six models most worth collecting — and loses it silently,
    because the other thirteen still work.
    """
    badged_new = (
        "fourgon-dreamer-d43.php",
        "fourgon-dreamer-d68-up.php",
        "fourgon-dreamer-capeasy-select.php",
        "fourgon-dreamer-d64-select.php",
        "fourgon-dreamer-lift-van-select.php",
        "fourgon-dreamer-lift-van-up-select.php",
    )
    for path in badged_new:
        assert tiles.get(path), path


def test_a_page_with_no_tiles_yields_nothing_rather_than_guessing() -> None:
    assert dreamer.parse_tiles("<html><body>nothing here</body></html>") == {}


# --------------------------------------------------------------------------- #
# A model page
# --------------------------------------------------------------------------- #


def test_d43_reads_as_dreamer_publish_it() -> None:
    product = dreamer.parse_model_page(
        _page("dreamer-model-d43.html"), _model("D43", dreamer.FUN), length_mm=5410
    )
    assert product.page_heading == "D43"
    assert product.mh_height_mm == 2630
    assert product.mh_width_mm == 2050
    assert product.mh_length_mm == 5410
    assert product.mh_passenger_seats_inc_driver == 4
    assert product.berths == 2


def test_an_optional_berth_is_not_counted() -> None:
    """`2 (O : 2 + 1)` is two berths with an optional third, not five."""
    product = dreamer.parse_model_page(
        _page("dreamer-model-d43.html"), _model("D43", dreamer.FUN)
    )
    assert product.berths_note == "2 (O : 2 + 1)"
    assert product.berths == 2


def test_the_up_model_carries_its_extra_berths_as_standard() -> None:
    product = dreamer.parse_model_page(
        _page("dreamer-model-d43-up.html"), _model("D43 UP", dreamer.FUN)
    )
    assert product.berths_note == "2+2"
    assert product.berths == 4
    assert product.mh_height_mm == 2760


def test_the_up_model_is_130mm_taller_than_its_twin() -> None:
    """The roof is the only thing that differs, and the height is where it shows."""
    plain = dreamer.parse_model_page(
        _page("dreamer-model-d43.html"), _model("D43", dreamer.FUN)
    )
    popped = dreamer.parse_model_page(
        _page("dreamer-model-d43-up.html"), _model("D43 UP", dreamer.FUN)
    )
    assert popped.mh_height_mm is not None and plain.mh_height_mm is not None
    assert popped.mh_height_mm - plain.mh_height_mm == 130


@pytest.mark.parametrize("count", [2, 4, 5])
def test_standard_count_sums_only_what_is_outside_the_bracket(count: int) -> None:
    values = {2: "2 (O : 2 + 1)", 4: "2 + 2", 5: "2+2+1"}
    assert dreamer._standard_count(values[count]) == count


def test_standard_count_returns_nothing_for_a_value_with_no_digits() -> None:
    assert dreamer._standard_count("on request") is None


# --------------------------------------------------------------------------- #
# The charset
# --------------------------------------------------------------------------- #


def test_a_latin1_page_is_decoded_rather_than_replaced() -> None:
    """The byte that took the first run down.

    Cap Easy Select's heater is `WEBASTO 2500\\xa0W FUEL HEATING` with a real non-breaking
    space, which is one byte in iso-8859-1 and not valid UTF-8 at all. Decoded as UTF-8
    with `errors="replace"` it becomes U+FFFD, which cannot then be written to a Windows
    console — so the whole run dies on one page's typography.
    """
    page = _page("dreamer-model-capeasy-select.html")
    assert "�" not in page
    product = dreamer.parse_model_page(
        page, _model("CAP EASY", dreamer.SELECT), length_mm=5480
    )
    assert product.pictos["svg__chauffage"] == "WEBASTO 2500 W FUEL HEATING"


def test_the_raw_fixture_really_is_not_utf8() -> None:
    """Guards the test above against a fixture that gets 'tidied' into UTF-8 one day."""
    raw = (FIXTURES / "dreamer-model-capeasy-select.html").read_bytes()
    with pytest.raises(UnicodeDecodeError):
        raw.decode("utf-8")


# --------------------------------------------------------------------------- #
# A seat count that is a ceiling
# --------------------------------------------------------------------------- #


def test_a_footnoted_chassis_maximum_is_not_a_seat_count() -> None:
    """City Camp Select publishes `6(p) people`, and `(p)` is the chassis's permitted
    maximum — *"Maximum number of authorised registered seats as defined by the chassis"*.
    A ceiling is not a figure FMLV records, so nothing is proposed and FMLV's own 5 stands.
    """
    product = dreamer.parse_model_page(
        _page("dreamer-model-citycamp-select.html"),
        _model("CITY CAMP", dreamer.SELECT),
    )
    assert product.pictos["svg__places"] == "6(p) people"
    assert product.mh_passenger_seats_inc_driver is None
    assert product.seats_ceiling_note == "6(p) people"


def test_an_unfootnoted_seat_count_is_taken() -> None:
    product = dreamer.parse_model_page(
        _page("dreamer-model-d68-select.html"), _model("D68", dreamer.SELECT)
    )
    assert product.mh_passenger_seats_inc_driver == 4


# --------------------------------------------------------------------------- #
# Dimensions
# --------------------------------------------------------------------------- #


def test_an_optional_lowered_height_is_not_the_vehicles_height() -> None:
    """City Camp publishes `(H) 2.04 M O : 2.00 m* (W) 2.03 M`, and the `2.00` belongs to a
    rear-suspension option. The base vehicle's figure is the one FMLV holds.
    """
    product = dreamer.parse_model_page(
        _page("dreamer-model-citycamp-select.html"),
        _model("CITY CAMP", dreamer.SELECT),
    )
    assert product.mh_height_mm == 2040
    assert product.mh_width_mm == 2030


def test_the_storage_area_dimensions_are_never_mistaken_for_the_vehicles() -> None:
    """Both pictos use `(H)`/`(L)`/`(W)`; only the exterior one feeds the fields."""
    product = dreamer.parse_model_page(
        _page("dreamer-model-d43.html"), _model("D43", dreamer.FUN)
    )
    assert product.pictos["svg__dimension_int"] == "(H) 670 MM (L) 1040 MM (W) 950 MM"
    assert product.mh_height_mm == 2630
    assert product.mh_width_mm == 2050


# --------------------------------------------------------------------------- #
# The checks
# --------------------------------------------------------------------------- #


def test_a_page_that_names_a_different_model_is_dropped() -> None:
    product = dreamer.parse_model_page(
        _page("dreamer-model-d68-select.html"), _model("D43", dreamer.SELECT)
    )
    identified, note = dreamer._check_identity(product, _model("D43", dreamer.SELECT))
    assert identified is False
    assert "D68 SELECT" in note


def test_a_page_that_names_the_right_model_passes() -> None:
    model = _model("D68", dreamer.SELECT)
    product = dreamer.parse_model_page(_page("dreamer-model-d68-select.html"), model)
    identified, _ = dreamer._check_identity(product, model)
    assert identified is True


def test_a_page_with_no_specification_block_is_dropped() -> None:
    product = dreamer.parse_model_page(
        "<html><h1>D43</h1></html>", _model("D43", dreamer.FUN)
    )
    intact, note = dreamer._check_shape(product)
    assert intact is False
    assert "changed shape" in note


def test_an_up_model_whose_page_stops_mentioning_a_roof_is_narrated() -> None:
    product = dreamer.parse_model_page(
        _page("dreamer-model-d43.html"), _model("D43 UP", dreamer.FUN)
    )
    warning = dreamer._check_roof(product)
    assert warning is not None
    assert "no longer says so" in warning


def test_an_up_model_whose_page_still_mentions_a_roof_is_quiet() -> None:
    product = dreamer.parse_model_page(
        _page("dreamer-model-d43-up.html"), _model("D43 UP", dreamer.FUN)
    )
    assert dreamer._check_roof(product) is None


def test_a_model_with_an_unstated_roof_is_never_warned_about() -> None:
    product = dreamer.parse_model_page(
        _page("dreamer-model-citycamp-select.html"),
        _model("CITY CAMP", dreamer.SELECT),
    )
    assert product.elevating_roof is None
    assert dreamer._check_roof(product) is None


# --------------------------------------------------------------------------- #
# Body type
# --------------------------------------------------------------------------- #


def test_a_high_top_without_a_roof_is_a_plain_high_top() -> None:
    product = dreamer.parse_model_page(
        _page("dreamer-model-d43.html"), _model("D43", dreamer.FUN)
    )
    body, note = dreamer._body_type(product)
    assert body is BodyType.CAMPERVAN_HIGH_TOP
    assert note is not None and "2,630mm" in note


def test_a_high_top_with_a_standard_roof_takes_the_fourth_body_type() -> None:
    product = dreamer.parse_model_page(
        _page("dreamer-model-d43-up.html"), _model("D43 UP", dreamer.FUN)
    )
    body, _ = dreamer._body_type(product)
    assert body is BodyType.CAMPERVAN_HIGH_TOP_ELEVATING_ROOF


def test_a_low_van_with_a_pop_up_roof_is_not_a_high_top() -> None:
    """Cap Easy Select is 1,990mm — below the threshold — and says 'a pop-up roof bed'."""
    product = dreamer.parse_model_page(
        _page("dreamer-model-capeasy-select.html"), _model("CAP EASY", dreamer.SELECT)
    )
    body, _ = dreamer._body_type(product)
    assert body is BodyType.CAMPERVAN_ELEVATING_ROOF


def test_no_body_type_is_proposed_where_the_roof_is_unstated() -> None:
    """Silence is normally enough to rule a roof out. Not here.

    City Camp Select publishes four berths in a van 2,040mm tall, its twin the Cap Land
    states `4 adult berths with pop-up roof` in identical circumstances, and FMLV holds it
    as `campervan_elevating_roof`. Downgrading it to a plain campervan would be a
    correction made against the evidence, so nothing is proposed at all.
    """
    product = dreamer.parse_model_page(
        _page("dreamer-model-citycamp-select.html"),
        _model("CITY CAMP", dreamer.SELECT),
    )
    assert dreamer._body_type(product) == (None, None)
    assert "CITY CAMP" in dreamer.ROOF_UNSTATED


def test_no_body_type_without_a_height() -> None:
    product = dreamer.DreamerProduct(
        model="D43", manufacturer_range=dreamer.FUN, source_url="", elevating_roof=False
    )
    assert dreamer._body_type(product) == (None, None)


# --------------------------------------------------------------------------- #
# The gearbox
# --------------------------------------------------------------------------- #


def test_the_fun_list_offers_an_automatic() -> None:
    from src.adapters import gearbox

    lines = [
        " ".join(line.split())
        for line in gearbox.lines_from_page(_page("dreamer-equipment-fun.html"))
    ]
    offers = dreamer._transmission_lines(lines)
    assert offers
    found = gearbox.automatic_available_from(offers)
    assert found is not None and found[0] is True


def test_a_cruise_control_caveat_never_rules_an_automatic_out() -> None:
    """The trap in the Select list, and the reason the page is not read whole.

    `Adaptive cruise control - manual transmission only` is a caveat on a driver-assistance
    feature, not a statement about what gearboxes exist — and the line directly below it
    offers lane-keeping `automatic transmission only`, which proves one does. Passed
    through unfiltered it reads as an explicit `No`, which would write a wrong value into
    FMLV rather than leaving the column blank.
    """
    from src.adapters import gearbox

    lines = [
        " ".join(line.split())
        for line in gearbox.lines_from_page(_page("dreamer-equipment-select.html"))
    ]
    unfiltered = gearbox.automatic_available_from(lines)
    assert unfiltered is not None and unfiltered[0] is False  # the trap, unguarded

    kept = dreamer._transmission_lines(lines)
    assert not [line for line in kept if "cruise control" in line.lower()]


def test_a_transmission_line_must_name_a_make() -> None:
    assert dreamer._transmission_lines(
        ["FIAT 140 hp automatic transmission, 3.5T - LIGHT DUTY"]
    )
    assert not dreamer._transmission_lines(["Adaptive cruise control - manual transmission only"])
    assert not dreamer._transmission_lines(["Lane-keeping assist - automatic transmission only"])


# --------------------------------------------------------------------------- #
# What is deliberately not collected
# --------------------------------------------------------------------------- #


def test_no_mass_price_or_base_vehicle_is_ever_emitted() -> None:
    """Dreamer publish no mass or price for the range they currently sell, and name their
    engines on a range-wide list with no model attribution. All three are left unset so
    that FMLV's existing values survive a run untouched.
    """
    product = dreamer.parse_model_page(
        _page("dreamer-model-d68-select.html"), _model("D68", dreamer.SELECT), length_mm=6360
    )
    extracted = dreamer._build_extracted_motorhome(product)
    motorhome = extracted.motorhome
    assert motorhome.mro_kilograms is None
    assert motorhome.mtplm_kilograms is None
    assert motorhome.mh_payload_kilograms is None
    assert motorhome.rrp_pounds is None
    assert motorhome.base_vehicle_manufacturer is None
    for absent in (
        "mro_kilograms",
        "mtplm_kilograms",
        "mh_payload_kilograms",
        "rrp_pounds",
        "base_vehicle_manufacturer",
    ):
        assert absent not in extracted.provenance


def test_the_superseded_table_is_named_but_never_fetched() -> None:
    """It is the obvious source and the wrong one; the URL is here so that whoever comes
    looking for it finds the reason instead."""
    source = Path(dreamer.__file__).read_text(encoding="utf-8")
    assert "caracteristiques-techniques" in dreamer.SUPERSEDED_SPECIFICATION_TABLE
    assert "SUPERSEDED_SPECIFICATION_TABLE" in source
    assert "http.fetch(SUPERSEDED_SPECIFICATION_TABLE)" not in source


def test_every_emitted_field_has_provenance() -> None:
    product = dreamer.parse_model_page(
        _page("dreamer-model-d43-up.html"), _model("D43 UP", dreamer.FUN), length_mm=5410
    )
    extracted = dreamer._build_extracted_motorhome(product)
    for field_name in ("mh_length_mm", "mh_height_mm", "mh_width_mm", "berths", "body_type"):
        assert getattr(extracted.motorhome, field_name) is not None
        assert field_name in extracted.provenance


def test_the_range_is_recorded_with_its_own_provenance() -> None:
    product = dreamer.parse_model_page(
        _page("dreamer-model-d68-select.html"), _model("D68", dreamer.SELECT)
    )
    extracted = dreamer._build_extracted_motorhome(product)
    assert extracted.motorhome.manufacturer_range == "Select"
    assert extracted.motorhome.model == "D68"
    assert "Select" in extracted.provenance["manufacturer_range"].snippet


# --------------------------------------------------------------------------- #
# The identity Dreamer have to settle
# --------------------------------------------------------------------------- #


def test_the_unsettled_identities_are_stated_rather_than_applied() -> None:
    """No rename is applied anywhere, because the settled way to evidence one is to match
    the mass in running order and this adapter collects none."""
    assert dreamer.AMBIGUOUS_IDENTITY
    assert dreamer.RENAME_CANDIDATES
    names = {model.model for model in dreamer.MODELS}
    for held in (*dreamer.RENAME_CANDIDATES, *dreamer.NOT_ON_THE_SITE):
        assert held not in names, held


# --------------------------------------------------------------------------- #
# The automatic, where the website says nothing and the catalogue does
# --------------------------------------------------------------------------- #


def test_the_website_settles_the_fun_range_by_itself() -> None:
    """`FIAT 140 hp automatic transmission, 3.5T - LIGHT DUTY`, read every run."""
    from src.adapters import gearbox

    lines = [
        " ".join(line.split())
        for line in gearbox.lines_from_page(_page("dreamer-equipment-fun.html"))
    ]
    found = gearbox.automatic_available_from(dreamer._transmission_lines(lines))
    assert found is not None and found[0] is True


def test_the_website_settles_nothing_for_select() -> None:
    """Its only engine-and-gearbox lines name a Ford and a Renault, both manual.

    Crucially this must come back as *nothing*, not as a `False`. Silence is a blank;
    writing an explicit "no automatic" into FMLV off these two lines would be wrong.
    """
    from src.adapters import gearbox

    lines = [
        " ".join(line.split())
        for line in gearbox.lines_from_page(_page("dreamer-equipment-select.html"))
    ]
    kept = dreamer._transmission_lines(lines)
    assert kept and all("manual" in line.lower() for line in kept)
    assert gearbox.automatic_available_from(kept) is None


def test_the_catalogue_fills_select_where_the_website_is_silent() -> None:
    """The SAPHIR finish includes `140 hp engine with automatic transmission` (p.33)."""
    found = dreamer._automatic_for(_model("D68", dreamer.SELECT), {dreamer.SELECT: None})
    assert found is not None and found[0] is True
    assert "SAPHIR" in found[1]


def test_the_three_vans_saphir_does_not_cover_stay_blank() -> None:
    """Not a guess from their size — Dreamer's own equipment table holds them apart.

    `dreamer-select-equipements.php` lays out four columns: `SELECT RANGE STANDARD`,
    `SELECT RANGE FINISH SAPHIR`, `CAP LAND SELECT / CITY CAMP SELECT` and `CAP EASY
    SELECT`. The finish that carries the automatic is not one of the last two, and both
    of those bases are stated as manual. Nothing denies an automatic, so: blank.
    """
    assert set(dreamer.SELECT_WITHOUT_AUTOMATIC) == {"CAP EASY", "CAP LAND", "CITY CAMP"}
    for name in dreamer.SELECT_WITHOUT_AUTOMATIC:
        assert dreamer._automatic_for(_model(name, dreamer.SELECT), {dreamer.SELECT: None}) is None


def test_the_website_always_beats_the_catalogue() -> None:
    """The catalogue cannot be re-fetched; the equipment page is read every run."""
    live = (False, "RENAULT Trafic Blue 130 hp engine with manual transmission only")
    assert dreamer._automatic_for(_model("D68", dreamer.SELECT), {dreamer.SELECT: live}) == live


def test_the_catalogue_says_nothing_about_the_fun_range() -> None:
    """It does not need to — the website settles FUN, so nothing is hardcoded for it."""
    assert dreamer.FUN not in dreamer.CATALOGUE_AUTOMATIC
