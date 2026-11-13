"""Project Yonder's parsing, against the five pages their site actually served.

Pure parsing only: no network. The fixtures are unmodified captures of
projectyonder.co.uk taken on 12 November 2026, each one carrying the inlined
`window.__remixContext` payload the adapter reads.

Every negative test here is a trap that was hit while the adapter was being written, or
one the survey found waiting: the sentence that offers an upgrade and fits a fridge in the
same breath, the FAQ answer that renders empty, the model page that still calls itself by
the old name, the two pages that disagree about what the van weighs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters import habitation, project_yonder
from src.product_model.enums import BodyType, Heating, Refrigeration

FIXTURES = Path(__file__).parent / "fixtures"


def _page(name: str) -> str:
    return (FIXTURES / f"project-yonder-{name}.html").read_text(encoding="utf-8")


@pytest.fixture
def home() -> str:
    return _page("home")


@pytest.fixture
def faq() -> project_yonder.Faq:
    return project_yonder.parse_faq(_page("faqs"))


def _product(slug: str, fixture: str) -> project_yonder.YonderProduct:
    return project_yonder.parse_model_page(
        _page(fixture), slug, f"{project_yonder.BASE_URL}/{slug}"
    )


@pytest.fixture
def nomad() -> project_yonder.YonderProduct:
    return _product("nomad", "nomad")


@pytest.fixture
def freedom() -> project_yonder.YonderProduct:
    return _product("freedom-4x", "freedom-4x")


@pytest.fixture
def utility() -> project_yonder.YonderProduct:
    return _product("freedom-4x-utility", "utility")


# --------------------------------------------------------------------------- #
# The payload
# --------------------------------------------------------------------------- #


def test_the_story_comes_out_of_the_inlined_payload(nomad: project_yonder.YonderProduct) -> None:
    """Nothing here is read from markup: a styled tile has no stable class."""
    assert nomad.story_name == "NOMAD"
    assert nomad.published.startswith("2026-09-07")


def test_the_homepage_story_sits_under_a_different_route(home: str) -> None:
    """A content page uses the catch-all route; the homepage has one of its own."""
    story = project_yonder.remix_story(home)
    assert project_yonder._blocks(story.get("content", {}), "cta_image_block")


def test_a_page_without_a_payload_is_an_error_not_an_empty_result() -> None:
    """Every figure comes from the payload, so its absence is not something to survive."""
    with pytest.raises(ValueError, match="no window.__remixContext"):
        project_yonder.remix_story("<html><body>Project Yonder</body></html>")


def test_tiles_are_keyed_on_their_label_not_their_position(
    freedom: project_yonder.YonderProduct,
) -> None:
    """The Freedom 4X carries eight tiles in two groups; the Nomad carries four."""
    tiles = project_yonder.spec_tiles(project_yonder.remix_story(_page("freedom-4x")))
    assert tiles["GVW"] == "4.1T"
    assert tiles["LENGTH"] == "7.0M"
    assert tiles["AUTOMATIC"] == "9-TRONIC"
    assert freedom.mtplm_kilograms == 4100


# --------------------------------------------------------------------------- #
# The roster
# --------------------------------------------------------------------------- #


def test_the_homepage_is_the_only_index_and_lists_three_campervans(home: str) -> None:
    cards, others = project_yonder.parse_roster(home)
    assert [card.slug for card in cards] == list(project_yonder.MODELS)
    assert len(cards) == project_yonder.EXPECTED_PRODUCTS


def test_the_gear_shop_is_told_from_a_model_by_its_link_not_its_name(home: str) -> None:
    """A model card links to a Storyblok story; the shop links off-site."""
    _cards, others = project_yonder.parse_roster(home)
    assert others == ["GEAR SHOP"]
    assert "GEAR SHOP" in project_yonder.NOT_A_MODEL


def test_the_card_subtitle_carries_the_wheelbase_that_joins_to_the_faq(home: str) -> None:
    cards, _others = project_yonder.parse_roster(home)
    found = {card.slug: project_yonder.wheelbase_of(card) for card in cards}
    assert found["nomad"] == ("MWB", "140")
    assert found["freedom-4x"] == ("LWB", "170")
    assert found["freedom-4x-utility"] == ("LWB", "170")


# --------------------------------------------------------------------------- #
# The FAQ, whose answers do not render
# --------------------------------------------------------------------------- #


def test_the_faq_answers_are_read_although_the_page_renders_them_empty(
    faq: project_yonder.Faq,
) -> None:
    """Collapsed accordions: fifteen questions on screen and not one answer."""
    assert len(faq.answers) == 15
    assert "How big are your vans?" in faq.answers


def test_the_faq_is_the_only_place_a_width_or_height_is_published(
    faq: project_yonder.Faq,
) -> None:
    assert faq.dimensions == {
        "MWB": (6000, 2100, 2900),
        "LWB": (7000, 2100, 2900),
    }


def test_the_faq_gross_weight_disagrees_with_every_model_page(
    faq: project_yonder.Faq, nomad: project_yonder.YonderProduct
) -> None:
    """Unresolvable from the site, so narrated every run rather than fixed in code."""
    assert faq.gross_weight_kilograms == 4400
    assert nomad.mtplm_kilograms == 4100


def test_each_faq_price_keeps_the_heading_that_says_which_van_it_prices(
    faq: project_yonder.Faq,
) -> None:
    """`AWD model from £169,725 OTR` on its own does not say what it is pricing."""
    assert faq.price_lines == [
        'Freedom 4X 140" (MWB) — RWD model from £152,775 OTR',
        'Freedom 4X 140" (MWB) — AWD model from £164,775 OTR',
        'Freedom 4X 170" (LWB) — RWD model from £157,895 OTR',
        'Freedom 4X 170" (LWB) — AWD model from £169,725 OTR',
    ]


def test_a_wheelbase_only_claims_its_own_faq_prices(faq: project_yonder.Faq) -> None:
    """Quoting the long van's price against the short one is a wrong conflict."""
    assert all("(MWB)" in line for line in faq.prices_for("MWB"))
    assert len(faq.prices_for("MWB")) == 2
    assert len(faq.prices_for("LWB")) == 2
    assert faq.prices_for("SWB") == []


def test_the_faq_settles_the_base_vehicle_and_the_gearbox_for_the_whole_range(
    faq: project_yonder.Faq,
) -> None:
    assert faq.base_vehicle == "Mercedes-Benz"
    assert faq.automatic_line is not None
    assert "automatic transmission as standard" in faq.automatic_line


# --------------------------------------------------------------------------- #
# A model page
# --------------------------------------------------------------------------- #


def test_every_model_publishes_a_price_a_length_and_a_gross_weight(
    nomad: project_yonder.YonderProduct,
    freedom: project_yonder.YonderProduct,
    utility: project_yonder.YonderProduct,
) -> None:
    assert (nomad.rrp_pounds, nomad.mh_length_mm, nomad.mtplm_kilograms) == (192625, 6000, 4100)
    assert (freedom.rrp_pounds, freedom.mh_length_mm, freedom.mtplm_kilograms) == (
        194775,
        7000,
        4100,
    )
    assert (utility.rrp_pounds, utility.mh_length_mm, utility.mtplm_kilograms) == (
        194775,
        7000,
        4100,
    )


def test_a_published_range_of_berths_records_its_lower_figure(
    freedom: project_yonder.YonderProduct,
) -> None:
    """`2-4 BERTHS`: the other two need a pop-top roof or bunks, both options."""
    assert freedom.berths_text == "2-4"
    assert freedom.berths == 2


def test_the_belt_range_records_its_lower_figure_too(
    freedom: project_yonder.YonderProduct,
) -> None:
    """For a different reason: "Optional belted passenger seats"."""
    assert freedom.belts_text == "2-4"
    assert freedom.travel_seats == 2


def test_the_price_asterisk_does_not_reach_the_figure(
    freedom: project_yonder.YonderProduct,
) -> None:
    assert freedom.price_text == "£194,775*"
    assert freedom.rrp_pounds == 194775


def test_the_nomad_page_still_calls_itself_freedom_4x(
    nomad: project_yonder.YonderProduct,
) -> None:
    """The rename is live in the nav and unfinished in the page: narrated every run."""
    assert nomad.story_name == "NOMAD"
    assert nomad.seo_title == "Freedom 4X - The Ultimate AWD Motorhome"
    assert "nomad" in project_yonder._RENAMED_FROM


def test_the_range_name_follows_their_prose_not_their_styled_navigation(
    utility: project_yonder.YonderProduct,
) -> None:
    """`UTILITY` alone files a Freedom 4X variant as an unrelated range."""
    assert utility.story_name == "UTILITY"
    assert utility.manufacturer_range == "Freedom 4X Utility"
    assert utility.model == "LWB"


# --------------------------------------------------------------------------- #
# The self-check
# --------------------------------------------------------------------------- #


def test_the_length_reconciles_between_two_separately_edited_pages(
    nomad: project_yonder.YonderProduct, faq: project_yonder.Faq
) -> None:
    holds, note = project_yonder._reconciles(nomad, faq)
    assert holds
    assert "6,000mm" in note


def test_a_length_that_disagrees_with_the_faq_drops_the_product(
    nomad: project_yonder.YonderProduct, faq: project_yonder.Faq
) -> None:
    """This is what guards the width and height, read from a row chosen by wheelbase."""
    nomad.mh_length_mm = 7000
    holds, note = project_yonder._reconciles(nomad, faq)
    assert not holds
    assert "out of date" in note


def test_a_wheelbase_the_faq_says_nothing_about_is_not_treated_as_a_failure(
    nomad: project_yonder.YonderProduct, faq: project_yonder.Faq
) -> None:
    nomad.model = "SWB"
    holds, note = project_yonder._reconciles(nomad, faq)
    assert holds
    assert "no dimensions" in note


# --------------------------------------------------------------------------- #
# Cutting the marketing prose down to a specification
# --------------------------------------------------------------------------- #


def test_an_upgrade_sentence_does_not_fit_bunks_to_a_van_that_has_none() -> None:
    """Read whole, this put `fixed_bunks` on all three vans."""
    sentence = (
        "Optional belted passenger seats, cosy kids bunk beds or even an elevating "
        "pop-top roof will make your little ones dreams a reality."
    )
    assert project_yonder._standard_prose(sentence) == []
    assert habitation.features_from([sentence]).get("bed_types") is not None


def test_a_sentence_keeps_the_fitting_and_drops_the_catalogue_after_it() -> None:
    """The fridge is fitted; the microwave beside it is a price list."""
    sentence = (
        "Experience fast & efficient stove top cooking with a two ring induction hob "
        "plus a 90L fridge freezer & a variety of additional cooking options such as "
        "air fryer, microwave & coffee machine all supported by an extensive 24V "
        "Victron Energy electrical system."
    )
    kept = project_yonder._standard_prose(sentence)
    assert len(kept) == 1
    assert "90L fridge freezer" in kept[0]
    assert "microwave" not in kept[0].lower()


def test_the_shared_option_filter_could_not_have_caught_either_of_them() -> None:
    """It keys on a price or on `option:` with a colon — how a spec sheet writes an extra.

    Project Yonder have no spec sheet, which is why this filter had to be written.
    """
    prose = "Optional belted passenger seats, cosy kids bunk beds or even a pop-top roof."
    assert habitation.usable_lines([prose]) == [prose]


def test_a_fragment_left_behind_by_the_cut_is_not_kept() -> None:
    assert project_yonder._standard_prose("Our family friendly upgrades allow you to.") == []


# --------------------------------------------------------------------------- #
# The built product
# --------------------------------------------------------------------------- #


def _build(
    product: project_yonder.YonderProduct, faq: project_yonder.Faq
) -> project_yonder.ExtractedMotorhome:
    row = project_yonder._WHEELBASE_OF_FAQ_ROW.get(product.model)
    if row in faq.dimensions:
        length, width, height = faq.dimensions[row]
        product.mh_width_mm, product.mh_height_mm = width, height
        product.dimensions_from_faq = (
            f"Our {row} campervan is {length / 1000:g}m long x {width / 1000:g}m wide "
            f"x {height / 1000:g}m high."
        )
        if height > project_yonder.HIGH_TOP_ABOVE_MM:
            product.body_type = BodyType.CAMPERVAN_HIGH_TOP
    return project_yonder._build_extracted_motorhome(product, faq)


def test_the_width_and_height_come_off_the_faq_row_for_this_wheelbase(
    nomad: project_yonder.YonderProduct, faq: project_yonder.Faq
) -> None:
    built = _build(nomad, faq)
    assert (built.motorhome.mh_width_mm, built.motorhome.mh_height_mm) == (2100, 2900)
    assert built.provenance["mh_width_mm"].source_url == project_yonder.FAQ_URL


def test_a_fixed_roof_sprinter_at_2900mm_is_a_campervan_high_top(
    freedom: project_yonder.YonderProduct, faq: project_yonder.Faq
) -> None:
    built = _build(freedom, faq)
    assert built.motorhome.body_type is BodyType.CAMPERVAN_HIGH_TOP
    assert "option" in built.provenance["body_type"].snippet


def test_the_base_vehicle_is_abbreviated_the_way_fmlv_spells_it(
    freedom: project_yonder.YonderProduct, faq: project_yonder.Faq
) -> None:
    """Their pages say Mercedes-Benz; FMLV's base-vehicle column says Mercedes."""
    assert freedom.base_vehicle == "Mercedes-Benz"
    assert _build(freedom, faq).motorhome.base_vehicle_manufacturer == "Mercedes"


def test_a_model_page_that_names_no_make_falls_back_to_the_faq(
    utility: project_yonder.YonderProduct, faq: project_yonder.Faq
) -> None:
    assert utility.base_vehicle is None
    assert _build(utility, faq).motorhome.base_vehicle_manufacturer == "Mercedes"


def test_no_mass_in_running_order_and_no_payload_is_ever_emitted(
    freedom: project_yonder.YonderProduct, faq: project_yonder.Faq
) -> None:
    """Neither is published for anything, and there is no FMLV row to fall back on."""
    built = _build(freedom, faq)
    assert built.motorhome.mro_kilograms is None
    assert built.motorhome.mh_payload_kilograms is None
    assert "mro_kilograms" not in built.provenance
    assert "mh_payload_kilograms" not in built.provenance


def test_the_mtplm_provenance_says_the_faq_disagrees_with_it(
    nomad: project_yonder.YonderProduct, faq: project_yonder.Faq
) -> None:
    snippet = _build(nomad, faq).provenance["mtplm_kilograms"].snippet
    assert "4.1T" in snippet
    assert "4.4T" in snippet


def test_the_price_provenance_says_the_faq_disagrees_with_it(
    nomad: project_yonder.YonderProduct, faq: project_yonder.Faq
) -> None:
    snippet = _build(nomad, faq).provenance["rrp_pounds"].snippet
    assert "£164,775" in snippet
    assert "£169,725" not in snippet  # the long van's price, not this one's


def test_the_freedom_4x_page_settles_the_heating_and_the_fridge(
    freedom: project_yonder.YonderProduct, faq: project_yonder.Faq
) -> None:
    """A Truma D6 E is the Combi D 6 E — a warm-air heater with a boiler in it."""
    built = _build(freedom, faq)
    assert built.motorhome.heating is Heating.BLOWN_AIR
    assert built.motorhome.refrigeration is Refrigeration.FRIDGE_FREEZER
    assert "Truma D6 E" in built.provenance["heating"].snippet


def test_the_other_two_pages_get_no_habitation_finding_at_all(
    nomad: project_yonder.YonderProduct,
    utility: project_yonder.YonderProduct,
    faq: project_yonder.Faq,
) -> None:
    """They carry no equipment prose; claiming the Freedom 4X's kit is the robeta mistake."""
    for product in (nomad, utility):
        motorhome = _build(product, faq).motorhome
        assert motorhome.heating is None
        assert motorhome.refrigeration is None
        assert motorhome.shower_toilet_separated is None


def test_a_microwave_that_is_offered_is_not_a_microwave_that_is_fitted(
    freedom: project_yonder.YonderProduct, faq: project_yonder.Faq
) -> None:
    assert _build(freedom, faq).motorhome.microwave is None


def test_no_bed_type_is_claimed_for_anything(
    freedom: project_yonder.YonderProduct, faq: project_yonder.Faq
) -> None:
    """The only beds Project Yonder name anywhere are optional bunks."""
    assert _build(freedom, faq).motorhome.bed_types == []


def test_no_floorplan_exists_so_no_positional_field_is_answered_or_pointed_at(
    freedom: project_yonder.YonderProduct, faq: project_yonder.Faq
) -> None:
    built = _build(freedom, faq)
    for name in ("sleeping_area", "kitchen_location", "lounge_location"):
        assert getattr(built.motorhome, name) is None
        assert name not in built.provenance
    assert built.motorhome.bathroom_layout == []


def test_the_gearbox_is_the_only_one_offered_rather_than_an_option(
    freedom: project_yonder.YonderProduct, faq: project_yonder.Faq
) -> None:
    built = _build(freedom, faq)
    assert built.motorhome.automatic_available is True
    assert built.motorhome.automatic is None
    assert "no separate automatic price" in built.provenance["automatic_available"].snippet


def test_the_product_is_not_filed_under_its_own_name_twice(
    nomad: project_yonder.YonderProduct, faq: project_yonder.Faq
) -> None:
    motorhome = _build(nomad, faq).motorhome
    assert (motorhome.manufacturer_range, motorhome.model) == ("Nomad", "MWB")
    assert motorhome.manufacturer == project_yonder.MANUFACTURER == "Project Yonder"


# --------------------------------------------------------------------------- #
# What the run says, now that the conflicts are settled
# --------------------------------------------------------------------------- #


def _narration(
    faq: project_yonder.Faq, products: list[project_yonder.YonderProduct]
) -> list[str]:
    said: list[str] = []
    project_yonder._narrate_conflicts(faq, products, said.append)
    return said


def test_the_two_page_conflicts_are_reported_as_settled_not_as_questions(
    faq: project_yonder.Faq,
    nomad: project_yonder.YonderProduct,
    freedom: project_yonder.YonderProduct,
) -> None:
    """A rule decided once must not be put to a reviewer again on every run."""
    said = _narration(faq, [nomad, freedom])
    settled = [line for line in said if line.startswith("SETTLED BY RULE")]
    assert len(settled) == 2
    assert any("GROSS WEIGHT" in line and "4.1T" in line and "4.4T" in line for line in settled)
    assert any("THE PRICE" in line for line in settled)
    assert all("ASK" not in line for line in settled)


def test_the_conflicts_are_still_said_out_loud_so_a_new_one_would_surface(
    faq: project_yonder.Faq, nomad: project_yonder.YonderProduct
) -> None:
    """Applied silently, the rule could never be seen to be wrong."""
    assert any("4.4T" in line for line in _narration(faq, [nomad]))


def test_a_gross_weight_the_two_pages_agree_on_is_not_narrated_at_all(
    faq: project_yonder.Faq, nomad: project_yonder.YonderProduct
) -> None:
    nomad.gross_weight_text = "4.4T"
    assert not any("GROSS WEIGHT" in line for line in _narration(faq, [nomad]))


def test_the_mass_in_running_order_is_the_one_remaining_question(
    faq: project_yonder.Faq, nomad: project_yonder.YonderProduct
) -> None:
    """Payload needs no asking: it is the published gross weight less the MIRO."""
    asks = [line for line in _narration(faq, [nomad]) if line.startswith("ASK PROJECT YONDER")]
    assert len(asks) == 1
    assert "MASS IN RUNNING ORDER" in asks[0]
    assert "PAYLOAD DOES NOT NEED ASKING FOR" in asks[0]


def test_every_default_range_has_a_model_entry() -> None:
    assert len(project_yonder.DEFAULT_RANGES) == project_yonder.EXPECTED_PRODUCTS
    assert {slug for slug, _label in project_yonder.DEFAULT_RANGES} == set(
        project_yonder.MODELS
    )
