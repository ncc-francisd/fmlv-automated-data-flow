"""Tests for the Wingamm caravan adapter's pure parsing functions, against the real pages.

Fixtures are three real pages from `wingamm.com`, fetched 17 September 2026 with
`<script>` and `<style>` removed. Three, because each carries something the others do not:

* **the caravan index** — the roster, and the trap it has to survive: it links all twelve
  Wingamm vehicles, eight of which are motorhomes.
* **rookie** — the Italian thousands dot (`1.000 Kg`), a two-figure `Total mass`, and
  Wingamm's "mini-caravan" wording on the layout's own page.
* **rookie-l** — the comma form (`1,200 Kg`), and the page that never calls itself a mini
  caravan, which is why the naming is read from the range.

No network here.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.adapters import adapter_for, wingamm, wingamm_caravan
from src.adapters.wingamm_caravan import (
    EXPECTED_LAYOUTS,
    MANUFACTURER,
    MANUFACTURER_DISPLAY_NAME,
    MICRO_MAX_MTPLM_KG,
    _BY_SLUG,
    _Figures,
    _body_type,
    _masses,
    _reconciles,
    build_extracted,
    caravan_cards,
    micro_naming_in,
    WingammCaravan,
)
from src.product_model.enums import CaravanBodyType
from src.vehicle_class import VehicleClass

FIXTURES = Path(__file__).parent / "fixtures"

URL = "https://www.wingamm.com/en/camper-caravan/rookie/"

PAGES = {"rookie": "wingamm_rookie.html", "rookie-l": "wingamm_rookie_l.html"}


def _index() -> str:
    return (FIXTURES / "wingamm_caravan_index.html").read_text(encoding="utf-8")


def _page(slug: str) -> str:
    return (FIXTURES / PAGES[slug]).read_text(encoding="utf-8")


def _product(slug: str) -> WingammCaravan:
    cards = caravan_cards(_index())
    return WingammCaravan(
        model=_BY_SLUG[slug],
        page=_Figures.read(_page(slug)),
        card=_Figures.read(cards[slug]),
        micro_naming=micro_naming_in(_page(slug)) or micro_naming_in(_index()),
    )


# --------------------------------------------------------------------------- #
# Registration
# --------------------------------------------------------------------------- #


def test_wingamm_now_holds_both_product_areas() -> None:
    """One brand, two modules — the Bailey and Eriba shape. No ambiguity either way,
    because the two differ by product area rather than by brand."""
    assert MANUFACTURER == wingamm.MANUFACTURER == "Wingamm"
    assert MANUFACTURER_DISPLAY_NAME == wingamm.MANUFACTURER_DISPLAY_NAME

    assert adapter_for("Wingamm", VehicleClass.CARAVAN) is wingamm_caravan
    assert adapter_for("Wingamm", VehicleClass.MOTORHOME) is wingamm
    assert wingamm_caravan.VEHICLE_CLASS is VehicleClass.CARAVAN


def test_the_motorhome_adapter_still_excludes_these_two() -> None:
    """`wingamm.py` has skipped them by name since 26 August 2026. If it ever stopped,
    both adapters would propose against the same vehicles."""
    assert {"rookie", "rookie-l"} <= wingamm._IGNORED_SLUGS


# --------------------------------------------------------------------------- #
# The roster, and the eight motorhomes it must not collect
# --------------------------------------------------------------------------- #


def test_the_roster_is_the_two_caravans_and_not_the_ten_other_links() -> None:
    """The trap: the caravan index links every Wingamm vehicle, motorhomes included."""
    assert set(caravan_cards(_index())) == {"rookie", "rookie-l"}
    assert len(caravan_cards(_index())) == EXPECTED_LAYOUTS == 2

    assert "oasi-610-st" in _index()
    assert "brownie" in _index()


def test_a_caravan_is_told_by_its_drawbar() -> None:
    """Structural rather than a hardcoded pair of slugs, so a third Rookie is noticed."""
    cards = caravan_cards(_index())

    for card in cards.values():
        assert "with drawbar" in card.lower()


def test_a_page_with_no_cards_yields_nothing() -> None:
    assert caravan_cards("<html><body>Wingamm</body></html>") == {}


def test_a_caravan_with_no_identity_is_not_guessed_at() -> None:
    """FMLV's range/model split is not derivable from the page, so an unknown slug is
    skipped by `collect` rather than given a made-up name."""
    assert set(_BY_SLUG) == {"rookie", "rookie-l"}
    assert _BY_SLUG["rookie"].fmlv_range == "Rookie"
    assert _BY_SLUG["rookie"].fmlv_model == "3.5"
    assert _BY_SLUG["rookie-l"].fmlv_model == "L"


# --------------------------------------------------------------------------- #
# The figures
# --------------------------------------------------------------------------- #


def test_each_caravan_yields_its_figures() -> None:
    rookie, rookie_l = _product("rookie"), _product("rookie-l")

    assert rookie.shipping_length_mm == 4990
    assert rookie.berths == 2
    assert (rookie.mro_kilograms, rookie.mtplm_kilograms) == (750, 1000)
    assert rookie.derived_payload_kilograms == 250

    assert rookie_l.shipping_length_mm == 6000
    assert rookie_l.berths == 4
    assert (rookie_l.mro_kilograms, rookie_l.mtplm_kilograms) == (940, 1200)
    assert rookie_l.derived_payload_kilograms == 260


def test_the_thousands_separator_goes_both_ways_in_one_range() -> None:
    """`1.000 Kg` on the Rookie and `1,200 Kg` on the Rookie L. A naive parse reads the
    first as 1.0 and puts a 1kg MTPLM on a caravan."""
    assert _masses("750 Kg - 1.000 Kg") == (750, 1000)
    assert _masses("940 Kg - 1,200 Kg") == (940, 1200)


def test_a_single_mass_is_the_laden_one_not_both() -> None:
    """The Rookie L's index card abbreviates to `Total mass: 1,200 Kg`. Using it for the
    running order too would invent a zero payload."""
    assert _masses("1,200 Kg") == (None, 1200)
    assert _product("rookie-l").card.mro_kilograms is None
    assert _product("rookie-l").card.mtplm_kilograms == 1200


def test_the_berth_count_is_read_under_both_of_its_names() -> None:
    """`Sleeps` on a model page, `Berths` on an index card — the same figure."""
    assert "Sleeps:" in _page("rookie-l")

    assert _product("rookie-l").page.berths == 4
    assert _product("rookie-l").card.berths == 4


def test_the_length_is_the_shipping_one() -> None:
    """Quoted "with drawbar" — body plus towing hitch. Reading it as the internal length
    is what `docs/adapters/README.md` names as the likeliest caravan mistake."""
    assert _product("rookie").page.shipping_length_mm == 4990

    caravan = build_extracted(_product("rookie"), URL, basis="x").caravan
    assert caravan.shipping_length_mm == 4990
    assert caravan.internal_length_mm is None


# --------------------------------------------------------------------------- #
# The self-check
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("slug", ["rookie", "rookie-l"])
def test_the_page_and_the_card_agree(slug: str) -> None:
    assert _reconciles(_product(slug))[0] is True


def test_a_card_that_contradicts_the_page_drops_the_layout() -> None:
    product = _product("rookie")
    disagreeing = replace(product, card=replace(product.card, berths=4))

    reconciles, why_not = _reconciles(disagreeing)

    assert reconciles is False
    assert "berth count" in why_not


def test_a_card_that_stays_silent_does_not_drop_the_layout() -> None:
    """Required to agree where it speaks, not required to speak — which is the Rookie L's
    real case, and losing a caravan over an abbreviated card would be the worse error."""
    product = _product("rookie")
    silent = replace(product, card=_Figures())

    assert _reconciles(silent)[0] is True


def test_a_page_missing_a_figure_is_dropped() -> None:
    product = _product("rookie")

    reconciles, why_not = _reconciles(replace(product, page=replace(product.page, berths=None)))

    assert reconciles is False
    assert "berth count" in why_not


def test_masses_the_wrong_way_round_are_dropped() -> None:
    """What reading `Total mass` backwards would produce."""
    product = _product("rookie")
    inverted = replace(product, page=replace(product.page, mro_kilograms=1000, mtplm_kilograms=750))

    reconciles, why_not = _reconciles(inverted)

    assert reconciles is False
    assert "running order" in why_not


# --------------------------------------------------------------------------- #
# The micro rule — the first products in the project to meet it
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("slug", ["rookie", "rookie-l"])
def test_both_rookies_are_micros(slug: str) -> None:
    """Both halves of the README's test: Wingamm's own naming, and 1000/1200kg against
    the 1250kg bar. FMLV already holds both as micro, and an earlier version of this
    adapter proposed downgrading them to rigid."""
    product = _product(slug)
    body_type, reason = _body_type(product)

    assert body_type is CaravanBodyType.MICRO
    assert str(MICRO_MAX_MTPLM_KG) in reason
    assert build_extracted(product, URL, basis="x").caravan.body_type is CaravanBodyType.MICRO


def test_naming_without_the_weight_is_not_a_micro() -> None:
    """Weight alone would have mislabelled thirteen products across Bailey and Adria; the
    naming alone must not do the reverse."""
    product = _product("rookie")
    heavy = replace(product, page=replace(product.page, mtplm_kilograms=1400))

    body_type, reason = _body_type(heavy)

    assert body_type is CaravanBodyType.RIGID
    assert "1400kg" in reason


def test_the_weight_without_the_naming_is_not_a_micro() -> None:
    """The half a reviewer cannot recompute from the figures — so if Wingamm restyle the
    page, these stop being micros by the rule rather than by an assertion here."""
    body_type, reason = _body_type(replace(_product("rookie"), micro_naming=None))

    assert body_type is CaravanBodyType.RIGID
    assert "walls fold or rise" in reason


def test_the_rookie_l_takes_its_naming_from_the_range() -> None:
    """Its own page never says "mini caravan"; the index says it of both, in the plural."""
    assert micro_naming_in(_page("rookie-l")) is None
    assert micro_naming_in(_page("rookie")) is not None
    assert micro_naming_in(_index()) is not None

    assert _product("rookie-l").micro_naming is not None


def test_the_quoted_evidence_is_a_sentence_wingamm_wrote() -> None:
    """The first version searched the raw markup and quoted a script's country list —
    `"SE","SI","SK"],"wait_for_up` — as its evidence for a body type."""
    quoted = micro_naming_in(
        '<script>var x = ["SE","SI","SK"],"wait_for_mini caravan";</script>'
        "<p>Our mini caravans with fiberglass monocoque</p>"
    )

    assert quoted is not None
    assert "wait_for" not in quoted
    assert "Our mini caravans with fiberglass monocoque" in quoted


# --------------------------------------------------------------------------- #
# What reaches the reviewer
# --------------------------------------------------------------------------- #


def test_the_identity_is_the_split_fmlv_holds() -> None:
    caravan = build_extracted(_product("rookie"), URL, basis="x").caravan

    assert caravan.manufacturer == "Wingamm"
    assert caravan.manufacturer_range == "Rookie"
    assert caravan.model == "3.5"


def test_both_halves_of_the_identity_carry_provenance() -> None:
    provenance = build_extracted(_product("rookie"), URL, basis="x").provenance

    assert "manufacturer_range" in provenance
    assert "model" in provenance


def test_no_price_is_collected() -> None:
    """Wingamm quote euro ex works, VAT excluded; FMLV holds a UK importer price."""
    extracted = build_extracted(_product("rookie"), URL, basis="x")

    assert extracted.caravan.rrp_pounds is None
    assert "rrp_pounds" not in extracted.provenance


def test_unpublished_dimensions_are_left_alone() -> None:
    """Width, height and headroom appear nowhere, so FMLV's own figures stand."""
    extracted = build_extracted(_product("rookie"), URL, basis="x")

    for field_name in ("overall_width_mm", "height_mm", "headroom_mm"):
        assert getattr(extracted.caravan, field_name) is None
        assert field_name not in extracted.provenance


def test_the_axle_count_is_neither_asserted_nor_compared() -> None:
    """Nothing publishes one. Silence is not a negative, so no provenance is recorded and
    the field is never proposed against FMLV's stored value."""
    extracted = build_extracted(_product("rookie"), URL, basis="x")

    assert "twin_axle" not in extracted.provenance


def test_the_optional_equipment_column_is_asked_to_stay_blank() -> None:
    extracted = build_extracted(_product("rookie"), URL, basis="x")

    assert "optional_equipment_payload_kilograms" in extracted.provenance
    assert extracted.caravan.optional_equipment_payload_kilograms is None
