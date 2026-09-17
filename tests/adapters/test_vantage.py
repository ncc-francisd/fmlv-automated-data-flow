"""Tests for the Vantage adapter's pure parsing functions, against the real pages.

Fixtures are four real pages from `vantagemotorhomes.co.uk`, fetched 17 September 2026
with `<script>` and `<style>` removed. Four, because each carries something the others do
not:

* **the 5.99m index** — six models, and the trap that both Ford F-Lines are linked from a
  *panel van* index.
* **cub** — an ordinary Fiat layout, and the marketing line "upgrade from a pop-top" that
  must not be read as an elevating roof.
* **ora-f-line** — the Ford, and the mixed-case heading (`ORA F Line`) that an
  upper-case-only pattern silently dropped.
* **vantage-r** — a **stock** page, which must be rejected. This is the negative test the
  whole roster design exists for.

No network here.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.adapters import adapter_for, vantage
from src.adapters.vantage import (
    DEFAULT_RANGES,
    EXPECTED_LAYOUTS,
    MANUFACTURER,
    _KNOWN_NON_MODELS,
    _reconciles,
    build_extracted,
    elevating_roof_in,
    find_model_slugs,
    parse_model_page,
)
from src.adapters import habitation
from src.product_model.enums import BodyType
from src.vehicle_class import VehicleClass

FIXTURES = Path(__file__).parent / "fixtures"

URL = "https://www.vantagemotorhomes.co.uk/cub"

PAGES = {
    "index": "vantage_index_599.html",
    "cub": "vantage_cub.html",
    "ora-f-line": "vantage_ora_f_line.html",
    "stock": "vantage_stock.html",
}


def _page(name: str) -> str:
    return (FIXTURES / PAGES[name]).read_text(encoding="utf-8")


def _product(slug: str, *, index_range: str | None = "5.99m"):
    parsed = parse_model_page(_page(slug), slug, index_range=index_range)
    assert parsed is not None
    return parsed


# --------------------------------------------------------------------------- #
# Registration
# --------------------------------------------------------------------------- #


def test_the_adapter_is_registered_for_campervans() -> None:
    assert adapter_for(MANUFACTURER, VehicleClass.MOTORHOME) is vantage
    assert vantage.VEHICLE_CLASS is VehicleClass.MOTORHOME
    assert MANUFACTURER == "Vantage"


def test_there_are_three_length_ranges() -> None:
    assert [label for _path, label in DEFAULT_RANGES] == ["5.41m", "5.99m", "6.36m"]


# --------------------------------------------------------------------------- #
# The range is the length — the inverted identity
# --------------------------------------------------------------------------- #


def test_the_range_is_the_length_and_the_model_is_the_name() -> None:
    """Inverted from every other brand, and confirmed against FMLV's own export."""
    cub = _product("cub", index_range="5.41m")

    assert cub.manufacturer_range == "5.41m"
    assert cub.model == "CUB"


def test_the_range_comes_from_the_page_not_from_the_index() -> None:
    """The index is used to check the range, never to supply it."""
    assert _product("cub", index_range=None).manufacturer_range == "5.41m"


def test_the_f_line_heading_is_not_upper_case() -> None:
    """The bug that silently collected 11 of 13: eleven pages head themselves `CUB`, and
    the other two head themselves `ORA F Line`. Only `EXPECTED_LAYOUTS` disagreed."""
    f_line = _product("ora-f-line")

    assert f_line.model == "ORA F-Line"
    assert f_line.manufacturer_range == "5.99m"


def test_the_f_line_name_is_hyphenated_as_vantage_write_it_elsewhere() -> None:
    """The heading says `ORA F Line`; the page title and its own prose say `ORA F-Line`.
    These two are new products, so the name proposed here becomes the name FMLV holds."""
    assert "ORA F Line" in _page("ora-f-line")
    assert _product("ora-f-line").model == "ORA F-Line"


# --------------------------------------------------------------------------- #
# The roster, and everything that is not a Vantage
# --------------------------------------------------------------------------- #


def test_the_index_links_both_fords_from_a_panel_van_page() -> None:
    """Which is why the make cannot come from the section — see the module docstring."""
    slugs = find_model_slugs(_page("index"))

    assert {"ora", "sol", "max", "teo", "ora-f-line", "sol-f-line-13"} <= set(slugs)


def test_the_stock_page_is_not_a_model_and_is_rejected() -> None:
    """The negative test the roster design exists for. `/vantage-r` lists used and ex-demo
    vehicles with their own prices, and reading one would propose a second-hand van as a
    current model."""
    assert "Stock Bonus" in _page("stock")

    assert parse_model_page(_page("stock"), "vantage-r") is None


def test_the_navigation_is_not_mistaken_for_models() -> None:
    """Pilote's pages are on every index, and Pilote are a different FMLV manufacturer."""
    slugs = set(find_model_slugs(_page("index")))

    assert not slugs & {"pilote", "pilote-atlas", "pilote-pacific", "galaxy"}
    assert {"pilote", "galaxy", "motorhome-stock", "vantage-r"} <= _KNOWN_NON_MODELS


def test_a_page_that_is_not_a_model_yields_nothing() -> None:
    assert parse_model_page("<html><body>Vantage</body></html>", "x") is None


def test_the_panel_van_roster_is_thirteen() -> None:
    """Vantage publish no count, so `EXPECTED_LAYOUTS` is the only guard against a lost
    card — and it is what caught the mixed-case heading bug. It covers both sections:
    thirteen panel vans plus the two campervans."""
    assert EXPECTED_LAYOUTS == 15


# --------------------------------------------------------------------------- #
# The figures
# --------------------------------------------------------------------------- #


def test_a_model_yields_every_field() -> None:
    cub = _product("cub", index_range="5.41m")

    assert cub.berths == 2
    assert cub.travel_seats == 2
    assert cub.base_vehicle_manufacturer == "Fiat"
    assert cub.mtplm_kilograms == 3500
    assert cub.payload_kilograms == 600
    assert cub.rrp_pounds == 74_995


def test_the_mass_in_running_order_is_derived() -> None:
    """Vantage publish no MRO. The derivation reproduces FMLV's stored figure exactly on
    all eleven existing models — 3500 - 600 = 2900 is what FMLV holds for the CUB."""
    assert _product("cub", index_range="5.41m").mro_kilograms == 2900


def test_the_base_vehicle_is_the_make_alone() -> None:
    """One name per company, not the trim — and read per page, so the Ford is a Ford."""
    assert _product("ora-f-line").base_vehicle_manufacturer == "Ford"
    assert _product("cub", index_range="5.41m").base_vehicle_manufacturer == "Fiat"
    assert "Transit" in _product("ora-f-line").base_vehicle_evidence


def test_the_price_is_the_otr_headline_and_not_an_option() -> None:
    """The same page lists `8 Speed Automatic Transmission £2520` and `CAT 1 Alarm £525`
    in a quotation calculator. The first bare £ on the page is not the price."""
    assert "£2520" in _page("cub") or "2520" in _page("cub")

    assert _product("cub", index_range="5.41m").rrp_pounds == 74_995


def test_a_page_with_no_otr_line_yields_no_price() -> None:
    """Better than a £525 campervan."""
    page = _page("cub").replace("(OTR)", "(each)")

    parsed = parse_model_page(page, "cub")
    assert parsed is not None
    assert parsed.rrp_pounds is None


# --------------------------------------------------------------------------- #
# The self-check
# --------------------------------------------------------------------------- #


def test_a_model_reconciles() -> None:
    assert _reconciles(_product("cub", index_range="5.41m"))[0] is True


def test_a_page_linked_from_the_wrong_length_index_is_dropped() -> None:
    """The only genuinely independent check this source offers: the index states the
    range and the page states its own."""
    reconciles, why_not = _reconciles(_product("cub", index_range="6.36m"))

    assert reconciles is False
    assert "6.36m" in why_not and "5.41m" in why_not


def test_a_payload_that_exceeds_the_vehicle_is_dropped() -> None:
    product = _product("cub", index_range="5.41m")

    reconciles, why_not = _reconciles(replace(product, payload_kilograms=4000))

    assert reconciles is False
    assert "no vehicle" in why_not


def test_a_model_missing_a_mass_is_dropped() -> None:
    product = _product("cub", index_range="5.41m")

    reconciles, why_not = _reconciles(replace(product, mtplm_kilograms=None))

    assert reconciles is False
    assert "gross vehicle weight" in why_not


# --------------------------------------------------------------------------- #
# What reaches the reviewer
# --------------------------------------------------------------------------- #


def test_every_model_is_a_high_top_campervan() -> None:
    """Asserted, because the roof rule needs a height and Vantage publish none. FMLV
    already holds this on all eleven existing models."""
    extracted = build_extracted(_product("cub", index_range="5.41m"), URL, basis="x")

    assert extracted.motorhome.body_type is BodyType.CAMPERVAN_HIGH_TOP
    assert "high top" in extracted.provenance["body_type"].snippet


def test_marketing_copy_is_not_read_as_an_elevating_roof() -> None:
    """The CUB is sold as "the ideal upgrade from a pop-top", which is a sentence about a
    different kind of van. Scanning the page turned that into a warning every run."""
    assert "pop-top" in _page("cub")

    assert elevating_roof_in(tuple(habitation.list_items(_page("cub")))) is None


def test_a_real_elevating_roof_in_the_equipment_is_reported() -> None:
    assert elevating_roof_in(("Elevating roof with stitched lining",)) is not None
    assert elevating_roof_in(("Rear parking sensors",)) is None


@pytest.mark.parametrize(
    ("field_name", "expected"),
    [("mh_length_mm", 5413), ("mh_width_mm", 2280), ("mh_height_mm", 2600)],
)
def test_the_dimensions_come_from_the_length_s_drawing(field_name: str, expected: int) -> None:
    """Read by hand from `CUB-Measurements-.png`, because the site's only textual length is
    the rounded range name — 5.41m against FMLV's 5413mm — and no width or height appears
    as text at all. Every one of these matched FMLV on all eleven panel vans before the
    constant existed, so it asserts nothing new; what it removes is three "could not be
    validated" rows against every model on every run."""
    extracted = build_extracted(_product("cub", index_range="5.41m"), URL, basis="x")

    assert getattr(extracted.motorhome, field_name) == expected
    assert field_name in extracted.provenance


def test_both_halves_of_the_identity_carry_provenance() -> None:
    provenance = build_extracted(_product("cub", index_range="5.41m"), URL, basis="x").provenance

    assert "manufacturer_range" in provenance
    assert "model" in provenance
    # The range is a measurement, so the snippet has to say why.
    assert "length" in provenance["manufacturer_range"].snippet


def test_the_base_vehicle_snippet_says_where_it_was_read() -> None:
    """Because the obvious wrong source — the index section — gives Fiat for a Ford."""
    extracted = build_extracted(_product("ora-f-line"), URL, basis="x")

    assert "own page" in extracted.provenance["base_vehicle_manufacturer"].snippet


# --------------------------------------------------------------------------- #
# The two campervans, which live in modal dialogues
# --------------------------------------------------------------------------- #


def _campervans():
    from src.adapters.vantage import read_campervans  # noqa: PLC0415

    return {c.manufacturer_range: c for c in read_campervans(_campervans_page())}


def _campervans_page() -> str:
    return (FIXTURES / "vantage_campervans.html").read_text(encoding="utf-8")


def test_both_campervans_are_collected_so_neither_is_reported_as_gone() -> None:
    """The whole point. `/fuze` and `/luna` both 404 and no index links them, so without
    this the run says two live vehicles have left the range every time."""
    assert set(_campervans()) == {"Fuze", "Luna"}
    assert all(c.model == "Conversion" for c in _campervans().values())


def test_the_campervan_section_links_no_model_pages() -> None:
    """Which is why they are read from the dialogue markup rather than from hrefs."""
    from src.adapters.vantage import find_model_slugs  # noqa: PLC0415

    assert find_model_slugs(_campervans_page()) == []


def test_only_luna_states_its_roof_and_only_luna_gets_a_body_type() -> None:
    """"pop-top" appears exactly once in the whole document, in Luna's description.
    Fuze's own pop-top is stated only inside the flipbook, which cannot be read."""
    from src.adapters.vantage import build_extracted_campervan  # noqa: PLC0415

    luna, fuze = _campervans()["Luna"], _campervans()["Fuze"]

    assert luna.pop_top_evidence is not None
    assert fuze.pop_top_evidence is None

    assert build_extracted_campervan(luna, URL).motorhome.body_type is BodyType.CAMPERVAN_ELEVATING_ROOF
    assert build_extracted_campervan(fuze, URL).motorhome.body_type is None


def test_a_campervan_with_no_stated_roof_keeps_its_identity() -> None:
    """Dropping it is what reports a live vehicle as discontinued, so the body type goes
    unproposed and FMLV's own value stands instead."""
    from src.adapters.vantage import build_extracted_campervan  # noqa: PLC0415

    extracted = build_extracted_campervan(_campervans()["Fuze"], URL)

    assert "manufacturer_range" in extracted.provenance
    assert "model" in extracted.provenance
    assert "body_type" not in extracted.provenance


def test_the_campervans_are_not_given_the_panel_vans_body_type() -> None:
    """They are Transit Customs at 2.15m — a standard roof with a pop-top — against the
    panel vans' 2.6m. Both the fixed high top and the high-top-plus-elevating-roof
    variant were asserted at some point and both were wrong."""
    from src.adapters.vantage import build_extracted_campervan  # noqa: PLC0415

    body_type = build_extracted_campervan(_campervans()["Luna"], URL).motorhome.body_type

    assert body_type is BodyType.CAMPERVAN_ELEVATING_ROOF
    assert body_type is not BodyType.CAMPERVAN_HIGH_TOP
    assert body_type is not BodyType.CAMPERVAN_HIGH_TOP_ELEVATING_ROOF


def test_no_mass_or_price_is_read_for_a_campervan() -> None:
    """They are published only inside a Flipsnack flipbook, whose page is a JavaScript
    shell carrying no text and no PDF. FMLV's own figures stand."""
    from src.adapters.vantage import build_extracted_campervan  # noqa: PLC0415

    extracted = build_extracted_campervan(_campervans()["Luna"], URL)

    for field_name in ("mtplm_kilograms", "mro_kilograms", "mh_payload_kilograms", "rrp_pounds"):
        assert getattr(extracted.motorhome, field_name) is None
        assert field_name not in extracted.provenance


def test_the_expected_count_covers_both_sections() -> None:
    assert EXPECTED_LAYOUTS == 15


# --------------------------------------------------------------------------- #
# The dimensions drawing — every figure published, published as pixels
# --------------------------------------------------------------------------- #


def test_the_dimensions_drawing_is_found_and_absolute() -> None:
    """Returned so a reviewer filling a blank dimension is pointed at it, since nothing
    can read it: the drawing gives the length, the height and three widths, and not one
    of those numbers appears anywhere in the page's HTML."""
    from src.adapters.vantage import BASE_URL, dimensions_drawing  # noqa: PLC0415

    drawing = dimensions_drawing(_page("cub"))

    assert drawing is not None
    assert drawing.startswith(BASE_URL)
    assert drawing.endswith("CUB-Measurements-.png")


def test_the_drawings_numbers_are_in_no_page_text() -> None:
    """The reason none of them is emitted. 5413, 2050, 2280 and 2480 are all on the CUB's
    drawing and none is in its markup."""
    for number in ("5413", "2050", "2280", "2480"):
        assert number not in _page("cub")


def test_the_drawing_is_not_found_by_its_filename() -> None:
    """They are called `CUB-Measurements-.png`, `SOL-6.png` and `NEO-2.png`, with no
    pattern between them. A filename filter found three of thirteen and reported the
    other ten as having no drawing at all."""
    from src.adapters.vantage import dimensions_drawing  # noqa: PLC0415

    drawing = dimensions_drawing(_page("ora-f-line"))

    assert drawing is not None
    assert "measure" not in drawing.lower().rsplit("/", 1)[-1].replace("dimensions", "")


def test_a_photograph_is_not_mistaken_for_the_drawing() -> None:
    """WordPress stamps a resized image with its pixel size, which is what separates the
    photographs from the drawings — `AVAST_CUB-1-1200x772.jpg` against `SOL-6.png`."""
    from src.adapters.vantage import _NOT_A_DRAWING  # noqa: PLC0415

    assert _NOT_A_DRAWING.search("AVAST_CUB-1-1200x772.jpg")
    assert _NOT_A_DRAWING.search("IMG_6713-1-1067x800.jpg")
    assert _NOT_A_DRAWING.search("Fiat-Logo.png")
    assert not _NOT_A_DRAWING.search("SOL-6.png")
    assert not _NOT_A_DRAWING.search("CUB-Measurements-.png")


def test_a_page_with_no_spec_block_has_no_drawing() -> None:
    from src.adapters.vantage import dimensions_drawing  # noqa: PLC0415

    assert dimensions_drawing("<html><body>Vantage</body></html>") is None
    assert dimensions_drawing(_page("stock")) is None


def test_the_f_lines_get_their_dimensions_from_a_hand_read_constant() -> None:
    """The two new models have no stored figure to preserve, so emit-nothing would have
    meant blank forever — `swift._MANUALLY_SOURCED_HEIGHT_MM`'s reasoning exactly."""
    extracted = build_extracted(_product("ora-f-line"), URL, basis="x")

    assert extracted.motorhome.mh_length_mm == 5931
    assert extracted.motorhome.mh_width_mm == 2112
    assert extracted.motorhome.mh_height_mm == 2650


def test_the_f_line_width_is_the_mirrors_folded_one() -> None:
    """2112mm, not the bare 2032 and not the 2474 with mirrors out — the same choice FMLV
    made for the eleven Fiats, where it holds 2280 against a bare 2050."""
    snippet = build_extracted(_product("ora-f-line"), URL, basis="x").provenance[
        "mh_width_mm"
    ].snippet

    assert "2112mm" in snippet
    assert "inc.mirrors folded" in snippet


def test_the_f_lines_share_nothing_with_the_fiat_panel_vans() -> None:
    """5931 against 5998, 2112 against 2280, 2650 against 2600. Copying the panel vans'
    figures across would have been wrong on all three."""
    from src.adapters.vantage import _MANUALLY_SOURCED_DIMENSIONS_MM  # noqa: PLC0415

    assert _MANUALLY_SOURCED_DIMENSIONS_MM["ORA F-Line"] == (5931, 2112, 2650)
    assert set(_MANUALLY_SOURCED_DIMENSIONS_MM) == {"ORA F-Line", "SOL F-Line"}


def test_the_f_line_overrides_its_range_rather_than_inheriting_it() -> None:
    """Both F-Lines sit in the 5.99m range and are not 5.99m vehicles — they are a Ford
    Transit where the rest are Fiat Ducatos. Falling through to the range would put
    5998x2280x2600 on a van that is 5931x2112x2650: wrong on all three, and plausible
    enough to pass a reviewer."""
    from src.adapters.vantage import _DIMENSIONS_BY_RANGE_MM  # noqa: PLC0415

    f_line = build_extracted(_product("ora-f-line"), URL, basis="x").motorhome

    assert _DIMENSIONS_BY_RANGE_MM["5.99m"] == (5998, 2280, 2600)
    assert (f_line.mh_length_mm, f_line.mh_width_mm, f_line.mh_height_mm) == (5931, 2112, 2650)


def test_a_range_with_no_known_dimensions_emits_none() -> None:
    """A fourth length would arrive unmeasured rather than borrowing another's figures."""
    from dataclasses import replace as _replace  # noqa: PLC0415

    unknown = _replace(_product("cub", index_range="5.41m"), manufacturer_range="7.00m")
    extracted = build_extracted(unknown, URL, basis="x")

    assert extracted.motorhome.mh_length_mm is None
    assert "mh_width_mm" not in extracted.provenance


def test_the_f_line_dimensions_are_still_not_published() -> None:
    """The canary. A manually sourced constant cannot refresh itself, so this says when
    Vantage start publishing these as text and the constant can go."""
    for number in ("5931", "2112", "2650", "2032", "2474"):
        assert number not in _page("ora-f-line"), (
            f"{number} is now in the F-Line page's markup — Vantage may have started "
            f"publishing dimensions as text, so _MANUALLY_SOURCED_DIMENSIONS_MM should "
            f"be replaced by a parse"
        )
