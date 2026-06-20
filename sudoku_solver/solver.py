"""Library API for solving Sudoku puzzles."""

from __future__ import annotations

import time

from .explanation import explanation_steps
from .strategies import techniques_for_strategy
from .techniques.common import (
    ALL_UNITS,
    CELL_INDICES,
    DIGIT_VALUES,
    PEERS,
    ExplanationStep,
    Move,
    Placement,
    SudokuState,
    Technique,
    TechniqueTiming,
    bit,
    bit_count,
    cell_text,
    is_single,
    single_digit,
    unsolved_cells,
)

MoveScore = tuple[int, int, int, int, int, str, str]


class SudokuSolver:
    """Coordinate technique selection, timing, logical solving, and search.

    Args:
        techniques: Optional explicit technique order. When omitted, the order
            is chosen from `strategy`.
        strategy: Strategy name used by `strategies.techniques_for_strategy`.
    """

    def __init__(self, techniques: list[Technique] | None = None, strategy: str = "human"):
        self.strategy = strategy
        self.timing_stats: dict[str, TechniqueTiming] = {}
        if techniques is not None:
            self.techniques = techniques
        else:
            self.techniques = techniques_for_strategy(strategy)

    def reset_timing(self) -> None:
        """Clear all recorded technique timing counters."""
        self.timing_stats = {}

    def _timing_for(self, technique_name: str) -> TechniqueTiming:
        """Return the mutable timing aggregate for a technique name."""
        if technique_name not in self.timing_stats:
            self.timing_stats[technique_name] = TechniqueTiming()
        return self.timing_stats[technique_name]

    def _find_moves_timed(self, technique: Technique, state: SudokuState) -> list[Move]:
        """Run a technique, recording elapsed time and success statistics."""
        start = time.perf_counter()
        moves = technique.find_moves(state)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        successful = bool(moves)

        self._timing_for(technique.name).record_run(elapsed_ms, successful)
        for move in moves:
            move.timing_ms = elapsed_ms
        return moves

    def _record_move_use(self, move: Move) -> Move:
        """Record that a selected move was actually used."""
        self._timing_for(move.technique).record_use()
        return move

    def _record_implied_step_uses(self, before: SudokuState, after: SudokuState, move: Move) -> None:
        """Record display-only propagation and forced-single steps."""
        selected_placements = {(placement.cell, placement.digit) for placement in move.placements}
        for step in explanation_steps(before, after, move, detailed_steps=True):
            if step.technique == "Propagation" and step.eliminations:
                timing = self._timing_for("Propagation")
                timing.record_run(0.0, True)
                timing.record_use()
            elif step.technique == "Naked Single":
                placements = {(placement.cell, placement.digit) for placement in step.placements}
                if placements and not placements <= selected_placements:
                    timing = self._timing_for("Naked Single")
                    timing.record_run(0.0, True)
                    timing.record_use()

    def _record_guess_run(self, move: Move, elapsed_ms: float, successful: bool) -> None:
        """Record timing for one speculative MRV guess."""
        move.timing_ms = elapsed_ms
        timing = self._timing_for(move.technique)
        timing.record_run(elapsed_ms, successful)
        if successful:
            timing.record_use()

    def next_move(self, state: SudokuState) -> Move | None:
        """Pick the next logical move according to the configured strategy."""
        if self.strategy == "fewest-steps":
            return self._highest_impact_move(state)

        for technique in self.techniques:
            moves = self._find_moves_timed(technique, state)
            if moves:
                return self._record_move_use(self._best_move(state, moves))
        return None

    def _best_move(self, state: SudokuState, moves: list[Move]) -> Move:
        """Choose the most useful move from one technique result set."""
        before_solved, before_candidates = self._candidate_totals(state.candidates)
        scored_moves = [
            (score, move)
            for move in moves
            if (score := self._move_score(state, move, before_solved, before_candidates)) is not None
        ]
        if not scored_moves:
            return min(
                moves,
                key=lambda move: (
                    -len(move.placements) - len(move.eliminations),
                    move.difficulty,
                    move.technique,
                    move.reason,
                ),
            )
        return max(scored_moves, key=lambda item: item[0])[1]

    def _candidate_totals(self, candidates: list[int]) -> tuple[int, int]:
        """Return solved-cell and total-candidate counts."""
        return (
            sum(1 for mask in candidates if is_single(mask)),
            sum(bit_count(mask) for mask in candidates),
        )

    def _move_score(
        self,
        state: SudokuState,
        move: Move,
        before_solved: int,
        before_candidates: int,
    ) -> MoveScore | None:
        """Return a deterministic board-impact score for a candidate move."""
        candidates = state.candidates[:]
        if not self._apply_move_to_candidates(candidates, move):
            return None

        after_solved, after_candidates = self._candidate_totals(candidates)

        return (
            after_solved - before_solved,
            before_candidates - after_candidates,
            len(move.placements),
            len(move.eliminations),
            -move.difficulty,
            move.technique,
            move.reason,
        )

    def _apply_move_to_candidates(self, candidates: list[int], move: Move) -> bool:
        """Apply a move to candidate masks without cloning a full SudokuState."""
        for placement in move.placements:
            if not self._place_digit_in_candidates(candidates, placement.cell, placement.digit):
                return False

        for elimination in move.eliminations:
            if not self._eliminate_digit_from_candidates(candidates, elimination.cell, elimination.digit):
                return False

        return self._candidates_consistency_ok(candidates)

    def _eliminate_digit_from_candidates(self, candidates: list[int], cell: int, digit: int) -> bool:
        """Remove one candidate from a local candidate-mask list."""
        digit_mask = bit(digit)
        current_mask = candidates[cell]
        if not (current_mask & digit_mask):
            return True

        new_mask = current_mask & ~digit_mask
        if new_mask == 0:
            return False

        candidates[cell] = new_mask
        if is_single(new_mask):
            fixed_digit = single_digit(new_mask)
            fixed_mask = bit(fixed_digit)
            for peer in PEERS[cell]:
                if candidates[peer] & fixed_mask:
                    if not self._eliminate_digit_from_candidates(candidates, peer, fixed_digit):
                        return False
        return True

    def _place_digit_in_candidates(self, candidates: list[int], cell: int, digit: int) -> bool:
        """Place a digit in a local candidate-mask list."""
        digit_mask = bit(digit)
        if not (candidates[cell] & digit_mask):
            return False

        current_digits = [
            candidate_digit
            for candidate_digit in DIGIT_VALUES
            if candidates[cell] & bit(candidate_digit)
        ]
        for candidate_digit in current_digits:
            if candidate_digit != digit:
                if not self._eliminate_digit_from_candidates(candidates, cell, candidate_digit):
                    return False

        for peer in PEERS[cell]:
            if candidates[peer] & digit_mask:
                if not self._eliminate_digit_from_candidates(candidates, peer, digit):
                    return False
        return True

    def _candidates_consistency_ok(self, candidates: list[int]) -> bool:
        """Return whether local candidate masks satisfy Sudoku invariants."""
        if any(mask == 0 for mask in candidates):
            return False

        for unit in ALL_UNITS:
            seen_fixed: set[int] = set()
            for cell in unit:
                mask = candidates[cell]
                if is_single(mask):
                    digit = single_digit(mask)
                    if digit in seen_fixed:
                        return False
                    seen_fixed.add(digit)

            for digit in DIGIT_VALUES:
                digit_mask = bit(digit)
                if not any(candidates[cell] & digit_mask for cell in unit):
                    return False
        return True

    def _highest_impact_move(self, state: SudokuState) -> Move | None:
        """Evaluate all logical moves and return the one with best impact."""
        best_move: Move | None = None
        best_score: MoveScore | None = None
        before_solved, before_candidates = self._candidate_totals(state.candidates)

        for technique in self.techniques:
            for move in self._find_moves_timed(technique, state):
                score = self._move_score(state, move, before_solved, before_candidates)
                if score is None:
                    continue

                if best_score is None or score > best_score:
                    best_score = score
                    best_move = move

        return self._record_move_use(best_move) if best_move is not None else None

    def _has_unprocessed_singles(self, state: SudokuState) -> bool:
        """Return whether solved cells still need explanation as singles."""
        return any(
            is_single(state.candidate_mask(cell)) and cell not in state.fixed_cells
            for cell in CELL_INDICES
        )

    def solve_logic(
        self,
        state: SudokuState,
        explain: bool = True,
        detailed_steps: bool = True,
    ) -> tuple[bool, list[ExplanationStep]]:
        """Apply logical moves until the puzzle is solved or logic is stuck.

        Args:
            state: Mutable puzzle state to solve in place.
            explain: Whether to collect display-ready explanation steps.
            detailed_steps: Whether to expand propagation into atomic steps.

        Returns:
            A `(solved, steps)` pair.
        """
        steps: list[ExplanationStep] = []

        while not state.solved() or (explain and self._has_unprocessed_singles(state)):
            move = self.next_move(state)
            if move is None:
                return False, steps

            before = state.clone()
            if not state.apply_move(move):
                return False, steps

            self._record_implied_step_uses(before, state, move)

            if explain:
                steps.extend(explanation_steps(before, state, move, detailed_steps))

        return True, steps

    def solve_with_search(
        self,
        state: SudokuState,
        explain: bool = True,
        detailed_steps: bool = True,
    ) -> tuple[SudokuState | None, list[ExplanationStep]]:
        """Solve with logical techniques first, then MRV backtracking."""
        all_steps: list[ExplanationStep] = []

        solved_logically, logic_steps = self.solve_logic(state, explain=explain, detailed_steps=detailed_steps)
        all_steps.extend(logic_steps)

        if solved_logically:
            return state, all_steps

        if not state.consistency_ok():
            return None, all_steps

        unsolved = unsolved_cells(state)
        if not unsolved:
            return None, all_steps

        cell = min(unsolved, key=lambda candidate_cell: bit_count(state.candidate_mask(candidate_cell)))

        for digit in state.candidate_digits(cell):
            child = state.clone()
            guess_move = Move(
                technique="Guess",
                difficulty=99,
                reason=f"MRV guess: try {digit} in {cell_text(cell)}.",
                placements=[Placement(cell, digit)],
            )

            before_guess = child.clone() if explain else None
            guess_start = time.perf_counter()
            guess_applied = child.apply_move(guess_move)
            guess_elapsed_ms = (time.perf_counter() - guess_start) * 1000.0
            self._record_guess_run(guess_move, guess_elapsed_ms, guess_applied)
            if not guess_applied:
                continue
            after_guess = child.clone() if explain else None

            result, child_steps = self.solve_with_search(child, explain=explain, detailed_steps=detailed_steps)
            if result is not None:
                if explain:
                    guess_steps = (
                        explanation_steps(before_guess, after_guess, guess_move, detailed_steps)
                        if before_guess and after_guess
                        else [ExplanationStep(guess_move)]
                    )
                    return result, all_steps + guess_steps + child_steps
                return result, all_steps

        return None, all_steps

    def solve_search_first(
        self,
        state: SudokuState,
        explain: bool = True,
        detailed_steps: bool = True,
    ) -> tuple[SudokuState | None, list[ExplanationStep]]:
        """Solve by MRV backtracking before applying logical techniques."""
        if state.solved():
            return state, []

        if not state.consistency_ok():
            return None, []

        unsolved = unsolved_cells(state)
        if not unsolved:
            return None, []

        cell = min(unsolved, key=lambda candidate_cell: bit_count(state.candidate_mask(candidate_cell)))

        for digit in state.candidate_digits(cell):
            child = state.clone()
            guess_move = Move(
                technique="Guess",
                difficulty=99,
                reason=f"MRV guess: try {digit} in {cell_text(cell)}.",
                placements=[Placement(cell, digit)],
            )

            before_guess = child.clone() if explain else None
            guess_start = time.perf_counter()
            guess_applied = child.apply_move(guess_move)
            guess_elapsed_ms = (time.perf_counter() - guess_start) * 1000.0
            self._record_guess_run(guess_move, guess_elapsed_ms, guess_applied)
            if not guess_applied:
                continue
            after_guess = child.clone() if explain else None

            result, child_steps = self.solve_search_first(child, explain=explain, detailed_steps=detailed_steps)
            if result is not None:
                if explain:
                    guess_steps = (
                        explanation_steps(before_guess, after_guess, guess_move, detailed_steps)
                        if before_guess and after_guess
                        else [ExplanationStep(guess_move)]
                    )
                    return result, guess_steps + child_steps
                return result, []

        return None, []
