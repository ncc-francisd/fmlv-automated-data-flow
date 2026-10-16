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


def test_the_site_inos_contradicts_itself_and_is_refused(inos_site: Brochure) -> None:
    """2,600 + 1,000 is 3,600 against an MTPLM of 2,800. Nothing is recorded from a
    document that disagrees with itself."""
    ok, basis = _reconciles(inos_site)
    assert ok is False
    assert "does not close" in basis
    assert "3600kg" in basis


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


def test_the_celtic_rambler_states_no_berth_count(celtic: Brochure) -> None:
    """Its beds are described without a count — an island bed and a slide-out sofa that
    converts. Counting furniture is not deriving a berth figure."""
    assert celtic.berths is None
    assert "not derived from furniture" in celtic.berths_basis
    built = build_extracted(celtic, basis="b")
    assert "berths" not in built.provenance


def test_no_sleeping_capacity_is_reported_as_such() -> None:
    berths, basis = berths_from("a lovely caravan")
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
