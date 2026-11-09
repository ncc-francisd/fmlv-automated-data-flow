"""Mini Freestyle — parsing and derivation only, no network.

The fixture is page 2 of the **2027 French catalogue**, as `fetch.pdf.extract_text` returns
it, carrying both specification tables. The source PDF is deliberately not committed.

The 2026 English edition the first version of this adapter read is gone from the site's
navigation and superseded by this one; see `docs/adapters/mini-freestyle.md`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.adapters import ADAPTERS, adapter_for, mini_freestyle
from src.adapters.mini_freestyle import (
    EXPECTED_LAYOUTS,
    FMLV_RANGE,
    HOME_PATH,
    RANGE_BY_MODEL,
    SILVER_RANGE,
    WITHDRAWN,
    Specification,
    _reconciles,
    _value,
    build_extracted,
    catalogue_url,
    parse_specifications,
)
from src.product_model.enums import CaravanBodyType
from src.vehicle_class import VehicleClass

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def catalogue() -> str:
    """Page 2 of the 2027 catalogue: the Minis table and the SILVER table, on one page."""
    return (FIXTURES / "mini-freestyle-catalogue-2027-page2.txt").read_text(encoding="utf-8")


def _by_model(specs: list[Specification]) -> dict[str, Specification]:
    return {spec.model: spec for spec in specs}


# --- registry -------------------------------------------------------------------------


def test_it_registers_under_trigano_with_the_mini_freestyle_display_name() -> None:
    """**Trigano is not a unique manufacturer.** The NCC list holds 187 Trigano/Silver and
    278 Trigano/Atom as well, and Atom is already an adapter here — so the display name is
    what tells them apart, and a registry row saying `Mini Freestyle` would find an empty
    baseline and propose every product as new."""
    assert mini_freestyle.MANUFACTURER == "Trigano"
    assert mini_freestyle.MANUFACTURER_DISPLAY_NAME == "Mini Freestyle"
    assert mini_freestyle.VEHICLE_CLASS is VehicleClass.CARAVAN
    assert (
        adapter_for("Trigano", VehicleClass.CARAVAN, display_name="Mini Freestyle")
        is mini_freestyle
    )
    assert ("Trigano", "Mini Freestyle", VehicleClass.CARAVAN) in ADAPTERS


def test_atom_still_resolves_on_the_same_manufacturer() -> None:
    """The check that this adapter has not displaced its sibling."""
    from src.adapters import atom

    assert adapter_for("Trigano", VehicleClass.MOTORHOME, display_name="Atom") is atom


# --- finding the catalogue ------------------------------------------------------------


def test_the_catalogue_is_sought_on_the_french_home_page() -> None:
    """**Not an oversight.** On 9 November 2026 the English home page stopped linking any
    catalogue while `/fr/` linked the 2027 edition, and the catalogue itself makes the
    French edition the authoritative one."""
    assert HOME_PATH == "/fr/"


def test_the_catalogue_url_is_read_not_constructed() -> None:
    """**Never hardcode it.** Its folder carries a year and its filename another, so the
    two have already disagreed once and both will move."""
    html = '<a class="lien-catalogue" href="files/2027/Minifreestyle_catalogue_2027.pdf">'

    assert catalogue_url(html) == (
        "https://www.mini-freestyle.com/files/2027/Minifreestyle_catalogue_2027.pdf"
    )


def test_the_relative_href_keeps_its_files_prefix() -> None:
    """**The trap this exists for.** The hrefs on this site are relative; dropping the
    `files/` segment gives a URL that returns a 404 *page*, not a PDF, and the first
    attempt at this survey did exactly that."""
    url = catalogue_url('<a href="files/2027/cat.pdf">')

    assert url is not None and "/files/" in url


def test_a_page_with_no_catalogue_yields_nothing() -> None:
    assert catalogue_url('<a href="/fr/about-us.html">About</a>') is None


def test_a_named_catalogue_wins_where_several_pdfs_are_linked() -> None:
    html = '<a href="files/2027/notice.pdf"> <a href="files/2027/catalogue_2027.pdf">'

    url = catalogue_url(html)

    assert url is not None and url.endswith("catalogue_2027.pdf")


# --- reading one cell -----------------------------------------------------------------


def test_a_decimal_comma_is_metres() -> None:
    assert _value("3,95", "m") == 3950
    assert _value("1,9", "m") == 1900


def test_an_asterisk_is_stripped() -> None:
    """The 2026 edition marked the Silver masses *values subject to confirmation*."""
    assert _value("925*", "kg") == 925


def test_two_figures_for_one_model_take_the_lower() -> None:
    """`695/807` is one model's two masses in running order. The base vehicle is the
    settled rule, and the base is the lower."""
    assert _value("695/807", "kg") == 695
    assert _value("750/1200", "kg") == 750


def test_an_empty_cell_is_not_a_zero() -> None:
    assert _value("-", "m") is None
    assert _value("", "kg") is None


# --- the spec tables ------------------------------------------------------------------


def test_both_tables_are_read_from_the_one_page(catalogue: str) -> None:
    """The 2027 edition puts the Minis and the SILVER line on a single page, where the 2026
    edition had one per page. Splitting on the page would now find only the first."""
    specs = _by_model(parse_specifications(catalogue))

    assert sorted(specs) == ["270", "290", "320", "380", "442"]


@pytest.mark.parametrize(
    ("model", "berths", "shipping", "body", "internal", "height", "headroom", "miro", "mtplm"),
    [
        ("270", 2, 3950, 2990, 2500, 1980, 1870, 594, 750),
        ("290", 2, 4420, 3470, 2970, 1980, 1870, 679, 750),
        ("320", 2, 4590, 3640, 3200, 1980, 1870, 692, 750),
        ("380", 3, 5310, 4280, 3800, 2000, 1950, 897, 1000),
        ("442", 3, 5910, 4880, 4400, 2000, 1950, 961, 1050),
    ],
)
def test_every_figure_matches_the_printed_table(  # noqa: PLR0913
    catalogue: str,
    model: str,
    berths: int,
    shipping: int,
    body: int,
    internal: int,
    height: int,
    headroom: int,
    miro: int,
    mtplm: int,
) -> None:
    """Read off the printed page, column by column. The whole range in one test because a
    column shifted by one is the failure that matters, and it only shows as a set."""
    spec = _by_model(parse_specifications(catalogue))[model]

    assert spec.berths == berths
    assert spec.shipping_length_mm == shipping
    assert spec.exterior_body_length_mm == body
    assert spec.internal_length_mm == internal
    assert spec.height_mm == height
    assert spec.headroom_mm == headroom
    assert spec.mro_kilograms == miro
    assert spec.mtplm_kilograms == mtplm


def test_the_320_is_longer_than_the_300_it_replaced(catalogue: str) -> None:
    """Worth pinning, because it is the thing that makes the 320 more than a rename.

    FMLV holds a `Mini / 300` at 4420mm over the hitch and 2970mm internally — the figures
    the 290 now carries. The 320 is a longer vehicle on the same product page, so a diff
    matching it to the 300 is matching a respec, not a relabel.
    """
    specs = _by_model(parse_specifications(catalogue))

    assert specs["320"].shipping_length_mm == 4590
    assert specs["290"].shipping_length_mm == 4420
    assert "300" not in specs


def test_the_awning_tolerance_does_not_swallow_the_figures(catalogue: str) -> None:
    """`Développé auvent + -5%` carries a digit inside the label itself, so separating it
    from its cells with "everything up to the first number" silently loses the row."""
    specs = _by_model(parse_specifications(catalogue))

    assert specs["270"].awning_length_mm == 8740
    assert specs["320"].awning_length_mm == 9140
    assert specs["442"].awning_length_mm == 9940


def test_the_standard_mass_is_taken_and_not_the_chassis_upgrade(catalogue: str) -> None:
    """`PTAC 750` sits directly above `Modification Administrative PTAC 750/1200`. The
    settled rule takes the standard figure, and the label is a prefix of the other."""
    specs = _by_model(parse_specifications(catalogue))

    assert specs["320"].mtplm_kilograms == 750
    assert specs["442"].mtplm_kilograms == 1050


def test_the_empty_weight_label_does_not_swallow_the_running_order_row(
    catalogue: str,
) -> None:
    """`Poids à vide` is a prefix of `Poids à vide en ordre de marche`. They stay apart
    only because a cell must begin with a digit, and `en` does not."""
    specs = _by_model(parse_specifications(catalogue))

    assert specs["270"].empty_weight_kilograms == 590
    assert specs["270"].mro_kilograms == 594


def test_an_artwork_caption_is_not_read_as_a_table_heading() -> None:
    """`380 442` and `270 320290` both appear on the page as captions above the
    photographs. Only the line directly above `NOMBRE DE PLACES` is a real heading."""
    page = "\n".join(
        [
            "380 442",
            "LIT TRANSVERSAL LITS JUMEAUX",
            "270 320290",
            "LIT TRANSVERSAL LIT CENTRAL",
            "270 290 320",
            "NOMBRE DE PLACES",
            "Nombre de places 2 2 2",
            "PTAC 750 750 750",
        ]
    )

    specs = _by_model(parse_specifications(page))

    assert sorted(specs) == ["270", "290", "320"]
    assert specs["320"].mtplm_kilograms == 750


def test_a_row_with_the_wrong_number_of_cells_is_not_read() -> None:
    """The cardinality failure: a short row shifts every value one model to the left, and
    the result reconciles perfectly while every caravan carries another's weight."""
    page = "\n".join(
        [
            "270 290 320",
            "NOMBRE DE PLACES",
            "Nombre de places 2 2 2",
            "PTAC 750 750",
        ]
    )

    specs = _by_model(parse_specifications(page))

    assert sorted(specs) == ["270", "290", "320"]
    assert all(spec.mtplm_kilograms is None for spec in specs.values())
    assert all(spec.berths == 2 for spec in specs.values())


def test_a_page_with_no_table_yields_nothing() -> None:
    assert parse_specifications("Nos caravanes surbaissées, plus de détails en ligne.") == []


# --- the self-check -------------------------------------------------------------------


def test_the_three_masses_must_be_in_order() -> None:
    spec = Specification(
        model="320", empty_weight_kilograms=675, mro_kilograms=692, mtplm_kilograms=750
    )

    reconciles, basis = _reconciles(spec)

    assert reconciles
    assert "58kg" in basis


def test_a_mass_in_running_order_above_the_maximum_is_refused() -> None:
    spec = Specification(model="320", mro_kilograms=800, mtplm_kilograms=750)

    reconciles, basis = _reconciles(spec)

    assert not reconciles
    assert "750" in basis


def test_an_empty_weight_above_the_running_order_is_refused() -> None:
    spec = Specification(
        model="320", empty_weight_kilograms=900, mro_kilograms=692, mtplm_kilograms=750
    )

    reconciles, _basis = _reconciles(spec)

    assert not reconciles


# --- what gets built --------------------------------------------------------------------


def _built(catalogue: str, model: str):
    spec = _by_model(parse_specifications(catalogue))[model]
    _reconciles_ok, basis = _reconciles(spec)
    return build_extracted(spec, "https://www.mini-freestyle.com/files/2027/cat.pdf", basis)


def test_the_minis_and_the_silvers_are_two_ranges_of_one_brand(catalogue: str) -> None:
    """Settled 9 November 2026. Mini Freestyle's "Our caravans" page offers two range
    tiles, each captioned MINI FREESTYLE above its name, and the 2027 catalogue heads its
    second table "Les SILVER". The display name stays `Mini Freestyle` for both.

    This reverses the reading of 7 October, when `Silver` looked like a navigation heading
    that would collide with NCC id 187 (`Trigano` / `Silver`). It does not: that id holds
    an older, separately branded Trend range, which nothing here touches.
    """
    for model in ("270", "290", "320"):
        assert _built(catalogue, model).caravan.manufacturer_range == FMLV_RANGE
    assert _built(catalogue, "380").caravan.manufacturer_range == SILVER_RANGE
    assert RANGE_BY_MODEL["442"] == SILVER_RANGE
    assert {
        _built(catalogue, m).caravan.manufacturer_display_name
        for m in ("270", "380")
    } == {"Mini Freestyle"}


def test_a_silver_is_not_labelled_a_mini_in_its_provenance(catalogue: str) -> None:
    """The prefix was hardcoded to "Mini", which would name a vehicle they do not sell."""
    built = _built(catalogue, "380")

    assert built.provenance["mro_kilograms"].snippet.startswith("Silver 380")
    assert "Range available while stocks last" in built.provenance["model"].snippet


def test_a_pop_top_is_filed_as_rigid(catalogue: str) -> None:
    """FMLV's `Pop Up` means a folding camper; a pop *top* is a rigid caravan whose roof
    raises. Settled by the requester, 7 October 2026."""
    built = _built(catalogue, "270")

    assert built.caravan.body_type is CaravanBodyType.RIGID
    assert "folding camper" in built.provenance["body_type"].snippet


def test_the_payload_is_derived_into_personal_effects(catalogue: str) -> None:
    """No payload is published, so it is MTPLM minus the mass in running order, and the
    whole of it goes to personal effects because no optional-equipment allowance exists."""
    built = _built(catalogue, "320")

    assert built.caravan.personal_effects_payload_kilograms == 58
    assert built.caravan.optional_equipment_payload_kilograms is None
    assert "arithmetic" in built.provenance["personal_effects_payload_kilograms"].snippet


def test_no_price_is_ever_proposed(catalogue: str) -> None:
    """There is none in the catalogue and none on the site. FMLV's three came from
    somewhere else and this adapter cannot maintain them."""
    built = _built(catalogue, "270")

    assert built.caravan.rrp_pounds is None
    assert "rrp_pounds" not in built.provenance


def test_no_nose_weight_is_proposed(catalogue: str) -> None:
    """Asked for TowCheck, 9 November 2026. Neither catalogue edition publishes one and
    nor does any page of the site, so the column stays blank rather than carried over."""
    built = _built(catalogue, "270")

    assert not any("nose" in snippet.lower() for snippet in
                   (p.snippet for p in built.provenance.values()))


def test_the_provenance_quotes_the_french_row_a_reader_will_find(catalogue: str) -> None:
    """Translating the label would send the next person looking for a row that is not in
    the document."""
    built = _built(catalogue, "320")

    assert "Poids à vide en ordre de marche" in built.provenance["mro_kilograms"].snippet
    assert "Hauteur hors tout" in built.provenance["height_mm"].snippet


# --- the roster -------------------------------------------------------------------------


def test_the_roster_size_is_pinned() -> None:
    """Three Minis and the Silver 380. The Silver 442 is read and held back, so it is not
    counted here."""
    assert EXPECTED_LAYOUTS == 4


def test_the_442_is_held_back_and_says_the_ruling_may_be_stale() -> None:
    """A model sitting in the catalogue and not in the output looks like a parsing failure
    unless the reason is said out loud — and here the reason is a ruling that newer
    evidence may overturn, which is the requester's call and not the adapter's."""
    assert "MAY OVERTURN" in WITHDRAWN["442"]
    assert "2027 catalogue" in WITHDRAWN["442"]
    assert "Silver 442" in WITHDRAWN["442"]


def test_the_withdrawn_model_is_still_in_the_catalogue(catalogue: str) -> None:
    """The contradiction is the maker's, and the adapter has to show it rather than hide
    it: they said the 442 had left the range and then published it again."""
    assert "442" in WITHDRAWN
    assert "442" in _by_model(parse_specifications(catalogue))


def test_the_reason_for_withdrawing_it_is_recorded() -> None:
    assert "9 october 2026" in WITHDRAWN["442"].lower()
