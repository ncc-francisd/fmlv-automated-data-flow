"""Beauer (via rivermotorhomes.co.uk) — French caravans whose bodies telescope outwards.

See `docs/adapters/beauer.md` for the survey. **The source is River Motorhomes**, the UK
seller, whose `/beauer/` index links one page per model under `/beauer-new/<slug>/`.

## Why a dealer's site is the source here, against the usual rule

The settled rule is that an importer decides what exists and what it costs while the
factory decides every number, and that specifications are not taken off a dealer page.
This reads the specifications off River's pages anyway, for a reason that was checked
rather than assumed:

**River have republished Beauer's own copy verbatim.** Beauer's English pages
(`beauer.fr/en/modele-beauer/<slug>/`) carry the identical wording — *"Weight of the fully
equipped trailer*"*, *"Payload"*, *"Gross Vehicle Weight Rating"* — and the identical
figures, to the kilogram. What the factory's own pages do **not** do is put the dimensions
where a plain fetch can reach them; River's do, in millimetres.

So `FACTORY_WEIGHTS` below records what Beauer themselves publish, and `_reconciles`
checks every page against it. If River ever edit a number, the run says so instead of
quietly recording a dealer's arithmetic.

## The trap: every model publishes two widths, and the second one is enormous

These caravans expand sideways when parked, and the page gives both states under two
headings:

```
Dimensions                      Dimensions when extended
  Width:  1950mm                  Width:  4600mm
  Length: 3850mm                  Height: 2000mm
  Height: 2650mm
```

**The travelling figures are the ones FMLV wants.** An extended width recorded as the
width puts 4600mm in a column where 1950mm belongs — a caravan wider than a motorway lane.

And it cannot be resolved by comparing magnitudes: the extended **height** is *lower* than
the closed height (2000 against 2650) while the extended **width** is far higher, so
"take the larger" and "take the smaller" are each wrong on one field. `_technical_sections`
splits on the headings and `extended_dimensions` exists only so the run can report what it
threw away.

## The price is River's, and it deserves a second look

Beauer price the X4 at **39.990 €** and River at **£39,990** — digit for digit, with the
symbol changed. At the house rate of 1.15 €/£ the French price is about £34,800, so either
River have set a UK price some 15% above the French one, which is ordinary for an import,
or a figure has been carried across with its currency swapped. Nothing here can tell which,
so the price is recorded — River are the UK seller and the price is theirs to state — and
`price_note` puts the comparison in front of the reviewer every run.

## Equipment is read by section, because the Options accordion looks like equipment

The page's accordions are `Interior Ambience`, `Living Room & Bedroom`, `Kitchen &
Bathroom`, `Chassis & Technology`, **`Options`** and `Technical Data`, and the section
names differ per model. Only the standard ones are read.

It matters more than usual here: the **only** heating Beauer offer — *"Heating + 2,000 W
Webasto gas or electric underfloor water heater"* and a *"Truma 1800W Eezy Electric
Heater"* — sits in `Options` on all three. Read whole, the page gives every Beauer wet
underfloor heating as standard. Read by section, it correctly gives none.
"""

from __future__ import annotations

import html as htmllib
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.caravan import Caravan
from ..product_model.enums import CaravanBodyType
from ..vehicle_class import VehicleClass
from . import habitation
from .base import ExtractedCaravan, Provenance

__all__ = [
    "BASE_URL",
    "EXPECTED_MODELS",
    "FACTORY_WEIGHTS",
    "INDEX_URL",
    "MANUFACTURER",
    "MANUFACTURER_DISPLAY_NAME",
    "MICRO_CARAVAN_CEILING_KG",
    "MINIMUM_CREDIBLE_PRICE",
    "OPTIONS_HEADING",
    "VEHICLE_CLASS",
    "FactoryWeights",
    "Model",
    "berths_from_prose",
    "body_type_for",
    "build_extracted",
    "collect",
    "extended_dimensions",
    "find_model_paths",
    "model_name",
    "parse_model",
    "parse_price",
    "parse_sections",
    "price_note",
    "standard_equipment",
    "technical_data",
]

BASE_URL = "https://www.rivermotorhomes.co.uk"
MANUFACTURER = "Beauer"
MANUFACTURER_DISPLAY_NAME = "Beauer"

#: Towed, so a caravan. Without this the module registers under the motorhome class.
VEHICLE_CLASS = VehicleClass.CARAVAN

#: The page that lists the range. Server-rendered, so no browser is needed.
INDEX_URL = f"{BASE_URL}/beauer/"

#: X4, X6 and X8. Compared against the collected count so a page dropped by a template
#: change is reported rather than read as a withdrawal.
EXPECTED_MODELS = 3

#: Below this a figure on the page is not the price of a Beauer — the cheapest is £39,990.
MINIMUM_CREDIBLE_PRICE = 10_000

#: A caravan is a micro only where the manufacturer calls it one **and** its MTPLM is at or
#: below this. The lightest Beauer is 1350kg, so the ceiling is never reached; it is named
#: so `body_type_for` states the test it applied rather than asserting `rigid` from nowhere.
MICRO_CARAVAN_CEILING_KG = 1250

#: The accordion whose contents are **not** equipment. Named rather than inferred, because
#: on this site every Beauer's heating lives in it.
OPTIONS_HEADING = "Options"

#: The euro-per-pound rate the project converts at, used only to put River's sterling price
#: beside Beauer's euro one in `price_note`. Nothing is converted for recording: the UK
#: seller's price is the price.
EUROS_PER_POUND = 1.15


@dataclass(frozen=True)
class FactoryWeights:
    """What **Beauer themselves** publish for a model, from `beauer.fr/en/`.

    Written down rather than fetched. The factory's pages carry these three figures in the
    same words River use, but do not expose the dimensions to a plain fetch, so there is
    nothing to be gained by fetching them every run — and a great deal to be gained by
    having them here, where `_reconciles` can test the dealer's page against the
    manufacturer's own numbers.

    `fully_equipped_kilograms` is Beauer's *"Weight of the fully equipped trailer"*, which
    is footnoted *"depending on the options selected"*. See `build_extracted`.
    """

    fully_equipped_kilograms: int
    payload_kilograms: int
    gross_kilograms: int
    euro_price: int


#: Keyed by the model name as the page's own heading gives it.
FACTORY_WEIGHTS: dict[str, FactoryWeights] = {
    "X4": FactoryWeights(1200, 150, 1350, 39_990),
    "X6": FactoryWeights(1700, 100, 1800, 74_990),
    "X8": FactoryWeights(2600, 100, 2700, 109_990),
}

#: `/beauer-new/beauer-x4/`. The index also links the older `/beauer/<slug>/` paths, which
#: still resolve; the `-new` ones are what it points at now and what is followed.
_MODEL_LINK = re.compile(r'href="(?:' + re.escape(BASE_URL) + r')?(/beauer-new/[a-z0-9-]+/)"', re.I)

#: `<div class="accordion-header …">Kitchen &amp; Bathroom<button`.
_ACCORDION = re.compile(
    r'<div class="accordion-header[^"]*">(?P<heading>.*?)<button.*?'
    r'<div class="accordion-body">(?P<body>.*?)</div>\s*</div>\s*</div>',
    re.S,
)

#: `<p><strong>Dimensions</strong></p>` — the sub-headings inside Technical Data.
_TECHNICAL_HEADING = re.compile(r"<p>\s*<strong>(.*?)</strong>\s*</p>", re.S)

#: `<li><strong>Width:</strong> 1950mm</li>`. The weight list's items are **unclosed** in
#: the source, so the terminator has to be the next `<li>` or the end of the list.
_TECHNICAL_ITEM = re.compile(
    r"<li>\s*<strong>(?P<label>.*?)</strong>(?P<value>.*?)(?=<li>|</ul>|</li>)", re.S
)

#: `Sleeps up to 4 people comfortably`.
_SLEEPS = re.compile(r"\bsleeps?\s+(?:up\s+to\s+)?(\d+)\b", re.I)

#: `AL-KO dual-axle chassis` on the X8; the others say only `AL-KO Chassis`.
_TWIN_AXLE = re.compile(r"\b(?:dual|twin|double)[- ]axle\b|\btwin\s+axles?\b", re.I)

#: An appliance that heats **water**, not the caravan. `habitation`'s "is the heating
#: unclear" check matches any line containing `heater`, so the X4's and X6's `6-Liter
#: Electric Water Heater` trips it — and reporting that as heating of an undetermined kind
#: sends a reviewer hunting for a system that is not there.
_WATER_HEATER = re.compile(r"\bwater heater\b|\bwater heating\b|\bboiler\b", re.I)

#: The cookie banner's container reuses `accordion-header`, so its "heading" is several
#: hundred words of consent copy and branch opening hours. Anything this long is furniture.
_MAX_HEADING_LENGTH = 60


def _plain(fragment: str) -> str:
    """Markup as readable lines, one per block element."""
    body = re.sub(r"(?is)<(script|style|svg|noscript)\b.*?</\1>", " ", fragment)
    text = re.sub(r"(?i)</(p|h\d|div|li|tr|td|th|dt|dd|br|span|strong)>|<br\s*/?>", "\n", body)
    return re.sub(r"<[^>]+>", " ", htmllib.unescape(text))


def _lines(fragment: str) -> list[str]:
    return [" ".join(line.split()) for line in _plain(fragment).split("\n") if line.strip()]


def _one_line(fragment: str) -> str:
    return " ".join(_plain(fragment).split())


def find_model_paths(index_html: str) -> list[str]:
    """Every model page the index links, in order.

    **Rediscovered each run rather than written in.** River publish no other roster of the
    Beauer range, and a hardcoded list would miss a fourth model in silence.
    """
    seen: dict[str, None] = {}
    for match in _MODEL_LINK.finditer(index_html):
        seen.setdefault(match.group(1), None)
    return list(seen)


def model_name(page_html: str) -> str | None:
    """`X4`, from the page's own `<h1>` — never from the slug.

    FMLV will hold these as one-name products, so the name has to be right: it becomes both
    the range and the model.
    """
    match = re.search(r"<h1[^>]*>(.*?)</h1>", page_html, re.S)
    if match is None:
        return None
    heading = _one_line(match.group(1))
    found = re.search(r"\bX\s*(\d+)\b", heading, re.I)
    return f"X{found.group(1)}" if found else (heading or None)


def parse_sections(page_html: str) -> dict[str, list[str]]:
    """Every accordion on the page, as `{heading: [lines]}`.

    The cookie banner's container reuses the same class, so its heading is hundreds of
    words of consent copy and branch opening hours — anything over `_MAX_HEADING_LENGTH`
    is furniture and is dropped.
    """
    sections: dict[str, list[str]] = {}
    for match in _ACCORDION.finditer(page_html):
        heading = _one_line(match.group("heading"))
        if not heading or len(heading) > _MAX_HEADING_LENGTH:
            continue
        sections.setdefault(heading, _lines(match.group("body")))
    return sections


def standard_equipment(sections: dict[str, list[str]]) -> list[str]:
    """Every equipment line **except** the Options accordion's and the Technical Data's.

    The exclusion is structural — by the section a line sits in — and it has to be. Every
    Beauer's heating is an option and none of its lines says so: *"Heating + 2,000 W
    Webasto gas or electric underfloor water heater"* reads exactly like standard
    equipment, and `usable_lines` cannot tell. Read whole, the page gives all three models
    wet underfloor heating they have not got.
    """
    return [
        line
        for heading, lines in sections.items()
        if heading not in {OPTIONS_HEADING, "Technical Data"}
        for line in lines
    ]


def technical_data(page_html: str) -> dict[str, dict[str, str]]:
    """The Technical Data accordion, as `{sub-heading: {label: value}}`.

    Keyed on the sub-heading precisely so `Dimensions` and `Dimensions when extended` stay
    apart — they carry the **same labels** with wildly different values, and merging them
    silently overwrites the travelling width with the deployed one.
    """
    body = parse_sections(page_html)
    raw = next(
        (
            match.group("body")
            for match in _ACCORDION.finditer(page_html)
            if _one_line(match.group("heading")) == "Technical Data"
        ),
        None,
    )
    if raw is None or "Technical Data" not in body:
        return {}

    found: dict[str, dict[str, str]] = {}
    headings = list(_TECHNICAL_HEADING.finditer(raw))
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(raw)
        name = _one_line(heading.group(1))
        items: dict[str, str] = {}
        for item in _TECHNICAL_ITEM.finditer(raw[heading.end() : end]):
            label = _one_line(item.group("label")).rstrip(": ").strip()
            value = _one_line(item.group("value")).strip()
            if label and value:
                items[label] = value
        if items:
            found[name] = items
    return found


def _millimetres(value: str | None) -> int | None:
    if value is None:
        return None
    match = re.search(r"([\d,]+)\s*mm\b", value, re.I)
    return int(match.group(1).replace(",", "")) if match else None


def _kilograms(value: str | None) -> int | None:
    if value is None:
        return None
    match = re.search(r"([\d,]+)\s*kg\b", value, re.I)
    return int(match.group(1).replace(",", "")) if match else None


def extended_dimensions(page_html: str) -> dict[str, int]:
    """The deployed figures, read **only** so the run can say what it refused."""
    section = technical_data(page_html).get("Dimensions when extended", {})
    found = {
        label.lower(): _millimetres(value)
        for label, value in section.items()
    }
    return {label: value for label, value in found.items() if value is not None}


def parse_price(page_html: str) -> int | None:
    """The one sterling figure on the page.

    River publish a single price per Beauer and no monthly finance figure beside it, so
    unlike their stock listings there is nothing here to be confused with.
    """
    prices = {
        int(raw.replace(",", ""))
        for raw in re.findall(r"(?:&pound;|£)\s*([\d,]{4,})", page_html)
    }
    credible = {price for price in prices if price >= MINIMUM_CREDIBLE_PRICE}
    return min(credible) if credible else None


def berths_from_prose(page_html: str, name: str | None) -> tuple[int | None, str]:
    """`Sleeps up to 4 people` — with the model's own name as corroboration.

    **The name encodes the figure**: an X4 sleeps 4, an X6 six, an X8 eight. That makes a
    genuine cross-check out of what would otherwise be a lone sentence of marketing prose,
    so a berth count is only taken where the two agree.

    "Up to" is not the berth-range trap. The upper figure of `Sleeps 2-4` needs options and
    the rule takes the lower; here the convertible bench that makes up the difference is in
    the **standard** equipment list, so the stated figure is reached as the caravan is sold.
    """
    stated = _SLEEPS.search(_one_line(page_html))
    if stated is None:
        return None, "no sleeping capacity is stated on the page"
    berths = int(stated.group(1))
    from_name = re.fullmatch(r"X(\d+)", name or "", re.I)
    if from_name is None:
        return berths, f"{berths} berths, from the page's own {stated.group(0)!r}"
    if int(from_name.group(1)) != berths:
        return None, (
            f"the page says {stated.group(0)!r} but the model is called {name} — the two "
            f"disagree, so no berth count is proposed"
        )
    return berths, (
        f"{berths} berths, from the page's own {stated.group(0)!r}, which agrees with the "
        f"model's name. The convertible bench that reaches it is standard equipment, not "
        f"an option"
    )


def body_type_for(name: str | None, gross_kilograms: int | None) -> tuple[CaravanBodyType, str]:
    """`rigid` for every Beauer, with the micro test stated rather than skipped.

    **An expanding caravan is still a rigid one.** It has solid walls and a solid roof
    throughout; what it does is slide a smaller box out of a larger one. It is not a
    folding caravan, which needs canvas, and the settled rule that a lifting roof does not
    change a caravan's body type points the same way.
    """
    weight = (
        f", and at {gross_kilograms}kg it is far above the {MICRO_CARAVAN_CEILING_KG}kg a "
        f"micro has to sit under"
        if gross_kilograms is not None
        else ""
    )
    return CaravanBodyType.RIGID, (
        f"a rigid caravan: the Beauer {name or ''} expands sideways when parked, but it has "
        f"solid walls and roof throughout and no canvas, so it is neither folding nor a "
        f"pop-up{weight}"
    )


@dataclass
class Model:
    """One Beauer as its River page describes it, refusals included."""

    url: str
    name: str | None = None
    rrp_pounds: int | None = None
    berths: int | None = None
    berths_basis: str = ""
    twin_axle: bool = False
    fully_equipped_kilograms: int | None = None
    payload_kilograms: int | None = None
    gross_kilograms: int | None = None
    length_mm: int | None = None
    width_mm: int | None = None
    height_mm: int | None = None
    extended: dict[str, int] = field(default_factory=dict)
    equipment: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return f"Beauer {self.name}" if self.name else self.url


def parse_model(page_html: str, url: str) -> Model | None:
    """One model page, or `None` when nothing on it names a Beauer."""
    name = model_name(page_html)
    if name is None:
        return None
    sections = parse_sections(page_html)
    technical = technical_data(page_html)
    travelling = technical.get("Dimensions", {})
    weights = technical.get("Weight", {})

    def weight(*labels: str) -> int | None:
        for label, value in weights.items():
            if any(wanted.lower() in label.lower() for wanted in labels):
                return _kilograms(value)
        return None

    berths, berths_basis = berths_from_prose(page_html, name)
    chassis = " ".join(sections.get("Chassis & Technology", []))
    return Model(
        url=url,
        name=name,
        rrp_pounds=parse_price(page_html),
        berths=berths,
        berths_basis=berths_basis,
        twin_axle=bool(_TWIN_AXLE.search(chassis)),
        fully_equipped_kilograms=weight("fully equipped"),
        payload_kilograms=weight("payload"),
        gross_kilograms=weight("gross vehicle weight", "weight rating"),
        length_mm=_millimetres(travelling.get("Length:") or travelling.get("Length")),
        width_mm=_millimetres(travelling.get("Width:") or travelling.get("Width")),
        height_mm=_millimetres(travelling.get("Height:") or travelling.get("Height")),
        extended=extended_dimensions(page_html),
        equipment=standard_equipment(sections),
    )


def _reconciles(model: Model) -> tuple[bool, str]:
    """Beauer's own published arithmetic, and their own published figures.

    Two checks, both real. The page prints three masses and
    `fully equipped + payload = gross` closes exactly on every model, so a misread column
    fails rather than passing quietly. And `FACTORY_WEIGHTS` holds what **Beauer** publish
    for the same three figures, so a dealer's page that has drifted from the manufacturer's
    is caught — which is the whole justification for reading specifications off a dealer at
    all.
    """
    masses = (model.fully_equipped_kilograms, model.payload_kilograms, model.gross_kilograms)
    if any(mass is None for mass in masses):
        return False, (
            f"the Technical Data section does not give all three masses — read "
            f"{masses!r} for fully equipped, payload and gross"
        )
    equipped, payload, gross = masses
    assert equipped is not None and payload is not None and gross is not None
    if equipped + payload != gross:
        return False, (
            f"Beauer's own arithmetic does not close: {equipped} + {payload} = "
            f"{equipped + payload}, but the page gives a gross weight of {gross}kg"
        )

    published = FACTORY_WEIGHTS.get(model.name or "")
    if published is None:
        return True, (
            f"{equipped} + {payload} = {gross}kg, Beauer's own published arithmetic. NOTE: "
            f"{model.name} is not a model this adapter has seen before, so River's figures "
            f"could not be checked against Beauer's own — worth confirming"
        )
    if (equipped, payload, gross) != (
        published.fully_equipped_kilograms,
        published.payload_kilograms,
        published.gross_kilograms,
    ):
        return False, (
            f"River give {equipped}/{payload}/{gross}kg where Beauer themselves publish "
            f"{published.fully_equipped_kilograms}/{published.payload_kilograms}/"
            f"{published.gross_kilograms}kg. A dealer's page has drifted from the "
            f"manufacturer's, so nothing is recorded until someone looks"
        )
    return True, (
        f"{equipped} + {payload} = {gross}kg, which closes, and all three match what "
        f"Beauer themselves publish"
    )


def price_note(model: Model) -> str | None:
    """River's sterling price set beside Beauer's euro one, every run.

    Not a refusal and not a conversion — the UK seller's price is the price. But the two
    figures are digit-for-digit identical with the symbol changed, which is either a normal
    import uplift or a number carried across by mistake, and a reviewer should be the one
    deciding that rather than finding out later.
    """
    published = FACTORY_WEIGHTS.get(model.name or "")
    if published is None or model.rrp_pounds is None:
        return None
    converted = round(published.euro_price / EUROS_PER_POUND)
    if model.rrp_pounds != published.euro_price:
        return None
    return (
        f"{model.label} — PRICE WORTH A LOOK: River ask £{model.rrp_pounds:,} and Beauer "
        f"publish {published.euro_price:,} euros, the same digits with the symbol changed. "
        f"At {EUROS_PER_POUND} euros per pound the French price is about £{converted:,}. "
        f"Recorded as River's, since they are the UK seller and the price is theirs to "
        f"state, but it is worth confirming it is not a currency slip"
    )


#: How each habitation reading is introduced. Findings for a person to type in.
_FEATURE_NOTES: dict[str, str] = {
    "heating": "the heating in the page's standard equipment",
    "refrigeration": "the refrigeration in the page's standard equipment",
    "microwave": "a microwave in the page's standard equipment",
    "shower_toilet_separated": "the washroom as the standard equipment describes it",
}


def build_extracted(model: Model, *, basis: str) -> ExtractedCaravan:
    """One Beauer, with provenance on everything it proposes."""
    features = habitation.features_from(model.equipment)
    # Dropped as on every other adapter: the copy names beds and their sizes without
    # saying which are built in and which are made up out of the seating.
    features.pop("bed_types", None)

    body_type, body_type_reason = body_type_for(model.name, model.gross_kilograms)
    caravan = Caravan(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        # One name, carried twice, because Nova will not take a blank — the settled
        # convention for a product whose maker gives it no range.
        manufacturer_range=model.name,
        model=model.name,
        berths=model.berths,
        rrp_pounds=model.rrp_pounds,
        price_min_range_pounds=model.rrp_pounds,
        mtplm_kilograms=model.gross_kilograms,
        mro_kilograms=model.fully_equipped_kilograms,
        # **Deliberately absent.** Beauer publish one payload and it is the total, not the
        # personal-effects half FMLV's column holds, and there is no baseline for this
        # brand to show which way they file it. It is used for the self-check only.
        personal_effects_payload_kilograms=None,
        optional_equipment_payload_kilograms=None,
        shipping_length_mm=model.length_mm,
        # **Not proposed.** The page gives one length and does not say whether it includes
        # the drawbar, so the body length cannot be derived from it.
        exterior_body_length_mm=None,
        overall_width_mm=model.width_mm,
        height_mm=model.height_mm,
        body_type=body_type,
        twin_axle=model.twin_axle,
    )
    for name, feature in features.items():
        setattr(caravan, name, feature.value)

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str) -> None:
        provenance[field_name] = Provenance(
            source_url=model.url, snippet=f"{model.label} — {snippet}"
        )

    record(
        "manufacturer_range",
        f'range "{model.name}", from the page heading. Beauer give these no range name, so '
        f"the model name is carried twice — Nova will not take a blank",
    )
    record("model", f'model "{model.name}", from the page heading')
    if model.rrp_pounds is not None:
        record(
            "rrp_pounds",
            f"£{model.rrp_pounds:,}, River Motorhomes' own price. They sell Beauer in the "
            f"UK, so under the settled rule the price is theirs to state",
        )
        record(
            "price_min_range_pounds",
            f"£{model.rrp_pounds:,} — River list one price for this model",
        )
    if model.berths is not None:
        record("berths", model.berths_basis)
    record(
        "twin_axle",
        f"{'an AL-KO dual-axle chassis, named in the Chassis & Technology section'
           if model.twin_axle
           else 'a single axle: the Chassis & Technology section names an AL-KO chassis '
                'and says nothing of a second axle'}",
    )
    if model.gross_kilograms is not None:
        record(
            "mtplm_kilograms",
            f"Gross Vehicle Weight Rating {model.gross_kilograms}kg. {basis}",
        )
    if model.fully_equipped_kilograms is not None:
        record(
            "mro_kilograms",
            f"Weight of the fully equipped trailer {model.fully_equipped_kilograms}kg. "
            f"BEAUER FOOTNOTE THIS '*depending on the options selected', so it is not "
            f"plainly a mass in running order and may include fitted options. It is their "
            f"only published mass and it matches their own site exactly",
        )
    if model.length_mm is not None:
        record(
            "shipping_length_mm",
            f"Length {model.length_mm}mm, the travelling figure. Beauer do not say whether "
            f"it includes the drawbar, so nothing is proposed for the body length",
        )
    if model.width_mm is not None:
        record(
            "overall_width_mm",
            f"Width {model.width_mm}mm — THE TRAVELLING WIDTH. This caravan expands "
            f"sideways and the same page gives "
            f"{model.extended.get('width:', model.extended.get('width', '?'))}mm for it "
            f"extended, which is not what FMLV records",
        )
    if model.height_mm is not None:
        record("height_mm", f"Height {model.height_mm}mm, the travelling figure")
    record("body_type", body_type_reason)
    for name, feature in features.items():
        provenance[name] = Provenance(
            source_url=model.url,
            snippet=(
                f"{model.label} — {feature.note or _FEATURE_NOTES.get(name, name)}: "
                f"{feature.snippet!r}"
            ),
        )
    return ExtractedCaravan(caravan=caravan, provenance=provenance)


def _notes(model: Model) -> Iterable[str]:
    """What the page offered that was turned down, and on what grounds."""
    if model.extended:
        stated = ", ".join(f"{label} {value}mm" for label, value in model.extended.items())
        yield (
            f"{model.label} — EXTENDED DIMENSIONS NOT PROPOSED. The page states {stated} "
            f"under 'Dimensions when extended'. FMLV records the travelling figures, which "
            f"are {model.width_mm}mm wide and {model.height_mm}mm high"
        )
    if model.payload_kilograms is not None:
        yield (
            f"{model.label} — PAYLOAD NOT PROPOSED. Beauer publish {model.payload_kilograms}"
            f"kg, which is the total payload, not the personal-effects half FMLV's column "
            f"holds. Used for the self-check only"
        )
    if "heating" not in habitation.features_from(model.equipment):
        unclear = habitation.heating_is_unclear(model.equipment)
        # A water heater is not space heating, and saying "the kind is unclear" about one
        # sends a reviewer looking for a heating system that is not there. The only line
        # that trips the check on the X4 and X6 is the 6-litre electric water heater.
        aside = (
            f" The only line mentioning a heater is {unclear!r}, which heats water, not "
            f"the caravan."
            if unclear and _WATER_HEATER.search(unclear)
            else f" A line mentions heating without naming its kind: {unclear!r}."
            if unclear
            else ""
        )
        yield (
            f"{model.label} — NO HEATING IS STANDARD.{aside} Beauer's only space heating, "
            f"a Webasto underfloor water heater and a Truma electric heater, is in the "
            f"Options accordion. Read whole, the page would have given this caravan wet "
            f"underfloor heating it has not got"
        )
    if note := price_note(model):
        yield note


def collect(
    http: Fetcher,
    browser: object,  # noqa: ARG001 — the index and the model pages are plain HTML
    snapshot_dir: Path,  # noqa: ARG001 — `http` already snapshots into it
    *,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedCaravan]:
    """Every Beauer River Motorhomes list."""
    index = http.fetch(INDEX_URL)
    if index.status_code != 200:
        msg = f"{INDEX_URL} returned {index.status_code} — the only roster there is"
        raise RuntimeError(msg)
    paths = find_model_paths(index.file_path.read_text(encoding="utf-8", errors="replace"))
    if not paths:
        msg = (
            f"no /beauer-new/ pages linked from {INDEX_URL} — River publish no other "
            f"roster, so this cannot be read as the range having been withdrawn"
        )
        raise RuntimeError(msg)
    on_progress(f"the index links {len(paths)} model page(s)")

    results: list[ExtractedCaravan] = []
    for path in paths:
        url = f"{BASE_URL}{path}"
        page = http.fetch(url)
        if page.status_code != 200:
            on_progress(f"SKIPPED: {url} returned {page.status_code}")
            continue
        model = parse_model(page.file_path.read_text(encoding="utf-8", errors="replace"), url)
        if model is None:
            on_progress(f"SKIPPED: nothing on {url} names a Beauer model")
            continue

        reconciles, basis = _reconciles(model)
        if not reconciles:
            on_progress(f"{model.label} — DROPPED: {basis}")
            continue

        results.append(build_extracted(model, basis=basis))
        on_progress(
            f"{model.label} — "
            + (f"£{model.rrp_pounds:,}" if model.rrp_pounds else "no price published")
            + f", {model.berths} berth, {model.gross_kilograms}kg, "
            + f"{model.length_mm}x{model.width_mm}x{model.height_mm}mm travelling, "
            + ("twin axle" if model.twin_axle else "single axle")
        )
        for note in _notes(model):
            on_progress(note)

    on_progress(
        "EACH MODEL IS RECORDED ONCE, not twice. Beauer offer two interior layouts per "
        "model, but they share one price, one gross weight and one set of dimensions and "
        "carry no name of their own, so under the settled rule they are a choice rather "
        "than a second product."
    )
    if len(results) != EXPECTED_MODELS:
        on_progress(
            f"expected {EXPECTED_MODELS} models and collected {len(results)} — check "
            f"whether River have changed the range"
        )
    on_progress(f"collected {len(results)} Beauer caravan(s)")
    return results
