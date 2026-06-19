from __future__ import annotations

import itertools
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sudoku import SudokuSolver
from techniques.common import SudokuState


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
        test_all_puzzle_fixtures,
    ]

    for test in tests:
        test()
        print(f"ok {test.__name__}")

    print(f"ok {len(tests)} test groups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
