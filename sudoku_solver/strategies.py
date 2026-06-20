"""Technique order definitions for solver strategies.

The strategy names and behavior here are documented in README.md and exposed
through the `--strategy` CLI option.
"""

from __future__ import annotations

from .techniques import (
    AIC,
    ALSXZ,
    ALSWing,
    AvoidableRectangle,
    BUGPlusOne,
    EmptyRectangle,
    FinnedJellyfish,
    FinnedSwordfish,
    FinnedXWing,
    Fish,
    GroupedAIC,
    GroupedXChain,
    HiddenSingle,
    HiddenSubset,
    LockedCandidates,
    MultiColoring,
    NakedSingle,
    NakedSubset,
    Nishio,
    RemotePairs,
    SimpleColoring,
    Skyscraper,
    SueDeCoq,
    TurbotFish,
    TwoStringKite,
    UniqueRectangleType1,
    UniqueRectangleType2,
    UniqueRectangleType3,
    UniqueRectangleType4,
    WWing,
    XChain,
    XYChain,
    XYWing,
    XYZWing,
)
from .techniques.common import Technique


def default_techniques() -> list[Technique]:
    """Return the full human-style logical technique order."""
    return [
        NakedSingle(),
        HiddenSingle(),
        LockedCandidates(),
        NakedSubset(2),
        HiddenSubset(2),
        NakedSubset(3),
        HiddenSubset(3),
        NakedSubset(4),
        HiddenSubset(4),
        Fish(2),   # X-Wing
        FinnedXWing(),
        SimpleColoring(),
        MultiColoring(),
        Skyscraper(),
        TwoStringKite(),
        TurbotFish(),
        WWing(),
        RemotePairs(),
        XYWing(),
        XYZWing(),
        XYChain(),
        EmptyRectangle(),
        Fish(3),   # Swordfish
        FinnedSwordfish(),
        UniqueRectangleType1(),
        UniqueRectangleType4(),
        UniqueRectangleType2(),
        UniqueRectangleType3(),
        SueDeCoq(),
        ALSXZ(),
        ALSWing(),
        XChain(),
        AIC(),
        GroupedAIC(),
        Fish(4),   # Jellyfish
        FinnedJellyfish(),
        AvoidableRectangle(),
        BUGPlusOne(),
        Nishio(),
        GroupedXChain(),
    ]


def human_fast_techniques() -> list[Technique]:
    """Return practical human-style techniques while skipping costly late methods."""
    return [
        NakedSingle(),
        HiddenSingle(),
        LockedCandidates(),
        NakedSubset(2),
        HiddenSubset(2),
        NakedSubset(3),
        HiddenSubset(3),
        NakedSubset(4),
        HiddenSubset(4),
        Fish(2),   # X-Wing
        FinnedXWing(),
        SimpleColoring(),
        MultiColoring(),
        Skyscraper(),
        TwoStringKite(),
        TurbotFish(),
        WWing(),
        RemotePairs(),
        XYWing(),
        XYZWing(),
        XYChain(),
        EmptyRectangle(),
        Fish(3),   # Swordfish
        FinnedSwordfish(),
        UniqueRectangleType1(),
        UniqueRectangleType4(),
        UniqueRectangleType2(),
        UniqueRectangleType3(),
        BUGPlusOne(),
    ]


def fast_techniques() -> list[Technique]:
    """Return the cheap technique order used by the `fastest` strategy."""
    return [
        NakedSingle(),
        HiddenSingle(),
        NakedSubset(2),
        LockedCandidates(),
        HiddenSubset(2),
    ]


def balanced_techniques() -> list[Technique]:
    """Return a fast order that adds low-cost guess-reducing techniques."""
    return [
        NakedSingle(),
        HiddenSingle(),
        NakedSubset(2),
        LockedCandidates(),
        XYWing(),
        WWing(),
        HiddenSubset(2),
    ]


def techniques_for_strategy(strategy: str) -> list[Technique]:
    """Return technique instances for a named solver strategy."""
    if strategy == "human-fast":
        return human_fast_techniques()
    if strategy == "fastest":
        return fast_techniques()
    if strategy == "balanced":
        return balanced_techniques()
    return default_techniques()
