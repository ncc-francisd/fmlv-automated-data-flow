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
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from html import unescape
from typing import Any

from ..product_model.enums import BathroomLayout, BedType, Heating, Refrigeration


@dataclass(frozen=True)
class Feature:
    """One habitation field's value and the source line that justified it.

    `snippet` is what a reviewer reads next to the proposal, so it is the manufacturer's
    own wording verbatim rather than a paraphrase — the requester asked for "a source
    which takes me to precisely that section of text".

    `note` is how that quote is introduced when the reasoning is not simply "it says so":
    an adapter's own wording is used when it is `None`. `refrigeration` needs it because
    a fridge freezer is now recorded from a line that says only "fridge", and a reviewer
    who cannot see why would read that as a mistake.
    """

    value: Any
    snippet: str
    note: str | None = None

#: A spec line describing a priced extra rather than standard equipment. The price is the
#: giveaway — Rimor's "Rear Adjustable Bed Option: £1,500" and "Alloy wheel option:
#: £1,350" both carry one — and so is an explicit "option"/"extra" with a colon.
#:
#: **`retailer fit` and `dealer fit` mean the same thing** and are Bailey's words for it:
#: "Fitted microwave oven (Retailer fit)" sits in the same bulleted list as the standard
#: equipment and describes a microwave the factory does not install. Reading it as fitted
#: would assert a microwave on every Bailey that merely *can* have one.
#:
#: An **optional** item is not the same as an absent one, and the difference matters most
#: for the microwave: a brand that offers one has not said there is none, so an adapter
#: should check the unfiltered lines before reporting an absence. `niesmann_bischoff` and
#: `bailey` both word their note that way.
#:
#: **`option of` is a choice, not a fitting**, and Murvi write their whole kitchen that
#: way: "Option of 12v 115L Isotherm compressor fridge, 12v 85L compressor fridge or
#: Dometic RM10.5T - 3-way, 93L AES fridge". Three fridges, none of them standard, and
#: recording any one of them would tell a reviewer the buyer has no say. `only available
#: with` is the same claim from the other end — Murvi's rear storage area is "only
#: available with a 65L compressor fridge", which states a condition, not a fitting.
_OPTION = re.compile(
    r"£\s*[\d,]|\b(?:option|optional|extra)s?\b\s*[:\-]|\bcost option\b"
    r"|\boption of\b|\bonly available with\b"
    r"|\((?:retailer|dealer)[- ]fit(?:ted)?\)",
    re.I,
)

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
#:
#: **`frozen compartment` is Dometic's own label** and Elddis quote it verbatim —
#: "Capacity 92L / Refrigerator compartment - 80,3L / Frozen compartment 12,1L". Without
#: it every Elddis fridge fell through to the assumption below, which reaches the same
#: answer but tells a reviewer the page did not say when it plainly did.
_FREEZER = re.compile(
    r"\bfreezer\b|\bfreezer compartment\b|\bfridge[-/ ]freezer\b|\bfrozen compartment\b",
    re.I,
)

#: A page saying there is **no** freezer. This is now the only thing that makes a plain
#: `fridge`, so it has to catch the ways a spec denies one — "no freezer", "without a
#: freezer compartment", "freezer not fitted" — while never matching the far commoner
#: line that states one. It is tested before `_FREEZER` because "fridge without freezer
#: compartment" contains both.
#:
#: The denial has to sit in **one clause**, which is why the gaps exclude a comma as well
#: as a full stop: "141L fridge with freezer compartment, oven not fitted" and "no oven,
#: 141 L freezer" both put a negative within a few words of a freezer that is really
#: there, and matching either would flip a fridge freezer to a fridge on a page that
#: states one outright.
_NO_FREEZER = re.compile(
    r"\bno\b[^.,]{0,25}\bfreezer\b|\bwithout\b[^.,]{0,25}\bfreezer\b"
    r"|\bfreezer\b[^.,]{0,25}\bnot\b[^.,]{0,15}\b(?:included|fitted|available|supplied)\b",
    re.I,
)

#: Any refrigeration at all. `refrigerator column` is Rimor's phrasing for a tall fridge.
_FRIDGE = re.compile(r"\bfridge\b|\brefrigerator\b|\brefrigeration\b", re.I)


def refrigeration_from(lines: Iterable[str]) -> Feature | None:
    """The refrigeration a page evidences, or `None` if no fridge is mentioned at all.

    Three cases, in the order they are tested:

    * **A freezer is denied** — a plain `fridge`. Explicit, and rare.
    * **A freezer is stated** anywhere on the page — a `fridge_freezer`. Any line will
      do, since a page mentioning a freezer both has one and has a fridge to put it in.
    * **A fridge, with the freezer neither stated nor denied** — also a `fridge_freezer`.

    That third case reverses the earlier reading, on the requester's ruling of 7
    September 2026: *"eighty to ninety percent of fridges supplied to caravan and motor
    home providers actually come with a freezer compartment […] unless it says it doesn't
    have a freezer compartment, we should be basically saying it has a fridge freezer
    even if the specification just says it has a ninety litre or a hundred and forty
    litre fridge, because the freezer compartment often goes unsaid."* The trade fits
    Dometic units, which almost all have one. FMLV's own hand-filled baseline agrees:
    `fridge_freezer` is Yes on 89% of the 1,590 rows in `data/exports`, so proposing
    `fridge` from a silent spec was contradicting the reviewers most of the time.

    This is the one feature here asserted from something other than the words on the
    page, so it carries a `note` saying so rather than letting a reviewer discover a
    "141 L fridge" quote under a fridge-freezer proposal and read it as a bug.
    """
    usable = usable_lines(lines)
    if denied := _first_match(usable, _NO_FREEZER):
        return Feature(Refrigeration.FRIDGE, denied, "the specification rules out a freezer")
    if freezer_line := _first_match(usable, _FREEZER):
        return Feature(Refrigeration.FRIDGE_FREEZER, freezer_line, "a freezer is mentioned")
    if fridge_line := _first_match(usable, _FRIDGE):
        return Feature(
            Refrigeration.FRIDGE_FREEZER,
            fridge_line,
            "a fridge, with a freezer neither stated nor ruled out — nearly all of these "
            "have a freezer compartment, so a fridge freezer",
        )
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
#:
#: **`hot air` is the Erwin Hymer Group's word for the same thing**, and its absence here
#: was why Dethleffs produced no heating reading at all: every one of its 48 layouts
#: publishes either "Gas hot air heating 6kW with 1.8kW electric heating element and hot
#: water boiler" or the diesel equivalent, and not one says "blown" or "warm". The hot
#: water boiler in those lines heats domestic water rather than radiators — the same
#: arrangement as the Truma Combi ruled on above.
#: `night heater` is the campervan trade's name for a small diesel air heater — Webasto's
#: Air Top and Eberspächer's Airtronic are both sold as one, and Moto-Trek list a
#: "Webasto Diesel Night heater". There is no such thing as a wet night heater: a water
#: heater is sold as a water heater.
_WARM_AIR = re.compile(
    r"\bblown[- ]air\b|\bwarm[- ]air\b|\bhot[- ]air\b|\bforced[- ]air\b"
    r"|\bcombi\b|\bairtop\b|\bair top\b|\bnight heater\b",
    re.I,
)

#: Water-based central heating. Deliberately narrow, and **never a bare "wet"**: "Wet
#: room Shower and cassette toilet" appears on seven Rimor products and is a bathroom,
#: not a heating system. Matching `wet` alone would have called every one of them wet
#: central heating.
#:
#: **`hot water heating` is a wet system and `hot water boiler` is not**, which is why the
#: phrase has to carry the word "heating" itself. Dethleffs' Alpa publishes "Hot-water
#: heating with boiler, automatic drain valve and shut-off valve" — radiators, drained for
#: winter — while its Globebus publishes "Gas hot air heating […] and hot water boiler",
#: where the boiler heats the taps. Matching a bare "hot water" would call both wet.
#: **`warm water heating` is the same system under another adjective** — Dethleffs write
#: "Hot-water heating", Niesmann + Bischoff "Warm water heating with thermostat control,
#: heating cartridge and touch screen panel". Both require the word "heating" for the
#: reason above, so a warm-water *boiler* still reads as domestic hot water.
#:
#: A `heating circuit` is plumbing by definition, and Niesmann's own line gives it away:
#: "(independent heating circuit in the rear bedroom)". Nothing blown-air is zoned that way.
_WET_CENTRAL = re.compile(
    r"\bwet[- ]central\b|\bwet[- ]system\b|\bwet[- ]heating\b|\balde\b"
    r"|\b(?:hot|warm)[- ]water heating\b|\bheating circuit\b"
    # `radiator` excludes the **base vehicle's** one. Bürstner's Habiton document lists
    # "Radiator grille surround, front and rear bumpers painted in vehicle colour", which
    # is a paint option on a Mercedes and was reading as wet central heating.
    r"|\bwater[- ]based\b|\bradiator\b(?!\s*(?:grille?|cover|surround|trim))"
    r"|\bunderfloor heating\b",
    re.I,
)

#: A heating system of unspecified kind, used only to tell "no heating mentioned" from
#: "heating mentioned but the type is unclear" — the second is narrated, not proposed.
_ANY_HEATING = re.compile(r"\bheating\b|\bheater\b|\bheat exchanger\b", re.I)

#: A second heater fitted alongside the real one, which says nothing about what the
#: vehicle's heating system *is*. Bürstner's Habiton lists "Electric auxiliary warm air
#: heater" beside a "Diesel hybrid heating (Timberline 1.0)" whose kind it never states;
#: read as the system, the auxiliary unit would have answered a question the document
#: leaves open. Filtered out of the heating reading entirely — including the "unclear"
#: narration, since it is not the line anyone needs to see.
_AUXILIARY_HEATER = re.compile(
    r"\bauxiliar(?:y|ies)\b|\bsupplementary\b|\bbooster\b|\bsecond(?:ary)? heater\b"
    r"|\bfrost protection\b|\bengine[- ]driven\b",
    re.I,
)

#: **How the plumbing gives a system away**, from the requester on 10 September 2026:
#: *"If the spec sheet mentions fluid capacity (litres), a circulation pump, or glycol, it
#: is a wet system. If it lists airflow (m³/h), ducting diameter (e.g. 60mm/90mm), or
#: outlet vents, it is a blown air system."*
#:
#: These are the **weak tier**, and what separates them from the patterns above is that
#: they are trusted only on a line that also mentions heating. Every one of them appears
#: innocently elsewhere: a fresh water tank has a capacity in litres, an air conditioner
#: quotes m³/h, and a washroom has an extractor vent. A brand fitting an aircon beside a
#: wet heater would otherwise be read as blown air off the aircon's airflow figure.
#:
#: `circulation` is required alongside the pump for the same reason — Eriba and Laika both
#: list a "submersible pump", which is the fresh water one.
_WET_PLUMBING = re.compile(
    r"\bglycol\b|\bcirculation pump\b|\bfluid capacity\b|\bheating fluid\b"
    r"|\bsystem fluid\b|\bexpansion (?:tank|vessel)\b",
    re.I,
)

#: The other half of the same ruling. `duct` covers the diameter case — a spec quoting
#: "60 mm ducting" is describing where the warm air goes.
_AIR_DUCTING = re.compile(
    r"\bm³/h\b|\bm3/h\b|\bcubic met(?:re|er)s? per hour\b"
    r"|\bduct(?:ing|ed|s)?\b|\boutlet vents?\b|\bwarm[- ]air outlets?\b",
    re.I,
)


def heating_from(lines: Iterable[str]) -> tuple[Heating, str] | None:
    """`(Heating, the line that said so)`, or `None` when the type is not settled.

    Wet central is tested before blown air **within a tier**: a vehicle with radiators
    may well also have a blown-air booster, and the water system is the answer to the
    question FMLV asks. `None` covers both "no heating mentioned" and "heating mentioned
    but neither kind named", which are different situations — see `heating_is_unclear`.

    **A line that is about the heating outranks one that merely contains a heating
    word**, whichever system it points at, and that is why the tiers are ordered the way
    they are rather than wet-then-air twice over. A washroom towel radiator is not a
    heating system: Swift's Conqueror lists "Towel rail above radiator", Auto-Trail's
    Frontier "Washroom area radiator". Where such a page also says "Blown air heating
    outlets", the blown air is the answer and the towel rail is a fitting.

    An **auxiliary** heater is discarded outright — see `_AUXILIARY_HEATER`. It is a
    second unit alongside the real one, so it answers nothing about the system.
    """
    usable = [
        line for line in usable_lines(lines) if not _AUXILIARY_HEATER.search(line)
    ]
    about_heating = [line for line in usable if _ANY_HEATING.search(line)]

    for scope in (about_heating, usable):
        if wet_line := _first_match(scope, _WET_CENTRAL):
            return Heating.WET_CENTRAL, wet_line
        if warm_line := _first_match(scope, _WARM_AIR):
            return Heating.BLOWN_AIR, warm_line

    # The weak tier, and only on a line that is talking about heating — see
    # `_WET_PLUMBING`. Wet still wins over air where a page carries both, for the same
    # reason as above: a wet system with a blown-air booster is a wet system.
    if plumbing := _first_match(about_heating, _WET_PLUMBING):
        return Heating.WET_CENTRAL, plumbing
    if ducting := _first_match(about_heating, _AIR_DUCTING):
        return Heating.BLOWN_AIR, ducting
    return None


def heating_is_unclear(lines: Iterable[str]) -> str | None:
    """The line mentioning heating whose *kind* could not be determined, if any.

    Worth narrating: it means the vocabulary above needs a phrase adding, rather than the
    manufacturer having said nothing.

    A bare `Heating` is a section heading, not a statement, so a line that says something
    is preferred — Bürstner's Habiton document has both, and "Diesel hybrid heating
    (Timberline 1.0) with control panel" is the line whose kind nobody could name.
    """
    usable = [
        line for line in usable_lines(lines) if not _AUXILIARY_HEATER.search(line)
    ]
    if heating_from(usable) is not None:
        return None
    substantive = [line for line in usable if len(line.split()) > 2]
    return _first_match(substantive, _ANY_HEATING) or _first_match(usable, _ANY_HEATING)


# --- Microwave -----------------------------------------------------------------------

#: A microwave, and specifically not an oven or a grill — Rimor lists "Oven" on 24
#: products and a microwave on none, so conflating them would invent 24 microwaves.
#:
#: **`combination oven` used to be here and had to come out** (10 September 2026). In the
#: British caravan trade the phrase means a gas oven and grill in one housing, not a
#: microwave-combi: Bailey publish "Combination oven (oven, grill, hob combined)" and
#: "Thetford triplex combination oven, grill with electronic ignition and flame failure
#: device" — a flame failure device being conclusive proof it burns gas. Every occurrence
#: across every fixture in this project is that appliance, so the phrase was inventing a
#: microwave on Bailey's caravans and on the Endeavour campervan. A real microwave-combi
#: says "microwave" somewhere in its name, which the first alternative already catches.
_MICROWAVE = re.compile(r"\bmicrowave\b", re.I)

#: A line that mentions a microwave only to exclude it — Murvi's "Additional 60W solar
#: panel (not with microwave oven)". It still proves one is offered, so it is not
#: discarded; it is just the worse quote of the two. See `microwave_offered`.
_MICROWAVE_RULED_OUT = re.compile(r"\bnot with\b|\bwithout\b|\bexcept\b|\bno\b\s+microwave", re.I)


def microwave_from(lines: Iterable[str]) -> tuple[bool, str] | None:
    """`(True, the line that said so)` when a microwave is stated, else `None`.

    **Never returns `False`.** A page that does not mention a microwave is not a page
    saying there is none, and `microwave` defaults to `False` on the product, so
    returning `False` here would propose an unevidenced negative on every product.
    """
    if line := _first_match(usable_lines(lines), _MICROWAVE):
        return True, line
    return None


def microwave_offered(lines: Iterable[str]) -> str | None:
    """The line naming a microwave **even as an option**, or `None` if there is no mention.

    The difference from `microwave_from` is the option filter, which this deliberately
    skips. It exists so an adapter can tell *"nobody mentions a microwave"* from *"one is
    offered but not fitted"* — two facts a reviewer would act on differently, and the
    second is the commoner. Bailey list "Fitted microwave oven (Retailer fit)" and
    Niesmann sell an 800-watt one as a priced extra; on both, an absence note that said
    "no mention anywhere" would be untrue.

    A line that mentions a microwave only to rule it out is the last resort rather than
    the first: Murvi's options page offers one at £250 and, twenty lines earlier, an
    "Additional 60W solar panel (not with microwave oven)". Both are evidence that one is
    offered; only the first is worth quoting.
    """
    lines = list(lines)
    offering = [line for line in lines if not _MICROWAVE_RULED_OUT.search(line)]
    return _first_match(offering, _MICROWAVE) or _first_match(lines, _MICROWAVE)


# --- Bathroom ------------------------------------------------------------------------

#: The shower and toilet in separate compartments — the one bathroom fact that is stated
#: in words rather than needing a drawing. The requester, 6 September 2026: *"if the
#: bathroom is integrated with a shower and toilet together or has a clear separation
#: within one room […] or has two separate rooms with separate doors […] basically a
#: factual output of separated toilet and shower."*
#:
#: `separate` has to sit next to the shower or the toilet, not merely somewhere on the
#: line: "Rear twin single beds" pages also say "separate" about other things.
#:
#: **`separable` counts too**, which is Laika's word: *"Vario-bathroom with integrated
#: separable shower"* — one room in which a partition divides the shower off. That is
#: exactly the case the requester described as qualifying, *"a clear separation within one
#: room"*, so the distinction between a permanent wall and a movable one is not one FMLV
#: draws. `separat(e|ed|es|ing|ion|able)` all inflect from the same stem.
#: The separating word has to be **qualifying the shower or the toilet**, which means it
#: has to sit next to one. The window was 40 characters and spanned a comma, which let
#: Swift's "Washroom and shower tray with foldaway washbasin and black separate vanity
#: unit" read as a separated washroom: the word "separate" there belongs to the vanity
#: unit and the shower is a clause away. Fifteen characters and no comma still admits
#: every real phrasing seen — "separate cassette toilet", "separated from the toilet",
#: "toilet and separate shower", Laika's "separable shower".
_SEPARATE_BATHROOM = re.compile(
    r"\bsepara(?:te|ted|tes|ting|tion|ble)\b[^.,]{0,15}\b(?:shower|toilet|wc)\b"
    r"|\b(?:shower|toilet|wc)\b[^.,]{0,15}\bsepara(?:te|ted|tes|ting|tion|ble)\b",
    re.I,
)

#: A single wet space — shower over the toilet, no division. Rimor says "Wet room".
_WET_ROOM = re.compile(r"\bwet[- ]room\b|\bshower over (?:the )?toilet\b", re.I)

#: An external shower is not the vehicle's bathroom, and says nothing about its layout.
_EXTERNAL_SHOWER = re.compile(r"\bexternal\b[^.]{0,30}\bshower\b|\boutdoor shower\b", re.I)


def shower_toilet_separated_from(lines: Iterable[str]) -> Feature | None:
    """Whether a partition divides the shower from the toilet, or `None` if unsaid.

    This is a **separate fact from where the washroom is**, and not one of
    `BathroomLayout`'s values. The requester, 7 September 2026, on a Kilig 66 Plus
    proposed as `separate_shower_toilet` over a held `side_shower_toilet`: *"those are not
    mutually exclusive. The location is mutually exclusive. But if the type or the
    construction or layout of the shower and toilet is that it is separate, those are two
    values."* FMLV holds both together on 84 of its 1,590 motorhome rows.

    So the words answer this, and the floorplan answers the location — `bathroom_layout`
    is never proposed from prose. Reading "separate shower cubicle and cassette toilet" as
    a *location* was the bug: it overwrote a side washroom with a construction detail and
    lost the location a reviewer had set by hand.

    A wet room is the explicit negative — one space, shower over the toilet — so it
    returns `False` rather than nothing.
    """
    usable = [line for line in usable_lines(lines) if not _EXTERNAL_SHOWER.search(line)]
    if wet := _first_match(usable, _WET_ROOM):
        return Feature(value=False, snippet=wet, note="one wet space, undivided")
    if line := _first_match(usable, _SEPARATE_BATHROOM):
        return Feature(value=True, snippet=line, note="the copy says they are separated")
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

#: Fixed bed types that say more than `fixed_bed` does. **One bed takes one description,
#: the most specific that fits**, so a bed already recorded as one of these is not also
#: recorded as `fixed_bed` — the requester, 8 September 2026:
#:
#: > *"Transverse beds are always fixed, so that should go down as a transverse bed. If it
#: > is an island bed, so you can walk all the way around it and it's located in the
#: > centre, you would call it an island bed. If it is other than those two, and it is a
#: > fixed double bed, it would be a fixed bed. […] I don't want to double up and tick
#: > both transverse bed and fixed bed — it implies there are more beds than there are in
#: > the vehicle."*
#:
#: So `fixed_bed` is the **fallback** for a bed that is fixed but none of these, not a
#: general "this bed is fixed" flag. `bed_types` stays multi-select for a vehicle with
#: several beds; what it must not do is describe one bed twice and inflate the count.
_MORE_SPECIFIC_THAN_FIXED: frozenset[BedType] = frozenset(
    {BedType.TRANSVERSE, BedType.ISLAND, BedType.FIXED_SEPARATE, BedType.FIXED_BUNKS}
)

#: Where one bed's description ends and the next begins. Crude on purpose: it only has to
#: keep two beds named in one sentence from being read as one, and the copy reliably joins
#: them with a connective — "a rear double island bed, and an electric drop-down double
#: bed at the front".
_BED_CLAUSE = re.compile(r",|\band\b|\bplus\b|/|&")


def _fixed_is_covered_by_a_specific_type(lowered: str) -> bool:
    """True when every "fixed" wording on the line sits with a more specific type.

    Scoped per clause rather than per line, because a line usually describes more than one
    bed. "Rear fixed double transverse bed" is one bed and records `transverse_bed` alone;
    "fixed double bed and twin single beds" is two beds and keeps both types, since the
    fixed double is not the twins.

    Conservative where the wording is ambiguous: a single clause asserting fixedness with
    nothing more specific in it keeps `fixed_bed`, which is the fallback doing its job.
    """
    fixed_phrases = [p for p, bed_type in BED_PHRASES if bed_type is BedType.FIXED]
    specific = [p for p, bed_type in BED_PHRASES if bed_type in _MORE_SPECIFIC_THAN_FIXED]
    for clause in _BED_CLAUSE.split(lowered):
        if any(phrase in clause for phrase in fixed_phrases) and not any(
            phrase in clause for phrase in specific
        ):
            return False
    return True

#: A bed made up rather than permanently there. `lift` is here alongside the folding
#: words because it is the same claim in different clothes: Rimor's Horus 12 bed "lifts to
#: create more storage space for travel", so it is not standing made up.
_MAKE_UP = re.compile(
    r"\bconvert\w*\b|\bmakes? (?:up )?(?:into )?a?\s*(?:double|single|bed)"
    r"|\bmake[- ]up bed\b|\bfold[- ]?(?:s|ing)?[- ]away\b|\bpull[- ]out bed\b"
    r"|\blifts?\b|\blift[- ]up\b|\bstow\w*\b",
    re.I,
)

#: A bed named *as* the seating it is made from — "double bed rear dinette", "half dinette
#: bed", "settee bed". The same claim as `_MAKE_UP` with the verb left out, which is how
#: the trade usually writes it, and `_MAKE_UP` cannot catch it because there is no verb to
#: match. Rimor's Kilig 77 Plus is the case in point: "Consists of double bed rear
#: dinette, a front & rear drop-down bed", where the dinette double went unrecorded and
#: the requester supplied the answer on 8 September 2026 — *"the correct answer is a drop
#: down bed and a makeup bed."*
#:
#: Adjacency is what keeps this honest. The seating word has to follow the bed word
#: directly, allowing only a position word between, so "Rear drop-down bed above lounge"
#: and "Fixed rear double bed and a front lounge" do not match: in those the lounge is
#: where the bed is or what else the vehicle has, not what the bed is made from.
_SEATING_BED = re.compile(
    r"\bbeds?\b[\s&,]*(?:front|rear|side|centre|center|middle)?[\s&,]*"
    r"(?:dinette|lounge|settee)\b"
    r"|\b(?:dinette|lounge|settee)\s+beds?\b",
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
#:
#: **A door and a window are landmarks too**, and Swift's long lists are full of them:
#: "External service doors - access under nearside front bed and larger access door under
#: fixed beds" is about storage, and "Curtains to all windows (except kitchen, washroom
#: and bunk bed windows)" is about curtains. Read as beds they gave the Conqueror a fixed
#: bed and the Sprite bunks off lines describing neither.
#:
#: Lighting is deliberately **not** here: Dethleffs evidence the Globetrail 600 KS's bunks
#: with "Light strip on the underside of the upper bunk bed, on both sides", which is a
#: real statement that the bunks exist.
_NOT_A_BED = re.compile(
    r"\bdivider\b|\bstep for climbing\b|\bbed linen\b|\bmattress(?:es)?\b"
    r"|\b(?:service|access) doors?\b|\bcurtains?\b|\bblinds?\b|\bflyscreens?\b",
    re.I,
)


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
        if makes_up or _SEATING_BED.search(line):
            matches.append(BedType.MAKE_UP)
        # A shape is only credited when it is not merely what the seating turns into.
        # Keyed to the verb form alone: "Rear lounge which converts into single beds"
        # describes one arrangement, so the singles belong to the converted lounge. A line
        # naming a seating bed *among others* — "double bed rear dinette, a front & rear
        # drop-down bed" — is a list of distinct beds, and suppressing the drop-down there
        # would lose a type the copy plainly states.
        if not (makes_up and _SEATING.search(line)):
            for phrase, bed_type in BED_PHRASES:
                if phrase in lowered:
                    matches.append(bed_type)

        # One bed, one description — see `_MORE_SPECIFIC_THAN_FIXED`. Dropped last so the
        # more specific type is credited from whichever phrase named it.
        if BedType.FIXED in matches and _fixed_is_covered_by_a_specific_type(lowered):
            matches = [b for b in matches if b is not BedType.FIXED]

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

    if refrigeration := refrigeration_from(usable):
        features["refrigeration"] = refrigeration
    if found := heating_from(usable):
        features["heating"] = Feature(found[0], found[1])
    if found := microwave_from(usable):
        features["microwave"] = Feature(found[0], found[1])
    # Deliberately **not** `bathroom_layout`: that column holds the washroom's location,
    # which only a drawing can give. See `shower_toilet_separated_from`.
    if found := shower_toilet_separated_from(usable):
        features["shower_toilet_separated"] = found

    bed_types, quotes = bed_types_from(usable)
    if bed_types:
        features["bed_types"] = Feature(bed_types, " / ".join(quotes))
    return features


# --- Getting the lines off a page ----------------------------------------------------
#
# Almost every British manufacturer publishes its standard equipment the same way: an
# accordion of headed sections, each holding a plain `<ul>`, with an "Options" or
# "Optional upgrades" section among them. Only the markup differs, so the shape of the
# reading lives here with the vocabulary rather than being copied into each adapter.


@dataclass(frozen=True)
class Equipment:
    """A page's bulleted equipment, split by whether the vehicle actually has it.

    The split is **structural — by the section a line sits in — and it has to be.**
    `usable_lines` already discards a line that marks itself as an extra, and on some
    pages every extra does say so. On others none of them do: Bailey's Endeavour offers
    a "Pop-top roof to create additional high level double bed" and Swift's Sprite a
    "Lux Pack (microwave, carpet set, and TV aerial)", neither carrying a marker of any
    kind. Read as standard, the first gives a campervan an over-cab bed it has not got
    and the second a microwave. Reading the heading costs nothing and does not depend on
    a copywriter staying tidy.
    """

    standard: tuple[str, ...] = ()
    optional: tuple[str, ...] = ()


_LIST_ITEM = re.compile(r"<li\b[^>]*>(.*?)</li>", re.S)


def plain_text(fragment: str) -> str:
    """One list item or heading as a person reads it: no markup, no entities, one line."""
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def list_items(fragment: str, *, inside: re.Pattern[str] | None = None) -> list[str]:
    """Every `<li>` in `fragment`, as text.

    `inside` narrows it to lists in a particular container — pass one where a region
    holds navigation or breadcrumbs as well, which is the usual reason to need it. The
    pattern's **last group** is taken as the container's contents.
    """
    regions = [match.groups()[-1] for match in inside.finditer(fragment)] if inside else [fragment]
    return [text for region in regions for item in _LIST_ITEM.findall(region) if (text := plain_text(item))]


def sectioned_equipment(
    page: str,
    *,
    heading: re.Pattern[str],
    optional_heading: re.Pattern[str],
    inside: re.Pattern[str] | None = None,
    include_head: bool = False,
    until: re.Pattern[str] | None = None,
    items: Callable[[str], list[str]] | None = None,
) -> Equipment:
    """A page's headed equipment sections, split into what is fitted and what is offered.

    `heading` matches one section's heading and captures its text in group 1; each
    section runs from its own heading to the next. `optional_heading` decides which
    sections are upgrades rather than equipment. `include_head` also reads whatever
    sits above the first heading, which is where a brand may put a summary — Bailey
    state the washroom's shape only in theirs — and which needs `inside` to be set,
    since the head of a page is also where the navigation lives.

    `until` bounds the **last** section, which otherwise runs to the end of the document
    and swallows the page footer: Swift's "Newsletter", "Terms and Conditions", "Privacy"
    and "Site map" all arrived as equipment before this existed. Harmless where the last
    section is the options one, as it happens to be on every Swift page — and not
    something to leave resting on that.

    `items` replaces the default `<li>` reading, for a brand that bullets its equipment
    some other way. Elddis need it: their lists are `<p>` blocks of `•`-prefixed lines
    separated by `<br />`, with no list element anywhere on the page.
    """
    read = items or (lambda fragment: list_items(fragment, inside=inside))
    sections = list(heading.finditer(page))
    if not sections:
        return Equipment(tuple(dict.fromkeys(read(page))))

    end_of_page = len(page)
    if until and (edge := until.search(page, sections[-1].end())):
        end_of_page = edge.start()

    standard = read(page[: sections[0].start()]) if include_head else []
    optional: list[str] = []
    for index, section in enumerate(sections):
        end = sections[index + 1].start() if index + 1 < len(sections) else end_of_page
        body = page[section.end() : end]
        target = optional if optional_heading.match(plain_text(section.group(1))) else standard
        target.extend(read(body))
    return Equipment(tuple(dict.fromkeys(standard)), tuple(dict.fromkeys(optional)))
