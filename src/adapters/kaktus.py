"""Kaktus (kaktusvans.co.uk) — hand-built campervans from Pontypool, Wales.

See `docs/adapters/kaktus.md` for the survey. **The source is the configurator**,
`/configure`, with each model's own page read alongside it for the habitation findings.

## A Next.js site that needs no browser

Every page here renders almost nothing as plain HTML: the content arrives in a streamed
**`self.__next_f`** payload, as a run of `self.__next_f.push([1, "…"])` calls whose second
element is a JSON-encoded string. Concatenating those strings and decoding them hands an
ordinary HTTP fetch the whole page's data.

That is the only trick this adapter needs, and it is worth stating plainly because the
page *looks* like a `BrowserFetcher` job and is not — reaching for the browser first is the
mistake `docs/adapters/README.md` warns about.

## The model pages publish nothing; the configurator publishes everything

`/vans/oasis` and `/vans/dune` carry a four-row summary — base vehicle, drive, power,
water — and **no price, no mass and no dimension**, in the rendered page or the payload.

`/configure` carries the figures as structured data:

```json
{"id":"oasis","name":"Oasis","tier":"LWB · Luxury off-grid","basePrice":157000}
{"id":"dune","name":"Dune","tier":"4x4 · Expedition","basePrice":142000}
```

## Two models in the configurator are four products in FMLV

FMLV splits each range by berth count — `Oasis / X4 LWB` and `Oasis / X2 LWB` — and the
configurator's **sleeping layout** group is that same split:

```json
{"id":"2-berth", "label":"2-berth",                 "price":0}
{"id":"pop-top", "label":"4-berth · pop-top roof",  "price":0, "poa":true}
{"id":"cabbunk", "label":"4-berth · Cabbunk system","price":0, "poa":true}
```

So each model yields **one product per distinct berth count**, which is why two models
produce four products.

**The `basePrice` is the two-berth price**, and both routes to four berths are marked
`poa` — price on application. The four-berth premium is therefore not published, and
nothing is invented for it: both products carry the `basePrice`, which is what FMLV already
holds for both and is consistent with a "from" price. `_FOUR_BERTH_NOTE` says so on every
run.

## The price trap is the option list

`/configure` publishes about **forty** prices beside the two that matter, from an £85
windscreen cover to a £4,750 seat retrim. Any "lowest number on the page" heuristic buys a
windscreen cover, so the price is read **only** from a model's own `basePrice` key.

## Mojave is not a product

`/vans/mojave` is a third range and must be excluded by name. Its own page says
*"Production planned from April 2027"*, *"Specification is for the prototype show vehicle
and may change before production"*, and *"Prices from £235,000 … subject to
confirmation"*. It is also a Mercedes-Benz Sprinter 519 expedition build at **5,000–5,350
kg**, where the rest of the range sits at 3,500.

## Nothing dimensional is proposed, because nothing is published

No mass and no dimension appears anywhere on this site — not on a model page, not in the
configurator, and there is no brochure. FMLV's figures came from somewhere off-site and
this adapter cannot maintain them, so they carry through untouched. That includes an
`MRO 3500 / MTPLM 3500 / payload 200` that cannot all be right; it needs asking about, not
guessing at.
"""

from __future__ import annotations

import html as htmllib
import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.model import Motorhome
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle
from . import habitation

__all__ = [
    "BASE_URL",
    "CONFIGURE_URL",
    "EXPECTED_PRODUCTS",
    "FMLV_WHEELBASE",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "MINIMUM_CREDIBLE_PRICE",
    "NOT_A_PRODUCT",
    "ConfiguredModel",
    "Option",
    "Product",
    "base_vehicle_from",
    "berth_options",
    "build_extracted",
    "collect",
    "find_van_paths",
    "flight_payload",
    "parse_groups",
    "parse_models",
    "products_for",
    "summary_rows",
]

BASE_URL = "https://www.kaktusvans.co.uk"
MANUFACTURER = "KAKTUS"
MANUFACTURER_DISPLAY_NAME = "Kaktus"

#: Campervans, so the default motorhome product area — no `VEHICLE_CLASS` needed.
CONFIGURE_URL = f"{BASE_URL}/configure"

#: Two configurator models at two berth counts each, which is what FMLV holds.
EXPECTED_PRODUCTS = 4

#: Below this, a figure in the configurator is an option rather than a vehicle. The
#: cheapest Kaktus is £142,000 and the dearest option is £4,750, so the gap is enormous.
MINIMUM_CREDIBLE_PRICE = 50_000

#: A page with its own name that is **not a current product**.
NOT_A_PRODUCT: dict[str, str] = {
    "mojave": (
        "a prototype, not a product: its page says 'Production planned from April 2027' "
        "and 'Specification is for the prototype show vehicle and may change before "
        "production', and prices it 'from £235,000 … subject to confirmation'. It is also "
        "a Mercedes-Benz Sprinter 519 expedition build at 5,000-5,350kg where the rest of "
        "the range sits at 3,500kg"
    ),
}

#: The wheelbase FMLV puts in each model string — `X4 LWB`, `X2 MWB`.
#:
#: **Kaktus publish only half of this.** The Oasis's tier reads `LWB · Luxury off-grid`;
#: the Dune's reads `4x4 · Expedition` and names no wheelbase anywhere on its page. So the
#: Dune's `MWB` cannot be derived and this map carries FMLV's own answer.
#:
#: `model` is therefore **never proposed** — no provenance is recorded for it — and this
#: exists to make the product *match* rather than to change anything.
FMLV_WHEELBASE: dict[str, str] = {
    "Oasis": "LWB",
    "Dune": "MWB",
}

#: `self.__next_f.push([1,"…"])`. The second element is a JSON string; the first is a
#: chunk kind that varies and is not needed.
_FLIGHT_CHUNK = re.compile(r'self\.__next_f\.push\(\[\d+,\s*("(?:\\.|[^"\\])*")\s*\]\)', re.S)

#: `{"id":"oasis","name":"Oasis","tier":"…","tagline":"…","basePrice":157000`.
_MODEL = re.compile(
    r'\{"id":"(?P<id>[a-z0-9-]+)","name":"(?P<name>[^"]+)","tier":"(?P<tier>[^"]*)"'
    r',"tagline":"(?P<tagline>[^"]*)","basePrice":(?P<price>\d+)'
)

#: `{"id":"berths","label":"Sleeping layout","kind":"single",…,"options":[…]}`.
_GROUP = re.compile(
    r'\{"id":"(?P<id>[a-z0-9-]+)","label":"(?P<label>[^"]*)","kind":"[^"]*"'
    r'(?P<rest>.*?)"options":\[(?P<options>.*?)\]\}',
    re.S,
)

#: One option inside a group.
_OPTION = re.compile(
    r'\{"id":"(?P<id>[a-z0-9-]+)","label":"(?P<label>[^"]*)","price":(?P<price>-?\d+)'
    r',"poa":(?P<poa>true|false|"\$undefined")'
    r'(?:,"desc":(?P<desc>"(?:\\.|[^"\\])*"|"\$undefined"))?'
)

#: `2-berth`, `4-berth · pop-top roof`.
_BERTHS = re.compile(r"(\d+)\s*-?\s*berth", re.I)

#: The model page's summary list — `<dt …>Base</dt><dd …>MAN TGE 4MOTION</dd>`.
#:
#: **Read from the rendered markup, not the flight payload.** The pairs appear in both, but
#: in the payload they are React nodes whose strings are JSON-escaped, and the Dune's
#: `60mm lift · 16\" off-road tyres` carries an escaped quote that a naive value pattern
#: stops at — losing the row. The plain `<dd>` has the same text with an HTML entity
#: instead, which `_text` resolves.
_SUMMARY_ROW = re.compile(
    r"<dt[^>]*>(?P<label>.*?)</dt>\s*<dd[^>]*>(?P<value>.*?)</dd>", re.S
)

#: Base vehicles Kaktus name, in the spelling FMLV files them under.
_BASE_VEHICLES: tuple[tuple[str, str], ...] = (
    (r"\bMAN\b", "MAN"),
    (r"\bVolkswagen\b|\bVW\b|\bCrafter\b", "VW"),
    (r"\bMercedes(?:-Benz)?\b|\bSprinter\b", "Mercedes"),
)


def flight_payload(page_html: str) -> str:
    """Every `self.__next_f` chunk, concatenated and JSON-decoded.

    The whole reason this site needs no browser. A chunk that will not decode is skipped
    rather than raising: the stream carries framing the page does not need, and one bad
    chunk must not cost the rest.
    """
    chunks: list[str] = []
    for match in _FLIGHT_CHUNK.finditer(page_html):
        try:
            chunks.append(json.loads(match.group(1)))
        except (ValueError, TypeError):
            continue
    return "".join(chunks)


def _text(fragment: str) -> str:
    """One line of readable text out of a markup fragment."""
    return " ".join(htmllib.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def _unescape(value: str | None) -> str:
    if not value or value == '"$undefined"':
        return ""
    if value.startswith('"'):
        try:
            value = json.loads(value)
        except ValueError:
            value = value.strip('"')
    return " ".join(htmllib.unescape(value).split())


@dataclass(frozen=True)
class ConfiguredModel:
    """One model as the configurator describes it."""

    key: str
    name: str
    tier: str
    tagline: str
    base_price: int


@dataclass(frozen=True)
class Option:
    """One choice inside a configurator group."""

    key: str
    label: str
    price: int
    poa: bool
    description: str = ""


def parse_models(payload: str) -> list[ConfiguredModel]:
    """Every model in the configurator, in the order it lists them."""
    found: dict[str, ConfiguredModel] = {}
    for match in _MODEL.finditer(payload):
        key = match.group("id")
        found.setdefault(
            key,
            ConfiguredModel(
                key=key,
                name=_unescape(match.group("name")),
                tier=_unescape(match.group("tier")),
                tagline=_unescape(match.group("tagline")),
                base_price=int(match.group("price")),
            ),
        )
    return list(found.values())


def parse_groups(payload: str) -> dict[str, list[Option]]:
    """The configurator's option groups, keyed by group id."""
    groups: dict[str, list[Option]] = {}
    for match in _GROUP.finditer(payload):
        options = [
            Option(
                key=option.group("id"),
                label=_unescape(option.group("label")),
                price=int(option.group("price")),
                poa=option.group("poa") == "true",
                description=_unescape(option.group("desc")),
            )
            for option in _OPTION.finditer(match.group("options"))
        ]
        if options:
            groups.setdefault(match.group("id"), options)
    return groups


def berth_options(groups: dict[str, list[Option]]) -> list[tuple[int, Option]]:
    """`(berths, the option that provides them)`, lowest first and one per count.

    **This is what turns two models into four products.** Where two options reach the same
    count — a pop-top roof and a cab bunk system both sleep four — the first is kept, so
    the count appears once.
    """
    seen: dict[int, Option] = {}
    for option in groups.get("berths", []):
        found = _BERTHS.search(option.label)
        if found is None:
            continue
        seen.setdefault(int(found.group(1)), option)
    return sorted(seen.items())


def base_vehicle_from(groups: dict[str, list[Option]]) -> tuple[str | None, str]:
    """The base vehicle, from the configurator's own `Base vehicle` group."""
    labels = " ".join(
        f"{option.label} {option.description}" for option in groups.get("base", [])
    )
    for pattern, make in _BASE_VEHICLES:
        if re.search(pattern, labels, re.I):
            return fmlv_base_vehicle(make), (
                f"{make}, from the configurator's Base vehicle group: "
                f"{labels.strip()!r}"
            )
    return None, "the configurator names no base vehicle"


def find_van_paths(home_html: str) -> list[str]:
    """Every `/vans/<slug>` page the home page links.

    **Rediscovered each run**, so a fourth range is noticed rather than missed. The home
    page is plain enough that these appear as ordinary `href`s.
    """
    seen: dict[str, None] = {}
    for match in re.finditer(r'href="(/vans/[a-z0-9-]+)"', home_html, re.I):
        seen.setdefault(match.group(1), None)
    return list(seen)


def summary_rows(page_html: str) -> dict[str, str]:
    """A model page's `label: value` summary — the only equipment prose Kaktus publish.

    The Oasis gives `Base`, `Drive`, `Power`, `Water`, `Sleeps`; the Dune gives `Base`,
    `Stance`, `Rack`, `Power`, `Built for`. **The labels differ per model**, so they are
    read as whatever pairs are there rather than looked up by name.
    """
    found: dict[str, str] = {}
    for match in _SUMMARY_ROW.finditer(page_html):
        label = _text(match.group("label"))
        value = _text(match.group("value"))
        if label and value:
            found.setdefault(label, value)
    return found


@dataclass
class Product:
    """One FMLV product: a configurator model at one berth count."""

    model: ConfiguredModel
    berths: int
    berth_option: Option
    url: str
    base_vehicle_manufacturer: str | None = None
    base_vehicle_basis: str = ""
    equipment: list[str] = field(default_factory=list)

    @property
    def wheelbase(self) -> str | None:
        return FMLV_WHEELBASE.get(self.model.name)

    @property
    def identity(self) -> tuple[str, str | None]:
        """`(range, model)` as FMLV files it — `Oasis` / `X4 LWB`."""
        wheelbase = self.wheelbase
        if wheelbase is None:
            return self.model.name, None
        return self.model.name, f"X{self.berths} {wheelbase}"

    @property
    def label(self) -> str:
        _range, model = self.identity
        return f"{self.model.name} {model or f'X{self.berths}'}"


def products_for(
    model: ConfiguredModel, groups: dict[str, list[Option]], *, url: str
) -> list[Product]:
    """One product per distinct berth count the configurator offers."""
    base_vehicle, basis = base_vehicle_from(groups)
    return [
        Product(
            model=model,
            berths=berths,
            berth_option=option,
            url=url,
            base_vehicle_manufacturer=base_vehicle,
            base_vehicle_basis=basis,
        )
        for berths, option in berth_options(groups)
    ]


def _reconciles(product: Product) -> tuple[bool, str]:
    """**Structural, because Kaktus publish no arithmetic to check.**

    No mass is published anywhere, so `MTPLM - MRO = payload` — the test every other
    adapter leans on — does not exist here. What can be verified is that the price came
    from a model's own `basePrice` rather than from the forty-odd options beside it, and
    that it is credible for a complete campervan. The survey says plainly that this adapter
    is less defended than most.
    """
    price = product.model.base_price
    if price < MINIMUM_CREDIBLE_PRICE:
        return False, (
            f"£{price:,} is below the £{MINIMUM_CREDIBLE_PRICE:,} a complete Kaktus can "
            f"credibly cost — that will be an option price, not a vehicle"
        )
    if product.wheelbase is None:
        return False, (
            f"{product.model.name} is not a range this adapter knows the wheelbase for, "
            f"so it cannot be given the model string FMLV files it under. Add it to "
            f"FMLV_WHEELBASE once someone has checked which wheelbase it is"
        )
    return True, (
        f"£{price:,}, the configurator's own basePrice for the {product.model.name} — not "
        f"one of the forty-odd option prices beside it"
    )


#: Said on every run for a four-berth product. The premium is genuinely unpublished.
_FOUR_BERTH_NOTE = (
    "the four-berth layouts are BOTH marked 'poa' in the configurator — the pop-top roof "
    "and the Cabbunk system — so Kaktus publish no price for the upgrade. The basePrice is "
    "the two-berth figure and is recorded here as a 'from' price, which is what FMLV "
    "already holds for both berth counts. Nothing is invented for a POA"
)

#: How each habitation reading is introduced.
_FEATURE_NOTES: dict[str, str] = {
    "heating": "the heating in the model page's own summary",
    "refrigeration": "the refrigeration in the model page's own summary",
    "microwave": "a microwave in the model page's own summary",
    "shower_toilet_separated": "the washroom as the model page describes it",
}


def build_extracted(product: Product, *, basis: str) -> ExtractedMotorhome:
    """One Kaktus campervan, with provenance on everything it proposes."""
    features = habitation.features_from(product.equipment)
    features.pop("bed_types", None)

    manufacturer_range, model = product.identity
    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=manufacturer_range,
        model=model,
        base_vehicle_manufacturer=product.base_vehicle_manufacturer,
        berths=product.berths,
        rrp_pounds=product.model.base_price,
        price_min_range_pounds=product.model.base_price,
        # **Deliberately absent, every one.** Kaktus publish no mass and no dimension
        # anywhere — not on a page, not in the configurator, and there is no brochure — so
        # FMLV's own figures carry through untouched. See the module docstring.
        mtplm_kilograms=None,
        mro_kilograms=None,
        mh_payload_kilograms=None,
        mh_length_mm=None,
        mh_width_mm=None,
        mh_height_mm=None,
        # Not proposed either: no height is published, so the high-top half of the body
        # type rule cannot be applied, and the elevating roof here is an *option*.
        body_type=None,
        # Not proposed: `Sleeps up to 4 · swivel cab seats` is a berth count, not a belted
        # seat count, and nothing else states one.
        mh_passenger_seats_inc_driver=None,
    )
    for name, feature in features.items():
        setattr(motorhome, name, feature.value)

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=product.url, snippet=f"{product.label} — {snippet}"
        )

    record(
        "manufacturer_range",
        f'range "{manufacturer_range}", the configurator\'s own name for this model',
    )
    # **No provenance for `model`.** FMLV's model string carries a wheelbase Kaktus only
    # publish for the Oasis, so there is nothing to confirm or correct on the Dune and
    # `compare_fields` must not be invited to look at either.
    record(
        "rrp_pounds",
        basis + (f". NOTE: {_FOUR_BERTH_NOTE}" if product.berths > 2 else ""),
    )
    record(
        "price_min_range_pounds",
        f"£{product.model.base_price:,} — the configurator's starting price for the "
        f"{product.model.name} before any option is added",
    )
    record(
        "berths",
        f"{product.berths} berths, from the configurator's Sleeping layout group: "
        f"{product.berth_option.label!r}"
        + (
            f" ({product.berth_option.description})"
            if product.berth_option.description
            else ""
        ),
    )
    if product.base_vehicle_manufacturer is not None:
        record("base_vehicle_manufacturer", product.base_vehicle_basis)
    for name, feature in features.items():
        provenance[name] = Provenance(
            source_url=product.url,
            snippet=(
                f"{product.label} — {feature.note or _FEATURE_NOTES.get(name, name)}: "
                f"{feature.snippet!r}"
            ),
        )
    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


def _notes(product: Product) -> Iterable[str]:
    """What was considered and not proposed."""
    if product.berths > 2:
        yield f"{product.label} — PRICE IS A 'FROM' FIGURE: {_FOUR_BERTH_NOTE}"
    if unclear := habitation.heating_is_unclear(product.equipment):
        yield (
            f"{product.label} — heating is mentioned but its kind is not named: "
            f"{unclear!r}. Nothing is proposed for it"
        )


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 — the flight payload makes a browser unnecessary
    snapshot_dir: Path,  # noqa: ARG001 — `http` already snapshots into it
    *,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every current Kaktus campervan, from the configurator."""
    configure = http.fetch(CONFIGURE_URL)
    if configure.status_code != 200:
        msg = f"{CONFIGURE_URL} returned {configure.status_code} — the only price source"
        raise RuntimeError(msg)
    payload = flight_payload(
        configure.file_path.read_text(encoding="utf-8", errors="replace")
    )
    if not payload:
        msg = (
            f"no self.__next_f payload on {CONFIGURE_URL} — the page's data could not be "
            f"decoded, so this is a parsing failure rather than an empty range"
        )
        raise RuntimeError(msg)

    models = parse_models(payload)
    groups = parse_groups(payload)
    if not models:
        msg = f"the configurator at {CONFIGURE_URL} lists no models"
        raise RuntimeError(msg)
    on_progress(
        f"the configurator lists {len(models)} model(s) and "
        f"{sum(len(options) for options in groups.values())} option(s)"
    )

    # The model pages are read only for their summary prose, which is the single source of
    # habitation findings. A page that will not load costs the findings, not the product.
    home = http.fetch(f"{BASE_URL}/")
    van_paths = {
        path.rsplit("/", 1)[-1]: path
        for path in find_van_paths(
            home.file_path.read_text(encoding="utf-8", errors="replace")
        )
    }
    for slug, reason in NOT_A_PRODUCT.items():
        if slug in van_paths:
            on_progress(f"{slug} — NOT A PRODUCT: {reason}")

    results: list[ExtractedMotorhome] = []
    for model in models:
        if model.key in NOT_A_PRODUCT:
            on_progress(f"{model.name} — NOT A PRODUCT: {NOT_A_PRODUCT[model.key]}")
            continue
        path = van_paths.get(model.key, f"/vans/{model.key}")
        url = f"{BASE_URL}{path}"
        equipment: list[str] = []
        page = http.fetch(url)
        if page.status_code == 200:
            rows = summary_rows(page.file_path.read_text(encoding="utf-8", errors="replace"))
            equipment = [f"{label}: {value}" for label, value in rows.items()]
            equipment.append(model.tagline)
        else:
            on_progress(
                f"{model.name} — its page returned {page.status_code}, so the habitation "
                f"findings could not be read. The product is still collected"
            )

        for product in products_for(model, groups, url=url):
            product.equipment = equipment
            reconciles, basis = _reconciles(product)
            if not reconciles:
                on_progress(f"{product.label} — DROPPED: {basis}")
                continue
            results.append(build_extracted(product, basis=basis))
            on_progress(
                f"{product.label} — £{product.model.base_price:,}, {product.berths} berth, "
                f"{product.base_vehicle_manufacturer or 'no base vehicle named'}"
            )
            for note in _notes(product):
                on_progress(note)

    on_progress(
        "NO MASS AND NO DIMENSION IS PROPOSED. Kaktus publish none anywhere — not on a "
        "model page, not in the configurator, and there is no brochure — so FMLV's MTPLM, "
        "mass in running order, payload, length, width and height all carry through "
        "untouched."
    )
    on_progress(
        "REJECT THE DERIVED PAYLOAD OF 0kg. FMLV holds MRO 3500 and MTPLM 3500 for every "
        "Kaktus, so the pipeline derives a payload of 0 and offers it against the 200kg "
        "and 400kg on record. The arithmetic is right and the conclusion is wrong: a "
        "campervan has a payload, so the figure at fault is the mass in running order, "
        "which cannot be 3500 if the MTPLM is. Kaktus publish nothing that can correct "
        "it. This will be proposed on EVERY run until they supply real masses — reject "
        "it each time rather than leaving it pending."
    )
    on_progress(
        "THERE IS NO ARITHMETIC SELF-CHECK. With no masses published there is nothing to "
        "test a parse against; the check here is structural, that the price came from a "
        "model's own basePrice rather than from the forty-odd option prices beside it."
    )
    if len(results) != EXPECTED_PRODUCTS:
        on_progress(
            f"expected {EXPECTED_PRODUCTS} products and collected {len(results)} — check "
            f"whether the range has changed"
        )
    on_progress(f"collected {len(results)} Kaktus campervan(s)")
    return results
