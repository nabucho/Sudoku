from __future__ import annotations

import argparse
import sys
from typing import Iterable, List, Optional, Sequence, Tuple

from techniques import (
    BUGPlusOne,
    FinnedXWing,
    Fish,
    HiddenSingle,
    HiddenSubset,
    LockedCandidates,
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
    UniqueRectangleType4,
    WWing,
    XYWing,
    XYZWing,
)
from techniques.common import *
from visualization import format_steps, print_progress_steps


class SudokuSolver:
    def __init__(self, techniques: Optional[List[Technique]] = None, strategy: str = "human"):
        self.strategy = strategy
        if techniques is not None:
            self.techniques = techniques
        elif strategy == "fastest":
            self.techniques = self.fast_techniques()
        else:
            self.techniques = self.default_techniques()

    @staticmethod
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
            Skyscraper(),
            TwoStringKite(),
            TurbotFish(),
            WWing(),
            RemotePairs(),
            Fish(3),   # Swordfish
            XYWing(),
            Fish(4),   # Jellyfish
            XYZWing(),
            UniqueRectangleType1(),
            UniqueRectangleType2(),
            UniqueRectangleType4(),
            BUGPlusOne(),
            Nishio(),
        ]

    @staticmethod
    def fast_techniques() -> List[Technique]:
        return [
            NakedSingle(),
            HiddenSingle(),
            LockedCandidates(),
            NakedSubset(2),
            HiddenSubset(2),
        ]

    def next_move(self, state: SudokuState) -> Optional[Move]:
        """
        Pick the first valid move according to technique order.
        """
        if self.strategy == "fewest-steps":
            return self._highest_impact_move(state)

        for technique in self.techniques:
            moves = technique.find_moves(state)
            if moves:
                return self._best_move(moves)
        return None

    def _best_move(self, moves: List[Move]) -> Move:
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

    def _highest_impact_move(self, state: SudokuState) -> Optional[Move]:
        best_move: Optional[Move] = None
        best_score: Optional[Tuple[int, int, int, int]] = None

        before_solved = sum(1 for mask in state.candidates if is_single(mask))
        before_candidates = sum(bit_count(mask) for mask in state.candidates)

        for technique in self.techniques:
            for move in technique.find_moves(state):
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

        return best_move

    def _expanded_steps(self, before: SudokuState, after: SudokuState, move: Move) -> List[Move]:
        replay = before.clone()
        steps: List[Move] = []
        forced_queue: List[Tuple[int, int]] = []
        queued_forced: set[int] = set()

        def append_step(step: Move, changed_cells: Iterable[int]) -> None:
            step.after_candidates = replay.candidates[:]
            step.changed_cells = sorted(set(changed_cells))
            steps.append(step)

        def queue_forced_single(cell: int, difficulty: int) -> None:
            if cell not in replay.fixed_cells and cell not in queued_forced and is_single(replay.candidate_mask(cell)):
                forced_queue.append((cell, difficulty))
                queued_forced.add(cell)

        def process_forced_singles() -> bool:
            while forced_queue:
                cell, difficulty = forced_queue.pop(0)
                queued_forced.discard(cell)
                if cell in replay.fixed_cells or not is_single(replay.candidate_mask(cell)):
                    continue
                if not select_forced_single(cell, difficulty):
                    return False
            return True

        def propagate_digit(source_cell: int, digit: int, difficulty: int) -> bool:
            eliminations: List[Elimination] = []
            for peer in sorted(PEERS[source_cell]):
                if not replay.can_place(peer, digit):
                    continue

                new_mask = replay.candidate_mask(peer) & ~bit(digit)
                if new_mask == 0:
                    return False

                replay.candidates[peer] = new_mask
                eliminations.append(Elimination(peer, digit))
                if is_single(new_mask):
                    queue_forced_single(peer, difficulty)

            if eliminations:
                noun = "peer" if len(eliminations) == 1 else "peers"
                step = Move(
                    technique="Propagation",
                    difficulty=difficulty,
                    reason=f"{placement_text(Placement(source_cell, digit))} removes {digit} from {len(eliminations)} {noun}.",
                    eliminations=eliminations,
                )
                step.cause_cells = [source_cell]
                append_step(step, [elimination.cell for elimination in eliminations])

            return True

        def select_digit(cell: int, digit: int, technique: str, reason: str, difficulty: int) -> bool:
            if not replay.can_place(cell, digit):
                return False

            replay.candidates[cell] = bit(digit)
            replay.fixed_cells.add(cell)
            append_step(
                Move(
                    technique=technique,
                    difficulty=difficulty,
                    reason=reason,
                    placements=[Placement(cell, digit)],
                ),
                [cell],
            )

            if not propagate_digit(cell, digit, difficulty):
                return False
            return process_forced_singles()

        def select_forced_single(cell: int, difficulty: int) -> bool:
            digit = single_digit(replay.candidate_mask(cell))
            r, c = i_to_rc(cell)
            return select_digit(
                cell,
                digit,
                "Naked Single",
                f"r{r+1}c{c+1} is forced to {digit}.",
                difficulty,
            )

        def eliminate_digits_group(
            eliminations: Sequence[Elimination],
            technique: str,
            reason: str,
            difficulty: int,
            cause_cells: Optional[Iterable[int]] = None,
        ) -> bool:
            applied: List[Elimination] = []
            changed_cells: List[int] = []

            for elimination in eliminations:
                dmask = bit(elimination.digit)
                cur = replay.candidate_mask(elimination.cell)
                if not (cur & dmask):
                    continue

                new_mask = cur & ~dmask
                if new_mask == 0:
                    return False

                replay.candidates[elimination.cell] = new_mask
                applied.append(elimination)
                changed_cells.append(elimination.cell)
                if is_single(new_mask) and elimination.cell not in replay.fixed_cells:
                    queue_forced_single(elimination.cell, difficulty)

            if applied:
                step = Move(
                    technique=technique,
                    difficulty=difficulty,
                    reason=reason,
                    eliminations=applied,
                )
                step.cause_cells = sorted(set(cause_cells or []))
                append_step(step, changed_cells)

            return True

        for placement in move.placements:
            cell = placement.cell
            digit = placement.digit
            if not replay.can_place(cell, digit):
                return self._coarse_expanded_steps(before, after, move)

            if not select_digit(cell, digit, move.technique, move.reason, move.difficulty):
                return self._coarse_expanded_steps(before, after, move)

        if move.eliminations:
            if not eliminate_digits_group(
                move.eliminations,
                move.technique,
                move.reason,
                move.difficulty,
                move.cause_cells,
            ):
                return self._coarse_expanded_steps(before, after, move)

        if not process_forced_singles():
            return self._coarse_expanded_steps(before, after, move)

        if replay.candidates != after.candidates:
            return self._coarse_expanded_steps(before, after, move)

        return steps

    def _explanation_steps(self, before: SudokuState, after: SudokuState, move: Move, detailed_steps: bool) -> List[Move]:
        if detailed_steps:
            return self._expanded_steps(before, after, move)
        return self._coarse_expanded_steps(before, after, move)

    def _coarse_expanded_steps(self, before: SudokuState, after: SudokuState, move: Move) -> List[Move]:
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

        known_eliminations = {(elimination.cell, elimination.digit) for elimination in full_move.eliminations}
        for cell, (before_mask, after_mask) in enumerate(zip(before.candidates, after.candidates)):
            removed_mask = before_mask & ~after_mask
            for digit in digits_from_mask(removed_mask):
                key = (cell, digit)
                if key not in known_eliminations:
                    full_move.eliminations.append(Elimination(cell, digit))
                    known_eliminations.add(key)

        full_move.after_candidates = after.candidates[:]
        full_move.changed_cells = sorted(changed_cells)
        steps = [full_move]
        placed_cells = {placement.cell for placement in full_move.placements}

        for cell, (before_mask, after_mask) in enumerate(zip(before.candidates, after.candidates)):
            if cell in placed_cells:
                continue
            if not is_single(before_mask) and is_single(after_mask):
                digit = single_digit(after_mask)
                r, c = i_to_rc(cell)
                implied_move = Move(
                    technique="Naked Single",
                    difficulty=1,
                    reason=f"r{r+1}c{c+1} is forced to {digit}.",
                    placements=[Placement(cell, digit)],
                )
                implied_move.after_candidates = after.candidates[:]
                implied_move.changed_cells = [cell]
                steps.append(implied_move)

        return steps

    def _has_unprocessed_singles(self, state: SudokuState) -> bool:
        return any(
            is_single(state.candidate_mask(cell)) and cell not in state.fixed_cells
            for cell in range(81)
        )

    def solve_logic(
        self,
        state: SudokuState,
        explain: bool = True,
        detailed_steps: bool = True,
    ) -> Tuple[bool, List[Move]]:
        steps: List[Move] = []

        while not state.solved() or (explain and self._has_unprocessed_singles(state)):
            move = self.next_move(state)
            if move is None:
                return False, steps

            before = state.clone() if explain else None
            if not state.apply_move(move):
                return False, steps

            if explain and before is not None:
                steps.extend(self._explanation_steps(before, state, move, detailed_steps))

        return True, steps

    def solve_with_search(
        self,
        state: SudokuState,
        explain: bool = True,
        detailed_steps: bool = True,
    ) -> Tuple[Optional[SudokuState], List[Move]]:
        """
        Logic first; if stuck, use MRV backtracking.
        """
        all_steps: List[Move] = []

        solved_logically, logic_steps = self.solve_logic(state, explain=explain, detailed_steps=detailed_steps)
        all_steps.extend(logic_steps)

        if solved_logically:
            return state, all_steps

        if not state.consistency_ok():
            return None, all_steps

        unsolved_cells = [cell for cell in range(81) if not is_single(state.candidate_mask(cell))]
        if not unsolved_cells:
            return None, all_steps

        # MRV heuristic
        cell = min(unsolved_cells, key=lambda c: bit_count(state.candidate_mask(c)))

        for d in state.candidate_digits(cell):
            child = state.clone()
            guess_move = Move(
                technique="Guess",
                difficulty=99,
                reason=f"MRV guess: try {d} in r{i_to_rc(cell)[0]+1}c{i_to_rc(cell)[1]+1}.",
                placements=[Placement(cell, d)],
            )

            before_guess = child.clone() if explain else None
            if not child.apply_move(guess_move):
                continue
            after_guess = child.clone() if explain else None

            result, child_steps = self.solve_with_search(child, explain=explain, detailed_steps=detailed_steps)
            if result is not None:
                if explain:
                    guess_steps = (
                        self._explanation_steps(before_guess, after_guess, guess_move, detailed_steps)
                        if before_guess and after_guess
                        else [guess_move]
                    )
                    return result, all_steps + guess_steps + child_steps
                return result, all_steps

        return None, all_steps

    def solve_search_first(
        self,
        state: SudokuState,
        explain: bool = True,
        detailed_steps: bool = True,
    ) -> Tuple[Optional[SudokuState], List[Move]]:
        if state.solved():
            return state, []

        if not state.consistency_ok():
            return None, []

        unsolved_cells = [cell for cell in range(81) if not is_single(state.candidate_mask(cell))]
        if not unsolved_cells:
            return None, []

        cell = min(unsolved_cells, key=lambda c: bit_count(state.candidate_mask(c)))

        for d in state.candidate_digits(cell):
            child = state.clone()
            guess_move = Move(
                technique="Guess",
                difficulty=99,
                reason=f"MRV guess: try {d} in r{i_to_rc(cell)[0]+1}c{i_to_rc(cell)[1]+1}.",
                placements=[Placement(cell, d)],
            )

            before_guess = child.clone() if explain else None
            if not child.apply_move(guess_move):
                continue
            after_guess = child.clone() if explain else None

            result, child_steps = self.solve_search_first(child, explain=explain, detailed_steps=detailed_steps)
            if result is not None:
                if explain:
                    guess_steps = (
                        self._explanation_steps(before_guess, after_guess, guess_move, detailed_steps)
                        if before_guess and after_guess
                        else [guess_move]
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


def read_puzzle_argument(puzzle: Optional[str], puzzle_file: Optional[str]) -> str:
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
        choices=("human", "fewest-steps", "fastest", "search-first"),
        default="human",
        help=(
            "Choose how moves are selected. human uses easy techniques first, "
            "fewest-steps picks the largest-impact logical move, fastest uses cheap "
            "logic before search, and search-first starts with MRV backtracking."
        ),
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
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
    explain = not args.no_steps
    detailed_steps = args.step_style == "detailed"

    print("Original puzzle:")
    print(original_puzzle)
    print()

    if args.strategy == "search-first":
        result, steps = solver.solve_search_first(state, explain=explain, detailed_steps=detailed_steps)
    elif args.logic_only:
        solved, steps = solver.solve_logic(state, explain=explain, detailed_steps=detailed_steps)
        result: Optional[SudokuState] = state if solved else None
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

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130)
    except BrokenPipeError:
        raise SystemExit(1)
