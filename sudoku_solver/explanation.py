"""Expand solver moves into display-ready explanation steps."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Sequence

from .techniques.common import (
    PEERS,
    Elimination,
    ExplanationStep,
    Move,
    Placement,
    SudokuState,
    bit,
    digits_from_mask,
    forced_cell_reason,
    is_single,
    placement_text,
    single_digit,
)


def explanation_steps(
    before: SudokuState,
    after: SudokuState,
    move: Move,
    detailed_steps: bool,
) -> list[ExplanationStep]:
    """Return explanation steps for one applied move.

    Args:
        before: State before applying the move.
        after: State after applying the move.
        move: Solver move that was applied.
        detailed_steps: When true, replay placements, eliminations, and
            propagations as atomic steps. When false, return a coarse summary.
    """
    if detailed_steps:
        return StepExpander(before, after, move).expanded_steps()
    return coarse_expanded_steps(before, after, move)


def coarse_expanded_steps(before: SudokuState, after: SudokuState, move: Move) -> list[ExplanationStep]:
    """Return a compact explanation step plus implied solved singles."""
    changed_cells = {
        cell
        for cell, (before_mask, after_mask) in enumerate(zip(before.candidates, after.candidates))
        if before_mask != after_mask
    }

    full_move = Move(
        technique=move.technique,
        difficulty=move.difficulty,
        reason=move.reason,
        placements=move.placements[:],
        eliminations=move.eliminations[:],
    )
    full_move.cause_cells = move.cause_cells[:]
    full_move.timing_ms = move.timing_ms

    known_eliminations = {(elimination.cell, elimination.digit) for elimination in full_move.eliminations}
    for cell, (before_mask, after_mask) in enumerate(zip(before.candidates, after.candidates)):
        removed_mask = before_mask & ~after_mask
        for digit in digits_from_mask(removed_mask):
            key = (cell, digit)
            if key not in known_eliminations:
                full_move.eliminations.append(Elimination(cell, digit))
                known_eliminations.add(key)

    steps = [ExplanationStep(full_move, after.candidates[:], sorted(changed_cells))]
    placed_cells = {placement.cell for placement in full_move.placements}

    for cell, (before_mask, after_mask) in enumerate(zip(before.candidates, after.candidates)):
        if cell in placed_cells:
            continue
        if not is_single(before_mask) and is_single(after_mask):
            digit = single_digit(after_mask)
            implied_move = Move(
                technique="Naked Single",
                difficulty=1,
                reason=forced_cell_reason(cell, digit),
                placements=[Placement(cell, digit)],
            )
            implied_move.timing_ms = 0.0
            steps.append(ExplanationStep(implied_move, after.candidates[:], [cell]))

    return steps


class StepExpander:
    """Replay one move to produce detailed explanation steps.

    The expander mirrors `SudokuState.apply_move()` but records intermediate
    placements, eliminations, propagated peer removals, and forced singles.
    If replay diverges from the already-applied state, it falls back to a
    coarse explanation so display remains correct.
    """

    def __init__(self, before: SudokuState, after: SudokuState, move: Move):
        """Initialize a replay from `before` toward `after` for `move`."""
        self.before = before
        self.after = after
        self.move = move
        self.replay = before.clone()
        self.steps: list[ExplanationStep] = []
        self.forced_queue = deque[tuple[int, int]]()
        self.queued_forced: set[int] = set()

    def expanded_steps(self) -> list[ExplanationStep]:
        """Replay the move and return detailed explanation steps."""
        for placement in self.move.placements:
            cell = placement.cell
            digit = placement.digit
            if not self.replay.can_place(cell, digit):
                return self.fallback()

            if not self.select_digit(cell, digit, self.move.technique, self.move.reason, self.move.difficulty):
                return self.fallback()

        if self.move.eliminations:
            if not self.eliminate_digits_group(
                self.move.eliminations,
                self.move.technique,
                self.move.reason,
                self.move.difficulty,
                self.move.cause_cells,
            ):
                return self.fallback()

        if not self.process_forced_singles():
            return self.fallback()

        if self.replay.candidates != self.after.candidates:
            return self.fallback()

        return self.steps

    def fallback(self) -> list[ExplanationStep]:
        """Return a safe coarse explanation when detailed replay cannot match."""
        return coarse_expanded_steps(self.before, self.after, self.move)

    def append_step(self, move: Move, changed_cells: Iterable[int]) -> None:
        """Append one display step using the replay state's current snapshot."""
        self.steps.append(ExplanationStep(move, self.replay.candidates[:], sorted(set(changed_cells))))

    def queue_forced_single(self, cell: int, difficulty: int) -> None:
        """Queue an unsolved singleton cell for forced placement explanation."""
        if (
            cell not in self.replay.fixed_cells
            and cell not in self.queued_forced
            and is_single(self.replay.candidate_mask(cell))
        ):
            self.forced_queue.append((cell, difficulty))
            self.queued_forced.add(cell)

    def process_forced_singles(self) -> bool:
        """Drain queued forced singles and record each placement."""
        while self.forced_queue:
            cell, difficulty = self.forced_queue.popleft()
            self.queued_forced.discard(cell)
            if cell in self.replay.fixed_cells or not is_single(self.replay.candidate_mask(cell)):
                continue
            if not self.select_forced_single(cell, difficulty):
                return False
        return True

    def propagate_digit(self, source_cell: int, digit: int, difficulty: int) -> bool:
        """Remove a placed digit from peers and record propagation changes."""
        eliminations: list[Elimination] = []
        for peer in sorted(PEERS[source_cell]):
            if not self.replay.can_place(peer, digit):
                continue

            new_mask = self.replay.candidate_mask(peer) & ~bit(digit)
            if new_mask == 0:
                return False

            self.replay.candidates[peer] = new_mask
            eliminations.append(Elimination(peer, digit))
            if is_single(new_mask):
                self.queue_forced_single(peer, difficulty)

        if eliminations:
            noun = "peer" if len(eliminations) == 1 else "peers"
            step = Move(
                technique="Propagation",
                difficulty=difficulty,
                reason=f"{placement_text(Placement(source_cell, digit))} removes {digit} from {len(eliminations)} {noun}.",
                eliminations=eliminations,
            )
            step.cause_cells = [source_cell]
            step.timing_ms = 0.0
            self.append_step(step, [elimination.cell for elimination in eliminations])

        return True

    def select_digit(self, cell: int, digit: int, technique: str, reason: str, difficulty: int) -> bool:
        """Record a placement, propagate it, and process new forced singles."""
        if not self.replay.can_place(cell, digit):
            return False

        self.replay.candidates[cell] = bit(digit)
        self.replay.fixed_cells.add(cell)
        step = Move(
            technique=technique,
            difficulty=difficulty,
            reason=reason,
            placements=[Placement(cell, digit)],
        )
        step.timing_ms = self.move.timing_ms if technique == self.move.technique else 0.0
        self.append_step(step, [cell])

        if not self.propagate_digit(cell, digit, difficulty):
            return False
        return self.process_forced_singles()

    def select_forced_single(self, cell: int, difficulty: int) -> bool:
        """Record a naked-single placement for a cell with one candidate."""
        digit = single_digit(self.replay.candidate_mask(cell))
        return self.select_digit(
            cell,
            digit,
            "Naked Single",
            forced_cell_reason(cell, digit),
            difficulty,
        )

    def eliminate_digits_group(
        self,
        eliminations: Sequence[Elimination],
        technique: str,
        reason: str,
        difficulty: int,
        cause_cells: Iterable[int] | None = None,
    ) -> bool:
        """Apply and record a group of candidate eliminations."""
        applied: list[Elimination] = []
        changed_cells: list[int] = []

        for elimination in eliminations:
            digit_mask = bit(elimination.digit)
            current_mask = self.replay.candidate_mask(elimination.cell)
            if not (current_mask & digit_mask):
                continue

            new_mask = current_mask & ~digit_mask
            if new_mask == 0:
                return False

            self.replay.candidates[elimination.cell] = new_mask
            applied.append(elimination)
            changed_cells.append(elimination.cell)
            if is_single(new_mask) and elimination.cell not in self.replay.fixed_cells:
                self.queue_forced_single(elimination.cell, difficulty)

        if applied:
            step = Move(
                technique=technique,
                difficulty=difficulty,
                reason=reason,
                eliminations=applied,
            )
            step.cause_cells = sorted(set(cause_cells or []))
            step.timing_ms = self.move.timing_ms if technique == self.move.technique else 0.0
            self.append_step(step, changed_cells)

        return True
