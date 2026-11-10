"""Landseer's parsing, against the two documents its media library actually served.

Pure parsing only: no network and no PDF handling. The `.txt` fixtures are what
`fetch.pdf.extract_text` produced from the 12 October 2026 editions, and
`landseer-custom-2-0-2027-pricing-august.txt` is the superseded August edition, kept
because its long-wheelbase price extracts with two stray glyphs in front of it.

Every negative test here is a trap that was hit while the adapter was being written, or
one the survey found waiting: the filename that repeats across editions, the option line
that looks like a sixth model, the mass nobody publishes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.adapters import landseer
from src.product_model.enums import BodyType, Heating

FIXTURES = Path(__file__).parent / "fixtures"


def _text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def pricing_sheet() -> str:
    return _text("landseer-custom-2-0-2027-pricing.txt")


@pytest.fixture
def artemis_brochure() -> str:
    return _text("landseer-artemis-2027-brochure.txt")


@pytest.fixture
def media_library() -> str:
    return _text("landseer-media-library.json")


def _custom_products(pricing_sheet: str) -> dict[tuple[str, str], landseer.LandseerProduct]:
    products = landseer.parse_pricing_sheet(pricing_sheet, "https://example.invalid", "fixture")
    return {(p.manufacturer_range, p.model): p for p in products}


# --------------------------------------------------------------------------- #
# Choosing the document
# --------------------------------------------------------------------------- #


def test_the_newest_edition_of_each_document_is_chosen(media_library: str) -> None:
    found = landseer.documents(media_library)

    assert set(found) == {"custom", "artemis"}
    assert found["custom"][2][:10] == "2026-10-12"
    assert found["artemis"][2][:10] == "2026-10-12"


def test_a_superseded_edition_filed_under_the_same_filename_is_not_chosen(
    media_library: str,
) -> None:
    """The Artemis brochure's filename is identical under `/2026/10/` and `/2026/08/`.

    Only the media listing's date tells them apart, which is why no URL is hardcoded and
    why the path is never read as a date.
    """
    items = json.loads(media_library)
    artemis = [
        item
        for item in items
        if "artemis" in item["title"]["rendered"].lower()
        and item["source_url"].endswith("57682-Landseer-Artemis-4pp-A4-1.pdf")
    ]
    assert len(artemis) == 2, "the two same-named editions should both still be listed"
    assert {item["source_url"].split("/uploads/")[1][:7] for item in artemis} == {
        "2026/10",
        "2026/08",
    }

    chosen = landseer.documents(media_library)["artemis"][0]
    assert "/2026/10/" in chosen


def test_the_pricing_sheet_is_whatever_is_newest_and_not_the_artemis(
    media_library: str,
) -> None:
    """Classified on the title, because the print job number changes when a job is re-set.

    `56143` became `57688` between the December 2025 and June 2026 editions while the
    document stayed the same, so keying on that number would have stopped finding it.
    """
    found = landseer.documents(media_library)

    assert "artemis" not in found["custom"][1].lower()
    assert "Pricing" in found["custom"][1]


def test_a_payload_that_is_not_a_media_listing_yields_nothing() -> None:
    assert landseer.documents("<html>404</html>") == {}
    assert landseer.documents('{"code":"rest_no_route"}') == {}


# --------------------------------------------------------------------------- #
# The price table
# --------------------------------------------------------------------------- #


def test_the_six_priced_lines_are_read_with_their_wheelbase_and_gearbox(
    pricing_sheet: str,
) -> None:
    lines = landseer._price_lines(pricing_sheet)

    assert [(line.engine, line.wheelbase, line.is_automatic, line.pounds) for line in lines] == [
        ("2.0", "SWB", False, 76_000),
        ("2.0", "SWB", True, 79_950),
        ("2.5", "SWB", True, 89_000),
        ("2.0", "LWB", False, 81_000),
        ("2.0", "LWB", True, 84_950),
        ("2.5", "LWB", True, 94_000),
    ]


def test_the_leighton_edition_is_an_option_and_never_becomes_a_model(
    pricing_sheet: str,
) -> None:
    """`Custom 2.0/2.5 - Leighton LV-RF Edition  Additional £7,000`.

    One price on either vehicle is the signature of an option, and this line sits in the
    model table where the six real ones do. It names two engines and no wheelbase, which
    is what keeps it out.
    """
    assert "Leighton" in pricing_sheet
    assert not any(
        "Leighton" in line.text for line in landseer._price_lines(pricing_sheet)
    )


def test_a_price_column_with_stray_glyphs_in_front_of_it_is_still_read() -> None:
    """The August 2026 edition extracts its long-wheelbase manual as `(LWB) °°£81,000`."""
    august = _text("landseer-custom-2-0-2027-pricing-august.txt")

    assert "°°£81,000" in august
    priced = {
        (line.engine, line.wheelbase, line.is_automatic): line.pounds
        for line in landseer._price_lines(august)
    }
    assert priced[("2.0", "LWB", False)] == 81_000


def test_the_price_grid_closes_as_a_rectangle(pricing_sheet: str) -> None:
    holds, note = landseer.price_grid_holds(landseer._price_lines(pricing_sheet))

    assert holds
    assert "£5,000" in note
    assert "£3,950" in note


def test_a_price_landing_on_the_wrong_row_breaks_the_grid(pricing_sheet: str) -> None:
    """The failure this check exists for: a shifted column, which nothing else would see."""
    lines = list(landseer._price_lines(pricing_sheet))
    shifted = [
        line if line.wheelbase != "LWB" or line.engine != "2.5"
        else landseer._PriceLine(line.engine, line.wheelbase, line.is_automatic, 97_500, line.text)
        for line in lines
    ]

    holds, note = landseer.price_grid_holds(shifted)

    assert not holds
    assert "not constant" in note


def test_a_sheet_that_is_not_the_pricing_sheet_is_refused(artemis_brochure: str) -> None:
    """`documents` picks the pricing sheet as "whatever is not the Artemis", so a third
    model's brochure could reach `parse_pricing_sheet`. It raises rather than returning
    nothing, so the run fails loudly instead of quietly collecting no Customs.
    """
    with pytest.raises(ValueError, match="priced model lines"):
        landseer.parse_pricing_sheet(artemis_brochure, "https://example.invalid", "fixture")


# --------------------------------------------------------------------------- #
# The Custom products
# --------------------------------------------------------------------------- #


def test_the_pricing_sheet_yields_four_products_across_two_ranges(
    pricing_sheet: str,
) -> None:
    """The automatic is an option on a manual base, so it is not a fifth and sixth product.

    The PHEV is, on the requester's decision of 10 November 2026 — a different engine at
    £13,000 more.
    """
    products = _custom_products(pricing_sheet)

    assert set(products) == {
        (landseer.CUSTOM_2_0, "SWB"),
        (landseer.CUSTOM_2_0, "LWB"),
        (landseer.CUSTOM_2_5, "SWB"),
        (landseer.CUSTOM_2_5, "LWB"),
    }


def test_the_recorded_price_is_the_manual_and_the_automatic_goes_to_its_own_column(
    pricing_sheet: str,
) -> None:
    short = _custom_products(pricing_sheet)[(landseer.CUSTOM_2_0, "SWB")]

    assert short.rrp_pounds == 76_000
    assert short.automatic_rrp_pounds == 79_950
    assert not short.automatic_is_the_only_gearbox


def test_the_phev_is_automatic_only_so_its_two_prices_are_one_figure(
    pricing_sheet: str,
) -> None:
    """`Custom 2.5 - PHEV 232ps 1 Speed Automatic`. There is no manual to record."""
    phev = _custom_products(pricing_sheet)[(landseer.CUSTOM_2_5, "LWB")]

    assert phev.rrp_pounds == 94_000
    assert phev.automatic_rrp_pounds == 94_000
    assert phev.automatic_is_the_only_gearbox


def test_each_wheelbase_takes_its_own_length_and_gross_weight(pricing_sheet: str) -> None:
    products = _custom_products(pricing_sheet)
    short = products[(landseer.CUSTOM_2_0, "SWB")]
    long = products[(landseer.CUSTOM_2_0, "LWB")]

    assert (short.mh_length_mm, short.mtplm_kilograms) == (5_050, 3_175)
    assert (long.mh_length_mm, long.mtplm_kilograms) == (5_450, 3_225)
    assert short.mh_width_mm == long.mh_width_mm == 2_150
    assert short.mh_height_mm == long.mh_height_mm == 2_070


def test_the_published_width_keeps_landseers_own_qualification(pricing_sheet: str) -> None:
    """`2.15m wide (mirrors folded)` is the only width Landseer publish anywhere.

    Recorded as stated, with the wording mirrored into the provenance rather than adjusted
    towards a body width nobody has measured.
    """
    short = _custom_products(pricing_sheet)[(landseer.CUSTOM_2_0, "SWB")]

    assert short.mh_width_note == "(mirrors folded)"
    extracted = landseer._build_extracted_motorhome(short)
    assert "mirrors folded" in extracted.provenance["mh_width_mm"].snippet


def test_no_mass_in_running_order_and_no_payload_is_ever_proposed(
    pricing_sheet: str,
) -> None:
    """Landseer have never published either, in any of the ten editions.

    A field with no provenance is not proposed, which is what leaves FMLV's own 2,400kg
    and 775kg on the two Custom rows alone. Proposing an empty value would blank them.
    """
    assert "running order" not in pricing_sheet.lower()
    assert "payload" not in pricing_sheet.lower()

    for product in _custom_products(pricing_sheet).values():
        extracted = landseer._build_extracted_motorhome(product)
        assert extracted.motorhome.mro_kilograms is None
        assert extracted.motorhome.mh_payload_kilograms is None
        assert "mro_kilograms" not in extracted.provenance
        assert "mh_payload_kilograms" not in extracted.provenance


def test_the_seat_count_is_reconciled_against_the_belts(pricing_sheet: str) -> None:
    """`5 travelling seats` and `with 3 x 3-point safety belts`, printed separately."""
    short = _custom_products(pricing_sheet)[(landseer.CUSTOM_2_0, "SWB")]

    assert short.mh_passenger_seats_inc_driver == 5
    assert short.rear_three_point_belts == 3
    reconciles, note = landseer._reconciles(short)
    assert reconciles
    assert "plus the two cab seats is 5" in note


def test_a_seat_count_the_belts_do_not_support_is_dropped(pricing_sheet: str) -> None:
    short = _custom_products(pricing_sheet)[(landseer.CUSTOM_2_0, "SWB")]
    short.mh_passenger_seats_inc_driver = 7

    reconciles, note = landseer._reconciles(short)

    assert not reconciles
    assert "claims 7 travelling seats" in note


def test_the_upgrade_to_seven_seats_is_not_counted(pricing_sheet: str) -> None:
    """`5 travelling seats (upgradable to 7)`. The upgrade is a paid extra."""
    assert "upgradable to 7" in pricing_sheet

    short = _custom_products(pricing_sheet)[(landseer.CUSTOM_2_0, "SWB")]
    assert short.mh_passenger_seats_inc_driver == 5


def test_the_custom_is_a_campervan_with_an_elevating_roof(pricing_sheet: str) -> None:
    """2.07m with a standard SCA pop-top, well under the 2,300mm high-top threshold."""
    short = _custom_products(pricing_sheet)[(landseer.CUSTOM_2_0, "SWB")]
    motorhome = landseer._build_extracted_motorhome(short).motorhome

    assert motorhome.body_type is BodyType.CAMPERVAN_ELEVATING_ROOF


def test_the_base_vehicle_is_recorded_as_fmlv_spells_it(pricing_sheet: str) -> None:
    short = _custom_products(pricing_sheet)[(landseer.CUSTOM_2_0, "SWB")]

    assert landseer._build_extracted_motorhome(short).motorhome.base_vehicle_manufacturer == "Ford"


def test_the_shared_specification_is_named_as_shared_on_the_phev(
    pricing_sheet: str,
) -> None:
    """One GVW pair covers both engines, so the PHEV's mass is not one measured for it."""
    phev = _custom_products(pricing_sheet)[(landseer.CUSTOM_2_5, "SWB")]
    snippet = landseer._build_extracted_motorhome(phev).provenance["mtplm_kilograms"].snippet

    assert "ONE GVW pair" in snippet


# --------------------------------------------------------------------------- #
# The Artemis
# --------------------------------------------------------------------------- #


def _artemis(brochure: str) -> landseer.LandseerProduct:
    return landseer.parse_artemis_brochure(brochure, "https://example.invalid", "fixture")


def test_the_artemis_is_a_man_at_its_launch_price(artemis_brochure: str) -> None:
    product = _artemis(artemis_brochure)
    motorhome = landseer._build_extracted_motorhome(product).motorhome

    assert motorhome.manufacturer_range == landseer.ARTEMIS
    assert motorhome.rrp_pounds == 106_900
    assert motorhome.base_vehicle_manufacturer == "MAN"


def test_the_artemis_is_not_a_renamed_custom(
    artemis_brochure: str, pricing_sheet: str
) -> None:
    """A different base vehicle at a different price, which is what settles it.

    The requester asked for a rename to be watched for; a MAN TGE at £106,900 against a
    Ford Transit Custom at £76,000 is a new model.
    """
    artemis = _artemis(artemis_brochure)
    custom = _custom_products(pricing_sheet)[(landseer.CUSTOM_2_0, "SWB")]

    assert artemis.base_vehicle != custom.base_vehicle
    assert artemis.rrp_pounds is not None and custom.rrp_pounds is not None
    assert artemis.rrp_pounds > custom.rrp_pounds * 1.3


def test_the_artemis_publishes_no_mass_no_dimension_and_no_berth_count(
    artemis_brochure: str,
) -> None:
    """The brochure is a brochure. Nothing is invented to fill the gaps."""
    motorhome = landseer._build_extracted_motorhome(_artemis(artemis_brochure)).motorhome

    assert motorhome.mtplm_kilograms is None
    assert motorhome.mro_kilograms is None
    assert motorhome.mh_length_mm is None
    assert motorhome.mh_width_mm is None
    assert motorhome.mh_height_mm is None
    assert motorhome.berths is None


def test_the_artemis_body_type_stays_blank(artemis_brochure: str) -> None:
    """No height is published, and its pop-top is a £9,200 option rather than evidence.

    Deriving a body type from eight mutually exclusive columns on an unpublished height is
    the guess the settled rule forbids.
    """
    product = _artemis(artemis_brochure)

    assert product.body_type is None
    assert "Pop-Top for MWB MAN TGE" in artemis_brochure
    extracted = landseer._build_extracted_motorhome(product)
    assert "body_type" not in extracted.provenance


def test_the_artemis_records_no_travel_seats(artemis_brochure: str) -> None:
    """Its bench is `2 travel positions, see options for 4 positions`, with no belt type.

    Only three-point belts count towards the figure and Landseer name none here, so the
    field is left for Landseer to answer rather than inferred from the seat count.
    """
    motorhome = landseer._build_extracted_motorhome(_artemis(artemis_brochure)).motorhome

    assert motorhome.mh_passenger_seats_inc_driver is None


def test_the_artemis_heating_is_read_from_the_truma(artemis_brochure: str) -> None:
    """`Truma 6DE - Diesel and Electric Hot Air and Water Heater (3 outlets)`."""
    motorhome = landseer._build_extracted_motorhome(_artemis(artemis_brochure)).motorhome

    assert motorhome.heating is Heating.BLOWN_AIR


def test_the_artemis_options_are_not_read_as_standard_equipment(
    artemis_brochure: str,
) -> None:
    """The £9,200 pop-top, the £3,500 second seat and the £1,895 air conditioning.

    The split is structural — everything after `OPTIONAL UPGRADES` — because a standard
    feature listed without a price would otherwise be indistinguishable from an extra.
    """
    product = _artemis(artemis_brochure)

    assert not any("Pop-Top for MWB" in line for line in product.standard_lines)
    assert any("Pop-Top for MWB" in line for line in product.all_lines)
    assert any("Shower Room with Premium Modern Tile" in line for line in product.standard_lines)


# --------------------------------------------------------------------------- #
# The roster
# --------------------------------------------------------------------------- #


def test_the_index_links_exactly_the_two_model_pages_and_the_conversion_service() -> None:
    """One page sells both Custom wheelbases, which is why FMLV holds two products for it.

    `/campervans/conversions` is Landseer's bespoke conversion service — a body shop and a
    paint booth, with no vehicle of its own.
    """
    slugs = landseer.parse_roster(_text("landseer-campervans-index.html"))

    assert set(slugs) == set(landseer.KNOWN_MODEL_PAGES) | set(landseer.NOT_A_MODEL)
    assert "conversions" in slugs


def test_a_model_page_nobody_has_surveyed_is_not_silently_ignored() -> None:
    index = '<a href="/campervans/landseer-orion">Orion</a>'

    slugs = landseer.parse_roster(index)

    assert "landseer-orion" not in landseer.KNOWN_MODEL_PAGES
    assert "landseer-orion" not in landseer.NOT_A_MODEL
    assert slugs == ("landseer-orion",)


# --------------------------------------------------------------------------- #
# Wiring
# --------------------------------------------------------------------------- #


def test_the_manufacturer_string_is_fmlvs_and_not_the_nccs() -> None:
    """FMLV's export says `Landseer`; the NCC supplier dropdown says `Landseer Leisure`.

    Crossing them means the run finds an empty baseline and proposes all five as new.
    """
    assert landseer.MANUFACTURER == "Landseer"
    assert landseer.MANUFACTURER_DISPLAY_NAME == "Landseer"


def test_every_range_is_offered_to_the_range_flag() -> None:
    labels = {label for _, label in landseer.DEFAULT_RANGES}

    assert labels == {landseer.CUSTOM_2_0, landseer.CUSTOM_2_5, landseer.ARTEMIS}


def test_the_expected_product_count_is_what_the_two_documents_describe(
    pricing_sheet: str, artemis_brochure: str
) -> None:
    products = landseer.parse_pricing_sheet(pricing_sheet, "https://example.invalid", "fixture")
    products.append(_artemis(artemis_brochure))

    assert len(products) == landseer.EXPECTED_PRODUCTS
