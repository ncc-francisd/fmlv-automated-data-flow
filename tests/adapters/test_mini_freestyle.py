"""Mini Freestyle — parsing and derivation only, no network.

The fixtures are the two spec pages of the catalogue of 8 October 2026, as
`fetch.pdf.extract_text` returns them. The source PDF is deliberately not committed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters import ADAPTERS, adapter_for, mini_freestyle
from src.adapters.mini_freestyle import (
    EXPECTED_LAYOUTS,
    FMLV_RANGE,
    Specification,
    _reconciles,
    _value,
    build_extracted,
    catalogue_url,
    parse_specifications,
)
from src.product_model.enums import CaravanBodyType
from src.vehicle_class import VehicleClass

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def minis() -> str:
    """Page 2: the 270 and the 300."""
    return (FIXTURES / "mini-freestyle-catalogue-page2.txt").read_text(encoding="utf-8")


@pytest.fixture
def silver() -> str:
    """Page 4: the 290 and the 442."""
    return (FIXTURES / "mini-freestyle-catalogue-page4.txt").read_text(encoding="utf-8")


def _by_model(specs):
    return {spec.model: spec for spec in specs}


# --- registry -------------------------------------------------------------------------


def test_it_registers_under_trigano_with_the_mini_freestyle_display_name() -> None:
    """**Trigano is not a unique manufacturer.** The NCC list holds 187 Trigano/Silver and
    278 Trigano/Atom as well, and Atom is already an adapter here — so the display name is
    what tells them apart, and a registry row saying `Mini Freestyle` would find an empty
    baseline and propose every product as new."""
    assert mini_freestyle.MANUFACTURER == "Trigano"
    assert mini_freestyle.MANUFACTURER_DISPLAY_NAME == "Mini Freestyle"
    assert mini_freestyle.VEHICLE_CLASS is VehicleClass.CARAVAN
    assert (
        adapter_for("Trigano", VehicleClass.CARAVAN, display_name="Mini Freestyle")
        is mini_freestyle
    )
    assert ("Trigano", "Mini Freestyle", VehicleClass.CARAVAN) in ADAPTERS


def test_atom_still_resolves_on_the_same_manufacturer() -> None:
    """The check that this adapter has not displaced its sibling."""
    from src.adapters import atom

    assert adapter_for("Trigano", VehicleClass.MOTORHOME, display_name="Atom") is atom


# --- finding the catalogue ------------------------------------------------------------


def test_the_catalogue_url_is_read_not_constructed() -> None:
    """**Never hardcode it.** Its folder carries one year and its filename another, so the
    two already disagree and both will move."""
    html = '<a class="lien-catalogue" href="files/2026/Minifreestyle_catalogue_2025_EN.pdf">'

    assert catalogue_url(html) == (
        "https://www.mini-freestyle.com/files/2026/Minifreestyle_catalogue_2025_EN.pdf"
    )


def test_the_relative_href_keeps_its_files_prefix() -> None:
    """**The trap this exists for.** The hrefs on this site are relative; dropping the
    `files/` segment gives a URL that returns a 404 *page*, not a PDF, and the first
    attempt at this survey did exactly that."""
    url = catalogue_url('<a href="files/2026/cat.pdf">')

    assert url is not None and "/files/" in url


def test_a_page_with_no_catalogue_yields_nothing() -> None:
    assert catalogue_url('<a href="/en/about-us.html">About</a>') is None


# --- reading one cell -----------------------------------------------------------------


def test_a_decimal_comma_is_metres() -> None:
    assert _value("3,95", "m") == 3950
    assert _value("1,9", "m") == 1900


def test_an_asterisk_is_stripped() -> None:
    """The Silver page marks its masses *values subject to confirmation*."""
    assert _value("925*", "kg") == 925


def test_two_figures_for_one_model_take_the_lower() -> None:
    """`695/807` is one model's two masses in running order. The base vehicle is the
    settled rule, and the base is the lower."""
    assert _value("695/807", "kg") == 695
    assert _value("750/1200", "kg") == 750


def test_an_empty_cell_is_not_a_zero() -> None:
    assert _value("-", "m") is None
    assert _value("", "kg") is None


# --- the spec tables ------------------------------------------------------------------


def test_the_minis_page_yields_the_270_and_the_300(minis: str) -> None:
    specs = _by_model(parse_specifications(minis, silver=False))

    assert sorted(specs) == ["270", "300"]
    assert specs["270"].shipping_length_mm == 3950
    assert specs["270"].exterior_body_length_mm == 2990
    assert specs["270"].internal_length_mm == 2500
    assert specs["270"].overall_width_mm == 2030
    assert specs["270"].mtplm_kilograms == 750
    assert specs["270"].mro_kilograms == 641
    assert specs["270"].berths == 2


def test_the_silver_page_yields_the_290_and_the_442(silver: str) -> None:
    specs = _by_model(parse_specifications(silver, silver=True))

    assert sorted(specs) == ["290", "442"]
    assert specs["442"].shipping_length_mm == 5910
    assert specs["442"].exterior_body_length_mm == 4880
    assert specs["442"].internal_length_mm == 4400
    assert specs["442"].mtplm_kilograms == 1050
    assert specs["442"].mro_kilograms == 942
    assert specs["442"].berths == 3
    assert specs["442"].awning_length_mm == 7280


def test_the_two_4420mm_models_are_told_apart_by_their_page(minis: str, silver: str) -> None:
    """**The trap this exists for.** The 300 and the 290 are both 4,42 m long, and the
    catalogue's columns carry no heading at all — so only the page distinguishes them. They
    differ in the one figure that matters: the mass in running order, 695 against 693."""
    on_minis = _by_model(parse_specifications(minis, silver=False))
    on_silver = _by_model(parse_specifications(silver, silver=True))

    assert on_minis["300"].shipping_length_mm == on_silver["290"].shipping_length_mm == 4420
    assert on_minis["300"].mro_kilograms == 695
    assert on_silver["290"].mro_kilograms == 693


def test_the_stray_l_on_the_internal_length_row_is_tolerated(minis: str) -> None:
    """The catalogue really does print `LInternal length`, on that row and no other."""
    assert "LInternal length" in minis

    assert _by_model(parse_specifications(minis, silver=False))["270"].internal_length_mm == 2500


def test_the_height_is_the_roof_closed_figure(minis: str) -> None:
    """**Both height fields were wrong in FMLV**, which held 2330 — the roof-*open* height
    — in `height_mm` and `headroom_mm` alike. The towing height is the roof closed, which
    is what Freedom settled, and the headroom is the internal height."""
    spec = _by_model(parse_specifications(minis, silver=False))["270"]

    assert spec.height_mm == 1980, "roof closed"
    assert spec.headroom_mm == 1870, "internal height"
    assert "2,33" in minis, "the roof-open height is published too, and is not used"


def test_a_page_with_no_table_yields_nothing() -> None:
    assert parse_specifications("just some prose", silver=False) == []


# --- the self-check -------------------------------------------------------------------


def test_the_three_masses_must_be_in_order() -> None:
    ok, reason = _reconciles(
        Specification("270", empty_weight_kilograms=600, mro_kilograms=641, mtplm_kilograms=750)
    )

    assert ok
    assert "109kg" in reason


def test_a_mass_in_running_order_above_the_maximum_is_refused() -> None:
    """A column read off by one breaks the ordering immediately, which is the only thing
    this catalogue lets us check — it publishes no payload."""
    ok, reason = _reconciles(
        Specification("270", empty_weight_kilograms=600, mro_kilograms=800, mtplm_kilograms=750)
    )

    assert not ok
    assert "not above" in reason


def test_an_empty_weight_above_the_running_order_is_refused() -> None:
    ok, _ = _reconciles(
        Specification("270", empty_weight_kilograms=700, mro_kilograms=641, mtplm_kilograms=750)
    )

    assert not ok


# --- what reaches the pipeline --------------------------------------------------------


def _built(page: str, *, silver: bool, model: str):
    spec = _by_model(parse_specifications(page, silver=silver))[model]
    ok, basis = _reconciles(spec)
    assert ok
    return build_extracted(spec, "https://example.invalid/cat.pdf", basis)


def test_every_model_files_under_one_range(minis: str, silver: str) -> None:
    """The site groups them as `Minis` and `Silver`, but those are navigation headings —
    and `Silver` is a different manufacturer in the NCC list, id 187."""
    for page, is_silver, model in ((minis, False, "270"), (silver, True, "442")):
        assert _built(page, silver=is_silver, model=model).caravan.manufacturer_range == FMLV_RANGE
    assert FMLV_RANGE == "Mini"


def test_a_pop_top_is_filed_as_rigid(minis: str) -> None:
    """**Settled by the requester, 7 October 2026.** The maker calls these pop top
    caravans and the roof does raise, but FMLV's `Pop Up` means a folding camper — a
    different vehicle. Micro fails the naming half of the two-part test, since the word
    appears nowhere on the site."""
    extracted = _built(minis, silver=False, model="270")

    assert extracted.caravan.body_type is CaravanBodyType.RIGID
    assert "folding camper" in extracted.provenance["body_type"].snippet


def test_the_payload_is_derived_into_personal_effects(silver: str) -> None:
    extracted = _built(silver, silver=True, model="442")

    assert extracted.caravan.personal_effects_payload_kilograms == 1050 - 942
    assert extracted.caravan.optional_equipment_payload_kilograms is None
    assert "optional_equipment_payload_kilograms" in extracted.provenance


def test_no_price_is_ever_proposed(minis: str) -> None:
    """There is none in the catalogue and none on the site."""
    extracted = _built(minis, silver=False, model="270")

    assert extracted.caravan.rrp_pounds is None
    assert "rrp_pounds" not in extracted.provenance


def test_the_roster_size_is_pinned() -> None:
    assert EXPECTED_LAYOUTS == 4


def test_a_named_catalogue_wins_where_several_pdfs_are_linked() -> None:
    """The site links one PDF today. If it ever links more, the one that says what it is
    should win rather than whichever came first in the markup."""
    html = '<a href="/files/terms.pdf"></a><a href="files/2026/x_catalogue_EN.pdf"></a>'

    url = catalogue_url(html)

    assert url is not None and url.endswith("x_catalogue_EN.pdf")
