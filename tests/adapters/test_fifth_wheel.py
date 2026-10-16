"""Fifth Wheel Co's brochures, captured 16 October 2026.

The fixtures are the extracted text of the pages that carry figures, and one slice of a
range page for the brochure link. Two INOS brochures are kept on purpose: the one the
site links and the one its email form sends, because they disagree and only one of them
adds up.

Almost every test here is about a figure *not* being recorded. These caravans slide
outwards, so every brochure publishes two widths; and one of the three documents
contradicts itself.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters.fifth_wheel import (
    EXPECTED_PRODUCTS,
    KNOWN_BERTHS,
    KNOWN_MASSES,
    MANUFACTURER,
    MANUFACTURER_DISPLAY_NAME,
    MANUFACTURER_SPELLING,
    RANGE_PATHS,
    RECORDED_LABELS,
    VEHICLE_CLASS,
    Brochure,
    _reconciles,
    berths_from,
    body_type_for,
    build_extracted,
    find_brochure_url,
    parse_brochure,
    parse_specification,
    price_from,
)
from src.product_model.enums import CaravanBodyType
from src.vehicle_class import VehicleClass

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _brochure(name: str, manufacturer_range: str) -> Brochure:
    return parse_brochure(
        _fixture(name), manufacturer_range=manufacturer_range, url="http://x/b.pdf"
    )


@pytest.fixture(scope="module")
def celtic() -> Brochure:
    return _brochure("fifth_wheel_celtic_rambler_brochure.txt", "Celtic Rambler")


@pytest.fixture(scope="module")
def dreamseeker() -> Brochure:
    return _brochure("fifth_wheel_dreamseeker_brochure.txt", "DreamSeeker")


@pytest.fixture(scope="module")
def inos_site() -> Brochure:
    return _brochure("fifth_wheel_inos_brochure_site.txt", "INOS")


@pytest.fixture(scope="module")
def inos_emailed() -> Brochure:
    return _brochure("fifth_wheel_inos_brochure_emailed.txt", "INOS")


# --- identity ------------------------------------------------------------------------------


def test_the_manufacturer_is_a_caravan_brand() -> None:
    assert MANUFACTURER == "Fifth Wheel Co"
    assert MANUFACTURER_DISPLAY_NAME == "Fifth Wheel Co"
    assert VEHICLE_CLASS is VehicleClass.CARAVAN
    assert len(RANGE_PATHS) == EXPECTED_PRODUCTS


def test_fmlvs_spelling_is_kept_over_the_manufacturers() -> None:
    """They write `Dreamseeker`; FMLV holds `DreamSeeker`. The export decides the identity
    strings, and a casing rename buys a reviewer nothing while touching the one thing a
    rename can corrupt."""
    assert "DreamSeeker" in RANGE_PATHS
    assert MANUFACTURER_SPELLING["DreamSeeker"] == "Dreamseeker"


def test_their_spelling_is_still_put_in_the_provenance(dreamseeker: Brochure) -> None:
    built = build_extracted(dreamseeker, basis="the arithmetic")
    assert "Dreamseeker" in built.provenance["manufacturer_range"].snippet


def test_the_brochure_link_is_found_on_the_range_page() -> None:
    """The email form is a gate on the interface; the page carries the file's own path."""
    url = find_brochure_url(_fixture("fifth_wheel_celtic_rambler_page.html"))
    assert url is not None
    assert url.endswith(".pdf")
    assert "/s/" in url


# --- the columnar table ----------------------------------------------------------------------


def test_the_label_and_value_columns_pair(celtic: Brochure) -> None:
    assert celtic.specification["overall length"].startswith("8.5m")
    assert celtic.specification["unit weight"].startswith("3,300kg")


def test_a_value_written_in_words_is_still_a_value(inos_site: Brochure) -> None:
    """The site's INOS writes `up to 1000kg` and `from 2800kg to 3,500kg`. A pattern
    anchored on a leading digit misses both, folds them into the line above and leaves
    fourteen labels against twelve values — refusing the whole table."""
    assert inos_site.specification["payload"].startswith("up to")
    assert inos_site.specification["mtplm"].startswith("from")


def test_a_square_metre_row_is_not_lost(celtic: Brochure) -> None:
    """`5.3m²` — and `²` is a word character in Unicode, so a boundary after the unit
    drops exactly those rows and unbalances the columns."""
    assert "additional slide out space" in celtic.specification


def test_a_wrapped_value_is_joined_back_on(celtic: Brochure) -> None:
    """`4,300kg (3,500kg if downplated` / `for towing on standard licence)`."""
    assert "standard licence" in celtic.specification["mtplm"]


def test_a_table_whose_columns_do_not_pair_is_refused() -> None:
    assert parse_specification("EXTERNAL DIMENSIONS\nOverall Width\nOverall Height\n2.3m") == {}


# --- the slide-out width, which is the whole risk -------------------------------------------------


def test_the_travelling_width_is_the_one_recorded(celtic: Brochure) -> None:
    built = build_extracted(celtic, basis="b")
    assert built.caravan.overall_width_mm == 2300
    assert celtic.specification["width with slide out extended"].startswith("3.3m")


def test_the_extended_width_has_no_fmlv_field(celtic: Brochure) -> None:
    """Kept out by its label, never by its magnitude."""
    assert "width with slide out extended" not in RECORDED_LABELS
    assert "width with slide out extended" in celtic.refused


def test_the_extended_width_is_named_in_the_width_provenance(celtic: Brochure) -> None:
    built = build_extracted(celtic, basis="b")
    assert "THE TRAVELLING WIDTH" in built.provenance["overall_width_mm"].snippet


# --- the fifth-wheel geometry -----------------------------------------------------------------------


def test_the_length_behind_the_tow_vehicle_is_the_shipping_length(
    celtic: Brochure, inos_emailed: Brochure
) -> None:
    """On a fifth-wheel it is shorter than the body, because the gooseneck overhangs the
    truck; on the conventionally-towed INOS it is longer. Both are FMLV's figures."""
    built = build_extracted(celtic, basis="b")
    assert built.caravan.shipping_length_mm == 6500
    assert built.caravan.exterior_body_length_mm == 8500

    inos = build_extracted(inos_emailed, basis="b")
    assert inos.caravan.shipping_length_mm == 8200
    assert inos.caravan.exterior_body_length_mm == 7000


# --- the self-check, and the document that fails it ----------------------------------------------------


def test_the_two_sound_brochures_reconcile(celtic: Brochure, dreamseeker: Brochure) -> None:
    for brochure in (celtic, dreamseeker):
        ok, basis = _reconciles(brochure)
        assert ok is True, basis
        assert "4300kg" in basis


def test_the_emailed_inos_reconciles_and_is_what_fmlv_holds(inos_emailed: Brochure) -> None:
    ok, _basis = _reconciles(inos_emailed)
    assert ok is True
    built = build_extracted(inos_emailed, basis="b")
    assert built.caravan.mro_kilograms == 2400
    assert built.caravan.personal_effects_payload_kilograms == 400
    assert built.caravan.mtplm_kilograms == 2800


def test_the_site_inos_masses_give_way_to_the_ones_that_add_up(inos_site: Brochure) -> None:
    """2,600 + 1,000 is 3,600 against an MTPLM of 2,800, so the fetched brochure's masses
    are not used. The requester settled it on the arithmetic, 16 October 2026: the figures
    recorded are the emailed brochure's, which reconcile and are what FMLV holds."""
    ok, basis = _reconciles(inos_site)
    assert ok is True
    assert "does NOT close" in basis
    assert inos_site.masses_overridden is True
    assert inos_site.figure("mro_kilograms") == 2400
    assert inos_site.figure("personal_effects_payload_kilograms") == 400
    assert inos_site.figure("mtplm_kilograms") == 2800


def test_the_overridden_masses_say_which_document_they_came_from(inos_site: Brochure) -> None:
    ok, basis = _reconciles(inos_site)
    assert ok
    built = build_extracted(inos_site, basis=basis)
    snippet = built.provenance["mro_kilograms"].snippet
    assert "send by email" in snippet
    assert "does not add up" in snippet


def test_the_dimensions_still_come_from_the_fetched_brochure(inos_site: Brochure) -> None:
    """Only the masses are overridden — the two INOS brochures agree on every dimension."""
    _ok, basis = _reconciles(inos_site)
    built = build_extracted(inos_site, basis=basis)
    assert built.caravan.exterior_body_length_mm == 7000
    assert built.caravan.shipping_length_mm == 8200
    assert built.caravan.overall_width_mm == 2300


def test_a_range_with_no_written_down_masses_is_still_refused() -> None:
    """The override is one manufacturer's confirmed answer, not a licence to accept any
    document that contradicts itself."""
    broken = Brochure(manufacturer_range="Celtic Rambler", url="http://x")
    broken.specification = {
        "unit weight": "3,300kg", "payload": "1,000kg", "mtplm": "9,999kg",
    }
    ok, basis = _reconciles(broken)
    assert ok is False
    assert "does not close" in basis


def test_the_two_inos_brochures_really_do_disagree(
    inos_site: Brochure, inos_emailed: Brochure
) -> None:
    assert inos_site.specification["unit weight"] != inos_emailed.specification["unit weight"]


# --- the downplate, and which figure is taken -------------------------------------------------------------


def test_the_figure_before_the_bracket_is_the_one_recorded(celtic: Brochure) -> None:
    """`4,300kg (3,500kg if downplated…)` — one chassis plated differently, so the band
    rule takes the upper figure, which is the one stated plainly."""
    built = build_extracted(celtic, basis="b")
    assert built.caravan.mtplm_kilograms == 4300
    assert built.caravan.personal_effects_payload_kilograms == 1000


def test_the_inos_base_chassis_figure_is_taken(inos_site: Brochure) -> None:
    """`from 2800kg to 3,500kg`, where the larger needs an upgraded chassis — so the
    base-vehicle rule applies and the base is read."""
    assert inos_site.figure("mtplm_kilograms") == 2800


# --- price and berths --------------------------------------------------------------------------------------


def test_the_price_comes_from_the_brochures_own_line(celtic: Brochure) -> None:
    assert celtic.rrp_pounds == 95000


def test_a_price_without_a_pound_sign_still_reads() -> None:
    """The pound sign does not survive extraction from these PDFs."""
    assert price_from("Prices from 77 ,500") == 77500


def test_berths_come_from_a_stated_count(dreamseeker: Brochure) -> None:
    assert dreamseeker.berths == 5


def test_the_celtic_ramblers_berths_come_from_the_requester(celtic: Brochure) -> None:
    """Its brochure describes an island king-size bed and a slide-out sofa that converts
    to a double, and states no count. The requester settled it at four on 16 October 2026,
    which is what FMLV holds — written down rather than counted off the furniture."""
    assert KNOWN_BERTHS["Celtic Rambler"][0] == 4
    assert celtic.berths == 4
    assert "confirmed by the requester" in celtic.berths_basis
    built = build_extracted(celtic, basis="b")
    assert "confirmed by the requester" in built.provenance["berths"].snippet


def test_the_brochures_own_count_beats_the_written_down_one() -> None:
    """So a range that starts stating a count is read from the document, not from here."""
    berths, basis = berths_from("Sleeps up to 6", manufacturer_range="Celtic Rambler")
    assert berths == 6
    assert "brochure's own" in basis


def test_a_range_with_neither_proposes_nothing() -> None:
    berths, basis = berths_from("a lovely caravan", manufacturer_range="Unknown")
    assert berths is None
    assert "no sleeping capacity" in basis


# --- what is built --------------------------------------------------------------------------------------------


def test_a_slide_out_caravan_is_still_rigid() -> None:
    body_type, reason = body_type_for(4300)
    assert body_type is CaravanBodyType.RIGID
    assert "no canvas" in reason
    assert "1250kg" in reason


def test_no_internal_length_is_proposed(celtic: Brochure) -> None:
    """The brochures publish an internal width and several internal heights, but no
    internal length."""
    built = build_extracted(celtic, basis="b")
    assert built.caravan.internal_length_mm is None
    assert "internal_length_mm" not in built.provenance


def test_an_identity_only_product_proposes_no_figure() -> None:
    """What a range whose brochure contradicts itself still emits, so that a live product
    is not reported as disappeared."""
    built = build_extracted(Brochure(manufacturer_range="INOS", url="http://x"), basis="b")
    assert built.caravan.manufacturer_range == "INOS"
    assert built.caravan.model == "INOS"
    assert built.caravan.mtplm_kilograms is None
    assert built.caravan.overall_width_mm is None
    assert "mtplm_kilograms" not in built.provenance
    assert "rrp_pounds" not in built.provenance


def test_the_floorplan_is_offered_as_a_reviewer_pointer(celtic: Brochure) -> None:
    """The positional fields can only be answered off a drawing by a person, and each
    range page carries a DAY and a NIGHT plan per layout variant. One pointer per
    unanswered field, so the link sits beside the question it answers."""
    built = build_extracted(celtic, basis="b")
    pointers = {
        name: p for name, p in built.provenance.items() if p.source_url.endswith("#layout")
    }
    assert pointers
    assert all("celtic-rambler" in p.source_url for p in pointers.values())
    assert any("DAY and NIGHT floorplans" in p.snippet for p in pointers.values())


def test_an_answered_field_gets_no_floorplan_pointer(celtic: Brochure) -> None:
    """There is nothing left to look up for a field the brochure already settled."""
    built = build_extracted(celtic, basis="b")
    assert built.caravan.berths == 4
    assert not built.provenance["berths"].source_url.endswith("#layout")


def test_the_self_check_says_the_same_thing_twice(inos_site: Brochure) -> None:
    """It tests the document's own masses, not the overridden ones — which were chosen
    because they reconcile, so checking those would always pass."""
    first = _reconciles(inos_site)
    second = _reconciles(inos_site)
    assert first == second
    assert "does NOT close" in second[1]
