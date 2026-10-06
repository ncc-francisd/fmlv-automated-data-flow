"""Bespoke NI (bespokeleisure.co.uk) — campervans converted in Ballymena.

See `docs/adapters/bespoke.md` for the survey. **Deliberately a partial adapter**, and the
reason is worth stating at the top: Bespoke publish **no mass of any kind**. Six model
pages and three PDFs were searched and there is not one `kg` figure, nor the words
payload, gross vehicle weight, kerb weight, MIRO or MTPLM. FMLV holds MRO and MTPLM for
all eight of its rows, so the figures exist — they are simply not published, and this
adapter emits nothing for them rather than disturbing good data.

**Two halves, and only one of them is strong.**

* The **Explore** is sold on the VW Transporter T7 and the Ford Transit Custom, and the
  leaflet linked from its pages carries a real base-vehicle price table — six variants,
  each with an engine, a gearbox and a price. That is the roster and the price source, and
  it is rediscovered every run rather than hardcoded.
* The **Edition** is the VW Crafter, and its page states **one** on-the-road price for
  what FMLV holds as three products. One price cannot be attributed to three variants, so
  the three are collected by **identity alone**: no price, no dimensions, nothing proposed.
  That claims their FMLV rows so a run cannot report them missing from the site, which is
  the Carthago lesson — see `docs/adapters/README.md`.

**What is read from the pages, and what is deliberately not.** The Explore pages state
`Explore Length 5.05m`, a height of `1.98m` and `Explore Width 2.27m`. The first two match
FMLV's 5050 and 1980 exactly and are emitted. **The width is not**: 2.27 m is 2270 mm
against FMLV's 2032, which is the body width — 2270 is across the mirrors, and the rule
in `docs/adapters/README.md` is that width excludes them.

**The self-check** is that two independent documents state the same thing: the leaflet's
price table names the engine and gearbox of every variant, and the model pages state the
headline prices for their own base vehicle. `price_disagreements` reports where the two
differ.
"""

from __future__ import annotations

import html as htmllib
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.enums import BodyType
from ..product_model.model import Motorhome
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

__all__ = [
    "BASE_URL",
    "EDITION",
    "EXPECTED_PRODUCTS",
    "EXPLORE",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "BespokeExplore",
    "collect",
    "leaflet_url",
    "parse_explore_prices",
    "price_disagreements",
]

BASE_URL = "https://bespokeleisure.co.uk"

#: NCC id 68. The supplier list and the manufacturer list both say `Bespoke NI`; the
#: display name is the shorter `Bespoke`, which is how the site brands itself.
MANUFACTURER = "Bespoke NI"
MANUFACTURER_DISPLAY_NAME = "Bespoke"

#: Six Explore variants from the leaflet's price table, plus the three Edition products
#: FMLV holds. The Explore count is Bespoke's own: their price table lists six.
EXPECTED_PRODUCTS = 9

#: Pages that link the Explore leaflet. More than one, because the leaflet is the roster
#: and losing it loses two thirds of the range — if Bespoke drop it from one page the next
#: is tried before the run gives up.
EXPLORE_PAGES: tuple[str, ...] = (
    "/new-vw-transporter-campervan/",
    "/ford-transit-custom-campervan-conversion/",
    "/bespoke-explore-ford-tourneo-custom/",
)

#: The leaflet, whose upload folder carries the month it was issued
#: (`/wp-content/uploads/2026/02/`). **Never hardcode that path** — it moves every time
#: Bespoke reissue, and the point of rediscovering it is to follow the current one.
_LEAFLET_HREF = re.compile(
    r'["\'](?P<url>https?://[^"\']*Bespoke-Explore-Leaflet[^"\']*\.pdf)["\']', re.I
)

#: One row of the leaflet's `Choose your vehicle base` table:
#:
#:     Ford Custom Trend 110PS 6 speed manual   £60,995
#:
#: The table prints Ford on the left and VW on the right, so two variants share a line and
#: the pattern is run over the whole document rather than line by line.
_PRICE_ROW = re.compile(
    r"(?P<label>(?:Ford|VW)[A-Za-z0-9 ]*?\d{3}\s*PS[A-Za-z0-9 ]*?)\s*£\s*(?P<price>[\d,]+)",
    re.I,
)

#: A headline price on a model page, for the cross-check in `price_disagreements`.
_PAGE_PRICE = re.compile(r"£\s*(?P<price>\d{2},\d{3})")

#: Every Explore is this long and this tall, stated on each page as `Explore Length 5.05m`
#: and `1.98m`. Both agree with FMLV to the millimetre, which is why they are emitted.
#: **The width is not**: the pages say 2.27 m across the mirrors where FMLV holds the
#: 2032 mm body width.
_EXPLORE_LENGTH_MM = 5050
_EXPLORE_HEIGHT_MM = 1980

#: A campervan taller than this is a high top — the shared NCC threshold. Every Explore is
#: 1980 mm with the roof down, so they are elevating-roof campervans and not high tops.
HIGH_TOP_ABOVE_MM = 2300


@dataclass(frozen=True)
class BespokeExplore:
    """One Explore variant: how the leaflet names it, and how FMLV files it."""

    #: The engine and gearbox as the leaflet's price table writes them, lower-cased and
    #: space-collapsed for matching. This is the join between the two.
    leaflet_label: str
    #: What FMLV holds. `Explore Transporter` for the VW, `Explore Custom` for the Ford.
    fmlv_range: str
    fmlv_model: str
    #: The make, routed through `fmlv_base_vehicle`.
    base_vehicle: str

    @property
    def label(self) -> str:
        return f"{self.fmlv_range} {self.fmlv_model}"


#: **FMLV's names, not the leaflet's**, per the rule in `docs/adapters/README.md` — with
#: one deliberate exception, settled on 6 October 2026.
#:
#: Below the price table the **same leaflet** carries a specification table, and its
#: columns are headed `Ford Custom TREND 110PS Manual`, `Ford Custom LIMITED 136PS Auto`
#: and `Ford Custom TOURNEO 170PS Auto`, with the VW side reading `T7 Commerce PLUS` and
#: `T7 Commerce PRO` the same way. **Custom is the Transit Custom family and the
#: capitalised word is the trim**, which is why the site gives the Tourneo its own page.
#:
#: So FMLV's `170 Limited` carries the wrong trim — `Limited` belongs to the 136 PS. The
#: corrected name is emitted, with provenance on `model`, so the run proposes the rename
#: rather than quietly agreeing with FMLV. It still matches FMLV's row at 0.714, over the
#: 0.5 threshold, and scores 0.000 against the 110 and the 136, whose engine codes read as
#: layout codes and disagree.
EXPLORE: tuple[BespokeExplore, ...] = (
    BespokeExplore(
        "ford custom trend 110ps 6 speed manual",
        "Explore Custom", "110 Trend Elevating Roof", "Ford",
    ),
    BespokeExplore(
        "ford custom limited 136ps 8 speed auto",
        "Explore Custom", "136 Limited Elevating Roof", "Ford",
    ),
    BespokeExplore(
        "ford custom tourneo 170ps 8 speed auto",
        "Explore Custom", "170 Tourneo Elevating Roof", "Ford",
    ),
    BespokeExplore(
        "vw t7 commerce plus 110ps 6 speed manual",
        "Explore Transporter", "110 Commerce Plus Elevating Roof", "VW",
    ),
    BespokeExplore(
        "vw t7 commerce plus 150ps 8 speed auto",
        "Explore Transporter", "150 Commerce Plus Elevating Roof", "VW",
    ),
    #: Not in FMLV as at 5 October 2026 — the leaflet's sixth row, which the first run
    #: will propose as a new product.
    BespokeExplore(
        "vw t7 commerce pro 170ps 8 speed auto",
        "Explore Transporter", "170 Commerce Pro Elevating Roof", "VW",
    ),
)

#: The Crafter products, **collected by identity alone**. Their page carries one
#: on-the-road price for all three and no engine, roof or berth breakdown, so there is
#: nothing to propose — but emitting the identity claims the FMLV row, which stops a run
#: reporting a van Bespoke still sell as missing from the site.
EDITION: tuple[tuple[str, str, str], ...] = (
    ("Edition 2", "140 Auto", "VW"),
    ("Edition 2", "177 Commerce Plus Auto Fixed Roof", "VW"),
    ("Edition 4", "177 Commerce Plus Auto Elevating Roof", "VW"),
)

EDITION_PAGE = "/volkswagen-crafter-campervan/"

#: Every Explore sleeps four — the retail brochure's `Four Berth`, and the leaflet's
#: standard specification lists a fold-out rear seat/bed plus a pop-top bed.
_EXPLORE_BERTHS = 4
#: Four belted travel seats, as FMLV holds for all eight rows. Bespoke state the vehicle
#: is M1 registered but print no belt count, so this is **not** proposed — see
#: `_build_explore`, which records no provenance for it.
_EXPLORE_SEATS = 4


def _normalise(label: str) -> str:
    return re.sub(r"\s+", " ", label).strip().casefold()


def leaflet_url(page_html: str) -> str | None:
    """The Explore leaflet this page links, or `None`."""
    match = _LEAFLET_HREF.search(htmllib.unescape(page_html))
    return match.group("url") if match else None


def parse_explore_prices(leaflet_text: str) -> dict[str, int]:
    """Every variant the leaflet's base-vehicle table prices, keyed by normalised label.

    The table prints Ford on the left of each line and VW on the right, so a line-by-line
    read would find half of them; this runs over the whole document instead.
    """
    found: dict[str, int] = {}
    for match in _PRICE_ROW.finditer(leaflet_text):
        label = _normalise(match.group("label"))
        found[label] = int(match.group("price").replace(",", ""))
    return found


def price_disagreements(prices: dict[str, int], page_prices: dict[str, set[int]]) -> list[str]:
    """Where a model page's headline price is not one the leaflet prints.

    **The only cross-check this manufacturer offers.** There is no arithmetic to reconcile
    — no mass is published, so `payload = MTPLM - MRO` is unavailable — but the leaflet and
    the pages are maintained separately and state overlapping facts. A page quoting a price
    the leaflet does not know is the signal that one of them has been reissued alone.
    """
    found: list[str] = []
    printed = set(prices.values())
    for path, seen in sorted(page_prices.items()):
        unknown = sorted(p for p in seen if p not in printed)
        if unknown:
            found.append(
                f"{path} shows "
                f"{', '.join(f'GBP{p:,}' for p in unknown)}, which the Explore leaflet "
                f"does not price. One of the two has been reissued without the other"
            )
    return found


def _build_explore(variant: BespokeExplore, price: int | None, source_url: str) -> ExtractedMotorhome:
    """One Explore as a `Motorhome`. **No mass of any kind** — Bespoke publish none."""
    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=variant.fmlv_range,
        model=variant.fmlv_model,
        base_vehicle_manufacturer=fmlv_base_vehicle(variant.base_vehicle),
        berths=_EXPLORE_BERTHS,
        mh_passenger_seats_inc_driver=_EXPLORE_SEATS,
        rrp_pounds=price,
        mh_length_mm=_EXPLORE_LENGTH_MM,
        mh_height_mm=_EXPLORE_HEIGHT_MM,
        # Not emitted: the pages give 2.27m across the mirrors, FMLV holds the 2032mm body.
        mh_width_mm=None,
        body_type=BodyType.CAMPERVAN_ELEVATING_ROOF,
        # Published nowhere. Omitted, never blanked, so FMLV's own figures stand.
        mro_kilograms=None,
        mtplm_kilograms=None,
        mh_payload_kilograms=None,
    )

    provenance: dict[str, Provenance] = {}

    def record(field: str, snippet: str) -> None:
        provenance[field] = Provenance(source_url=source_url, snippet=snippet)

    if price is not None:
        record(
            "rrp_pounds",
            f"GBP{price:,} — the standard retail price for a fully converted Bespoke "
            f"Explore on the {variant.leaflet_label}, from the leaflet's "
            f"'Choose your vehicle base' table",
        )
    record(
        "base_vehicle_manufacturer",
        f"the leaflet prices this variant as a {variant.leaflet_label}",
    )
    record(
        "model",
        f"the leaflet's 'Choose your vehicle base' table names this variant "
        f"'{variant.leaflet_label}', giving the engine and the trim; 'Elevating Roof' is "
        f"the Austops pop-top every Explore carries",
    )
    record(
        "berths",
        "four — the retail brochure says 'Four Berth', and the standard specification "
        "lists a fold-out rear seat/bed and a pop-top bed",
    )
    record(
        "mh_length_mm",
        f"{_EXPLORE_LENGTH_MM}mm — the model pages state 'Explore Length 5.05m'",
    )
    record(
        "mh_height_mm",
        f"{_EXPLORE_HEIGHT_MM}mm — the model pages state 1.98m, the roof down",
    )
    record(
        "body_type",
        f"an elevating-roof campervan: every Explore has an Austops pop-top and is "
        f"{_EXPLORE_HEIGHT_MM}mm with it down, under the {HIGH_TOP_ABOVE_MM}mm high-top "
        f"threshold",
    )
    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


def _build_edition(fmlv_range: str, fmlv_model: str, base_vehicle: str) -> ExtractedMotorhome:
    """One Crafter, **identity only**.

    Its page prices the range once and breaks out no engine, roof or berth count, so there
    is nothing here to propose. The identity alone claims the FMLV row, which is the whole
    point: without it a run reports three vans Bespoke still sell as missing from the site.
    """
    return ExtractedMotorhome(
        motorhome=Motorhome(
            manufacturer=MANUFACTURER,
            manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
            manufacturer_range=fmlv_range,
            model=fmlv_model,
            base_vehicle_manufacturer=fmlv_base_vehicle(base_vehicle),
        ),
        provenance={},
    )


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 — plain WordPress, no JavaScript needed
    snapshot_dir: Path,  # noqa: ARG001 — `http` already snapshots into it
    *,
    ranges: tuple[tuple[str, str], ...] = (),  # noqa: ARG001
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every Bespoke campervan: six Explores priced from the leaflet, three Editions named.

    **Five fetches** — four model pages and the leaflet.
    """
    from ..fetch.pdf import extract_text  # noqa: PLC0415 — only this adapter needs it

    leaflet: str | None = None
    page_prices: dict[str, set[int]] = {}
    for path in EXPLORE_PAGES:
        url = f"{BASE_URL}{path}"
        try:
            html = http.fetch(url).file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as error:  # noqa: BLE001
            on_progress(f"WARNING: {url} did not fetch ({type(error).__name__})")
            continue
        text = re.sub(r"<[^>]+>", " ", htmllib.unescape(html))
        page_prices[path] = {
            int(m.group("price").replace(",", "")) for m in _PAGE_PRICE.finditer(text)
        }
        if leaflet is None:
            leaflet = leaflet_url(html)

    prices: dict[str, int] = {}
    if leaflet is None:
        on_progress(
            "WARNING: no Explore leaflet is linked from any model page. It is the roster "
            "and the only price source for two thirds of the range, so the Explores are "
            "collected without a price rather than not at all"
        )
    else:
        on_progress(f"reading {leaflet.rsplit('/', 1)[-1]}")
        try:
            prices = parse_explore_prices(extract_text(http.fetch(leaflet).file_path).text)
        except Exception as error:  # noqa: BLE001
            on_progress(
                f"WARNING: the Explore leaflet could not be read "
                f"({type(error).__name__}), so no Explore is priced this run"
            )
        if not prices:
            on_progress(
                "WARNING: the leaflet published no 'Choose your vehicle base' rows this "
                "run — the table has changed shape, not emptied"
            )

    for message in price_disagreements(prices, page_prices):
        on_progress(f"PRICES DISAGREE — {message}")

    results: list[ExtractedMotorhome] = []
    for variant in EXPLORE:
        price = prices.get(variant.leaflet_label)
        if price is None and prices:
            on_progress(
                f"WARNING: {variant.label} — the leaflet no longer prices a "
                f"{variant.leaflet_label!r}, so no price is proposed for it"
            )
        results.append(
            _build_explore(variant, price, leaflet or f"{BASE_URL}{EXPLORE_PAGES[0]}")
        )

    for fmlv_range, fmlv_model, base_vehicle in EDITION:
        results.append(_build_edition(fmlv_range, fmlv_model, base_vehicle))
    on_progress(
        f"{len(EDITION)} Edition product(s) collected by identity alone — their page "
        f"states one on-the-road price for all three and no engine, roof or berth "
        f"breakdown, so nothing is proposed and FMLV's figures stand"
    )

    on_progress(
        f"{len(results)} product(s) collected. NO MASS IS EMITTED for any of them: "
        f"Bespoke publish no payload, gross vehicle weight or kerb weight anywhere on "
        f"the site or in any of their three PDFs, so FMLV's own MRO and MTPLM stand"
    )
    if len(results) != EXPECTED_PRODUCTS:
        on_progress(
            f"expected {EXPECTED_PRODUCTS} products and built {len(results)} — EXPLORE or "
            f"EDITION has been edited without its count being updated"
        )
    return results
