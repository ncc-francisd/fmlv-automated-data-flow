"""Robeta — six Slovenian campervans, read from the UK dealer who publishes the numbers.

`docs/adapters/robeta.md` is the survey; this is what it decided.

**The importer comes first.** The requester's instruction, 11 November 2026: *"given Cara
has got some technical information, we should get it from there first. And if there's some
missing, we then try and seek it from the European website."* That happens to be the best
source as well as the instructed one: Cara Motorhomes publish, per model, a plain HTML
table of MIRO, MTPLM, payload and all three dimensions beside a sterling price — and all
forty-two of those values matched FMLV's six rows on the day of the survey, because FMLV's
data was taken from these pages.

Four things are worth knowing before changing anything here.

* **`payload == MTPLM - MIRO` is the self-check**, and it is a real one: Cara print the
  three in three separate table rows, so a misread row breaks the arithmetic. See
  `_reconciles`.

* **Never read Cara's `/vehicle-details/` pages.** Those are individual units for sale —
  `new-robeta-apollo-for-sale-...-n447` — so a mass on one is that van's plate and that
  van's options, not the model's. The same URL shape also carries Sunlight, Adria,
  Auto-Trail, Coachman and VW stock, so a loose match would collect other manufacturers'
  vehicles outright. `RANGE_LINK` only ever matches `/robeta-motorhomes/the-range/`.

* **`berths`, `mh_passenger_seats_inc_driver` and `body_type` are NOT emitted**, and that
  is the whole open question of this adapter rather than an oversight. See
  `_narrate_open_questions`.

* **The factory sells more models than the UK gets.** `robeta-campervans.com` has a
  Hercules, a Dionysus and an Ananya; neither UK dealer lists any of them. The importer
  defines the range, so the roster is what Cara list, and `_check_factory_roster` narrates
  anything new rather than collecting it.
"""

from __future__ import annotations

import html as html_module
import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.model import Motorhome
from . import gearbox, habitation
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

__all__ = [
    "CARA_BASE_URL",
    "DEFAULT_RANGES",
    "EXPECTED_PRODUCTS",
    "FACTORY_BASE_URL",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "MODELS",
    "RobetaProduct",
    "collect",
    "factory_properties",
    "parse_range_page",
    "parse_roster",
]

#: The UK dealer, and the primary source.
CARA_BASE_URL = "https://www.caramotorhomes.co.uk"

#: The factory, in Slovenj Gradec, Slovenia. Used only for what Cara do not publish.
FACTORY_BASE_URL = "https://www.robeta-campervans.com"

#: `BASE_URL` is the factory, because that is the manufacturer this adapter is *for*.
#: Everything numeric comes from `CARA_BASE_URL`.
BASE_URL = FACTORY_BASE_URL

#: Byte-for-byte the `manufacturer` value in FMLV's export, and the NCC manufacturer
#: list's name at id 255. **One `t`** — the requester calls it "Robetta" in conversation
#: and neither system spells it that way.
MANUFACTURER = "Robeta"
MANUFACTURER_DISPLAY_NAME = "Robeta"

#: Where the roster is discovered. Cara's model pages appear in **no** sitemap, so the
#: links have to be followed out of the Robeta section itself.
RANGE_INDEX_URL = f"{CARA_BASE_URL}/robeta-motorhomes/the-range/"
ROBETA_SECTION_URL = f"{CARA_BASE_URL}/robeta-motorhomes/"

#: The factory's roster page, watched for a model the UK does not get.
FACTORY_LINEUP_URL = f"{FACTORY_BASE_URL}/model-lineup"

EXPECTED_PRODUCTS = 6


@dataclass(frozen=True)
class _Model:
    """One model: Cara's slug, FMLV's name, and the factory page that describes it."""

    slug: str
    #: FMLV holds the same string in `manufacturer_range` and `model` on all six — the
    #: doubling Nova forces on a product whose name is one word.
    name: str
    #: The factory page carrying this model's JSON-LD, relative to `FACTORY_BASE_URL`.
    #: The Schumacher Edition sits at the site root rather than under `/models/`.
    factory_path: str
    #: The name the factory's JSON-LD uses, which is not the FMLV name.
    factory_name: str


MODELS: tuple[_Model, ...] = (
    _Model("adonis", "Adonis", "/models/adonis", "ROBETA ADONIS"),
    _Model("apollo", "Apollo", "/models/apollo", "ROBETA APOLLO"),
    _Model("ares", "Ares", "/models/ares", "ROBETA ARES"),
    _Model("helios", "Helios", "/models/helios", "ROBETA HELIOS"),
    _Model("kronos", "Kronos", "/models/kronos", "ROBETA KRONOS"),
    _Model(
        "schumacher-edition",
        "Schumacher Edition",
        "/schumacher",
        "Robeta Schumacher Edition",
    ),
)

#: `(slug, label)` for `--range`. Every model is its own range here.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = tuple(
    (model.slug, model.name) for model in MODELS
)

_BY_SLUG = {model.slug: model for model in MODELS}

#: Models the factory sells that no UK dealer lists, with what each one is. Watched every
#: run by `_check_factory_roster`, never collected: the importer defines the range.
NOT_SOLD_IN_THE_UK: dict[str, str] = {
    "hercules": (
        "a new Mercedes-Benz model — the factory calls it a 'Private Mercedes-Benz grand "
        "tourer for two' and gave it a launch blog post. Neither Cara nor SC Sporthomes "
        "list it, and it has never been in FMLV: the February and November 2026 exports "
        "hold the same six products"
    ),
    "dionysus": (
        "named only in the factory contact form's model dropdown — no model page, no "
        "specification, and not on either UK dealer's site"
    ),
    "ananya": (
        "the 'glampervan', which has its own section of the factory site and a press page "
        "but is not sold through a UK dealer"
    ),
}


# --------------------------------------------------------------------------- #
# Reading Cara
# --------------------------------------------------------------------------- #

#: A link to one of Cara's Robeta model pages. **Deliberately narrow.** `/vehicle-details/`
#: on the same site is individual stock, Robeta's and five other manufacturers'.
RANGE_LINK = re.compile(r"/robeta-motorhomes/the-range/([a-z0-9-]+)/", re.I)

_TAG = re.compile(r"<[^>]+>")
_ROW = re.compile(r"(?is)<tr[^>]*>(.*?)</tr>")
_CELL = re.compile(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>")

#: `Price from £105,290`.
_PRICE = re.compile(r"Price\s*from\s*£\s*(?P<pounds>[\d,]+)", re.I)

#: The spec table's row labels, mapped to the `Motorhome` field each one fills.
_TABLE_FIELDS: dict[str, str] = {
    "miro (kg)": "mro_kilograms",
    "mtplm (kg)": "mtplm_kilograms",
    "payload (kg)": "mh_payload_kilograms",
    "height (mm)": "mh_height_mm",
    "width (mm)": "mh_width_mm",
    "length (mm)": "mh_length_mm",
}

#: The chassis, where Cara's prose names it — *"built on the Mercedes Sprinter chassis"*.
_CARA_CHASSIS = re.compile(
    r"built on the\s+(?P<make>Mercedes(?:-Benz)?|Fiat|Peugeot|Citro[eë]n|Ford|Renault|MAN|VW)\b",
    re.I,
)


def _text(fragment: str) -> str:
    return " ".join(html_module.unescape(_TAG.sub(" ", fragment)).split())


def _integer(raw: str) -> int | None:
    digits = re.sub(r"[^\d]", "", raw)
    return int(digits) if digits else None


def parse_roster(*pages: str) -> list[str]:
    """Every Robeta model slug Cara link, in first-seen order.

    Cara's model pages carry no `<loc>` in any of their eight sitemaps, so the roster is
    whatever the Robeta section links. Order is first-seen so a run reads the same way
    twice.
    """
    seen: list[str] = []
    for page in pages:
        for slug in RANGE_LINK.findall(page):
            lowered = slug.lower()
            if lowered not in seen:
                seen.append(lowered)
    return seen


@dataclass
class RobetaProduct:
    """One model as the two sites describe it, before it becomes a `Motorhome`."""

    name: str
    slug: str
    source_url: str

    rrp_pounds: int | None = None
    mro_kilograms: int | None = None
    mtplm_kilograms: int | None = None
    mh_payload_kilograms: int | None = None
    mh_length_mm: int | None = None
    mh_width_mm: int | None = None
    mh_height_mm: int | None = None
    base_vehicle: str | None = None

    #: Robeta's published configuration spans, e.g. `2 - 6`. Narrated, never proposed.
    sleeping_capacity: str | None = None
    seating_capacity: str | None = None
    #: The factory's `additionalProperty` block, for the habitation findings.
    factory: dict[str, str] = field(default_factory=dict)
    factory_url: str | None = None

    standard_lines: list[str] = field(default_factory=list)
    all_lines: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return f"{MANUFACTURER_DISPLAY_NAME} {self.name}"


def parse_range_page(page: str, model_name: str, slug: str, source_url: str) -> RobetaProduct:
    """One model from Cara's range page: the price, the masses and the dimensions.

    The table is ordinary `<tr><td>label</td><td>value</td></tr>`, which is why this
    adapter needs no browser and no PDF reader.
    """
    product = RobetaProduct(name=model_name, slug=slug, source_url=source_url)

    price = _PRICE.search(page)
    if price is not None:
        product.rrp_pounds = _integer(price.group("pounds"))

    for row in _ROW.findall(page):
        cells = [_text(cell) for cell in _CELL.findall(row)]
        cells = [cell for cell in cells if cell]
        if len(cells) < 2:
            continue
        field_name = _TABLE_FIELDS.get(cells[0].lower())
        if field_name is None:
            continue
        value = _integer(cells[1])
        if value is not None and getattr(product, field_name) is None:
            setattr(product, field_name, value)

    chassis = _CARA_CHASSIS.search(_text(page))
    if chassis is not None:
        product.base_vehicle = chassis.group("make")

    return product


# --------------------------------------------------------------------------- #
# Reading the factory
# --------------------------------------------------------------------------- #

_JSON_LD = re.compile(
    r'(?is)<script[^>]+type="application/ld\+json"[^>]*>(?P<payload>.*?)</script>'
)


def factory_properties(page: str) -> dict[str, dict[str, str]]:
    """`{product name: {property: value}}` for every schema.org Product on a factory page.

    The factory is a Next.js site that serves **static** HTML with JSON-LD in it, so this
    needs no browser. One page can carry several products: the Adonis's own page has no
    Product block of its own and instead embeds the whole five-model lineup array, which
    is why this returns a map rather than a single block.
    """
    found: dict[str, dict[str, str]] = {}
    for match in _JSON_LD.finditer(page):
        try:
            payload = json.loads(html_module.unescape(match.group("payload")))
        except ValueError:
            continue
        stack = [payload]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
                continue
            if not isinstance(node, dict):
                continue
            stack.extend(value for value in node.values() if isinstance(value, (dict, list)))
            if node.get("@type") != "Product":
                continue
            name = node.get("name")
            if not isinstance(name, str):
                continue
            properties: dict[str, str] = {}
            for entry in node.get("additionalProperty") or []:
                if not isinstance(entry, dict):
                    continue
                key, value = entry.get("name"), entry.get("value")
                if isinstance(key, str) and isinstance(value, str):
                    properties[key.strip()] = " ".join(value.split())
            if properties:
                found.setdefault(name.strip(), {}).update(properties)
    return found


#: The factory's own words for a chassis, in its `Base Vehicle` property.
_FACTORY_CHASSIS = re.compile(
    r"\b(Mercedes(?:-Benz)?|Fiat|Peugeot|Citro[eë]n|Ford|Renault|MAN|VW)\b", re.I
)


# --------------------------------------------------------------------------- #
# The self-check
# --------------------------------------------------------------------------- #


def _reconciles(product: RobetaProduct) -> tuple[bool, str]:
    """Whether Cara's three published masses agree: `payload == MTPLM - MIRO`.

    Cara print MIRO, MTPLM and payload in three separate table rows, so this is a genuine
    redundancy the source publishes against itself rather than a restatement. A row read
    out of order, a value landing on its neighbour's label or a stray digit all break it,
    and none of those would be visible downstream — the figures would still be plausible
    masses for a campervan.

    A product missing any of the three cannot be checked, and is **dropped** rather than
    passed through: all six publish all three, so an absence means the page changed shape
    and whatever was parsed from it is not trustworthy either.
    """
    masses = (product.mro_kilograms, product.mtplm_kilograms, product.mh_payload_kilograms)
    if any(mass is None for mass in masses):
        missing = [
            name
            for name, mass in zip(("MIRO", "MTPLM", "payload"), masses, strict=True)
            if mass is None
        ]
        return False, f"Cara's table is missing {', '.join(missing)}, so nothing checks it"

    mro, mtplm, payload = masses
    assert mro is not None and mtplm is not None and payload is not None  # noqa: S101
    expected = mtplm - mro
    if expected != payload:
        return False, (
            f"MTPLM {mtplm:,}kg less MIRO {mro:,}kg is {expected:,}kg, but Cara publish a "
            f"payload of {payload:,}kg"
        )
    return True, (
        f"MTPLM {mtplm:,}kg less MIRO {mro:,}kg is the published payload of {payload:,}kg"
    )


# --------------------------------------------------------------------------- #
# Building the product
# --------------------------------------------------------------------------- #

#: Factory properties worth quoting into the run for whoever types habitation in.
_FINDING_PROPERTIES = (
    "Main Bed Dimensions",
    "Additional Bed Dimensions",
    "Pop-up Roof Bed Dimensions",
    "Bed Size",
    "Refrigerator",
    "Cooker/Sink",
    "Fresh Water Tank",
    "Wastewater/Black Water",
)


def _build_extracted_motorhome(product: RobetaProduct) -> ExtractedMotorhome:
    """One model as a `Motorhome`, with the provenance a reviewer reads beside each field.

    **Three fields are deliberately not emitted**, and this is the adapter's one open
    question rather than a gap in the sources:

    * `berths` — Robeta publish a *configuration span* (`Sleeping Capacity 2 - 6`), not a
      berth count for the vehicle as built, and the pop-up roof that supplies the upper end
      is called an **upgrade** in identical words on every factory model page. Cara say the
      same on the Adonis: *"looking to travel with 4 passengers, why not add a pop top?"*
    * `mh_passenger_seats_inc_driver` — the same span problem, and the two ends swap round
      between models. The Adonis's *"for Two" package replaces the travelling seats*, so
      its standard is the **upper** figure; the Ares *"can be upgraded to seat up to 5"*,
      so its standard is the **lower**. One rule cannot serve both.
    * `body_type` — all six clear the 2,300mm high-top threshold on height alone, so the
      only live question is whether the pop-up roof is standard, which is the same
      unresolved question.

    Emitting nothing leaves FMLV's own figures untouched, which is the right failure here:
    the requester believes the roofs are standard and the published sources say they are an
    option, and until that is settled a proposal either way would be a guess shipped to a
    live site. `_narrate_open_questions` puts the evidence in front of the reviewer every
    run instead.
    """
    features = habitation.features_from(product.standard_lines)
    automatic = gearbox.automatic_available_from(product.all_lines)

    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.name,
        model=product.name,
        base_vehicle_manufacturer=fmlv_base_vehicle(product.base_vehicle),
        rrp_pounds=product.rrp_pounds,
        mro_kilograms=product.mro_kilograms,
        mtplm_kilograms=product.mtplm_kilograms,
        mh_payload_kilograms=product.mh_payload_kilograms,
        mh_length_mm=product.mh_length_mm,
        mh_width_mm=product.mh_width_mm,
        mh_height_mm=product.mh_height_mm,
        automatic_available=automatic[0] if automatic else None,
        # Habitation: findings, never proposals — see `docs/adapters/README.md`.
        heating=features["heating"].value if "heating" in features else None,
        refrigeration=(
            features["refrigeration"].value if "refrigeration" in features else None
        ),
        shower_toilet_separated=(
            features["shower_toilet_separated"].value
            if "shower_toilet_separated" in features
            else None
        ),
        bed_types=features["bed_types"].value if "bed_types" in features else [],
        microwave=features["microwave"].value if "microwave" in features else None,
    )

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str, *, url: str | None = None) -> None:
        provenance[field_name] = Provenance(
            source_url=url or product.source_url,
            snippet=f"{product.label} — {snippet}",
        )

    record(
        "manufacturer_range",
        f"range {product.name!r}. FMLV holds the same string as the model on all six "
        f"Robeta products, which is what Nova forces on a one-word name",
    )
    if product.rrp_pounds is not None:
        record(
            "rrp_pounds",
            f"'Price from £{product.rrp_pounds:,}' on Cara Motorhomes' own range page. "
            f"Cara are one of two UK Robeta dealers and the only one publishing a price — "
            f"SC Sporthomes list the brand and no figures at all. The factory's own price "
            f"is in euros and is not used",
        )
    if product.mro_kilograms is not None:
        record("mro_kilograms", f"Cara's specification table, 'MIRO (kg) {product.mro_kilograms}'")
    if product.mtplm_kilograms is not None:
        record(
            "mtplm_kilograms", f"Cara's specification table, 'MTPLM (kg) {product.mtplm_kilograms}'"
        )
    if product.mh_payload_kilograms is not None:
        reconciles, note = _reconciles(product)
        record(
            "mh_payload_kilograms",
            f"Cara's specification table, 'Payload (kg) {product.mh_payload_kilograms}' — "
            f"and it reconciles: {note}" if reconciles else note,
        )
    for field_name, label in (
        ("mh_length_mm", "Length"),
        ("mh_width_mm", "Width"),
        ("mh_height_mm", "Height"),
    ):
        value = getattr(product, field_name)
        if value is not None:
            record(field_name, f"Cara's specification table, '{label} (mm) {value}'")
    if product.base_vehicle is not None:
        record(
            "base_vehicle_manufacturer",
            f"the chassis is named as {product.base_vehicle}",
        )
    if automatic is not None:
        record("automatic_available", gearbox.provenance_note(automatic))

    for field_name, feature in features.items():
        detail = f" — {feature.note}" if feature.note else ""
        provenance[field_name] = Provenance(
            source_url=product.factory_url or product.source_url,
            snippet=f"{product.label} — the specification says {feature.snippet!r}{detail}",
        )

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


# --------------------------------------------------------------------------- #
# The run
# --------------------------------------------------------------------------- #


def _feature_value(value: object) -> str:
    """One habitation value as a reviewer would type it into FMLV."""
    if isinstance(value, list):
        return ";".join(_feature_value(item) for item in value) or "none"
    return getattr(value, "value", str(value))


def _narrate_open_questions(
    product: RobetaProduct, on_progress: Callable[[str], None]
) -> None:
    """Put the berth, seat and roof evidence in front of the reviewer, every run.

    These three fields are not proposed — see `_build_extracted_motorhome` — so this is
    the only place the question is visible. Saying it once per product per run is
    deliberate: it is the thing standing between this adapter and a complete one.
    """
    spans = []
    if product.sleeping_capacity:
        spans.append(f"Sleeping Capacity '{product.sleeping_capacity}'")
    if product.seating_capacity:
        spans.append(f"Seating Capacity '{product.seating_capacity}'")
    if spans:
        # Only say it where there is a pop-up roof to say it about: the Schumacher Edition
        # has none, and claiming otherwise would invent a reason for its figures.
        roof = (
            ". The factory calls the pop-up roof that supplies the upper figure an upgrade"
            if "Pop-up Roof Bed Dimensions" in product.factory
            else ""
        )
        on_progress(
            f"{product.label} — OPEN: Robeta publish {' and '.join(spans)}, a span of "
            f"configurations rather than the vehicle as built. berths, travel seats and "
            f"body_type are therefore NOT proposed and FMLV's own figures stand{roof}"
        )

    quoted = [
        f"{name} '{product.factory[name]}'"
        for name in _FINDING_PROPERTIES
        if name in product.factory
    ]
    if quoted:
        on_progress(f"{product.label} — habitation, as Robeta state it: " + " | ".join(quoted))

    # What those words were *read as*. Said out loud because `store.changes` records
    # habitation findings for a **new** product only, and all six Robeta products are
    # matched — so without this the reading never reaches a reviewer at all. The
    # refrigeration one matters: FMLV held `fridge` on five of the six, and the requester
    # confirmed on 11 November 2026 that these refrigerators do have a freezer section.
    features = habitation.features_from(product.standard_lines)
    if features:
        on_progress(
            f"{product.label} — read as: "
            + " | ".join(
                f"{name} = {_feature_value(feature.value)}"
                for name, feature in sorted(features.items())
            )
            + ". These are findings on a matched product, so the review will NOT show them"
        )


def _check_factory_roster(
    http: Fetcher, on_progress: Callable[[str], None]
) -> None:
    """Narrate a factory model no UK dealer lists, and one that has started to be listed."""
    result = http.fetch(FACTORY_LINEUP_URL)
    if result.status_code != 200:
        on_progress(
            f"could not read the factory lineup (HTTP {result.status_code}), so a new "
            f"model would go unnoticed this run"
        )
        return
    page = result.file_path.read_text(encoding="utf-8", errors="replace").lower()
    for slug, why in NOT_SOLD_IN_THE_UK.items():
        if slug in page:
            on_progress(f"factory model NOT collected — {slug}: {why}")


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 - both sites serve static HTML
    snapshot_dir: Path,  # noqa: ARG001 - `Fetcher` snapshots every request already
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every Robeta campervan Cara Motorhomes list for the UK."""
    wanted = {entry[-1] for entry in ranges}

    # --- the roster, from Cara ---------------------------------------------
    pages: list[str] = []
    for url in (ROBETA_SECTION_URL, RANGE_INDEX_URL):
        result = http.fetch(url)
        if result.status_code == 200:
            pages.append(result.file_path.read_text(encoding="utf-8", errors="replace"))
        else:
            on_progress(f"{url} returned HTTP {result.status_code}")
    if not pages:
        raise RuntimeError(
            f"neither {ROBETA_SECTION_URL} nor {RANGE_INDEX_URL} could be read, and Cara's "
            f"model pages are in no sitemap, so there is no other way to the roster"
        )

    slugs = parse_roster(*pages)
    on_progress(f"Cara list {len(slugs)} Robeta model(s): {', '.join(slugs)}")
    for slug in slugs:
        if slug not in _BY_SLUG:
            on_progress(
                f"NEW MODEL on Cara's Robeta range that this adapter does not know: "
                f"/robeta-motorhomes/the-range/{slug}/"
            )
    for model in MODELS:
        if model.slug not in slugs:
            on_progress(f"Cara no longer list {model.name} ({model.slug})")

    _check_factory_roster(http, on_progress)

    # --- the factory's lineup block, which carries the Adonis's properties --
    lineup = http.fetch(FACTORY_LINEUP_URL)
    factory_all: dict[str, dict[str, str]] = {}
    if lineup.status_code == 200:
        factory_all.update(
            factory_properties(lineup.file_path.read_text(encoding="utf-8", errors="replace"))
        )

    # --- each model ---------------------------------------------------------
    extracted: list[ExtractedMotorhome] = []
    for model in MODELS:
        if model.name not in wanted:
            continue
        url = f"{RANGE_INDEX_URL}{model.slug}/"
        result = http.fetch(url)
        if result.status_code != 200:
            on_progress(f"DROPPED {model.name}: Cara returned HTTP {result.status_code} for {url}")
            continue
        page = result.file_path.read_text(encoding="utf-8", errors="replace")
        product = parse_range_page(page, model.name, model.slug, url)
        product.all_lines = [
            " ".join(line.split()) for line in gearbox.lines_from_page(page)
        ]

        # The factory, for what Cara do not publish.
        factory_url = f"{FACTORY_BASE_URL}{model.factory_path}"
        factory_page = http.fetch(factory_url)
        properties = dict(factory_all.get(model.factory_name, {}))
        if factory_page.status_code == 200:
            body = factory_page.file_path.read_text(encoding="utf-8", errors="replace")
            properties.update(factory_properties(body).get(model.factory_name, {}))
            lines = [" ".join(line.split()) for line in gearbox.lines_from_page(body)]
            product.standard_lines = [line for line in lines if line]
            product.all_lines.extend(product.standard_lines)
            product.factory_url = factory_url
        else:
            on_progress(
                f"{model.name}: the factory page returned HTTP {factory_page.status_code}, "
                f"so the habitation findings are missing this run"
            )
        product.factory = properties
        product.sleeping_capacity = properties.get("Sleeping Capacity")
        product.seating_capacity = properties.get("Seating Capacity")
        if product.base_vehicle is None:
            stated = properties.get("Base Vehicle", "")
            match = _FACTORY_CHASSIS.search(stated)
            if match is not None:
                product.base_vehicle = match.group(1)

        reconciles, note = _reconciles(product)
        if not reconciles:
            on_progress(f"DROPPED {product.label}: {note}")
            continue

        extracted.append(_build_extracted_motorhome(product))
        price = f"£{product.rrp_pounds:,}" if product.rrp_pounds else "NO PRICE"
        on_progress(
            f"{product.label}: {price}, MIRO {product.mro_kilograms:,}kg, MTPLM "
            f"{product.mtplm_kilograms:,}kg, payload {product.mh_payload_kilograms:,}kg — "
            f"{note}"
        )
        _narrate_open_questions(product, on_progress)

    if wanted == {model.name for model in MODELS} and len(extracted) != EXPECTED_PRODUCTS:
        on_progress(
            f"collected {len(extracted)} products where Cara list {EXPECTED_PRODUCTS}"
        )
    return extracted
