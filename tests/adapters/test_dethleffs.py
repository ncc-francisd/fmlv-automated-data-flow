"""Dethleffs' parsing, against real captured model pages.

No network. Each `dethleffs_<layout>.html` fixture is one model page trimmed to the three
things the adapter reads: the technical-data modal, the main-facts card and the body-type
tag. **All five tables sharing the modal's class are kept**, including the four equipment
lists, because picking the specification out of them is what the parse gets right or wrong.

Nine of the 48 layouts were kept, each for a reason:

* `just_van_t1` — the requester's warning made concrete: a "Van" the site tags `Low
  Profile`. Also the `<sup>` footnote sitting inside the height cell.
* `globetrail_540_dr` — dual height `265 / 278 (○)`, a `with mirrors` width 60cm wider
  than the body, and a pop-top offered as a cost option.
* `alpa_a_6820_2` and `alpa_i_6820_2` — the pair that collides. Same number, different
  body, and the range whose letter FMLV keeps in the *range*.
* `globebus_performance_4x4_t46` and `globetrail_performance_600_dr_classic` — the same VW
  Crafter under a motorhome and a campervan. The reason body type cannot come from chassis.
* `globebus_active_i1` — berths printed as a bare `4`, and a letter FMLV keeps in the model.
* `trend_active_i7027` — seats printed as a range, `2 - 3 (○)`.
* `xl_a_7872_2_family` — FMLV range `XL` with the whole letter-bearing name as the model.

Every negative test below is a trap that is real on this site — see
`docs/adapters/dethleffs.md`.
"""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

import pytest

from src.adapters import dethleffs
from src.adapters.dethleffs import DethleffsLayout
from src.product_model.enums import BedType, BodyType, Heating, Refrigeration

FIXTURES = Path(__file__).parent / "fixtures"

#: (fixture name, the URL it was captured from). The URL matters: `parse_layout` reads the
#: section out of it, and the section is one leg of the motorhome/campervan self-check.
CAPTURED: tuple[tuple[str, str], ...] = (
    ("just_van_t1", "https://www.dethleffs.co.uk/motorhomes/just-van/t-1"),
    ("globetrail_540_dr", "https://www.dethleffs.co.uk/camper-van/globetrail/540-dr-fiat"),
    ("alpa_a_6820_2", "https://www.dethleffs.co.uk/motorhomes/alpa/a-6820-2"),
    ("alpa_i_6820_2", "https://www.dethleffs.co.uk/motorhomes/alpa/i-6820-2"),
    (
        "globebus_performance_4x4_t46",
        "https://www.dethleffs.co.uk/motorhomes/globebus-performance-4x4/t-46",
    ),
    (
        "globetrail_performance_600_dr_classic",
        "https://www.dethleffs.co.uk/camper-van/globetrail-performance/600-dr-classic",
    ),
    ("globebus_active_i1", "https://www.dethleffs.co.uk/motorhomes/globebus-active/i-1"),
    ("trend_active_i7027", "https://www.dethleffs.co.uk/motorhomes/trend-active/i-7027"),
    ("xl_a_7872_2_family", "https://www.dethleffs.co.uk/motorhomes/xl-a/a-7872-2"),
)

#: What Dethleffs publicly list on the GB site, and what the sitemap must therefore yield:
#: 36 motorhomes and 12 campervans. Reconciled against all 11 range pages on 2 September
#: 2026 with nothing missing in either direction.
EXPECTED_LAYOUT_COUNT = 48
EXPECTED_MOTORHOME_COUNT = 36
EXPECTED_CAMPERVAN_COUNT = 12


def _read(name: str) -> str:
    return (FIXTURES / f"dethleffs_{name}.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def layouts() -> dict[str, DethleffsLayout]:
    """Every captured layout, keyed on its fixture name, parsed as `collect` parses it."""
    found: dict[str, DethleffsLayout] = {}
    for name, url in CAPTURED:
        layout = dethleffs.parse_layout(url, _read(name))
        assert layout is not None, f"{name} did not parse"
        found[name] = layout
    return found


# --------------------------------------------------------------------------- #
# The specification table, picked out of five that share its class
# --------------------------------------------------------------------------- #


def test_every_captured_page_parses(layouts: dict[str, DethleffsLayout]) -> None:
    assert len(layouts) == len(CAPTURED)


def test_spec_table_is_the_one_with_two_header_cells() -> None:
    """Four equipment tables share the modal's class and have a single `<th>`.

    Taking the first table blindly reads `Electrical installation` on any page where the
    order changes, so the discriminator is the header count, not the position.
    """
    html = _read("just_van_t1")
    assert len(dethleffs._TABLE.findall(html)) == 5

    range_heading, model, specs = dethleffs.parse_spec_table(html)
    assert (range_heading, model) == ("Just Van", "T 1")
    assert dethleffs.LABEL_MRO in specs
    # ...and not a heading from one of the equipment tables.
    assert range_heading not in {"Electrical installation", "Heating", "Water supply", "Gas supply"}


def test_reference_row_reads_exactly(layouts: dict[str, DethleffsLayout]) -> None:
    """Just Van T 1, the row quoted in `docs/adapters/dethleffs.md`, field for field."""
    layout = layouts["just_van_t1"]
    assert layout.range_heading == "Just Van"
    assert layout.model == "T 1"
    assert layout.rrp_pounds == 61990
    assert layout.base_vehicle_manufacturer == "Fiat"
    assert (layout.mh_length_mm, layout.mh_width_mm, layout.mh_height_mm) == (5990, 2200, 2730)
    assert layout.mro_kilograms == 2611
    assert layout.mro_band == (2480, 2742)
    assert layout.mtplm_kilograms == 3499
    assert layout.berths == 2
    assert layout.mh_passenger_seats_inc_driver == 4


# --------------------------------------------------------------------------- #
# Body type comes from the tag, because the name and the chassis both lie
# --------------------------------------------------------------------------- #


def test_just_van_is_a_motorhome_not_a_campervan(layouts: dict[str, DethleffsLayout]) -> None:
    """The requester's warning, and the trap the whole body-type rule exists to avoid.

    "Van" in the name, `Low Profile` on the page. Anything inferring the type from the model
    name files a 2.20m-wide GRP coach-built as a panel-van conversion.
    """
    layout = layouts["just_van_t1"]
    assert layout.body_tag == "Low Profile"
    assert layout.body_type is BodyType.COACH_BUILT_LOW_PROFILE
    assert layout.body_type is not BodyType.CAMPERVAN


def test_the_same_vw_crafter_underpins_both_a_motorhome_and_a_campervan(
    layouts: dict[str, DethleffsLayout],
) -> None:
    """Globebus is always a motorhome and Globetrail always a campervan — not the chassis.

    Requester rule, 2 September 2026. These two layouts share a base vehicle and differ in
    body type, so a classifier keyed on the chassis gets one of them wrong whichever way it
    guesses.
    """
    motorhome = layouts["globebus_performance_4x4_t46"]
    campervan = layouts["globetrail_performance_600_dr_classic"]

    assert motorhome.base_vehicle_manufacturer == campervan.base_vehicle_manufacturer == "VW"
    assert motorhome.family == "Globebus"
    assert campervan.family == "Globetrail"
    assert motorhome.body_type is BodyType.COACH_BUILT_LOW_PROFILE
    assert campervan.body_type is BodyType.CAMPERVAN_HIGH_TOP


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("alpa_a_6820_2", BodyType.COACH_BUILT_OVER_CAB_BED),
        ("alpa_i_6820_2", BodyType.A_CLASS),
        ("globebus_active_i1", BodyType.A_CLASS),
        ("xl_a_7872_2_family", BodyType.COACH_BUILT_OVER_CAB_BED),
        ("globetrail_540_dr", BodyType.CAMPERVAN_HIGH_TOP),
    ],
)
def test_body_type_from_the_site_tag(
    layouts: dict[str, DethleffsLayout], name: str, expected: BodyType
) -> None:
    assert layouts[name].body_type is expected


def test_an_optional_pop_top_does_not_make_it_an_elevating_roof(
    layouts: dict[str, DethleffsLayout],
) -> None:
    """Per `docs/adapters/README.md`, a cost-option roof does not change what the vehicle is.

    All ten Fiat Globetrails offer one, marked `(○)`.
    """
    layout = layouts["globetrail_540_dr"]
    assert layout.poptop_published is not None
    assert dethleffs.OPTIONAL_MARK in layout.poptop_published
    assert layout.has_standard_elevating_roof is False
    assert layout.body_type is BodyType.CAMPERVAN_HIGH_TOP


def test_a_standard_pop_top_would_make_it_an_elevating_roof(
    layouts: dict[str, DethleffsLayout],
) -> None:
    """The other half of the 2×2, which no current layout exercises.

    Written as a rule rather than a constant so a future standard-fit roof classifies itself
    instead of being silently filed as a plain high top.
    """
    standard = replace(layouts["globetrail_540_dr"], poptop_published="209 x 143")
    assert standard.has_standard_elevating_roof is True
    assert standard.body_type is BodyType.CAMPERVAN_HIGH_TOP_ELEVATING_ROOF


def test_a_low_campervan_is_not_a_high_top(layouts: dict[str, DethleffsLayout]) -> None:
    short = replace(layouts["globetrail_540_dr"], mh_height_mm=2050)
    assert short.body_type is BodyType.CAMPERVAN


def test_an_unknown_tag_is_blank_not_the_nearest_type(
    layouts: dict[str, DethleffsLayout],
) -> None:
    assert replace(layouts["just_van_t1"], body_tag="Skyliner").body_type is None
    assert replace(layouts["just_van_t1"], body_tag=None).body_type is None


# --------------------------------------------------------------------------- #
# The FMLV identity, which the export decides and the website does not
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("name", "fmlv_range", "fmlv_model"),
    [
        # FMLV keeps the body letter in the RANGE for these...
        ("alpa_a_6820_2", "Alpa A", "6820-2"),
        ("alpa_i_6820_2", "Alpa I", "6820-2"),
        ("trend_active_i7027", "Trend Active I", "7027"),
        # ...and in the MODEL for these.
        ("globebus_active_i1", "Globebus Active", "I 1"),
        ("xl_a_7872_2_family", "XL", "A 7872-2 Family"),
        # Ranges FMLV names differently from the site.
        ("globetrail_540_dr", "Globetrail Classic", "540 DR"),
        # Ranges with no FMLV counterpart keep the site's own name.
        ("just_van_t1", "Just Van", "T 1"),
        # Deliberately NOT mapped onto FMLV's misfiled `Globetrail VW Performance 4X4`.
        ("globebus_performance_4x4_t46", "Globebus Performance 4x4", "T 46"),
    ],
)
def test_fmlv_identity(
    layouts: dict[str, DethleffsLayout], name: str, fmlv_range: str, fmlv_model: str
) -> None:
    layout = layouts[name]
    assert layout.fmlv_range == fmlv_range
    assert layout.fmlv_model == fmlv_model


def test_the_two_alpa_ranges_do_not_collapse_into_one(
    layouts: dict[str, DethleffsLayout],
) -> None:
    """`/motorhomes/alpa` serves two ranges, so the range cannot come from the URL.

    Both layouts are `6820-2` to FMLV and are told apart only by the range, which is why
    deriving it from the path would merge two different vehicles.
    """
    coachbuilt, a_class = layouts["alpa_a_6820_2"], layouts["alpa_i_6820_2"]
    assert coachbuilt.url.rsplit("/", 2)[1] == a_class.url.rsplit("/", 2)[1] == "alpa"
    assert coachbuilt.fmlv_model == a_class.fmlv_model == "6820-2"
    assert coachbuilt.fmlv_range != a_class.fmlv_range
    assert coachbuilt.body_type is not a_class.body_type


def test_an_unmapped_range_heading_falls_back_to_the_site_name(
    layouts: dict[str, DethleffsLayout],
) -> None:
    """Visible and wrong beats silently mis-filed under a neighbouring range."""
    unknown = replace(layouts["just_van_t1"], range_heading="Aero Active Low profile")
    assert unknown.fmlv_range == "Aero Active Low profile"
    assert unknown.fmlv_model == "T 1"


def test_range_map_covers_every_heading_the_site_publishes(
    layouts: dict[str, DethleffsLayout],
) -> None:
    for layout in layouts.values():
        assert layout.range_heading in dethleffs.RANGE_MAP


# --------------------------------------------------------------------------- #
# The value traps
# --------------------------------------------------------------------------- #


def test_footnote_superscripts_are_stripped_from_value_cells(
    layouts: dict[str, DethleffsLayout],
) -> None:
    """`<td>273 <sup>1</sup></td>` is 273cm, not 2731."""
    assert "<sup>" in _read("just_van_t1")
    assert layouts["just_van_t1"].mh_height_mm == 2730


def test_dual_height_takes_the_standard_roof(layouts: dict[str, DethleffsLayout]) -> None:
    """All ten Fiat Globetrails print `265 / 278 (○)`; the 278 is the optional pop-top."""
    _range_heading, _model, specs = dethleffs.parse_spec_table(_read("globetrail_540_dr"))
    assert specs[dethleffs.LABEL_HEIGHT] == "265 / 278 (○)"
    assert layouts["globetrail_540_dr"].mh_height_mm == 2650


def test_width_excludes_mirrors(layouts: dict[str, DethleffsLayout]) -> None:
    """The `with mirrors` row is 60cm wider and must not be matched by prefix."""
    _range_heading, _model, specs = dethleffs.parse_spec_table(_read("globetrail_540_dr"))
    assert specs[dethleffs.LABEL_WIDTH] == "205"
    assert specs[dethleffs.LABEL_WIDTH_WITH_MIRRORS] == "265"
    assert layouts["globetrail_540_dr"].mh_width_mm == 2050


def test_the_open_pop_top_height_is_not_the_vehicle_height(
    layouts: dict[str, DethleffsLayout],
) -> None:
    _range_heading, _model, specs = dethleffs.parse_spec_table(_read("globetrail_540_dr"))
    assert specs[dethleffs.LABEL_HEIGHT_POPTOP_OPEN] == "358"
    assert layouts["globetrail_540_dr"].mh_height_mm == 2650


def test_berths_and_seats_take_the_standard_figure(
    layouts: dict[str, DethleffsLayout],
) -> None:
    """`2 / 3 (○)` is two berths, and `2 - 3 (○)` is two seats."""
    assert layouts["just_van_t1"].berths_published == "2 / 3 (○)"
    assert layouts["just_van_t1"].berths == 2
    assert layouts["trend_active_i7027"].seats_published == "2 - 3 (○)"
    assert layouts["trend_active_i7027"].mh_passenger_seats_inc_driver == 2


def test_berths_printed_as_a_single_number_are_not_dropped(
    layouts: dict[str, DethleffsLayout],
) -> None:
    """18 of the 48 layouts print a bare `4`, meaning standard and maximum are the same.

    A parser expecting `n / n` loses them silently, which is the worst kind of failure here.
    """
    layout = layouts["globebus_active_i1"]
    assert layout.berths_published == "4"
    assert layout.berths == 4


def test_payload_is_derived_and_is_not_the_optional_equipment_mass(
    layouts: dict[str, DethleffsLayout],
) -> None:
    """The trap shared with Sunlight, Etrusco and Bürstner.

    `Manufacturer-specified mass for optional equipment` sits between the two masses, right
    where payload would go: 555kg on this layout against a real payload of 888kg.
    """
    layout = layouts["just_van_t1"]
    _range_heading, _model, specs = dethleffs.parse_spec_table(_read("just_van_t1"))
    assert specs[dethleffs.LABEL_NOT_PAYLOAD] == "555"
    assert layout.mh_payload_kilograms == 3499 - 2611 == 888


def test_price_drops_the_pence(layouts: dict[str, DethleffsLayout]) -> None:
    _range_heading, _model, specs = dethleffs.parse_spec_table(_read("just_van_t1"))
    assert specs[dethleffs.LABEL_PRICE].startswith("£61,990.00")
    assert layouts["just_van_t1"].rrp_pounds == 61990


# --------------------------------------------------------------------------- #
# The self-checks
# --------------------------------------------------------------------------- #


def test_every_captured_layout_passes_every_self_check(
    layouts: dict[str, DethleffsLayout],
) -> None:
    for name, layout in layouts.items():
        assert dethleffs._band_reconciles(layout), name
        assert dethleffs._card_disagreements(layout) == [], name
        assert dethleffs._family_disagreement(layout) is None, name
        assert dethleffs._reconciles(layout), name


def test_a_band_from_another_layout_fails_the_check(
    layouts: dict[str, DethleffsLayout],
) -> None:
    """The band is a function of the mass, so a slipped pairing cannot stay self-consistent."""
    slipped = replace(layouts["just_van_t1"], mro_band=(2603, 2877))  # the 540 DR's band
    assert dethleffs._band_reconciles(slipped) is False


def test_rounding_slack_is_allowed(layouts: dict[str, DethleffsLayout]) -> None:
    """The band is printed rounded to whole kilograms, so a kilogram either way is fine."""
    nudged = replace(layouts["just_van_t1"], mro_band=(2479, 2743))
    assert dethleffs._band_reconciles(nudged) is True


def test_a_missing_band_does_not_fail_the_check(layouts: dict[str, DethleffsLayout]) -> None:
    assert dethleffs._band_reconciles(replace(layouts["just_van_t1"], mro_band=None)) is True


def test_the_card_catches_a_misread_row(layouts: dict[str, DethleffsLayout]) -> None:
    """The check the ±5% band cannot do.

    The band only proves a mass is paired with its own tolerance; it says nothing about
    whether the right row was read. The card is a second, independent rendering of six
    values, so a wrong row shows up as a disagreement.
    """
    layout = layouts["just_van_t1"]
    assert dethleffs._card_disagreements(replace(layout, mh_length_mm=6630)) == [
        "length (table 6630, card 5990)"
    ]
    assert dethleffs._card_disagreements(replace(layout, rrp_pounds=63690)) == [
        "price (table 63690, card 61990)"
    ]


def test_a_field_absent_from_the_card_is_not_a_disagreement(
    layouts: dict[str, DethleffsLayout],
) -> None:
    layout = layouts["just_van_t1"]
    assert dethleffs._card_disagreements(replace(layout, card={})) == []
    assert dethleffs._card_disagreements(replace(layout, card=None)) == []


def test_the_family_rule_catches_a_campervan_tag_on_a_motorhome_page(
    layouts: dict[str, DethleffsLayout],
) -> None:
    """Family name, URL section and body tag are three statements of one fact."""
    mislabelled = replace(layouts["globebus_performance_4x4_t46"], body_tag="Camper Van")
    disagreement = dethleffs._family_disagreement(mislabelled)
    assert disagreement is not None
    assert "motorhomes" in disagreement


def test_the_family_rule_catches_a_motorhome_tag_on_a_globetrail(
    layouts: dict[str, DethleffsLayout],
) -> None:
    mislabelled = replace(
        layouts["globetrail_540_dr"], section="motorhomes", body_tag="Low Profile"
    )
    disagreement = dethleffs._family_disagreement(mislabelled)
    assert disagreement is not None
    assert "Globetrail" in disagreement


def test_masses_that_do_not_reconcile_are_rejected(
    layouts: dict[str, DethleffsLayout],
) -> None:
    layout = layouts["just_van_t1"]
    assert dethleffs._reconciles(replace(layout, mtplm_kilograms=2000)) is False  # below MRO
    assert dethleffs._reconciles(replace(layout, mtplm_kilograms=2650)) is False  # payload 39kg
    assert dethleffs._reconciles(replace(layout, mro_kilograms=None)) is True  # nothing to check


# --------------------------------------------------------------------------- #
# The roster
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def model_urls() -> list[str]:
    return dethleffs.parse_sitemap_model_urls(
        (FIXTURES / "dethleffs_sitemap_index.xml").read_text(encoding="utf-8"),
        (FIXTURES / "dethleffs_sitemap.xml").read_text(encoding="utf-8"),
    )


def test_the_sitemap_yields_the_whole_published_roster(model_urls: list[str]) -> None:
    """Dethleffs list 36 motorhomes and 12 campervans on the GB site."""
    assert len(model_urls) == EXPECTED_LAYOUT_COUNT
    assert sum("/motorhomes/" in url for url in model_urls) == EXPECTED_MOTORHOME_COUNT
    assert sum("/camper-van/" in url for url in model_urls) == EXPECTED_CAMPERVAN_COUNT


def test_the_sitemap_filter_excludes_everything_that_is_not_a_layout(
    model_urls: list[str],
) -> None:
    """Range pages, the configurator and marketing pages all share a prefix with layouts."""
    assert not any("/configurator/" in url for url in model_urls)
    assert "https://www.dethleffs.co.uk/motorhomes" not in model_urls
    assert "https://www.dethleffs.co.uk/motorhomes/just-van" not in model_urls
    assert "https://www.dethleffs.co.uk/2025/globebus-performance-4x4" not in model_urls
    assert "https://www.dethleffs.co.uk/active" not in model_urls
    for url in model_urls:
        assert re.match(
            r"^https://www\.dethleffs\.co\.uk/(motorhomes|camper-van)/[^/]+/[^/]+$", url
        )


def test_every_default_range_has_layouts(model_urls: list[str]) -> None:
    """The stated roster, which is what turns a vanished range into a warning."""
    for path, label in dethleffs.DEFAULT_RANGES:
        prefix = f"{dethleffs.BASE_URL}/{path}/"
        assert any(url.startswith(prefix) for url in model_urls), label


def test_every_layout_belongs_to_a_declared_range(model_urls: list[str]) -> None:
    """No layout sits outside `DEFAULT_RANGES` — the check that the roster is complete."""
    prefixes = tuple(f"{dethleffs.BASE_URL}/{path}/" for path, _label in dethleffs.DEFAULT_RANGES)
    assert [url for url in model_urls if not url.startswith(prefixes)] == []


def test_the_campervan_path_is_singular() -> None:
    """`/campervans` 404s; the real path is `/camper-van`."""
    assert all("camper-van" in path or "motorhomes" in path for path, _ in dethleffs.DEFAULT_RANGES)
    assert not any("campervans" in path for path, _ in dethleffs.DEFAULT_RANGES)


# --------------------------------------------------------------------------- #
# Narrowing the baseline for a --range run
# --------------------------------------------------------------------------- #


def test_every_range_selector_maps_to_fmlv_ranges() -> None:
    """The gap that a real `--range` run exposed.

    `cli.baseline_scope` defaults to matching the FMLV `manufacturer_range` against the
    selector label. Here a selector is a URL *path*, and no path label is an FMLV range
    name — so without the hook every narrowed run would diff against an empty baseline and
    propose live products as new, which uploads duplicates.
    """
    for _path, label in dethleffs.DEFAULT_RANGES:
        assert label in dethleffs.RANGE_PATH_TO_FMLV_RANGES, label


def test_every_mapped_fmlv_range_is_reachable_from_a_selector() -> None:
    """No stray entry that no `--range` value can ever select."""
    labels = {label for _path, label in dethleffs.DEFAULT_RANGES}
    assert set(dethleffs.RANGE_PATH_TO_FMLV_RANGES) == labels


def test_every_range_map_target_is_claimed_by_some_selector() -> None:
    """Every range the adapter can emit must be in scope for some narrowed run.

    Otherwise a `--range` run collects a product whose baseline row it never looked at, and
    proposes it as new alongside the row it should have matched.
    """
    emitted = {fmlv_range for fmlv_range, _strip in dethleffs.RANGE_MAP.values()}
    claimed: set[str] = set()
    for ranges in dethleffs.RANGE_PATH_TO_FMLV_RANGES.values():
        claimed |= ranges
    assert emitted <= claimed


@pytest.mark.parametrize(
    ("label", "in_scope", "out_of_scope"),
    [
        # One path, two FMLV ranges — the case the default scope cannot express.
        ("Alpa", ["Alpa A", "Alpa I"], ["XL", "Trend Active T"]),
        ("Trend Active", ["Trend Active T", "Trend Active I"], ["Just Camp Active"]),
        # Paths FMLV names differently from the site.
        ("Globetrail", ["Globetrail Classic"], ["Globetrail Active"]),
        ("XL A", ["XL"], ["XL Family I"]),
        # The misfiled baseline row travels with the range that really owns it.
        (
            "Globebus Performance 4x4",
            ["Globebus Performance 4x4", "Globetrail VW Performance 4X4"],
            ["Globebus Performance"],
        ),
    ],
)
def test_baseline_scope_selects_the_right_rows(
    label: str, in_scope: list[str], out_of_scope: list[str]
) -> None:
    from src.product_model.model import Motorhome

    for fmlv_range in in_scope:
        assert dethleffs.baseline_in_scope(Motorhome(manufacturer_range=fmlv_range), {label})
    for fmlv_range in out_of_scope:
        assert not dethleffs.baseline_in_scope(Motorhome(manufacturer_range=fmlv_range), {label})


def test_the_cli_picks_up_the_hook() -> None:
    """`cli.baseline_scope` finds it by `getattr`, so a rename here silently disables it."""
    from src.cli import baseline_scope
    from src.product_model.model import Motorhome

    scope = baseline_scope(dethleffs, [("motorhomes/alpa", "Alpa")])
    assert scope(Motorhome(manufacturer_range="Alpa I")) is True
    assert scope(Motorhome(manufacturer_range="Alpa")) is False


# --------------------------------------------------------------------------- #
# Wiring
# --------------------------------------------------------------------------- #


def test_manufacturer_matches_the_registry() -> None:
    """`MANUFACTURER` is the join key back to FMLV and the `ADAPTERS` key; a typo detaches
    the run from its history and hides the brand from the trigger dropdown."""
    import csv

    rows = list(csv.DictReader((Path("config") / "manufacturers.csv").open(encoding="utf-8")))
    row = next(r for r in rows if r["manufacturer_id"] == "85")
    assert row["fmlv_manufacturer"] == dethleffs.MANUFACTURER == "Dethleffs"
    assert row["fmlv_display_name"] == dethleffs.MANUFACTURER_DISPLAY_NAME
    assert row["ncc_supplier_name"] == "Dethleffs"


# --------------------------------------------------------------------------- #
# Floorplans — one per layout, and never a neighbour's
# --------------------------------------------------------------------------- #


def test_the_layouts_own_floorplan_is_the_one_taken() -> None:
    """Every layout page has one, filed under the German `grundrisse`."""
    assert dethleffs.parse_floorplan(_read("floorplans_just_van_t1")) == (
        "/dethleffs/01_DE/03_bilddaten_2026-27/02_wohnmobile/just-van/grundrisse"
        "/image-thumb__202664__wls-det-view-w-markers/just-van-t-001_2000x1000.png"
    )


@pytest.mark.parametrize(
    ("fixture_name", "expected", "would_have_been"),
    [
        # The page shows the whole range's plans in a variant selector, and the T-16's
        # comes first. Taking the first image would have handed the T-46 the T-16's layout.
        (
            "floorplans_globebus_performance_4x4_t46",
            "globebus-performance-t-46_2026_v2.svg",
            "globebus-performance-t-16_2026_v2.svg",
        ),
        # Here the first is not even a layout: `xl_family_sg-umbau.svg` is a seating-group
        # conversion diagram.
        (
            "floorplans_xl_a_6822_2",
            "xl_a_6822_2_2000x1000.png",
            "xl_family_sg-umbau.svg",
        ),
    ],
)
def test_a_neighbours_floorplan_is_never_taken(
    fixture_name: str, expected: str, would_have_been: str
) -> None:
    """The failure this guards against is silent and looks like success.

    A page carries up to sixteen plans — the other layouts in the range, and a related-range
    teaser — and only one is the layout's own. A reviewer reads a kitchen position off
    whatever they are shown and records it as fact, so the wrong drawing is worse than none
    at all. `m-model-variants__img` and `m-productteaser__img` are what tell them apart.
    """
    html = _read(fixture_name)

    picked = dethleffs.parse_floorplan(html)

    assert picked is not None
    assert picked.rsplit("/", 1)[-1] == expected
    assert would_have_been in html  # the trap is really in the page, not imagined
    assert would_have_been not in picked


def test_a_page_with_no_floorplan_offers_none() -> None:
    assert dethleffs.parse_floorplan("<html><body>no plans here</body></html>") is None


def test_the_floorplan_becomes_a_pointer_on_every_positional_field() -> None:
    """The reviewer's five questions, each linked to the drawing that answers it.

    Requested 9 September 2026, on finding Dethleffs offered none: *"all of them have floor
    plans, I believe, but the floor plan hasn't been offered in the review."* It had never
    been wired — Dethleffs predates the pattern.
    """
    layout = replace(
        dethleffs.parse_layout(
            "https://www.dethleffs.co.uk/motorhomes/just-van/t-1", _read("just_van_t1")
        ),
        floorplan_path="/dethleffs/some/grundrisse/just-van-t-001.png",
    )

    provenance = dethleffs._build_extracted_motorhome(layout).provenance

    pointers = {
        name: entry for name, entry in provenance.items() if entry.reviewer_reference
    }
    assert set(pointers) == {
        "sleeping_area",
        "kitchen_location",
        "lounge_location",
        "bathroom_layout",
        "bed_types",
    }
    for name, entry in pointers.items():
        assert entry.source_url == (
            "https://www.dethleffs.co.uk/dethleffs/some/grundrisse/just-van-t-001.png"
        ), name
        assert entry.snippet.startswith(layout.label), name


def test_no_floorplan_means_no_pointers() -> None:
    """A layout page that stops publishing one must not leave a dead link behind."""
    layout = replace(
        dethleffs.parse_layout(
            "https://www.dethleffs.co.uk/motorhomes/just-van/t-1", _read("just_van_t1")
        ),
        floorplan_path=None,
    )

    provenance = dethleffs._build_extracted_motorhome(layout).provenance

    assert not [entry for entry in provenance.values() if entry.reviewer_reference]


# --------------------------------------------------------------------------- #
# Habitation: what the page's own wording settles, reported as findings
# --------------------------------------------------------------------------- #


def test_the_heater_fitted_as_standard_is_read_and_the_optional_one_is_not(
    layouts: dict[str, DethleffsLayout],
) -> None:
    """The whole reason `parse_standard_equipment` tracks the sub-heading.

    Globetrail's standard heater is a 4 kW hot-air unit and its options include a `Diesel
    heater Combi 6D`. `Combi` is settled warm-air vocabulary, so an undivided read of the
    table would quote the option — a heater the buyer may not have — as the evidence.
    """
    layout = layouts["globetrail_540_dr"]

    assert layout.features["heating"].value is Heating.BLOWN_AIR
    assert "Hot air heating 4 kW" in layout.features["heating"].snippet
    assert "Combi" not in layout.features["heating"].snippet
    assert not any("Combi" in line for line in dethleffs.parse_standard_equipment(
        _read("globetrail_540_dr")
    ))


def test_hot_air_and_hot_water_heating_are_told_apart(
    layouts: dict[str, DethleffsLayout],
) -> None:
    """One word decides it, and Dethleffs use both phrases on neighbouring ranges.

    Globebus: "Gas hot air heating 6kW … and hot water boiler" — a hot-air heater whose
    boiler serves the taps. Alpa: "Hot-water heating with boiler, automatic drain valve
    and shut-off valve for the sleeping area", and XL A adds "Heat exchanger for hot-water
    heating" — a water-borne system, zoned and drainable.
    """
    assert layouts["globebus_active_i1"].features["heating"].value is Heating.BLOWN_AIR
    assert layouts["alpa_a_6820_2"].features["heating"].value is Heating.WET_CENTRAL
    assert layouts["xl_a_7872_2_family"].features["heating"].value is Heating.WET_CENTRAL


def test_every_captured_layout_answers_its_heating(
    layouts: dict[str, DethleffsLayout],
) -> None:
    """54 of 54 on the live site, 9 September 2026 — the field was blank on all of them
    until `hot air` was added to the shared warm-air vocabulary."""
    unanswered = [name for name, layout in layouts.items() if "heating" not in layout.features]

    assert unanswered == []


def test_the_refrigerator_row_is_what_makes_a_fridge_freezer(
    layouts: dict[str, DethleffsLayout],
) -> None:
    """The requester found this one: Globebus Active I 1 went out asserting no fridge.

    Dethleffs never write the word "fridge" in an equipment list. The only mention is a
    specification row, `Refrigerator volume (thereof freezer), approx. 137 (15)`, and the
    parenthesis is the freezer's 15 litres — which is what makes it a fridge freezer
    rather than a fridge.
    """
    layout = layouts["globebus_active_i1"]

    assert layout.features["refrigeration"].value is Refrigeration.FRIDGE_FREEZER
    assert "thereof freezer" in layout.features["refrigeration"].snippet
    # The campervans publish no such row, and nothing is invented for them.
    assert "refrigeration" not in layouts["globetrail_540_dr"].features


def test_the_beds_come_from_the_summary_not_the_range_prose(
    layouts: dict[str, DethleffsLayout],
) -> None:
    """The page describes every layout in the range; only `og:description` is this one's.

    Globebus Active I 1's summary says "a transverse double bed". Further down, the same
    page says "The practical single beds have a length of 195 cm" and labels it `(I 4)`.
    Reading the prose would give this layout its neighbour's beds.
    """
    layout = layouts["globebus_active_i1"]

    assert layout.features["bed_types"].value == [BedType.TRANSVERSE]
    assert "transverse double bed" in layout.features["bed_types"].snippet


def test_a_microwave_nobody_mentions_is_reported_as_absent(
    layouts: dict[str, DethleffsLayout],
) -> None:
    """The requester's ruling for this one field, against the usual rule on silence.

    `microwave` appears on none of the 54 layout pages and nowhere in the 160-page MY2027
    GB technical-data PDF, which does itemise an oven where one is fitted.
    """
    for name, layout in layouts.items():
        assert layout.microwave_absence is not None, name

    product = dethleffs._build_extracted_motorhome(layouts["just_van_t1"]).motorhome
    assert product.microwave is False


def test_a_stated_microwave_stops_the_absence_being_asserted() -> None:
    """A mention anywhere is enough, an options list included: reporting No against a
    microwave the page names would be a false statement rather than a silence."""
    assert dethleffs.microwave_absence_note(["Kitchen: Microwave oven"]) is None
    assert dethleffs.microwave_absence_note(["Kitchen: Oven in the floor units"]) is not None


def test_each_habitation_reading_quotes_the_line_that_settled_it(
    layouts: dict[str, DethleffsLayout],
) -> None:
    """A finding is only useful with its evidence — see `product_model.findings`."""
    extracted = dethleffs._build_extracted_motorhome(layouts["alpa_a_6820_2"])

    for field in ("heating", "refrigeration", "microwave"):
        entry = extracted.provenance[field]
        assert entry.source_url == layouts["alpa_a_6820_2"].url
        assert entry.snippet.startswith(layouts["alpa_a_6820_2"].label)
        assert not entry.reviewer_reference  # a statement, not a pointer at a drawing


def test_a_published_storage_opening_is_what_makes_a_rear_garage(
    layouts: dict[str, DethleffsLayout],
) -> None:
    """The requester's ruling, 2 September 2026: under-bed storage is not a rear garage.

    All 36 motorhomes publish `Measurement storage opening right/left (W x H)` — the
    external hatch. The 12 Globetrail campervans publish neither: their under-bed space is
    loaded through the rear doors. The site's *prose* calls that a rear garage and its
    equipment list calls it "rear storage space with 4 integrated lashing eyes"; the
    specification row is the specific source and it wins.
    """
    assert layouts["globebus_active_i1"].rear_garage is True
    assert layouts["just_van_t1"].rear_garage is True
    assert layouts["alpa_a_6820_2"].rear_garage is True
    assert layouts["globetrail_540_dr"].rear_garage is False
    assert layouts["globetrail_performance_600_dr_classic"].rear_garage is False


def test_the_rear_garage_quotes_the_opening_or_says_there_is_none(
    layouts: dict[str, DethleffsLayout],
) -> None:
    """It is a proposed value, so the reviewer decides it — with the measurement in hand."""
    with_garage = dethleffs._build_extracted_motorhome(layouts["globebus_active_i1"])
    without = dethleffs._build_extracted_motorhome(layouts["globetrail_540_dr"])

    assert with_garage.motorhome.rear_garage is True
    assert "75 x 100" in with_garage.provenance["rear_garage"].snippet
    assert without.motorhome.rear_garage is False
    assert "no storage-opening row" in without.provenance["rear_garage"].snippet
