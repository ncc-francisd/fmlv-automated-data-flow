"""The automatic-gearbox vocabulary.

Every "real wording" quoted here was taken from a snapshot in `data/snapshots`, and the
false-positive guards are the phrasings that a bare search for the word `automatic` was
found to trip over in the same sweep.
"""

from __future__ import annotations

import pytest

from src.adapters.gearbox import automatic_available_from


# --- Found, from the manufacturer's own words ---------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        # Real snapshot wordings, one per shape the regexes allow.
        "180 HP - 8-speed automatic - 4 cylinder - 2,200 ccm",
        "2.2-litre 180 hp engine - automatic transmission - 4.5 T Al-Ko chassis",
        "Built on a Ford Transit with a 2.0L, 165bhp engine and 8-speed automatic gearbox",
        "180bhp Euro 6E Fiat Ducato engine with 8 speed Automatic transmission",
        "Automatic 8 speed gearbox available as a cost option",
        "Transmission 9G Tronic automatic transmission",
        "9G-TRONIC automatic transmission",
        "8G automatic torque converter",
        "Gearbox: automatic",
    ],
)
def test_a_cited_automatic_is_found(line: str) -> None:
    assert automatic_available_from([line]) == (True, line)


@pytest.mark.parametrize(
    "line",
    [
        "IVECO Daily 3.0 Hi-Matic",
        "Fiat Ducato 2.3 Comfort-Matic",
        "Peugeot Boxer BlueHDi EAT8",
        "Ford Transit 2.0 EcoBlue PowerShift",
        "Volkswagen Crafter 2.0 TDI DSG",
    ],
)
def test_a_chassis_makers_trade_name_is_enough_on_its_own(line: str) -> None:
    """These name no gearbox word — the name is the claim, and a brochure often prints
    nothing else."""
    assert automatic_available_from([line]) == (True, line)


@pytest.mark.parametrize(
    "line",
    [
        "Boite automatique 9 rapports",
        "Boîte automatique",
        "Automatikgetriebe",
        "Cambio automatico",
    ],
)
def test_the_claim_is_read_in_the_languages_the_sources_use(line: str) -> None:
    assert automatic_available_from([line]) == (True, line)


def test_an_option_counts_where_habitation_would_discard_it() -> None:
    """The one rule this module deliberately does not share with `habitation`.

    An automatic is a priced factory option on almost every chassis FMLV holds, so the
    question is whether one can be had, not what the base price includes. Reading these
    through `habitation.usable_lines` would discard all three.
    """
    for line in (
        "Optional 9-speed fully automatic gearbox*",
        "Automatic gearbox option: £2,450",
        "Powerful, smooth and safe with optional automatic gearbox as a cost option.",
    ):
        assert automatic_available_from([line]) == (True, line)


# --- Ruled out, explicitly ----------------------------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        "Automatic transmission not available on this model",
        "Automatic gearbox unavailable",
        "Not available as an automatic",
        "Manual gearbox only",
        "Manual only",
        "No automatic option",
    ],
)
def test_an_explicit_denial_is_recorded_as_no(line: str) -> None:
    assert automatic_available_from([line]) == (False, line)


def test_a_denial_beats_a_citation_anywhere_on_the_page() -> None:
    """Checked across every line before any positive is, so a page that offers an
    automatic on one layout and rules it out on this one is not read as a Yes."""
    lines = [
        "8-speed automatic gearbox across the range",
        "Automatic transmission not available on this model",
    ]
    assert automatic_available_from(lines) == (False, lines[1])


def test_naming_the_manual_is_not_a_denial() -> None:
    """Almost every chassis in FMLV is a manual as standard with an automatic offered,
    so reading this as `No` would turn the commonest sentence in the industry into a
    wrong negative."""
    assert automatic_available_from(["6-speed manual gearbox"]) is None
    assert automatic_available_from(["Transmission: 6 speed manual"]) is None


# --- Silence, and the words that only look like the answer --------------------------


@pytest.mark.parametrize(
    "line",
    [
        "141L fridge with automatic energy selection (AES)",
        "Dometic 3-way fridge with AES automatic energy selection",
        "Automatic gas changeover regulator",
        "Truma Combi 4 heating with automatic ignition",
        "Automatic levelling jacks",
        "Automatic satellite dish",
        "Automatic headlights and rain-sensing wipers",
        "Automatic air conditioning",
        "Automatic battery charger",
        "Rear lounge converts to a dinette to eat 6",
    ],
)
def test_the_word_automatic_elsewhere_in_the_spec_is_not_a_gearbox(line: str) -> None:
    """A motorhome specification is full of the word. Every pattern demands a gearbox
    word beside it or a trade name, which is why none of these fires."""
    assert automatic_available_from([line]) is None


def test_a_page_that_never_raises_the_subject_returns_nothing() -> None:
    """`None`, not `False` — silence is not a negative. The whole reason the field has
    three states."""
    assert automatic_available_from(["Berths 4", "Length 7,000 mm", "Payload 575 kg"]) is None
    assert automatic_available_from([]) is None


def test_metadata_lines_are_not_read_as_specification() -> None:
    """`Tags` and `Categories` repeat words out of context — the same exclusion
    `habitation` makes."""
    assert automatic_available_from(["Tags 687TC, rimor, automatic gearbox"]) is None


def test_the_line_that_justified_it_comes_back_whole() -> None:
    """It becomes the provenance snippet a reviewer reads, so it is the manufacturer's
    own wording rather than the matched fragment."""
    found = automatic_available_from(["  Optional   9-speed fully automatic gearbox*  "])
    assert found == (True, "Optional 9-speed fully automatic gearbox*")
