"""Fleurette, one of the two brands of Fleurette Constructeur.

Built 29 October 2026. See `docs/adapters/fleurette-florium.md`. FMLV manufacturer
**`Fleurette Constructeur`**, display name **`Fleurette`**. **Motorhomes only** — the van
conversions are Florium's Black Pearl and Fleurette have no equivalent.

## Why there are two modules over one reader

`MANUFACTURER` is the company and is shared with `florium.py`, exactly as `swift.py`,
`bessacarr.py` and `ace.py` share `Swift Group Ltd`. `ADAPTERS` keys on the display name
alongside it, so the two register separately, take separate `--range` arguments and diff
against separate NCC exports, while `fleurette_florium.py` reads the one catalogue whose
every technical column is headed with both brands at once.

Thirteen layouts across four ranges. The Florium twin of each is in `florium.py`, which
also carries the four Black Pearls that make its total seventeen.

## The price is manually sourced, and is the whole reason this is buildable

Fleurette publish **no price on any website** — not on the model pages, not in the
44-page catalogue, not in 7,252 sitemap URLs. The survey on 14 October 2026 stopped here.
What unblocked it was four UK price lists emailed by Léa Timores on 28 October, headed
*"2027 Recommended Retail Prices (£) with VAT + Transport — OTR — valid from the 1st July
2026"*: sterling, on-the-road, and covering every layout.

They are on no website, so no run can rediscover them. `PRICES` is therefore a constant,
read once and said to be so in provenance, on the `joa.py` pattern — **re-verify at the
model-year changeover**.

**Six layouts cost more than their Florium twin** because Fleurette fit a `Wellness`
specification Florium do not. Where neither brand does, the two are priced identically:
`60LG` £68,690 and `64LDF` £70,990 in both lists, `67LO` £74,390 in both. So the
catalogue's "same vehicle, two veneers" holds for seven layouts and not for six — and
`Wellness` still stays out of the model name, because the technical table and the price
list both file these layouts under Migrateur, Magister and Discover. See
`fleurette_florium.py`.

## Two prices per layout, and which is the base

Every Fiat coachbuilt is listed twice, manual and automatic, £2,800–£2,900 apart. The
**manual** is the base vehicle, and the catalogue says so independently: page 39 marks
`Porteur FIAT Ducato : moteur Multijet 140 ch en boite manuelle` as `S` on the Migrateur
and Magister columns and the automatic as `O`.

**Discover inverts that** — its four layouts are published only `based on FIAT chassis
with automatic gearbox`, and page 39 agrees, marking the manual unavailable and the
automatic standard. So the automatic price *is* the base there, and taking "the cheaper of
two" blindly would have been wrong on exactly those four.

The **Elister** has one price for both its layouts, £102,990, on a `Sprinter Mercedes Benz
- 150 hp - Manual Transmission`; its automatic arrives inside a £3,350 Deluxe Pack and so
is an option.

## What cannot be uploaded yet, and why nothing is dropped for it

Four Discover layouts have **no mass**: the catalogue prints `NC` — *non communiqué* —
and Léa confirmed on 28 October that *"the MiRO weights for the Discover and Wincester
models will not be available until next week. Testing is currently underway."* They are
collected anyway and reach the reviewer with no mass and a pointer, because an adapter
that returns nine of thirteen products tells a reviewer the other four have been
discontinued. `vantage.py` did exactly that to two live campervans.

**The model pages publish masses for some of them and those must not be used.** Every page
carrying one is a previous model year's — the Discover 75LMF's 3134 kg sits under *"Photos
of the 2026 collection"* — while the pages marked 2027 carry none. The site is not read
here at all; see the survey document.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ..fetch.http import Fetcher
from . import fleurette_florium as shared
from .base import ExtractedMotorhome

__all__ = [
    "DEFAULT_RANGES",
    "EXPECTED_LAYOUTS",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "PRICES",
    "collect",
]

#: The company, byte for byte as the FMLV export spells it — confirmed against product
#: 9214 on 28 October 2026. **Shared with `florium.py`**, which is the point; see the
#: module docstring.
MANUFACTURER = "Fleurette Constructeur"

#: The brand. What the public sees: Nova composes a product's name from this, never from
#: `MANUFACTURER`, so a vehicle reads `Fleurette Migrateur 60LG` and never "Fleurette
#: Constructeur Migrateur 60LG".
MANUFACTURER_DISPLAY_NAME = "Fleurette"

#: Fleurette's four ranges, spelt as their own catalogue and price list spell them.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = tuple(
    (name, name) for name, _florium, _codes, _body in shared.RANGE_PAIRS
)

#: Thirteen layouts. The catalogue's own technical table is the count, and it is what
#: would notice a column going missing from a document that otherwise still parses.
EXPECTED_LAYOUTS = len(shared.SHARED_CODES)

#: `(range, layout) -> price in pounds`, from the 2027 UK price list. **Manually sourced**
#: — see the module docstring. The manual-transmission figure except on the Discover,
#: which is published automatic-only.
PRICES: dict[tuple[str, str], int] = {
    ("Migrateur", "60LG"): 68690,
    ("Migrateur", "64LDF"): 70990,
    ("Migrateur", "69LJG"): 75790,
    ("Magister", "67LO"): 74390,
    ("Magister", "70LMF"): 77890,
    ("Magister", "70LJG"): 78590,
    ("Magister", "74LMF"): 79290,
    ("Elister", "73LMF"): 102990,
    ("Elister", "73LJG"): 102990,
    ("Discover", "72LMF"): 94990,
    ("Discover", "72LJG"): 95890,
    ("Discover", "74LJG"): 107990,
    ("Discover", "75LMF"): 107090,
}

#: Named in provenance against every price.
PRICE_SOURCE = (
    "the 2027 UK price lists emailed by Fleurette on 28 October 2026 "
    "('FLEURETTE RRP GB 2027.pdf' and 'ELISTER BELIXTER RRP GB 2027.pdf'), valid from "
    "1 July 2026"
)

#: Which range each shared column belongs to, for this brand — index 0 of the pair.
_RANGE_AT: tuple[str, ...] = tuple(
    fleurette for fleurette, _florium, _body in shared.SHARED_RANGE_AT
)


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 — the catalogue is a plain PDF fetch
    snapshot_dir: Path,  # noqa: ARG001 — `http` already snapshots into it
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every Fleurette layout the catalogue vouches for, priced from the emailed lists."""
    wanted = {label for _path, label in ranges}
    columns, _vans = shared.collect_columns(http, on_progress=on_progress)

    products: list[ExtractedMotorhome] = []
    for column in columns:
        manufacturer_range = _RANGE_AT[shared.SHARED_CODES.index(column.code)]
        if manufacturer_range not in wanted:
            continue
        price = PRICES.get((manufacturer_range, column.code))
        if price is None:
            on_progress(
                f"{manufacturer_range} {column.code}: not in the 2027 UK price list, so "
                f"no price is proposed and FMLV's own figure stands"
            )
        products.append(
            shared.build_product(
                column,
                manufacturer=MANUFACTURER,
                display_name=MANUFACTURER_DISPLAY_NAME,
                manufacturer_range=manufacturer_range,
                price=price,
                price_source=PRICE_SOURCE,
            )
        )
        on_progress(
            f"read {manufacturer_range} {column.code}: {column.length_mm}mm, "
            f"{column.mro_kilograms or 'no'} kg MRO, £{price or 0:,}"
        )

    shared.narrate_unpublished(products, on_progress=on_progress)
    if len(ranges) == len(DEFAULT_RANGES) and len(products) != EXPECTED_LAYOUTS:
        on_progress(
            f"expected {EXPECTED_LAYOUTS} Fleurette layouts and built {len(products)} — "
            f"check whether the catalogue's technical table has really changed"
        )
    return products
