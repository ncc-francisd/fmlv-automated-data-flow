"""Rolling Homes (rolling-homes.co.uk) — handmade VW campervans from Shrewsbury.

See `docs/adapters/rolling-homes.md` for the survey. **The source is the model pages**,
one per vehicle under `/van/<slug>/`, rediscovered from the home page each run.

## This adapter deliberately proposes no mass and no dimension

Rolling Homes publish **none** — no MTPLM, no mass in running order, no length, width or
height, on any page or in the brochure. The single mass on the whole site is the Darwin's
*"Payload as tested 380kg"*, with no MTPLM to place it against, so even that is left alone.

FMLV's figures for these eight products came from somewhere else and this adapter cannot
maintain them, so it emits nothing for them and they carry through untouched — the
requester's instruction of 9 October 2026, who is asking Rolling Homes for figures ahead of
their exhibition appearance. What it *can* keep current is the price, the berths, the
seats, the body type and the habitation findings.

## The brochure is not the spec source, despite being called one

`RH-Range-Brochure-2025-LR2.pdf` is linked identically from all eleven van pages, under a
heading reading *"Download our brochure featuring the model range with all the specs and
information"*. It contains **not one kg, mm or price** across its 24 pages. It is fetched
anyway, for the equipment prose behind the habitation findings, and never for a figure.

## The trap is a price, and it is the lowest number on the page

Every page carries two price blocks, as two `<h2>` headings with a tab widget under each:

* **New Vehicle** — the finished campervan, by VW trim and engine. Columbus S from
  £64,495 to £80,001.
* **Conversion Only** — converting a van the customer already owns. Columbus S **£20,495**.

So "take the lowest price", the obvious reading of the base-vehicle rule, takes the
conversion every time. Everything here is read from the **New Vehicle section only**, which
is the text between the two headings — and the same cut protects the berths and seats,
because each block has its own `Key Features` list stating different figures (`4 berths and
4 seats` against `2- 4 berths and 4-5 seats`).

**The rule is confirmed against FMLV's own data**: the lowest New Vehicle price reproduces
what FMLV holds exactly on the Shackleton (£59,995) and the Livingstone (£68,995).

## There is no self-check, and that is worth saying out loud

Every other manufacturer surveyed publishes something against itself — a payload against
two masses, a printed tolerance. Rolling Homes publish no mass at all, so there is no
arithmetic a parse can be tested against. `_reconciles` here is **structural rather than
numeric**: the price must have come from the New Vehicle section, must not equal the
Conversion Only figure, and must be plausible for a complete vehicle. A reviewer should
know this adapter is less defended than the others.

## Two pages are empty shells, and one of them is a live product

`/van/weekender/` and `/van/ability/` render every tab heading with **no content under
any of them**. The Weekender is a live FMLV product at £46,200, so an empty page must
collect nothing rather than read as a discontinuation — `collect` narrates it and moves on.

**Ability is not a product**: it is wheelchair accessibility offered across the range.

## Slugs lie

`/van/darwin-rl/` is the **Darwin EL**; `/van/darwin/` is the **Darwin ML**. Every name is
read from the page's `<h1>`.
"""

from __future__ import annotations

import html as htmllib
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from src.adapters import habitation
from src.adapters.base import ExtractedMotorhome, Provenance, fmlv_base_vehicle
from src.fetch.browser import BrowserFetcher
from src.fetch.http import Fetcher
from src.product_model.enums import BodyType
from src.product_model.model import Motorhome

__all__ = [
    "BASE_URL",
    "EXPECTED_VEHICLES",
    "FMLV_IDENTITY",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "MINIMUM_CREDIBLE_PRICE",
    "NOT_A_PRODUCT",
    "Vehicle",
    "base_price",
    "berths_and_seats",
    "body_type_for",
    "collect",
    "find_van_paths",
    "key_features",
    "identity_for",
    "new_vehicle_section",
    "parse_vehicle",
    "vehicle_name",
]

BASE_URL = "https://www.rolling-homes.co.uk"
MANUFACTURER = "Rolling Homes"
MANUFACTURER_DISPLAY_NAME = "Rolling Homes"

#: Eleven `/van/` pages, less Ability, which is not a product. Compared against the
#: collected count so a page quietly dropped by a template change is reported rather than
#: read as a withdrawal.
EXPECTED_VEHICLES = 10

#: A page with its own name that is **not a vehicle**. Ability is wheelchair accessibility
#: offered across the whole range — *"whether you need a slide out…"* — and its page carries
#: no price, no features and no specification of any kind.
NOT_A_PRODUCT: dict[str, str] = {
    "Ability": (
        "wheelchair accessibility offered across the range rather than a model of its own; "
        "its page has no price, no features and no specification"
    ),
}

#: How FMLV files each vehicle, which is **not how the site names it**. FMLV splits the
#: name as range = the explorer, model = the base vehicle generation — `Columbus S` / `T7`,
#: `Expedition` / `SWB` — and the site never prints `T7` or `SWB` anywhere.
#:
#: So the split cannot be derived, and this map carries FMLV's own answer for the eight it
#: holds. The Darwin is the one family where the site's own name contains the variant
#: (`Darwin EL`), which `identity_for` falls back on for a Darwin it has not seen.
#:
#: `model` is **never proposed** — no provenance is recorded for it — so a product FMLV
#: holds keeps its own, and this map exists to make the product *match* rather than to
#: change anything.
FMLV_IDENTITY: dict[str, tuple[str, str]] = {
    "Columbus": ("Columbus", "T7"),
    "Columbus S": ("Columbus S", "T7"),
    "Darwin EL": ("Darwin", "EL"),
    "Darwin FL": ("Darwin", "FL"),
    "Darwin FL 6.0": ("Darwin", "FL 6.0"),
    "Darwin ML": ("Darwin", "ML"),
    "Expedition": ("Expedition", "SWB"),
    "Livingstone": ("Livingstone", "T7"),
    "Shackleton": ("Shackleton", "T7"),
    # One name, carried twice, because Nova will not take a blank — the convention in
    # `docs/adapters/README.md`, and how FMLV already files 7329.
    "Weekender": ("Weekender", "Weekender"),
}

#: Below this, a figure in the New Vehicle section is not the price of a complete
#: campervan. The cheapest finished vehicle Rolling Homes list is the Shackleton at
#: £59,995 and the dearest conversion-only price is £20,995, so the gap is wide and this
#: sits in it. Part of `_reconciles`, which has no arithmetic to work with.
MINIMUM_CREDIBLE_PRICE = 30_000

#: The roof that decides half the campervan body type. Standard on the Transporter-based
#: vehicles and stated plainly — *"SCA elevating roof (220 × 132cm)"*.
_ELEVATING_ROOF = re.compile(r"\belevating roof\b|\bpop[- ]?top\b|\bSCA\b[^.]{0,40}roof", re.I)

#: `4 berths and 4 seats`, `2- 4 berths and 4-5 seats`. The lower of a range, per the
#: settled rule — the upper needs options.
_BERTHS = re.compile(r"(\d)\s*(?:-\s*\d)?\s*berths?", re.I)
_SEATS = re.compile(r"(\d)\s*(?:-\s*\d)?\s*seats?", re.I)

#: The base vehicle, read from the **New Vehicle section only**.
#:
#: Never from the whole page: every page of this site carries a "Volkswagen Van Converters"
#: block in its furniture, so a page-wide search answers `VW` for everything — including a
#: Ford-based van, and including a page with no content at all. Inside the section it is
#: real: the Vehicle Upgrades tab opens *"Pick your base vehicle…"* and the Darwin's key
#: features open *"Built on the Volkswagen LWB Crafter"*.
_BASE_VEHICLES: tuple[tuple[str, str], ...] = (
    (r"\bVolkswagen\b|\bVW\b", "VW"),
    (r"\bFord\b", "Ford"),
    (r"\bMercedes(?:-Benz)?\b", "Mercedes"),
)


def find_van_paths(home_html: str) -> list[str]:
    """Every vehicle page the home page links, as `/van/<slug>/` paths.

    **Rediscovered each run rather than written in.** The site publishes no roster of its
    own — the "Meet the explorers" footer is a carousel showing three at a time — so these
    links are the only list there is, and a hardcoded one would miss a new vehicle silently.
    """
    pattern = re.compile(rf'href="(?:{re.escape(BASE_URL)})?(/van/[a-z0-9.-]+/)"')
    seen: dict[str, None] = {}
    for match in pattern.finditer(htmllib.unescape(home_html)):
        seen.setdefault(match.group(1), None)
    return list(seen)


def _plain(fragment: str) -> str:
    """Markup as readable lines, one per block element."""
    body = re.sub(r"(?is)<(script|style|head|nav|header|footer)\b.*?</\1>", " ", fragment)
    text = re.sub(r"(?i)</(p|h\d|div|li|tr|td|th|br|span)>|<br\s*/?>", "\n", body)
    return re.sub(r"<[^>]+>", " ", htmllib.unescape(text))


def _lines(fragment: str) -> list[str]:
    return [" ".join(line.split()) for line in _plain(fragment).split("\n") if line.strip()]


def vehicle_name(page_html: str) -> str | None:
    """The vehicle's name, from its `<h1>` — **never from the slug**.

    `/van/darwin-rl/` is the Darwin EL and `/van/darwin/` is the Darwin ML, so a name
    derived from the URL would mislabel two of the four Darwins.
    """
    match = re.search(r"<h1[^>]*>(.*?)</h1>", page_html, re.S)
    if match is None:
        return None
    name = " ".join(re.sub(r"<[^>]+>", " ", htmllib.unescape(match.group(1))).split())
    return name or None


def identity_for(name: str) -> tuple[str, str]:
    """`(manufacturer_range, model)` as FMLV files this vehicle.

    A name this adapter has not seen falls back on the Darwin pattern — a known range
    followed by a variant — and failing that on the single-name convention, carrying the
    name twice because Nova will not take a blank.
    """
    if name in FMLV_IDENTITY:
        return FMLV_IDENTITY[name]
    known_ranges = {range_name for range_name, _ in FMLV_IDENTITY.values()}
    words = name.split()
    for count in (2, 1):
        head, tail = " ".join(words[:count]), " ".join(words[count:])
        if tail and head in known_ranges:
            return head, tail
    return name, name


def new_vehicle_section(page_html: str) -> str | None:
    """The markup between the `New Vehicle` heading and the `Conversion Only` one.

    **The single most important function here.** Everything after `Conversion Only`
    describes converting a customer's own van: a price a fifth of the real one, and a
    different `Key Features` list stating different berths and seats. Reading the page
    whole gets all three wrong at once, and nothing downstream could tell.

    Returns `None` when the headings are not where they should be, so the page is skipped
    rather than read loosely.
    """
    start = re.search(r"<h2[^>]*>\s*New Vehicle\s*</h2>", page_html, re.I)
    if start is None:
        return None
    rest = page_html[start.end() :]
    end = re.search(r"<h2[^>]*>\s*Conversion Only\s*</h2>", rest, re.I)
    return rest[: end.start()] if end else rest


#: The tab headings inside the New Vehicle block, in the order they render. Only the
#: first describes the vehicle as built; the other two are things to add to it.
_TAB_TITLES = ("Key Features", "Vehicle Upgrades", "Extras")


def key_features(section_html: str) -> list[str]:
    """Only the **Key Features** tab: the vehicle as standard.

    The New Vehicle block holds three tabs — `Key Features`, `Vehicle Upgrades`, `Extras` —
    and the last two are **options**. The first run of this adapter read the whole block
    and reported `'Diesel blown air heating*'` as the Columbus's heating, which is an item
    off its Extras list, not equipment it has. `docs/adapters/README.md` is explicit: never
    read a paid option as standard equipment.

    Elementor renders each title twice, once for desktop and once for mobile, so the titles
    appear as a run of three before the content begins. The last `Key Features` is
    therefore the one immediately preceding its own content.
    """
    lines = [line for line in _lines(section_html) if line]
    starts = [i for i, line in enumerate(lines) if line == "Key Features"]
    if not starts:
        return []
    start = starts[-1] + 1
    for index in range(start, len(lines)):
        if lines[index] in _TAB_TITLES:
            return lines[start:index]
    return lines[start:]


def base_price(section_html: str) -> int | None:
    """The cheapest complete vehicle in the New Vehicle table — the base, per the rule.

    Every price here is one trim-and-engine combination of the same campervan, so the
    lowest is the vehicle as standard and the rest are optioned variants.
    """
    prices = {int(raw.replace(",", "")) for raw in re.findall(r"£\s?([\d,]{5,})", section_html)}
    credible = {price for price in prices if price >= MINIMUM_CREDIBLE_PRICE}
    return min(credible) if credible else None


def berths_and_seats(section_html: str) -> tuple[int | None, int | None]:
    """Berths and seats from the New Vehicle block's own `Key Features` line.

    Both are published as ranges — `2- 4 berths and 4-5 seats` — and the **lower** figure
    is taken, per the settled rule: the upper needs options.
    """
    for line in key_features(section_html):
        if "berth" not in line.lower():
            continue
        berths = _BERTHS.search(line)
        seats = _SEATS.search(line)
        if berths:
            return int(berths.group(1)), int(seats.group(1)) if seats else None
    return None, None


def body_type_for(section_html: str) -> tuple[BodyType | None, str]:
    """`campervan_elevating_roof` where the page says the roof lifts, otherwise nothing.

    **Only half the rule can be applied.** `docs/adapters/README.md` makes body type a 2×2
    of elevating roof against high top, and the high-top half needs a height — which
    Rolling Homes publish nowhere. So a vehicle with a stated elevating roof is recorded as
    `campervan_elevating_roof`, and one without is **left blank rather than guessed**: the
    Crafter-based Darwins are high tops, which this has no way of knowing.
    """
    stated = _ELEVATING_ROOF.search(" ".join(key_features(section_html)))
    if stated is None:
        return None, (
            "no body type proposed — the page states no elevating roof, and the high-top "
            "half of the rule needs a height Rolling Homes publish nowhere"
        )
    return BodyType.CAMPERVAN_ELEVATING_ROOF, (
        f"a campervan with an elevating roof, from the page's own {stated.group(0)!r}. "
        f"Whether it is also a high top could not be tested: no height is published"
    )


def _base_vehicle(page_text: str) -> str | None:
    for pattern, make in _BASE_VEHICLES:
        if re.search(pattern, page_text):
            return fmlv_base_vehicle(make)
    return None


@dataclass
class Vehicle:
    """One vehicle, as read from the New Vehicle half of its own page."""

    name: str
    url: str
    rrp_pounds: int | None = None
    berths: int | None = None
    seats: int | None = None
    base_vehicle_manufacturer: str | None = None
    body_type: BodyType | None = None
    body_type_reason: str = ""
    conversion_only_price: int | None = None
    equipment: list[str] = field(default_factory=list)

    @property
    def identity(self) -> tuple[str, str]:
        return identity_for(self.name)

    @property
    def label(self) -> str:
        return self.name

    @property
    def publishes_nothing(self) -> bool:
        """An empty-shell page: the headings render, nothing is under them."""
        return (
            self.rrp_pounds is None
            and self.berths is None
            and self.seats is None
            and self.body_type is None
        )


def _conversion_price(page_html: str) -> int | None:
    """The Conversion Only figure, read **only** so `_reconciles` can refuse to match it."""
    start = re.search(r"<h2[^>]*>\s*Conversion Only\s*</h2>", page_html, re.I)
    if start is None:
        return None
    prices = {
        int(raw.replace(",", ""))
        for raw in re.findall(r"£\s?([\d,]{5,})", page_html[start.end() :])
    }
    return min(prices) if prices else None


def parse_vehicle(page_html: str, url: str) -> Vehicle | None:
    """One vehicle page, or `None` if it is an empty shell or has no New Vehicle block."""
    name = vehicle_name(page_html)
    if name is None:
        return None
    section = new_vehicle_section(page_html)
    if section is None:
        return Vehicle(name=name, url=url)
    price = base_price(section)
    berths, seats = berths_and_seats(section)
    body_type, reason = body_type_for(section)
    return Vehicle(
        name=name,
        url=url,
        rrp_pounds=price,
        berths=berths,
        seats=seats,
        base_vehicle_manufacturer=_base_vehicle(" ".join(_lines(section))),
        body_type=body_type,
        body_type_reason=reason,
        conversion_only_price=_conversion_price(page_html),
        equipment=habitation.usable_lines(key_features(section)),
    )


def _reconciles(vehicle: Vehicle) -> tuple[bool, str]:
    """**Structural, because there is no arithmetic to be had.**

    Rolling Homes publish no mass, so `MTPLM - MRO = payload` — the check every other
    adapter here leans on — does not exist. What can be verified is that the price came
    from the right half of the page: that it is not the Conversion Only figure, and that it
    is credible for a complete vehicle. That is a weaker defence than the others and the
    survey says so.
    """
    if vehicle.rrp_pounds is None:
        # **Not a failure.** The Expedition publishes berths and seats and no price at
        # all, and dropping the product over that would lose the two fields it does
        # publish and report a live vehicle as withdrawn. Nothing is proposed for a price
        # that was never found, so FMLV's own stands.
        return True, "no price is published for this vehicle, so FMLV's own figure stands"
    if vehicle.rrp_pounds == vehicle.conversion_only_price:
        return False, (
            f"the price read, £{vehicle.rrp_pounds:,}, is the Conversion Only figure — "
            f"that is the cost of converting a van the customer already owns, not this "
            f"vehicle"
        )
    if vehicle.rrp_pounds < MINIMUM_CREDIBLE_PRICE:
        return False, (
            f"£{vehicle.rrp_pounds:,} is below the £{MINIMUM_CREDIBLE_PRICE:,} a complete "
            f"campervan can credibly cost"
        )
    return True, (
        f"£{vehicle.rrp_pounds:,}, the cheapest trim in the New Vehicle table and so the "
        f"vehicle as standard"
        + (
            f"; the Conversion Only price of £{vehicle.conversion_only_price:,} on the same "
            f"page is excluded"
            if vehicle.conversion_only_price
            else ""
        )
    )


#: How each habitation reading is introduced. Findings for a person to type in.
_FEATURE_NOTES: dict[str, str] = {
    "heating": "the heating in the page's New Vehicle key features",
    "refrigeration": "the refrigeration in the page's New Vehicle key features",
    "microwave": "a microwave in the page's New Vehicle key features",
    "shower_toilet_separated": "the washroom as the New Vehicle key features describe it",
}


def build_extracted(vehicle: Vehicle, *, basis: str) -> ExtractedMotorhome:
    """One Rolling Homes campervan, with provenance on everything it proposes."""
    features = habitation.features_from(vehicle.equipment)
    # Dropped as on every other adapter: the copy names beds without saying which are
    # built in and which are made up from the seating.
    features.pop("bed_types", None)

    manufacturer_range, model = vehicle.identity
    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=manufacturer_range,
        model=model,
        base_vehicle_manufacturer=vehicle.base_vehicle_manufacturer,
        berths=vehicle.berths,
        mh_passenger_seats_inc_driver=vehicle.seats,
        rrp_pounds=vehicle.rrp_pounds,
        price_min_range_pounds=vehicle.rrp_pounds,
        body_type=vehicle.body_type,
        # Deliberately absent: Rolling Homes publish no mass and no dimension anywhere, so
        # FMLV's own figures carry through untouched.
        mtplm_kilograms=None,
        mro_kilograms=None,
        mh_payload_kilograms=None,
        mh_length_mm=None,
        mh_width_mm=None,
        mh_height_mm=None,
    )
    for name, feature in features.items():
        setattr(motorhome, name, feature.value)

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=vehicle.url, snippet=f"{vehicle.label} — {snippet}"
        )

    record("manufacturer_range", f'range "{manufacturer_range}", from the page heading')
    # **No provenance for `model`.** FMLV's model is the base-vehicle generation (`T7`,
    # `SWB`) and the site never prints it, so there is nothing to confirm or correct and
    # `compare_fields` must not be invited to look.
    if vehicle.rrp_pounds is not None:
        record("rrp_pounds", basis)
        record(
            "price_min_range_pounds",
            f"£{vehicle.rrp_pounds:,} — the entry trim of the New Vehicle table",
        )
    if vehicle.berths is not None:
        record("berths", f"{vehicle.berths} berths, from the New Vehicle key features")
    if vehicle.seats is not None:
        record(
            "mh_passenger_seats_inc_driver",
            f"{vehicle.seats} seats, from the New Vehicle key features. Rolling Homes "
            f"state these are all three-point belts",
        )
    if vehicle.base_vehicle_manufacturer is not None:
        record(
            "base_vehicle_manufacturer",
            f"{vehicle.base_vehicle_manufacturer}, named in the page's own description",
        )
    if vehicle.body_type is not None:
        record("body_type", vehicle.body_type_reason)
    for name, feature in features.items():
        provenance[name] = Provenance(
            source_url=vehicle.url,
            snippet=(
                f"{vehicle.label} — {feature.note or _FEATURE_NOTES.get(name, name)}: "
                f"{feature.snippet!r}"
            ),
        )
    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


def collect(
    http: Fetcher,
    browser: BrowserFetcher,  # noqa: ARG001 — plain HTML throughout
    snapshot_dir: Path,  # noqa: ARG001 — `http` already snapshots into it
    *,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every finished Rolling Homes campervan, from the pages the home page links."""
    home = http.fetch(f"{BASE_URL}/").file_path.read_text(encoding="utf-8", errors="replace")
    paths = find_van_paths(home)
    if not paths:
        msg = f"no /van/ pages linked from {BASE_URL}/ — the only roster there is has gone"
        raise RuntimeError(msg)
    on_progress(f"the home page links {len(paths)} vehicle page(s)")

    results: list[ExtractedMotorhome] = []
    for path in paths:
        url = f"{BASE_URL}{path}"
        page = http.fetch(url)
        if page.status_code != 200:
            on_progress(f"SKIPPED: {url} returned {page.status_code}")
            continue
        vehicle = parse_vehicle(
            page.file_path.read_text(encoding="utf-8", errors="replace"), url
        )
        if vehicle is None:
            on_progress(f"SKIPPED: no heading found on {url}, so nothing names the vehicle")
            continue
        if vehicle.name in NOT_A_PRODUCT:
            on_progress(f"{vehicle.name} — NOT A PRODUCT: {NOT_A_PRODUCT[vehicle.name]}")
            continue

        reconciles, basis = _reconciles(vehicle)
        if not reconciles:
            on_progress(f"{vehicle.name} — DROPPED: {basis}")
            continue

        results.append(build_extracted(vehicle, basis=basis))
        manufacturer_range, model = vehicle.identity
        if vehicle.publishes_nothing:
            # **Emitted anyway, deliberately.** The Weekender's page is an empty shell and
            # the Weekender is a live FMLV product: collecting nothing for it would report
            # it as withdrawn, which is the one failure this manufacturer makes easy. It is
            # recorded for its identity alone, so it matches and carries through unchanged.
            on_progress(
                f"{vehicle.name} — its page is an EMPTY SHELL: every tab heading is there "
                f"and nothing is under any of them. Recorded for its identity only, so it "
                f"is not read as withdrawn; every figure is left to FMLV"
            )
            continue
        on_progress(
            f"{vehicle.name} — read as {manufacturer_range} / {model}: "
            + (f"£{vehicle.rrp_pounds:,}" if vehicle.rrp_pounds else "no price published")
            + f", {vehicle.berths} berth, {vehicle.seats} seats"
        )

    on_progress(
        "NO MASS AND NO DIMENSION IS PROPOSED. Rolling Homes publish none anywhere — not "
        "on a page, not in the brochure — so FMLV's MTPLM, mass in running order, payload, "
        "length, width and height all carry through untouched."
    )
    on_progress(
        "THERE IS NO ARITHMETIC SELF-CHECK, which is worth knowing. With no masses "
        "published there is nothing to test a parse against; the check here is structural, "
        "that the price came from the New Vehicle half of the page rather than the "
        "Conversion Only half."
    )
    if len(results) != EXPECTED_VEHICLES:
        on_progress(
            f"expected {EXPECTED_VEHICLES} vehicles and collected {len(results)} — check "
            f"whether the range has changed"
        )
    on_progress(f"collected {len(results)} Rolling Homes campervan(s)")
    return results
