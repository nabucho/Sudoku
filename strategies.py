from __future__ import annotations

from typing import List

from techniques import (
    ALSXZ,
    ALSWing,
    AIC,
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
from techniques.common import Technique


def default_techniques() -> List[Technique]:
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
        Fish(3),   # Swordfish
        FinnedSwordfish(),
        XYWing(),
        Fish(4),   # Jellyfish
        FinnedJellyfish(),
        XYZWing(),
        XYChain(),
        EmptyRectangle(),
        UniqueRectangleType1(),
        UniqueRectangleType2(),
        UniqueRectangleType3(),
        UniqueRectangleType4(),
        AvoidableRectangle(),
        ALSXZ(),
        ALSWing(),
        XChain(),
        GroupedXChain(),
        AIC(),
        GroupedAIC(),
        BUGPlusOne(),
        Nishio(),
    ]


def fast_techniques() -> List[Technique]:
    return [
        HiddenSingle(),
        NakedSingle(),
        NakedSubset(2),
        LockedCandidates(),
        HiddenSubset(2),
    ]


def balanced_techniques() -> List[Technique]:
    return [
        HiddenSingle(),
        NakedSingle(),
        NakedSubset(2),
        LockedCandidates(),
        XYWing(),
        WWing(),
        HiddenSubset(2),
    ]


def techniques_for_strategy(strategy: str) -> List[Technique]:
    if strategy == "fastest":
        return fast_techniques()
    if strategy == "balanced":
        return balanced_techniques()
    return default_techniques()
