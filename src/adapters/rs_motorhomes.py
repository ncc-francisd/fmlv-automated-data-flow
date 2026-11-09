"""RS Motorhomes — four bespoke luxury coachbuilts, from PDFs the site never links to.

`docs/adapters/rs-motorhomes.md` is the survey; this is what it decided.

**The documents are unlinked.** Every model page on rsmotorhomes.com is marketing: no
specification table, no weight, no price, and no dimension outside prose like *"a total
length of 30ft (9.1 Metres)"*. Both documents a buyer would want sit behind an email form.
The site's own WordPress media library answers without one, and `MEDIA_URL` is the whole
survey — it lists every non-image upload with its title and date, among them a current
*"RS <model> Specification Document"* for three of the four models.

**Take the date from the listing and never from the path.** The paths lie in both
directions: the 2027 specification documents are filed under `/2026/02/` and a 2026
brochure under `/2024/01/`.

Three things make this adapter unlike the others:

* **There is no arithmetic self-check.** No mass in running order and no payload is
  published for any model, so the payload reconciliation that guards every other adapter
  does not exist here. `_reconciles` falls back on three weaker checks — the price is
  printed twice per document, the gross train weight should exceed the gross vehicle
  weight by the stated towing capacity, and the cover's chassis should agree with the
  chassis table's. See `_discrepancies`, and note that the third already fires.
* **One model has no current document.** The Evolution is read from the HTML table at
  `EVOLUTION_SPEC_URL`, which is of 2022–23 vintage and prints **two rows both labelled
  `Gross Vehicle Weight`**, 7,200kg and 10.5 tonnes. A label cannot choose between them,
  so its mass is refused rather than guessed — see `parse_specification_page`.
* **The site is also a dealership.** `/listings/` and `/preowned-motorhomes/` are RS Sales
  Nottingham's used stock and include Bailey, Carado, Dethleffs and Swift vehicles beside
  used RS ones. Nothing here ever reads them: a used `rs-endeavour-4` listing is one
  unit's plate, not the model's specification.
"""

from __future__ import annotations

import html as html_module
import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from ..fetch.http import Fetcher
from ..fetch.pdf import extract_text
from ..product_model.model import Motorhome
from . import gearbox, habitation
from .base import ExtractedMotorhome, Provenance, fmlv_base_vehicle

__all__ = [
    "BASE_URL",
    "DEFAULT_RANGES",
    "EVOLUTION_SPEC_URL",
    "EXPECTED_LAYOUTS",
    "FMLV_RANGE",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "MEDIA_URL",
    "MODELS",
    "ORPHANED_PAGES",
    "RSProduct",
    "collect",
    "parse_roster",
    "parse_specification_page",
    "parse_specification_pdf",
    "specification_documents",
]

BASE_URL = "https://www.rsmotorhomes.com"
MANUFACTURER = "RS Motorhomes"
MANUFACTURER_DISPLAY_NAME = "RS Motorhomes"

#: FMLV files all four models under one range, and the export spells it `RS`. There is no
#: second range to keep it apart from, so this is the only label `--range` has to offer.
FMLV_RANGE = "RS"

#: `(key, label)` for `--range`. One entry, because one range.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (("rs", FMLV_RANGE),)

#: The roster, from RS's own `/luxury-motorhomes/` index: Endeavour, Elysian, Evolution,
#: Envoy. It also matches the active FMLV export exactly, which is the stronger check of
#: the two — see `ORPHANED_PAGES` for the page that would otherwise make it five.
EXPECTED_LAYOUTS = 4

#: Where the specification documents are found, since nothing links them. WordPress serves
#: its media library over the REST API without authentication, and `media_type=application`
#: narrows it to the non-image uploads.
MEDIA_URL = (
    f"{BASE_URL}/wp-json/wp/v2/media"
    "?per_page=100&media_type=application&_fields=id,source_url,title,date"
)

#: The models index, kept for provenance rather than parsing — the roster it states is in
#: `MODELS` and the figures are not on it.
MODELS_INDEX_URL = f"{BASE_URL}/luxury-motorhomes/"

#: The Evolution's only source. The equivalent pages for the other three do not exist,
#: including `/rs-elysian-specifications/`, which the Elysian's own page still links to and
#: which returns 404.
EVOLUTION_SPEC_URL = f"{BASE_URL}/rs-evolution-specifications/"

#: Models that are not collected, mapped to what was established about each. Watched every
#: run by `parse_roster`, never fetched.
#:
#: **`Emotion` is here on a careful reading of the index, not on its absence from it.** A
#: `DISCOVER THE RS EMOTION` button does appear on `/luxury-motorhomes/` — but on the
#: *Bespoke* block at the foot of the page, which is about custom adaptations and has no
#: vehicle of its own. The four real models each have a heading of their own above their
#: prose and their own button; the Emotion has a button and no heading, which is a stale
#: link rather than a listing. That is why `parse_roster` reads headings.
ORPHANED_PAGES: dict[str, str] = {
    "Emotion": (
        "the RS Emotion, an 18-tonne Mercedes-Benz Antos at 12.1m with four slide-outs. "
        "Its page resolves and a leftover button on the index's Bespoke block still links "
        "it, but it has no section of its own on the index, it is absent from the "
        "navigation, it renders a PHP warning, and it is not in the active FMLV export. "
        "Treated as a withdrawn model on the requester's agreement of 9 November 2026"
    ),
}


@dataclass(frozen=True)
class _ModelSource:
    """One model, and the title its specification document carries in the media library."""

    #: FMLV's `model` string. The range carries the `RS`, so the model does not repeat it.
    model: str
    #: The media library title to match, or `None` for the Evolution, which has no
    #: document and is read from `EVOLUTION_SPEC_URL` instead.
    media_title: str | None


#: The four models in the order the index lists them.
MODELS: tuple[_ModelSource, ...] = (
    _ModelSource("Endeavour", "RS Endeavour Specification Document"),
    _ModelSource("Elysian", "RS Elysian Specification Document"),
    _ModelSource("Evolution", None),
    _ModelSource("Envoy", "RS Envoy Specification Document"),
)


# --------------------------------------------------------------------------- #
# Finding the documents
# --------------------------------------------------------------------------- #


def specification_documents(payload: str) -> dict[str, tuple[str, str]]:
    """`{media title: (url, upload date)}` for every PDF the media library lists.

    Keyed on the title because that is the only field that names the model: the URL's
    folder is the month WordPress happened to file it under, which on this site is wrong
    for every current document.

    Where a title appears twice, the **newest upload wins**, so a reissue under the same
    name is picked up without an edit here.
    """
    try:
        items = json.loads(payload)
    except ValueError:
        return {}
    if not isinstance(items, list):
        return {}

    found: dict[str, tuple[str, str]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        url = item.get("source_url")
        if not isinstance(url, str) or not url.lower().endswith(".pdf"):
            continue
        rendered = item.get("title")
        title = rendered.get("rendered") if isinstance(rendered, dict) else rendered
        if not isinstance(title, str):
            continue
        title = " ".join(html_module.unescape(title).split())
        date = item.get("date") if isinstance(item.get("date"), str) else ""
        if title in found and found[title][1] >= date:
            continue
        found[title] = (url, date)
    return found


# --------------------------------------------------------------------------- #
# Reading one document
# --------------------------------------------------------------------------- #

#: A mass as any of the three ways these documents write one: `7,200kg`, `16 ton`,
#: `10.5 Tonnes`. The unit is required — a bare number next to a weight label is not
#: trusted, because on this site it is as likely to be a litre count or a millimetre.
_MASS = re.compile(r"([\d,]+(?:\.\d+)?)\s*(kg|kilograms?|tonnes?|tons?)\b", re.I)

#: A dimension in millimetres, which is the only way either source writes one.
_MILLIMETRES = re.compile(r"([\d,]+)\s*mm\b", re.I)

#: The cover price. Printed once here and once in the body, which is check one of three.
_COVER_PRICE = re.compile(r"From\s+£\s*([\d,]+)\s*(?:inc|incl)", re.I)

#: The body price, under the `STANDARD RS <MODEL>` heading. All four model names are one
#: word, which is what lets this span the line break with `\s+`.
_BODY_PRICE = re.compile(r"STANDARD\s+RS\s+[A-Za-z]+\s+£\s*([\d,]+)")

#: The cover's own claim about the chassis: the line immediately above the cover price.
#: It is **not** labelled, which is why it cannot be confused with the chassis table's
#: `Base Vehicle` row — and why it is worth checking, since on the Envoy the two disagree.
_COVER_CHASSIS = re.compile(r"\n[ \t]*([^\n]+?)[ \t]*\n[ \t]*From\s+£\s*[\d,]+\s*(?:inc|incl)", re.I)

#: Where the standard specification stops and the priced options begin. Everything after
#: this is excluded from the habitation read, because an option is not a feature of the
#: vehicle — `habitation.usable_lines` drops a line that marks itself as an extra, and
#: nothing in these tables does.
_OPTIONS_HEADING = re.compile(r"TAILOR\s+YOUR|Optional\s+Extras", re.I)

#: The berth claim where it is written as a sentence rather than against a label, which is
#: how the HTML table puts it. Narrated, never recorded — see `_build_extracted_motorhome`.
_CAPACITY_SENTENCE = re.compile(r"Comfortably\s+accommodates\s+up\s+to\s+\d+\s+people", re.I)

#: A model named on its own, as the index's section headings and the site navigation both
#: do: a line reading exactly `RS Endeavour` or `RS ENDEAVOUR`.
#:
#: **Both cases are matched and the result is title-cased**, so the two agree instead of
#: reading as eight models. Taking the navigation as well is deliberate — it is a second
#: roster, it lists the same four, and a model appearing in one but not the other is worth
#: hearing about. What neither carries is `DISCOVER THE RS EMOTION`, the stale button that
#: a link-following roster would mistake for a fifth vehicle.
_MODEL_HEADING = re.compile(r"^RS\s+([A-Za-z]+)$", re.M)

#: Rear belts offered as a layout option, which three of the four documents say and the
#: Envoy's does not. Never changes a count — see `_CAB_SEATS`.
_OPTIONAL_REAR_BELTS = re.compile(
    r"[Rr]ear\s+seatbelts\s+available\s+depending\s+on\s+layout", re.I
)

#: The cab seating, as each document states it, mapped to **belted travel seats including
#: the driver**. Deliberately a closed vocabulary of the exact phrases met rather than a
#: pattern: the alternative is inferring a seat count from prose, and a wrong one here is
#: a claim about how many people may legally travel.
#:
#: Rear belts are excluded on purpose. Three of the four documents offer them as *"rear
#: seatbelts available depending on layout"*, which is an option, and the settled rule
#: counts three-point belts the maker states as fitted — never ones a layout might add.
#:
#: **Each phrase carries its own sentence**, because the two are not the same claim: a
#: *single passenger seat* is one seat beside the driver's, and *two cab seats* is two
#: seats in total. Both come to two, and a shared wording would have said the Envoy has
#: three.
_CAB_SEATS: tuple[tuple[re.Pattern[str], int, str], ...] = (
    (
        re.compile(r"Passenger\s+Seat\s+Single\s+passenger\s+seat", re.I),
        2,
        "'Passenger Seat Single passenger seat' — one beside the driver's",
    ),
    (
        re.compile(r"Cab\s+Seats\s+Two\s+cab\s+seats", re.I),
        2,
        "'Cab Seats Two cab seats' — the driver's among them",
    ),
    (
        re.compile(r"^\s*Single\s+Passenger\s+Seat\s*$", re.I | re.M),
        2,
        "'Single Passenger Seat' — one beside the driver's",
    ),
)


def _number(raw: str) -> float:
    return float(raw.replace(",", ""))


def _mass_kilograms(value: str) -> int | None:
    """`7,200kg` -> 7200, `16 ton` -> 16000, `10.5 Tonnes` -> 10500; anything else `None`."""
    match = _MASS.search(value)
    if match is None:
        return None
    amount = _number(match.group(1))
    if match.group(2).lower().startswith(("ton", "tonne")):
        amount *= 1000
    return int(round(amount))


def _millimetres(value: str) -> int | None:
    match = _MILLIMETRES.search(value)
    return int(_number(match.group(1))) if match else None


def _labelled(text: str, label: str) -> list[str]:
    """Every value printed against `label`, in document order.

    Both sources write a row as the label followed by its value — `Overall Length 9,100mm`
    in the PDFs, `Overall Length – 9448mm` on the HTML page — so one pattern reads both.

    **It returns a list, not a value.** The Evolution's page prints two rows both labelled
    `Gross Vehicle Weight` and they differ by 3.3 tonnes, so a caller that takes the first
    match would record one of two masses with equal confidence. Callers decide what to do
    with more than one; `_single` refuses.
    """
    pattern = re.compile(
        rf"^[ \t]*{re.escape(label)}[ \t]*[-–—:]?[ \t]*(.+?)[ \t]*$",
        re.I | re.M,
    )
    return [match.group(1) for match in pattern.finditer(text)]


def _single(text: str, label: str) -> str | None:
    """The one value printed against `label`, or `None` where the document prints two.

    Identical repeats are fine — the Evolution's page prints `Engine Capacity – 4500cc`
    twice — so only *differing* values are refused.
    """
    values = _labelled(text, label)
    distinct = {" ".join(value.split()) for value in values}
    if len(distinct) != 1:
        return None
    return next(iter(distinct))


@dataclass
class RSProduct:
    """One model as its source states it, before anything is decided about FMLV's columns."""

    model: str
    source_url: str
    #: The chassis table's `Base Vehicle`, verbatim — `Iveco Daily 72-210`, `DAF XB – 16000KG`.
    base_vehicle: str | None = None
    #: The cover's unlabelled chassis line, where there is a cover. Checked against
    #: `base_vehicle` and never recorded: on the Envoy the cover is simply wrong.
    cover_chassis: str | None = None
    mh_length_mm: int | None = None
    mh_width_mm: int | None = None
    mh_height_mm: int | None = None
    #: Gross vehicle weight, which is FMLV's MTPLM. `None` where the source prints two
    #: contradictory ones.
    mtplm_kilograms: int | None = None
    #: Gross train weight, used only to check the towing capacity. Never recorded: FMLV
    #: has no column for it, and reading it as a mass is the mistake that put 10,500kg in
    #: the Evolution's MTPLM.
    gross_train_kilograms: int | None = None
    towing_capacity_kilograms: int | None = None
    mh_passenger_seats_inc_driver: int | None = None
    seats_snippet: str | None = None
    #: Whether this document offers rear belts as a layout option, which only three of the
    #: four do. It changes nothing about the count — an optional belt is never counted —
    #: and only decides whether the provenance explains itself that way.
    offers_optional_rear_belts: bool = False
    rrp_pounds: int | None = None
    #: What the two printings of the price said, for `_reconciles`.
    cover_price_pounds: int | None = None
    body_price_pounds: int | None = None
    #: The berth claim, narrated but never recorded — see `collect`.
    capacity_claim: str | None = None
    #: The standard-specification prose, for the habitation findings and the gearbox.
    standard_lines: tuple[str, ...] = ()
    #: Every line of the document, including the options, for the gearbox read only.
    all_lines: tuple[str, ...] = ()
    #: Labels the source printed more than one differing value for.
    ambiguous_labels: tuple[str, ...] = field(default_factory=tuple)

    @property
    def label(self) -> str:
        return f"{FMLV_RANGE} {self.model}"


def _read_common(product: RSProduct, text: str) -> None:
    """The rows both sources print, read into `product`."""
    for label, attribute in (
        ("Overall Length", "mh_length_mm"),
        ("Overall Width", "mh_width_mm"),
        ("Overall Height", "mh_height_mm"),
    ):
        value = _single(text, label)
        if value is None:
            if _labelled(text, label):
                product.ambiguous_labels += (label,)
            continue
        setattr(product, attribute, _millimetres(value))

    gross = _single(text, "Gross Vehicle Weight")
    if gross is None:
        if _labelled(text, "Gross Vehicle Weight"):
            product.ambiguous_labels += ("Gross Vehicle Weight",)
    else:
        product.mtplm_kilograms = _mass_kilograms(gross)

    train = _single(text, "Gross Train Weight")
    if train is not None and "towing" not in train.lower():
        # The Envoy writes `Gross Train Weight 12-ton towing capacity`, which is not a
        # train weight at all. A row that contradicts its own label is not read.
        product.gross_train_kilograms = _mass_kilograms(train)

    towing = _single(text, "Towing Capacity")
    if towing is not None:
        product.towing_capacity_kilograms = _mass_kilograms(towing)

    capacity = _single(text, "Capacity")
    if capacity is None:
        # The HTML table has no `Capacity` label; it states the claim as a bare sentence.
        bare = _CAPACITY_SENTENCE.search(text)
        capacity = bare.group(0).strip() if bare else None
    if capacity is not None:
        product.capacity_claim = capacity

    product.offers_optional_rear_belts = bool(_OPTIONAL_REAR_BELTS.search(text))

    for pattern, seats, phrase in _CAB_SEATS:
        if pattern.search(text):
            product.mh_passenger_seats_inc_driver = seats
            product.seats_snippet = phrase
            break


def parse_specification_pdf(text: str, model: str, source_url: str) -> RSProduct:
    """One model from its 2027 specification document.

    The options table is cut off before the habitation read: these documents put every
    priced extra in a table of its own with no per-line marker, so a reviewer would
    otherwise be told the vehicle has an external shower because £500 buys one.
    """
    product = RSProduct(model=model, source_url=source_url)

    standard = _OPTIONS_HEADING.split(text, maxsplit=1)[0]
    product.standard_lines = tuple(
        line.strip() for line in standard.splitlines() if line.strip()
    )
    product.all_lines = tuple(line.strip() for line in text.splitlines() if line.strip())

    base_vehicle = _single(text, "Base Vehicle")
    if base_vehicle is not None:
        product.base_vehicle = base_vehicle
    cover = _COVER_CHASSIS.search(text)
    if cover is not None:
        product.cover_chassis = " ".join(cover.group(1).split())

    _read_common(product, text)

    cover_price = _COVER_PRICE.search(text)
    if cover_price is not None:
        product.cover_price_pounds = int(_number(cover_price.group(1)))
    body_price = _BODY_PRICE.search(text)
    if body_price is not None:
        product.body_price_pounds = int(_number(body_price.group(1)))
    if product.cover_price_pounds == product.body_price_pounds:
        product.rrp_pounds = product.cover_price_pounds

    return product


def parse_roster(index_html: str) -> tuple[str, ...]:
    """The models `/luxury-motorhomes/` names, as FMLV spells them.

    **Headings, not links.** The index carries a `DISCOVER THE RS EMOTION` button on its
    *Bespoke* block, which is about custom adaptations and names no vehicle of its own, so
    a link-following roster would report five models where RS sell four. Each real model
    is named on a line of its own, in the page's headings and again in the navigation; the
    withdrawn one is not.
    """
    text = "\n".join(gearbox.lines_from_page(index_html))
    found = (name.title() for name in _MODEL_HEADING.findall(text))
    return tuple(dict.fromkeys(found))


def parse_specification_page(html: str, model: str, source_url: str) -> RSProduct:
    """One model from an on-site `*-specifications` HTML table, which is the Evolution's.

    The table's cells are read as text rather than as markup, because the rows are not
    `<th>`/`<td>` pairs: each is one cell reading `Label – Value`. `lines_from_page` is
    borrowed from `gearbox` for the split — it is the project's one place that knows which
    tags end a line of displayed text, and duplicating that list here is how the two would
    drift apart.
    """
    text = "\n".join(gearbox.lines_from_page(html))
    product = RSProduct(model=model, source_url=source_url)
    product.standard_lines = tuple(
        line.strip() for line in text.splitlines() if line.strip()
    )
    product.all_lines = product.standard_lines

    base_vehicle = _single(text, "Base Vehicle")
    if base_vehicle is not None:
        product.base_vehicle = base_vehicle

    _read_common(product, text)
    return product


# --------------------------------------------------------------------------- #
# The checks
# --------------------------------------------------------------------------- #


def _reconciles(product: RSProduct) -> tuple[bool, str]:
    """Whether `product` is worth proposing at all.

    **There is no arithmetic here, because RS publish none.** No model's mass in running
    order or payload is stated anywhere, so MTPLM minus MRO cannot be checked against a
    payload the way every other adapter checks it. What is left is a shape test: a
    document that yielded no dimension at all has not been read, whatever else it gave.
    """
    dimensions = (product.mh_length_mm, product.mh_width_mm, product.mh_height_mm)
    if all(value is None for value in dimensions):
        return False, (
            "not one of its length, width or height could be read, so the document's "
            "shape has changed and nothing it gave can be trusted"
        )
    if product.base_vehicle is None:
        return False, (
            "it states no base vehicle, which every edition of this document has carried "
            "and which FMLV requires"
        )
    return True, ""


def _discrepancies(product: RSProduct) -> list[str]:
    """Everything the source says about itself that does not hold together.

    None of these drops the product. Each is a statement by RS that contradicts another
    statement by RS, and a reviewer needs to see it rather than have it silently resolved.
    """
    notes: list[str] = []

    if (
        product.cover_price_pounds is not None
        and product.body_price_pounds is not None
        and product.cover_price_pounds != product.body_price_pounds
    ):
        notes.append(
            f"its cover says £{product.cover_price_pounds:,} and its own standard-"
            f"specification heading says £{product.body_price_pounds:,}. NO PRICE IS "
            f"RECORDED while the document disagrees with itself"
        )
    elif product.cover_price_pounds is None and product.body_price_pounds is None:
        notes.append("it prints no price, so FMLV's own figure is left alone")

    if product.cover_chassis and product.base_vehicle:
        cover = product.cover_chassis.split()[0].lower()
        table = product.base_vehicle.split()[0].lower()
        if cover != table:
            notes.append(
                f"its COVER names a {product.cover_chassis!r} and its chassis table names "
                f"a {product.base_vehicle!r}. The table is the vehicle and the cover is a "
                f"leftover; the table is what is recorded"
            )

    if (
        product.gross_train_kilograms is not None
        and product.mtplm_kilograms is not None
        and product.towing_capacity_kilograms is not None
    ):
        implied = product.gross_train_kilograms - product.mtplm_kilograms
        if implied != product.towing_capacity_kilograms:
            notes.append(
                f"its gross train weight {product.gross_train_kilograms:,}kg minus its "
                f"gross vehicle weight {product.mtplm_kilograms:,}kg leaves {implied:,}kg "
                f"where it states a towing capacity of "
                f"{product.towing_capacity_kilograms:,}kg. Where the document also gives a "
                f"reduced figure for the automatic, the train weight is the automatic's"
            )

    for label in product.ambiguous_labels:
        notes.append(
            f"it prints MORE THAN ONE differing value against {label!r}, so that field is "
            f"REFUSED rather than guessed. A label cannot choose between two values and "
            f"neither can this adapter"
        )

    if product.mtplm_kilograms is None and "Gross Vehicle Weight" not in product.ambiguous_labels:
        notes.append("no gross vehicle weight could be read, so FMLV's MTPLM is left alone")

    if product.mh_passenger_seats_inc_driver is None:
        notes.append(
            "its cab seating is not stated in any wording this adapter recognises, so no "
            "travel-seat count is proposed"
        )

    return notes


# --------------------------------------------------------------------------- #
# Building the product
# --------------------------------------------------------------------------- #


def _build_extracted_motorhome(product: RSProduct) -> ExtractedMotorhome:
    """One model as a `Motorhome`, with the provenance a reviewer reads beside each field.

    Five fields are deliberately left with **no provenance and so no proposal**:

    * `mro_kilograms` and `mh_payload_kilograms` — RS publish neither, for any model. A
      field with no provenance is never proposed, which leaves FMLV's own figures alone
      rather than blanking them.
    * `berths` — the claim is marketing and the marketing disagrees with itself: *"2 berth
      up to 6 berth"* on one page, *"up to 7 berth"* on the index, *"up to 8 people"* on
      another. Under the settled lower-figure rule all four would be 2 against FMLV's 4,
      and the requester kept that decision on 9 November 2026. It is narrated instead.
    * `body_type` — nothing published settles it for a matched product, and the rule is to
      derive it or leave it blank, never to guess.
    * `automatic` — the variant, as opposed to whether one is offered, needs a price for
      the automatic and these documents give none.
    """
    features = habitation.features_from(product.standard_lines)
    automatic = gearbox.automatic_available_from(product.all_lines)

    motorhome = Motorhome(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=FMLV_RANGE,
        model=product.model,
        base_vehicle_manufacturer=fmlv_base_vehicle(
            product.base_vehicle.split()[0] if product.base_vehicle else None
        ),
        rrp_pounds=product.rrp_pounds,
        mtplm_kilograms=product.mtplm_kilograms,
        mh_length_mm=product.mh_length_mm,
        mh_width_mm=product.mh_width_mm,
        mh_height_mm=product.mh_height_mm,
        mh_passenger_seats_inc_driver=product.mh_passenger_seats_inc_driver,
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
        automatic_available=automatic[0] if automatic else None,
    )

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=product.source_url,
            snippet=f"{product.label} — {snippet}",
        )

    record(
        "manufacturer_range",
        f"range {FMLV_RANGE!r}, which is how FMLV files all four RS models and the only "
        f"range this manufacturer has",
    )
    if product.base_vehicle is not None:
        record(
            "base_vehicle_manufacturer",
            f"'Base Vehicle {product.base_vehicle}', from the chassis table. Where a cover "
            f"page disagrees with this row the row is taken, because the row is where the "
            f"engine, the tank and the brakes are also described",
        )
    if product.mh_length_mm is not None:
        record("mh_length_mm", f"'Overall Length {product.mh_length_mm:,}mm'")
    if product.mh_width_mm is not None:
        record(
            "mh_width_mm",
            f"'Overall Width {product.mh_width_mm:,}mm'. RS qualify it neither way, so it "
            f"is taken as the body — they state no mirror or awning allowance anywhere",
        )
    if product.mh_height_mm is not None:
        record("mh_height_mm", f"'Overall Height {product.mh_height_mm:,}mm'")
    if product.mtplm_kilograms is not None:
        record(
            "mtplm_kilograms",
            f"'Gross Vehicle Weight {product.mtplm_kilograms:,}kg'. RS publish NO mass in "
            f"running order and NO payload for any model, so this figure stands alone and "
            f"no arithmetic checks it",
        )
    if product.mh_passenger_seats_inc_driver is not None:
        # The rear-belt caveat is only said where the document says it. The Envoy's does
        # not mention rear belts at all, and claiming it offered them would be inventing a
        # reason for the number.
        caveat = (
            " Rear belts are 'available depending on layout', which is an option and so is "
            "not counted."
            if product.offers_optional_rear_belts
            else ""
        )
        record(
            "mh_passenger_seats_inc_driver",
            f"{product.seats_snippet}, so {product.mh_passenger_seats_inc_driver} belted "
            f"travel seats as built.{caveat}",
        )
    if product.rrp_pounds is not None:
        record(
            "rrp_pounds",
            f"'From £{product.rrp_pounds:,} inc. VAT' on the cover and '£"
            f"{product.rrp_pounds:,}' again under the standard-specification heading. RS "
            f"sell direct, so their own headline figure is the guide price",
        )
    if automatic is not None:
        record("automatic_available", gearbox.provenance_note(automatic))

    for field_name, feature in features.items():
        detail = f" — {feature.note}" if feature.note else ""
        provenance[field_name] = Provenance(
            source_url=product.source_url,
            snippet=f"{product.label} — the specification says {feature.snippet!r}{detail}",
        )

    return ExtractedMotorhome(motorhome=motorhome, provenance=provenance)


# --------------------------------------------------------------------------- #
# The run
# --------------------------------------------------------------------------- #


def _wanted_models(ranges: Iterable[tuple[str, ...]]) -> tuple[_ModelSource, ...]:
    """Every model in scope. `--range` selects the one range, so it is all or nothing."""
    labels = {entry[-1].casefold() for entry in ranges}
    if not labels or FMLV_RANGE.casefold() in labels or "rs" in labels:
        return MODELS
    return ()


def _check_roster(http: Fetcher, on_progress: Callable[[str], None]) -> None:
    """Compare RS's own index against `MODELS`, and narrate every difference.

    This is the adapter's **only completeness check**, because nothing RS publish
    reconciles arithmetically. It is therefore worth more here than on any other
    manufacturer, and it is why a failure to read the index is a warning rather than a
    silence.
    """
    result = http.fetch(MODELS_INDEX_URL)
    if result.status_code != 200:
        on_progress(
            f"WARNING: {MODELS_INDEX_URL} returned {result.status_code}, so the roster "
            f"could not be checked this run. It is the only completeness check there is"
        )
        return

    listed = parse_roster(result.file_path.read_text(encoding="utf-8", errors="replace"))
    known = {source.model for source in MODELS}
    on_progress(f"the models index heads {len(listed)} model(s): {', '.join(listed)}")

    for model in listed:
        if model in known:
            continue
        if model in ORPHANED_PAGES:
            on_progress(
                f"WARNING: the index has a heading for the {model} again, which was "
                f"recorded as withdrawn. It is NOT collected: add it to MODELS to collect "
                f"it. What was established: {ORPHANED_PAGES[model]}"
            )
            continue
        on_progress(
            f"WARNING: the index heads a model this adapter does not know: {model!r}. It "
            f"is NOT collected. Add it to MODELS, with the media title of its "
            f"specification document"
        )

    for model in sorted(known - set(listed)):
        on_progress(
            f"WARNING: {model} is in MODELS but the index no longer heads it, so RS may "
            f"have withdrawn it. It is still collected this run; check the index"
        )


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 — plain HTTP throughout; nothing here needs rendering
    snapshot_dir: Path,  # noqa: ARG001 — `Fetcher` owns the snapshot directory
    *,
    ranges: tuple[tuple[str, str], ...] = DEFAULT_RANGES,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedMotorhome]:
    """Every current RS model, from the specification documents and the one HTML table."""
    wanted = _wanted_models(ranges)
    if not wanted:
        on_progress(f"no range matched; the only range is {FMLV_RANGE!r}")
        return []

    on_progress(f"asking the site's own media library for its PDFs: {MEDIA_URL}")
    listing = http.fetch(MEDIA_URL)
    if listing.status_code != 200:
        message = (
            f"{MEDIA_URL} returned {listing.status_code}. Nothing on this site links a "
            f"specification document, so this endpoint is the only way to find them"
        )
        raise RuntimeError(message)

    documents = specification_documents(
        listing.file_path.read_text(encoding="utf-8", errors="replace")
    )
    on_progress(f"the media library lists {len(documents)} PDF(s)")

    _check_roster(http, on_progress)

    results: list[ExtractedMotorhome] = []
    for source in wanted:
        product: RSProduct | None = None

        if source.media_title is None:
            on_progress(
                f"[{FMLV_RANGE} {source.model}] NO SPECIFICATION DOCUMENT EXISTS for this "
                f"model, so it is read from {EVOLUTION_SPEC_URL}, an on-site table of "
                f"2022-23 vintage. Its figures are the oldest this adapter records"
            )
            page = http.fetch(EVOLUTION_SPEC_URL)
            if page.status_code != 200:
                on_progress(
                    f"SKIPPED [{FMLV_RANGE} {source.model}]: {EVOLUTION_SPEC_URL} returned "
                    f"{page.status_code}, which leaves this model with no source at all"
                )
                continue
            product = parse_specification_page(
                page.file_path.read_text(encoding="utf-8", errors="replace"),
                source.model,
                EVOLUTION_SPEC_URL,
            )
        else:
            found = documents.get(source.media_title)
            if found is None:
                on_progress(
                    f"SKIPPED [{FMLV_RANGE} {source.model}]: the media library no longer "
                    f"lists {source.media_title!r}. Either RS renamed it or they withdrew "
                    f"the model; check the listing before believing either"
                )
                continue
            url, date = found
            on_progress(
                f"[{FMLV_RANGE} {source.model}] reading {url.rsplit('/', 1)[-1]}, uploaded "
                f"{date[:10]}"
            )
            fetched = http.fetch(url)
            if fetched.status_code != 200:
                on_progress(
                    f"SKIPPED [{FMLV_RANGE} {source.model}]: {url} returned "
                    f"{fetched.status_code}"
                )
                continue
            try:
                text = extract_text(fetched.file_path).text
            except Exception as error:  # noqa: BLE001 — one unreadable PDF is not the run
                on_progress(
                    f"SKIPPED [{FMLV_RANGE} {source.model}]: its document could not be "
                    f"read ({type(error).__name__})"
                )
                continue
            product = parse_specification_pdf(text, source.model, url)

        reconciles, why_not = _reconciles(product)
        if not reconciles:
            on_progress(f"SKIPPED [{product.label}]: {why_not}")
            continue
        for note in _discrepancies(product):
            on_progress(f"[{product.label}] NOTE: {note}")
        if product.capacity_claim:
            on_progress(
                f"[{product.label}] BERTHS ARE NOT PROPOSED. RS state "
                f"{product.capacity_claim!r} here, and their pages elsewhere say 'up to 6', "
                f"'up to 7' and 'up to 8' for the same vehicles. FMLV's own figure stands"
            )
        on_progress(
            f"[{product.label}] NO MASS IN RUNNING ORDER AND NO PAYLOAD is published, so "
            f"both columns are left as FMLV holds them rather than blanked or derived"
        )
        results.append(_build_extracted_motorhome(product))

    if len(results) != EXPECTED_LAYOUTS:
        on_progress(
            f"WARNING: collected {len(results)} model(s) where the roster has "
            f"{EXPECTED_LAYOUTS}. Nothing RS publish reconciles arithmetically, so this "
            f"count is the main defence — check /luxury-motorhomes/ before accepting"
        )
    on_progress(f"collected {len(results)} product(s)")
    return results
