"""The habitation fields the pipeline **reports on** rather than proposes.

A finding says *"here is what a deep read of the manufacturer's copy found, and here is
the line it found it in"*. It is not a proposal: nothing accepts it, nothing rejects it,
and it never reaches an upload CSV. A person reads it and types the value into FMLV
themselves.

## Why these fields left the decision flow

Every field here was, until 9 September 2026, an ordinary proposal — and the habitation
group was the one part of the review that kept going wrong:

* `bathroom_layout` and `bed_types` are **lists**, so "nothing found" is `[]` rather than
  `None`, and `diff.compare` read that as a proposal to *delete* the value. An Eriba
  Touring 430 lost its `side_shower_toilet` and a Dethleffs Alpa A 6820-2 lost its
  `fixed_separate_beds` that way, both to a reviewer pressing Accept on what read as a
  confirmation. Both reached real uploads.
* The washroom's location, the kitchen's, the lounge's and which end the beds are at are
  **only in the drawing**. A dropdown per field per product, all pointing at one
  floorplan, is a lot of clicks to record something the reviewer read in one glance.
* Refrigeration, heating and the microwave are in the copy but *thinly* — a fridge's
  litres with no word about a freezer, a heater's kilowatts with no word about whether it
  is blown air or wet. A confirm-or-replace row on those asks a reviewer to arbitrate
  evidence the adapter has already shown them.

The requester's ruling, 9 September 2026: *"it would be simpler to take out the
habitation questions that we've been trying to integrate into the reviewer […] an
additional line, not to accept or reject, but simply to state a finding, would be to list
the factual things that you've been able to find with a really deep scan of the website
[…] you could put the source, and it could take you to that copy, but we could leave it
to humans to add those elements to the CSV."*

## What stayed a proposal

`twin_axle` and `rear_garage`, deliberately. Both are stated plainly and unambiguously in
a specification — an axle count and a garage's opening size — and both are single
booleans with no list to go empty. The requester, the same day: *"did I mention rear
garage? I think that's like twin axle. But for motor homes, I assume you would still
include that as part of the spec and not as other items we found."* So is `body_type`,
which is derived from a published height and segment rather than read off a drawing.

## New products only

Findings are recorded for a **new** product, never a matched one. A model FMLV already
holds carries its own habitation values across untouched, so there is nothing for a
person to type and a finding would be noise on every product every run. The requester:
*"your findings about those areas like heating, microwave and fridges only need to apply
to what are identified as new models. We will keep and retain the existing values for
existing models."*

The floorplan pointer is the exception — it is recorded for every product, new or
matched, because a reviewer working any product may want to see the layout.
"""

from __future__ import annotations

#: Reported as findings, never proposed. `store.changes` records them and
#: `diff.compare` skips them, so a matched product gets no row for any of them at all.
FINDING_FIELDS: tuple[str, ...] = (
    "bed_types",
    "bathroom_layout",
    "shower_toilet_separated",
    "sleeping_area",
    "kitchen_location",
    "lounge_location",
    "heating",
    "refrigeration",
    "microwave",
)


#: The one finding that is a pointer rather than a value: the layout drawing, which
#: answers every positional field at once. Not a `Motorhome`/`Caravan` field name — it is
#: about the product, not one column of it — which is why it is spelled unlike the rest
#: and why nothing downstream may treat it as a field path.
FLOORPLAN_FIELD = "floorplan"


#: What a person reads the drawing for, when the adapter found nothing else to say. One
#: sentence rather than the five per-field pointers this replaced, because a reviewer
#: opens the drawing once and reads the whole layout off it.
FLOORPLAN_SNIPPET = (
    "The layout drawing. Read off it which end the beds are at, whether the kitchen is "
    "rear, side or corner, whether the lounge is front, rear or twin, what the washroom "
    "is and whether it is rear or side, and which beds are built in rather than made up "
    "from the seating."
)


#: How each finding is headed in the review. Named for what a person is looking for
#: rather than for the FMLV column, since the column names read as jargon in a list of
#: plain statements.
FINDING_LABELS: dict[str, str] = {
    FLOORPLAN_FIELD: "Floorplan",
    "microwave": "Microwave",
    "refrigeration": "Refrigeration",
    "heating": "Heating",
    "bed_types": "Bed types",
    "bathroom_layout": "Washroom",
    "shower_toilet_separated": "Shower and toilet separated",
    "sleeping_area": "Sleeping area",
    "kitchen_location": "Kitchen",
    "lounge_location": "Lounge",
}


#: What a finding states when the adapter read the copy and the copy said nothing. Only
#: the microwave has one, and only because the requester ruled that silence is an answer
#: there — 9 September 2026: *"it should probably just recommend no, and say we couldn't
#: find any evidence or mention of a microwave, and I would just default to accepting a
#: no."* Safe here in a way it would not be as a proposal: a finding writes nothing, and
#: the note below says exactly what the recommendation rests on.
#:
#: Every other field keeps the project's rule that silence is not a negative — a page
#: that never mentions a freezer is not a page saying there is none.
SILENCE_MEANS: dict[str, tuple[str, str]] = {
    "microwave": (
        "False",
        "No mention of a microwave was found anywhere in the specification, so the "
        "recommendation is No.",
    ),
}


def is_finding_field(field: str) -> bool:
    """Whether the pipeline reports `field` instead of proposing a value for it."""
    return field in FINDING_FIELDS


def finding_label(field: str) -> str:
    """`field` as a person reads it in the findings list."""
    return FINDING_LABELS.get(field, field.replace("_", " "))
