"""RS Motorhomes' parsing functions, against real captured documents and pages.

No network and no PDF parsing here — `tests/fetch/test_pdf.py` covers extraction, and the
`.txt` fixtures are what it produces.

Almost every negative test below is a trap this site actually set: a cover page naming a
different chassis from the document's own table, a mass written `16 ton`, a "gross train
weight" that is really a towing capacity, two rows sharing one label three tonnes apart,
and a roster button for a model that has no vehicle. See `docs/adapters/rs-motorhomes.md`.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from src.adapters import rs_motorhomes
from src.adapters.rs_motorhomes import RSProduct
from src.product_model.enums import Heating, Refrigeration

FIXTURES = Path(__file__).parent / "fixtures"

ENDEAVOUR_SPEC = "rs-motorhomes-endeavour-2027-spec.txt"
ENVOY_SPEC = "rs-motorhomes-envoy-2027-spec.txt"
EVOLUTION_PAGE = "rs-motorhomes-evolution-specifications.html"
INDEX_PAGE = "rs-motorhomes-luxury-motorhomes-index.html"
MEDIA_LISTING = "rs-motorhomes-media-library.json"


def _text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def endeavour() -> RSProduct:
    return rs_motorhomes.parse_specification_pdf(
        _text(ENDEAVOUR_SPEC), "Endeavour", "https://example.invalid/endeavour.pdf"
    )


@pytest.fixture(scope="module")
def envoy() -> RSProduct:
    return rs_motorhomes.parse_specification_pdf(
        _text(ENVOY_SPEC), "Envoy", "https://example.invalid/envoy.pdf"
    )


@pytest.fixture(scope="module")
def evolution() -> RSProduct:
    return rs_motorhomes.parse_specification_page(
        _text(EVOLUTION_PAGE), "Evolution", rs_motorhomes.EVOLUTION_SPEC_URL
    )


# --------------------------------------------------------------------------- #
# Finding the documents nothing links
# --------------------------------------------------------------------------- #


def test_the_media_library_yields_the_three_specification_documents() -> None:
    """The whole survey. Not one of these PDFs is linked from any page on the site."""
    found = rs_motorhomes.specification_documents(_text(MEDIA_LISTING))

    for source in rs_motorhomes.MODELS:
        if source.media_title is None:
            continue
        assert source.media_title in found, source.media_title
        url, date = found[source.media_title]
        assert url.endswith(".pdf")
        assert date.startswith("2026")


def test_the_filed_path_is_not_trusted_for_the_date() -> None:
    """**The trap.** RS file their 2027 documents under `/2026/02/`, so a parser that read
    the model year out of the path would date every current document a year early."""
    found = rs_motorhomes.specification_documents(_text(MEDIA_LISTING))
    url, date = found["RS Endeavour Specification Document"]

    assert "/2026/02/" in url
    assert "2027" in _text(ENDEAVOUR_SPEC)
    assert date[:4] == "2026"


def test_only_pdfs_are_taken() -> None:
    """The listing also holds a `.doc` per model and an `.ods` vehicle stock sheet, all of
    them superseded, and `RS-Envoy.doc` would otherwise shadow nothing useful at all."""
    payload = _text(MEDIA_LISTING)
    assert ".doc" in payload
    assert ".ods" in payload

    for url, _date in rs_motorhomes.specification_documents(payload).values():
        assert url.endswith(".pdf")


def test_a_reissue_under_the_same_title_wins_on_date() -> None:
    """So RS re-uploading a document is picked up without an edit to this adapter."""
    payload = json.dumps(
        [
            {
                "source_url": "https://example.invalid/old.pdf",
                "title": {"rendered": "RS Endeavour Specification Document"},
                "date": "2026-09-23T10:00:00",
            },
            {
                "source_url": "https://example.invalid/new.pdf",
                "title": {"rendered": "RS Endeavour Specification Document"},
                "date": "2027-01-04T10:00:00",
            },
        ]
    )
    found = rs_motorhomes.specification_documents(payload)

    assert found["RS Endeavour Specification Document"][0].endswith("new.pdf")


def test_an_unreadable_listing_yields_nothing_rather_than_raising() -> None:
    assert rs_motorhomes.specification_documents("<html>not json</html>") == {}
    assert rs_motorhomes.specification_documents('{"code": "rest_forbidden"}') == {}


def test_html_entities_in_a_title_are_unescaped() -> None:
    """The listing writes `&#8211;` for an en dash, so a title is compared after unescaping
    or a document with punctuation in its name is never matched."""
    payload = json.dumps(
        [
            {
                "source_url": "https://example.invalid/a.pdf",
                "title": {"rendered": "RS Evolution &#8211; DAF LF260 &#8211; 2023"},
                "date": "2022-10-17T10:00:00",
            }
        ]
    )

    assert "RS Evolution – DAF LF260 – 2023" in rs_motorhomes.specification_documents(payload)


# --------------------------------------------------------------------------- #
# The roster
# --------------------------------------------------------------------------- #


def test_the_index_names_exactly_the_four_models() -> None:
    assert rs_motorhomes.parse_roster(_text(INDEX_PAGE)) == (
        "Endeavour",
        "Elysian",
        "Evolution",
        "Envoy",
    )


def test_the_roster_is_every_model_this_adapter_knows() -> None:
    assert {source.model for source in rs_motorhomes.MODELS} == set(
        rs_motorhomes.parse_roster(_text(INDEX_PAGE))
    )
    assert rs_motorhomes.EXPECTED_LAYOUTS == len(rs_motorhomes.MODELS)


def test_the_emotions_stale_button_is_not_read_as_a_fifth_model() -> None:
    """**The roster trap.** `/luxury-motorhomes/` carries a `DISCOVER THE RS EMOTION`
    button — on the *Bespoke* block, which is about custom adaptations and names no vehicle
    of its own. A link-following or button-following roster reports five models where RS
    sell four, which is why `parse_roster` reads the lines that name a model on their own.
    """
    index = _text(INDEX_PAGE)
    assert "DISCOVER THE RS EMOTION" in index
    assert "rs-emotion" in index

    assert "Emotion" not in rs_motorhomes.parse_roster(index)
    assert "Emotion" in rs_motorhomes.ORPHANED_PAGES


def test_the_shouted_navigation_and_the_headings_are_one_roster() -> None:
    """Both appear on the index — `RS ENDEAVOUR` in the nav, `RS Endeavour` as the heading
    — and reading them as written gives eight models instead of four."""
    index = _text(INDEX_PAGE)
    assert "RS ENDEAVOUR" in index

    roster = rs_motorhomes.parse_roster(index)
    assert len(roster) == len(set(roster)) == 4


# --------------------------------------------------------------------------- #
# Reading a specification document
# --------------------------------------------------------------------------- #


def test_the_endeavour_document_yields_every_field_fmlv_needs(endeavour: RSProduct) -> None:
    assert endeavour.base_vehicle == "Iveco Daily 72-210"
    assert endeavour.mh_length_mm == 9100
    assert endeavour.mh_width_mm == 2400
    assert endeavour.mh_height_mm == 3400
    assert endeavour.mtplm_kilograms == 7200
    assert endeavour.gross_train_kilograms == 10500
    assert endeavour.towing_capacity_kilograms == 3500
    assert endeavour.mh_passenger_seats_inc_driver == 2
    assert endeavour.rrp_pounds == 299995


def test_no_mass_in_running_order_or_payload_exists_to_read(endeavour: RSProduct) -> None:
    """**The headline risk.** RS publish neither, for any model, so the payload arithmetic
    that checks every other adapter's parse does not exist here — see `_reconciles`."""
    text = _text(ENDEAVOUR_SPEC).lower()
    for absent in ("running order", "payload", "unladen", "miro", "kerb"):
        assert absent not in text


def test_the_price_is_only_taken_when_both_printings_agree(endeavour: RSProduct) -> None:
    """The nearest thing to a self-check these documents offer: the figure appears on the
    cover and again under the standard-specification heading."""
    assert endeavour.cover_price_pounds == endeavour.body_price_pounds == 299995

    doctored = _text(ENDEAVOUR_SPEC).replace("£299,995 \n   Chassis", "£319,995 \n   Chassis")
    disagreeing = rs_motorhomes.parse_specification_pdf(doctored, "Endeavour", "x")

    assert disagreeing.cover_price_pounds == 299995
    assert disagreeing.body_price_pounds == 319995
    assert disagreeing.rrp_pounds is None
    assert any("NO PRICE IS RECORDED" in note for note in rs_motorhomes._discrepancies(disagreeing))


def test_the_options_table_is_kept_out_of_the_habitation_read(endeavour: RSProduct) -> None:
    """These documents price every extra in a table with no per-line marker, so
    `habitation.usable_lines` cannot tell an option from a fitting. The split is structural.
    """
    standard = "\n".join(endeavour.standard_lines)
    assert "Microwave Included" in standard
    assert "External Shower" not in standard
    assert "Satellite Dish" not in standard
    assert "External Shower £500" in "\n".join(endeavour.all_lines)


def test_the_cover_contradicts_the_envoys_own_chassis_table(envoy: RSProduct) -> None:
    """**The worst trap in the document.** The cover says Iveco; five lines later the
    chassis table says DAF, with a 200-litre tank, hydraulic cab tilt and a diff lock. The
    table is the vehicle. FMLV currently holds this model as a Mercedes.
    """
    assert envoy.cover_chassis == "IVECO DAILY 72-210"
    assert envoy.base_vehicle is not None
    assert envoy.base_vehicle.startswith("DAF XB")

    notes = rs_motorhomes._discrepancies(envoy)
    assert any("COVER" in note and "chassis table" in note for note in notes)


def test_a_mass_written_in_tons_is_read_in_kilogrammes(envoy: RSProduct) -> None:
    assert "Gross Vehicle Weight 16 ton" in _text(ENVOY_SPEC)
    assert envoy.mtplm_kilograms == 16000


def test_a_train_weight_that_is_really_a_towing_capacity_is_not_read(envoy: RSProduct) -> None:
    """RS write `Gross Train Weight 12-ton towing capacity`. A row contradicting its own
    label is refused, because 12,000kg recorded as a train weight would then reconcile
    against nothing and look like an error in the vehicle rather than in the document."""
    assert "12-ton towing capacity" in _text(ENVOY_SPEC)
    assert envoy.gross_train_kilograms is None


def test_the_envoy_states_its_cab_seats_differently(envoy: RSProduct) -> None:
    """`Two cab seats` is the total; `Single passenger seat` is one *beside* the driver.
    Both come to two, and one shared wording would have claimed the Envoy seats three."""
    assert envoy.mh_passenger_seats_inc_driver == 2
    assert envoy.seats_snippet is not None
    assert "the driver's among them" in envoy.seats_snippet
    assert not envoy.offers_optional_rear_belts


def test_optional_rear_belts_are_never_counted(endeavour: RSProduct) -> None:
    """Three documents offer them 'depending on layout'. A belt an option might add is not
    a belt the vehicle has, and a lap belt would not count even if it did."""
    assert endeavour.offers_optional_rear_belts
    assert endeavour.mh_passenger_seats_inc_driver == 2


# --------------------------------------------------------------------------- #
# The Evolution, which has no document
# --------------------------------------------------------------------------- #


def test_the_evolution_is_read_from_its_on_site_table(evolution: RSProduct) -> None:
    assert evolution.base_vehicle == "DAF LF 260"
    assert evolution.mh_length_mm == 9448
    assert evolution.mh_width_mm == 2600
    assert evolution.mh_height_mm == 3700
    assert evolution.rrp_pounds is None


def test_two_rows_under_one_label_refuse_the_field(evolution: RSProduct) -> None:
    """**The reason this adapter reads lists and not values.** The page prints
    `Gross Vehicle Weight – 7200KG` and `Gross Vehicle Weight – 10.5 Tonnes`, three tonnes
    apart. A label cannot choose between them. FMLV's row has used *both*, 7,200 as the
    mass in running order and 10,500 as the MTPLM, which is how this reaches a reviewer
    looking plausible.
    """
    page = _text(EVOLUTION_PAGE)
    assert "Gross Vehicle Weight" in page

    assert evolution.mtplm_kilograms is None
    assert "Gross Vehicle Weight" in evolution.ambiguous_labels
    assert any("REFUSED" in note for note in rs_motorhomes._discrepancies(evolution))


def test_an_identical_repeat_is_not_an_ambiguity(evolution: RSProduct) -> None:
    """The same page prints `Engine Capacity – 4500cc` twice. Refusing every repeated label
    would throw away a field the page is perfectly clear about."""
    assert _text(EVOLUTION_PAGE).count("Engine Capacity") >= 2
    assert "Overall Length" not in evolution.ambiguous_labels
    assert evolution.mh_length_mm == 9448


def test_the_berth_claim_is_read_and_never_recorded(evolution: RSProduct) -> None:
    """RS say 'up to 8 people' here, 'up to 6' in the documents and 'up to 7' on the index,
    for the same vehicles. Under the lower-figure rule all four would be 2 against FMLV's
    4, and the requester kept that decision on 9 November 2026."""
    assert evolution.capacity_claim == "Comfortably accommodates up to 8 people"

    built = rs_motorhomes._build_extracted_motorhome(evolution)
    assert built.motorhome.berths is None
    assert "berths" not in built.provenance


# --------------------------------------------------------------------------- #
# What is dropped, and what is only reported
# --------------------------------------------------------------------------- #


def test_a_document_that_yielded_no_dimension_is_dropped() -> None:
    """There is no arithmetic to fail, so the shape test is what stands in for one."""
    blank = RSProduct(model="Endeavour", source_url="x", base_vehicle="Iveco Daily 72-210")
    reconciles, why_not = rs_motorhomes._reconciles(blank)

    assert not reconciles
    assert "length, width or height" in why_not


def test_a_document_with_no_base_vehicle_is_dropped(endeavour: RSProduct) -> None:
    reconciles, why_not = rs_motorhomes._reconciles(replace(endeavour, base_vehicle=None))

    assert not reconciles
    assert "base vehicle" in why_not


def test_a_real_document_reconciles(
    endeavour: RSProduct, envoy: RSProduct, evolution: RSProduct
) -> None:
    for product in (endeavour, envoy, evolution):
        assert rs_motorhomes._reconciles(product)[0], product.model


def test_the_train_weight_check_notices_the_automatics_figure(endeavour: RSProduct) -> None:
    """10,500 − 7,200 = 3,300, and RS state 3,500kg — because the train weight is the
    Hi-Matic's, whose towing capacity they give as 3,300kg in the same row."""
    notes = rs_motorhomes._discrepancies(endeavour)

    assert any("3,300kg" in note and "3,500kg" in note for note in notes)


# --------------------------------------------------------------------------- #
# The built product
# --------------------------------------------------------------------------- #


def test_the_built_endeavour_carries_the_right_columns(endeavour: RSProduct) -> None:
    built = rs_motorhomes._build_extracted_motorhome(endeavour)
    motorhome = built.motorhome

    assert motorhome.manufacturer == rs_motorhomes.MANUFACTURER == "RS Motorhomes"
    assert motorhome.manufacturer_range == "RS"
    assert motorhome.model == "Endeavour"
    assert motorhome.base_vehicle_manufacturer == "IVECO"
    assert motorhome.mtplm_kilograms == 7200
    assert motorhome.rrp_pounds == 299995
    assert motorhome.automatic_available is True


def test_the_envoys_chassis_is_spelled_fmlvs_way(envoy: RSProduct) -> None:
    """`DAF XB – 16000KG` names the make and then the chassis; FMLV holds the make."""
    built = rs_motorhomes._build_extracted_motorhome(envoy)

    assert built.motorhome.base_vehicle_manufacturer == "DAF"


def test_an_unpublished_field_gets_no_provenance_and_so_no_proposal(
    endeavour: RSProduct,
) -> None:
    """A field with no provenance entry is never proposed, which leaves FMLV's own figures
    alone rather than blanking them — see `diff.compare`."""
    built = rs_motorhomes._build_extracted_motorhome(endeavour)

    assert built.motorhome.mro_kilograms is None
    assert built.motorhome.mh_payload_kilograms is None
    for never_proposed in ("mro_kilograms", "mh_payload_kilograms", "berths", "body_type"):
        assert never_proposed not in built.provenance


def test_the_habitation_findings_are_recorded_from_the_first_run(
    endeavour: RSProduct, evolution: RSProduct
) -> None:
    """A new adapter reports them from the start — `docs/adapters/README.md`. They are
    findings, never proposals, so nothing accepts or rejects them.
    """
    for product in (endeavour, evolution):
        built = rs_motorhomes._build_extracted_motorhome(product)
        assert built.motorhome.heating is Heating.WET_CENTRAL, product.model
        assert built.motorhome.refrigeration is Refrigeration.FRIDGE_FREEZER, product.model
        assert built.motorhome.microwave is True, product.model


def test_the_heating_is_wet_central_because_the_plumbing_says_so(endeavour: RSProduct) -> None:
    """Every model has a 'Full Alde ... water radiator heating system throughout'. It is
    diesel-fired, and the fuel is not what decides the column — the radiators are. FMLV
    currently records blown air on all four."""
    assert "water radiator" in _text(ENDEAVOUR_SPEC)

    built = rs_motorhomes._build_extracted_motorhome(endeavour)
    assert built.motorhome.heating is Heating.WET_CENTRAL


def test_an_automatic_offered_as_an_option_is_still_a_yes(endeavour: RSProduct) -> None:
    """The Endeavour's standard gearbox is a 6-speed manual; the Hi-Matic is named only in
    the towing row. Cited at all, even as an option, is a Yes."""
    assert "6-speed manual" in _text(ENDEAVOUR_SPEC)

    built = rs_motorhomes._build_extracted_motorhome(endeavour)
    assert built.motorhome.automatic_available is True
    assert "Hi-Matic" in built.provenance["automatic_available"].snippet


def test_every_provenance_snippet_names_the_product(endeavour: RSProduct) -> None:
    built = rs_motorhomes._build_extracted_motorhome(endeavour)

    assert built.provenance
    for field_name, provenance in built.provenance.items():
        assert provenance.snippet.startswith("RS Endeavour"), field_name
        assert provenance.source_url == endeavour.source_url


# --------------------------------------------------------------------------- #
# Wiring
# --------------------------------------------------------------------------- #


def test_the_single_range_is_how_fmlv_files_all_four() -> None:
    assert rs_motorhomes.DEFAULT_RANGES == (("rs", "RS"),)
    assert rs_motorhomes.FMLV_RANGE == "RS"


def test_the_dealerships_used_stock_is_never_a_source() -> None:
    """`/listings/` and `/preowned-motorhomes/` hold Bailey, Carado, Dethleffs and Swift
    vehicles beside used RS ones, and a used listing is one unit's plate."""
    source = Path(rs_motorhomes.__file__).read_text(encoding="utf-8")
    for path in ("/listings/", "/preowned-motorhomes/", "/inventory/"):
        assert f'"{rs_motorhomes.BASE_URL}{path}"' not in source
