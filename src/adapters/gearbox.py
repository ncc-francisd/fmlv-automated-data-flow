"""Whether a model is offered with an automatic gearbox, read from a maker's own spec prose.

`automatic_available` joined the FMLV upload template on 3 November 2026 — column BN,
inserted ahead of `latest_model_id`. The requester's brief, the same day:

    simply if an automatic version is cited in the source website, or the PDF, that we
    enter the value yes, and if it isn't, or it's specifically isn't, then we enter the
    value no […] where you can't tell, you would leave it blank.

So this returns **three states**, and the blank one carries the weight. `True` where an
automatic is cited, `False` where the source rules one out, and `None` — no return at all
— where the page never raises the subject. Most manufacturers' pages never do.

This lives beside `habitation` rather than inside it because a gearbox is not a
habitation feature: it belongs to the base vehicle, and the vocabulary is the chassis
makers' own. Everything else about the two modules is the same, including the two rules
that matter most:

* **Only ever assert from positive evidence.** Silence is not a negative, exactly as in
  `habitation` and in `docs/adapters/README.md` on unfound figures. Writing `No` wherever
  a site says nothing would put a negative on roughly sixty brands on the strength of
  nobody having looked — and FMLV's own data argues against it: Rimor's first export under
  the new template carries `Yes` on all 39 rows and `No` on none.

* **An option still counts.** This is where it parts company with `habitation`, and the
  difference is not a detail. Every other field that module reads is wrong if it reports a
  paid extra as fitted, so `_OPTION` filters those lines out before anything sees them.
  Here the paid extra *is* the answer: an automatic is a factory option on almost every
  Ducato ever bodied, and the question asked is whether one can be had, not what is fitted
  to the base price. Lines this module reads are therefore deliberately **unfiltered**.

**`automatic` on its own is worthless** and the regexes never use it. A motorhome
specification is full of the word: automatic energy selection on a Dometic fridge,
automatic ignition on a hob, automatic gas changeover, automatic levelling jacks, an
automatic satellite dish, automatic headlights, automatic air conditioning. Every pattern
below therefore demands either a gearbox word beside it or a chassis maker's trade name
for one, which is the whole reason this is a vocabulary and not a keyword search.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

#: A chassis maker's own name for its automatic. These need no gearbox word beside them —
#: the name *is* the claim — and a brochure very often prints nothing else.
#:
#: Collected from the base vehicles this project actually meets: Fiat's `Comfort-Matic`
#: and the ZF nine-speed that replaced it, IVECO's `Hi-Matic`, Mercedes' `7G-Tronic` and
#: `9G-Tronic`, Ford's `PowerShift` and `SelectShift`, VW's `DSG`, and Peugeot/Citroën's
#: `EAT8`.
#:
#: **`EAT8` is matched without a space on purpose.** Allowing one would make `eat 6` a
#: match, and "a dinette to eat 6" is ordinary copy on a floorplan page.
_TRADE_NAME = (
    r"\bcomfort\s?-?\s?matic\b|\bhi\s?-?\s?matic\b"
    r"|\b[79]\s?g\s?-?\s?tronic\b|\bpowershift\b|\bselect\s?shift\b"
    r"|\beat[68]\b|\btiptronic\b|\bdsg\b"
)

#: The gearbox itself, named as automatic. Each alternative pins the word `automatic` to a
#: transmission word or a speed count, so the fridge and the hob cannot reach it.
_AUTOMATIC_BOX = (
    r"\bautomatic\s+(?:gear\s?box|transmission|gears)\b"
    r"|\b(?:gear\s?box|transmission)\s*[:\-]?\s*automatic\b"
    r"|\bauto(?:matic)?\s+gear\s?box\b"
    r"|\b\d+\s?-?\s?speed\s+automatic\b"
    r"|\bautomatic\s+\d+\s?-?\s?speed\b"
    r"|\bautomated\s+manual\b|\btorque\s+converter\b"
)

#: The same claim in the languages this project's sources are actually written in — Pilote,
#: Rapido, Fleurette, Joa and Globe-Traveller all publish in French, and the German and
#: Italian makers' English pages sometimes leave the term untranslated.
_AUTOMATIC_FOREIGN = (
    r"\bbo[iî]te\s+automatique\b|\btransmission\s+automatique\b"
    r"|\bautomatikgetriebe\b|\bcambio\s+automatico\b"
)

_AUTOMATIC = re.compile(
    f"{_AUTOMATIC_BOX}|{_AUTOMATIC_FOREIGN}|{_TRADE_NAME}", re.I
)

#: A source settling the question the other way. Rare — most pages simply say nothing, and
#: that is `None`, not this — so every alternative here is an explicit denial rather than
#: an inference.
#:
#: **"6-speed manual" is deliberately not here.** Naming the standard gearbox says nothing
#: about what the options list offers, and almost every chassis in FMLV is a manual as
#: standard with an automatic available. Reading it as a denial would turn the commonest
#: sentence in the industry into a wrong `No`.
_NO_AUTOMATIC = re.compile(
    r"\bno\s+automatic\s+(?:gear\s?box|transmission|option|version)?\b"
    r"|\bautomatic\s*(?:gear\s?box|transmission)?\s*(?:is\s+)?(?:not\s+available|unavailable)\b"
    r"|\bnot\s+available\s+(?:as|with|in|on)\s+(?:an?\s+)?automatic\b"
    r"|\bmanual\s+(?:gear\s?box|transmission)\s+only\b"
    r"|\bmanual\s+only\b"
    r"|\bonly\s+available\s+(?:as|with)\s+(?:a\s+)?manual\b",
    re.I,
)

#: The `Tags` and `Categories` metadata lines, which repeat words out of context. Same
#: exclusion `habitation` makes, for the same reason.
_METADATA = re.compile(r"^\s*(tags|categories)\b", re.I)


def _candidates(lines: Iterable[str]) -> list[str]:
    """Every line worth reading — collapsed whitespace, metadata dropped, options kept."""
    cleaned = (" ".join(str(line).split()) for line in lines)
    return [line for line in cleaned if line and not _METADATA.match(line)]


def automatic_available_from(lines: Iterable[str]) -> tuple[bool, str] | None:
    """`(available, the line that said so)`, or `None` where the source never says.

    A denial is looked for **first and across every line**, so that "automatic gearbox not
    available on this layout" is read as the `No` it is rather than matched as a `Yes` by
    the words it contains.
    """
    candidates = _candidates(lines)
    for line in candidates:
        if _NO_AUTOMATIC.search(line):
            return False, line
    for line in candidates:
        if _AUTOMATIC.search(line):
            return True, line
    return None


#: Everything that is not prose: scripts, styles, and the no-script fallback.
_NOT_PROSE = re.compile(r"(?is)<(script|style|noscript)\b.*?</\1>")

#: The tags that end a line of displayed text. Splitting on these keeps a gearbox out of
#: the sentence that follows it in the markup.
_LINE_BREAK = re.compile(r"(?is)<br\s*/?>|</(?:p|div|li|tr|h[1-6]|td|th|ul|ol|span)>")

_TAG = re.compile(r"<[^>]+>")


def lines_from_page(page: str) -> list[str]:
    """Every line of displayed text on an HTML page, for the gearbox vocabulary to read.

    **Deliberately the whole page, not the habitation lines.** The two live in different
    places and assuming otherwise gets nothing: Globe-Traveller print `Automatic gearbox`
    twelve times on a model page and not once in the specification table that
    `habitation_lines` reads, because the gearbox belongs to the base vehicle and the
    table describes the conversion. Across the 551 snapshots this vocabulary was built
    against, the wording turned up in an options list, a chassis paragraph, a marketing
    sentence and a technical table in roughly equal measure.

    Reading the whole page is only safe because the vocabulary is narrow — see this
    module's docstring on why `automatic` alone is never matched. A page-wide search for
    that word would be useless; a page-wide search for `8-speed automatic` is not.
    """
    text = _NOT_PROSE.sub(" ", page)
    return _candidates(_TAG.sub(" ", chunk) for chunk in _LINE_BREAK.split(text))


def provenance_note(found: tuple[bool, str]) -> str:
    """The sentence a reviewer reads beside the field, with the maker's line quoted.

    One wording for every adapter, so a reviewer who has accepted this field on one brand
    recognises it on the next and does not have to work out whether a differently-phrased
    note means something different.
    """
    available, line = found
    lead = (
        "An automatic version is offered"
        if available
        else "An automatic version is ruled out"
    )
    return f"{lead}: {line}"
