"""Tests for the Atom adapter's pure parsing functions, against the real pages.

Fixtures are the real browser-rendered pages from `atommotorhomes.com`, fetched 16 September
2026 with `<script>` and `<style>` removed — see `docs/adapters/atom.md`. Rendered, because
plain HTTP returns three kilobytes and the word "Atom".

* **`atom_models.html`** — the comparison table, which is the source.
* **`atom_config.html`** — the configurator, the only place a mass in running order appears.
* **`atom_core_b.html`, `atom_core_g.html`** — two model pages: one that prints the wrong
  height, and one whose prose names a bed the other's does not.

No network here.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.adapters import adapter_for, atom
from src.adapters.atom import (
    BASE_VEHICLE,
    BODY_TYPE,
    CONFIG_NAMES,
    EXPECTED_LAYOUTS,
    LAYOUTS,
    MANUFACTURER,
    MANUFACTURER_DISPLAY_NAME,
    OTR_PRICES,
    AtomProduct,
    _build_extracted_motorhome,
    _reconciles,
    copy_lines_from,
    plain_text,
    read_comparison_table,
    read_gross_vehicle_mass,
    read_running_order,
)
from src.product_model.enums import BodyType

FIXTURES = Path(__file__).parent / "fixtures"


def _page(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _products() -> list[AtomProduct]:
    return read_comparison_table(_page("atom_models.html"))


def _by_label() -> dict[str, AtomProduct]:
    return {product.label: product for product in _products()}


# --------------------------------------------------------------------------- #
# The roster
# --------------------------------------------------------------------------- #


def test_the_comparison_table_yields_four_layouts_in_order() -> None:
    assert [(p.manufacturer_range, p.model) for p in _products()] == list(LAYOUTS)
    assert len(LAYOUTS) == EXPECTED_LAYOUTS == 4


def test_the_split_renders_the_names_the_requester_asked_for() -> None:
    """FMLV prepends the display name, so `Core` + `B` reads as "Atom Core B".

    `pilote.py` learned this the hard way — see commit `be7bf49`, where `Pilote Van`
    rendered as "Pilote Pilote Van V630S".
    """
    rendered = [f"{MANUFACTURER_DISPLAY_NAME} {r} {m}" for r, m in LAYOUTS]

    assert rendered == ["Atom Core B", "Atom Core G", "Atom Element B", "Atom Element G"]


def test_the_manufacturer_is_the_maker_and_the_brand_is_the_display_name() -> None:
    """The NCC's own `264, Swift Group Ltd, Ace Motorhomes` files a brand this way."""
    assert MANUFACTURER == "Trigano"
    assert MANUFACTURER_DISPLAY_NAME == "Atom"


def _table(berths: str = "2 2 2 2") -> str:
    """A minimal comparison table, for the shapes the real page cannot be edited into."""
    return (
        "<div>Specification Core B Core G Element B Element G "
        f"Berths {berths} "
        "Seatbelts 2 2 2 2 "
        "Length 5986mm 5986mm 5986mm 5986mm "
        "Width 2040mm 2040mm 2040mm 2040mm "
        "Height 2710mm 2710mm 2710mm 2710mm "
        "Max Authorised Weight 3500kg 3500kg 3500kg 3500kg</div>"
    )


def test_the_synthetic_table_matches_the_real_one() -> None:
    """So the negative tests below are testing the same parser the real page goes through."""
    assert [(p.manufacturer_range, p.model) for p in read_comparison_table(_table())] == list(
        LAYOUTS
    )


def test_a_row_short_of_a_column_yields_nothing_rather_than_half() -> None:
    """A row that lost a column means the table was redesigned, not that a model went.

    Refusing the whole table is deliberate: the four layouts publish identical figures, so
    a misalignment cannot be spotted by eye in the output.
    """
    assert read_comparison_table(_table(berths="2 2 2")) == []


def test_a_fifth_column_yields_nothing() -> None:
    """What Atom adding the promised four-berth model would look like."""
    assert read_comparison_table(_table(berths="2 2 2 2 4")) == []


def test_a_page_without_the_table_yields_nothing() -> None:
    assert read_comparison_table("<p>Atom</p>") == []


# --------------------------------------------------------------------------- #
# The figures
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("label", ["Core B", "Core G", "Element B", "Element G"])
def test_every_layout_shares_the_crafter_body(label: str) -> None:
    """One Crafter body, four interior layouts — identical is right, not a misread."""
    product = _by_label()[label]

    assert product.berths == 2
    assert product.mh_passenger_seats_inc_driver == 2
    assert product.mh_length_mm == 5986
    assert product.mh_width_mm == 2040
    assert product.mh_height_mm == 2710
    assert product.mtplm_kilograms == 3500


def test_the_height_is_the_tables_not_the_model_pages() -> None:
    """The Core page prints 2170mm — transposed digits — and the table prints 2710mm.

    Not cosmetic: 2170 would fall below the 2300mm threshold and file these as plain
    campervans. The requester confirmed 2710 from the photographs, 16 September 2026.
    """
    assert "Height 2170mm" in plain_text(_page("atom_core_b.html"))
    assert "Height 2710mm" in plain_text(_page("atom_models.html"))
    assert _by_label()["Core B"].mh_height_mm == 2710


def test_the_width_needs_no_mirror_judgement() -> None:
    """Atom label it `(excl. door mirrors)`, which is the settled rule's figure outright."""
    assert "Width (excl. door mirrors) 2040mm" in plain_text(_page("atom_core_b.html"))
    assert _by_label()["Core B"].mh_width_mm == 2040


def test_two_seatbelts_is_right_and_not_a_parse_error() -> None:
    """Low enough to look wrong, so it is pinned against the table's own row."""
    assert "Seatbelts 2 2 2 2" in plain_text(_page("atom_models.html"))
    assert all(p.mh_passenger_seats_inc_driver == 2 for p in _products())


# --------------------------------------------------------------------------- #
# The configurator, which is the only source for the running order
# --------------------------------------------------------------------------- #


def test_the_running_orders_are_read_per_layout() -> None:
    assert read_running_order(_page("atom_config.html")) == {
        "Core 600B": 2720,
        "Core 600G": 2720,
        "Element 600B": 2810,
        "Element 600G": 2810,
    }


def test_the_configurator_names_every_layout_the_table_does() -> None:
    """The two sources name the layouts differently, so the mapping has to be complete."""
    running = read_running_order(_page("atom_config.html"))

    assert {CONFIG_NAMES[key] for key in LAYOUTS} == set(running)


def test_the_configurator_confirms_the_tables_mtplm() -> None:
    """Two independent sources for the one figure, which is most of the self-check."""
    assert read_gross_vehicle_mass(_page("atom_config.html")) == 3500
    assert {p.mtplm_kilograms for p in _products()} == {3500}


def test_the_payload_is_derived_because_atom_publish_none() -> None:
    product = replace(_by_label()["Core B"], mro_kilograms=2720)

    assert product.mh_payload_kilograms == 3500 - 2720 == 780
    snippet = _build_extracted_motorhome(product).provenance["mh_payload_kilograms"].snippet
    assert "nothing corroborates this" in snippet


def test_no_running_order_means_no_payload() -> None:
    assert _by_label()["Core B"].mh_payload_kilograms is None


# --------------------------------------------------------------------------- #
# The price, which the website does not publish
# --------------------------------------------------------------------------- #


def test_the_on_the_road_prices_are_the_press_packs() -> None:
    assert OTR_PRICES == {
        ("Core", "B"): 62_600,
        ("Core", "G"): 61_940,
        ("Element", "B"): 68_925,
        ("Element", "G"): 68_260,
    }


def test_every_layout_is_priced() -> None:
    assert all(product.rrp_pounds is not None for product in _products())


def test_the_price_provenance_says_it_is_not_from_the_site() -> None:
    """A reviewer must not think a run confirmed this, because no run can."""
    snippet = _build_extracted_motorhome(_by_label()["Core B"]).provenance["rrp_pounds"].snippet

    assert "press pack" in snippet
    assert "Not from the website" in snippet
    assert "re-checked by hand" in snippet


def test_the_configurators_prices_are_not_the_on_the_road_ones() -> None:
    """Its "Winter Sale Price" is the ex works figure mislabelled, hence the constants."""
    text = plain_text(_page("atom_config.html"))

    assert "Winter Sale Price" in text
    assert "£62,155" in text  # ex works for the Core 600B
    assert "62,600" not in text  # the on-the-road price appears nowhere


# --------------------------------------------------------------------------- #
# The self-check, such as it is
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("label", ["Core B", "Core G", "Element B", "Element G"])
def test_every_real_layout_reconciles(label: str) -> None:
    product = replace(_by_label()[label], mro_kilograms=2720)
    reconciles, why_not = _reconciles(product)

    assert reconciles is True, why_not


def test_a_running_order_above_the_mtplm_is_caught() -> None:
    """What reading the GVM as a running order, or crossing two layouts, looks like."""
    product = replace(_by_label()["Core B"], mro_kilograms=3500)

    reconciles, why_not = _reconciles(product)

    assert reconciles is False
    assert "not below its MTPLM" in why_not


def test_an_implausible_payload_is_caught() -> None:
    product = replace(_by_label()["Core B"], mro_kilograms=1200)

    reconciles, why_not = _reconciles(product)

    assert reconciles is False
    assert "too much for a 3.5 tonne panel van" in why_not


def test_a_product_missing_a_published_figure_is_dropped() -> None:
    product = AtomProduct(manufacturer_range="Core", model="B", source_url="x")

    reconciles, why_not = _reconciles(product)

    assert reconciles is False
    assert "comparison table yielded no" in why_not


# --------------------------------------------------------------------------- #
# Habitation, which is in the prose rather than in any list
# --------------------------------------------------------------------------- #


def test_the_equipment_is_not_in_list_items() -> None:
    """Atom render their specification as divs, which is why the first run found nothing.

    `habitation.list_items` sees only the navigation, so the prose is split into sentences
    instead — see `copy_lines_from`.
    """
    from src.adapters import habitation  # noqa: PLC0415

    items = habitation.list_items(_page("atom_core_b.html"))

    assert len(items) < 20
    assert not any("fridge" in item.lower() for item in items)


def test_the_prose_yields_the_fridge_and_the_heating() -> None:
    lines = copy_lines_from(_page("atom_core_b.html"))
    product = replace(_by_label()["Core B"], copy_lines=tuple(lines))

    motorhome = _build_extracted_motorhome(product).motorhome

    assert motorhome.refrigeration is not None
    assert motorhome.heating is not None


def test_a_habitation_finding_quotes_the_page() -> None:
    product = replace(
        _by_label()["Core B"], copy_lines=tuple(copy_lines_from(_page("atom_core_b.html")))
    )

    snippet = _build_extracted_motorhome(product).provenance["refrigeration"].snippet

    assert "fridge" in snippet.lower()


def test_a_page_with_no_prose_asserts_nothing() -> None:
    """Silence is not a negative."""
    motorhome = _build_extracted_motorhome(_by_label()["Core B"]).motorhome

    assert motorhome.refrigeration is None
    assert motorhome.heating is None
    assert motorhome.microwave is None


# --------------------------------------------------------------------------- #
# What else reaches the reviewer
# --------------------------------------------------------------------------- #


def test_every_layout_is_a_high_top_vw_campervan() -> None:
    motorhome = _build_extracted_motorhome(_by_label()["Core B"]).motorhome

    assert BODY_TYPE is BodyType.CAMPERVAN_HIGH_TOP
    assert motorhome.body_type is BodyType.CAMPERVAN_HIGH_TOP
    assert motorhome.base_vehicle_manufacturer == BASE_VEHICLE == "VW"


def test_the_height_provenance_explains_which_source_won() -> None:
    snippet = _build_extracted_motorhome(_by_label()["Core B"]).provenance["mh_height_mm"].snippet

    assert "2170mm" in snippet
    assert "high-top threshold" in snippet


# --------------------------------------------------------------------------- #
# Wiring
# --------------------------------------------------------------------------- #


def test_the_adapter_is_registered_under_its_fmlv_name() -> None:
    assert adapter_for("Trigano") is atom


# --------------------------------------------------------------------------- #
# The spec rows, which are the real cross-check
# --------------------------------------------------------------------------- #


def test_the_spec_rows_are_recovered_as_label_and_value() -> None:
    """Atom render these as divs, which is why `habitation.list_items` found nothing."""
    rows = atom.spec_rows(_page("atom_core_b.html"))

    assert rows["Heating & Hot Water"] == "Truma Combi Neo 4E"
    assert rows["70ltr compressor fridge"] == "Included"
    assert rows["Width (excl. door mirrors)"] == "2040mm"


def test_a_model_page_agrees_with_the_comparison_table() -> None:
    """Two independently rendered sources for the same three figures."""
    rows = atom.spec_rows(_page("atom_core_b.html"))

    assert atom.cross_check(_by_label()["Core B"], rows) == []


def test_a_model_page_that_disagrees_is_reported() -> None:
    """The fault this catches: the table and the page drifting apart under the parse."""
    rows = {**atom.spec_rows(_page("atom_core_b.html")), "Length": "6200mm"}

    notes = atom.cross_check(_by_label()["Core B"], rows)

    assert len(notes) == 1
    assert "5986mm for mh_length_mm" in notes[0]
    assert "6200mm" in notes[0]


def test_the_height_is_never_cross_checked() -> None:
    """It disagrees by design — 2170mm on the Core pages against the table's 2710mm.

    Checking it would warn on every run about something already settled.
    """
    assert "mh_height_mm" not in atom.CROSS_CHECKED
    assert atom.spec_rows(_page("atom_core_b.html"))["Height"] == "2170mm"
    assert atom.cross_check(_by_label()["Core B"], atom.spec_rows(_page("atom_core_b.html"))) == []


def test_a_missing_row_is_not_a_disagreement() -> None:
    """The Element pages publish no height, and an absent row contradicts nothing."""
    assert atom.cross_check(_by_label()["Core B"], {}) == []
