"""Coachman (coachman.co.uk) — touring caravans.

The sibling of `coachman.py`, and a separate module for the usual reason: FMLV keeps
motorhomes and touring caravans as separate exports with separate schemas, so this one
produces `Caravan`s and registers under `(Coachman, Coachman, caravan)`. See
`docs/adapters/coachman.md` § "The caravans come into scope" for the survey.

**Coachman are listed twice in the NCC's supplier dropdown.** `Coachman Motorhomes` and
`Coachman Caravans` are separate entries, split for historic reasons on the FMLV side, and
only the second reaches these products — hence `ncc_supplier_name_caravan` in the registry
and the off-area sheet `cli.fetch_export` now discards. Nothing in this module depends on
that; it is recorded here because the adapter is unreachable without it.

**The site's shape is the motorhome one, so every parser is imported rather than rewritten.**
Same WordPress install, same markup, different post type: `caravan` instead of `motorhome`,
`caravan_model` instead of `motorhome_model`. Three sources, as before:

* **Identity** — `/wp-json/wp/v2/caravan_model` gives the four ranges with the `count` that
  doubles as a completeness check, and `/wp-json/wp/v2/caravan` gives all 19 products with
  their full titles.
* **Specification** — each range page's technical panels, one `<h2>`-headed panel per model,
  carrying 22 labelled rows. **This is the primary source here**, which inverts the
  motorhome arrangement: a caravan panel publishes price, berths, axles, every dimension,
  both masses, both payloads and the hitch weight, where a motorhome panel adds only width,
  height and the base vehicle to what the card already says.
* **The homepage cards** — price, berths, length, axles, MTPLM and MRO, keyed by
  `(post type, term ID, model)`. Not needed for any value, and read anyway: see
  `_agrees_with_card`.

**Three figures the panel publishes that nothing else in this project has had.**
`Maximum Hitch Weight` is the nose weight TowCheck needs and could not previously get;
`Personal Payload` and `Total / Maximum User Payload` are published *together* and are
equal on all 17 weighed models, which settles for Coachman the worry the Bailey pilot
raised about a lone payload figure secretly being a total.

**Two models publish `TBC` where every mass should be.** VIP 520 and VIP 565, on the card
and the panel alike, in MTPLM, MRO, both payloads, the hitch weight and the upper MTPLM.
They are recorded with those fields blank rather than dropped — the price, the dimensions
and the berths are real — and the gaps surface as `missing_required` for a person. That is
`docs/adapters/README.md`'s missing-data rule working, not a fault to fix here.

**What is deliberately not recorded**, each for a reason that would otherwise be rediscovered:

*No `exterior_body_length_mm`.* Coachman publish `Length`, `Interior Length` and
`Overall Length`, and the first two are the same number as the third on all 19. There is no
body-only figure, which is the same gap Bailey have, and the field is out of automated
scope in `config/field_guide_caravan.csv` because of it.

*`optional_equipment_payload_kilograms` on the four Acadias, and nowhere else.* The panel
has one payload row, and `Total / Maximum User Payload` equals `Personal Payload` on every
model — which first read as proof that the optional half was nil. Coachman's own 2027
model-data file says otherwise: on the Acadias both rows are the **total**, 5kg of which
is optional equipment, and the label `Personal Payload` is wrong on their own page. The
split comes from the file; see `MANUFACTURER_FILE_2027`. Laser, Lusso and VIP genuinely
carry none, so for those the single published figure was right all along.

*No `Upper MTPLM`.* It is the optioned weight-plate upgrade — 1750kg against a base 1679kg —
and the base vehicle rule takes the base figure.

*The air-conditioning height.* Coachman publish two: 2675mm *"including T.V Aerial"* and
2750mm *"including Air Conditioning"*. FMLV holds 2675 on all 19, so the choice between
them has already been made and this follows it rather than reopening it.

*No bed types, no sleeping area, no kitchen, bathroom or lounge location.* The panel's
`Layout` row is per-model and explicit — `Fixed Double`, `Fixed Single`, `No Fixed Bed` —
and its `Bed Sizes` row names `Front Beds`, `Fixed Bed` and `Side Dinette`. That is enough
to guess from and not enough to be right: **VIP 520 publishes `No Fixed Bed` and a front
make-up only, and FMLV holds it as sleeping at both ends with fixed bunks.** Neither row
says where a bed is, and the one model that tests the inference defeats it. See
`docs/adapters/README.md` — derive it or leave it blank, never guess across an exclusive
group.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from ..fetch.http import Fetcher
from ..product_model.caravan import Caravan
from ..product_model.enums import CaravanBodyType
from ..vehicle_class import VehicleClass
from . import habitation
from .base import ExtractedCaravan, Provenance
from .coachman import (
    BASE_URL,
    _kilograms,
    _millimetres,
    _plain,
    _pounds,
    _squash,
    parse_cards,
    parse_equipment,
    parse_range_counts,
    parse_range_slugs,
    parse_ranges,
    parse_roster,
    parse_specification_panels,
)

MANUFACTURER = "Coachman"
MANUFACTURER_DISPLAY_NAME = "Coachman"

#: What makes this the caravan adapter. Without it `ADAPTERS` would key it on
#: `(Coachman, Coachman, motorhome)` and it would silently replace `coachman.py`.
VEHICLE_CLASS = VehicleClass.CARAVAN

#: The WordPress post type. Its taxonomy is `{POST_TYPE}_model`, which is how
#: `coachman.parse_roster` finds a product's terms without being told the name.
POST_TYPE = "caravan"

#: What Coachman's own site claims: four ranges totalling 19 layouts, as the taxonomy's
#: per-range `count` reports them. Asserted in the tests and compared against every run.
EXPECTED_PRODUCTS = 19

#: (range slug, label) for `--range`. **Only a menu.** A full run reads the taxonomy and
#: takes whatever is in it, so a range Coachman add between model years is collected
#: without an edit here — which is how the motorhome side picked up Veloce for nothing.
#: The slug is the taxonomy's own, which is also the range page's URL.
DEFAULT_RANGES: tuple[tuple[str, str], ...] = (
    ("acadia", "Acadia"),
    ("laser", "Laser"),
    ("lusso", "Lusso"),
    ("vip", "VIP"),
)

#: Panel label -> `CoachmanCaravanSpec` field, for the rows read straight across.
#:
#: `Overall Length` rather than `Length`: the two carry the same number on all 19, and the
#: explicit one is the one to name. It is the **shipping** length — body plus towing hitch —
#: which FMLV's own figures confirm, holding 7390mm against Coachman's 7390mm for the
#: Acadia 545 Xtra while its `exterior_body_length_mm` is 6480mm.
_PANEL_MILLIMETRES: tuple[tuple[str, str], ...] = (
    ("Interior Length", "internal_length_mm"),
    ("Overall Length", "shipping_length_mm"),
    ("Overall Width", "overall_width_mm"),
    ("Overall Height (including T.V Aerial)", "height_mm"),
    ("Maximum Headroom", "headroom_mm"),
)

_PANEL_KILOGRAMS: tuple[tuple[str, str], ...] = (
    ("MTPLM", "mtplm_kilograms"),
    ("Mass in Running Order", "mro_kilograms"),
    ("Personal Payload", "personal_effects_payload_kilograms"),
    ("Maximum Hitch Weight", "max_nose_weight_kilograms"),
)

#: The second payload row, read only to check the first against it. Not recorded.
_TOTAL_PAYLOAD_LABEL = "Total / Maximum User Payload"

#: Coachman write the awning in centimetres, with or without a space: `1014 cm`, `1062cm`.
_AWNING_LABEL = "Awning Size (Approx. for reference only)"

#: `'1014 cm'` -> `10140`. The only figure on the page in centimetres, and the only one
#: FMLV wants in millimetres from a different unit — hence a helper here rather than in
#: `coachman.py`, where no motorhome field needs it.
_CENTIMETRES = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*cm", re.IGNORECASE)


def _centimetres(value: str) -> int | None:
    match = _CENTIMETRES.search(value)
    return round(float(match.group(1).replace(",", "")) * 10) if match else None


@dataclass(frozen=True)
class _ManufacturerFigures:
    """One model's row from Coachman's own 2027 model-data file."""

    mtplm_kilograms: int | None = None
    mro_kilograms: int | None = None
    personal_effects_payload_kilograms: int | None = None
    #: The half the website does not publish at all — see `MANUFACTURER_FILE_2027`.
    optional_equipment_payload_kilograms: int | None = None
    max_nose_weight_kilograms: int | None = None
    #: True where the two payload halves **re-divide a figure the site already publishes**
    #: rather than filling a gap, so the site's single number is not a rival reading to be
    #: preferred — it is the sum, under a label that calls it the personal half. Applied
    #: only when `personal + optional` equals what the site publishes, which is what makes
    #: this safe: the file cannot move the total, only say how it splits.
    reapportions_published_payload: bool = False


#: Figures from **Coachman's own 2027 model-data file**, where the website does not carry
#: them or carries them in a shape it cannot express.
#:
#: `New Model Data 2027 list - Coachman-16-11-26.csv`, sent by Coachman and received
#: 16 November 2026. Forty-one rows, of which the twenty-two dealer-special models
#: (`Festival 545`, `Chiltington VIP`, `Penhurst Laser Xtra` and the rest) are out of
#: scope: FMLV does not list them. Only the nineteen core layouts are read, and of those
#: only the five below need anything from the file.
#:
#: **Two reasons an entry is here, and nothing else qualifies.**
#:
#: * **The site publishes `TBC`.** VIP 520 and VIP 565 are `TBC` in every mass row on the
#:   panel *and* the card, checked again live on 16 November 2026. They are the pair that
#:   produced no review rows at all, and the file is their only source.
#: * **The site cannot express the split.** The panel has one payload row. Coachman's file
#:   divides it into personal effects and optional equipment, and FMLV has a column for
#:   each. The four Acadia layouts carry 5kg of optional equipment; every Laser, Lusso and
#:   VIP carries none, so for those the single published figure was already right.
#:
#: **This overturns what the adapter first recorded.** The module docstring said the
#: optional half was nil throughout because `Total / Maximum User Payload` equalled
#: `Personal Payload` on every model. Those two rows *are* equal — but on the Acadias they
#: are both the total, and the label `Personal Payload` is simply wrong on Coachman's own
#: page. The worry logged during the Bailey pilot, that one published payload figure might
#: secretly be a total, turns out to be exactly what this was.
#:
#: **Every entry is audited against the live site each run** by `audit_manufacturer_file`,
#: which narrates a disagreement and announces an entry the site has caught up with, so a
#: stored figure cannot quietly outlive its reason for existing.
MANUFACTURER_FILE_2027: dict[tuple[str, str], _ManufacturerFigures] = {
    # The two the site publishes as TBC. Both reconcile: 1591-1449 = 142, 1679-1524 = 155.
    ("VIP", "520"): _ManufacturerFigures(1591, 1449, 142, None, 100),
    ("VIP", "565"): _ManufacturerFigures(1679, 1524, 155, None, 100),
    # The payload split only. Masses are left to the site, which agrees with the file to
    # the kilogram on all four, so there is nothing to override there.
    #
    # `660 Xtra` is listed with the others **and is expected to be refused**: its halves
    # come to 165kg against the 175kg its own masses imply, so the reapportioning rule
    # rejects it and the site's single figure stands. It is here rather than hand-noted as
    # an exception so that the arithmetic decides, and so the split starts applying by
    # itself if Coachman correct the row.
    ("Acadia", "545 Xtra"): _ManufacturerFigures(
        personal_effects_payload_kilograms=155,
        optional_equipment_payload_kilograms=5,
        reapportions_published_payload=True,
    ),
    ("Acadia", "575 Xtra"): _ManufacturerFigures(
        personal_effects_payload_kilograms=155,
        optional_equipment_payload_kilograms=5,
        reapportions_published_payload=True,
    ),
    ("Acadia", "655 Xtra"): _ManufacturerFigures(
        personal_effects_payload_kilograms=160,
        optional_equipment_payload_kilograms=5,
        reapportions_published_payload=True,
    ),
    ("Acadia", "660 Xtra"): _ManufacturerFigures(
        personal_effects_payload_kilograms=160,
        optional_equipment_payload_kilograms=5,
        reapportions_published_payload=True,
    ),
}

#: Rows of Coachman's file that **do not reconcile**, named so nobody re-derives them.
#:
#: Faults in one document, not conflicts between two sources — so neither is applied and
#: neither raises a question. The site's figure stands in both cases, and in both the
#: site's figure is the one the arithmetic supports.
MANUFACTURER_FILE_DISAGREES: dict[tuple[str, str], str] = {
    ("Lusso", "IV"): (
        "their file gives a mass in running order of 1096kg, which leaves a payload of "
        "960kg against the 160kg they state. The site's 1896kg is a straight digit "
        "transposition of it and reconciles exactly (2056 - 1896 = 160), so the file is "
        "simply mistyped and the site is right"
    ),
}

#: `Twin axle`, `Twin Axle` — the Lusso IV capitalises where its three siblings do not, so
#: this is matched case-insensitively rather than compared to a literal.
_TWIN_AXLE = re.compile(r"\btwin\b", re.I)

#: A trailing parenthetical on an equipment line, naming which models it applies to.
#:
#: **The reason this module filters where `coachman.py` does not.** Coachman publish one
#: equipment list per range, and on the caravan side its lines are *qualified*:
#: "Thetford N4090 91 litre electronic fridge freezer (545 Xtra and 575 Xtra)" sits beside
#: "Thetford N4142 137 litre electronic fridge freezer (665 Xtra and 660 Xtra)". Reading
#: either onto all four Acadias would assert a refrigerator the model does not have, and
#: FMLV's own rows disagree within the range, so a range-wide blanket is demonstrably wrong
#: here even though it is right for heating and the microwave.
_QUALIFIER = re.compile(r"\(([^()]*)\)\s*$")

#: A qualifier that *excludes* rather than selects: "(excluding 660 xtra)".
_EXCLUDING = re.compile(r"\b(?:exclud(?:e|es|ing)|except)\b", re.I)

#: A qualifier naming an axle count rather than a model: "(single axles)",
#: "(Twin axle models)".
_AXLE_QUALIFIER = re.compile(r"\b(single|twin)\s+axles?\b", re.I)

#: A qualifier saying outright that the line varies by model without saying how:
#: "(model specific)", "(where possible)", "(where fitted)".
_UNSPECIFIED = re.compile(r"\bmodel specific\b|\bwhere (?:possible|fitted|applicable)\b", re.I)

#: A token that could be one of Coachman's model identifiers: a three-digit layout code or
#: an upper-case roman numeral.
#:
#: **Deliberately narrow, and still not trusted on its own.** A trailing parenthetical is
#: usually not a model qualifier at all — `(25m)`, `(Thatcham Approved)`, `(5 year Glycol)`
#: — so a token only restricts a line when it matches a model this range actually has.
#: Matching case-sensitively for the roman numerals is what stops the `i` inside
#: "model specific" reading as the Lusso I.
_MODEL_TOKEN = re.compile(r"\b\d{3}\b|\b[IVX]{1,4}\b")


def _tokens_in(text: str) -> set[str]:
    return set(_MODEL_TOKEN.findall(text))


def applies_to(
    line: str, model: str, *, twin_axle: bool, models_in_range: frozenset[str]
) -> bool:
    """Whether one range-wide equipment line applies to one model of that range.

    Coachman publish one equipment list per range and qualify individual lines in
    parentheses. Four cases:

    * `(single axles)` / `(Twin axle models)` — applies to models with that axle count;
    * `(545 Xtra and 575 Xtra)` — applies only to the models named, where those names are
      models **this range has**;
    * `(excluding 660 xtra)` — applies unless this model is the one named;
    * `(model specific)` — applies to nobody. Coachman are saying outright that the line
      does not hold for every model and not saying which, so writing it onto all of them
      would assert exactly what they just denied.

    Anything else — including a parenthetical that names no model, which is most of them —
    leaves the line applying to the whole range. **A line is only ever narrowed on a
    qualifier that demonstrably names a model of this range**, because a rule that guesses
    at parentheses runs silently on every line of every range forever.
    """
    match = _QUALIFIER.search(line)
    if match is None:
        return True
    qualifier = match.group(1)

    if axle := _AXLE_QUALIFIER.search(qualifier):
        return (axle.group(1).lower() == "twin") == twin_axle

    named = _tokens_in(qualifier) & {_model_token(name) for name in models_in_range}
    if named:
        if _EXCLUDING.search(qualifier):
            return _model_token(model) not in named
        return _model_token(model) in named

    return not _UNSPECIFIED.search(qualifier)


def _model_token(model: str) -> str:
    """The part of a model name a qualifier would name. `'545 Xtra'` -> `'545'`."""
    match = _MODEL_TOKEN.search(model)
    return match.group(0) if match else model.strip().upper()


def unmatched_qualifiers(lines: tuple[str, ...], models: frozenset[str]) -> list[str]:
    """Lines qualified for a layout code this range does not have — a site fault to narrate.

    Coachman's Acadia list offers a fridge freezer to `(665 Xtra and 660 Xtra)` in a range
    whose models are 545, 575, 655 and 660. `665` is a typo for `655`, and the consequence
    is real: the Acadia 655 Xtra is left with no refrigeration line at all, because the
    other fridge line is reserved for `(545 Xtra and 575 Xtra)`.

    Narrated every run rather than corrected here. A typo is one wrong number in one place,
    and naming it keeps it visible; inventing a rule that repairs near-miss layout codes
    would run silently on every line Coachman ever publish. Same treatment as the Bailey
    B65 length — see `docs/adapters/README.md`.
    """
    known = {_model_token(name) for name in models}
    flagged: list[str] = []
    for line in lines:
        match = _QUALIFIER.search(line)
        if match is None:
            continue
        qualifier = match.group(1)
        if _AXLE_QUALIFIER.search(qualifier):
            continue
        # Three-digit codes only. A roman numeral that matches nothing is far more likely
        # to be an ordinary word than a mistyped Lusso.
        #
        # **Any** unknown code flags the line, not only a line where every code is unknown:
        # the Acadia's `(665 Xtra and 660 Xtra)` names one real model and one that does not
        # exist, so a stricter test would pass it and the 655 would stay quietly unserved.
        codes = {token for token in _tokens_in(qualifier) if token.isdigit()}
        if codes - known:
            flagged.append(line)
    return flagged


@dataclass(frozen=True)
class CoachmanCaravanSpec:
    """One technical panel, as the fields FMLV wants."""

    internal_length_mm: int | None = None
    shipping_length_mm: int | None = None
    overall_width_mm: int | None = None
    height_mm: int | None = None
    headroom_mm: int | None = None
    awning_length_mm: int | None = None
    mtplm_kilograms: int | None = None
    mro_kilograms: int | None = None
    personal_effects_payload_kilograms: int | None = None
    #: Blank on every model the site speaks for, and set only from Coachman's own file —
    #: see `MANUFACTURER_FILE_2027`.
    optional_equipment_payload_kilograms: int | None = None
    max_nose_weight_kilograms: int | None = None
    #: Read to check the payload columns, never recorded.
    total_payload_kilograms: int | None = None
    rrp_pounds: int | None = None
    berths: int | None = None
    twin_axle: bool = False
    #: Field names taken from Coachman's 2027 model-data file rather than the website, so
    #: `build_extracted` can cite the right source. Empty for every model the site covers.
    from_manufacturer_file: frozenset[str] = frozenset()

    @property
    def payload_reconciles(self) -> bool | None:
        """Whether the payload columns equal `MTPLM - MRO`, or `None` if unknowable.

        The one arithmetic relationship Coachman state four sides of, so it catches a
        misread figure that is otherwise entirely plausible.

        **The two payload columns are summed, not checked one at a time.** They are halves
        of one figure, and on the Acadias the personal half alone is 5kg short of the
        masses by design — see `MANUFACTURER_FILE_2027`. Checking `personal` against
        `MTPLM - MRO` would report all four as broken. `Total / Maximum User Payload`, the
        site's own second row, is still checked whole, because that one *is* the total.
        """
        if self.mtplm_kilograms is None or self.mro_kilograms is None:
            return None
        derived = self.mtplm_kilograms - self.mro_kilograms
        published: list[int] = []
        if (
            self.personal_effects_payload_kilograms is not None
            or self.optional_equipment_payload_kilograms is not None
        ):
            published.append(
                (self.personal_effects_payload_kilograms or 0)
                + (self.optional_equipment_payload_kilograms or 0)
            )
        if self.total_payload_kilograms is not None:
            published.append(self.total_payload_kilograms)
        if not published:
            return None
        return all(value == derived for value in published)


def spec_from_panel(pairs: dict[str, str]) -> CoachmanCaravanSpec:
    """One technical panel's 22 labelled rows as the dozen figures FMLV records.

    Every unreadable value comes back `None`, which is what `TBC` produces and what the
    two unweighed VIPs need: absent, never zero and never an exception.
    """
    millimetres = {
        field: _millimetres(pairs.get(label, "")) for label, field in _PANEL_MILLIMETRES
    }
    kilograms = {
        field: _kilograms(pairs.get(label, "")) for label, field in _PANEL_KILOGRAMS
    }
    berths = _plain(pairs.get("Berths", ""))
    return CoachmanCaravanSpec(
        **millimetres,
        **kilograms,
        awning_length_mm=_centimetres(pairs.get(_AWNING_LABEL, "")),
        total_payload_kilograms=_kilograms(pairs.get(_TOTAL_PAYLOAD_LABEL, "")),
        rrp_pounds=_pounds(pairs.get("Price", "")),
        berths=int(berths) if berths.isdigit() else None,
        twin_axle=bool(_TWIN_AXLE.search(pairs.get("Axles", ""))),
    )


#: Why each field came from the file rather than the page, written into its provenance so
#: a reviewer is not left to work out why one figure has a different source from its
#: neighbours.
#: Coachman's own names for these figures, so provenance reads as their page does rather
#: than as a Python attribute with the underscores taken out.
_FIELD_LABELS: dict[str, str] = {
    "mtplm_kilograms": "MTPLM",
    "mro_kilograms": "Mass in Running Order",
    "personal_effects_payload_kilograms": "personal effects payload",
    "optional_equipment_payload_kilograms": "optional equipment payload",
    "max_nose_weight_kilograms": "Maximum Hitch Weight",
}

_TBC_REASON = "because the site publishes 'TBC' for every mass on this model"

_MANUFACTURER_FILE_REASONS: dict[str, str] = {
    "mtplm_kilograms": _TBC_REASON,
    "mro_kilograms": _TBC_REASON,
    "personal_effects_payload_kilograms": _TBC_REASON,
    "max_nose_weight_kilograms": (
        f"{_TBC_REASON}. Recorded for the TowCheck sister site; FMLV has no column for "
        f"it, so it is a finding and is written only to the readable copy of the upload"
    ),
}

#: The same two columns again, worded for the other reason a figure comes from the file:
#: not a gap on the page, but a published total the page divides wrongly.
_REAPPORTIONED_REASONS: dict[str, str] = {
    "personal_effects_payload_kilograms": (
        "because the site publishes a single payload figure under a label calling it the "
        "personal half, when Coachman's own data shows it is the total of both halves"
    ),
    "optional_equipment_payload_kilograms": (
        "which the technical panel has no row for at all. The split was accepted only "
        "because the two halves add up to exactly the figure the site publishes — the "
        "file is allowed to divide that total, never to change it"
    ),
}

_MANUFACTURER_FILE_FIELDS: tuple[str, ...] = (
    "mtplm_kilograms",
    "mro_kilograms",
    "personal_effects_payload_kilograms",
    "optional_equipment_payload_kilograms",
    "max_nose_weight_kilograms",
)


def apply_manufacturer_file(
    range_label: str,
    model: str,
    spec: CoachmanCaravanSpec,
    *,
    on_progress: Callable[[str], None] = lambda message: None,
) -> CoachmanCaravanSpec:
    """Fold Coachman's own 2027 figures into a spec read off the site, auditing both ways.

    **The site wins wherever it speaks and agrees**, so an entry stops mattering the
    moment Coachman publish the same number, and that is announced rather than left
    silent. Where the site speaks and *disagrees*, the file is still not applied — a
    stored table must never quietly overwrite the live source — but the divergence is
    narrated loudly, because it means one of the two has moved.

    The file is applied only where the site is silent: a `TBC` mass, or the
    optional-equipment column the panel has no row for at all.
    """
    figures = MANUFACTURER_FILE_2027.get((range_label, model))
    if figures is None:
        if note := MANUFACTURER_FILE_DISAGREES.get((range_label, model)):
            on_progress(
                f"[{range_label}] {model} — KNOWN FAULT in Coachman's own 2027 file, not "
                f"a question and not a source conflict: {note}"
            )
        return spec

    if figures.reapportions_published_payload:
        return _reapportion_payload(range_label, model, spec, figures, on_progress)

    changes: dict[str, int] = {}
    taken: set[str] = set()
    for field_name in _MANUFACTURER_FILE_FIELDS:
        supplied = getattr(figures, field_name)
        if supplied is None:
            continue
        live = getattr(spec, field_name)
        if live is None:
            changes[field_name] = supplied
            taken.add(field_name)
        elif live == supplied:
            on_progress(
                f"[{range_label}] {model} — the site now publishes {field_name} as "
                f"{live}, matching Coachman's 2027 file. That entry has done its job and "
                f"can be deleted from MANUFACTURER_FILE_2027"
            )
        else:
            on_progress(
                f"[{range_label}] {model} — DISAGREEMENT: the site publishes "
                f"{field_name} as {live} and Coachman's 2027 file says {supplied}. The "
                f"site is used; one of the two has moved and the file entry needs "
                f"rechecking"
            )

    if not changes:
        return spec

    merged = replace(spec, **changes, from_manufacturer_file=frozenset(taken))
    if merged.payload_reconciles is False:
        on_progress(
            f"[{range_label}] {model} — Coachman's 2027 file does not reconcile once "
            f"merged: MTPLM {merged.mtplm_kilograms} - mass in running order "
            f"{merged.mro_kilograms} is not the payload "
            f"{(merged.personal_effects_payload_kilograms or 0) + (merged.optional_equipment_payload_kilograms or 0)}. "
            f"Recorded anyway, for a reviewer to judge"
        )
    else:
        on_progress(
            f"[{range_label}] {model} — took {', '.join(sorted(taken))} from Coachman's "
            f"2027 model-data file, received 16 November 2026, because the site publishes "
            f"nothing there"
        )
    return merged


def _reapportion_payload(
    range_label: str,
    model: str,
    spec: CoachmanCaravanSpec,
    figures: _ManufacturerFigures,
    on_progress: Callable[[str], None],
) -> CoachmanCaravanSpec:
    """Split the one payload figure the site publishes into the two columns FMLV has.

    **The file is only ever allowed to divide the published total, never to change it.**
    If the two halves do not add up to what the site publishes, the split is refused and
    the site's single figure is left exactly as it was. That is what makes a stored table
    safe here: the worst it can do is decline to act.
    """
    published = spec.personal_effects_payload_kilograms
    personal = figures.personal_effects_payload_kilograms or 0
    optional = figures.optional_equipment_payload_kilograms or 0

    if published is None:
        on_progress(
            f"[{range_label}] {model} — no payload published on the site, so there is "
            f"nothing for Coachman's 2027 file to re-divide"
        )
        return spec

    if personal + optional != published:
        on_progress(
            f"[{range_label}] {model} — KNOWN FAULT in Coachman's own 2027 file, not a "
            f"question and not a source conflict: it divides the payload {personal}kg "
            f"personal + {optional}kg optional = {personal + optional}kg, but the site "
            f"publishes {published}kg and both masses agree with the file "
            f"({spec.mtplm_kilograms} - {spec.mro_kilograms} = {published}). "
            f"{abs(published - personal - optional)}kg are unaccounted for and there is "
            f"no way to tell which half is short, so the split is refused and the site's "
            f"single figure stands. Worth querying with Coachman"
        )
        return spec

    on_progress(
        f"[{range_label}] {model} — divided the site's {published}kg payload into "
        f"{personal}kg personal effects + {optional}kg optional equipment, from "
        f"Coachman's 2027 model-data file. The panel's 'Personal Payload' row is the "
        f"total, not the personal half"
    )
    return replace(
        spec,
        personal_effects_payload_kilograms=personal,
        optional_equipment_payload_kilograms=optional,
        from_manufacturer_file=frozenset(
            {
                "personal_effects_payload_kilograms",
                "optional_equipment_payload_kilograms",
            }
        ),
    )


@dataclass(frozen=True)
class CoachmanCaravanProduct:
    """One caravan: its identity from the API, its figures from the range page's panel."""

    term_id: int
    range_label: str
    range_slug: str
    model: str
    title: str
    #: Every model of this range, so a qualified equipment line can be narrowed only on a
    #: name the range actually has. See `applies_to`.
    models_in_range: frozenset[str] = frozenset()
    spec: CoachmanCaravanSpec | None = None
    equipment: habitation.Equipment | None = None
    #: The homepage card, read purely to check the panel against. See `_agrees_with_card`.
    card_mtplm_kilograms: int | None = None
    card_mro_kilograms: int | None = None
    card_berths: int | None = None

    @property
    def label(self) -> str:
        return " ".join(part for part in (self.range_label, self.model) if part)


def _agrees_with_card(product: CoachmanCaravanProduct) -> str | None:
    """Why the panel and the homepage card disagree, or `None` if they do not.

    The panel is keyed on the `<h2>` above it and the card on `(post type, term ID, model)`.
    Those are two different joins over Coachman's own data, so agreement is real evidence
    that this panel belongs to this caravan — and disagreement means one of the joins has
    slipped, which produces entirely plausible caravans carrying each other's weights.
    Compared only where both sides published a figure, so the two `TBC` models are not
    failed for being blank.
    """
    spec = product.spec
    if spec is None:
        return None
    for name, panel_value, card_value in (
        ("MTPLM", spec.mtplm_kilograms, product.card_mtplm_kilograms),
        ("mass in running order", spec.mro_kilograms, product.card_mro_kilograms),
        ("berths", spec.berths, product.card_berths),
    ):
        if panel_value is not None and card_value is not None and panel_value != card_value:
            return (
                f"the technical panel says {name} {panel_value} and the homepage card "
                f"says {card_value}"
            )
    return None


def build_extracted(
    product: CoachmanCaravanProduct, *, panel_url: str, roster_url: str
) -> ExtractedCaravan:
    """One parsed caravan as a `Caravan` plus the provenance a reviewer reads beside it."""
    spec = product.spec or CoachmanCaravanSpec()
    features = _habitation_features(product)

    caravan = Caravan(
        manufacturer=MANUFACTURER,
        manufacturer_display_name=MANUFACTURER_DISPLAY_NAME,
        manufacturer_range=product.range_label,
        model=product.model,
        berths=spec.berths,
        rrp_pounds=spec.rrp_pounds,
        mtplm_kilograms=spec.mtplm_kilograms,
        mro_kilograms=spec.mro_kilograms,
        personal_effects_payload_kilograms=spec.personal_effects_payload_kilograms,
        optional_equipment_payload_kilograms=spec.optional_equipment_payload_kilograms,
        max_nose_weight_kilograms=spec.max_nose_weight_kilograms,
        internal_length_mm=spec.internal_length_mm,
        shipping_length_mm=spec.shipping_length_mm,
        overall_width_mm=spec.overall_width_mm,
        height_mm=spec.height_mm,
        headroom_mm=spec.headroom_mm,
        awning_length_mm=spec.awning_length_mm,
        twin_axle=spec.twin_axle,
        body_type=CaravanBodyType.RIGID,
        # Habitation, from the range page's equipment list filtered to this model —
        # reported as findings rather than proposed, so the pipeline never writes them.
        heating=features["heating"].value if "heating" in features else None,
        refrigeration=(
            features["refrigeration"].value if "refrigeration" in features else None
        ),
        microwave=features["microwave"].value if "microwave" in features else None,
        shower_toilet_separated=(
            features["shower_toilet_separated"].value
            if "shower_toilet_separated" in features
            else None
        ),
    )

    provenance: dict[str, Provenance] = {}

    def record(field_name: str, snippet: str, source_url: str = panel_url) -> None:
        provenance[field_name] = Provenance(
            source_url=source_url, snippet=f"{product.label} — {snippet}"
        )

    for field_name, label, suffix in (
        ("rrp_pounds", "Price", ""),
        ("berths", "Berths", ""),
        ("mtplm_kilograms", "MTPLM", "kg"),
        ("mro_kilograms", "Mass in Running Order", "kg"),
        ("personal_effects_payload_kilograms", "Personal Payload", "kg"),
        ("internal_length_mm", "Interior Length", "mm"),
        ("shipping_length_mm", "Overall Length", "mm"),
        ("overall_width_mm", "Overall Width", "mm"),
        ("height_mm", "Overall Height (including T.V Aerial)", "mm"),
        ("headroom_mm", "Maximum Headroom", "mm"),
        ("awning_length_mm", _AWNING_LABEL, "mm"),
    ):
        value = getattr(caravan, field_name)
        if value is None or field_name in spec.from_manufacturer_file:
            continue
        rendered = f"£{value:,}" if field_name == "rrp_pounds" else f"{value}{suffix}"
        record(field_name, f"{label}: {rendered}, from the range page's technical panel")

    if (
        spec.max_nose_weight_kilograms is not None
        and "max_nose_weight_kilograms" not in spec.from_manufacturer_file
    ):
        record(
            "max_nose_weight_kilograms",
            f"Maximum Hitch Weight: {spec.max_nose_weight_kilograms}kg. Recorded for the "
            f"TowCheck sister site, which cannot say whether a car may legally tow a "
            f"caravan without it. FMLV has no column for it, so it is reported as a "
            f"finding and written only to the readable copy of the upload",
        )

    # The payload columns, which need saying rather than listing: the site publishes one
    # figure under a label that is wrong on four models, and FMLV has a column for each
    # half. Skipped where the file supplied them — those are cited below instead.
    if (
        spec.personal_effects_payload_kilograms is not None
        and "personal_effects_payload_kilograms" not in spec.from_manufacturer_file
    ):
        record(
            "personal_effects_payload_kilograms",
            f"Personal Payload: {spec.personal_effects_payload_kilograms}kg. Coachman "
            f"publish '{_TOTAL_PAYLOAD_LABEL}' as the same figure and this range carries "
            f"no optional-equipment payload in their own 2027 model data, so the whole of "
            f"MTPLM - mass in running order belongs in this column",
        )

    # Whatever Coachman's own file supplied, cited as theirs and not as the website's.
    reapportioned = (
        "optional_equipment_payload_kilograms" in spec.from_manufacturer_file
    )
    reasons = _REAPPORTIONED_REASONS if reapportioned else _MANUFACTURER_FILE_REASONS
    for field_name in sorted(spec.from_manufacturer_file):
        value = getattr(caravan, field_name)
        if value is None:
            continue
        provenance[field_name] = Provenance(
            source_url=panel_url,
            snippet=(
                f"{product.label} — {_FIELD_LABELS.get(field_name, field_name)}: "
                f"{value}kg, from Coachman's own 2027 model-data file "
                f"('New Model Data 2027 list - Coachman-16-11-26.csv', received "
                f"16 November 2026), {reasons.get(field_name, '')}"
            ),
        )

    # Asserted by the adapter rather than read off the page, so a reviewer should see it
    # said rather than infer it from a value with no source.
    record("twin_axle", f"Axles: {'Twin axle' if spec.twin_axle else 'Single axle'}")
    record(
        "body_type",
        "A touring caravan is rigid unless its walls fold or rise — a lifting roof does "
        "not change the type, even where a manufacturer calls it a pop-up (NCC rule, "
        "7 September 2026). Coachman market no micro and nothing here folds.",
    )
    record(
        "manufacturer_range",
        (
            f"range '{product.range_label}' from taxonomy term {product.term_id}. The "
            f"homepage card is headed '{product.model}' alone, which is not unique across "
            f"ranges, so the range comes from the term and not the card"
        ),
        source_url=roster_url,
    )

    for name, feature in features.items():
        record(
            name,
            (
                f"{feature.note or 'from the range page'}: {feature.snippet!r}. Coachman "
                f"publish this list per range; the line either names no model, so it holds "
                f"for all of {product.range_label}, or names this one"
            ),
        )

    return ExtractedCaravan(caravan=caravan, provenance=provenance)


def _habitation_features(product: CoachmanCaravanProduct) -> dict[str, habitation.Feature]:
    """The range's equipment list, narrowed to the lines that apply to this model.

    `bed_types` is dropped whatever the lines say. The qualifiers select by model where
    they are present, but a bed named in an unqualified line is still a bed asserted across
    the whole range, and the panel's own per-model `Bed Sizes` row is the better source
    that this module has already declined to guess from.
    """
    if product.equipment is None:
        return {}
    twin_axle = product.spec.twin_axle if product.spec else False
    lines = tuple(
        line
        for line in habitation.usable_lines(product.equipment.standard)
        if applies_to(
            line,
            product.model,
            twin_axle=twin_axle,
            models_in_range=product.models_in_range,
        )
    )
    features = habitation.features_from(lines)
    features.pop("bed_types", None)
    return features


def collect(
    http: Fetcher,
    browser: object = None,  # noqa: ARG001 — server-rendered throughout
    snapshot_dir: Path | None = None,  # noqa: ARG001 — `http` snapshots every fetch
    *,
    ranges: tuple[tuple[str, str], ...] | None = None,
    on_progress: Callable[[str], None] = lambda message: None,
) -> list[ExtractedCaravan]:
    """Collect Coachman's touring caravans: four ranges, 19 layouts, three sources.

    `ranges` narrows to the named range slugs for a smoke run; `None` reads whatever the
    taxonomy holds, so a range Coachman add is collected without an edit to this module.
    """
    taxonomy_url = f"{BASE_URL}/wp-json/wp/v2/{POST_TYPE}_model?per_page=100"
    roster_url = f"{BASE_URL}/wp-json/wp/v2/{POST_TYPE}?per_page=100"

    on_progress(f"reading the Coachman caravan ranges from {taxonomy_url} ...")
    taxonomy = http.fetch(taxonomy_url)
    if taxonomy.status_code != 200:
        msg = (
            f"Coachman's caravan taxonomy returned {taxonomy.status_code}; without it no "
            f"product can be given a range"
        )
        raise RuntimeError(msg)
    taxonomy_payload = taxonomy.file_path.read_text(encoding="utf-8", errors="replace")
    ranges_by_id = parse_ranges(taxonomy_payload)
    counts = parse_range_counts(taxonomy_payload)
    slugs_by_id = parse_range_slugs(taxonomy_payload)

    wanted_slugs = {slug for slug, _label in ranges} if ranges else None
    if wanted_slugs is not None:
        ranges_by_id = {
            term: name
            for term, name in ranges_by_id.items()
            if slugs_by_id.get(term) in wanted_slugs
        }
    on_progress(
        f"{len(ranges_by_id)} range(s): "
        + ", ".join(
            f"{name} ({counts.get(term, '?')})" for term, name in ranges_by_id.items()
        )
    )

    on_progress(f"reading the roster from {roster_url} ...")
    roster = http.fetch(roster_url)
    if roster.status_code != 200:
        msg = f"Coachman's caravan roster returned {roster.status_code}; it names every product"
        raise RuntimeError(msg)
    entries = parse_roster(
        roster.file_path.read_text(encoding="utf-8", errors="replace"), POST_TYPE, ranges_by_id
    )
    entries = [entry for entry in entries if entry.term_id in ranges_by_id]
    on_progress(f"{len(entries)} caravan(s) in the roster")

    homepage_url = f"{BASE_URL}/"
    on_progress(f"fetching {homepage_url} to check the panels against its cards ...")
    homepage = http.fetch(homepage_url)
    cards = (
        parse_cards(homepage.file_path.read_text(encoding="utf-8", errors="replace"))
        if homepage.status_code == 200
        else {}
    )
    if not cards:
        on_progress(
            f"WARNING: the homepage returned {homepage.status_code} and no cards were "
            f"read, so the panels are recorded without their cross-check"
        )

    products: list[CoachmanCaravanProduct] = []
    for term, slug in slugs_by_id.items():
        if term not in {entry.term_id for entry in entries}:
            continue
        label = ranges_by_id.get(term, str(term))
        page = http.fetch(f"{BASE_URL}/{slug}/")
        if page.status_code != 200:
            on_progress(
                f"[{label}] SKIPPED the whole range: /{slug}/ returned {page.status_code}, "
                f"and its technical panels are the only source of every figure"
            )
            continue
        range_html = page.file_path.read_text(encoding="utf-8", errors="replace")
        panels = parse_specification_panels(range_html)
        equipment = parse_equipment(range_html)

        in_range = [entry for entry in entries if entry.term_id == term]
        models_in_range = frozenset(entry.model for entry in in_range)
        for faulty in unmatched_qualifiers(tuple(equipment.standard), models_in_range):
            on_progress(
                f"[{label}] KNOWN SITE FAULT, not a question: an equipment line names a "
                f"layout this range does not have, so whichever model that was meant for "
                f"goes without it — {faulty!r}"
            )

        for entry in in_range:
            pairs = panels.get(entry.model)
            if pairs is None:
                on_progress(
                    f"[{label}] {entry.title} — SKIPPED: no technical panel headed "
                    f"'{entry.model}' on /{slug}/, so it has no figures at all"
                )
                continue
            # `CoachmanCard.key` squashes the heading to alphanumerics, so the lookup must
            # squash the roster's model the same way: the card reads `545 Xtra`.
            card = cards.get((POST_TYPE, term, _squash(entry.model)))
            products.append(
                CoachmanCaravanProduct(
                    term_id=term,
                    range_label=label,
                    range_slug=slug,
                    model=entry.model,
                    title=entry.title,
                    models_in_range=models_in_range,
                    spec=apply_manufacturer_file(
                        label,
                        entry.model,
                        spec_from_panel(pairs),
                        on_progress=on_progress,
                    ),
                    equipment=equipment,
                    card_mtplm_kilograms=card.mtplm_kilograms if card else None,
                    card_mro_kilograms=card.mro_kilograms if card else None,
                    card_berths=card.berths if card else None,
                )
            )

    # Coachman's own CMS counts its products per range — a completeness check they
    # maintain against themselves, in a machine-readable field.
    for term, expected in counts.items():
        if term not in ranges_by_id:
            continue
        found = sum(1 for product in products if product.term_id == term)
        if found != expected:
            on_progress(
                f"WARNING: the taxonomy says {ranges_by_id.get(term, term)!r} has "
                f"{expected} model(s) but {found} were collected"
            )

    results: list[ExtractedCaravan] = []
    for product in products:
        if disagreement := _agrees_with_card(product):
            on_progress(
                f"{product.label} — SKIPPED: {disagreement}, so the panel may belong to "
                f"another caravan"
            )
            continue
        spec = product.spec
        if spec is not None and spec.payload_reconciles is False:
            # Narrated, not dropped: the figures are Coachman's own and a reviewer seeing
            # all four can judge. Discarding a real caravan over an arithmetic quibble
            # would hide the page rather than the problem.
            on_progress(
                f"{product.label}: payload {spec.personal_effects_payload_kilograms}kg "
                f"does not equal MTPLM - mass in running order "
                f"({spec.mtplm_kilograms} - {spec.mro_kilograms}) — recording anyway"
            )
        if spec is not None and spec.mtplm_kilograms is None:
            on_progress(
                f"{product.label}: every mass is published as 'TBC', so MTPLM, mass in "
                f"running order, payload and nose weight are left blank"
            )
        results.append(
            build_extracted(
                product,
                panel_url=f"{BASE_URL}/{product.range_slug}/",
                roster_url=roster_url,
            )
        )
        on_progress(f"read {product.label}")

    on_progress(f"{len(results)} caravan(s) collected")
    return results
