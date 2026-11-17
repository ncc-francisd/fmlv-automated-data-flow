"""The FMLV touring-caravan export schema.

The sibling of `schema.py`. Column order is taken verbatim from a real NCC export
(`data/exports/28_Bailey/…_touring-caravans.xlsx`, 81 products, cross-checked against
Adria's 11) and must be preserved on upload.

**Where it differs from the motorhome schema** — 62 columns against 68, and the overlap
is less than the count suggests:

* **No base vehicle.** A caravan is towed, so `base_vehicle_manufacturer`,
  `mh_passenger_seats_inc_driver` and the four `automatic_*` gearbox columns have no
  caravan equivalent. `rear_garage` and `sleeping_area_separate_childrens_area` are gone
  too.
* **Different body types** — rigid/folding/pop-up/micro rather than the eight
  campervan and coachbuilt shapes (`enums.CaravanBodyType`).
* **Renamed dimensions.** `mh_length_mm`/`mh_width_mm`/`mh_height_mm` become
  `exterior_body_length_mm`/`overall_width_mm`/`height_mm`.
* **Four lengths, not one**, and telling them apart matters more than the names admit:
  `internal_length_mm` is the habitable space; `exterior_body_length_mm` is the body;
  `shipping_length_mm` adds the towing hitch, so it is always the larger of the two (by
  845-1500mm across Bailey's range); and `awning_length_mm` is the awning rail
  measurement rather than a vehicle dimension at all, running to 11557mm on a van less
  than half that long. Mapping shipping and exterior body the wrong way round would be
  quiet, plausible and wrong on every product at once.
* **Split payload.** There is no single payload column. `mtplm - mro` is
  `personal_effects_payload_kilograms` plus `optional_equipment_payload_kilograms`, and
  the latter is populated on **none** of the 92 real caravan products this project holds
  — so in practice the check is `mtplm - mro == personal_effects`.
* **Two extras with no motorhome counterpart**: `twin_axle` and `headroom_mm`.
"""

from __future__ import annotations

import csv

from .. import paths
from ..vehicle_class import VehicleClass
from .enums import (
    BathroomLayout,
    BedType,
    CaravanBodyType,
    CaravanSleepingArea,
    Heating,
    KitchenLocation,
    LoungeLocation,
    Refrigeration,
)

#: Bed types and kitchen locations in the order the *caravan* export lists them, which
#: is not the order the motorhome export uses — beds run make-up/fixed/bunks/separate/
#: island/transverse here against make-up/fixed/transverse/island/separate/bunks there,
#: and kitchens side/rear/corner against rear/side/corner.
#:
#: The members are identical, so the enums are shared; only the column *order* differs,
#: and that belongs to the schema rather than the enum. Spelled out rather than sorted
#: from the enum so the contract with the importer is visible, and checked below for
#: completeness so adding an enum member cannot silently drop a column.
_BED_TYPE_COLUMNS: tuple[str, ...] = (
    "make_up_beds",
    "fixed_bed",
    "fixed_bunks",
    "fixed_separate_beds",
    "island_bed",
    "transverse_bed",
    "drop_down_bed",
)

_KITCHEN_COLUMNS: tuple[str, ...] = ("side_kitchen", "rear_kitchen", "corner_kitchen")

assert set(_BED_TYPE_COLUMNS) == set(BedType.columns()), (
    "caravan bed-type columns have drifted from the BedType enum"
)
assert set(_KITCHEN_COLUMNS) == set(KitchenLocation.columns()), (
    "caravan kitchen columns have drifted from the KitchenLocation enum"
)

#: Exact column order of the touring-caravan export. Do not reorder.
#:
#: Note `mtplm_kilograms` precedes `mro_kilograms` here and follows it in the motorhome
#: export. Harmless while both are written by name, and exactly the sort of thing that
#: stops being harmless the moment anyone writes a row positionally.
COLUMNS: tuple[str, ...] = (
    "product_id",
    "year",
    "manufacturing_release_date",
    "manufacturer",
    "manufacturer_display_name",
    "manufacturer_range",
    "dealer_specials_range",
    "dealer",
    "model",
    "dealer_model_variant",
    *CaravanBodyType.columns(),
    "berths",
    "rrp_pounds",
    "price_min_range_pounds",
    "price_max_range_pounds",
    "mtplm_kilograms",
    "mro_kilograms",
    "optional_equipment_payload_kilograms",
    "personal_effects_payload_kilograms",
    "internal_length_mm",
    "overall_width_mm",
    "exterior_body_length_mm",
    "shipping_length_mm",
    "height_mm",
    "awning_length_mm",
    "twin_axle",
    "headroom_mm",
    *CaravanSleepingArea.columns(),
    *_BED_TYPE_COLUMNS,
    *_KITCHEN_COLUMNS,
    *BathroomLayout.columns(),
    # Not a member of that group — the washroom's construction, not its location or
    # provision, so it is not an alternative to any of them. Listed here to keep the
    # column in the exact position FMLV's template has it. See `BathroomLayout`.
    "separate_shower_toilet",
    *LoungeLocation.columns(),
    *Heating.columns(),
    *Refrigeration.columns(),
    "microwave",
    "latest_model_id",
    "images",
    "archived",
    # Appended past the end of FMLV's own template, deliberately — see
    # OUTSIDE_FMLV_TEMPLATE.
    "max_nose_weight_kilograms",
)

#: Columns that exist for us and **never** for FMLV. FMLV has no maximum nose weight
#: field and is not getting one — the figure is for the TowCheck sister site — so it is
#: held out of `UPLOAD_COLUMNS`, which must stay FMLV's own template exactly.
#:
#: Distinct from the motorhome schema's `NOT_YET_IN_UPLOAD_TEMPLATE`, which holds back a
#: column Steadfast have built but not released: that one is temporary and is kept out of
#: *both* files so nobody pastes it in early. This one is permanent, and it is **not**
#: kept out of the generated file — see `GENERATED_COLUMNS`.
OUTSIDE_FMLV_TEMPLATE: frozenset[str] = frozenset({"max_nose_weight_kilograms"})

#: FMLV's own upload template, exactly: 62 columns ending at `archived` in column BJ.
#: Nothing may be added to this, reordered within it or removed from it — see
#: `GENERATED_COLUMNS` for where our own columns go instead.
UPLOAD_COLUMNS: tuple[str, ...] = tuple(
    column for column in COLUMNS if column not in OUTSIDE_FMLV_TEMPLATE
)

#: A column with no field behind it: a blank header and a blank cell on every row.
#: `caravan_io.write_csv` writes one wherever this appears in its `columns`.
SPACER_COLUMN = ""

#: What a run's generated CSVs actually carry — **both** of them, the upload and the
#: readable copy alike. FMLV's 62 template columns, then two spacers, then our own.
#:
#: **The nose weight lands in column BM**, which is where the requester keeps it
#: (17 November 2026) and saves him transposing it by hand out of BK. The two blank
#: columns are a deliberate buffer: Steadfast's export already carries an `active` column
#: in BK that the template does not, so putting ours hard against `archived` would park
#: it exactly where FMLV's own next column is most likely to land.
#:
#: **This rests on FMLV's importer reading only as far as BJ** — the requester's
#: understanding, not something this repo can prove, and the first upload carrying these
#: columns must be checked against FMLV before the rest of the caravan adapters follow.
#: If it turns out the importer does not tolerate them, the upload goes back to
#: `UPLOAD_COLUMNS` and only the readable copy keeps the nose weight.
GENERATED_COLUMNS: tuple[str, ...] = (
    *UPLOAD_COLUMNS,
    SPACER_COLUMN,
    SPACER_COLUMN,
    "max_nose_weight_kilograms",
)

#: Written back exactly as read. Guide: "PLEASE Leave as is!"
CARRY_THROUGH: frozenset[str] = frozenset(
    {
        "product_id",
        "year",
        "manufacturing_release_date",
        "latest_model_id",
        "images",
        "archived",
    }
)

#: Guide: "REQUIRED FIELD". No `base_vehicle_manufacturer` and no passenger seats, and
#: `personal_effects_payload_kilograms` takes the place the motorhome payload held.
#:
#: `exterior_body_length_mm` is deliberately **not** required, despite being a dimension
#: every other schema would treat as fundamental. Bailey quote internal and shipping
#: length and nothing between them, FMLV itself holds it blank on 5 of Bailey's 27 live
#: products, and the requester reads that as an industry trend rather than one brand's
#: omission (3 September 2026). Marking it required would raise an error against FMLV's
#: own current data on every run.
REQUIRED: frozenset[str] = frozenset(
    {
        "manufacturer",
        "manufacturer_display_name",
        "manufacturer_range",
        "model",
        "berths",
        "rrp_pounds",
        "mtplm_kilograms",
        "mro_kilograms",
        "personal_effects_payload_kilograms",
        "internal_length_mm",
        "overall_width_mm",
        "shipping_length_mm",
        "height_mm",
        "awning_length_mm",
        "headroom_mm",
    }
)

#: Guide: "LEAVE BLANK UNLESS DEALER EXCLUSIVE". Not scraped.
DEALER_ONLY: frozenset[str] = frozenset(
    {"dealer_specials_range", "dealer", "dealer_model_variant"}
)


def _load_in_scope() -> frozenset[str]:
    """Read `config/field_guide_caravan.csv`'s scope column, as `schema.py` does its own."""
    with paths.field_guide_path(VehicleClass.CARAVAN).open(
        newline="", encoding="utf-8-sig"
    ) as handle:
        return frozenset(
            row["field_name"]
            for row in csv.DictReader(handle)
            if row.get("automated_collection_scope_flag", "").strip() == "in_scope"
        )


#: Every run must attempt these — see `schema.IN_SCOPE`.
IN_SCOPE: frozenset[str] = _load_in_scope()

#: The Yes/No layout columns, all of which map into an enum group or a plain bool.
#:
#: `twin_axle` sits here rather than with the dimensions despite being a chassis fact:
#: it is a Yes/No column, it is what `diff.compare` needs to treat as a layout-priority
#: change, and it behaves exactly like `microwave` does on the motorhome side.
LAYOUT: frozenset[str] = frozenset(
    [
        *CaravanBodyType.columns(),
        *CaravanSleepingArea.columns(),
        *BedType.columns(),
        *KitchenLocation.columns(),
        *BathroomLayout.columns(),
        "separate_shower_toilet",
        *LoungeLocation.columns(),
        *Heating.columns(),
        *Refrigeration.columns(),
        "twin_axle",
        "microwave",
    ]
)

#: Numeric columns that change often — the fields a run actually chases.
#: `optional_equipment_payload_kilograms` is deliberately absent: it is out of scope in
#: the field guide and unpopulated on every real caravan product this project holds.
TRACKED_NUMERIC: tuple[str, ...] = (
    "rrp_pounds",
    "price_min_range_pounds",
    "price_max_range_pounds",
    "mtplm_kilograms",
    "mro_kilograms",
    "personal_effects_payload_kilograms",
    "internal_length_mm",
    "overall_width_mm",
    "exterior_body_length_mm",
    "shipping_length_mm",
    "height_mm",
    "awning_length_mm",
    "headroom_mm",
    "berths",
)
