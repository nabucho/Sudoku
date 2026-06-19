from __future__ import annotations

import itertools
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUZZLE_FILES = ["puzzle", "puzzle2", "puzzle3", "puzzle4"]
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


def main() -> int:
    tests = [
        test_direct_strategies,
        test_human_logic_only,
        test_step_styles,
        test_cli_validation,
    ]

    for test in tests:
        test()
        print(f"ok {test.__name__}")

    print(f"ok {len(tests)} test groups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
