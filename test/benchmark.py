"""Benchmark solver strategies across puzzle fixtures."""

from __future__ import annotations

import argparse
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sudoku_solver.explanation import explanation_steps
from sudoku_solver.solver import MoveScore, SudokuSolver
from sudoku_solver.techniques.common import ExplanationStep, Move, SudokuState

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STRATEGIES = ["human", "human-fast", "balanced", "fastest", "search-first"]
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


@dataclass(frozen=True)
class StrategyProfile:
    """Aggregate wall-time buckets for one benchmarked strategy."""

    wall_ms: float
    technique_ms: float
    score_ms: float
    apply_ms: float

    @property
    def overhead_ms(self) -> float:
        return max(0.0, self.wall_ms - self.technique_ms - self.score_ms - self.apply_ms)


class ProfilingSudokuSolver(SudokuSolver):
    """Solver variant used by benchmarks to time non-technique buckets."""

    def __init__(self, strategy: str):
        super().__init__(strategy=strategy)
        self.profile_buckets: dict[str, float] = defaultdict(float)

    def _move_score(
        self,
        state: SudokuState,
        move: Move,
        before_solved: int,
        before_candidates: int,
    ) -> MoveScore | None:
        start = time.perf_counter()
        try:
            return super()._move_score(state, move, before_solved, before_candidates)
        finally:
            self.profile_buckets["score_ms"] += (time.perf_counter() - start) * 1000.0

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

            before = state.clone()
            apply_start = time.perf_counter()
            applied = state.apply_move(move)
            self.profile_buckets["apply_ms"] += (time.perf_counter() - apply_start) * 1000.0
            if not applied:
                return False, steps

            self._record_implied_step_uses(before, state, move)
            if explain:
                steps.extend(explanation_steps(before, state, move, detailed_steps))

        return True, steps


def fixture_paths() -> list[Path]:
    """Return all benchmark fixture paths."""
    return [path for path in sorted(PUZZLE_DIR.iterdir()) if path.is_file()]


def run_strategy(
    strategy: str,
    paths: list[Path],
    *,
    profile_buckets: bool = False,
) -> tuple[dict[str, dict[str, float]], list[ProfileRow], int, StrategyProfile]:
    """Run one strategy over fixtures and collect aggregate/profile timings."""
    aggregate: dict[str, dict[str, float]] = {}
    profile_rows: list[ProfileRow] = []
    failures = 0
    score_ms = 0.0
    apply_ms = 0.0
    wall_start = time.perf_counter()

    for path in paths:
        state = SudokuState.from_board(path.read_text(encoding="utf-8"))
        solver = ProfilingSudokuSolver(strategy=strategy) if profile_buckets else SudokuSolver(strategy=strategy)
        solver.reset_timing()
        result, _ = solver.solve_with_search(state, explain=False)
        solved = result is not None
        if not solved:
            failures += 1

        if isinstance(solver, ProfilingSudokuSolver):
            score_ms += solver.profile_buckets["score_ms"]
            apply_ms += solver.profile_buckets["apply_ms"]

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
    technique_ms = sum(stats["total_ms"] for stats in aggregate.values())
    profile = StrategyProfile(wall_ms=wall_ms, technique_ms=technique_ms, score_ms=score_ms, apply_ms=apply_ms)
    return aggregate, profile_rows, failures, profile


def print_summary(
    strategy: str,
    aggregate: dict[str, dict[str, float]],
    failures: int,
    profile: StrategyProfile,
    puzzle_count: int,
) -> None:
    """Print aggregate timing rows for one strategy."""
    print(f"Strategy: {strategy}")
    print(f"Puzzles: {puzzle_count}  Failures: {failures}  Wall ms: {profile.wall_ms:.2f}")
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


def print_bucket_profile(strategy: str, profile: StrategyProfile) -> None:
    """Print high-level wall-time buckets for one strategy."""
    print(f"Profile buckets for {strategy}:")
    print("View                 Total ms  Share")
    print("-------------------  --------  ------")
    rows = [
        ("discovery", profile.technique_ms),
        ("move scoring", profile.score_ms),
        ("applying moves", profile.apply_ms),
        ("overhead", profile.overhead_ms),
    ]
    for view, elapsed_ms in rows:
        share = elapsed_ms / profile.wall_ms * 100.0 if profile.wall_ms else 0.0
        print(f"{view[:19]:19}  {elapsed_ms:8.2f}  {share:5.1f}%")
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
        choices=("human", "human-fast", "fewest-steps", "fastest", "balanced", "search-first"),
        help=(
            "Strategy to benchmark. Can be passed multiple times. "
            "Defaults to human, human-fast, balanced, fastest, search-first."
        ),
    )
    parser.add_argument(
        "--profile-slowest",
        type=int,
        default=0,
        metavar="N",
        help="Print the N slowest per-puzzle technique timing rows across all selected strategies.",
    )
    parser.add_argument(
        "--profile-buckets",
        action="store_true",
        help="Print wall-time buckets for technique discovery, move scoring, applying moves, and overhead.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        metavar="N",
        help="Benchmark only the first N fixtures. Defaults to all fixtures.",
    )
    return parser


def main() -> int:
    """Run the benchmark command-line interface."""
    args = build_arg_parser().parse_args()

    paths = fixture_paths()
    if args.limit > 0:
        paths = paths[:args.limit]
    if not paths:
        raise SystemExit("No fixtures found.")

    strategies = args.strategy or DEFAULT_STRATEGIES
    all_profile_rows: list[ProfileRow] = []
    for strategy in strategies:
        aggregate, profile_rows, failures, profile = run_strategy(strategy, paths, profile_buckets=args.profile_buckets)
        all_profile_rows.extend(profile_rows)
        print_summary(strategy, aggregate, failures, profile, len(paths))
        if args.profile_buckets:
            print_bucket_profile(strategy, profile)
    print_slowest_profile(all_profile_rows, args.profile_slowest)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
