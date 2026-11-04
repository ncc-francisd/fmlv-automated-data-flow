"""The FMLV motorhome/campervan export schema.

Column order here is taken verbatim from a real NCC export
(`csv-examples/.../motorhome-campervans.xlsx`) and must be preserved on upload.

The field guide splits these columns into classes that behave very differently, and
the pipeline treats them differently as a result:

* ``CARRY_THROUGH`` — marked "PLEASE Leave as is!". Read from the current export and
  written back untouched. Never extracted, never diffed.
* ``REQUIRED`` — must be present for a row to be valid on upload.
* ``LAYOUT`` — the ~40 Yes/No columns, modelled internally as the enums in `enums.py`.
* ``DEALER_ONLY`` — "LEAVE BLANK UNLESS DEALER EXCLUSIVE". Not available from
  manufacturer sites, so out of scope for scraping.
"""

from __future__ import annotations

import csv

from .. import paths
from .enums import (
    BathroomLayout,
    BedType,
    BodyType,
    Heating,
    KitchenLocation,
    LoungeLocation,
    Refrigeration,
    SleepingArea,
)

#: Exact column order of the motorhome/campervan export. Do not reorder.
COLUMNS: tuple[str, ...] = (
    "product_id",
    "year",
    "manufacturing_release_date",
    "manufacturer",
    "base_vehicle_manufacturer",
    "manufacturer_display_name",
    "manufacturer_range",
    "dealer_specials_range",
    "dealer",
    "model",
    "dealer_model_variant",
    *BodyType.columns(),
    "mh_passenger_seats_inc_driver",
    "berths",
    "rrp_pounds",
    "price_min_range_pounds",
    "price_max_range_pounds",
    "mro_kilograms",
    "mtplm_kilograms",
    "mh_payload_kilograms",
    "mh_length_mm",
    "mh_width_mm",
    "mh_height_mm",
    *SleepingArea.columns(),
    *BedType.columns(),
    *KitchenLocation.columns(),
    *BathroomLayout.columns(),
    # Not a member of that group — the washroom's construction, not its location or
    # provision, so it is not an alternative to any of them. Listed here to keep the
    # column in the exact position FMLV's template has it. See `BathroomLayout`.
    "separate_shower_toilet",
    *LoungeLocation.columns(),
    *Heating.columns(),
    "rear_garage",
    *Refrigeration.columns(),
    "microwave",
    "automatic_mro_kilograms",
    "automatic_mh_payload_kilograms",
    "automatic_rrp_pounds",
    "automatic_price_min_range_pounds",
    # Added by Steadfast on 3 November 2026, and **inserted here rather than appended**:
    # everything below it moved one column to the right. Keeping our order identical to
    # theirs is what makes the upload safe whether the site matches the header by name or
    # by position, which we have never established. See `Motorhome.automatic_available`.
    "automatic_available",
    "latest_model_id",
    "images",
    "archived",
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

#: Guide: "REQUIRED FIELD".
REQUIRED: frozenset[str] = frozenset(
    {
        "manufacturer",
        "base_vehicle_manufacturer",
        "manufacturer_display_name",
        "manufacturer_range",
        "model",
        "mh_passenger_seats_inc_driver",
        "berths",
        "rrp_pounds",
        "mro_kilograms",
        "mtplm_kilograms",
        "mh_payload_kilograms",
        "mh_length_mm",
        "mh_width_mm",
        "mh_height_mm",
    }
)

#: Guide: "LEAVE BLANK UNLESS DEALER EXCLUSIVE". Not scraped.
DEALER_ONLY: frozenset[str] = frozenset(
    {"dealer_specials_range", "dealer", "dealer_model_variant"}
)

def _load_in_scope() -> frozenset[str]:
    """Read the field guide's `automated_collection_scope_flag` column for `in_scope` rows.

    Loaded from `config/field_guide_motorhome.csv` at import time, rather than
    hand-copied here, so a reviewer can change what's in scope by editing that one
    column without touching code.
    """
    with paths.field_guide_path().open(newline="", encoding="utf-8-sig") as handle:
        return frozenset(
            row["field_name"]
            for row in csv.DictReader(handle)
            if row.get("automated_collection_scope_flag", "").strip() == "in_scope"
        )


#: Every run must attempt these — if an adapter can't find one on a matched
#: (existing) product, that's surfaced to the reviewer as "confirm or replace"
#: rather than silently left unchecked. See `diff.compare.compare_fields`.
IN_SCOPE: frozenset[str] = _load_in_scope()


#: Columns this schema knows but the **live** FMLV upload template does not carry yet.
#:
#: `automatic_available` is column BN of the template Steadfast have built but not yet
#: released. Until they do, an upload carrying it has one column too many and the site
#: rejects the file, so the reviewer was deleting column BN out of every upload by hand
#: before sending it — a step that has to be done exactly right on a 69-column sheet.
#:
#: Holding it back here instead means the column is read from an export the moment one
#: carries it, is proposed and reviewed as normal, and is simply not written out. **When
#: Steadfast go live, empty this set** — that is the whole switch, and the tests in
#: `tests/product_model/test_io.py` describe both states.
NOT_YET_IN_UPLOAD_TEMPLATE: frozenset[str] = frozenset({"automatic_available"})

#: The columns an upload actually carries, in `COLUMNS` order.
UPLOAD_COLUMNS: tuple[str, ...] = tuple(
    column for column in COLUMNS if column not in NOT_YET_IN_UPLOAD_TEMPLATE
)

#: The Yes/No layout columns, all of which map into an enum group.
LAYOUT: frozenset[str] = frozenset(
    [
        *BodyType.columns(),
        *SleepingArea.columns(),
        *BedType.columns(),
        *KitchenLocation.columns(),
        *BathroomLayout.columns(),
        "separate_shower_toilet",
        *LoungeLocation.columns(),
        *Heating.columns(),
        *Refrigeration.columns(),
        "rear_garage",
        "microwave",
    ]
)

#: All-or-nothing group describing the automatic-gearbox variant, where one exists.
AUTOMATIC: tuple[str, ...] = (
    "automatic_mro_kilograms",
    "automatic_mh_payload_kilograms",
    "automatic_rrp_pounds",
    "automatic_price_min_range_pounds",
)

#: Numeric columns that change often — the fields a run actually chases.
TRACKED_NUMERIC: tuple[str, ...] = (
    "rrp_pounds",
    "price_min_range_pounds",
    "price_max_range_pounds",
    "mro_kilograms",
    "mtplm_kilograms",
    "mh_payload_kilograms",
    "mh_length_mm",
    "mh_width_mm",
    "mh_height_mm",
    "berths",
    "mh_passenger_seats_inc_driver",
    *AUTOMATIC,
)

YES = "Yes"
NO = "No"
IMAGE_SEPARATOR = ", "
