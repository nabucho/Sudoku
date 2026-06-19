"""Command-line interface for the Sudoku solver."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from sudoku_solver.solver import SudokuSolver
from sudoku_solver.techniques.common import SudokuState, rc_to_i
from sudoku_solver.visualization import format_steps, print_progress_steps, print_timing_summary

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
    """Return puzzle text from either an inline argument, file, or default."""
    if puzzle and puzzle_file:
        raise ValueError("Use either a puzzle argument or --file, not both.")

    if puzzle_file:
        with open(puzzle_file, "r", encoding="utf-8") as handle:
            return handle.read()

    return puzzle or DEFAULT_PUZZLE


def pretty_puzzle(puzzle: str) -> str:
    """Format puzzle input as a 9x9 grid with separators."""
    chars = [ch for ch in puzzle if ch in "1234567890."]
    if len(chars) != 81:
        raise ValueError("String puzzle must contain exactly 81 digits / dots / zeros.")

    lines = []
    for row in range(9):
        if row and row % 3 == 0:
            lines.append("-" * 21)
        row_parts = []
        for col in range(9):
            if col and col % 3 == 0:
                row_parts.append("|")
            char = chars[rc_to_i(row, col)]
            row_parts.append(char if char in "123456789" else ".")
        lines.append(" ".join(row_parts))
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser documented in README.md."""
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
    """Run the command-line solver.

    Args:
        argv: Optional argument list. When `None`, arguments are read from
            `sys.argv`.

    Returns:
        Process exit code, where `0` means solved and `1` means no solution was
        found with the selected mode.
    """
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

    result: SudokuState | None
    if args.strategy == "search-first":
        result, steps = solver.solve_search_first(state, explain=explain, detailed_steps=detailed_steps)
    elif args.logic_only:
        solved, steps = solver.solve_logic(state, explain=explain, detailed_steps=detailed_steps)
        result = state if solved else None
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
                for step_number, step_text in enumerate(format_steps(steps, args.step_style), start=1):
                    print(f"{step_number:02d}. {step_text}")
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
