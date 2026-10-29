"""Florium, the other brand of Fleurette Constructeur, and the one with the vans.

Built 29 October 2026. See `docs/adapters/fleurette-florium.md`. FMLV manufacturer
**`Fleurette Constructeur`**, display name **`Florium`**.

`MANUFACTURER` is shared with `fleurette.py` — the `Swift Group Ltd` arrangement, where
`ADAPTERS` keys on the display name alongside it so the two register separately. Both read
`fleurette_florium.py`, which parses the one catalogue whose technical columns are headed
with both brands at once. The module docstrings there and in `fleurette.py` carry the
reasoning that is common to the pair; this one covers what is Florium's alone.

## Seventeen layouts, because Florium have the vans

Thirteen shared with Fleurette — Baxter, Mayflower, Belixter, Wincester — plus the four
**Black Pearl** panel-van conversions, which Fleurette do not sell and which have their own
technical page and their own price list.

The shared thirteen are the same vehicles as Fleurette's in a different trim, ash against
walnut, and are **priced identically wherever neither brand adds a specification**: `60LG`
£68,690 and `64LDF` £70,990 in both lists, `67LO` £74,390 in both. Where Fleurette fit
`Wellness`, Florium are £2,000–£3,300 cheaper. Two layouts differ with no stated reason —
`72LMF` and `72LJG` are £1,300 under their Discover twins — which is on the open-questions
list rather than explained.

## The Black Pearls are campervans, and two of their price rows do not add up

2590mm to the roof, which clears the 2300mm high-top threshold, on a Fiat Ducato L2/L3/L4
panel van. Their price list carries two rows that contradict the rest of the same sheet:

    Model 63LJ - Fiat L3H2 180 hp - Automatic transmission   25 kg   £57 275
    Model 59LT - Fiat L2H2 180 hp - Automatic transmission   25 kg   £55 300

Both sit on a **shorter body** than that layout's other rows — the 63s are otherwise L4H2,
the 59 otherwise L3H2 — both are out of sequence in the list, and both are £10,000 to
£12,000 *below* the same layout's 140 hp manual, while the sheet's own Fiat Options price a
180 hp engine at **+£2,160**. A 59LT 180 hp automatic should be £67,190 + £2,160 = £69,350,
not £55,300.

So the arithmetic says it is not those rows, and `PRICES` carries the **140 hp manual**
throughout. Raised with Fleurette on 28 October 2026 and unanswered.

The Black Pearl sheet also footnotes *"exclude factory charge of €330.00"* — a euro charge
excluded from a sterling on-the-road price. The printed sterling figure is recorded and the
exclusion said in provenance; nothing is added to it, because a converted addition to a
published price would be an invention.
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

#: The company, shared with `fleurette.py` — see that module's docstring.
MANUFACTURER = "Fleurette Constructeur"

#: The brand. A vehicle reads `Florium Black Pearl 59LT`, never the company's name.
MANUFACTURER_DISPLAY_NAME = "Florium"

#: The van range, which has no Fleurette twin.
BLACK_PEARL = "Black Pearl"

#: Florium's five ranges, spelt as their own catalogue and price lists spell them.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = tuple(
    (name, name) for _fleurette, name, _codes, _body in shared.RANGE_PAIRS
) + ((BLACK_PEARL, BLACK_PEARL),)

#: Thirteen shared layouts plus four vans.
EXPECTED_LAYOUTS = len(shared.SHARED_CODES) + len(shared.BLACK_PEARL_CODES)

#: `(range, layout) -> price in pounds`, from the 2027 UK price lists. **Manually
#: sourced**; the manual-transmission figure except on the Wincester, which is published
#: automatic-only. See the module docstring for the two Black Pearl rows not used.
PRICES: dict[tuple[str, str], int] = {
    ("Baxter", "60LG"): 68690,
    ("Baxter", "64LDF"): 70990,
    ("Baxter", "69LJG"): 73790,
    ("Mayflower", "67LO"): 74390,
    ("Mayflower", "70LMF"): 74590,
    ("Mayflower", "70LJG"): 75390,
    ("Mayflower", "74LMF"): 75490,
    ("Belixter", "73LMF"): 102990,
    ("Belixter", "73LJG"): 102990,
    ("Wincester", "72LMF"): 93690,
    ("Wincester", "72LJG"): 94590,
    ("Wincester", "74LJG"): 106190,
    ("Wincester", "75LMF"): 105390,
    (BLACK_PEARL, "59LT"): 64390,
    (BLACK_PEARL, "63LJ"): 66990,
    (BLACK_PEARL, "63LD"): 67690,
    (BLACK_PEARL, "63KS"): 68690,
}

#: Named in provenance against every price.
PRICE_SOURCE = (
    "the 2027 UK price lists emailed by Fleurette on 28 October 2026 "
    "('FLORIUM RRP GB 2027.pdf', 'ELISTER BELIXTER RRP GB 2027.pdf' and "
    "'BLACK PEARL RRP GB 2027.pdf', the last footnoting an excluded €330 factory "
    "charge), valid from 1 July 2026"
)

#: Which range each shared column belongs to, for this brand — index 1 of the pair.
_RANGE_AT: tuple[str, ...] = tuple(
    florium for _fleurette, florium, _body in shared.SHARED_RANGE_AT
)


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 — the catalogue is a plain PDF fetch
    snapshot_dir: Path,  # noqa: ARG001 — `http` already snapshots into it
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every Florium layout the catalogue vouches for, priced from the emailed lists."""
    wanted = {label for _path, label in ranges}
    columns, vans = shared.collect_columns(http, on_progress=on_progress)

    placed = [
        (_RANGE_AT[shared.SHARED_CODES.index(column.code)], column) for column in columns
    ]
    placed += [(BLACK_PEARL, column) for column in vans]

    products: list[ExtractedMotorhome] = []
    for manufacturer_range, column in placed:
        if manufacturer_range not in wanted:
            continue
        price = PRICES.get((manufacturer_range, column.code))
        if price is None:
            on_progress(
                f"{manufacturer_range} {column.code}: not in the 2027 UK price lists, so "
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
            f"expected {EXPECTED_LAYOUTS} Florium layouts and built {len(products)} — "
            f"check whether the catalogue's technical tables have really changed"
        )
    return products
