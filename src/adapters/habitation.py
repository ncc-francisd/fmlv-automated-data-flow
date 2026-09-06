"""Habitation features read from a manufacturer's own spec prose.

The fields in `schema.LAYOUT` divide sharply in how hard they are to collect, and the
requester drew the line on 6 September 2026:

* **Factual** — refrigeration, heating, microwave, rear garage, and whether the shower
  and toilet are separated. Manufacturers state these *in words* in a specification
  list, so an adapter can extract them and quote the line it read. That is what this
  module does.
* **Subjective** — lounge location, sleeping area, kitchen location, and (for most
  brands) which beds a layout has. These need a floorplan drawing, and a reviewer picks
  them from a dropdown given a link to it. Nothing here attempts them, except bed types
  where the copy names the beds outright, which several brands do.

This lives outside any one adapter because the vocabulary is the **industry's, not a
manufacturer's**: "141L fridge with freezer compartment", "Combi C4 heating", "separate
shower cubicle and cassette toilet", "electric drop-down double bed" are phrasings that
recur across brands. An adapter passes its spec lines in and gets back a value plus the
line that justified it, which becomes the provenance snippet a reviewer clicks through to.

Two rules run through all of it:

* **Only ever assert a feature from positive evidence.** A page that never mentions a
  microwave is not a page saying there is no microwave, so `microwave_from` returns
  `None` rather than `False` and the field is left for a reviewer. Silence is not a
  negative — the same principle as `docs/adapters/README.md` on unfound figures.
* **Never read a paid option as standard equipment.** "Rear Adjustable Bed Option:
  £1,500" describes a bed the buyer may not have, and `_is_option` filters those lines
  out before anything else looks at them.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from ..product_model.enums import BathroomLayout, BedType, Heating, Refrigeration


@dataclass(frozen=True)
class Feature:
    """One habitation field's value and the source line that justified it.

    `snippet` is what a reviewer reads next to the proposal, so it is the manufacturer's
    own wording verbatim rather than a paraphrase — the requester asked for "a source
    which takes me to precisely that section of text".
    """

    value: Any
    snippet: str

#: A spec line describing a priced extra rather than standard equipment. The price is the
#: giveaway — Rimor's "Rear Adjustable Bed Option: £1,500" and "Alloy wheel option:
#: £1,350" both carry one — and so is an explicit "option"/"extra" with a colon.
_OPTION = re.compile(r"£\s*[\d,]|\b(?:option|optional|extra)s?\b\s*[:\-]|\bcost option\b", re.I)

#: The `Tags` and `Categories` metadata lines. They repeat feature words out of context
#: ("Tags 687TC, rimor, transverse bed"), so they are never read as specification.
_METADATA = re.compile(r"^\s*(tags|categories)\b", re.I)


def _is_option(line: str) -> bool:
    return bool(_OPTION.search(line))


def usable_lines(lines: Iterable[str]) -> list[str]:
    """The specification lines worth reading: no priced options, no tag metadata."""
    return [
        line
        for line in lines
        if line.strip() and not _is_option(line) and not _METADATA.match(line)
    ]


def _first_match(lines: Iterable[str], pattern: re.Pattern[str]) -> str | None:
    """The first line matching `pattern`, for quoting as provenance."""
    return next((line for line in lines if pattern.search(line)), None)


# --- Refrigeration -------------------------------------------------------------------

#: A freezer, however it is worded. The requester's ruling, 6 September 2026: *"If there
#: is any mention of freezer compartment, then I would say it is proposed as a fridge
#: freezer."* This is checked across **every** line, never just the one naming the
#: fridge, because the same page routinely abbreviates: Rimor's Sarus 66 Plus summary
#: says "141 L fridge" while its specification list says "141L fridge with freezer
#: compartment". Reading the summary alone would silently downgrade it.
_FREEZER = re.compile(r"\bfreezer\b|\bfreezer compartment\b|\bfridge[-/ ]freezer\b", re.I)

#: Any refrigeration at all. `refrigerator column` is Rimor's phrasing for a tall fridge.
_FRIDGE = re.compile(r"\bfridge\b|\brefrigerator\b|\brefrigeration\b", re.I)


def refrigeration_from(lines: Iterable[str]) -> tuple[Refrigeration, str] | None:
    """`(Refrigeration, the line that said so)`, or `None` if no fridge is mentioned.

    A freezer anywhere on the page wins, since a page that mentions one both has one and
    has a fridge to put it in.
    """
    usable = usable_lines(lines)
    if freezer_line := _first_match(usable, _FREEZER):
        return Refrigeration.FRIDGE_FREEZER, freezer_line
    if fridge_line := _first_match(usable, _FRIDGE):
        return Refrigeration.FRIDGE, fridge_line
    return None


# --- Heating -------------------------------------------------------------------------

#: Warm-air heating. The requester's ruling, 6 September 2026: *"any mention of the word
#: blown air or warm air means it's a warm air and not a wet central heating system […]
#: we just want to know whether it is a water based, wet central heating system or a warm
#: air one. We don't really care whether it's a Truma brand or a different type."*
#:
#: `Combi` and `AirTop` are here because they settle the question even though they name a
#: product: a Truma Combi is a warm-air heater with a water tank in it, not a wet system,
#: which the requester confirmed in the same ruling. They are the phrasings Rimor
#: actually uses — 33 of its 34 products say "Combi C4/C6 heating and hot water system"
#: or "Truma Combi C6", and one says "Webasto AirTop".
_WARM_AIR = re.compile(
    r"\bblown[- ]air\b|\bwarm[- ]air\b|\bforced[- ]air\b|\bcombi\b|\bairtop\b|\bair top\b",
    re.I,
)

#: Water-based central heating. Deliberately narrow, and **never a bare "wet"**: "Wet
#: room Shower and cassette toilet" appears on seven Rimor products and is a bathroom,
#: not a heating system. Matching `wet` alone would have called every one of them wet
#: central heating.
_WET_CENTRAL = re.compile(
    r"\bwet[- ]central\b|\bwet[- ]system\b|\bwet[- ]heating\b|\balde\b"
    r"|\bwater[- ]based\b|\bradiator|\bunderfloor heating\b",
    re.I,
)

#: A heating system of unspecified kind, used only to tell "no heating mentioned" from
#: "heating mentioned but the type is unclear" — the second is narrated, not proposed.
_ANY_HEATING = re.compile(r"\bheating\b|\bheater\b", re.I)


def heating_from(lines: Iterable[str]) -> tuple[Heating, str] | None:
    """`(Heating, the line that said so)`, or `None` when the type is not settled.

    Wet central is tested first: a vehicle with radiators may well also have a blown-air
    booster, and the water system is the answer to the question FMLV asks. `None` covers
    both "no heating mentioned" and "heating mentioned but neither kind named", which are
    different situations — see `heating_is_unclear`.
    """
    usable = usable_lines(lines)
    if wet_line := _first_match(usable, _WET_CENTRAL):
        return Heating.WET_CENTRAL, wet_line
    if warm_line := _first_match(usable, _WARM_AIR):
        return Heating.BLOWN_AIR, warm_line
    return None


def heating_is_unclear(lines: Iterable[str]) -> str | None:
    """The line mentioning heating whose *kind* could not be determined, if any.

    Worth narrating: it means the vocabulary above needs a phrase adding, rather than the
    manufacturer having said nothing.
    """
    usable = usable_lines(lines)
    if heating_from(usable) is not None:
        return None
    return _first_match(usable, _ANY_HEATING)


# --- Microwave -----------------------------------------------------------------------

#: A microwave, and specifically not an oven or a grill — Rimor lists "Oven" on 24
#: products and a microwave on none, so conflating them would invent 24 microwaves.
_MICROWAVE = re.compile(r"\bmicrowave\b|\bcombination oven\b|\bcombi oven\b", re.I)


def microwave_from(lines: Iterable[str]) -> tuple[bool, str] | None:
    """`(True, the line that said so)` when a microwave is stated, else `None`.

    **Never returns `False`.** A page that does not mention a microwave is not a page
    saying there is none, and `microwave` defaults to `False` on the product, so
    returning `False` here would propose an unevidenced negative on every product.
    """
    if line := _first_match(usable_lines(lines), _MICROWAVE):
        return True, line
    return None


# --- Bathroom ------------------------------------------------------------------------

#: The shower and toilet in separate compartments — the one bathroom fact that is stated
#: in words rather than needing a drawing. The requester, 6 September 2026: *"if the
#: bathroom is integrated with a shower and toilet together or has a clear separation
#: within one room […] or has two separate rooms with separate doors […] basically a
#: factual output of separated toilet and shower."*
#:
#: `separate` has to sit next to the shower or the toilet, not merely somewhere on the
#: line: "Rear twin single beds" pages also say "separate" about other things.
_SEPARATE_BATHROOM = re.compile(
    r"\bseparate\b[^.]{0,40}\b(?:shower|toilet|wc)\b|\b(?:shower|toilet|wc)\b[^.]{0,40}\bseparate\b",
    re.I,
)

#: A single wet space — shower over the toilet, no division. Rimor says "Wet room".
_WET_ROOM = re.compile(r"\bwet[- ]room\b|\bshower over (?:the )?toilet\b", re.I)

#: An external shower is not the vehicle's bathroom, and says nothing about its layout.
_EXTERNAL_SHOWER = re.compile(r"\bexternal\b[^.]{0,30}\bshower\b|\boutdoor shower\b", re.I)


def bathroom_from(lines: Iterable[str]) -> tuple[BathroomLayout, str] | None:
    """`(BathroomLayout, the line that said so)`, or `None` when the copy cannot settle it.

    Only the **separated** case is decided here, because it is the only one the words
    determine. A combined washroom still needs a location — `BathroomLayout` offers
    `rear_shower_toilet` and `side_shower_toilet`, and nothing in the prose says which —
    so a wet room returns `None` and goes to the reviewer with the floorplan.
    """
    usable = [line for line in usable_lines(lines) if not _EXTERNAL_SHOWER.search(line)]
    if _first_match(usable, _WET_ROOM):
        return None
    if line := _first_match(usable, _SEPARATE_BATHROOM):
        return BathroomLayout.SEPARATE_SHOWER_TOILET, line
    return None


# --- Bed types -----------------------------------------------------------------------

#: Bed wording -> FMLV bed type, longest phrase first so `double bunk beds` is not read
#: as a plain `bed`. Unlike the other groups here `bed_types` is a **list**: a layout
#: routinely has a fixed bed at the back and a drop-down over the cab, which is exactly
#: the Sarus 66 Plus case that prompted this module — FMLV holds island + drop-down and
#: the adapter had been proposing island alone.
BED_PHRASES: tuple[tuple[str, BedType], ...] = (
    ("drop-down", BedType.DROP_DOWN),
    ("drop down", BedType.DROP_DOWN),
    ("dropdown", BedType.DROP_DOWN),
    ("bunk bed", BedType.FIXED_BUNKS),
    ("bunks", BedType.FIXED_BUNKS),
    ("island bed", BedType.ISLAND),
    ("central bed", BedType.ISLAND),
    ("transverse", BedType.TRANSVERSE),
    ("twin single bed", BedType.FIXED_SEPARATE),
    ("twin bed", BedType.FIXED_SEPARATE),
    ("single beds", BedType.FIXED_SEPARATE),
    # `fixed_bed` is asserted **only from an explicit word**, never from a shape or a
    # size. "French bed" describes a cut corner, "double" describes width, and neither
    # says the bed is permanently made up — Rimor's Horus 12 has "a rear double French
    # bed that also lifts to create more storage space", which is not a fixed bed at all.
    # The requester, 6 September 2026: *"A double bed is not a fixed bed […] French bed
    # really has to do with the shape of it. It normally is fixed, but actually that's not
    # relevant. It says it folds away."*
    #
    # A shape word with nothing else to go on therefore contributes nothing, and the
    # layout falls through to its floorplan — which is the honest answer, since FMLV has
    # no column for "French bed" and the only question it asks is built-in versus made up.
    ("fixed bed", BedType.FIXED),
    ("fixed double", BedType.FIXED),
    ("permanent bed", BedType.FIXED),
)

#: A bed made up rather than permanently there.
#: A bed made up rather than permanently there. `lift` is here alongside the folding
#: words because it is the same claim in different clothes: Rimor's Horus 12 bed "lifts to
#: create more storage space for travel", so it is not standing made up.
_MAKE_UP = re.compile(
    r"\bconvert\w*\b|\bmakes? (?:up )?(?:into )?a?\s*(?:double|single|bed)"
    r"|\bmake[- ]up bed\b|\bfold[- ]?(?:s|ing)?[- ]away\b|\bpull[- ]out bed\b"
    r"|\blifts?\b|\blift[- ]up\b|\bstow\w*\b",
    re.I,
)

#: Seating that becomes a bed. This decides whether a shape named on the same line is
#: *also* recorded, and the distinction is whether the bed exists when nobody is making
#: it up:
#:
#: * "Rear lounge which converts into single beds" — the singles exist only once the
#:   lounge is made up, so this is `make_up_beds` **and not** `fixed_separate_beds`.
#: * "Rear Twin single beds, which can make a double bed" — the twins are permanently
#:   there and join to make a double, so this is `fixed_separate_beds` **and**
#:   `make_up_beds`. `bed_types` is the schema's one multi-select group, so recording
#:   both is right rather than a compromise.
_SEATING = re.compile(r"\blounge\b|\bdinette\b|\bsettee\b|\bseating\b", re.I)

#: Lines that mention a bed without describing the vehicle's sleeping arrangement — an
#: accessory, or a bed used as a landmark. Rimor's "Twin bed divider with steps. By
#: night, a handy step for climbing into bed…" is the case in point.
_NOT_A_BED = re.compile(r"\bdivider\b|\bstep for climbing\b|\bbed linen\b|\bmattress\b", re.I)


def bed_types_from(lines: Iterable[str]) -> tuple[list[BedType], list[str]]:
    """`(bed types, the lines that named them)`, both empty when the copy names none.

    The requester's ruling, 6 September 2026: *"if the statement is there about what beds
    are there, a drop down bed and an island bed in the copy or in the specification list
    or in general copy, then I would include that as a proposal."*

    Order is the order the copy names them, deduplicated, so the provenance reads in the
    same sequence as the value. Paid options are already gone via `usable_lines`, so a
    "Rear Adjustable Bed Option: £1,500" never becomes a bed the buyer may not have.
    """
    found: list[BedType] = []
    quoted: list[str] = []
    for line in usable_lines(lines):
        if _NOT_A_BED.search(line):
            continue
        lowered = line.lower()
        if "bed" not in lowered and "bunk" not in lowered:
            continue

        matches: list[BedType] = []
        makes_up = bool(_MAKE_UP.search(line))
        if makes_up:
            matches.append(BedType.MAKE_UP)
        # A shape is only credited when it is not merely what the seating turns into.
        if not (makes_up and _SEATING.search(line)):
            for phrase, bed_type in BED_PHRASES:
                if phrase in lowered:
                    matches.append(bed_type)

        new = [b for b in dict.fromkeys(matches) if b not in found]
        if new:
            found.extend(new)
            quoted.append(line)
    return found, quoted


# --- One entry point -----------------------------------------------------------------

def features_from(lines: Iterable[str]) -> dict[str, Feature]:
    """Every habitation feature a manufacturer's spec prose settles, keyed by field name.

    The keys are `Motorhome`/`Caravan` field names, so an adapter can hand the result
    straight to its product builder and its provenance recorder without knowing which
    features were found. Absent keys mean "the copy did not say", which is deliberately
    different from a `False` or a blank — see the module docstring.

    Wiring a second adapter into this should be one call plus a loop, which is the point
    of it living here rather than in `rimor.py`.
    """
    usable = usable_lines(lines)
    features: dict[str, Feature] = {}

    if found := refrigeration_from(usable):
        features["refrigeration"] = Feature(found[0], found[1])
    if found := heating_from(usable):
        features["heating"] = Feature(found[0], found[1])
    if found := microwave_from(usable):
        features["microwave"] = Feature(found[0], found[1])
    if found := bathroom_from(usable):
        features["bathroom_layout"] = Feature(found[0], found[1])

    bed_types, quotes = bed_types_from(usable)
    if bed_types:
        features["bed_types"] = Feature(bed_types, " / ".join(quotes))
    return features
