"""Bespoke NI — parsing and derivation only, no network."""

from __future__ import annotations

from src.adapters import ADAPTERS, adapter_for, bespoke
from src.adapters.bespoke import (
    EDITION,
    EXPECTED_PRODUCTS,
    EXPLORE,
    leaflet_url,
    parse_explore_prices,
    price_disagreements,
)
from src.product_model.enums import BodyType
from src.vehicle_class import VehicleClass

#: The leaflet's `Choose your vehicle base` table, as `fetch.pdf` extracts it. Ford on the
#: left of each line, VW on the right — which is the trap the parser exists for.
LEAFLET = """\
1. Choose your vehicle base:
Standard retail price for fully converted Bespoke Explore:

Ford Custom Trend 110PS 6 speed manual   £60,995      VW T7 Commerce Plus 110PS 6 speed manual   £64,995
Ford Custom Limited 136PS 8 speed auto   £65,995      VW T7 Commerce Plus 150PS 8 speed auto     £69,995
Ford Custom Tourneo 170PS 8 speed auto   £68,995      VW T7 Commerce Pro 170PS 8 speed auto      £73,995

4. Choose any extras:
Bespoke performance gloss black body kit     £1500
"""


def _explore(model: str):
    return next(v for v in EXPLORE if v.fmlv_model == model)


# --- registry -------------------------------------------------------------------------


def test_the_adapter_is_wired_in() -> None:
    assert bespoke.MANUFACTURER == "Bespoke NI"
    assert bespoke.MANUFACTURER_DISPLAY_NAME == "Bespoke"
    assert (
        adapter_for("Bespoke NI", VehicleClass.MOTORHOME, display_name="Bespoke") is bespoke
    )
    assert ("Bespoke NI", "Bespoke", VehicleClass.MOTORHOME) in ADAPTERS


# --- the leaflet ----------------------------------------------------------------------


def test_both_columns_of_the_price_table_are_read() -> None:
    """**The trap this exists for.** The table prints Ford on the left of each line and VW
    on the right, so a line-by-line read finds three variants and misses three."""
    prices = parse_explore_prices(LEAFLET)

    assert len(prices) == 6
    assert prices["ford custom trend 110ps 6 speed manual"] == 60995
    assert prices["vw t7 commerce pro 170ps 8 speed auto"] == 73995


def test_an_option_price_is_not_mistaken_for_a_vehicle() -> None:
    """The same document prices a body kit at GBP1500. Only rows naming an engine count."""
    assert 1500 not in parse_explore_prices(LEAFLET).values()


def test_the_leaflet_url_is_read_not_constructed() -> None:
    """**Never hardcode the path.** The upload folder carries the issue month and moves on
    every reissue; the point of rediscovering it is to follow the current one."""
    html = (
        '<a href="https://bespokeleisure.co.uk/wp-content/uploads/2026/02/'
        'Bespoke-Explore-Leaflet.pdf">Download</a>'
    )

    assert leaflet_url(html) == (
        "https://bespokeleisure.co.uk/wp-content/uploads/2026/02/Bespoke-Explore-Leaflet.pdf"
    )
    assert leaflet_url("<a href='/about/'>About</a>") is None


def test_a_document_with_no_table_yields_nothing_rather_than_guessing() -> None:
    assert parse_explore_prices("no table here") == {}


# --- the roster -----------------------------------------------------------------------


def test_nine_products_across_the_two_halves() -> None:
    assert len(EXPLORE) + len(EDITION) == EXPECTED_PRODUCTS == 9
    assert len(EXPLORE) == 6
    assert len(EDITION) == 3


def test_every_explore_variant_is_priced_by_the_leaflet() -> None:
    """A label that drifts from the leaflet's wording silently loses that variant's price,
    so the join is pinned here rather than discovered on a live run."""
    prices = parse_explore_prices(LEAFLET)

    for variant in EXPLORE:
        assert variant.leaflet_label in prices, variant.label


def test_the_products_are_named_as_fmlv_files_them() -> None:
    """FMLV's own strings, not the leaflet's — see the rule in `docs/adapters/README.md`.
    The leaflet calls the 170PS Ford a Tourneo where FMLV holds `170 Limited`."""
    assert _explore("170 Limited Elevating Roof").fmlv_range == "Explore Custom"
    assert "tourneo" in _explore("170 Limited Elevating Roof").leaflet_label


def test_the_base_vehicle_is_the_marque_alone() -> None:
    assert {v.base_vehicle for v in EXPLORE} == {"Ford", "VW"}


# --- what reaches the pipeline --------------------------------------------------------


def test_no_mass_is_ever_emitted() -> None:
    """**The reason this adapter is partial.** Six model pages and three PDFs carry no kg
    figure at all. FMLV holds MRO and MTPLM for all eight rows and payload reconciles on
    every one, so emitting a blank would destroy good data."""
    for variant in EXPLORE:
        motorhome = bespoke._build_explore(variant, 60995, "u").motorhome
        assert motorhome.mro_kilograms is None
        assert motorhome.mtplm_kilograms is None
        assert motorhome.mh_payload_kilograms is None


def test_the_width_is_not_emitted_because_the_site_measures_the_mirrors() -> None:
    """**The trap this exists for.** The pages state `Explore Width 2.27m`. That is 2270mm
    across the mirrors; FMLV holds 2032, the body width. Length and height, which agree to
    the millimetre, are emitted."""
    extracted = bespoke._build_explore(_explore("110 Trend Elevating Roof"), 60995, "u")

    assert extracted.motorhome.mh_width_mm is None
    assert "mh_width_mm" not in extracted.provenance
    assert extracted.motorhome.mh_length_mm == 5050
    assert extracted.motorhome.mh_height_mm == 1980


def test_an_explore_is_an_elevating_roof_campervan_not_a_high_top() -> None:
    """1980mm with the roof down, under the shared 2300mm threshold."""
    motorhome = bespoke._build_explore(_explore("110 Trend Elevating Roof"), 1, "u").motorhome

    assert motorhome.body_type is BodyType.CAMPERVAN_ELEVATING_ROOF


def test_an_unpriced_variant_emits_nothing_rather_than_zero() -> None:
    extracted = bespoke._build_explore(_explore("110 Trend Elevating Roof"), None, "u")

    assert extracted.motorhome.rrp_pounds is None
    assert "rrp_pounds" not in extracted.provenance


def test_an_edition_is_collected_by_identity_alone() -> None:
    """Its page prices the range once for three products and breaks out no engine, roof or
    berth count. Emitting the identity claims the FMLV row so a run cannot report a van
    Bespoke still sell as missing — the Carthago lesson — while proposing nothing."""
    extracted = bespoke._build_edition("Edition 2", "140 Auto", "VW")

    assert extracted.provenance == {}
    assert extracted.motorhome.manufacturer_range == "Edition 2"
    assert extracted.motorhome.base_vehicle_manufacturer == "VW"
    assert extracted.motorhome.rrp_pounds is None
    assert extracted.motorhome.mh_length_mm is None


def test_seats_are_not_proposed() -> None:
    """Bespoke state the vehicle is M1 registered but print no belt count, and only
    three-point belts count. FMLV's figure stands."""
    extracted = bespoke._build_explore(_explore("110 Trend Elevating Roof"), 1, "u")

    assert "mh_passenger_seats_inc_driver" not in extracted.provenance


# --- the cross-check ------------------------------------------------------------------


def test_a_page_price_the_leaflet_does_not_know_is_reported() -> None:
    """**The only cross-check here.** No mass is published, so there is no arithmetic to
    reconcile; what is checked is that two separately-maintained documents agree."""
    prices = parse_explore_prices(LEAFLET)

    found = price_disagreements(prices, {"/a-page/": {60995, 99999}})

    assert len(found) == 1
    assert "GBP99,999" in found[0]
    assert "reissued" in found[0]


def test_agreeing_documents_report_nothing() -> None:
    prices = parse_explore_prices(LEAFLET)

    assert price_disagreements(prices, {"/a-page/": {60995, 73995}}) == []
