"""Tests for the settled width rule that four adapters share.

`mirrors folded` is a label that means opposite things on the two body shapes, and getting
it wrong is silent — the figure is plausible, internally consistent and about 200mm too
wide. See `base.width_from_mirrors_folded` and `docs/adapters/README.md`.

No network here.
"""

from __future__ import annotations

import pytest

from src.adapters.base import width_from_mirrors_folded
from src.product_model.enums import BodyType

#: Every body type built on a panel van, where the folded mirrors are wider than the body.
PANEL_VANS = [
    BodyType.CAMPERVAN,
    BodyType.CAMPERVAN_ELEVATING_ROOF,
    BodyType.CAMPERVAN_HIGH_TOP,
    BodyType.CAMPERVAN_HIGH_TOP_ELEVATING_ROOF,
]

#: Every body type whose habitation body overhangs the mirrors.
BODIED = [
    BodyType.MICRO,
    BodyType.COACH_BUILT_LOW_PROFILE,
    BodyType.COACH_BUILT_OVER_CAB_BED,
    BodyType.A_CLASS,
]


def test_the_two_lists_cover_every_body_type() -> None:
    """A new body type must be classified deliberately, not fall through a default."""
    assert set(PANEL_VANS) | set(BODIED) == set(BodyType)


@pytest.mark.parametrize("body_type", PANEL_VANS)
def test_a_panel_van_records_nothing(body_type: BodyType) -> None:
    """A Ducato's body is about 2050mm against folded mirrors of about 2260mm.

    The requester's ruling, 12 September 2026: leave it blank rather than record a figure
    that includes the mirrors.
    """
    assert width_from_mirrors_folded(2260, body_type) is None


@pytest.mark.parametrize("body_type", BODIED)
def test_a_bodied_motorhome_records_the_figure(body_type: BodyType) -> None:
    """At 2350mm the habitation body overhangs the folded mirrors, so this is the body."""
    assert width_from_mirrors_folded(2350, body_type) == 2350


def test_an_unknown_body_type_keeps_the_figure() -> None:
    """A van has not been established, and blanking on a guess would lose a measurement."""
    assert width_from_mirrors_folded(2260, None) == 2260


def test_nothing_published_stays_nothing() -> None:
    assert width_from_mirrors_folded(None, BodyType.A_CLASS) is None
    assert width_from_mirrors_folded(None, BodyType.CAMPERVAN) is None
    assert width_from_mirrors_folded(None, None) is None


def test_the_four_brands_that_share_this_agree_on_it() -> None:
    """Benimar, Mobilvetta and Panama route their width through here; Elnagh has no van."""
    from src.adapters import benimar, elnagh, mclouis, mobilvetta, panama  # noqa: PLC0415

    for module in (benimar, mobilvetta, panama):
        assert "width_from_mirrors_folded" in module.__dict__

    # Elnagh and McLouis sell no panel van, so the question never arises for them.
    assert elnagh.BODY_TYPE not in PANEL_VANS
    assert mclouis.BODY_TYPE not in PANEL_VANS
