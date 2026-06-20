"""Benchmark solver strategies across puzzle fixtures."""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sudoku_solver.solver import SudokuSolver
from sudoku_solver.techniques.common import SudokuState

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STRATEGIES = ["human", "balanced", "fastest", "search-first"]
PUZZLE_DIR = ROOT / "test" / "puzzles"


@dataclass(frozen=True)
class ProfileRow:
    """Per-puzzle timing summary for one technique under one strategy."""

    strategy: str
    puzzle: str
    technique: str
    attempts: int
    successes: int
    used: int
    total_ms: float
    successful_ms: float
    solved: bool

    @property
    def average_ms(self) -> float:
        return self.total_ms / self.attempts if self.attempts else 0.0

    @property
    def success_percent(self) -> float:
        return self.successes / self.attempts * 100.0 if self.attempts else 0.0


def fixture_paths() -> list[Path]:
    """Return all benchmark fixture paths."""
    return [path for path in sorted(PUZZLE_DIR.iterdir()) if path.is_file()]


def run_strategy(strategy: str, paths: list[Path]) -> tuple[dict[str, dict[str, float]], list[ProfileRow], int, float]:
    """Run one strategy over fixtures and collect aggregate/profile timings."""
    aggregate: dict[str, dict[str, float]] = {}
    profile_rows: list[ProfileRow] = []
    failures = 0
    wall_start = time.perf_counter()

    for path in paths:
        state = SudokuState.from_board(path.read_text(encoding="utf-8"))
        solver = SudokuSolver(strategy=strategy)
        solver.reset_timing()
        result, _ = solver.solve_with_search(state, explain=False)
        solved = result is not None
        if not solved:
            failures += 1

        for technique, stats in solver.timing_stats.items():
            entry = aggregate.setdefault(
                technique,
                {
                    "attempts": 0.0,
                    "successes": 0.0,
                    "used": 0.0,
                    "total_ms": 0.0,
                    "successful_ms": 0.0,
                },
            )
            entry["attempts"] += stats.attempts
            entry["successes"] += stats.successes
            entry["used"] += stats.used
            entry["total_ms"] += stats.total_ms
            entry["successful_ms"] += stats.successful_ms
            profile_rows.append(
                ProfileRow(
                    strategy=strategy,
                    puzzle=str(path.relative_to(ROOT)),
                    technique=technique,
                    attempts=stats.attempts,
                    successes=stats.successes,
                    used=stats.used,
                    total_ms=stats.total_ms,
                    successful_ms=stats.successful_ms,
                    solved=solved,
                )
            )

    wall_ms = (time.perf_counter() - wall_start) * 1000.0
    return aggregate, profile_rows, failures, wall_ms


def print_summary(strategy: str, aggregate: dict[str, dict[str, float]], failures: int, wall_ms: float, puzzle_count: int) -> None:
    """Print aggregate timing rows for one strategy."""
    print(f"Strategy: {strategy}")
    print(f"Puzzles: {puzzle_count}  Failures: {failures}  Wall ms: {wall_ms:.2f}")
    print("Technique                 Used  Runs    Found  Total ms  Avg ms  Avg found ms")
    print("------------------------  ----  ----  -------  --------  ------  --------------")

    rows = []
    for technique, stats in aggregate.items():
        attempts = stats["attempts"]
        successes = stats["successes"]
        avg_ms = stats["total_ms"] / attempts if attempts else 0.0
        success_percent = successes / attempts * 100.0 if attempts else 0.0
        avg_success_ms = stats["successful_ms"] / successes if successes else 0.0
        rows.append((stats["used"], avg_ms, technique, stats, success_percent, avg_success_ms))

    for _, avg_ms, technique, stats, success_percent, avg_success_ms in sorted(rows, key=lambda row: (-row[0], row[1], row[2])):
        print(
            f"{technique[:24]:24}  "
            f"{int(stats['used']):4d}  "
            f"{int(stats['attempts']):4d}  "
            f"{success_percent:6.1f}%  "
            f"{stats['total_ms']:8.2f}  "
            f"{avg_ms:6.2f}  "
            f"{avg_success_ms:14.2f}"
        )
    print()


def print_slowest_profile(rows: list[ProfileRow], limit: int) -> None:
    """Print the slowest per-puzzle technique timing rows."""
    if limit <= 0 or not rows:
        return

    print(f"Slowest technique runs by puzzle (top {limit}):")
    print("Strategy      Puzzle                Technique                 Runs  Used  Total ms  Avg ms    Found")
    print("------------  --------------------  ------------------------  ----  ----  --------  ------  -------")
    slowest = sorted(rows, key=lambda row: (-row.total_ms, -row.average_ms, row.strategy, row.puzzle, row.technique))
    for row in slowest[:limit]:
        print(
            f"{row.strategy[:12]:12}  "
            f"{row.puzzle[:20]:20}  "
            f"{row.technique[:24]:24}  "
            f"{row.attempts:4d}  "
            f"{row.used:4d}  "
            f"{row.total_ms:8.2f}  "
            f"{row.average_ms:6.2f}  "
            f"{row.success_percent:6.1f}%"
        )
    print()


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the benchmark CLI parser documented in README.md."""
    parser = argparse.ArgumentParser(description="Benchmark Sudoku solver strategy timing across fixtures.")
    parser.add_argument(
        "--strategy",
        action="append",
        choices=("human", "fewest-steps", "fastest", "balanced", "search-first"),
        help="Strategy to benchmark. Can be passed multiple times. Defaults to human, balanced, fastest, search-first.",
    )
    parser.add_argument(
        "--profile-slowest",
        type=int,
        default=0,
        metavar="N",
        help="Print the N slowest per-puzzle technique timing rows across all selected strategies.",
    )
    return parser


def main() -> int:
    """Run the benchmark command-line interface."""
    args = build_arg_parser().parse_args()

    paths = fixture_paths()
    if not paths:
        raise SystemExit("No fixtures found.")

    strategies = args.strategy or DEFAULT_STRATEGIES
    all_profile_rows: list[ProfileRow] = []
    for strategy in strategies:
        aggregate, profile_rows, failures, wall_ms = run_strategy(strategy, paths)
        all_profile_rows.extend(profile_rows)
        print_summary(strategy, aggregate, failures, wall_ms, len(paths))
    print_slowest_profile(all_profile_rows, args.profile_slowest)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
