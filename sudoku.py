from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Sequence

from explanation import explanation_steps
from strategies import techniques_for_strategy
from techniques.common import (
    CELL_INDICES,
    ExplanationStep,
    Move,
    Placement,
    SudokuState,
    Technique,
    TechniqueTiming,
    bit_count,
    cell_text,
    is_single,
    rc_to_i,
    unsolved_cells,
)
from visualization import format_steps, print_progress_steps, print_timing_summary


class SudokuSolver:
    def __init__(self, techniques: list[Technique] | None = None, strategy: str = "human"):
        self.strategy = strategy
        self.timing_stats: dict[str, TechniqueTiming] = {}
        if techniques is not None:
            self.techniques = techniques
        else:
            self.techniques = techniques_for_strategy(strategy)

    def reset_timing(self) -> None:
        self.timing_stats = {}

    def _timing_for(self, technique_name: str) -> TechniqueTiming:
        if technique_name not in self.timing_stats:
            self.timing_stats[technique_name] = TechniqueTiming()
        return self.timing_stats[technique_name]

    def _find_moves_timed(self, technique: Technique, state: SudokuState) -> list[Move]:
        start = time.perf_counter()
        moves = technique.find_moves(state)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        successful = bool(moves)

        self._timing_for(technique.name).record_run(elapsed_ms, successful)
        for move in moves:
            move.timing_ms = elapsed_ms
        return moves

    def _record_move_use(self, move: Move) -> Move:
        self._timing_for(move.technique).record_use()
        return move

    def _record_guess_run(self, move: Move, elapsed_ms: float, successful: bool) -> None:
        move.timing_ms = elapsed_ms
        timing = self._timing_for(move.technique)
        timing.record_run(elapsed_ms, successful)
        if successful:
            timing.record_use()

    def next_move(self, state: SudokuState) -> Move | None:
        """
        Pick the first valid move according to technique order.
        """
        if self.strategy == "fewest-steps":
            return self._highest_impact_move(state)

        for technique in self.techniques:
            moves = self._find_moves_timed(technique, state)
            if moves:
                return self._record_move_use(self._best_move(moves))
        return None

    def _best_move(self, moves: list[Move]) -> Move:
        """
        Simple heuristic:
          - more eliminations / placements first
          - lower difficulty first
        """
        return min(
            moves,
            key=lambda m: (
                -len(m.placements) - len(m.eliminations),
                m.difficulty,
                m.technique,
            )
        )

    def _highest_impact_move(self, state: SudokuState) -> Move | None:
        best_move: Move | None = None
        best_score: tuple[int, int, int, int] | None = None

        before_solved = sum(1 for mask in state.candidates if is_single(mask))
        before_candidates = sum(bit_count(mask) for mask in state.candidates)

        for technique in self.techniques:
            for move in self._find_moves_timed(technique, state):
                child = state.clone()
                if not child.apply_move(move):
                    continue

                after_solved = sum(1 for mask in child.candidates if is_single(mask))
                after_candidates = sum(bit_count(mask) for mask in child.candidates)
                score = (
                    after_solved - before_solved,
                    before_candidates - after_candidates,
                    len(move.placements) + len(move.eliminations),
                    -move.difficulty,
                )

                if best_score is None or score > best_score:
                    best_score = score
                    best_move = move

        return self._record_move_use(best_move) if best_move is not None else None

    def _has_unprocessed_singles(self, state: SudokuState) -> bool:
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
        steps: list[ExplanationStep] = []

        while not state.solved() or (explain and self._has_unprocessed_singles(state)):
            move = self.next_move(state)
            if move is None:
                return False, steps

            before = state.clone() if explain else None
            if not state.apply_move(move):
                return False, steps

            if explain and before is not None:
                steps.extend(explanation_steps(before, state, move, detailed_steps))

        return True, steps

    def solve_with_search(
        self,
        state: SudokuState,
        explain: bool = True,
        detailed_steps: bool = True,
    ) -> tuple[SudokuState | None, list[ExplanationStep]]:
        """
        Logic first; if stuck, use MRV backtracking.
        """
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

        # MRV heuristic
        cell = min(unsolved, key=lambda c: bit_count(state.candidate_mask(c)))

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
        if state.solved():
            return state, []

        if not state.consistency_ok():
            return None, []

        unsolved = unsolved_cells(state)
        if not unsolved:
            return None, []

        cell = min(unsolved, key=lambda c: bit_count(state.candidate_mask(c)))

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


# ============================================================
# Command-line interface
# ============================================================

DEFAULT_PUZZLE = (
    "...8....3"
    "..8.61..."
    "14.37..2."
    "..4.8...7"
    "...7...4."
    "9.6.5..1."
    "2......9."
    ".1......."
    "5......3."
)


def read_puzzle_argument(puzzle: str | None, puzzle_file: str | None) -> str:
    if puzzle and puzzle_file:
        raise ValueError("Use either a puzzle argument or --file, not both.")

    if puzzle_file:
        with open(puzzle_file, "r", encoding="utf-8") as handle:
            return handle.read()

    return puzzle or DEFAULT_PUZZLE


def pretty_puzzle(puzzle: str) -> str:
    chars = [ch for ch in puzzle if ch in "1234567890."]
    if len(chars) != 81:
        raise ValueError("String puzzle must contain exactly 81 digits / dots / zeros.")

    lines = []
    for r in range(9):
        if r and r % 3 == 0:
            lines.append("-" * 21)
        row_parts = []
        for c in range(9):
            if c and c % 3 == 0:
                row_parts.append("|")
            ch = chars[rc_to_i(r, c)]
            row_parts.append(ch if ch in "123456789" else ".")
        lines.append(" ".join(row_parts))
    return "\n".join(lines)

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Solve a Sudoku puzzle. Empty cells may be written as 0 or .; "
            "non-puzzle characters are ignored."
        )
    )
    parser.add_argument(
        "puzzle",
        nargs="?",
        help="81-character puzzle string, using 0 or . for empty cells.",
    )
    parser.add_argument(
        "-f",
        "--file",
        dest="puzzle_file",
        help="Read the puzzle from a text file.",
    )
    parser.add_argument(
        "--logic-only",
        action="store_true",
        help="Use logical techniques only; do not fall back to search.",
    )
    parser.add_argument(
        "--no-steps",
        action="store_true",
        help="Print only the original and solved boards.",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Print compact step text instead of a colored board after each step.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors in progress output.",
    )
    parser.add_argument(
        "--no-pause",
        action="store_true",
        help="Do not wait for a key press after each progress step.",
    )
    parser.add_argument(
        "--step-style",
        choices=("detailed", "grouped", "batched"),
        default="detailed",
        help=(
            "Choose how solution steps are printed. "
            "Use detailed for one line per move, grouped to collapse forced singles, "
            "or batched to collapse consecutive moves with the same technique."
        ),
    )
    parser.add_argument(
        "--strategy",
        choices=("human", "fewest-steps", "fastest", "balanced", "search-first"),
        default="human",
        help=(
            "Choose how moves are selected. human uses easy techniques first, "
            "fewest-steps picks the largest-impact logical move, fastest uses cheap "
            "logic before search, balanced adds a few cheap guess-reducing techniques, "
            "and search-first starts with MRV backtracking."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        puzzle = read_puzzle_argument(args.puzzle, args.puzzle_file)
        original_puzzle = pretty_puzzle(puzzle)
        state = SudokuState.from_board(puzzle)
    except OSError as exc:
        parser.error(f"Could not read puzzle file: {exc}")
    except ValueError as exc:
        parser.error(str(exc))

    if args.logic_only and args.strategy == "search-first":
        parser.error("--logic-only cannot be used with --strategy search-first.")

    initial_candidates = state.candidates[:]
    solver = SudokuSolver(strategy=args.strategy)
    solver.reset_timing()
    explain = not args.no_steps
    detailed_steps = args.step_style == "detailed"

    print("Original puzzle:")
    print(original_puzzle)
    print()

    if args.strategy == "search-first":
        result, steps = solver.solve_search_first(state, explain=explain, detailed_steps=detailed_steps)
    elif args.logic_only:
        solved, steps = solver.solve_logic(state, explain=explain, detailed_steps=detailed_steps)
        result: SudokuState | None = state if solved else None
    else:
        result, steps = solver.solve_with_search(state, explain=explain, detailed_steps=detailed_steps)

    if not result:
        print("No solution found.", file=sys.stderr)
        return 1

    print("Solved board:")
    print(result.pretty())

    if explain:
        print()
        print("Steps:")
        if steps:
            if args.no_progress:
                for i, step_text in enumerate(format_steps(steps, args.step_style), start=1):
                    print(f"{i:02d}. {step_text}")
            else:
                print_progress_steps(
                    steps,
                    state.given_cells,
                    initial_candidates,
                    args.step_style,
                    not args.no_color,
                    not args.no_pause,
                )
        else:
            print("Already solved; no steps needed.")

    print_timing_summary(solver.timing_stats)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130)
    except BrokenPipeError:
        raise SystemExit(1)
