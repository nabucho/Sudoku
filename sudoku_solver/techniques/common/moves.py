"""Move, explanation, and timing models shared by the solver."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Sequence

from .grid import cell_text
from .types import CellDigit, EliminationKey, SourceDigitRole, SourceDigitRoles


@dataclass(frozen=True)
class Placement:
    """A solved digit placement produced by a technique or guess."""

    cell: int
    digit: int


@dataclass(frozen=True)
class Elimination:
    """A candidate removal produced by a technique or propagation."""

    cell: int
    digit: int


@dataclass
class TechniqueTiming:
    """Aggregated timing counters for a solving technique."""

    attempts: int = 0
    successes: int = 0
    used: int = 0
    total_ms: float = 0.0
    successful_ms: float = 0.0

    def record_run(self, elapsed_ms: float, successful: bool) -> None:
        """Record one technique attempt and whether it found at least one move."""
        self.attempts += 1
        self.total_ms += elapsed_ms
        if successful:
            self.successes += 1
            self.successful_ms += elapsed_ms

    def record_use(self) -> None:
        """Record that a found move from this technique was selected."""
        self.used += 1

    @property
    def average_ms(self) -> float:
        return self.total_ms / self.attempts if self.attempts else 0.0

    @property
    def success_percent(self) -> float:
        return (self.successes / self.attempts * 100.0) if self.attempts else 0.0


def placement_text(placement: Placement) -> str:
    return f"{cell_text(placement.cell)}={placement.digit}"


def elimination_text(elimination: Elimination) -> str:
    return f"{cell_text(elimination.cell)}!={elimination.digit}"


def source_digit_roles_for_cells(
    cells: Iterable[int],
    digits: Iterable[int],
    role: SourceDigitRole = "primary",
) -> SourceDigitRoles:
    """Return source-digit metadata for every cell/digit combination."""
    return {
        (cell, digit): role
        for cell in cells
        for digit in digits
    }


@dataclass
class Move:
    """A logical solver action before it is expanded for display.

    Techniques return moves containing placements, eliminations, explanatory
    text, difficulty, and cause cells. Rendering-specific state such as board
    snapshots belongs to :class:`ExplanationStep`.
    """

    technique: str
    reason: str
    placements: List[Placement] = field(default_factory=list)
    eliminations: List[Elimination] = field(default_factory=list)
    difficulty: int = 0
    cause_cells: List[int] = field(default_factory=list, repr=False)
    source_digit_roles: SourceDigitRoles = field(default_factory=dict, repr=False)
    timing_ms: float = field(default=0.0, repr=False)

    def summary(self) -> str:
        if self.reason.startswith(f"{self.technique}:"):
            return self.reason
        return f"{self.technique}: {self.reason}"


def elimination_key(eliminations: Sequence[Elimination], *, sorted_key: bool = False) -> EliminationKey:
    """Return a typed, hashable key for a sequence of eliminations."""
    pairs = ((elimination.cell, elimination.digit) for elimination in eliminations)
    return tuple[CellDigit, ...](sorted(pairs) if sorted_key else pairs)


@dataclass
class ExplanationStep:
    """A display-ready step with board snapshot metadata.

    Explanation steps wrap a :class:`Move` and add the candidate grid state
    after applying that step plus the cells changed by the step.
    """

    move: Move
    after_candidates: List[int] | None = field(default=None, repr=False)
    changed_cells: List[int] = field(default_factory=list, repr=False)

    @property
    def technique(self) -> str:
        return self.move.technique

    @property
    def reason(self) -> str:
        return self.move.reason

    @property
    def placements(self) -> List[Placement]:
        return self.move.placements

    @property
    def eliminations(self) -> List[Elimination]:
        return self.move.eliminations

    @property
    def difficulty(self) -> int:
        return self.move.difficulty

    @property
    def cause_cells(self) -> List[int]:
        return self.move.cause_cells

    @property
    def source_digit_roles(self) -> SourceDigitRoles:
        return self.move.source_digit_roles

    @property
    def timing_ms(self) -> float:
        return self.move.timing_ms

    def summary(self) -> str:
        return self.move.summary()
