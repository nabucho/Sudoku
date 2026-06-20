from .aic import AIC, GroupedAIC, GroupedXChain, XChain
from .als import ALSXZ, ALSWing
from .basic import HiddenSingle, HiddenSubset, LockedCandidates, NakedSingle, NakedSubset
from .coloring import MultiColoring, SimpleColoring
from .fish import FinnedJellyfish, FinnedSwordfish, FinnedXWing, Fish
from .misc import SueDeCoq
from .single_digit_chains import EmptyRectangle, Skyscraper, TurbotFish, TwoStringKite
from .unique import (
    AvoidableRectangle,
    BUGPlusOne,
    Nishio,
    UniqueRectangleType1,
    UniqueRectangleType2,
    UniqueRectangleType3,
    UniqueRectangleType4,
)
from .wings import RemotePairs, WWing, XYChain, XYWing, XYZWing

__all__ = [
    "ALSXZ",
    "ALSWing",
    "AIC",
    "AvoidableRectangle",
    "BUGPlusOne",
    "EmptyRectangle",
    "FinnedJellyfish",
    "FinnedSwordfish",
    "FinnedXWing",
    "Fish",
    "GroupedAIC",
    "GroupedXChain",
    "HiddenSingle",
    "HiddenSubset",
    "LockedCandidates",
    "NakedSingle",
    "NakedSubset",
    "Nishio",
    "MultiColoring",
    "RemotePairs",
    "SimpleColoring",
    "Skyscraper",
    "SueDeCoq",
    "TurbotFish",
    "TwoStringKite",
    "UniqueRectangleType1",
    "UniqueRectangleType2",
    "UniqueRectangleType3",
    "UniqueRectangleType4",
    "WWing",
    "XChain",
    "XYChain",
    "XYWing",
    "XYZWing",
]
