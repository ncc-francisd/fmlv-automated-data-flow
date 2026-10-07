"""AURA — parsing and derivation only, no network.

Fixtures are the real pages of 7 October 2026 with the inline CSS stripped. Each was
chosen because it broke the parser: the OnTour T for its two tables, the Prestige campervan
for a heading split across two cells, the Beachy for headings with no `AURA` prefix, and
the Maxia because reading it as a stream gave one layout another's weights.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters import ADAPTERS, adapter_for, aura, aura_caravan
from src.adapters.aura import (
    EXPECTED_LAYOUTS,
    FMLV_MODEL_NAMES,
    PAGES,
    Specification,
    _reconciles,
    columns_of,
    lower_of_a_range,
    parse_layouts,
    three_point_belts,
)
from src.adapters.aura_caravan import FMLV_MODEL_NAMES as CARAVAN_MODEL_NAMES
from src.adapters.aura_caravan import parse_caravan_layouts
from src.product_model.enums import BodyType, CaravanBodyType
from src.vehicle_class import VehicleClass

FIXTURES = Path(__file__).parent / "fixtures"


def _page(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def ontour_t() -> str:
    return _page("aura-ontour-t-layouts.html")


@pytest.fixture
def maxia() -> str:
    return _page("aura-maxia-layouts.html")


@pytest.fixture
def prestige_campervan() -> str:
    return _page("aura-prestige-campervan-layouts.html")


@pytest.fixture
def beachy() -> str:
    return _page("aura-beachy-caravan-layouts.html")


def _by_model(layouts):
    return {layout.fmlv_model: layout for layout in layouts}


# --- registry -------------------------------------------------------------------------


def test_both_halves_are_wired_in_under_hobby_with_the_aura_display_name() -> None:
    """**The join key, and the reason the display name is part of it.** NCC id 243 is a
    different Aura and NCC id 37 is a different Hobby; only the pair identifies this one.
    """
    assert aura.MANUFACTURER == "Hobby"
    assert aura.MANUFACTURER_DISPLAY_NAME == "AURA"
    assert aura.VEHICLE_CLASS is VehicleClass.MOTORHOME
    assert aura_caravan.VEHICLE_CLASS is VehicleClass.CARAVAN
    assert adapter_for("Hobby", VehicleClass.MOTORHOME, display_name="AURA") is aura
    assert adapter_for("Hobby", VehicleClass.CARAVAN, display_name="AURA") is aura_caravan
    assert ("Hobby", "AURA", VehicleClass.MOTORHOME) in ADAPTERS
    assert ("Hobby", "AURA", VehicleClass.CARAVAN) in ADAPTERS


# --- the trap the whole parser exists for ---------------------------------------------


def test_a_layout_takes_the_figures_from_its_own_column(maxia: str) -> None:
    """**The trap this exists for.** Each table lays two layouts side by side — names in
    one row, figures in the row below — so reading the page as a stream of text gives the
    second layout the first one's weights. It did exactly that: the 740 WE came out with
    the 710 GE's MIRO of 3273 and its 7120mm length. Both are plausible and internally
    consistent, which is what makes it the dangerous kind of wrong."""
    layouts = _by_model(parse_layouts(maxia, "Maxia T"))

    assert layouts["710 GE"].spec.mro_kilograms == 3273
    assert layouts["710 GE"].spec.length_mm == 7120
    assert layouts["740 WE"].spec.mro_kilograms == 3294
    assert layouts["740 WE"].spec.length_mm == 7400
    assert layouts["740 WF"].spec.mro_kilograms == 3296


def test_a_table_whose_names_and_figures_do_not_match_up_yields_nothing() -> None:
    """A cardinality failure is not an invitation to guess at the alignment."""
    html = (
        "<table><tr><td>AURA Maxia 710 GE</td><td>AURA Maxia 740 WE</td></tr>"
        "<tr><td>Berths 2 | MTPLM 4400kg</td></tr></table>"
    )

    assert columns_of(html) == []


def test_every_layout_block_is_read_once(ontour_t: str) -> None:
    """The tables repeat — a layout appears in a slider and again in a dialog — so without
    deduplication the roster doubles."""
    layouts = parse_layouts(ontour_t, "OnTour T")

    assert sorted(layout.fmlv_model for layout in layouts) == ["700F", "700FH", "710 GE"]


# --- the four heading shapes ----------------------------------------------------------


def test_a_heading_sharing_its_cell_with_a_badge_still_parses(ontour_t: str) -> None:
    """`AURA OnTour T 700 F | First Edition` — anchoring the pattern to the end of the
    cell lost every layout that carries the badge."""
    assert "700F" in _by_model(parse_layouts(ontour_t, "OnTour T"))


def test_a_heading_split_across_two_cells_still_parses(prestige_campervan: str) -> None:
    """`AURA Prestige | 640 ET` — the range and the model are separate elements here,
    where every other page puts them in one."""
    layouts = _by_model(parse_layouts(prestige_campervan, "Prestige"))

    assert "640 ET" in layouts
    assert layouts["640 ET"].spec.mro_kilograms == 3120


def test_a_caravan_heading_without_the_aura_prefix_still_parses(beachy: str) -> None:
    """The caravan pages head their layouts `Beachy 360`, with no `AURA` in front."""
    layouts = _by_model(parse_caravan_layouts(beachy, "Beachy"))

    assert sorted(layouts) == ["360", "420", "420 Plus", "450"]


def test_the_range_comes_from_the_page_not_the_heading() -> None:
    """The Prestige T and Maxia T pages both head their layouts without the `T`, so a
    range read from the heading would file them under the wrong one."""
    assert [page.fmlv_range for page in PAGES if "prestige-t" in page.path] == ["Prestige T"]
    assert [page.fmlv_range for page in PAGES if "maxia" in page.path] == ["Maxia T"]


# --- the two rules this adapter applies against FMLV ----------------------------------


def test_a_berth_range_takes_the_lower_figure() -> None:
    """`Berths 3 (up to 4)` is three. FMLV holds the upper figure on seven of the
    thirteen, which is what this corrects."""
    assert lower_of_a_range("3 (up to 4)") == 3
    assert lower_of_a_range("5 (optional 6)") == 5
    assert lower_of_a_range("4") == 4
    assert lower_of_a_range("no number here") is None


def test_a_lap_belt_is_not_a_travel_seat() -> None:
    """**The OnTour A 720 GFM reads `6 (inc x2 lap belts)`.** That is four travel seats,
    not the six FMLV holds. Written as a subtraction so a layout that gains or loses a lap
    belt still reads correctly."""
    assert three_point_belts("6 (inc x2 lap belts)") == 4
    assert three_point_belts("4") == 4
    assert three_point_belts("5 (inc 1 lap belt)") == 4


def test_the_ontour_a_really_does_state_six_belts(maxia: str) -> None:
    """Guard against the fixture being the thing that makes the rule look right."""
    ontour_a = _page("aura-ontour-t-layouts.html")

    assert "lap belt" not in ontour_a.lower(), "the OnTour T has none, so the rule is live"
    assert "lap belt" not in maxia.lower()


# --- the self-check -------------------------------------------------------------------


def test_the_published_payload_checks_the_two_masses() -> None:
    ok, reason = _reconciles(
        Specification(mtplm_kilograms=3500, mro_kilograms=3014, published_payload_kilograms=486)
    )

    assert ok
    assert "3500" in reason


def test_a_payload_that_does_not_reconcile_is_refused() -> None:
    """**Dropped, not proposed.** The caravan pages have no such check at all, which is
    why nothing on that side is proposed."""
    ok, reason = _reconciles(
        Specification(mtplm_kilograms=3500, mro_kilograms=3014, published_payload_kilograms=400)
    )

    assert not ok
    assert "486kg against a published payload of 400kg" in reason


def test_the_roster_size_is_pinned() -> None:
    assert EXPECTED_LAYOUTS == 13


# --- what reaches the pipeline --------------------------------------------------------


def test_the_base_vehicle_is_spelled_fmlvs_way(ontour_t: str) -> None:
    """`Citroën` with the diaeresis, routed through the shared helper — and not derivable
    from the range, since OnTour C is a Citroën where OnTour T and A are Fiats."""
    page = next(p for p in PAGES if "ontour-t" in p.path)
    layout = _by_model(parse_layouts(ontour_t, "OnTour T"))["710 GE"]

    extracted = aura.build_extracted(layout, page, "basis")

    assert extracted.motorhome.base_vehicle_manufacturer == "Fiat"


def test_no_price_is_ever_proposed(ontour_t: str) -> None:
    """The site carries only range-level `from` figures, and they match no FMLV row at the
    entry end — motorhomes advertise from GBP83,995 where the cheapest layout is 85,795."""
    page = next(p for p in PAGES if "ontour-t" in p.path)
    layout = _by_model(parse_layouts(ontour_t, "OnTour T"))["710 GE"]

    extracted = aura.build_extracted(layout, page, "basis")

    assert extracted.motorhome.rrp_pounds is None
    assert "rrp_pounds" not in extracted.provenance


def test_a_caravan_is_collected_by_identity_alone(beachy: str) -> None:
    """**Nothing is proposed for the caravans.** The importer's spreadsheets are the
    authority and FMLV matches them; this site disagrees with them on every layout and is
    demonstrably behind. Emitting the identity still claims the FMLV row, so a run cannot
    report a caravan AURA still sell as missing."""
    layout = _by_model(parse_caravan_layouts(beachy, "Beachy"))["420"]
    page = next(p for p in aura_caravan.PAGES if "beachy" in p.path)

    extracted = aura_caravan.build_extracted(layout, page)

    assert extracted.provenance == {}
    assert extracted.caravan.manufacturer == "Hobby"
    assert extracted.caravan.manufacturer_display_name == "AURA"
    assert extracted.caravan.body_type is CaravanBodyType.RIGID
    assert extracted.caravan.mtplm_kilograms is None, "read, but never proposed"


def test_the_two_beachys_do_not_collide_on_one_fmlv_row(beachy: str) -> None:
    """**The trap this exists for.** The site writes `420+` where FMLV holds `420 Plus`,
    and both reduce to the single token `420` — so without the name map the two Beachys
    claim the same FMLV row and one of them vanishes."""
    assert CARAVAN_MODEL_NAMES["420+"] == "420 Plus"

    models = sorted(l.fmlv_model for l in parse_caravan_layouts(beachy, "Beachy"))

    assert "420" in models and "420 Plus" in models
    assert len(set(models)) == len(models)


# --- what the live run against FMLV taught -------------------------------------------


def test_the_site_adds_a_space_fmlv_does_not(ontour_t: str) -> None:
    """**The trap this exists for.** The site writes `700 FH` where FMLV holds `700FH`,
    and the space was enough to stop it matching: it arrived as a new product beside a
    disappearance notice for the very row it was meant to update."""
    assert FMLV_MODEL_NAMES == {"700 F": "700F", "700 FH": "700FH"}

    models = _by_model(parse_layouts(ontour_t, "OnTour T"))

    assert "700FH" in models and "700 FH" not in models


def test_no_dimension_is_proposed(ontour_t: str) -> None:
    """**The site is the coarser source.** It publishes centimetres where FMLV holds
    millimetres, so every length comes back rounded — 676cm against FMLV's 6759mm, 288cm
    against 2883. Proposing them was thirty rows asking a reviewer to make good data
    worse. The masses are exact kilograms on both sides and are proposed."""
    page = next(p for p in PAGES if "ontour-t" in p.path)
    layout = _by_model(parse_layouts(ontour_t, "OnTour T"))["710 GE"]

    extracted = aura.build_extracted(layout, page, "basis")

    for field in ("mh_length_mm", "mh_width_mm", "mh_height_mm"):
        assert field not in extracted.provenance, field
    assert "mtplm_kilograms" in extracted.provenance
    assert "mro_kilograms" in extracted.provenance


def test_a_coach_builts_body_type_is_not_guessed_from_its_range(ontour_t: str) -> None:
    """The OnTour A describes its over-cab bed as an *option*, so a range name cannot tell
    a low profile from an over-cab. FMLV's own value is better than a guess."""
    page = next(p for p in PAGES if "ontour-t" in p.path)
    layout = _by_model(parse_layouts(ontour_t, "OnTour T"))["710 GE"]

    extracted = aura.build_extracted(layout, page, "basis")

    assert extracted.motorhome.body_type is None
    assert "body_type" not in extracted.provenance


def test_a_campervans_body_type_comes_from_its_height(prestige_campervan: str) -> None:
    """Here the site does settle it: 267cm is 2670mm, over the shared 2300mm threshold,
    which is the high top FMLV already holds for all three campervans."""
    page = next(p for p in PAGES if "campervans-prestige" in p.path)
    layout = _by_model(parse_layouts(prestige_campervan, "Prestige"))["640 ET"]

    extracted = aura.build_extracted(layout, page, "basis")

    assert layout.spec.height_mm == 2670
    assert extracted.motorhome.body_type is BodyType.CAMPERVAN_HIGH_TOP
    assert "body_type" in extracted.provenance
