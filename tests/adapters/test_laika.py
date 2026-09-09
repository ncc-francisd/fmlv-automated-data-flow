"""Laika's adapter — schema.org JSON-LD, and the two traps in it.

Fixtures were saved from the live site on 9 September 2026.

* **`laika_models_index_jsonld.html`** — the index page's `application/ld+json` blocks and
  nothing else, that being the whole of what `parse_layouts` reads. It carries **both**
  shapes: `ProductGroup`s for the multi-layout ranges and bare `Vehicle`s for the two Kreos
  ranges, which is the distinction a parser has to get right or lose a fifth of the roster.
* **`laika_floorplans_coachbuilt_ecovip.html`** — a well-behaved slider, five layouts.
* **`laika_floorplans_coachbuilt_kreos.html`** — the layout whose correct drawing is served
  under a Carado image-bank filename, which is why nothing here judges an asset by its name.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters import laika
from src.product_model.enums import BodyType

FIXTURES = Path(__file__).parent / "fixtures"
INDEX = "laika_models_index_jsonld.html"
SLIDER_ECOVIP = "laika_floorplans_coachbuilt_ecovip.html"
SLIDER_KREOS = "laika_floorplans_coachbuilt_kreos.html"

#: What Laika's UK site publishes: Ecovip Titanio 5 low-profile + 3 A-class, Kreos 1 + 1.
EXPECTED_LAYOUTS = 10


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def layouts() -> dict[str, laika.LaikaLayout]:
    return {item.model: item for item in laika.parse_layouts(_read(INDEX))}


# --------------------------------------------------------------------------- #
# The roster
# --------------------------------------------------------------------------- #


def test_the_index_yields_the_whole_uk_range(layouts: dict[str, laika.LaikaLayout]) -> None:
    """One fetch, ten layouts — the count Laika's own sitemap and range pages agree on."""
    assert len(layouts) == EXPECTED_LAYOUTS


def test_a_one_layout_range_is_not_dropped(layouts: dict[str, laika.LaikaLayout]) -> None:
    """The trap worth the whole fixture: both Kreos ranges are a shape of their own.

    A multi-layout range is a `ProductGroup` carrying `hasVariant`. A one-layout range is a
    bare `["Product", "Vehicle"]` with none, so a parser written for the first shape loses
    2 of 10 and says nothing about it.
    """
    assert {"H 5109 MB", "L 5009 MB"} <= set(layouts)
    assert {item.range_label for item in layouts.values()} == {"Ecovip Titanio", "Kreos"}


def test_a_range_prefixed_name_is_reduced_to_the_layout(
    layouts: dict[str, laika.LaikaLayout],
) -> None:
    """The index publishes one Kreos as `Kreos H 5109 MB` and the other as `L 5009 MB`."""
    assert layouts["H 5109 MB"].range_label == "Kreos"
    assert layouts["L 5009 MB"].range_label == "Kreos"


# --------------------------------------------------------------------------- #
# The fields
# --------------------------------------------------------------------------- #


def test_every_field_fmlv_needs_is_read(layouts: dict[str, laika.LaikaLayout]) -> None:
    """`L 2009`, checked against the page's own Technical Data panel value by value."""
    layout = layouts["L 2009"]

    assert layout.rrp_pounds == 85_100
    assert layout.mro_kilograms == 2971
    assert layout.mtplm_kilograms == 3500
    assert layout.mh_payload_kilograms == 529
    assert (layout.mh_length_mm, layout.mh_width_mm, layout.mh_height_mm) == (6590, 2250, 2990)
    assert layout.mh_passenger_seats_inc_driver == 4
    assert layout.base_vehicle_manufacturer == "Fiat"


def test_nothing_is_left_blank_across_the_roster(
    layouts: dict[str, laika.LaikaLayout],
) -> None:
    """A gap here means a field moved, and the structured data makes that detectable."""
    for layout in layouts.values():
        for field in (
            "rrp_pounds",
            "mro_kilograms",
            "mtplm_kilograms",
            "mh_length_mm",
            "mh_width_mm",
            "mh_height_mm",
            "mh_passenger_seats_inc_driver",
            "berths",
            "base_vehicle_manufacturer",
            "body_type",
        ):
            assert getattr(layout, field) is not None, f"{layout.label}.{field}"


def test_dimensions_are_converted_from_centimetres(
    layouts: dict[str, laika.LaikaLayout],
) -> None:
    """Laika publish `unitCode: CMT`; FMLV stores millimetres."""
    assert layouts["L 2009"].mh_length_mm == 6590  # the page says 659 cm


def test_berths_record_the_standard_figure(layouts: dict[str, laika.LaikaLayout]) -> None:
    """`2 - 4` means 2: the extra berths need optional equipment.

    The published string is kept so a reviewer seeing `2` can tell where it came from.
    """
    layout = layouts["L 2009"]
    assert layout.berths_published == "2 - 4"
    assert layout.berths == 2


def test_the_base_vehicle_is_the_short_name(layouts: dict[str, laika.LaikaLayout]) -> None:
    """`Mercedes-Benz Sprinter 417 AL-KO` is a Mercedes — through the shared helper."""
    assert layouts["H 5109 MB"].base_vehicle_manufacturer == "Mercedes"


# --------------------------------------------------------------------------- #
# Range and body type
# --------------------------------------------------------------------------- #


def test_the_integrated_suffix_is_not_a_range() -> None:
    """`Ecovip Titanio I` is the A-class build of `Ecovip Titanio`, not a second range.

    FMLV records the body type in its own column, exactly as Adria's 60Y editions file
    under `Matrix` rather than `Matrix 60Y`. Confirmed by the requester, 9 September 2026.
    """
    assert laika.fmlv_range("Ecovip Titanio I") == "Ecovip Titanio"
    assert laika.fmlv_range("Kreos I") == "Kreos"
    assert laika.fmlv_range("Ecovip Titanio") == "Ecovip Titanio"
    assert laika.fmlv_range(None) is None


def test_body_type_comes_from_the_url_laika_files_it_under() -> None:
    """Laika describe their range as "Low-profile and A-class" — their words, not a guess.

    The requester confirmed there is no over-cab bed anywhere in the range, and no UK
    campervans.
    """
    assert (
        laika.body_type_for("https://www.laika.it/en-gb/motorhomes/coachbuilt/kreos/")
        is BodyType.COACH_BUILT_LOW_PROFILE
    )
    assert (
        laika.body_type_for("https://www.laika.it/en-gb/motorhomes/a-class/kreos/")
        is BodyType.A_CLASS
    )
    assert laika.body_type_for("https://www.laika.it/en-gb/caravans/something/") is None
    assert laika.body_type_for(None) is None


def test_the_two_body_styles_are_both_represented(
    layouts: dict[str, laika.LaikaLayout],
) -> None:
    counts = {BodyType.A_CLASS: 0, BodyType.COACH_BUILT_LOW_PROFILE: 0}
    for layout in layouts.values():
        counts[layout.body_type] += 1  # type: ignore[index]
    assert counts == {BodyType.A_CLASS: 4, BodyType.COACH_BUILT_LOW_PROFILE: 6}


# --------------------------------------------------------------------------- #
# Floorplans, and the one that belongs to another manufacturer
# --------------------------------------------------------------------------- #


def test_a_well_behaved_slider_yields_one_drawing_per_layout() -> None:
    plans = laika.parse_floorplans(_read(SLIDER_ECOVIP))

    assert set(plans) == {"L 2009", "L 3019", "L 4009", "L 4009 DS", "L 4012 DS"}
    assert "L-2009" in plans["L 2009"]


def test_a_misleading_filename_does_not_lose_a_good_drawing() -> None:
    """`L 5009 MB`'s plan is served under a **Carado image-bank name**, and is correct.

    The Erwin Hymer Group brands share an image bank and Laika's WordPress keeps the name
    a file was uploaded under, so this layout's low-profile drawing arrives as
    `carado-imagebank-data_VE_Camper-Van_CV540…png`. A filename check was tried here first
    and threw the plan away; the requester spotted it by opening the page. An asset's name
    is not evidence about its content, and on a shared image bank not even about its brand.
    """
    section = _read(SLIDER_KREOS)

    plans = laika.parse_floorplans(section)

    assert set(plans) == {"L 5009 MB"}
    assert "carado-imagebank-data" in plans["L 5009 MB"]


def test_each_slide_keeps_to_its_own_drawing() -> None:
    """The structure is the guarantee, so a slide with no image must not borrow one."""
    section = (
        '<div class="section__floorplan-slider">'
        '<div data-name="L 2009"></div>'
        '<div data-name="L 3019">'
        '<img src="https://www.laika.it/wp-content/uploads/2026/07/L-3019.png">'
        "</div></div>"
    )

    plans = laika.parse_floorplans(section)

    assert set(plans) == {"L 3019"}


def test_a_page_with_no_slider_yields_nothing() -> None:
    assert laika.parse_floorplans("<html><body>nothing here</body></html>") == {}


# --------------------------------------------------------------------------- #
# The self-check
# --------------------------------------------------------------------------- #


def test_every_real_layout_reconciles(layouts: dict[str, laika.LaikaLayout]) -> None:
    for layout in layouts.values():
        keep, reason = laika._reconciles(layout)
        assert keep, f"{layout.label}: {reason}"


def test_two_masses_from_different_layouts_are_caught() -> None:
    """The failure this exists for: a slipped record pairing one layout's running order
    with another's permissible maximum. It reads as a plausible motorhome otherwise."""
    layout = laika.LaikaLayout(
        range_label="Kreos", model="L 5009 MB", mro_kilograms=4450, mtplm_kilograms=4500
    )

    keep, reason = laika._reconciles(layout)

    assert keep is False
    assert "different layouts" in reason


def test_a_missing_mass_is_not_treated_as_a_misalignment() -> None:
    """Nothing to check against; the absent figure is its own signal to the reviewer."""
    layout = laika.LaikaLayout(range_label="Kreos", model="L 5009 MB", mtplm_kilograms=4500)

    assert laika._reconciles(layout)[0] is True


# --------------------------------------------------------------------------- #
# Provenance
# --------------------------------------------------------------------------- #


def test_a_derived_payload_shows_its_arithmetic(
    layouts: dict[str, laika.LaikaLayout],
) -> None:
    """Laika publish no payload, so a reviewer has to see where the number came from."""
    extracted = laika._build_extracted_motorhome(layouts["L 2009"])

    snippet = extracted.provenance["mh_payload_kilograms"].snippet
    assert "3500kg permissible maximum - 2971kg running order = 529kg" in snippet
    assert "Laika publish no payload" in snippet


def test_the_floorplan_becomes_a_pointer_on_every_positional_field(
    layouts: dict[str, laika.LaikaLayout],
) -> None:
    extracted = laika._build_extracted_motorhome(
        layouts["L 2009"], "https://www.laika.it/plan-L-2009.png"
    )

    pointers = {
        name for name, entry in extracted.provenance.items() if entry.reviewer_reference
    }
    assert pointers == {
        "sleeping_area",
        "kitchen_location",
        "lounge_location",
        "bathroom_layout",
        "bed_types",
    }


def test_no_drawing_means_no_pointers(layouts: dict[str, laika.LaikaLayout]) -> None:
    """A layout whose slider is ever emptied must not leave a dead link behind."""
    extracted = laika._build_extracted_motorhome(layouts["L 5009 MB"])

    assert not [e for e in extracted.provenance.values() if e.reviewer_reference]
