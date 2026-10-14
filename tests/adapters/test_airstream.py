"""Lowdhams' Airstream browse page and stock pages, captured 14 October 2026.

The fixtures are each page's own markup with its scripts, styles and SVGs removed and
then sliced to the region the parser reads. Each slice was checked at capture time to
parse identically to the whole page.

Almost every test here is about something **not** being recorded. That is the shape of
this adapter: the pages carry an MTPLM, a length, a width and a height, and all four are
facts about one unit in a showroom rather than about the model.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters.airstream import (
    EUROPEAN_SPECIFICATION,
    EXPECTED_PRODUCTS,
    MANUFACTURER,
    MANUFACTURER_DISPLAY_NAME,
    MINIMUM_CREDIBLE_PRICE,
    VEHICLE_CLASS,
    Vehicle,
    body_type_for,
    build_extracted,
    find_vehicle_paths,
    parse_cards,
    parse_features,
    parse_specification,
    parse_vehicle,
    plating_verdict,
)
from src.product_model.enums import CaravanBodyType
from src.vehicle_class import VehicleClass

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def browse() -> str:
    return _fixture("airstream_browse.html")


@pytest.fixture(scope="module")
def i534() -> str:
    return _fixture("airstream_international_534.html")


@pytest.fixture(scope="module")
def i684() -> str:
    return _fixture("airstream_international_684.html")


@pytest.fixture(scope="module")
def wt22rb() -> str:
    return _fixture("airstream_world_traveller_22rb.html")


@pytest.fixture(scope="module")
def used25ib() -> str:
    return _fixture("airstream_used_25_ib.html")


def _vehicle(html: str, *, price: int | None = None) -> Vehicle:
    parsed = parse_vehicle(html, "https://www.lowdhams.com/vehicle/x", rrp_pounds=price)
    assert parsed is not None
    return parsed


# --- identity --------------------------------------------------------------------------


def test_airstream_is_one_word_and_a_caravan() -> None:
    """The marque, not the importer: NCC file the supplier as Lowdhams and they differ."""
    assert MANUFACTURER == "Airstream"
    assert MANUFACTURER_DISPLAY_NAME == "Airstream"
    assert VEHICLE_CLASS is VehicleClass.CARAVAN


def test_the_browse_page_is_the_only_roster(browse: str) -> None:
    paths = find_vehicle_paths(browse)
    assert len(paths) == 4
    assert all(path.startswith("/vehicle/") for path in paths)


# --- the price, which only the browse page carries ---------------------------------------


def test_the_price_comes_off_the_card(browse: str) -> None:
    prices = {path: card.rrp_pounds for path, card in parse_cards(browse).items()}
    assert prices["/vehicle/new-airstream-international-684-caravan-450280"] == 109950
    assert prices["/vehicle/new-airstream-world-traveller-22rb-caravan-451790"] == 72995
    assert prices["/vehicle/new-airstream-international-534-caravan-424170"] == 97950


def test_the_monthly_finance_figure_is_not_the_price(browse: str) -> None:
    """Each card prints `£1,229 / Monthly` beside `Only £109,950`.

    It is the *smaller* of the two and it comes *first* in some cards, so neither "the
    lowest price" nor "the first price" picks the right one. The reading is anchored on
    the word `Only`.
    """
    assert "1,229" in browse
    assert all(
        card.rrp_pounds is None or card.rrp_pounds >= MINIMUM_CREDIBLE_PRICE
        for card in parse_cards(browse).values()
    )


def test_a_vehicle_page_carries_no_price_of_its_own(i534: str) -> None:
    """Which is why the browse page is fetched at all rather than just for its links."""
    assert _vehicle(i534).rrp_pounds is None


# --- the specification block ---------------------------------------------------------------


def test_the_range_and_model_are_stated_separately(i534: str, wt22rb: str) -> None:
    """FMLV's own split, published as two fields — nothing has to be derived from a name."""
    assert (_vehicle(i534).manufacturer_range, _vehicle(i534).model) == ("International", "534")
    assert (_vehicle(wt22rb).manufacturer_range, _vehicle(wt22rb).model) == (
        "World Traveller",
        "22RB",
    )


def test_berths_and_axles_are_read(i684: str) -> None:
    vehicle = _vehicle(i684)
    assert vehicle.berths == 4
    assert vehicle.twin_axle is True


def test_a_single_axle_is_false_and_not_merely_absent(i534: str) -> None:
    """`None` would mean "the page did not say", which is a different thing."""
    assert _vehicle(i534).twin_axle is False


def test_a_label_whose_value_is_missing_does_not_take_the_next_label() -> None:
    """The block is a flat run of alternating labels and values, so a gap would shift
    everything after it by one and quietly pair `Model` with `MTPLM`."""
    spec = parse_specification(
        '<div id="product-specs"><div>Range</div><div>Model</div><div>534</div>'
        '<div>Berths</div><div>4</div></div>'
    )
    assert "Range" not in spec
    assert spec["Model"] == "534"
    assert spec["Berths"] == "4"


def test_a_page_with_no_specification_block_is_not_a_vehicle() -> None:
    assert parse_vehicle("<html><body>Nothing here</body></html>", "http://x") is None


# --- what makes something a product ----------------------------------------------------------


def test_the_used_25_ib_is_not_the_current_range(used25ib: str) -> None:
    """Dropped on its `Condition`, which every card states, rather than on its slug."""
    vehicle = _vehicle(used25ib)
    assert vehicle.condition == "Used"
    assert vehicle.is_new is False


def test_the_three_new_caravans_are_the_expected_count(
    i534: str, i684: str, wt22rb: str
) -> None:
    assert EXPECTED_PRODUCTS == 3
    assert all(_vehicle(html).is_new for html in (i534, i684, wt22rb))


# --- the MTPLM, which is the whole reason this adapter is careful --------------------------------


def test_the_534s_mtplm_is_its_bands_lower_limit_and_is_refused(i534: str) -> None:
    """1830kg is Airstream's published *floor*; FMLV holds the 1900kg upper limit."""
    vehicle = _vehicle(i534)
    assert vehicle.stock_mtplm_kilograms == 1830
    verdict = plating_verdict(vehicle.model, vehicle.stock_mtplm_kilograms)
    assert "downplate" in verdict
    assert "1900kg" in verdict
    assert "Nothing is proposed" in verdict


def test_the_684s_plate_falls_outside_the_published_band(i684: str) -> None:
    """2400kg against a published 2500-2920kg. Whatever it is, it is not the model's."""
    vehicle = _vehicle(i684)
    assert vehicle.stock_mtplm_kilograms == 2400
    assert "OUTSIDE" in plating_verdict(vehicle.model, vehicle.stock_mtplm_kilograms)


def test_a_plate_at_the_upper_limit_is_recognised_as_the_models_own(wt22rb: str) -> None:
    """The World Traveller reads 2000kg, which its brochure and FMLV both give."""
    vehicle = _vehicle(wt22rb)
    assert vehicle.stock_mtplm_kilograms == 2000
    assert "upper limit" in plating_verdict(vehicle.model, vehicle.stock_mtplm_kilograms)


def test_an_unknown_model_is_placed_against_nothing() -> None:
    assert "nothing to place it against" in plating_verdict("999ZZ", 2000)


def test_every_published_band_runs_lower_to_upper() -> None:
    for model, published in EUROPEAN_SPECIFICATION.items():
        assert published.mro_kilograms < published.mtplm_lower_kilograms, model
        assert published.mtplm_lower_kilograms <= published.mtplm_upper_kilograms, model


def test_the_published_uppers_are_what_fmlv_holds() -> None:
    """FMLV's MTPLMs came from this table and must not be displaced by a showroom plate."""
    assert EUROPEAN_SPECIFICATION["534"].mtplm_upper_kilograms == 1900
    assert EUROPEAN_SPECIFICATION["684"].mtplm_upper_kilograms == 2920
    assert EUROPEAN_SPECIFICATION["25 IB"].mtplm_upper_kilograms == 3500
    assert EUROPEAN_SPECIFICATION["22RB"].mtplm_upper_kilograms == 2000


# --- nothing dimensional is ever built --------------------------------------------------------


def test_no_mass_and_no_dimension_reaches_the_product(i684: str) -> None:
    built = build_extracted(_vehicle(i684, price=109950), basis="test")
    caravan = built.caravan
    assert caravan.mtplm_kilograms is None
    assert caravan.mro_kilograms is None
    assert caravan.personal_effects_payload_kilograms is None
    assert caravan.shipping_length_mm is None
    assert caravan.overall_width_mm is None
    assert caravan.height_mm is None


def test_none_of_the_refused_fields_is_given_provenance(i684: str) -> None:
    """`compare_fields` must not even be invited to look at them."""
    built = build_extracted(_vehicle(i684, price=109950), basis="test")
    for refused in (
        "mtplm_kilograms",
        "mro_kilograms",
        "shipping_length_mm",
        "overall_width_mm",
        "height_mm",
    ):
        assert refused not in built.provenance


def test_the_overall_height_is_read_only_so_it_can_be_refused(wt22rb: str) -> None:
    """2.00m on the page against 2740 in FMLV, because it is the *interior* height: the
    brochure prints `Exterior height 2.74 m` and `Interior height 2 m`."""
    assert _vehicle(wt22rb).stock_dimensions["Overall Height"] == "2.00m"
    assert EUROPEAN_SPECIFICATION["22RB"].height_mm == 2740


# --- what is built ------------------------------------------------------------------------------


def test_the_fields_that_are_proposed_are_exactly_these(i684: str) -> None:
    built = build_extracted(_vehicle(i684, price=109950), basis="the card")
    assert sorted(built.provenance) == [
        "berths",
        "body_type",
        "manufacturer_range",
        "model",
        "price_min_range_pounds",
        "rrp_pounds",
        "twin_axle",
    ]


def test_an_airstream_is_a_rigid_caravan(i534: str) -> None:
    body_type, reason = body_type_for(_vehicle(i534))
    assert body_type is CaravanBodyType.RIGID
    assert "1250kg" in reason


def test_the_micro_test_is_applied_rather_than_assumed() -> None:
    """A caravan is a micro only where it is named one *and* is at or under 1250kg. If a
    future Airstream came in under that ceiling the body type would be left blank, not
    asserted."""
    light = Vehicle(url="http://x", manufacturer_range="International", model="LIGHT")
    EUROPEAN_SPECIFICATION["LIGHT"] = EUROPEAN_SPECIFICATION["534"].__class__(
        900, 1100, 1200, 4000, 2500, 2100
    )
    try:
        body_type, reason = body_type_for(light)
        assert body_type is None
        assert "micro" in reason
    finally:
        del EUROPEAN_SPECIFICATION["LIGHT"]


# --- the habitation findings ----------------------------------------------------------------------


def test_a_priced_extra_is_not_read_as_equipment(i534: str) -> None:
    """The 534's list carries `Motor mover (Optional Extra)` among its features."""
    features = parse_features(i534)
    assert "Motor mover (Optional Extra)" in features
    built = build_extracted(_vehicle(i534), basis="test")
    assert "Motor mover" not in str(built.provenance)


def test_the_dealership_copy_is_cut_off(i534: str) -> None:
    """Warranty, part exchange and insurance follow the features in the same block and
    read as equipment if they are not stopped at."""
    features = parse_features(i534)
    assert "3 burner hob" in features
    assert not any("warranty" in line.lower() for line in features)
    assert not any("part exchange" in line.lower() for line in features)


def test_a_page_with_no_features_block_yields_nothing(i684: str) -> None:
    """Two of the four pages carry none at all, which is ordinary rather than a failure."""
    assert parse_features(i684) == []


def test_full_central_heating_is_left_unresolved(i534: str) -> None:
    """Deliberate. Every other `central heating` line in this repo's fixtures carries
    `Alde` or `radiator` and is wet — but one reads `Truma diesel central heating`, which
    is warm air. The bare phrase does not settle the kind, so the run narrates it instead
    of teaching the shared vocabulary something false."""
    assert "Full central heating" in parse_features(i534)
    built = build_extracted(_vehicle(i534), basis="test")
    assert built.caravan.heating is None
    assert "heating" not in built.provenance
