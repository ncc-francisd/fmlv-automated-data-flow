"""Eriba's touring-caravan adapter — the third caravan brand, and the first built on a
columnar price list rather than on per-layout pages.

Fixtures were saved from the live source on 7 September 2026. The PDF itself is never
committed, per `docs/adapters/README.md`; what is kept is the extracted text of the pages
that matter:

* **`..._touring_p5.txt`** — the clean four-model spread. Every row carries one value per
  model, so this is the base case.
* **`..._touring_p6.txt`** — *the page that broke the parser on its first live run.* Five
  models, and a `Heating type` row printing **two** values. That is the blank-cell trap in
  the wild, and the cardinality check is what caught it.
* **`..._feeling_novaline_p16.txt`** — two ranges on one spread, plus a
  `Bed dimension: Sleeping roof` row with three values against four models.
* **`..._front_and_notes.txt`** — page 1's title with page 24's boilerplate, which claims
  euros ex works in a sterling UK document. The currency check has to ignore it.

The two range pages are trimmed the way Bailey's and Swift's were — scripts, styles,
comments and responsive-image `srcset`s dropped, whitespace between tags collapsed. The
Touring page is kept **whole**, because its emptiness is the point: a truncated fixture
would return no layouts whatever the parser did.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from src.adapters import ADAPTERS, adapter_for, adapters_for, eriba_caravan
from src.product_model.enums import (
    BedType,
    CaravanBodyType,
    CaravanSleepingArea,
    Heating,
    Refrigeration,
)
from src.vehicle_class import VehicleClass

FIXTURES_DIR = Path(__file__).parent / "fixtures"

TOURING_P5 = "eriba_pricelist_touring_p5.txt"
TOURING_P6 = "eriba_pricelist_touring_p6.txt"
FEELING_NOVALINE_P16 = "eriba_pricelist_feeling_novaline_p16.txt"
FRONT_AND_NOTES = "eriba_pricelist_front_and_notes.txt"
BROCHURES = "eriba_brochures.html"
RANGE_FEELING = "eriba_range_feeling.html"
RANGE_TOURING = "eriba_range_touring.html"
CONFIGURATOR_MODELS = "eriba_configurator_touring_models.json"


def fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def layouts(name: str) -> dict[str, eriba_caravan.EribaCaravan]:
    """Every layout on one spec page, keyed `"<Range> <model>"`."""
    parsed, _problems = eriba_caravan.parse_spec_page(fixture(name))
    return {
        f"{range_name} {model}": eriba_caravan.EribaCaravan.from_rows(range_name, model, rows)
        for range_name, model, rows in parsed
    }


# --------------------------------------------------------------------------- #
# Registration — three edits in `adapters/__init__.py`, all of which fail silently
# --------------------------------------------------------------------------- #


def test_this_adapter_is_registered_for_caravans_and_the_other_for_motorhomes() -> None:
    """Miss a wiring edit and `adapter_for` returns `None`, which reads as "nobody has
    written one yet" — Eriba would simply never appear in the trigger dropdown.

    Eriba builds both areas, so there are **two modules and not one with a flag**: this
    one for the 18 caravans and `eriba` for the two ERIBA Car campervans, added
    9 September 2026. They share a manufacturer id and a `MANUFACTURER` string and are
    keyed apart by `VehicleClass`, the same arrangement as the Bailey pair.
    """
    from src.adapters import eriba

    assert adapter_for("Eriba", VehicleClass.CARAVAN) is eriba_caravan
    assert adapter_for("Eriba", VehicleClass.MOTORHOME) is eriba
    assert adapters_for("Eriba") == {
        VehicleClass.CARAVAN: eriba_caravan,
        VehicleClass.MOTORHOME: eriba,
    }
    assert ADAPTERS[("Eriba", VehicleClass.CARAVAN)] is eriba_caravan
    assert eriba.MANUFACTURER == eriba_caravan.MANUFACTURER


def test_the_range_labels_are_the_fmlv_range_names() -> None:
    """`cli.baseline_scope` matches a `--range` label against `manufacturer_range`, and
    these coincide — confirmed against the export — so no `baseline_in_scope` hook is
    needed. A label that drifted from FMLV's spelling would scope a run to zero baseline
    rows and propose every layout as new."""
    assert [label for _slug, label in eriba_caravan.DEFAULT_RANGES] == [
        "Touring",
        "Feeling",
        "Novaline",
    ]
    assert not hasattr(eriba_caravan, "baseline_in_scope")


# --------------------------------------------------------------------------- #
# Finding the document
# --------------------------------------------------------------------------- #


def test_it_finds_the_caravan_price_list_and_not_its_two_neighbours() -> None:
    """The brochures page offers three PDFs. Picking the campervan list would collect the
    Eriba Car, which is a different product area entirely."""
    url = eriba_caravan.find_price_list_url(fixture(BROCHURES))

    assert url == (
        "https://www.eriba.com/eriba/drucksachen/preislisten/caravans/eriba-caravans-gb_en.pdf"
    )
    assert "campervans" not in (url or "")
    assert "eriba-op" not in (url or "")


def test_a_missing_price_list_card_is_none_rather_than_an_exception() -> None:
    """A site reshuffle should be a narratable skip, not a crash."""
    assert eriba_caravan.find_price_list_url("<html><body>nothing here</body></html>") is None


def test_the_documents_own_euro_boilerplate_does_not_condemn_it() -> None:
    """Page 24 says *"recommended retail prices in Euro … ex works"* in a document titled
    `Price list for UK and IRL` whose every figure carries a pound sign. Asserting on that
    footnote would refuse a perfectly good sterling price list every single run."""
    text = fixture(FRONT_AND_NOTES)

    assert "in Euro" in text, "the fixture must still contain the misleading boilerplate"
    assert eriba_caravan.price_list_currency_problem(text) is None


def test_a_document_actually_quoting_euros_is_refused() -> None:
    """The Weinsberg lesson: verify the currency in the document, not the label on the
    card. A euro figure must never reach `rrp_pounds`."""
    problem = eriba_caravan.price_list_currency_problem(
        "ERIBA CARAVANS 2027 Price list for UK and IRL\nPrice £ 25,170.-\nList price in EUR"
    )

    assert problem is not None
    assert "EUR" in problem


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Price list for UK and IRL with no currency at all", "no pound sign"),
        ("Preisliste Deutschland\nPrice £ 25,170.-", "does not describe itself"),
    ],
)
def test_a_document_that_is_not_the_uk_sterling_edition_is_refused(
    text: str, expected: str
) -> None:
    problem = eriba_caravan.price_list_currency_problem(text)

    assert problem is not None
    assert expected in problem


# --------------------------------------------------------------------------- #
# The columnar spread
# --------------------------------------------------------------------------- #


def test_a_four_model_spread_gives_every_layout_its_own_figures() -> None:
    """The whole risk in this document is attribution: the four columns must not swap.
    These are the printed figures for the four Touring layouts on page 5."""
    found = layouts(TOURING_P5)

    assert list(found) == ["Touring 310", "Touring 420", "Touring 430", "Touring 530"]
    assert [c.rrp_pounds for c in found.values()] == [25170, 27390, 27390, 28280]
    assert [c.mtplm_kilograms for c in found.values()] == [1000, 1100, 1100, 1300]
    assert [c.mro_kilograms for c in found.values()] == [820, 940, 930, 1010]
    assert [c.berths for c in found.values()] == [3, 2, 3, 3]


def test_the_three_lengths_are_not_interchanged() -> None:
    """`docs/adapters/README.md` calls swapping shipping and exterior body length "the most
    plausible single mistake available". Eriba label all three separately, and shipping must
    be the largest because it alone includes the drawbar."""
    touring_310 = layouts(TOURING_P5)["Touring 310"]

    assert touring_310.shipping_length_mm == 5060
    assert touring_310.exterior_body_length_mm == 3710
    assert touring_310.internal_length_mm == 3660
    assert touring_310.awning_length_mm == 6350
    assert touring_310.shipping_length_mm > touring_310.exterior_body_length_mm
    # The awning rail is not a vehicle dimension and routinely exceeds the body.
    assert touring_310.awning_length_mm > touring_310.exterior_body_length_mm


def test_centimetres_become_millimetres() -> None:
    """Every dimension in this document is in centimetres. A missed factor of ten would
    put a 5-metre caravan through `validation`'s 4000mm plausibility floor."""
    touring_310 = layouts(TOURING_P5)["Touring 310"]

    assert touring_310.overall_width_mm == 2000
    assert touring_310.height_mm == 2270
    assert touring_310.headroom_mm == 1950


def test_a_five_model_spread_survives_a_row_that_is_short() -> None:
    """Page 6 broke the first live run. Its `Heating type` row prints two values against
    five models, so which layouts they belong to cannot be recovered — but every row FMLV
    needs is complete, and dropping the short row must not cost the page its layouts."""
    found = layouts(TOURING_P6)

    assert list(found) == [
        "Touring 540",
        "Touring 542",
        "Touring 620",
        "Touring 630",
        "Touring 642",
    ]
    assert [c.mro_kilograms for c in found.values()] == [1003, 1020, 1290, 1215, 1230]
    assert [c.rrp_pounds for c in found.values()] == [28990, 28990, 33600, 33600, 33600]


def test_every_row_the_adapter_needs_is_complete_on_all_three_spreads() -> None:
    """The corollary of the test above: once the two blankable rows are excluded, nothing
    the adapter reads is ever short. A problem appearing here means a row has started
    blanking and its field can no longer be attributed to a column."""
    for name in (TOURING_P5, TOURING_P6, FEELING_NOVALINE_P16):
        _parsed, problems = eriba_caravan.parse_spec_page(fixture(name))
        assert problems == [], f"{name}: {problems}"


def test_a_row_with_the_wrong_number_of_values_is_dropped_and_reported() -> None:
    """The alignment defence, on the shape that actually occurred: page 6's `Heating type`
    printed two values against five models. Heating is no longer parsed, so this exercises
    the same failure on a row that is — a price row one value short must be dropped, never
    stretched to fit, because a partly-aligned row is worse than a missing one."""
    short = (
        "PRICES AND TECHNICAL DATA ERIBA TOURING\n"
        "Touring 310 Touring 420 Touring 430 Touring 530\n"
        "Price £ 25,170.- 27,390.- 28,280.-\n"
        "Axle Mono Mono Mono Mono\n"
        "Standard equipment\n"
    )

    parsed, problems = eriba_caravan.parse_spec_page(short)

    assert any("price" in note and "3 value(s) for 4 model(s)" in note for note in problems)
    # The page keeps its layouts and its good rows; only the ambiguous row is lost.
    assert [model for _range, model, _rows in parsed] == ["310", "420", "430", "530"]
    assert all("price" not in rows for _range, _model, rows in parsed)
    assert all(rows["axle"] == "Mono" for _range, _model, rows in parsed)


def test_bed_dimension_rows_are_never_parsed() -> None:
    """Page 16's `Bed dimension: Sleeping roof` row has three values for four models,
    because the Novaline has no such roof — and **which** model is missing cannot be
    recovered from the line. Rimor's "present and unattributable" in miniature, so these
    rows are boundaries only and no bed field is emitted from them."""
    assert "Bed dimension: Sleeping roof, L x W (cm)" in eriba_caravan.SPEC_LABELS
    assert not any("bed dimension" in key for key in eriba_caravan._VALUE_PATTERNS)


def test_heating_is_a_boundary_label_and_not_a_parsed_field() -> None:
    """Two independent reasons, either of which is sufficient — see the module docstring."""
    assert "Heating type" in eriba_caravan.SPEC_LABELS
    assert "heating type" not in eriba_caravan._VALUE_PATTERNS


def test_two_ranges_on_one_spread_are_split_by_their_own_headings() -> None:
    """Page 16 runs three Feeling layouts into a Novaline. Taking the range from the page
    heading rather than each column would file the Novaline 442 under Feeling."""
    found = layouts(FEELING_NOVALINE_P16)

    assert list(found) == ["Feeling 425", "Feeling 442", "Feeling 470", "Novaline 442"]
    assert found["Novaline 442"].manufacturer_range == "Novaline"
    assert found["Novaline 442"].model == "442"


def test_the_lower_berth_figure_is_recorded_and_the_published_range_is_kept() -> None:
    """The standard rule: the higher figure needs options. FMLV's own baseline agrees on
    all 18, and the published wording travels into the provenance so a reviewer sees it."""
    feeling_425 = layouts(FEELING_NOVALINE_P16)["Feeling 425"]

    assert feeling_425.berths_published == "3 - 5"
    assert feeling_425.berths == 3


def test_a_wrapped_label_does_not_swallow_its_own_values() -> None:
    """`Manufacturer-specified mass for optional equipment` wraps, with `(kg)*` and then
    the values on the next line. Reading to the next known label is what handles it."""
    found = layouts(TOURING_P5)

    assert [c.optional_equipment_allowance_kg for c in found.values()] == [92, 57, 77, 197]


def test_a_page_with_no_layout_header_yields_nothing_rather_than_guessing() -> None:
    parsed, problems = eriba_caravan.parse_spec_page(
        "PRICES AND TECHNICAL DATA ERIBA TOURING\nPrice £ 25,170.-\n"
    )

    assert parsed == []
    assert problems == ["no layout header found on the page"]


def test_prose_naming_a_layout_is_not_mistaken_for_a_header() -> None:
    """Page 10's packages table contains `Comfort package Touring 310`. Only a line that is
    *entirely* layout names is a header."""
    assert eriba_caravan._model_header("Package Comfort package Touring 310 Comfort") is None
    assert eriba_caravan._model_header("LAYOUT 430 530 542 630 642") is None
    assert eriba_caravan._model_header("Touring 310 Touring 420") == [
        ("Touring", "310"),
        ("Touring", "420"),
    ]


# --------------------------------------------------------------------------- #
# The self-check
# --------------------------------------------------------------------------- #


def test_every_layout_reconciles_against_its_printed_tolerance_band() -> None:
    """The mass in running order is printed with its legal ±5% range, so the band is a
    *function* of the mass and a slipped column pairs one layout's mass with another's."""
    for name in (TOURING_P5, TOURING_P6, FEELING_NOVALINE_P16):
        for label, caravan in layouts(name).items():
            keep, reason = caravan.reconciles()
            assert keep, f"{label}: {reason}"
            assert caravan.band_reconciles is True


def test_a_mass_paired_with_another_layouts_band_is_dropped() -> None:
    """The failure the check exists for. 820kg bands to 779-861; handed 1010's band it must
    refuse, because that is what a misaligned column looks like."""
    misaligned = eriba_caravan.EribaCaravan(
        manufacturer_range="Touring", model="310", mro_kilograms=820, mass_band=(960, 1061)
    )

    keep, reason = misaligned.reconciles()

    assert keep is False
    assert "misaligned" in reason


def test_the_printed_rounding_is_tolerated() -> None:
    """930 × 1.05 is 976.5, printed as 977. A check that demanded exactness would drop
    real layouts every run."""
    rounded = eriba_caravan.EribaCaravan(
        manufacturer_range="Touring", model="430", mro_kilograms=930, mass_band=(884, 977)
    )

    assert rounded.band_reconciles is True


def test_an_unladen_weight_above_the_running_mass_is_dropped() -> None:
    """The second, free alignment check: the mass before gas and water must be the lower
    of the two, whichever range it is."""
    swapped = eriba_caravan.EribaCaravan(
        manufacturer_range="Touring",
        model="310",
        mro_kilograms=820,
        mass_band=(779, 861),
        unladen_kilograms=940,
    )

    keep, reason = swapped.reconciles()

    assert keep is False
    assert "unladen" in reason


def test_a_layout_with_no_band_is_kept_and_said_to_be_unchecked() -> None:
    """"Could not check" is not "failed" — only a contradiction drops a product."""
    unknown = eriba_caravan.EribaCaravan(
        manufacturer_range="Touring", model="310", mro_kilograms=820
    )

    keep, reason = unknown.reconciles()

    assert keep is True
    assert unknown.band_reconciles is None
    assert "cannot be checked" in reason


# --------------------------------------------------------------------------- #
# Payload
# --------------------------------------------------------------------------- #


def test_the_whole_payload_goes_to_personal_effects() -> None:
    """`MTPLM - MRO`, as Bailey and Swift do. Eriba's optional-equipment figure is a
    ceiling on what may be ordered, not weight the caravan carries."""
    touring_310 = layouts(TOURING_P5)["Touring 310"]

    assert touring_310.derived_payload_kilograms == 180
    assert touring_310.optional_equipment_allowance_kg == 92
    assert touring_310.minimum_payload_kilograms == 88


def test_the_optional_equipment_column_is_asked_to_be_cleared_not_filled() -> None:
    """FMLV holds the whole payload in this column on all 18 Eriba rows, with the REQUIRED
    personal-effects column blank. Recording provenance with no value turns that into a
    confirm-or-clear rather than a silent blanking."""
    extracted = eriba_caravan.build_extracted(
        layouts(TOURING_P5)["Touring 310"], "https://example.test/pricelist.pdf"
    )

    assert extracted.caravan.personal_effects_payload_kilograms == 180
    assert extracted.caravan.optional_equipment_payload_kilograms is None
    assert "optional_equipment_payload_kilograms" in extracted.provenance
    assert "Leave this blank" in (
        extracted.provenance["optional_equipment_payload_kilograms"].snippet
    )


# --------------------------------------------------------------------------- #
# Body type
# --------------------------------------------------------------------------- #


def test_a_pop_up_roof_is_still_a_rigid_caravan() -> None:
    """The NCC rule of 7 September 2026, and the reason this adapter corrects FMLV on
    fifteen products. Eriba's own row says `Pop-up roof`; the body type does not follow it,
    because `type_pop_up` describes a folding caravan and not a roof."""
    touring_310 = layouts(TOURING_P5)["Touring 310"]
    assert touring_310.roof_type == "Pop-up roof"

    extracted = eriba_caravan.build_extracted(touring_310, "https://example.test/p.pdf")

    assert extracted.caravan.body_type is CaravanBodyType.RIGID
    snippet = extracted.provenance["body_type"].snippet
    assert "Pop-up roof" in snippet, "the reviewer must see the wording being overridden"
    assert "deliberate" in snippet


def test_every_roof_type_gives_the_same_body_type() -> None:
    """Three roof types across the range — `Pop-up roof`, `Sleeping roof`, `Fix roof` — and
    one body type. A 1000kg Touring 310 is not a micro either: Eriba never use the word."""
    everything = {**layouts(TOURING_P5), **layouts(TOURING_P6), **layouts(FEELING_NOVALINE_P16)}
    roofs = {c.roof_type for c in everything.values()}

    assert roofs == {"Pop-up roof", "Sleeping roof", "Fix roof"}
    for caravan in everything.values():
        built = eriba_caravan.build_extracted(caravan, "https://example.test/p.pdf")
        assert built.caravan.body_type is CaravanBodyType.RIGID


# --------------------------------------------------------------------------- #
# The website: cross-check and floorplans
# --------------------------------------------------------------------------- #


def test_the_range_page_layouts_parse_with_their_floorplans() -> None:
    """Each layout's block is rendered twice, once per button wrapper, so the rows must
    collapse rather than duplicating."""
    found = eriba_caravan.parse_range_page(fixture(RANGE_FEELING))

    assert [name for name, _rows, _plan in found] == [
        "Feeling 425",
        "Feeling 442",
        "Feeling 470",
    ]
    for _name, _rows, plan in found:
        assert plan is not None
        assert plan.startswith("https://www.eriba.com/")
        assert plan.endswith("_hoch.svg")


def test_the_touring_range_page_publishes_nothing_to_cross_check() -> None:
    """Not a parse failure — the page genuinely carries no slider and no spec table, on
    `/gb/en` and on the international site alike. The fixture is the whole page, so this
    asserts something about Eriba rather than about where a truncation fell."""
    html = fixture(RANGE_TOURING)

    assert "The ERIBA Touring" in html, "the fixture must be the real page"
    assert "Pop-top roof" in html, "which markets the very roof it publishes no data for"
    assert eriba_caravan.parse_range_page(html) == []


def test_the_website_and_the_price_list_agree_on_every_shared_field() -> None:
    """The evidence that the columnar split is aligned. Two independently rendered sources,
    nine layouts, and no disagreement — which is what lets the same parser be trusted on the
    nine Touring layouts nothing can check."""
    from_site = {
        name: eriba_caravan.EribaCaravan.from_rows(*name.split(), rows)
        for name, rows, _plan in eriba_caravan.parse_range_page(fixture(RANGE_FEELING))
    }
    from_pdf = layouts(FEELING_NOVALINE_P16)

    for name, site_caravan in from_site.items():
        agreed, disagreements = eriba_caravan.cross_check(from_pdf[name], site_caravan)
        assert disagreements == []
        assert agreed >= 10, f"{name} compared only {agreed} fields"


def test_the_standard_equipment_marker_is_not_a_disagreement() -> None:
    """The website appends `(○)` to some values and the price list does not. Six of the
    nine layouts would otherwise report a false disagreement on roof type and berths."""
    found = eriba_caravan.parse_range_page(fixture(RANGE_FEELING))
    _name, rows, _plan = found[0]

    assert rows["roof type"] == "Sleeping roof"
    assert rows["berths"] == "3 - 5"


def test_a_real_disagreement_is_reported() -> None:
    """The cross-check has to be able to fail, or it is not a check."""
    from_pdf = eriba_caravan.EribaCaravan("Feeling", "425", mtplm_kilograms=1200)
    from_site = eriba_caravan.EribaCaravan("Feeling", "425", mtplm_kilograms=1250)

    agreed, disagreements = eriba_caravan.cross_check(from_pdf, from_site)

    assert agreed == 0
    assert disagreements == ["mtplm_kilograms: price list says 1200, the range page says 1250"]


def test_the_floorplan_is_a_reviewer_pointer_on_the_positional_fields() -> None:
    """An adapter that cannot know a positional field can still say where to look, and the
    pointer must survive onto a new product — which is what `reviewer_reference` is for."""
    extracted = eriba_caravan.build_extracted(
        layouts(FEELING_NOVALINE_P16)["Feeling 425"],
        "https://example.test/p.pdf",
        floorplan_url="https://example.test/eriba_feeling_425_hoch.svg",
    )

    for name in eriba_caravan.FLOORPLAN_FIELDS:
        assert extracted.provenance[name].reviewer_reference is True
        assert extracted.provenance[name].source_url.endswith("_hoch.svg")
        # `bathroom_layout` is a list, so its unanswered state is `[]`.
        assert getattr(extracted.caravan, name) in (None, [])


def test_a_touring_layout_gets_no_positional_pointer_at_all() -> None:
    """There is no Touring drawing anywhere on the site — all nine predicted URLs 404 — so
    the pointer is absent rather than pointing somewhere useless."""
    extracted = eriba_caravan.build_extracted(
        layouts(TOURING_P5)["Touring 310"], "https://example.test/p.pdf"
    )

    for name in eriba_caravan.FLOORPLAN_FIELDS:
        assert name not in extracted.provenance


# --------------------------------------------------------------------------- #
# The built product
# --------------------------------------------------------------------------- #


def test_every_field_carries_provenance_naming_the_layout() -> None:
    """A value with no provenance is neither compared against the baseline nor proposed on
    a new product — it fails in the way that is hardest to notice."""
    extracted = eriba_caravan.build_extracted(
        layouts(TOURING_P5)["Touring 310"], "https://example.test/p.pdf"
    )

    # `bed_types` defaults to an empty list rather than None, and is deliberately never set
    # here — Eriba publish bed dimensions only in rows that may blank, so they are unread.
    assert extracted.caravan.bed_types == []
    valued = {
        name
        for name, value in vars(extracted.caravan).items()
        if value is not None
        and value != []
        and name not in {"images", "extra_column_flags", "archived"}
    }
    for name in valued - {"manufacturer", "manufacturer_display_name", "twin_axle"}:
        assert name in extracted.provenance, f"{name} is set but unregistered"
    for provenance in extracted.provenance.values():
        assert provenance.snippet.startswith("Touring 310 — ")


def test_both_halves_of_the_identity_are_recorded_together() -> None:
    """Accepting a range change without its model corrupts the name — Bailey's `Adamo I`."""
    extracted = eriba_caravan.build_extracted(
        layouts(TOURING_P5)["Touring 310"], "https://example.test/p.pdf"
    )

    assert extracted.caravan.manufacturer_range == "Touring"
    assert extracted.caravan.model == "310"
    for name in ("manufacturer_range", "model"):
        assert "they are one name" in extracted.provenance[name].snippet


def test_the_freezer_is_read_from_eribas_own_wording() -> None:
    """`Refrigerator volume incl. freezer (l): 81 (10)` settles it in words, which is what
    the provenance has to quote — FMLV holds seven of these as a plain fridge."""
    extracted = eriba_caravan.build_extracted(
        layouts(TOURING_P5)["Touring 310"], "https://example.test/p.pdf"
    )

    assert extracted.caravan.refrigeration is Refrigeration.FRIDGE_FREEZER
    assert "incl. freezer" in extracted.provenance["refrigeration"].snippet


def test_the_price_provenance_states_the_basis() -> None:
    """A manufacturer changing basis between runs otherwise reads as a range-wide price
    move. Eriba's is on-the-road including VAT, from their own published wording."""
    extracted = eriba_caravan.build_extracted(
        layouts(TOURING_P5)["Touring 310"], "https://example.test/p.pdf"
    )

    snippet = extracted.provenance["rrp_pounds"].snippet
    assert "£25,170" in snippet
    assert "On The Road" in snippet


def test_all_eighteen_are_single_axle() -> None:
    everything = {**layouts(TOURING_P5), **layouts(TOURING_P6), **layouts(FEELING_NOVALINE_P16)}

    assert not any(c.twin_axle for c in everything.values())
    assert {c.axle_evidence for c in everything.values()} == {"Mono"}


def test_the_three_spec_pages_hold_thirteen_of_the_eighteen_layouts() -> None:
    """The manufacturer's own roster is 18 across three ranges; these fixtures are three of
    the four spreads. A count that drifts means a row stopped parsing."""
    everything = {**layouts(TOURING_P5), **layouts(TOURING_P6), **layouts(FEELING_NOVALINE_P16)}

    assert len(everything) == 13
    assert sum(1 for name in everything if name.startswith("Touring")) == 9


# --------------------------------------------------------------------------- #
# The configurator API — bed types, the sleeping area, and a drawing for all 18
# --------------------------------------------------------------------------- #


def configurator_layouts() -> dict[str, eriba_caravan.ConfiguratorLayout]:
    """Every layout in the saved Touring API response, keyed by its marketing name."""
    parsed = eriba_caravan.parse_configurator_models(fixture(CONFIGURATOR_MODELS), "touring")
    return {layout.label: layout for layout in parsed}


def configurator_page(series_id: object) -> str:
    """The one thing the adapter reads off the configurator page: its base64 config."""
    blob = base64.b64encode(
        json.dumps({"seriesName": "ERIBA Touring", "seriesId": series_id}).encode()
    ).decode()
    return f"""<div id="configurator" data-config='{blob}'></div>"""


def test_the_series_id_is_read_from_the_page_not_hardcoded() -> None:
    """A range Eriba renumbers must not silently serve another range's layouts."""
    assert eriba_caravan.parse_configurator_series_id(configurator_page(4125120)) == 4125120


@pytest.mark.parametrize(
    "html",
    [
        "<div id='configurator'></div>",
        """<div data-config='not base64 at all'></div>""",
        # A string id is not one to trust into a URL path.
        None,
    ],
)
def test_an_unreadable_config_gives_no_series_id(html: str | None) -> None:
    page = configurator_page("4125120") if html is None else html
    assert eriba_caravan.parse_configurator_series_id(page) is None


def test_the_configurator_names_each_bed_and_which_end_it_is_at() -> None:
    """The two fields the price list cannot express, stated rather than inferred.

    Eriba print bed *dimensions* — "Bed dimension: Rear bed, L x W (cm) 188 x 140" — which
    say nothing about the type. `technicalDataBed` says both type and end.
    """
    found = configurator_layouts()

    front_and_rear = found["Touring 310"]
    assert front_and_rear.bed_types == (BedType.FIXED, BedType.MAKE_UP)
    assert front_and_rear.sleeping_area is CaravanSleepingArea.BOTH

    rear_only = found["Touring 420"]
    assert rear_only.bed_types == (BedType.MAKE_UP,)
    assert rear_only.sleeping_area is CaravanSleepingArea.REAR


def test_an_optional_pop_top_bed_is_not_a_bed_the_buyer_has() -> None:
    """Touring 620 lists a pop-top double as an option; counting it would say `both`.

    The standing rule, and here the source states it outright rather than leaving it to a
    price in the prose: `isOptional` is `yes`.
    """
    layout = configurator_layouts()["Touring 620"]

    assert layout.bed_types == (BedType.FIXED_SEPARATE,)
    assert layout.sleeping_area is CaravanSleepingArea.REAR
    assert "pop-top" not in layout.bed_evidence


def test_every_layout_gets_a_per_layout_deep_link_and_a_drawing() -> None:
    """The finding that prompted this: Touring layouts do have a plan, and their own URL.

    The range pages carry an SVG for nine of the eighteen and none for Touring, which is
    why the survey concluded no Touring drawing was reachable anywhere. The configurator
    has one for every layout, and `?selectedModelId=` addresses each on its own.
    """
    for layout in configurator_layouts().values():
        assert layout.url == (
            f"https://www.eriba.com/gb/en/configurator/touring"
            f"?selectedModelId={layout.model_id}"
        )
        assert layout.floorplan_url is not None
        assert layout.floorplan_url.startswith("https://www.eriba.com/")


def test_the_configurator_republishes_the_berths_and_both_masses() -> None:
    """A third independent source for the figures, so `collect` can cross-check them."""
    layout = configurator_layouts()["Touring 310"]

    assert (layout.berths, layout.mtplm_kilograms, layout.mro_kilograms) == (3, 1000, 820)


@pytest.mark.parametrize("payload", ["", "not json", "{}", "[]", '[{"id": 1}]'])
def test_an_unusable_api_response_yields_no_layouts(payload: str) -> None:
    """Narrated and skipped by `collect`: this source supplements, it is never load-bearing."""
    assert eriba_caravan.parse_configurator_models(payload, "touring") == []


def test_the_configurator_agrees_with_the_price_list_on_every_saved_layout() -> None:
    """The cross-check that makes the rest of it trustworthy.

    Two documents published independently — a sterling PDF price list and a JSON API — and
    they agree on the berth count and both masses. That also corroborates the *positional*
    reading of the price list's columnar spread, which is the fragile part of this adapter.
    """
    from_price_list = layouts(TOURING_P5)
    from_api = configurator_layouts()

    compared = 0
    for label, layout in from_api.items():
        product = from_price_list.get(label)
        if product is None:
            continue
        compared += 1
        assert product.berths == layout.berths, label
        assert product.mtplm_kilograms == layout.mtplm_kilograms, label
        assert product.mro_kilograms == layout.mro_kilograms, label
    assert compared >= 2


def test_a_configurator_layout_answers_the_fields_and_stops_pointing_at_the_plan() -> None:
    """An answered field loses its floorplan pointer — there is nothing left to look up.

    The other positional fields keep theirs: the configurator settles where the *beds*
    are and says nothing about the kitchen, the lounge or the washroom.
    """
    product = layouts(TOURING_P5)["Touring 310"]
    layout = configurator_layouts()[product.label]

    extracted = eriba_caravan.build_extracted(
        product, "https://example.invalid/price-list.pdf", configurator=layout
    )

    assert extracted.caravan.bed_types == [BedType.FIXED, BedType.MAKE_UP]
    assert extracted.caravan.sleeping_area is CaravanSleepingArea.BOTH
    # Read, not referred: these carry a value and the record that states it.
    for name in ("bed_types", "sleeping_area"):
        assert extracted.provenance[name].reviewer_reference is False
        assert "selectedModelId" in extracted.provenance[name].source_url
    # Still nobody's call but a reviewer's — now with a drawing to read them off.
    for name in ("kitchen_location", "lounge_location", "bathroom_layout"):
        assert extracted.provenance[name].reviewer_reference is True
        assert extracted.provenance[name].source_url == layout.floorplan_url


def test_without_the_configurator_nothing_regresses() -> None:
    """The API is supplementary, so losing it costs the two fields and nothing else."""
    product = layouts(TOURING_P5)["Touring 310"]

    extracted = eriba_caravan.build_extracted(
        product, "https://example.invalid/price-list.pdf"
    )

    assert extracted.caravan.bed_types == []
    assert extracted.caravan.sleeping_area is None
    assert extracted.caravan.mtplm_kilograms == 1000
    assert "bed_types" not in extracted.provenance


# --------------------------------------------------------------------------- #
# Heating — one system per page, because one system is all the document has
# --------------------------------------------------------------------------- #


def test_heating_is_read_from_the_clean_page() -> None:
    """Four models, four identical cells, nothing to attribute."""
    found = eriba_caravan.heating_from_spec_page(fixture(TOURING_P5))

    assert found is not None
    assert found[0] is Heating.BLOWN_AIR
    assert "Gas heating, 3.5 kW" in found[1]


def test_a_cell_wrapped_over_three_lines_is_still_one_cell() -> None:
    """Page 6, the row that was read as three layouts stating no heating.

    They state a longer value — `Gas heating, integrated boiler, 4 kW` — which pypdf
    returns as `Gas heating,` / `integrated boiler, 4` / `kW`. Reading a line at a time
    saw two cells against five models and gave up. The row ends at the next printed
    label, so `SPEC_LABELS` bounds it rather than a guess at the line shape.
    """
    row = eriba_caravan._heating_row(fixture(TOURING_P6))

    assert row.count("Gas heating") == 5
    assert "integrated boiler, 4 kW" in row
    # The next printed row must not have been swept in with it.
    assert "Gas bottle storage" not in row


def test_both_of_eribas_heaters_are_the_same_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Which is why the row needs no splitting: the two forms differ only in the water.

    The 3.5 kW pairs with a separate `Electric boiler 5 l`; the 4 kW has the boiler inside
    the heater, `Gas boiler 10 l`. Neither is water-borne *space* heating — and Alde, the
    wet-central brand, appears once in the whole document as an example of optional
    equipment.
    """
    del monkeypatch  # only here to keep the signature uniform with the parametrised ones
    for name in (TOURING_P5, TOURING_P6, FEELING_NOVALINE_P16):
        found = eriba_caravan.heating_from_spec_page(fixture(name))
        assert found is not None, name
        assert found[0] is Heating.BLOWN_AIR, name


@pytest.mark.parametrize(
    ("row", "why"),
    [
        ("Heating type Alde wet central heating\nBerths 3 3\n", "a wet system"),
        ("Heating type Gas heating, 3.5 kW Alde 3010\nBerths 3 3\n", "one of each"),
        ("Heating type Diesel heating 4 kW\nBerths 3 3\n", "not the gas one"),
        ("Berths 3 3 3\n", "no such row"),
    ],
)
def test_anything_but_one_gas_system_is_left_to_fmlv(row: str, why: str) -> None:
    """The moment two systems could be on one row, which layout has which matters again.

    And that is exactly what cannot be recovered from a row whose cells wrap, so nothing
    is recorded rather than something guessed.
    """
    assert eriba_caravan.heating_from_spec_page(row) is None, why


def test_a_page_heating_value_reaches_the_product_with_its_reasoning() -> None:
    """A reviewer seeing `blown_air_heating` from "Gas heating" needs the why beside it."""
    product = layouts(TOURING_P5)["Touring 310"]

    extracted = eriba_caravan.build_extracted(
        product,
        "https://example.invalid/price-list.pdf",
        heating=eriba_caravan.heating_from_spec_page(fixture(TOURING_P5)),
    )

    assert extracted.caravan.heating is Heating.BLOWN_AIR
    snippet = extracted.provenance["heating"].snippet
    assert "gas warm air" in snippet
    assert "Alde" in snippet


def test_without_a_readable_row_the_heating_stays_unset() -> None:
    """FMLV's own value stands, and the run says why."""
    product = layouts(TOURING_P5)["Touring 310"]

    extracted = eriba_caravan.build_extracted(
        product, "https://example.invalid/price-list.pdf"
    )

    assert extracted.caravan.heating is None
    assert "heating" not in extracted.provenance


# --------------------------------------------------------------------------- #
# Microwave — the one field asserted from absence, and why that is safe here
# --------------------------------------------------------------------------- #


def test_a_document_that_never_mentions_a_microwave_says_there_is_none() -> None:
    """The one departure from "only assert a feature from positive evidence".

    Safe because this is an itemised equipment table rather than a marketing page: it
    lists the hob, the fridge and the water heater, and Eriba name an oven in the same
    document as optional equipment. The requester, 9 September 2026: *"it should probably
    just recommend no, and [say] we couldn't find any evidence or mention of microwave."*
    """
    note = eriba_caravan.microwave_absence_note(fixture(TOURING_P5))

    assert note is not None
    assert "no microwave anywhere in the price list" in note


@pytest.mark.parametrize(
    "text",
    [
        "Microwave oven fitted above the hob",
        "Combination oven / microwave",
    ],
)
def test_a_microwave_mentioned_as_fitted_stops_the_assertion(text: str) -> None:
    """One that is named needs a human, so the field is left alone rather than set `True`.

    Absence is the only thing this reads. Whether a named microwave is standard is a
    judgement, and getting it wrong in either direction is worse than asking.
    """
    assert eriba_caravan.microwave_absence_note(text) is None


def test_a_priced_microwave_option_still_means_no_microwave() -> None:
    """Because the vehicle *as standard* has none — the standing paid-option rule.

    `habitation.usable_lines` drops a priced line before anything reads it, so this falls
    through to absence, which is the right answer rather than a lucky one.
    """
    note = eriba_caravan.microwave_absence_note("Microwave: £450")

    assert note is not None


def test_the_recommendation_reaches_the_reviewer_with_its_reasoning() -> None:
    """A `No` asserted from silence has to show its working, or it is indistinguishable
    from a `No` nobody checked."""
    product = layouts(TOURING_P5)["Touring 310"]

    extracted = eriba_caravan.build_extracted(
        product,
        "https://example.invalid/price-list.pdf",
        microwave_absent=eriba_caravan.microwave_absence_note(fixture(TOURING_P5)),
    )

    assert extracted.caravan.microwave is False
    snippet = extracted.provenance["microwave"].snippet
    assert "no microwave anywhere in the price list" in snippet
    # A recommendation, not a reviewer reference: it carries a value to accept or refuse.
    assert extracted.provenance["microwave"].reviewer_reference is False


def test_no_note_leaves_the_microwave_alone() -> None:
    """`None` has to stay `None`, so a mention never becomes a silent `No`."""
    product = layouts(TOURING_P5)["Touring 310"]

    extracted = eriba_caravan.build_extracted(
        product, "https://example.invalid/price-list.pdf"
    )

    assert extracted.caravan.microwave is None
    assert "microwave" not in extracted.provenance
