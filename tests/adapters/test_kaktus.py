"""Kaktus's Next.js pages, captured 15 October 2026.

The fixtures are slices of the real pages, each checked at capture time to parse
identically to the whole. The configurator's fixture keeps its `<script>` tags, because
that is where its data lives — stripping them, which is right for every other HTML
adapter here, would empty it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters.kaktus import (
    EXPECTED_PRODUCTS,
    FMLV_WHEELBASE,
    MANUFACTURER,
    MANUFACTURER_DISPLAY_NAME,
    MINIMUM_CREDIBLE_PRICE,
    NOT_A_PRODUCT,
    ConfiguredModel,
    Option,
    Product,
    _notes,
    _reconciles,
    base_vehicle_from,
    berth_options,
    build_extracted,
    find_van_paths,
    flight_payload,
    parse_groups,
    parse_models,
    products_for,
    summary_rows,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def configure() -> str:
    return _fixture("kaktus_configure.html")


@pytest.fixture(scope="module")
def payload(configure: str) -> str:
    return flight_payload(configure)


@pytest.fixture(scope="module")
def groups(payload: str) -> dict[str, list[Option]]:
    return parse_groups(payload)


@pytest.fixture(scope="module")
def models(payload: str) -> list[ConfiguredModel]:
    return parse_models(payload)


# --- identity ------------------------------------------------------------------------------


def test_the_manufacturer_is_spelled_in_capitals() -> None:
    """`KAKTUS` is how the NCC list spells it and how the export's column reads; the
    display name and the supplier are both `Kaktus`."""
    assert MANUFACTURER == "KAKTUS"
    assert MANUFACTURER_DISPLAY_NAME == "Kaktus"


# --- the flight payload, which is the only trick this site needs ---------------------------------


def test_the_payload_decodes_without_a_browser(payload: str) -> None:
    """The page renders almost nothing as HTML; its data is in `self.__next_f` chunks."""
    assert len(payload) > 5_000
    assert '"basePrice"' in payload


def test_a_page_with_no_payload_decodes_to_nothing() -> None:
    assert flight_payload("<html><body>nothing here</body></html>") == ""


def test_an_undecodable_chunk_does_not_cost_the_rest() -> None:
    """The stream carries framing the page does not need; one bad chunk must not lose it."""
    html = (
        '<script>self.__next_f.push([1,"good "])</script>'
        "<script>self.__next_f.push([1,not-json])</script>"
        '<script>self.__next_f.push([1,"tail"])</script>'
    )
    assert flight_payload(html) == "good tail"


# --- the configurator ------------------------------------------------------------------------------


def test_both_models_and_their_base_prices_are_read(models: list[ConfiguredModel]) -> None:
    prices = {model.name: model.base_price for model in models}
    assert prices == {"Oasis": 157000, "Dune": 142000}


def test_the_option_prices_are_never_mistaken_for_a_vehicle(groups: dict[str, list[Option]]) -> None:
    """The configurator publishes about forty prices from £85 to £4,750 beside the two
    that matter, so any "lowest number on the page" reading buys a windscreen cover."""
    option_prices = [
        option.price for options in groups.values() for option in options if option.price
    ]
    assert len(option_prices) > 20
    assert min(option_prices) < 1_000
    assert max(option_prices) < MINIMUM_CREDIBLE_PRICE


def test_the_base_vehicle_comes_from_its_own_group(groups: dict[str, list[Option]]) -> None:
    base_vehicle, basis = base_vehicle_from(groups)
    assert base_vehicle == "MAN"
    assert "MAN TGE" in basis


# --- two models, four products -----------------------------------------------------------------------


def test_the_sleeping_layout_group_gives_the_berth_counts(groups: dict[str, list[Option]]) -> None:
    counts = [berths for berths, _option in berth_options(groups)]
    assert counts == [2, 4]


def test_two_routes_to_four_berths_still_make_one_product(groups: dict[str, list[Option]]) -> None:
    """A pop-top roof and a Cabbunk system both sleep four; FMLV holds one X4 per range."""
    labels = [option.label for option in groups["berths"]]
    assert sum("4-berth" in label for label in labels) == 2
    assert len(berth_options(groups)) == 2


def test_both_four_berth_options_are_price_on_application(groups: dict[str, list[Option]]) -> None:
    """Which is why the basePrice is recorded against the X4 as a "from" figure."""
    four_berth = [option for option in groups["berths"] if "4-berth" in option.label]
    assert four_berth
    assert all(option.poa for option in four_berth)
    assert all(option.price == 0 for option in four_berth)


def test_the_four_products_match_what_fmlv_holds(
    models: list[ConfiguredModel], groups: dict[str, list[Option]]
) -> None:
    identities = [
        product.identity
        for model in models
        for product in products_for(model, groups, url="http://x")
    ]
    assert sorted(identities) == [
        ("Dune", "X2 MWB"),
        ("Dune", "X4 MWB"),
        ("Oasis", "X2 LWB"),
        ("Oasis", "X4 LWB"),
    ]
    assert EXPECTED_PRODUCTS == 4


def test_the_wheelbase_is_fmlvs_answer_and_is_never_proposed(
    models: list[ConfiguredModel], groups: dict[str, list[Option]]
) -> None:
    """Kaktus publish `LWB` for the Oasis and name no wheelbase at all for the Dune, so
    the model string cannot be derived and must not be offered as a change."""
    assert FMLV_WHEELBASE == {"Oasis": "LWB", "Dune": "MWB"}
    oasis = next(model for model in models if model.name == "Oasis")
    built = build_extracted(products_for(oasis, groups, url="http://x")[0], basis="test")
    assert built.motorhome.model == "X2 LWB"
    assert "model" not in built.provenance


def test_an_unknown_range_is_dropped_rather_than_mis_named(groups: dict[str, list[Option]]) -> None:
    """Without a wheelbase there is no model string, and a wrong one would fail to match."""
    unknown = ConfiguredModel("sahara", "Sahara", "tier", "tagline", 160000)
    product = products_for(unknown, groups, url="http://x")[0]
    ok, basis = _reconciles(product)
    assert ok is False
    assert "FMLV_WHEELBASE" in basis


# --- Mojave ------------------------------------------------------------------------------------------


def test_mojave_is_named_as_not_a_product() -> None:
    assert "mojave" in NOT_A_PRODUCT
    reason = NOT_A_PRODUCT["mojave"]
    assert "April 2027" in reason
    assert "prototype" in reason


def test_mojave_is_linked_from_the_home_page() -> None:
    """So the exclusion is load-bearing: without it a prototype arrives as a product."""
    assert "/vans/mojave" in find_van_paths(_fixture("kaktus_home.html"))


def test_the_home_page_links_every_range() -> None:
    assert sorted(find_van_paths(_fixture("kaktus_home.html"))) == [
        "/vans/dune",
        "/vans/mojave",
        "/vans/oasis",
    ]


# --- the model pages, read only for habitation --------------------------------------------------------


def test_each_model_page_has_its_own_summary_labels() -> None:
    """The Oasis gives Drive, Water and Sleeps; the Dune gives Stance, Rack and Built for."""
    oasis = summary_rows(_fixture("kaktus_oasis.html"))
    dune = summary_rows(_fixture("kaktus_dune.html"))
    assert oasis["Base"] == "MAN TGE / VW Crafter"
    assert "diesel heater" in oasis["Water"]
    assert dune["Base"] == "MAN TGE 4MOTION"
    assert set(oasis) != set(dune)


def test_a_value_containing_a_quote_is_not_truncated() -> None:
    '''The Dune's stance reads `60mm lift · 16" off-road tyres`. In the flight payload
    that quote is escaped and a naive value pattern stops at it, losing the row.'''
    assert summary_rows(_fixture("kaktus_dune.html"))["Stance"].endswith('16" off-road tyres')


def test_a_wet_room_is_not_a_separated_washroom() -> None:
    """The Oasis's own tagline says `Full kitchen, wet room and Victron power`."""
    product = _product(berths=2)
    product.equipment = ["The flagship long-wheelbase build. Full kitchen, wet room."]
    built = build_extracted(product, basis="test")
    assert built.motorhome.shower_toilet_separated is False


def test_a_diesel_heater_alone_does_not_settle_the_heating_type() -> None:
    """Narrated rather than guessed: `75L fresh · 75L waste · diesel heater` names a
    heater without saying whether the system is blown air or wet."""
    product = _product(berths=2)
    product.equipment = ["Water: 75L fresh - 75L waste - diesel heater"]
    built = build_extracted(product, basis="test")
    assert built.motorhome.heating is None
    assert "heating" not in built.provenance
    assert any("its kind is not named" in note for note in _notes(product))


# --- what is built --------------------------------------------------------------------------------------


def _product(*, berths: int) -> Product:
    return Product(
        model=ConfiguredModel("oasis", "Oasis", "LWB", "tagline", 157000),
        berths=berths,
        berth_option=Option("2-berth", f"{berths}-berth", 0, berths > 2),
        url="http://x",
        base_vehicle_manufacturer="MAN",
        base_vehicle_basis="MAN, from the configurator",
    )


def test_no_mass_and_no_dimension_reaches_the_product() -> None:
    built = build_extracted(_product(berths=2), basis="test")
    motorhome = built.motorhome
    assert motorhome.mtplm_kilograms is None
    assert motorhome.mro_kilograms is None
    assert motorhome.mh_payload_kilograms is None
    assert motorhome.mh_length_mm is None
    assert motorhome.mh_width_mm is None
    assert motorhome.mh_height_mm is None
    for refused in ("mtplm_kilograms", "mro_kilograms", "mh_length_mm", "mh_height_mm"):
        assert refused not in built.provenance


def test_no_body_type_is_proposed() -> None:
    """No height is published, so the high-top half of the rule cannot be applied — and
    the elevating roof here is an option, not standard equipment."""
    built = build_extracted(_product(berths=4), basis="test")
    assert built.motorhome.body_type is None
    assert "body_type" not in built.provenance


def test_no_seat_count_is_proposed() -> None:
    """`Sleeps up to 4 · swivel cab seats` is a berth count, not a belted seat count."""
    built = build_extracted(_product(berths=2), basis="test")
    assert built.motorhome.mh_passenger_seats_inc_driver is None
    assert "mh_passenger_seats_inc_driver" not in built.provenance


def test_the_four_berth_price_is_marked_as_a_from_figure() -> None:
    built = build_extracted(_product(berths=4), basis="the basePrice")
    assert "poa" in built.provenance["rrp_pounds"].snippet
    assert any("FROM" in note for note in _notes(_product(berths=4)))


def test_the_two_berth_price_carries_no_such_caveat() -> None:
    built = build_extracted(_product(berths=2), basis="the basePrice")
    assert "poa" not in built.provenance["rrp_pounds"].snippet


def test_a_price_below_the_floor_is_refused() -> None:
    cheap = Product(
        model=ConfiguredModel("oasis", "Oasis", "LWB", "t", 850),
        berths=2,
        berth_option=Option("2-berth", "2-berth", 0, False),
        url="http://x",
    )
    ok, basis = _reconciles(cheap)
    assert ok is False
    assert "option price" in basis
