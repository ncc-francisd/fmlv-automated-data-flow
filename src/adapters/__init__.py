"""Manufacturer adapters, and the lookup from a registry row to the code that runs it.

Per DESIGN.md §5.1 this package is "the only manufacturer-specific code". `base.py`
defines what an adapter is; each sibling module is one. A module satisfies the
`Adapter` protocol structurally — `adria.collect` has the right shape — so an adapter
is a module here, not a class that has to be instantiated.

`ADAPTERS` is keyed by `(Manufacturer.fmlv_manufacturer, VehicleClass)` rather than by
`manufacturer_id`. The name column is required to match the FMLV export's `manufacturer`
value exactly, which makes it the same string the baseline is filtered on, and it does not
depend on the still-open question of what `manufacturer_id` actually is or whether it is
stable (TODO.md, "For Ben").

The product area is in the key because a manufacturer can need **two adapters**. FMLV keeps
motorhomes and touring caravans as separate exports with separate schemas (DESIGN.md §3),
and eight of the registered manufacturers build both — Bailey's caravans live on the same
site as its motorhomes, under different URLs, with a different spec table and a different
set of columns to fill. Those are two different collect() implementations producing two
differently-shaped products, not one adapter with a flag.

An adapter says which area it serves with a module-level `VEHICLE_CLASS`. Omitting it means
motorhomes, so the seventeen adapters written before caravans existed need no edit — the
same `getattr` opt-in `DEFAULT_RANGES` and `baseline_in_scope` use.
"""

from __future__ import annotations

from . import (
    ace,
    adria,
    atom,
    auto_sleepers,
    auto_trail,
    bailey,
    bailey_caravan,
    benimar,
    bessacarr,
    burstner,
    carado,
    chausson,
    coachman,
    dethleffs,
    elddis,
    elnagh,
    eriba,
    eriba_caravan,
    etrusco,
    hymer,
    joa,
    knaus,
    laika,
    le_voyageur,
    mclouis,
    mobilvetta,
    morelo,
    niesmann_bischoff,
    panama,
    pilote,
    moto_trek,
    murvi,
    rimor,
    sunlight,
    swift,
    swift_caravan,
    vantage,
    vantourer,
    weinsberg,
    westfalia,
    wingamm,
    wingamm_caravan,
)
from ..vehicle_class import DEFAULT as DEFAULT_VEHICLE_CLASS
from ..vehicle_class import VehicleClass
from .base import Adapter, ExtractedMotorhome, Provenance

#: Every adapter module, in the order they were written. `ADAPTERS` is derived from
#: this rather than spelled out as a dict literal, so registering one is a single edit
#: and the (manufacturer, class) key can never drift from what the module declares.
_MODULES: tuple[Adapter, ...] = (
    ace,
    adria,
    atom,
    auto_sleepers,
    auto_trail,
    bailey,
    bailey_caravan,
    benimar,
    bessacarr,
    burstner,
    carado,
    chausson,
    coachman,
    dethleffs,
    elddis,
    elnagh,
    eriba,
    eriba_caravan,
    etrusco,
    hymer,
    joa,
    knaus,
    laika,
    le_voyageur,
    mclouis,
    mobilvetta,
    morelo,
    niesmann_bischoff,
    panama,
    pilote,
    moto_trek,
    murvi,
    rimor,
    sunlight,
    swift,
    swift_caravan,
    vantage,
    vantourer,
    weinsberg,
    westfalia,
    wingamm,
    wingamm_caravan,
)


def adapter_vehicle_class(adapter: Adapter) -> VehicleClass:
    """Which FMLV product area an adapter produces, defaulting to motorhomes.

    Read with `getattr` so an adapter written before caravans existed — every one of
    the seventeen — needs no edit to keep working.
    """
    return VehicleClass(getattr(adapter, "VEHICLE_CLASS", DEFAULT_VEHICLE_CLASS))


#: Every adapter, keyed by `(fmlv_manufacturer, fmlv_display_name, VehicleClass)`.
#:
#: **The display name is in the key because `fmlv_manufacturer` is not unique.** It names
#: the legal manufacturer, and one manufacturer can own several brands, each of which FMLV
#: files under its own id with its own display name:
#:
#: | id | `fmlv_manufacturer` | display name |
#: |---|---|---|
#: | 26 | `Swift Group Ltd` | Swift |
#: | 228 | `Swift Group Ltd` | Bessacarr |
#: | 264 | `Swift Group Ltd` | **Ace Motorhomes** |
#: | 187 | `Trigano` | Silver |
#: | 222 | `Trigano` | Mini Freestyle |
#: | 278 | `Trigano` | **Atom** |
#:
#: Keyed on the manufacturer alone, a second brand's adapter would overwrite the first and
#: one of them would become unreachable — `swift.py` and `ace.py` both declaring
#: `Swift Group Ltd` for motorhomes. `registry.loader` cross-checks duplicate
#: `manufacturer_id`s and `website_url`s, but not duplicate `fmlv_manufacturer`, so nothing
#: else would have warned.
#:
#: The product area stays in the key for the reason it always was: one brand can need two
#: adapters, one per area, as Bailey and Eriba do.
ADAPTERS: dict[tuple[str, str, VehicleClass], Adapter] = {
    (
        module.MANUFACTURER,
        module.MANUFACTURER_DISPLAY_NAME,
        adapter_vehicle_class(module),
    ): module
    for module in _MODULES
}

__all__ = [
    "ADAPTERS",
    "Adapter",
    "ExtractedMotorhome",
    "Provenance",
    "adapter_for",
    "adapter_vehicle_class",
    "adapters_for",
    "ace",
    "adria",
    "atom",
    "auto_sleepers",
    "auto_trail",
    "bailey",
    "bailey_caravan",
    "benimar",
    "bessacarr",
    "burstner",
    "carado",
    "chausson",
    "coachman",
    "dethleffs",
    "elddis",
    "elnagh",
    "eriba",
    "eriba_caravan",
    "etrusco",
    "hymer",
    "joa",
    "knaus",
    "laika",
    "le_voyageur",
    "mclouis",
    "mobilvetta",
    "morelo",
    "niesmann_bischoff",
    "panama",
    "pilote",
    "moto_trek",
    "murvi",
    "rimor",
    "sunlight",
    "swift",
    "swift_caravan",
    "vantage",
    "vantourer",
    "weinsberg",
    "westfalia",
    "wingamm",
    "wingamm_caravan",
]


def adapter_for(
    fmlv_manufacturer: str,
    vehicle_class: VehicleClass = DEFAULT_VEHICLE_CLASS,
    *,
    display_name: str | None = None,
) -> Adapter | None:
    """The adapter for one manufacturer's product area, or `None` if nobody wrote one.

    Returning `None` rather than raising keeps "we have no adapter for this brand" a
    normal, reportable state — a sweep across the whole registry has to skip most
    manufacturers for exactly this reason until Phase 4's remaining adapters land. It is
    also the normal answer for "Bailey, but caravans" until that adapter exists, which is
    why `vehicle_class` defaults rather than being required.

    **`display_name` is only needed where a manufacturer owns more than one brand**, which
    is why it is optional and keyword-only: `Swift Group Ltd` is Swift, Bessacarr *and* Ace
    Motorhomes, and `Trigano` is Silver, Mini Freestyle and Atom. Where one adapter answers
    to the manufacturer it is returned without one, so every caller that never had a brand
    to disambiguate keeps working. Where several do and none is named, the answer is `None`
    rather than an arbitrary pick — silently running Swift's adapter for Ace would produce
    a full set of plausible, wrong proposals against real `product_id`s.
    """
    wanted = VehicleClass(vehicle_class)
    candidates = {
        registered_name: adapter
        for (manufacturer, registered_name, registered_class), adapter in ADAPTERS.items()
        if manufacturer == fmlv_manufacturer and registered_class == wanted
    }
    if display_name is not None and display_name in candidates:
        return candidates[display_name]
    if len(candidates) == 1:
        return next(iter(candidates.values()))
    return None


def adapters_for(
    fmlv_manufacturer: str, *, display_name: str | None = None
) -> dict[VehicleClass, Adapter]:
    """Every product area this manufacturer has an adapter for.

    For the review app's trigger page, which has to offer "Bailey motorhomes" and "Bailey
    caravans" as separate choices rather than one "Bailey" that silently means whichever
    adapter was registered.
    """
    return {
        registered_class: adapter
        for (manufacturer, registered_name, registered_class), adapter in ADAPTERS.items()
        if manufacturer == fmlv_manufacturer
        and (display_name is None or registered_name == display_name)
    }
