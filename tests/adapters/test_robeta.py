"""Robeta's parsing, against the pages the two sites actually served on 11 November 2026.

Pure parsing only: no network. The fixtures are Cara Motorhomes' Adonis and Schumacher
Edition range pages, their Robeta section index, and two factory pages.

The negative tests here are the traps the survey found waiting: Cara's stock listings,
which carry five other manufacturers' vehicles under a near-identical URL; the factory
models the UK does not get; and the published capacity spans, which look like berth counts
and are not.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters import robeta

FIXTURES = Path(__file__).parent / "fixtures"


def _text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def cara_adonis() -> str:
    return _text("robeta-cara-adonis.html")


@pytest.fixture
def cara_schumacher() -> str:
    return _text("robeta-cara-schumacher-edition.html")


@pytest.fixture
def cara_section() -> str:
    return _text("robeta-cara-robeta-section.html")


@pytest.fixture
def factory_ares() -> str:
    return _text("robeta-factory-ares.html")


@pytest.fixture
def factory_lineup() -> str:
    return _text("robeta-factory-lineup.html")


def _adonis(page: str) -> robeta.RobetaProduct:
    return robeta.parse_range_page(page, "Adonis", "adonis", "https://example.invalid")


# --------------------------------------------------------------------------- #
# The roster
# --------------------------------------------------------------------------- #


def test_the_roster_is_the_six_models_cara_list(cara_section: str, cara_adonis: str) -> None:
    slugs = robeta.parse_roster(cara_section, cara_adonis)

    assert set(slugs) == {model.slug for model in robeta.MODELS}
    assert len(slugs) == robeta.EXPECTED_PRODUCTS


def test_a_stock_listing_is_never_read_as_a_model() -> None:
    """Cara's `/vehicle-details/` pages are individual units for sale.

    A mass on one is that van's plate and that van's options. Worse, the same URL shape
    carries Sunlight, Adria, Auto-Trail, Coachman and VW stock, so a loose match would
    collect other manufacturers' vehicles outright.
    """
    index = """
      <a href="/robeta-motorhomes/the-range/ares/">Ares</a>
      <a href="/vehicle-details/new-robeta-apollo-for-sale-cara-motorhomes-caravans-ltd-n447/">one van</a>
      <a href="/vehicle-details/new-sunlight-cliff-540-adventure-for-sale-cara-motorhomes-caravans-ltd-n557/">a Sunlight</a>
    """

    assert robeta.parse_roster(index) == ["ares"]


def test_every_model_cara_list_is_one_this_adapter_knows(cara_section: str) -> None:
    """`collect` narrates an unknown slug; this is what keeps the map honest meanwhile."""
    for slug in robeta.parse_roster(cara_section):
        assert slug in {model.slug for model in robeta.MODELS}


def test_the_factory_models_the_uk_does_not_get_are_listed_but_not_collected() -> None:
    assert set(robeta.NOT_SOLD_IN_THE_UK) == {"hercules", "dionysus", "ananya"}
    assert not {model.slug for model in robeta.MODELS} & set(robeta.NOT_SOLD_IN_THE_UK)


def test_the_factory_lineup_still_shows_a_model_the_uk_does_not_get(
    factory_lineup: str,
) -> None:
    """The watch in `_check_factory_roster` only works while this holds."""
    assert "hercules" in factory_lineup.lower()


# --------------------------------------------------------------------------- #
# Cara's table
# --------------------------------------------------------------------------- #


def test_the_price_and_every_published_figure_is_read(cara_adonis: str) -> None:
    product = _adonis(cara_adonis)

    assert product.rrp_pounds == 105_290
    assert product.mro_kilograms == 2_980
    assert product.mtplm_kilograms == 3_500
    assert product.mh_payload_kilograms == 520
    assert product.mh_length_mm == 5_930
    assert product.mh_width_mm == 2_070
    assert product.mh_height_mm == 2_690


def test_the_chassis_is_read_from_caras_prose(cara_adonis: str) -> None:
    """*"The 5.93m Robeta Adonis built on the Mercedes Sprinter chassis"*."""
    product = _adonis(cara_adonis)

    assert product.base_vehicle is not None
    assert product.base_vehicle.lower().startswith("mercedes")


def test_the_schumacher_edition_is_read_the_same_way(cara_schumacher: str) -> None:
    """The one model at a different scale: 5.5 tonnes and a quarter of a million pounds."""
    product = robeta.parse_range_page(
        cara_schumacher, "Schumacher Edition", "schumacher-edition", "https://example.invalid"
    )

    assert product.rrp_pounds == 272_331
    assert product.mtplm_kilograms == 5_500
    assert product.mh_payload_kilograms == 1_375


def test_the_payload_reconciles_against_the_other_two_masses(cara_adonis: str) -> None:
    reconciles, note = robeta._reconciles(_adonis(cara_adonis))

    assert reconciles
    assert "520" in note


def test_a_mass_landing_on_the_wrong_row_is_dropped(cara_adonis: str) -> None:
    """The failure this check exists for: a plausible mass attached to the wrong label."""
    product = _adonis(cara_adonis)
    product.mro_kilograms = 2_890

    reconciles, note = robeta._reconciles(product)

    assert not reconciles
    assert "but Cara publish a payload of 520kg" in note


def test_a_product_missing_a_mass_is_dropped_rather_than_passed_through(
    cara_adonis: str,
) -> None:
    """All six publish all three, so an absence means the page changed shape."""
    product = _adonis(cara_adonis)
    product.mh_payload_kilograms = None

    reconciles, note = robeta._reconciles(product)

    assert not reconciles
    assert "missing payload" in note


# --------------------------------------------------------------------------- #
# The factory's JSON-LD
# --------------------------------------------------------------------------- #


def test_the_factory_properties_are_read_from_json_ld(factory_ares: str) -> None:
    properties = robeta.factory_properties(factory_ares)["ROBETA ARES"]

    assert properties["Sleeping Capacity"] == "2 - 6"
    assert properties["Pop-up Roof Bed Dimensions"] == "200 x 160 cm"
    assert properties["Refrigerator"] == "65L pull-out drawer compressor fridge"


def test_one_page_can_carry_several_products(factory_lineup: str) -> None:
    """The Adonis's own page has no Product block and embeds the whole lineup array."""
    found = robeta.factory_properties(factory_lineup)

    assert len(found) >= 5
    assert "ROBETA ADONIS" in found
    assert found["ROBETA ADONIS"]["Sleeping Capacity"] == "2 - 4"


def test_a_page_with_no_json_ld_yields_nothing() -> None:
    assert robeta.factory_properties("<html><body>nothing here</body></html>") == {}
    assert robeta.factory_properties('<script type="application/ld+json">{oops</script>') == {}


# --------------------------------------------------------------------------- #
# The open question
# --------------------------------------------------------------------------- #


def test_berths_seats_and_body_type_are_never_proposed(
    cara_adonis: str, factory_lineup: str
) -> None:
    """The adapter's one deliberate gap — see `_build_extracted_motorhome`.

    Robeta publish a span of configurations, not the vehicle as built, and the pop-up roof
    that supplies the upper end is an upgrade. A field with no provenance is not proposed,
    so FMLV's own figures stand until the requester settles it with Cara.
    """
    product = _adonis(cara_adonis)
    product.factory = robeta.factory_properties(factory_lineup)["ROBETA ADONIS"]
    product.sleeping_capacity = product.factory.get("Sleeping Capacity")

    extracted = robeta._build_extracted_motorhome(product)

    assert extracted.motorhome.berths is None
    assert extracted.motorhome.mh_passenger_seats_inc_driver is None
    assert extracted.motorhome.body_type is None
    for name in ("berths", "mh_passenger_seats_inc_driver", "body_type"):
        assert name not in extracted.provenance


def test_every_uk_models_published_capacity_is_a_span_and_not_a_number(
    factory_lineup: str,
) -> None:
    """Which is why none of them can be read as a berth count.

    The one single figure on this page belongs to the **Hercules**, which no UK dealer
    lists and this adapter does not collect — so its being a plain `2` proves nothing
    about the six that are collected.
    """
    found = robeta.factory_properties(factory_lineup)
    uk = {model.factory_name for model in robeta.MODELS}

    spans = {
        name: props["Sleeping Capacity"]
        for name, props in found.items()
        if "Sleeping Capacity" in props and name in uk
    }
    assert spans
    assert all("-" in span for span in spans.values()), spans
    assert found["ROBETA HERCULES"]["Sleeping Capacity"] == "2"
    assert "ROBETA HERCULES" not in uk


def test_the_figures_that_are_proposed_all_carry_provenance(cara_adonis: str) -> None:
    extracted = robeta._build_extracted_motorhome(_adonis(cara_adonis))

    for name in (
        "rrp_pounds",
        "mro_kilograms",
        "mtplm_kilograms",
        "mh_payload_kilograms",
        "mh_length_mm",
        "mh_width_mm",
        "mh_height_mm",
        "base_vehicle_manufacturer",
    ):
        assert name in extracted.provenance, name
        assert extracted.provenance[name].snippet


def test_the_payload_provenance_states_the_arithmetic(cara_adonis: str) -> None:
    extracted = robeta._build_extracted_motorhome(_adonis(cara_adonis))

    assert "reconciles" in extracted.provenance["mh_payload_kilograms"].snippet


# --------------------------------------------------------------------------- #
# Wiring
# --------------------------------------------------------------------------- #


def test_the_manufacturer_is_spelled_with_one_t() -> None:
    """`Robeta` everywhere, confirmed by the requester on 11 November 2026.

    The NCC manufacturer list at id 255, the NCC supplier export dropdown, FMLV's export,
    Cara's URL and the factory's domain all agree. He says "Robetta" out loud.
    """
    assert robeta.MANUFACTURER == "Robeta"
    assert robeta.MANUFACTURER_DISPLAY_NAME == "Robeta"
    assert "robeta-motorhomes" in robeta.RANGE_INDEX_URL
    assert "robeta-campervans" in robeta.FACTORY_BASE_URL


def test_the_habitation_reading_is_rendered_as_a_reviewer_would_type_it(
    factory_ares: str,
) -> None:
    """`store.changes` shows habitation findings for NEW products only, and all six Robeta
    products are matched — so the run narration is the only place this reading appears.
    """
    from src.product_model.enums import BedType, Refrigeration

    assert robeta._feature_value(Refrigeration.FRIDGE_FREEZER) == "fridge_freezer"
    assert robeta._feature_value([BedType.MAKE_UP, BedType.FIXED]) == "make_up_beds;fixed_bed"
    assert robeta._feature_value([]) == "none"


def test_robetas_refrigerator_reads_as_a_fridge_freezer(factory_ares: str) -> None:
    """*"65L pull-out drawer compressor fridge"* — a litre figure and no word on a freezer.

    The house default for that case is `fridge_freezer`, and the requester confirmed on
    11 November 2026 that these do have a freezer section. FMLV holds plain `fridge` on
    five of the six and needs flipping by hand.
    """
    from src.adapters import gearbox, habitation

    lines = [" ".join(line.split()) for line in gearbox.lines_from_page(factory_ares)]
    features = habitation.features_from([line for line in lines if line])

    assert "refrigeration" in features
    assert robeta._feature_value(features["refrigeration"].value) == "fridge_freezer"


def test_every_model_is_offered_to_the_range_flag() -> None:
    assert {label for _, label in robeta.DEFAULT_RANGES} == {
        model.name for model in robeta.MODELS
    }
    assert len(robeta.DEFAULT_RANGES) == robeta.EXPECTED_PRODUCTS


def test_the_range_and_the_model_are_the_same_string(cara_adonis: str) -> None:
    """FMLV holds `Adonis`/`Adonis` on all six — the doubling Nova forces on one name."""
    motorhome = robeta._build_extracted_motorhome(_adonis(cara_adonis)).motorhome

    assert motorhome.manufacturer_range == motorhome.model == "Adonis"
