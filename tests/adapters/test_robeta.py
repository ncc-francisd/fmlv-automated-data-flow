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

from src.adapters import gearbox, habitation, robeta
from src.product_model.enums import BodyType

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
    """Cara's pages still list six; the UK range is eight.

    The Hercules and the Ananya were confirmed as 2027 UK range by Cara's own General
    Manager on 12 November 2026, while their website went on listing the original six.
    The importer's word defines the range, so the two are collected from the factory —
    see `robeta.FACTORY_ONLY` — and this roster parser is left reading exactly what Cara
    publish, which is how a Cara page appearing for either one gets noticed.
    """
    slugs = robeta.parse_roster(cara_section, cara_adonis)

    assert set(slugs) == {model.slug for model in robeta.MODELS if model.on_cara}
    assert len(slugs) == 6
    assert robeta.EXPECTED_PRODUCTS == 8


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
    """Only the Dionysus is left out now.

    The Hercules and the Ananya were in this set until 12 November 2026, when Cara named
    both as UK range for 2027. The Dionysus was not named, and still appears nowhere but
    the factory contact form's dropdown.
    """
    assert set(robeta.NOT_SOLD_IN_THE_UK) == {"dionysus"}
    assert not {model.slug for model in robeta.MODELS} & set(robeta.NOT_SOLD_IN_THE_UK)


def test_the_factory_lineup_carries_the_hercules_as_a_collected_model(
    factory_lineup: str,
) -> None:
    """It is on the lineup page, which is where its berth count comes from."""
    assert "hercules" in factory_lineup.lower()
    assert "Hercules" in {model.name for model in robeta.MODELS}


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


def test_four_three_point_belts_as_built_on_every_model_with_a_bench(
    cara_adonis: str,
) -> None:
    """The driver, the passenger and two on the bench behind.

    Settled by the requester on 11 November 2026. Only three-point belts count, which is
    the settled rule and the terms his figure is already stated in.
    """
    bench_models = (
        {model.name for model in robeta.MODELS if model.on_cara}
        - {"Schumacher Edition"}
    )
    assert {robeta.STANDARD_TRAVEL_SEATS[name] for name in bench_models} == {4}
    # The two 2027 additions are not covered by this judgement: they have no Cara page,
    # and their seat counts come off the factory page as published figures.
    assert not set(robeta.STANDARD_TRAVEL_SEATS) & robeta.FACTORY_ONLY

    motorhome = robeta._build_extracted_motorhome(_adonis(cara_adonis)).motorhome
    assert motorhome.mh_passenger_seats_inc_driver == 4


def test_the_schumacher_edition_has_two_seats_and_no_bench(cara_schumacher: str) -> None:
    """Robeta publish its `Seating Capacity` as `2` outright.

    It is a two-berth grand tourer with a floating bed and no rear bench, so the
    four-belt figure does not apply and recording it would contradict the maker.
    """
    assert robeta.STANDARD_TRAVEL_SEATS["Schumacher Edition"] == 2

    product = robeta.parse_range_page(
        cara_schumacher, "Schumacher Edition", "schumacher-edition", "https://example.invalid"
    )
    extracted = robeta._build_extracted_motorhome(product)

    assert extracted.motorhome.mh_passenger_seats_inc_driver == 2
    assert "no rear bench" in extracted.provenance["mh_passenger_seats_inc_driver"].snippet


def test_four_belts_agrees_with_every_published_seating_span(factory_lineup: str) -> None:
    """The check that makes the figure more than one person's word.

    The standard sits at a **different place in each span** — the lower end of the Ares's
    `4 - 5`, the upper end of the Adonis's `2 - 4`, the middle of the Apollo's `2 - 5` —
    and four is consistent with all of them. A span that merely contained four would prove
    nothing; two spans that *start* and *end* at four agree with it independently.
    """
    spans = {
        "ROBETA ARES": (4, 5),
        "ROBETA ADONIS": (2, 4),
        "ROBETA KRONOS": (2, 4),
        "ROBETA APOLLO": (2, 5),
        "ROBETA HELIOS": (2, 5),
    }
    for factory_name, (low, high) in spans.items():
        model = next(m for m in robeta.MODELS if m.factory_name == factory_name)
        assert low <= robeta.STANDARD_TRAVEL_SEATS[model.name] <= high, factory_name

    assert spans["ROBETA ARES"][0] == 4, "the Ares span starts at the standard"
    assert spans["ROBETA ADONIS"][1] == 4, "the Adonis span ends at the standard"


def test_every_model_has_two_berths_as_built(cara_adonis: str) -> None:
    """Settled by the requester, 11 November 2026, in two steps.

    The pop-up roof is an option on five models and standard on none; and on the three
    published as `2 - 6` the Family Edition's lifting bed is a *second* option. Strip both
    and two is left — which is also the lower end of every published span.
    """
    assert set(robeta.STANDARD_BERTHS) == {
        model.name for model in robeta.MODELS if model.on_cara
    }
    assert set(robeta.STANDARD_BERTHS.values()) == {2}
    # And deliberately does not cover the two 2027 additions — see `FACTORY_ONLY`.
    assert not set(robeta.STANDARD_BERTHS) & robeta.FACTORY_ONLY

    motorhome = robeta._build_extracted_motorhome(_adonis(cara_adonis)).motorhome
    assert motorhome.berths == 2


def test_the_schumacher_edition_is_the_one_with_no_roof_option() -> None:
    """*"the Schumacher edition does not have the option. That's the only one."*"""
    assert "Schumacher Edition" not in robeta.POP_TOP_OPTION
    assert robeta.POP_TOP_OPTION == {"Adonis", "Apollo", "Ares", "Helios", "Kronos"}


def test_every_robeta_is_a_plain_high_top(cara_adonis: str, cara_schumacher: str) -> None:
    """No model has an elevating roof as standard, so none is the elevating-roof type.

    FMLV held `campervan_high_top_elevating_roof` on the Helios and the Kronos, which this
    corrects. The height alone would not have settled it — the roof does.
    """
    for page, name, slug in (
        (cara_adonis, "Adonis", "adonis"),
        (cara_schumacher, "Schumacher Edition", "schumacher-edition"),
    ):
        product = robeta.parse_range_page(page, name, slug, "https://example.invalid")
        body_type, note = robeta._body_type(product)
        assert body_type is BodyType.CAMPERVAN_HIGH_TOP, name
        assert note is not None and "plain high top" in note


def test_a_campervan_under_the_threshold_gets_no_body_type(cara_adonis: str) -> None:
    """The threshold still has to be cleared — a height alone never decides the type."""
    product = _adonis(cara_adonis)
    product.mh_height_mm = 2_100

    assert robeta._body_type(product) == (None, None)


def test_every_uk_models_published_capacity_is_a_span_and_not_a_number(
    factory_lineup: str,
) -> None:
    """Which is why none of *them* can be read as a berth count.

    The one single figure on this page belongs to the **Hercules**, and that is exactly
    why the Hercules may be read straight off it while the other five may not: a span is
    a set of configurations needing a judgement about which options are standard, and a
    plain `2` is the vehicle as built. `_standard_berths_from` enforces the distinction.
    """
    found = robeta.factory_properties(factory_lineup)
    with_cara = {model.factory_name for model in robeta.MODELS if model.on_cara}

    spans = {
        name: props["Sleeping Capacity"]
        for name, props in found.items()
        if "Sleeping Capacity" in props and name in with_cara
    }
    assert spans
    assert all("-" in span for span in spans.values()), spans
    assert all(robeta._standard_berths_from(span) is None for span in spans.values())

    assert found["ROBETA HERCULES"]["Sleeping Capacity"] == "2"
    assert robeta._standard_berths_from("2") == 2


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


# --------------------------------------------------------------------------- #
# The two 2027 additions, which Cara have no page for
# --------------------------------------------------------------------------- #


@pytest.fixture
def factory_hercules() -> str:
    return _text("robeta-factory-hercules.html")


@pytest.fixture
def factory_ananya() -> str:
    return _text("robeta-factory-ananya.html")


def test_both_2027_additions_are_collected_from_the_factory() -> None:
    """Cara named them; Cara's website does not list them.

    John Burton, Cara's General Manager, to the NCC directory on 12 November 2026:
    *"There are 2 new models within the Robeta range for 2027, Hercules and Ananya."*
    The importer defines the range, so both are in scope — but Cara publish no page for
    either, and every number this adapter normally collects comes off a Cara page.
    """
    factory_only = {model.name for model in robeta.MODELS if not model.on_cara}
    assert factory_only == robeta.FACTORY_ONLY == {"Hercules", "Ananya"}


def test_the_hercules_essentials_list_reads(factory_hercules: str) -> None:
    specs = robeta.parse_launch_specs(factory_hercules)
    assert specs["Length"] == "6.97 m"
    assert specs["Travelling seats"] == "4"
    assert specs["Driving licence"] == "C1"
    assert specs["Refrigerator"] == "90 l · optional 140 l"


def test_the_hercules_publishes_no_mass_and_no_sterling_price(factory_hercules: str) -> None:
    """Its only price is tagged `eligibleRegion: DE`, and there is no mass at all.

    Converting the German figure would invent a UK price: this project's euro conversion
    assumes a domestic VAT-INCLUSIVE price, and that is what a German RRP is — at a
    German VAT rate, for a German buyer.
    """
    product = robeta.parse_factory_model_page(
        factory_hercules, "Hercules", "hercules", "https://example.invalid/models/hercules"
    )
    assert product.rrp_pounds is None
    assert product.mro_kilograms is None
    assert product.mtplm_kilograms is None
    assert product.mh_payload_kilograms is None
    assert "130,990" in factory_hercules.replace("&#x27;", "'")


def test_the_hercules_gives_a_length_seats_and_a_chassis(factory_hercules: str) -> None:
    product = robeta.parse_factory_model_page(
        factory_hercules, "Hercules", "hercules", "https://example.invalid/models/hercules"
    )
    assert product.mh_length_mm == 6970
    assert product.travel_seats == 4
    assert product.base_vehicle is not None
    assert product.base_vehicle.lower().startswith("mercedes")
    assert product.factory_only is True


def test_the_ananya_key_facts_list_reads(factory_ananya: str) -> None:
    facts = robeta.parse_key_facts(factory_ananya)
    assert facts["Vehicle Length"] == "6.97 meters"
    assert facts["Vehicle Height"] == "2.66 meters"
    assert facts["Number of Seats"] == "3"
    assert facts["Payload Capacity"] == "1,362 kg"


def test_the_ananya_gives_two_dimensions_and_three_seats(factory_ananya: str) -> None:
    product = robeta.parse_factory_model_page(
        factory_ananya, "Ananya", "ananya", "https://example.invalid/ananya"
    )
    assert product.mh_length_mm == 6970
    assert product.mh_height_mm == 2660
    assert product.travel_seats == 3


def test_the_ananya_publishes_two_candidate_plated_weights_so_neither_is_taken(
    factory_ananya: str,
) -> None:
    """*"Base chassis rating (Sprinter 419): 4,100 kg. Category B registration is possible
    only if the completed vehicle is homologated at 3,500 kg."*

    That is two plated weights and no way to tell which a UK buyer gets, so no mass is
    recorded at all. A payload without a MIRO or an MTPLM to sit against is not a figure
    FMLV can use either.
    """
    product = robeta.parse_factory_model_page(
        factory_ananya, "Ananya", "ananya", "https://example.invalid/ananya"
    )
    assert product.mtplm_kilograms is None
    assert product.mro_kilograms is None
    assert product.mh_payload_kilograms is None

    facts = robeta.parse_key_facts(factory_ananya)
    rating = facts["Base chassis rating (Sprinter 419)"]
    assert "4,100 kg" in rating
    assert "3,500 kg" in rating


def test_a_factory_only_product_emits_no_price_or_mass_provenance(
    factory_hercules: str,
) -> None:
    product = robeta.parse_factory_model_page(
        factory_hercules, "Hercules", "hercules", "https://example.invalid/models/hercules"
    )
    product.berths = 2
    extracted = robeta._build_extracted_motorhome(product)

    assert extracted.motorhome.berths == 2
    assert extracted.motorhome.mh_passenger_seats_inc_driver == 4
    assert extracted.motorhome.mh_length_mm == 6970
    for absent in (
        "rrp_pounds",
        "mro_kilograms",
        "mtplm_kilograms",
        "mh_payload_kilograms",
    ):
        assert absent not in extracted.provenance
    assert "Cara have no range page" in extracted.provenance["berths"].snippet


def test_a_plain_capacity_becomes_berths_and_a_span_never_does() -> None:
    """The whole distinction the two 2027 additions turn on."""
    assert robeta._standard_berths_from("2") == 2
    assert robeta._standard_berths_from("4") == 4
    assert robeta._standard_berths_from("2 - 6") is None
    assert robeta._standard_berths_from("2 + 2") is None
    assert robeta._standard_berths_from("2 to 4") is None
    assert robeta._standard_berths_from(None) is None


def test_no_body_type_without_a_height(factory_hercules: str) -> None:
    """The Hercules publishes no height, so its body type stays blank rather than guessed.

    It is plainly a high top in the photographs, but a dimension is what decides high top
    from standard here and there is no dimension.
    """
    product = robeta.parse_factory_model_page(
        factory_hercules, "Hercules", "hercules", "https://example.invalid/models/hercules"
    )
    assert product.mh_height_mm is None
    assert robeta._body_type(product) == (None, None)


def test_the_ananya_is_a_high_top_on_its_published_height(factory_ananya: str) -> None:
    product = robeta.parse_factory_model_page(
        factory_ananya, "Ananya", "ananya", "https://example.invalid/ananya"
    )
    body, note = robeta._body_type(product)
    assert body is BodyType.CAMPERVAN_HIGH_TOP
    assert note is not None and "2,660mm" in note


def test_a_page_with_neither_spec_block_yields_nothing() -> None:
    """Which is what `collect` drops on, rather than proposing an empty product."""
    product = robeta.parse_factory_model_page(
        "<html><body>coming soon</body></html>", "Hercules", "hercules", "https://x.invalid"
    )
    assert product.stated == {}
    assert product.mh_length_mm is None


def test_a_factory_only_product_reports_no_habitation(factory_ananya: str) -> None:
    """Because reading marketing copy produces confident nonsense.

    The Ananya's `refrigeration` came out of *"maybe a mini-fridge if you're lucky"* — a
    sentence about how **other** manufacturers build vans — and it would have reached a
    reviewer as a finding with that quotation attached. The five models with a Cara page
    are read from the factory's structured `additionalProperty` block instead, which
    these two do not have.
    """
    product = robeta.parse_factory_model_page(
        factory_ananya, "Ananya", "ananya", "https://example.invalid/ananya"
    )
    product.standard_lines = [
        " ".join(line.split()) for line in gearbox.lines_from_page(factory_ananya)
    ]
    assert habitation.features_from(product.standard_lines)  # the prose does yield some
    assert robeta._habitation_of(product) == {}  # and none of it is used

    extracted = robeta._build_extracted_motorhome(product)
    assert extracted.motorhome.refrigeration is None
    assert extracted.motorhome.heating is None
    assert extracted.motorhome.bed_types == []


def test_a_cara_model_still_reports_habitation(cara_adonis: str) -> None:
    """The guard above must not have switched it off for everybody."""
    product = _adonis(cara_adonis)
    product.standard_lines = ["85L compressor refrigerator", "separate shower and toilet"]
    assert robeta._habitation_of(product)


def test_a_factory_only_product_is_never_narrated_as_having_no_roof(
    factory_hercules: str,
) -> None:
    """The span narration asserts things only established for the six Cara models."""
    product = robeta.parse_factory_model_page(
        factory_hercules, "Hercules", "hercules", "https://example.invalid/models/hercules"
    )
    product.sleeping_capacity = "2"
    product.seating_capacity = "4"
    product.berths = 2

    said: list[str] = []
    robeta._narrate_open_questions(product, said.append)

    assert said, "a factory-only product should still be narrated"
    assert not [line for line in said if "no pop-up roof offered" in line]
    assert not [line for line in said if "three-point belted" in line]
    assert [line for line in said if "the factory page states" in line]
