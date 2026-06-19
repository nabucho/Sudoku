from __future__ import annotations

import itertools
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sudoku import SudokuSolver
from techniques.basic import HiddenSingle, LockedCandidates, NakedSingle
from techniques.common import ALL_DIGITS_MASK, ROW_UNITS, SudokuState, bit, cell_text, rc_to_i


ROOT = Path(__file__).resolve().parents[1]
PUZZLE_FILES = ["puzzle", "puzzle2", "puzzle3", "puzzle4"]
PUZZLE_DIR = ROOT / "test" / "puzzles"
STRATEGIES = ["human", "fewest-steps", "fastest", "balanced", "search-first"]
STEP_STYLES = ["detailed", "grouped", "batched"]


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "sudoku.py"), *args],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


def run_benchmark_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "test" / "benchmark.py"), *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def puzzle_path(name: str) -> str:
    return str(Path("test") / name)


def assert_success(args: list[str]) -> None:
    result = run_command(args)
    if result.returncode != 0:
        raise AssertionError(f"Expected success for {args}, got {result.returncode}: {result.stderr.strip()}")


def assert_failure_contains(args: list[str], expected: str) -> None:
    result = run_command(args)
    if result.returncode == 0 or expected not in result.stderr:
        raise AssertionError(
            f"Expected failure containing {expected!r} for {args}, "
            f"got {result.returncode}: {result.stderr.strip()}"
        )


def state_with_candidates(overrides: dict[int, int], fixed_cells: set[int] | None = None) -> SudokuState:
    candidates = [ALL_DIGITS_MASK] * 81
    for cell, mask in overrides.items():
        candidates[cell] = mask
    return SudokuState(candidates, fixed_cells=fixed_cells or set())


def test_direct_strategies() -> None:
    for fixture, strategy in itertools.product(PUZZLE_FILES, STRATEGIES):
        assert_success(["--file", puzzle_path(fixture), "--strategy", strategy, "--no-steps"])


def test_human_logic_only() -> None:
    for fixture in ["puzzle", "puzzle2", "puzzle3"]:
        assert_success(["--file", puzzle_path(fixture), "--strategy", "human", "--logic-only", "--no-steps"])

    result = run_command(["--file", puzzle_path("puzzle4"), "--strategy", "human", "--logic-only", "--no-steps"])
    if result.returncode != 1 or result.stderr.strip() != "No solution found.":
        raise AssertionError(f"Expected puzzle4 human logic-only to be unsolved, got {result.returncode}: {result.stderr}")


def test_step_styles() -> None:
    for fixture, style in itertools.product(PUZZLE_FILES, STEP_STYLES):
        assert_success(
            [
                "--file",
                puzzle_path(fixture),
                "--strategy",
                "human",
                "--step-style",
                style,
                "--no-progress",
                "--no-pause",
            ]
        )


def test_cli_validation() -> None:
    assert_failure_contains(
        ["--file", puzzle_path("puzzle"), "--logic-only", "--strategy", "search-first", "--no-steps"],
        "--logic-only cannot be used with --strategy search-first",
    )
    assert_failure_contains(["--file", str(Path("test") / "missing"), "--no-steps"], "Could not read puzzle file")


def test_basic_techniques_directly() -> None:
    naked_state = state_with_candidates({rc_to_i(0, 0): bit(5)})
    naked_moves = NakedSingle().find_moves(naked_state)
    if len(naked_moves) != 1 or naked_moves[0].placements[0].digit != 5:
        raise AssertionError(f"Expected naked single placement, got {naked_moves}")
    if naked_moves[0].reason != f"{cell_text(rc_to_i(0, 0))} is forced to 5.":
        raise AssertionError(f"Unexpected naked single reason: {naked_moves[0].reason}")

    hidden_overrides = {
        cell: ALL_DIGITS_MASK & ~bit(7)
        for cell in ROW_UNITS[0]
        if cell != rc_to_i(0, 3)
    }
    hidden_overrides[rc_to_i(0, 3)] = bit(1) | bit(7)
    hidden_moves = HiddenSingle().find_moves(state_with_candidates(hidden_overrides))
    if len(hidden_moves) != 1 or hidden_moves[0].placements[0].cell != rc_to_i(0, 3):
        raise AssertionError(f"Expected hidden single at r1c4, got {hidden_moves}")
    if "within row 1" not in hidden_moves[0].reason:
        raise AssertionError(f"Unexpected hidden single reason: {hidden_moves[0].reason}")

    locked_overrides = {
        rc_to_i(0, 3): ALL_DIGITS_MASK,
        rc_to_i(0, 4): ALL_DIGITS_MASK,
        rc_to_i(0, 5): ALL_DIGITS_MASK,
        rc_to_i(0, 6): ALL_DIGITS_MASK,
    }
    for cell in range(81):
        if cell not in locked_overrides:
            locked_overrides[cell] = ALL_DIGITS_MASK & ~bit(9)
    locked_state = state_with_candidates(locked_overrides)
    locked_moves = LockedCandidates().find_moves(locked_state)
    pointing_moves = [
        move for move in locked_moves
        if move.reason.startswith("Pointing: digit 9 in box 2 is confined to row 1.")
    ]
    if not pointing_moves:
        raise AssertionError(f"Expected pointing locked candidate move, got {[move.reason for move in locked_moves]}")
    if not any(elimination.cell == rc_to_i(0, 6) and elimination.digit == 9 for elimination in pointing_moves[0].eliminations):
        raise AssertionError(f"Expected elimination from r1c7, got {pointing_moves[0].eliminations}")


def test_timing_measurements() -> None:
    state = SudokuState.from_board((ROOT / "test" / "puzzle").read_text(encoding="utf-8"))
    solver = SudokuSolver(strategy="fastest")
    result, _ = solver.solve_with_search(state, explain=False)
    if result is None:
        raise AssertionError("Expected fastest strategy to solve puzzle for timing test")

    hidden_stats = solver.timing_stats.get("Hidden Single")
    if hidden_stats is None or hidden_stats.attempts == 0 or hidden_stats.total_ms <= 0:
        raise AssertionError(f"Expected Hidden Single timing stats, got {hidden_stats}")
    if hidden_stats.success_percent < 0 or hidden_stats.success_percent > 100:
        raise AssertionError(f"Invalid success percent: {hidden_stats.success_percent}")


def test_benchmark_profile_output() -> None:
    result = run_benchmark_command(["--only-original", "--strategy", "fastest", "--profile-slowest", "3"])
    if result.returncode != 0:
        raise AssertionError(f"Expected benchmark success, got {result.returncode}: {result.stderr.strip()}")
    required = ["Strategy: fastest", "Slowest technique runs by puzzle", "Technique", "Total ms"]
    missing = [text for text in required if text not in result.stdout]
    if missing:
        raise AssertionError(f"Benchmark output missing {missing}: {result.stdout}")


def test_all_puzzle_fixtures() -> None:
    fixtures = sorted(path for path in PUZZLE_DIR.iterdir() if path.is_file())
    if len(fixtures) != 50:
        raise AssertionError(f"Expected 50 puzzle fixtures in {PUZZLE_DIR}, got {len(fixtures)}")

    solver = SudokuSolver(strategy="fastest")
    for path in fixtures:
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) != 9 or any(len(line) != 9 for line in lines):
            raise AssertionError(f"Expected 9x9 grid in {path}")
        if any(ch not in ".123456789" for line in lines for ch in line):
            raise AssertionError(f"Unexpected character in {path}")

        state = SudokuState.from_board(path.read_text(encoding="utf-8"))
        solver.reset_timing()
        result, _ = solver.solve_with_search(state, explain=False)
        if result is None:
            raise AssertionError(f"Expected {path} to solve")


def main() -> int:
    tests = [
        test_direct_strategies,
        test_human_logic_only,
        test_step_styles,
        test_cli_validation,
        test_basic_techniques_directly,
        test_timing_measurements,
        test_benchmark_profile_output,
        test_all_puzzle_fixtures,
    ]

    for test in tests:
        test()
        print(f"ok {test.__name__}")

    print(f"ok {len(tests)} test groups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
