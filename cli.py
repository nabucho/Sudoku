"""Command-line interface for the Sudoku solver."""

from __future__ import annotations

import argparse
import random
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from sudoku_solver.solver import SudokuSolver
from sudoku_solver.techniques.common import SudokuState, rc_to_i
from sudoku_solver.visualization import format_steps, print_progress_steps, print_timing_summary

PUZZLE_BANK_DIR = Path(__file__).resolve().parent / "sudoku-exchange-puzzle-bank"
DEFAULT_DIFFICULTIES = ("easy", "medium", "hard", "diabolical")
PUZZLE_BANK_METADATA_FILES = {"license"}


class RandomSource(Protocol):
    """Minimal random interface needed for puzzle-bank sampling."""

    def randrange(self, stop: int) -> int:
        """Return a random integer in `range(stop)`."""
        ...


def difficulty_choices(puzzle_bank_dir: Path = PUZZLE_BANK_DIR) -> tuple[str, ...]:
    """Return available difficulty names from puzzle-bank text files."""
    difficulties = tuple(
        sorted(
            path.stem for path in puzzle_bank_dir.glob("*.txt") if path.stem.lower() not in PUZZLE_BANK_METADATA_FILES
        )
    )
    return difficulties or DEFAULT_DIFFICULTIES


def random_puzzle_from_difficulty(
    difficulty: str,
    puzzle_bank_dir: Path = PUZZLE_BANK_DIR,
    rng: RandomSource | None = None,
) -> str:
    """Return a random puzzle from one Sudoku Exchange difficulty file."""
    if difficulty not in DEFAULT_DIFFICULTIES:
        raise ValueError(f"Unknown difficulty {difficulty!r}. Choose one of: {', '.join(DEFAULT_DIFFICULTIES)}.")

    path = puzzle_bank_dir / f"{difficulty}.txt"
    if not path.is_file():
        raise FileNotFoundError(
            f"Puzzle bank difficulty file not found: {path}. "
            "Clone submodules with `git submodule update --init --recursive`."
        )

    return random_puzzle_from_bank_file(path, rng)


def random_puzzle_from_bank_file(path: Path, rng: RandomSource | None = None) -> str:
    """Return a random puzzle from one Sudoku Exchange puzzle-bank file."""
    if not path.is_file():
        raise FileNotFoundError(f"Puzzle bank file not found: {path}.")

    selected: str | None = None
    seen = 0

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            puzzle = next(
                (field for field in line.split() if len(field) == 81 and all(char in "0123456789." for char in field)),
                None,
            )
            if puzzle is None:
                continue

            seen += 1
            random_index = rng.randrange(seen) if rng is not None else random.randrange(seen)
            if random_index == 0:
                selected = puzzle

    if selected is None:
        raise ValueError(f"No valid Sudoku puzzles found in {path}.")

    return selected


def read_puzzle_argument(
    puzzle: str | None,
    puzzle_file: str | None,
    difficulty: str | None = None,
    puzzle_bank_dir: Path = PUZZLE_BANK_DIR,
    puzzle_bank_file: Path | None = None,
) -> str:
    """Return puzzle text from one explicit input source."""
    source_count = sum(source is not None for source in (puzzle, puzzle_file, difficulty, puzzle_bank_file))
    if source_count > 1:
        raise ValueError("Use only one of a puzzle argument, --file, --difficulty, or --puzzle-bank-file.")

    if puzzle_file:
        with open(puzzle_file, "r", encoding="utf-8") as handle:
            return handle.read()

    if difficulty:
        return random_puzzle_from_difficulty(difficulty, puzzle_bank_dir)

    if puzzle_bank_file:
        return random_puzzle_from_bank_file(puzzle_bank_file)

    if puzzle:
        return puzzle

    raise ValueError("Provide a puzzle argument, --file, --difficulty, or --puzzle-bank-file.")


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
        description=("Solve a Sudoku puzzle. Empty cells may be written as 0 or .; non-puzzle characters are ignored.")
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
        "--difficulty",
        choices=difficulty_choices(),
        help=(
            "When no puzzle or --file is provided, choose a random puzzle from the matching "
            "Sudoku Exchange Puzzle Bank difficulty file."
        ),
    )
    parser.add_argument(
        "--puzzle-bank-dir",
        type=Path,
        default=PUZZLE_BANK_DIR,
        help=(
            f"Directory containing Sudoku Exchange Puzzle Bank difficulty .txt files. Defaults to {PUZZLE_BANK_DIR}."
        ),
    )
    parser.add_argument(
        "--puzzle-bank-file",
        type=Path,
        help="Choose a random puzzle from one concrete Sudoku Exchange Puzzle Bank .txt file.",
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
        choices=("human", "human-fast", "fewest-steps", "fastest", "balanced", "search-first"),
        default="human-fast",
        help=(
            "Choose how moves are selected. human uses the full explanatory technique set, "
            "human-fast skips costly low-yield techniques before search, fewest-steps picks "
            "the largest-impact logical move, fastest uses cheap logic before search, "
            "balanced adds a few cheap guess-reducing techniques, and search-first starts "
            "with MRV backtracking."
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
        puzzle = read_puzzle_argument(
            args.puzzle,
            args.puzzle_file,
            args.difficulty,
            args.puzzle_bank_dir,
            args.puzzle_bank_file,
        )
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
