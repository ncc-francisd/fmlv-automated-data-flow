"""Tests for the Adria adapter's pure parsing functions, against real captured data.

The fixtures here are real snapshots (see `docs/adapters/adria.md`). From the Phase 4
survey: the `/livewire/update` JSON response for the Matrix range's layout-selector
component, and the text `pypdf` extracts from the technical-data PDF for one
configuration (Matrix Supreme 670 DC, "Supreme Alde RHD" trim). Added 2026-08-20 with
the 60Y editions: the same pair for Matrix 60Y, plus a Supersonic spec sheet, which is
here for one reason — it is Mercedes-based where every other fixture is Fiat, so it is
what stops `parse_base_vehicle_manufacturer` passing by returning a constant.

No network, no browser — the fetch side is covered separately in
`tests/fetch/test_browser.py`.
"""

from __future__ import annotations

from pathlib import Path

from src.adapters import adria, habitation
from src.adapters.adria import (
    DEFAULT_RANGES,
    RANGES,
    LivewireProduct,
    _build_extracted_motorhome,
    baseline_in_scope,
    cross_source_disagreements,
    parse_base_vehicle_manufacturer,
    parse_livewire_products,
    parse_technical_data_pdf,
    pdf_describes_layout,
    pdf_title,
    range_config,
    technical_data_pdf_url,
    unwrap_livewire,
)
from src.product_model.enums import BedType, Heating
from src.product_model.model import Motorhome

FIXTURES = Path(__file__).parent / "fixtures"
LIVEWIRE_RESPONSE = FIXTURES / "adria_matrix_livewire_response.json"
PDF_TEXT = FIXTURES / "adria_matrix_670dc_pdf_text.txt"
SIXTY_YEAR_LIVEWIRE_RESPONSE = FIXTURES / "adria_60y_matrix_livewire_response.json"
SIXTY_YEAR_PDF_TEXT = FIXTURES / "adria_60y_matrix_670sl_pdf_text.txt"
MERCEDES_PDF_TEXT = FIXTURES / "adria_supersonic_780dc_pdf_text.txt"


def test_unwrap_livewire_unpacks_array_wire_format() -> None:
    wrapped = {"apiData": [[{"label": "670 DC"}], {"s": "arr"}], "plain": "value"}

    unwrapped = unwrap_livewire(wrapped)

    assert unwrapped == {"apiData": [{"label": "670 DC"}], "plain": "value"}


def test_unwrap_livewire_leaves_ordinary_dicts_alone() -> None:
    # A real product dict has far more than an "s" key — must not be mistaken for
    # Livewire's [value, meta] wrapper shape.
    product = {"id": "14", "label": "Supreme Alde RHD", "price": {"retail_price": 93920}}

    assert unwrap_livewire(product) == product


def test_parse_livewire_products_reads_real_matrix_response() -> None:
    body = LIVEWIRE_RESPONSE.read_bytes()

    products = parse_livewire_products(body)

    assert len(products) > 0
    supreme_alde = next(p for p in products if p.trim_label == "Supreme Alde RHD")
    assert supreme_alde.layout_label == "670 DC"
    assert supreme_alde.product_id == "100351-2526-gxajsm5200w031-14"
    assert supreme_alde.price_pounds == 93920
    assert supreme_alde.price_string == "£93,920.00"
    assert supreme_alde.configurator_url is not None
    assert "configure.adria-mobil.com" in supreme_alde.configurator_url


def test_parse_livewire_products_skips_nodes_without_an_id() -> None:
    # The layout-level "base vehicle" entry has id=null and chassis dims but isn't a
    # sellable configuration — it must not show up as a product.
    body = LIVEWIRE_RESPONSE.read_bytes()

    products = parse_livewire_products(body)

    assert all(p.product_id for p in products)


def test_technical_data_pdf_url_derives_market_and_period_from_configurator_url() -> None:
    product = LivewireProduct(
        layout_label="670 DC",
        trim_label="Supreme Alde RHD",
        product_id="100351-2526-gxajsm5200w031-14",
        price_pounds=93920,
        price_string="£93,920.00",
        berths=4,
        seats=None,
        configurator_url="https://configure.adria-mobil.com/gb/25-26?link=1&range=A",
    )

    url = technical_data_pdf_url(product)

    assert url == "https://configure.adria-mobil.com/gb/25-26/100351-2526-gxajsm5200w031-14/pdf"


def test_technical_data_pdf_url_is_none_without_a_configurator_url() -> None:
    product = LivewireProduct(
        layout_label="670 DC",
        trim_label=None,
        product_id="x",
        price_pounds=None,
        price_string=None,
        berths=None,
        seats=None,
        configurator_url=None,
    )

    assert technical_data_pdf_url(product) is None


def test_parse_technical_data_pdf_reads_real_matrix_670dc_sheet() -> None:
    text = PDF_TEXT.read_text(encoding="utf-8")

    specs = parse_technical_data_pdf(text)

    assert specs["mh_length_mm"].value == 7485
    assert specs["mh_width_mm"].value == 2299
    assert specs["mh_height_mm"].value == 2905
    assert specs["mro_kilograms"].value == 3228
    assert specs["mtplm_kilograms"].value == 3650
    assert specs["berths"].value == 4
    assert specs["mh_passenger_seats_inc_driver"].value == 4
    # Snippets are what a reviewer sees next to the proposed value — should be the
    # actual matched text, not just the bare number.
    assert "Mass in running order" in specs["mro_kilograms"].snippet


def test_parse_technical_data_pdf_is_missing_but_not_crashing_on_unrelated_text() -> None:
    specs = parse_technical_data_pdf("This PDF has no spec table at all.")

    assert specs == {}


def test_spec_snippet_keeps_the_qualifier_that_the_recorded_figure_drops() -> None:
    # docs/adapters/README.md: record the base figure, carry the published wording into
    # the snippet. The 60Y Matrix sheet prints seats as "3 AT 3,500KG (4 AT 3,650KG)" —
    # the 3 is what FMLV records, and the reviewer cannot judge it without the rest.
    specs = parse_technical_data_pdf(SIXTY_YEAR_PDF_TEXT.read_text(encoding="utf-8"))

    seats = specs["mh_passenger_seats_inc_driver"]
    assert seats.value == 3
    assert seats.snippet == "Nr. of seats 3 AT 3,500KG (4 AT 3,650KG)"

    mro = specs["mro_kilograms"]
    assert mro.value == 3134
    assert "WITHOUT LUXE OR ALL INC' PACK" in mro.snippet


# --------------------------------------------------------------------------- #
# Self-checks: is this the right vehicle's spec sheet?
# --------------------------------------------------------------------------- #


def test_pdf_title_is_read_from_the_running_footer() -> None:
    text = PDF_TEXT.read_text(encoding="utf-8")

    assert pdf_title(text) == "MATRIX SUPREME 670 DC"


def test_pdf_describes_layout_confirms_a_matching_sheet() -> None:
    text = PDF_TEXT.read_text(encoding="utf-8")

    assert pdf_describes_layout(text, "670 DC") is True


def test_pdf_describes_layout_rejects_another_vehicles_sheet() -> None:
    # The failure this adapter uniquely risks: a constructed PDF URL resolving to a
    # different product. The numbers would be plausible and nothing downstream catches
    # it, so a False here is what stops the product being proposed at all.
    text = PDF_TEXT.read_text(encoding="utf-8")

    assert pdf_describes_layout(text, "780 SL") is False


def test_pdf_describes_layout_is_undecided_without_a_title_or_a_layout() -> None:
    # None is not False: an unanswerable question must not drop a product.
    assert pdf_describes_layout("no footer here at all", "670 DC") is None
    assert pdf_describes_layout(PDF_TEXT.read_text(encoding="utf-8"), None) is None


def test_cross_source_disagreement_is_reported_with_both_figures() -> None:
    specs = parse_technical_data_pdf(PDF_TEXT.read_text(encoding="utf-8"))
    product = LivewireProduct(
        layout_label="670 DC",
        trim_label="Supreme Alde RHD",
        product_id="x",
        price_pounds=None,
        price_string=None,
        berths=3,  # the sheet says 4
        seats=None,
        configurator_url=None,
    )

    assert cross_source_disagreements(product, specs) == {"berths": (3, 4)}


def test_agreeing_sources_report_nothing() -> None:
    specs = parse_technical_data_pdf(PDF_TEXT.read_text(encoding="utf-8"))
    body = LIVEWIRE_RESPONSE.read_bytes()
    supreme_alde = next(
        p for p in parse_livewire_products(body) if p.trim_label == "Supreme Alde RHD"
    )

    assert cross_source_disagreements(supreme_alde, specs) == {}


def test_a_disagreement_puts_both_figures_in_front_of_the_reviewer() -> None:
    specs = parse_technical_data_pdf(PDF_TEXT.read_text(encoding="utf-8"))
    product = LivewireProduct(
        layout_label="670 DC",
        trim_label="Supreme Alde RHD",
        product_id="x",
        price_pounds=None,
        price_string=None,
        berths=3,
        seats=None,
        configurator_url=None,
    )

    extracted = _build_extracted_motorhome(
        product,
        range_config("motorhomes/matrix", "Matrix"),
        "https://www.adria.co.uk/motorhomes/matrix",
        "https://configure.adria-mobil.com/gb/25-26/x/pdf",
        specs,
        "Fiat",
        cross_source_disagreements(product, specs),
    )

    # The spec sheet's figure is the one recorded...
    assert extracted.motorhome.berths == 4
    # ...but the range page's disagreeing figure is not lost.
    assert "3" in extracted.provenance["berths"].snippet
    assert "range page" in extracted.provenance["berths"].snippet


# --------------------------------------------------------------------------- #
# Base vehicle manufacturer
# --------------------------------------------------------------------------- #


def test_base_vehicle_manufacturer_reads_the_chassis_section_heading() -> None:
    text = PDF_TEXT.read_text(encoding="utf-8")

    assert parse_base_vehicle_manufacturer(text) == "Fiat"


def test_base_vehicle_manufacturer_is_not_a_constant() -> None:
    text = MERCEDES_PDF_TEXT.read_text(encoding="utf-8")

    assert parse_base_vehicle_manufacturer(text) == "Mercedes"


def test_base_vehicle_manufacturer_is_unset_rather_than_guessed_when_ambiguous() -> None:
    text = "CA. Fiat Chassis\nsome equipment\nCB. Mercedes Chassis\nmore equipment\n"

    assert parse_base_vehicle_manufacturer(text) is None


def test_base_vehicle_manufacturer_ignores_the_chassis_type_line() -> None:
    # "Chassis type FIAT special" describes the variant, not the manufacturer, and is
    # the wrong shape for base_vehicle_manufacturer.
    assert parse_base_vehicle_manufacturer("Chassis type FIAT special\n") is None


# --------------------------------------------------------------------------- #
# The 60Y anniversary editions
# --------------------------------------------------------------------------- #


def test_sixty_year_page_yields_its_single_layout() -> None:
    products = parse_livewire_products(SIXTY_YEAR_LIVEWIRE_RESPONSE.read_bytes())

    assert len(products) == 1
    assert products[0].layout_label == "670 SL"



def test_an_ordinary_range_still_names_its_products_by_layout_and_trim() -> None:
    body = LIVEWIRE_RESPONSE.read_bytes()
    supreme_alde = next(
        p for p in parse_livewire_products(body) if p.trim_label == "Supreme Alde RHD"
    )
    specs = parse_technical_data_pdf(PDF_TEXT.read_text(encoding="utf-8"))

    extracted = _build_extracted_motorhome(
        supreme_alde,
        range_config("motorhomes/matrix", "Matrix"),
        "https://www.adria.co.uk/motorhomes/matrix",
        "https://configure.adria-mobil.com/gb/25-26/x/pdf",
        specs,
        "Fiat",
        {},
    )

    assert extracted.motorhome.manufacturer_range == "Matrix"
    assert extracted.motorhome.model == "670 DC Supreme Alde RHD"


def test_sixty_year_sheet_confirms_its_own_identity() -> None:
    text = SIXTY_YEAR_PDF_TEXT.read_text(encoding="utf-8")

    assert pdf_title(text) == "MATRIX 670 SL 60Y"
    assert pdf_describes_layout(text, "670 SL") is True



def test_default_ranges_stays_the_two_element_shape_the_cli_reads() -> None:
    assert all(len(entry) == 2 for entry in DEFAULT_RANGES)
    assert len(DEFAULT_RANGES) == len(RANGES)


def _baseline_row(manufacturer_range: str, model: str) -> Motorhome:
    return Motorhome(
        manufacturer="Adria Mobil", manufacturer_range=manufacturer_range, model=model
    )



def test_a_sixty_year_run_does_not_pull_in_the_ordinary_range() -> None:
    row = _baseline_row("Matrix", "Supreme 670 DC")

    assert baseline_in_scope(row, {"Matrix 60Y"}) is False




def test_an_unknown_range_pair_falls_back_to_the_label_as_the_fmlv_range() -> None:
    config = range_config("motorhomes/whatever", "Whatever")

    assert config.fmlv_range == "Whatever"
    assert config.model_suffix is None


# --------------------------------------------------------------------------- #
# The habitation findings, from the technical-data sheet
# --------------------------------------------------------------------------- #

MATRIX_670DC = "adria_matrix_670dc_pdf_text.txt"
SUPERSONIC_780DC = "adria_supersonic_780dc_pdf_text.txt"
MATRIX_670SL = "adria_60y_matrix_670sl_pdf_text.txt"


def _sheet(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _findings(name: str) -> dict[str, object]:
    fitted, _pack = adria.fitted_equipment(_sheet(name))
    return habitation.features_from(fitted)


def test_the_cross_means_fitted_not_crossed_out() -> None:
    """Settled from the sheets themselves, and the whole reading rests on it.

    "Right hand drive" is marked on a right-hand-drive vehicle, and the flagship
    Supersonic's roof air conditioning is marked where the Matrix's is not.
    """
    matrix, _pack = adria.fitted_equipment(_sheet(MATRIX_670DC))
    supersonic, _pack = adria.fitted_equipment(_sheet(SUPERSONIC_780DC))

    assert "Right hand drive" in matrix
    assert "Roof-mounted air conditioning system" in supersonic
    assert "Roof-mounted air conditioning system" not in matrix


def test_a_line_carrying_a_value_counts_as_fitted() -> None:
    """`Refrigerator 142 L` has a capacity where its neighbours have a mark."""
    fitted, _pack = adria.fitted_equipment(_sheet(MATRIX_670DC))

    assert "Refrigerator 142 L" in fitted


def test_the_reading_starts_at_the_first_lettered_section() -> None:
    """Above it sit the cover figures and the All Inclusive Pack, a priced option pack.

    The pack's contents may well also be marked as fitted further down — that is what
    buying the pack does — but the pack listing itself is not evidence of fitment, and
    neither is "2305 total width (mm)".
    """
    fitted, pack = adria.fitted_equipment(_sheet(SUPERSONIC_780DC))

    assert "Auxiliary hot-water heater" in pack
    assert "total height (mm)" in pack
    assert not [line for line in fitted if line.endswith("(mm)")]


def test_alde_makes_the_matrix_wet_central() -> None:
    features = _findings(MATRIX_670DC)

    assert features["heating"].value is Heating.WET_CENTRAL
    assert "Alde Compact 3030" in features["heating"].snippet


def test_a_truma_combi_makes_the_anniversary_matrix_blown_air() -> None:
    features = _findings(MATRIX_670SL)

    assert features["heating"].value is Heating.BLOWN_AIR
    assert "Truma Combi 6E" in features["heating"].snippet


def test_the_bathroom_section_settles_the_washroom() -> None:
    features = _findings(MATRIX_670DC)

    assert features["shower_toilet_separated"].value is True
    assert "Separate shower cabin" in features["shower_toilet_separated"].snippet


def test_the_beds_differ_per_layout_because_one_sheet_is_one_vehicle() -> None:
    assert _findings(MATRIX_670DC)["bed_types"].value == [BedType.ISLAND]
    assert _findings(MATRIX_670SL)["bed_types"].value == [BedType.FIXED_SEPARATE]


def test_no_sheet_names_a_microwave() -> None:
    for name in (MATRIX_670DC, SUPERSONIC_780DC, MATRIX_670SL):
        assert "microwave" not in _findings(name)


# --- the rebuilt site, 29 September 2026 ------------------------------------------------


def test_the_ranges_are_the_ones_the_rebuilt_site_publishes() -> None:
    """Adria rebuilt adria.co.uk in September 2026. Campervans moved from `/campervans/`
    to `/vans/`, and `compact-max`, `twin-sports`, `twin-supreme` and the `/60y/` pages
    all went — the last three of those now return 404."""
    paths = [config.path for config in adria.RANGES]

    assert paths == [
        "motorhomes/supersonic",
        "motorhomes/sonic",
        "motorhomes/matrix",
        "motorhomes/coral",
        "motorhomes/compact",
        "vans/supertwin",
        "vans/twin",
    ]


def test_no_range_path_still_points_at_campervans() -> None:
    """The section was renamed, and a stale path yields nothing rather than failing."""
    assert not [c for c in adria.RANGES if c.path.startswith("campervans/")]


def test_range_selectors_are_unique_so_a_range_flag_is_unambiguous() -> None:
    selectors = [config.path for config in adria.RANGES]

    assert len(selectors) == len(set(selectors))


def test_a_market_link_is_preferred_over_a_language_one() -> None:
    """**Four caravans looked unpublished because of this.** The Adora and Action range
    pages carry two sets of configurator links, four saying `/en/` and four `/gb/`, and
    every `en` PDF 404s. `en` is a language fallback; `gb` is the UK market, and this is
    the UK site."""
    page = (
        '<a href="https://configure.adria-mobil.com/en/26-27">x</a>'
        '<a href="https://configure.adria-mobil.com/gb/26-27">y</a>'
    )

    assert adria._configurator_base(page) == "https://configure.adria-mobil.com/gb/26-27"


def test_a_page_offering_only_a_language_still_uses_it() -> None:
    """Better a market that might work than none at all."""
    page = '<a href="https://configure.adria-mobil.com/en/26-27">x</a>'

    assert adria._configurator_base(page) == "https://configure.adria-mobil.com/en/26-27"


def test_a_page_with_no_configurator_link_yields_nothing() -> None:
    assert adria._configurator_base("<p>no links here</p>") is None


# --- the roster, read from the rendered page ------------------------------------------


def test_the_layout_selector_yields_every_configuration() -> None:
    cards = (FIXTURES / "adria_supersonic_layout_selector.html").read_text(encoding="utf-8")

    got = adria.parse_dom_products(cards)

    assert len(got) == 5
    assert [p.layout_label for p in got] == ["780 DC", "780 DL", "780 SL", "890 LC", "890 LL"]
    assert {p.trim_label for p in got} == {"Standard RHD"}
    assert all(p.configurator_url == "https://configure.adria-mobil.com/gb/26-27" for p in got)


def test_a_livewire_modifier_does_not_empty_the_roster() -> None:
    """**The trap this exists for.** On 1 October 2026 Adria changed every button from
    `wire:click` to `wire:click.prevent`. The attribute name was matched literally, so
    both adapters went to zero products overnight — caravans share this parser — and a
    run could only fail on the empty-scrape guard. Modifiers are ordinary Livewire."""
    button = (
        'wire:click{mod}="setProductId(\'100351-2627-cpel-b6200w032-14\')"'
        ' data-gtm-type="780 DC" data-gtm-value="Standard RHD"'
    )

    for modifier in ("", ".prevent", ".stop", ".prevent.stop", ".self"):
        got = adria.parse_dom_products(button.format(mod=modifier))
        assert len(got) == 1, f"{modifier!r} emptied the roster"
        assert got[0].layout_label == "780 DC"


def test_either_apostrophe_spelling_is_read() -> None:
    """A live DOM writes a literal apostrophe; a saved snapshot writes `&#039;`."""
    for quote in ("'", "&#039;"):
        markup = (
            f'wire:click.prevent="setProductId({quote}abc-1{quote})"'
            ' data-gtm-type="670 DC" data-gtm-value="Select RHD"'
        )
        got = adria.parse_dom_products(markup)
        assert len(got) == 1 and got[0].product_id == "abc-1"


# --- the supplied price list ----------------------------------------------------------


def test_the_price_list_covers_the_whole_published_range() -> None:
    """35 configurations on the site, 35 rows on the 2027 list, one apiece. The other
    four rows on Adria's list are SUN LIVING's and belong to that adapter."""
    assert len(adria.PRICES_NOT_ON_THE_SITE) == 35
    assert {key[0] for key in adria.PRICES_NOT_ON_THE_SITE} == {
        config.fmlv_range for config in adria.RANGES
    }


def test_the_price_is_keyed_on_what_the_site_calls_the_van_not_the_price_list() -> None:
    """TWIN's price list sells `Select`/`Supreme`; the site labels the same vans
    `Standard RHD`/`SunRoofXL RHD`. The PDFs are titled `TWIN SELECT 640 SGX` for the
    first and `TWIN SUPREME 640 SGX` for the second, so the site's label is the key."""
    twin = {key[2] for key in adria.PRICES_NOT_ON_THE_SITE if key[0] == "TWIN"}

    assert twin == {"Standard RHD", "SunRoofXL RHD", "Supreme PTR RHD"}
    assert adria.PRICES_NOT_ON_THE_SITE[("TWIN", "640 SGX", "Standard RHD")] == 78999
    assert adria.PRICES_NOT_ON_THE_SITE[("TWIN", "640 SGX", "SunRoofXL RHD")] == 78499


def test_an_unlisted_configuration_is_priced_at_nothing_not_zero() -> None:
    """Emitting a 0 or a blank would wipe the figure FMLV already holds."""
    config = next(c for c in adria.RANGES if c.fmlv_range == "TWIN")
    unknown = adria.LivewireProduct(
        layout_label="999 ZZ", trim_label="Standard RHD", product_id="x",
        price_pounds=None, price_string=None, berths=None, seats=None,
        configurator_url=None,
    )

    assert adria.price_for(unknown, config) is None


# --- the model name comes from the spec sheet -----------------------------------------


def _conf(layout, trim):
    return adria.LivewireProduct(
        layout_label=layout, trim_label=trim, product_id="x", price_pounds=None,
        price_string=None, berths=None, seats=None, configurator_url=None,
    )


def test_the_model_is_named_as_the_spec_sheet_names_it() -> None:
    """`TWIN SUPREME 640 SLB` is series, trim, layout; FMLV holds `Supreme 640 SLB`."""
    twin = next(c for c in adria.RANGES if c.fmlv_range == "TWIN")

    got = adria._model_from_pdf_title("TWIN SUPREME 640 SLB", _conf("640 SLB", "SunRoofXL RHD"), twin)

    assert got == "Supreme 640 SLB"


def test_a_range_with_no_trim_keeps_the_layout_alone() -> None:
    supersonic = next(c for c in adria.RANGES if c.fmlv_range == "Supersonic")

    got = adria._model_from_pdf_title(
        "SUPERSONIC 780 DC", _conf("780 DC", "Standard RHD"), supersonic
    )

    assert got == "780 DC"


def test_the_layout_code_keeps_its_own_casing() -> None:
    """The sheet shouts everything; only the trim words are title-cased, so `MB 600 SPB`
    survives rather than becoming `Mb 600 Spb`."""
    supertwin = next(c for c in adria.RANGES if c.fmlv_range == "Supertwin")

    got = adria._model_from_pdf_title(
        "SUPERTWIN MB 600 SPB", _conf("MB 600 SPB", "Supreme RHD AWD"), supertwin
    )

    assert got == "MB 600 SPB"


def test_the_pop_top_comes_from_the_trim_because_the_sheet_omits_it() -> None:
    """Both PTR variants of a layout share one spec sheet and one title, so the only
    thing separating them is the trim label. FMLV spells it `PopTop`."""
    supertwin = next(c for c in adria.RANGES if c.fmlv_range == "Supertwin")
    title = "SUPERTWIN MB 700 SGX"

    plain = adria._model_from_pdf_title(title, _conf("MB 700 SGX", "Supreme RHD AWD"), supertwin)
    popped = adria._model_from_pdf_title(
        title, _conf("MB 700 SGX", "Supreme PTR RHD AWD"), supertwin
    )

    assert plain == "MB 700 SGX"
    assert popped == "MB 700 SGX PopTop"


def test_a_missing_or_odd_title_falls_back_to_the_range_page() -> None:
    """A product whose PDF failed is still worth collecting."""
    twin = next(c for c in adria.RANGES if c.fmlv_range == "TWIN")
    product = _conf("640 SLB", "SunRoofXL RHD")

    assert adria._model_from_pdf_title(None, product, twin) is None
    assert adria._model_from_pdf_title("SOMETHING ELSE 999 ZZ", product, twin) is None
    assert adria._model_name(product, twin) == "640 SLB SunRoofXL RHD"
