"""The manufacturer registry data model.

One `Manufacturer` per row of `config/manufacturers.csv` — who to visit, where, and in
what shape. See `config/manufacturers.README.md` for the column-by-column field guide.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..vehicle_class import DEFAULT as DEFAULT_VEHICLE_CLASS
from ..vehicle_class import VehicleClass


class Status(str, Enum):
    """Whether a manufacturer participates in scheduled sweeps."""

    ACTIVE = "active"
    PAUSED = "paused"  # skip in scheduled sweeps, still runnable manually
    RETIRED = "retired"  # brand no longer trading


class TriState(str, Enum):
    """yes / no / unknown — used where the answer is genuinely undiscovered yet."""

    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Manufacturer:
    """One manufacturer, as recorded in the registry.

    `manufacturer_id` is the NCC-assigned identifier Ben has populated the registry
    with — not a slug we invented (see the open question this raised in TODO.md about
    confirming what system it comes from). `ncc_supplier_name` is a separate identity
    again: the exact label this manufacturer has in the NCC site's own "Export Products
    by Supplier" dropdown (`fetch/ncc.py`), which doesn't always match
    `fmlv_manufacturer` (e.g. `"Adria Mobil"` vs `"Adria Caravans & Motorhomes"`).

    **One brand can have two supplier labels, one per product area.** Every dual-area
    manufacturer up to Coachman had a single label covering both — `Bailey of Bristol`
    returns the motorhome and caravan sheets together — so `ncc_supplier_name` alone was
    enough. The NCC list Coachman twice, as `Coachman Motorhomes` and `Coachman
    Caravans`, for historic reasons, and the caravans are reachable only under the
    second. `ncc_supplier_name_caravan` holds it; blank means the one label serves both,
    which is still the normal case. Read it through `supplier_name_for`, never directly.
    """

    manufacturer_id: int
    fmlv_manufacturer: str
    fmlv_display_name: str | None
    categories: tuple[str, ...]
    status: Status
    pilot_priority: int | None
    country: str | None
    website_url: str
    uk_site_url: str | None
    models_index_url: str | None
    price_list_url: str | None
    brochure_url: str | None
    ncc_supplier_name: str | None
    ncc_supplier_name_caravan: str | None
    specs_format: str
    needs_javascript: TriState
    login_required: bool
    ncc_member: bool | None
    contact_name: str | None
    contact_email: str | None
    contact_phone: str | None
    last_verified: str | None
    notes: str | None

    def supplier_name_for(
        self, vehicle_class: VehicleClass = DEFAULT_VEHICLE_CLASS
    ) -> str | None:
        """The "Export Products by Supplier" label that reaches this product area.

        Falls back to `ncc_supplier_name` whenever no area-specific label is recorded,
        which is every manufacturer but Coachman: one supplier entry returning both
        sheets is still the normal arrangement, and this must not change their
        behaviour.
        """
        if (
            VehicleClass(vehicle_class) is VehicleClass.CARAVAN
            and self.ncc_supplier_name_caravan
        ):
            return self.ncc_supplier_name_caravan
        return self.ncc_supplier_name

    @property
    def splits_suppliers_by_area(self) -> bool:
        """Whether the two product areas come from two different supplier entries.

        The reason this is worth a name: a split supplier's export still contains
        *both* sheets, and the off-area one is not a baseline — `Coachman Caravans`
        returns a two-row motorhome sheet against the thirteen `Coachman Motorhomes`
        holds. `cli.fetch_export` discards it on the strength of this.
        """
        return bool(
            self.ncc_supplier_name_caravan
            and self.ncc_supplier_name
            and self.ncc_supplier_name_caravan != self.ncc_supplier_name
        )

    @property
    def includes_motorhomes(self) -> bool:
        """Whether this manufacturer is in scope for a motorhome run.

        The prototype is motorhome-only (see DESIGN.md §3). A manufacturer with no
        `categories` recorded yet is included by default — nothing to exclude on —
        rather than silently skipped; a `categories_unset` issue is still raised at
        load time so the gap gets noticed and filled in.
        """
        if not self.categories:
            return True
        return "motorhome" in self.categories

    @property
    def is_runnable(self) -> bool:
        return self.status == Status.ACTIVE

    @property
    def crawl_entry_point(self) -> str | None:
        """The best URL to start a crawl from, preferring the most specific one known."""
        return self.models_index_url or self.uk_site_url or self.website_url
