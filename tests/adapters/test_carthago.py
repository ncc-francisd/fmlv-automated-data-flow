"""Carthago parsing, against real pages captured in `fixtures/`.

Pure parsing only — no network. The fixtures were chosen for what each one breaks: the
T 143 KB-LE pair is one layout on two chassis and the whole reason the base vehicle joined
product identity; the Chic S-plus is an Iveco and an A-class with a two-figure gross weight
and a bracketed second height; and the T 148 KB-LE H is a page Carthago have not filled in.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters import carthago
from src.adapters.carthago import (
    EXPECTED_PRODUCTS,
    RANGES,
    CarthagoMotorhome,
    _dimensions,
    _reconciles,
    body_type_for,
    build_extracted,
    chassis_from_url,
    identity_for,
    parse_price,
    parse_running_order,
    parse_technical_data,
    roster_from,
    visible_lines,
)
from src.product_model.enums import BodyType

FIXTURES = Path(__file__).parent / "fixtures"


def _lines(name: str) -> list[str]:
    return (FIXTURES / f"carthago_{name}_text.txt").read_text(encoding="utf-8").splitlines()


def _range(slug: str):
    return next(r for r in RANGES if r.slug == slug)


def _product(name: str, slug: str, chassis: str | None) -> CarthagoMotorhome:
    lines = _lines(name)
    config = _range(slug)
    manufacturer_range, model = identity_for(lines[0], config)
    return CarthagoMotorhome(
        config=config,
        url=f"https://www.carthago.com/x/{chassis}",
        manufacturer_range=manufacturer_range,
        model=model,
        chassis=chassis,
        fields=parse_technical_data(lines),
        lines=lines,
    )


@pytest.fixture
def fiat() -> CarthagoMotorhome:
    return _product("t143_fiat", "c1-tourer-t", "Fiat")


@pytest.fixture
def mercedes() -> CarthagoMotorhome:
    return _product("t143_mercedes", "c1-tourer-t", "Mercedes")


@pytest.fixture
def iveco() -> CarthagoMotorhome:
    return _product("s_plus_iveco", "chic-s-plus", "IVECO")


# --- identity and roster --------------------------------------------------------------


def test_the_manufacturer_is_the_ncc_lists_spelling() -> None:
    assert carthago.MANUFACTURER == "Carthago"
    assert carthago.MANUFACTURER_DISPLAY_NAME == "Carthago"


def test_nine_ranges_and_carthagos_own_product_count() -> None:
    """Each range overview card states a `Floor plans` count and the nine add to 76."""
    assert len(RANGES) == 9
    assert EXPECTED_PRODUCTS == 76


def test_fmlv_files_the_semi_integrated_under_the_plain_range() -> None:
    """The site sells `C1-tourer T`; FMLV holds range `C1-tourer` with the `T` in the
    model. Its `chic c-line` holds both the A-class and the semi-integrated."""
    assert _range("c1-tourer-t").fmlv_range == "C1-tourer"
    assert _range("chic-c-line-t").fmlv_range == "chic c-line"
    assert _range("chic-c-line").fmlv_range == "chic c-line"


def test_the_c2_tourer_roster_comes_from_its_json(fiat) -> None:
    """**The trap this exists for.** The C2-tourer renders no cards at all, so a card-only
    reader returns zero for the largest range in the line-up — 26 of the 76."""
    page = (FIXTURES / "carthago_c2_tourer_cgrb.json").read_text(encoding="utf-8")
    wrapped = f'<script type="application/json" class="cgrb__data">{page}</script>'

    got = roster_from(wrapped, _range("c2-tourer"))

    assert len(got) == 26


def test_the_json_names_a_chassis_the_url_does_not() -> None:
    """Eight C2-tourer permalinks end `-2` and say nothing about the base vehicle, which
    on this manufacturer is half a product's identity."""
    page = (FIXTURES / "carthago_c2_tourer_cgrb.json").read_text(encoding="utf-8")
    wrapped = f'<script type="application/json" class="cgrb__data">{page}</script>'

    got = dict(roster_from(wrapped, _range("c2-tourer")))
    silent = [url for url in got if chassis_from_url(url) is None]

    assert silent, "expected some permalinks not to name their chassis"
    assert all(got[url] is not None for url in silent)


def test_a_card_rendered_range_reads_its_links() -> None:
    cards = (FIXTURES / "carthago_c1_tourer_t_cards.html").read_text(encoding="utf-8")

    got = roster_from(cards, _range("c1-tourer-t"))

    assert len(got) == 18
    assert {chassis for _url, chassis in got} == {"Fiat", "Mercedes"}


def test_the_chassis_is_read_from_the_url() -> None:
    assert chassis_from_url("https://x/c1-tourer-t-143-kb-le-2-fiat-ducato/") == "Fiat"
    assert chassis_from_url("https://x/c1-tourer-t-143-kb-le-mercedes-benz/") == "Mercedes"
    assert chassis_from_url("https://x/chic-s-plus-50-le-2-iveco-daily/") == "IVECO"
    assert chassis_from_url("https://x/c2-tourer-i-146-ff-rb-le-comfort-4-2-t-2/") is None


def test_the_range_is_stripped_off_the_title() -> None:
    assert identity_for("C1-tourer T 143 KB-LE lightweight 3.5 t - Carthago", _range("c1-tourer-t")) == (
        "C1-tourer",
        "T 143 KB-LE lightweight 3.5 t",
    )
    assert identity_for("chic s-plus I 50 LE - Carthago", _range("chic-s-plus")) == (
        "chic s-plus",
        "I 50 LE",
    )


def test_a_title_that_dropped_its_layout_letter_gets_it_back() -> None:
    """The T 148 KB-LE H is headed `C1-tourer 148 KB-LE H comfort 4.2 t` where every
    sibling carries its `T`, and FMLV holds the `T`."""
    assert identity_for("C1-tourer 148 KB-LE H comfort 4.2 t", _range("c1-tourer-t")) == (
        "C1-tourer",
        "T 148 KB-LE H comfort 4.2 t",
    )


def test_a_title_from_another_series_is_refused() -> None:
    assert identity_for("chic e-line I 50 LE", _range("c1-tourer-t")) is None


# --- one layout, two chassis, two vehicles ---------------------------------------------


def test_the_two_chassis_are_genuinely_different_vehicles(fiat, mercedes) -> None:
    """The whole reason the base vehicle joined product identity on 23 September 2026.
    Same range, same model, different length, height and mass."""
    assert (fiat.manufacturer_range, fiat.model) == (mercedes.manufacturer_range, mercedes.model)

    assert _dimensions(fiat.lines) == (6900, 2270, 2920)
    assert _dimensions(mercedes.lines) == (7060, 2270, 2950)
    assert fiat.mro_kilograms == 2943
    assert mercedes.mro_kilograms == 2896


# --- the technical block ---------------------------------------------------------------


def test_the_basic_vehicle_is_read_from_the_table_not_the_navigation(fiat) -> None:
    """**A parse trap that cost a pass.** `Basic vehicle` appears first in a navigation
    card where its value is a floor-plan count, so reading document-wide gives `2`."""
    assert fiat.fields["Basic vehicle"] == "Fiat Ducato"
    assert fiat.lines.count("Basic vehicle") > 1


def test_the_dimensions_survive_their_footnotes(iveco) -> None:
    """The page states `8010 / 2270 1) / 3125 (3290 2)` across several runs: footnote
    markers interleaved, and a bracketed second height that is an upgrade."""
    assert _dimensions(iveco.lines) == (8010, 2270, 3125)


def test_the_base_figure_is_taken_from_every_pair(iveco) -> None:
    """`5.600 / 5.800` gross weight, `4 / 5` seats, `4 / 5` berths — base vehicle and the
    lower berth count, which the settled rules ask for separately and agree on."""
    assert iveco.mtplm_kilograms == 5600
    assert iveco.travel_seats == 4
    assert iveco.berths == 4


def test_the_payload_is_derived(fiat) -> None:
    """Carthago publish none. Their 'weight of additional equipment in series production'
    is a different figure — the same trap as Frankia's Nutzlast."""
    assert fiat.derived_payload_kilograms == 3500 - 2943


def test_the_price_is_sterling(fiat) -> None:
    """`90.730,- £` — dot thousands, `,-` for the pence. The range page's JSON labels the
    same numbers in euro and is wrong."""
    assert parse_price(fiat.lines) == 90_730


# --- the self-check --------------------------------------------------------------------


def test_the_published_tolerance_band_brackets_the_mass(fiat) -> None:
    assert parse_running_order("2.943 (2.796 - 3.090)") == (2943, (2796, 3090))

    ok, reason = _reconciles(fiat)

    assert ok is True
    assert "brackets it exactly" in reason


def test_a_mass_from_the_wrong_row_is_caught(fiat) -> None:
    """76 products come off one template, so a column slipping would otherwise produce
    plausible motorhomes carrying each other's weights."""
    slipped = CarthagoMotorhome(
        config=fiat.config,
        url=fiat.url,
        manufacturer_range=fiat.manufacturer_range,
        model=fiat.model,
        chassis=fiat.chassis,
        fields={**fiat.fields, "Weight in running order (kg)": "3.500 (2.796 - 3.090)"},
        lines=fiat.lines,
    )

    ok, reason = _reconciles(slipped)

    assert ok is False
    assert "different rows" in reason


# --- the unfinished page ---------------------------------------------------------------


def test_a_page_with_no_technical_table_still_has_an_identity() -> None:
    """**Dropping it was worse than it sounds.** Its FMLV row went unclaimed, and the
    matcher gave 8899 and 8904 to two unmatched C2-tourer products and proposed renaming a
    C1-tourer into one. Emitting the identity alone claims the row and proposes nothing."""
    stub = _product("t148_stub", "c1-tourer-t", "Fiat")

    assert stub.fields == {}
    assert (stub.manufacturer_range, stub.model) == (
        "C1-tourer",
        "T 148 KB-LE H comfort 4.2 t",
    )

    extracted = build_extracted(stub, mass_basis="")

    assert extracted.motorhome.mtplm_kilograms is None
    assert extracted.motorhome.rrp_pounds is None
    for field in ("mtplm_kilograms", "mro_kilograms", "rrp_pounds", "mh_length_mm"):
        assert field not in extracted.provenance
    assert "model" in extracted.provenance


# --- body type --------------------------------------------------------------------------


def test_the_body_style_is_stated_not_derived() -> None:
    assert body_type_for("Coachbuilt")[0] is BodyType.COACH_BUILT_LOW_PROFILE
    assert body_type_for("A class")[0] is BodyType.A_CLASS
    assert body_type_for(None)[0] is None
    assert body_type_for("Cabriolet")[0] is None


def test_the_iveco_a_class_carries_its_style(iveco) -> None:
    extracted = build_extracted(iveco, mass_basis="")

    assert extracted.motorhome.body_type is BodyType.A_CLASS
    assert extracted.motorhome.base_vehicle_manufacturer == "IVECO"


# --- the whole product -------------------------------------------------------------------


def test_a_product_carries_every_field_fmlv_holds(fiat) -> None:
    extracted = build_extracted(fiat, mass_basis="checked")
    m = extracted.motorhome

    assert (m.manufacturer_range, m.model) == ("C1-tourer", "T 143 KB-LE lightweight 3.5 t")
    assert m.base_vehicle_manufacturer == "Fiat"
    assert (m.mh_length_mm, m.mh_width_mm, m.mh_height_mm) == (6900, 2270, 2920)
    assert (m.mtplm_kilograms, m.mro_kilograms) == (3500, 2943)
    assert m.berths == 2
    assert m.mh_passenger_seats_inc_driver == 4
    assert m.rrp_pounds == 90_730
    assert m.body_type is BodyType.COACH_BUILT_LOW_PROFILE


def test_the_chassis_provenance_says_why_it_matters(fiat) -> None:
    provenance = build_extracted(fiat, mass_basis="").provenance

    assert "part of the identity" in provenance["base_vehicle_manufacturer"].snippet
