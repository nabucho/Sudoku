from __future__ import annotations

import contextlib
import io
import itertools
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cli import main as cli_main, pretty_puzzle, read_puzzle_argument
from sudoku_solver.solver import SudokuSolver
from sudoku_solver.strategies import default_techniques
from sudoku_solver.techniques.basic import HiddenSingle, LockedCandidates, NakedSingle
from sudoku_solver.techniques.common import (
    ALL_DIGITS_MASK,
    ROW_UNITS,
    Elimination,
    ExplanationStep,
    Move,
    Placement,
    SudokuState,
    Technique,
    TechniqueTiming,
    apply_move_to_candidates,
    bit,
    cell_text,
    rc_to_i,
)
from sudoku_solver.visualization import (
    STYLE_CHANGED,
    STYLE_DECISION_SOURCE,
    STYLE_MAIN_SOURCE_DIGIT,
    STYLE_REMOVED_CANDIDATE,
    STYLE_SELECTED,
    STYLE_SHARED_SOURCE_DIGIT,
    ansi_text,
    format_steps,
    print_progress_steps,
    print_timing_summary,
    render_progress_grid,
    steps_for_progress,
    steps_for_style,
    wait_for_keypress,
)

ROOT = Path(__file__).resolve().parents[1]
PUZZLE_DIR = ROOT / "test" / "puzzles"
SYNTHETIC_DIR = ROOT / "test" / "synthetic"
ONLINE_DIR = ROOT / "test" / "online"
STRATEGIES = ["human", "human-fast", "fewest-steps", "fastest", "balanced", "search-first"]
STEP_STYLES = ["detailed", "grouped", "batched"]
REPRESENTATIVE_PUZZLE_NAMES = [
    "diabolical_34",
    "hard_30",
    "diabolical_54",
    "diabolical_39",
    "diabolical_15",
    "hard_33",
    "hard_10",
    "hard_44",
    "diabolical_53",
    "diabolical_46",
    "diabolical_48",
    "puzzle4",
]
LOGIC_ONLY_SOLVED_NAMES = ["easy_01", "medium_01", "hard_01"]
LOGIC_ONLY_UNSOLVED_NAME = "diabolical_51"
EXPECTED_SOUNDNESS_TECHNIQUES = {
    "AIC",
    "ALS-Wing",
    "ALS-XZ",
    "Avoidable Rectangle",
    "Empty Rectangle",
    "Finned Jellyfish",
    "Finned Swordfish",
    "Finned X-Wing",
    "Grouped AIC",
    "Grouped X-Chain",
    "Hidden Pair",
    "Hidden Single",
    "Hidden Triple",
    "Locked Candidates",
    "Multi-Coloring",
    "Naked Pair",
    "Naked Single",
    "Naked Triple",
    "Nishio",
    "Simple Coloring",
    "Skyscraper",
    "Sue de Coq",
    "Swordfish",
    "Turbot Fish",
    "Two-String Kite",
    "Unique Rectangle Type 1",
    "Unique Rectangle Type 4",
    "W-Wing",
    "X-Chain",
    "X-Wing",
    "XY-Chain",
    "XY-Wing",
    "XYZ-Wing",
}


class SoundnessCheckingSolver(SudokuSolver):
    """Validate every emitted logical move against the current search branch."""

    def __init__(self, puzzle_name: str, strategy: str = "human-fast"):
        super().__init__(strategy=strategy)
        self.puzzle_name = puzzle_name
        self._solution_cache: dict[tuple[tuple[int, ...], tuple[int, int, bool]], bool] = {}
        self.soundness_coverage: Counter[str] = Counter()
        self.soundness_examples: dict[str, str] = {}

    def _find_moves_timed(self, technique: Technique, state: SudokuState) -> list[Move]:
        moves = super()._find_moves_timed(technique, state)
        for move in moves:
            self._assert_move_sound(state, move)
        return moves

    def _assert_move_sound(self, state: SudokuState, move: Move) -> None:
        for placement in move.placements:
            if self._has_solution_with_digit_removed(state, placement.cell, placement.digit):
                raise AssertionError(
                    f"{self.puzzle_name}: {move.technique} placed {cell_text(placement.cell)}={placement.digit}, "
                    f"but another solution remains if that digit is removed. Move: {move.summary()}"
                )

        for elimination in move.eliminations:
            if self._has_solution_with_digit_placed(state, elimination.cell, elimination.digit):
                raise AssertionError(
                    f"{self.puzzle_name}: {move.technique} removed candidate "
                    f"{cell_text(elimination.cell)}!={elimination.digit}, but a solution still exists with it. "
                    f"Move: {move.summary()}"
                )

        if move.placements or move.eliminations:
            self.soundness_coverage[move.technique] += 1
            self.soundness_examples.setdefault(move.technique, move.summary())

    def _has_solution_with_digit_removed(self, state: SudokuState, cell: int, digit: int) -> bool:
        return self._has_solution_with_constraint(state, cell, digit, place_digit=False)

    def _has_solution_with_digit_placed(self, state: SudokuState, cell: int, digit: int) -> bool:
        return self._has_solution_with_constraint(state, cell, digit, place_digit=True)

    def _has_solution_with_constraint(self, state: SudokuState, cell: int, digit: int, *, place_digit: bool) -> bool:
        key = (tuple(state.candidates), (cell, digit, place_digit))
        if key not in self._solution_cache:
            constrained = state.clone()
            applied = (
                constrained.place_digit(cell, digit)
                if place_digit
                else constrained.eliminate_digit(cell, digit)
            )
            if not applied or not constrained.consistency_ok():
                self._solution_cache[key] = False
            else:
                result, _ = SudokuSolver(strategy="search-first").solve_search_first(constrained, explain=False)
                self._solution_cache[key] = result is not None
        return self._solution_cache[key]


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


def styled_fragment(text: str, *, fg: int | None = None, bg: int | None = None, bold: bool = False) -> str:
    return ansi_text(text, fg=fg, bg=bg, bold=bold)


def progress(message: str) -> None:
    print(f"    {message}", flush=True)


def puzzle_fixtures() -> list[Path]:
    return sorted(path for path in PUZZLE_DIR.iterdir() if path.is_file())


def puzzle_fixture(name: str) -> Path:
    path = PUZZLE_DIR / name
    if not path.is_file():
        raise AssertionError(f"Expected puzzle fixture {path}")
    return path


def puzzle_fixture_subset(names: list[str]) -> list[Path]:
    return [puzzle_fixture(name) for name in names]


def fixture_arg(path: Path) -> str:
    return str(path.relative_to(ROOT))


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


def parse_cell_reference(text: str) -> int:
    col_marker = text.index("c")
    row = int(text[1:col_marker]) - 1
    col = int(text[col_marker + 1:]) - 1
    return rc_to_i(row, col)


def parse_candidate_mask(text: str) -> int:
    mask = 0
    for char in text:
        mask |= bit(int(char))
    return mask


def parse_cell_list(text: str) -> set[int]:
    if text == "none":
        return set()
    return {int(cell) for cell in text.split(",") if cell}


def parse_expected_placements(text: str) -> set[tuple[int, int]]:
    if text == "none":
        return set()
    placements = set()
    for item in text.split(", "):
        cell_text_value, digit = item.split("=")
        placements.add((parse_cell_reference(cell_text_value), int(digit)))
    return placements


def parse_expected_eliminations(text: str) -> set[tuple[int, int]]:
    if text == "none":
        return set()
    eliminations = set()
    for item in text.split(", "):
        cell_text_value, digit = item.split("!=")
        eliminations.add((parse_cell_reference(cell_text_value), int(digit)))
    return eliminations


def load_synthetic_fixture(path: Path) -> tuple[str, SudokuState, set[tuple[int, int]], set[tuple[int, int]]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    candidate_start = lines.index("candidates:")
    metadata = {
        key: value
        for line in lines[:candidate_start]
        for key, value in [line.split(": ", 1)]
    }
    candidate_rows = lines[candidate_start + 1:]
    if len(candidate_rows) != 9:
        raise AssertionError(f"Expected 9 candidate rows in {path}, got {len(candidate_rows)}")

    candidates: list[int] = []
    for row in candidate_rows:
        row_cells = row.split()
        if len(row_cells) != 9:
            raise AssertionError(f"Expected 9 candidate cells in {path}: {row}")
        candidates.extend(parse_candidate_mask(cell) for cell in row_cells)

    return (
        metadata["technique"],
        SudokuState(
            candidates,
            fixed_cells=parse_cell_list(metadata["fixed"]),
            given_cells=parse_cell_list(metadata["given"]),
        ),
        parse_expected_placements(metadata["placements"]),
        parse_expected_eliminations(metadata["eliminations"]),
    )


def assert_technique_fixtures(
    fixtures: list[Path],
    techniques: dict[str, Technique],
) -> set[str]:
    fixture_names = set()
    for path in fixtures:
        technique_name, state, expected_placements, expected_eliminations = load_synthetic_fixture(path)
        progress(f"checking {path.name} with {technique_name}")
        fixture_names.add(technique_name)
        technique = techniques.get(technique_name)
        if technique is None:
            raise AssertionError(f"{path} references unknown technique {technique_name!r}")

        moves = technique.find_moves(state)
        expected = (expected_placements, expected_eliminations)
        actual = [
            (
                {(placement.cell, placement.digit) for placement in move.placements},
                {(elimination.cell, elimination.digit) for elimination in move.eliminations},
            )
            for move in moves
        ]
        if expected not in actual:
            raise AssertionError(
                f"{technique_name} fixture {path.name} did not produce expected move. "
                f"Expected {expected}, got {actual}"
            )

    return fixture_names


def test_direct_strategies() -> None:
    for fixture, strategy in itertools.product(puzzle_fixtures()[:4], STRATEGIES):
        progress(f"CLI solve {fixture.name} using strategy={strategy}")
        assert_success(["--file", fixture_arg(fixture), "--strategy", strategy, "--no-steps"])


def test_human_logic_only() -> None:
    for fixture in puzzle_fixture_subset(LOGIC_ONLY_SOLVED_NAMES):
        progress(f"logic-only human solve probe {fixture.name}")
        assert_success(["--file", fixture_arg(fixture), "--strategy", "human", "--logic-only", "--no-steps"])

    unsolved_fixture = puzzle_fixture(LOGIC_ONLY_UNSOLVED_NAME)
    progress(f"logic-only human failure probe {unsolved_fixture.name}")
    result = run_command(["--file", fixture_arg(unsolved_fixture), "--strategy", "human", "--logic-only", "--no-steps"])
    if result.returncode != 1 or result.stderr.strip() != "No solution found.":
        raise AssertionError(
            f"Expected logic-only failure for {unsolved_fixture}, got {result.returncode}: {result.stderr}"
        )


def test_step_styles() -> None:
    for fixture, style in itertools.product(puzzle_fixtures()[:4], STEP_STYLES):
        progress(f"render step-style={style} for {fixture.name}")
        assert_success(
            [
                "--file",
                fixture_arg(fixture),
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
        ["--file", fixture_arg(puzzle_fixtures()[0]), "--logic-only", "--strategy", "search-first", "--no-steps"],
        "--logic-only cannot be used with --strategy search-first",
    )
    assert_failure_contains(["--file", str(Path("test") / "missing"), "--no-steps"], "Could not read puzzle file")


def test_cli_helpers_in_process() -> None:
    if read_puzzle_argument("0" * 81, None) != "0" * 81:
        raise AssertionError("Expected inline puzzle argument to be returned")

    try:
        read_puzzle_argument("0" * 81, str(puzzle_fixtures()[0]))
    except ValueError as exc:
        if "Use either" not in str(exc):
            raise AssertionError(f"Unexpected read_puzzle_argument error: {exc}")
    else:
        raise AssertionError("Expected read_puzzle_argument to reject puzzle plus file")

    pretty = pretty_puzzle("." * 81)
    if pretty.count(".") != 81 or "---------------------" not in pretty:
        raise AssertionError(f"Unexpected pretty puzzle output: {pretty}")

    stdout = io.StringIO()
    stderr = io.StringIO()
    progress("running in-process CLI solve")
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        exit_code = cli_main(["--file", str(puzzle_fixtures()[0]), "--no-steps"])
    if exit_code != 0:
        raise AssertionError(f"Expected in-process CLI success, got {exit_code}: {stderr.getvalue()}")
    if "Original puzzle:" not in stdout.getvalue() or "Solved board:" not in stdout.getvalue():
        raise AssertionError(f"Unexpected in-process CLI output: {stdout.getvalue()}")

    unsolved_fixture = puzzle_fixture(LOGIC_ONLY_UNSOLVED_NAME)
    stdout = io.StringIO()
    stderr = io.StringIO()
    progress(f"running in-process CLI logic-only failure for {unsolved_fixture.name}")
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        exit_code = cli_main(
            [
                "--file",
                str(unsolved_fixture),
                "--strategy",
                "human",
                "--logic-only",
                "--no-steps",
            ]
        )
    if exit_code != 1 or "No solution found." not in stderr.getvalue():
        raise AssertionError(f"Expected logic-only failure, got {exit_code}: {stderr.getvalue()}")


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


def test_synthetic_technique_fixtures() -> None:
    techniques: dict[str, Technique] = {technique.name: technique for technique in default_techniques()}
    fixtures = sorted(SYNTHETIC_DIR.glob("*.sdkc"))
    progress(f"checking {len(fixtures)} synthetic technique fixtures")

    if not fixtures:
        raise AssertionError(f"Expected synthetic technique fixtures in {SYNTHETIC_DIR}")

    fixture_names = assert_technique_fixtures(fixtures, techniques)
    missing = set(techniques) - fixture_names
    extra = fixture_names - set(techniques)
    if missing or extra:
        raise AssertionError(f"Synthetic fixture mismatch: missing={sorted(missing)}, extra={sorted(extra)}")


def test_online_technique_fixtures() -> None:
    techniques: dict[str, Technique] = {technique.name: technique for technique in default_techniques()}
    fixtures = sorted(ONLINE_DIR.glob("*.sdkc"))
    progress(f"checking {len(fixtures)} online/reference technique fixtures")

    if not fixtures:
        raise AssertionError(f"Expected online technique fixtures in {ONLINE_DIR}")

    assert_technique_fixtures(fixtures, techniques)


def test_timing_measurements() -> None:
    progress("checking technique timing measurements")
    state = SudokuState.from_board(puzzle_fixtures()[0].read_text(encoding="utf-8"))
    solver = SudokuSolver(strategy="fastest")
    result, _ = solver.solve_with_search(state, explain=False)
    if result is None:
        raise AssertionError("Expected fastest strategy to solve puzzle for timing test")

    hidden_stats = solver.timing_stats.get("Hidden Single")
    if hidden_stats is None or hidden_stats.attempts == 0 or hidden_stats.total_ms <= 0:
        raise AssertionError(f"Expected Hidden Single timing stats, got {hidden_stats}")
    if hidden_stats.success_percent < 0 or hidden_stats.success_percent > 100:
        raise AssertionError(f"Invalid success percent: {hidden_stats.success_percent}")

    propagation_state = SudokuState.from_board((PUZZLE_DIR / "diabolical_03").read_text(encoding="utf-8"))
    propagation_solver = SudokuSolver(strategy="human")
    progress("checking propagation timing measurements")
    result, _ = propagation_solver.solve_with_search(propagation_state, explain=False)
    if result is None:
        raise AssertionError("Expected human strategy to solve diabolical_03 for propagation timing test")
    naked_stats = propagation_solver.timing_stats.get("Naked Single")
    if naked_stats is None or naked_stats.used <= 2:
        raise AssertionError(f"Expected propagated naked singles to be counted, got {naked_stats}")
    propagation_stats = propagation_solver.timing_stats.get("Propagation")
    if propagation_stats is None or propagation_stats.used == 0:
        raise AssertionError(f"Expected propagation steps to be counted, got {propagation_stats}")


def test_best_move_uses_board_impact() -> None:
    solver = SudokuSolver(techniques=[])
    state = state_with_candidates(
        {
            rc_to_i(0, 0): bit(1) | bit(2),
            rc_to_i(0, 1): bit(1) | bit(3),
            rc_to_i(0, 2): bit(2) | bit(3),
            rc_to_i(8, 8): bit(4) | bit(5) | bit(6) | bit(7),
        }
    )
    propagating_move = Move(
        technique="Test",
        difficulty=1,
        reason="Place 1 and create a naked single through propagation.",
        placements=[Placement(rc_to_i(0, 0), 1)],
    )
    larger_explicit_move = Move(
        technique="Test",
        difficulty=1,
        reason="Remove two candidates without solving a cell.",
        eliminations=[Elimination(rc_to_i(8, 8), 4), Elimination(rc_to_i(8, 8), 5)],
    )

    best_move = solver._best_move(state, [larger_explicit_move, propagating_move])
    if best_move is not propagating_move:
        raise AssertionError(f"Expected propagated board impact to win, got {best_move}")


def test_changed_unit_move_validation() -> None:
    candidates = [ALL_DIGITS_MASK] * 81
    candidates[rc_to_i(0, 0)] = bit(1) | bit(2)
    for col in range(1, 9):
        candidates[rc_to_i(0, col)] &= ~bit(1)

    move = Move(
        technique="Test",
        difficulty=1,
        reason="Remove the row's last candidate for 1.",
        eliminations=[Elimination(rc_to_i(0, 0), 1)],
    )
    if apply_move_to_candidates(candidates, move, validate_all=False):
        raise AssertionError("Expected changed-unit validation to catch a missing row digit")


def test_fewest_steps_avoids_internal_chain_eliminations() -> None:
    state = SudokuState.from_board((PUZZLE_DIR / "diabolical_05").read_text(encoding="utf-8"))
    solver = SudokuSolver(strategy="fewest-steps")
    result, _ = solver.solve_with_search(state, explain=False)
    if result is None:
        raise AssertionError("Expected fewest-steps to solve diabolical_05")


def test_visualization_directly() -> None:
    placement_move = Move(
        technique="Naked Single",
        difficulty=1,
        reason="r1c1 is forced to 5.",
        placements=[Placement(rc_to_i(0, 0), 5)],
    )
    placement_move.timing_ms = 1.25
    placement_step = ExplanationStep(placement_move, [ALL_DIGITS_MASK] * 81, [rc_to_i(0, 0)])

    elimination_move = Move(
        technique="Propagation",
        difficulty=1,
        reason="r1c1=5 removes 5 from peers.",
        eliminations=[Elimination(rc_to_i(0, 1), 5)],
    )
    elimination_move.cause_cells = [rc_to_i(0, 0)]
    elimination_step = ExplanationStep(elimination_move, [ALL_DIGITS_MASK] * 81, [rc_to_i(0, 1)])

    steps = [placement_step, elimination_step]
    detailed = format_steps(steps, "detailed")
    if "Naked Single" not in detailed[0] or "1.25 ms" not in detailed[0]:
        raise AssertionError(f"Unexpected detailed formatting: {detailed}")

    grouped = steps_for_style([placement_step, placement_step], "grouped")
    if len(grouped) != 1 or grouped[0].technique != "Naked Singles":
        raise AssertionError(f"Expected grouped naked singles, got {grouped}")

    batched = steps_for_style([elimination_step, elimination_step], "batched")
    if len(batched) != 1 or batched[0].technique != "Propagations":
        raise AssertionError(f"Expected batched propagations, got {batched}")

    progress_steps = steps_for_progress([elimination_step, elimination_step], "detailed")
    if len(progress_steps) != 1 or progress_steps[0].technique != "Propagations":
        raise AssertionError(f"Expected grouped progress propagations, got {progress_steps}")

    unrelated_move = Move(
        technique="Propagation",
        difficulty=1,
        reason="r1c2=5 removes 5 from peers.",
        eliminations=[Elimination(rc_to_i(0, 1), 5)],
    )
    unrelated_move.cause_cells = [rc_to_i(0, 2)]
    unrelated_step = ExplanationStep(unrelated_move, [ALL_DIGITS_MASK] * 81, [rc_to_i(0, 1)])
    combined_steps = steps_for_style([placement_step, unrelated_step], "detailed")
    if len(combined_steps) != 2:
        raise AssertionError(f"Expected unrelated propagation to remain separate, got {combined_steps}")

    combined_steps = steps_for_style([placement_step, elimination_step], "detailed")
    if len(combined_steps) != 1 or not combined_steps[0].placements or not combined_steps[0].eliminations:
        raise AssertionError(f"Expected caused propagation to merge with placement, got {combined_steps}")

    candidates = [ALL_DIGITS_MASK] * 81
    candidates[rc_to_i(0, 0)] = bit(5)
    grid = render_progress_grid(
        candidates,
        given_cells={rc_to_i(0, 8)},
        solved_cells=set(),
        selected_cells=[rc_to_i(0, 0)],
        candidate_eliminations=[Elimination(rc_to_i(0, 1), 5)],
        cause_cells=[rc_to_i(0, 2)],
        use_color=False,
    )
    if "5" not in grid or "|" not in grid or "1 2 3" not in grid:
        raise AssertionError(f"Unexpected progress grid output: {grid}")

    colored_grid = render_progress_grid(
        candidates,
        given_cells={rc_to_i(0, 8)},
        solved_cells=set(),
        selected_cells=[rc_to_i(0, 0)],
        candidate_eliminations=[Elimination(rc_to_i(0, 1), 5)],
        cause_cells=[rc_to_i(0, 2)],
        use_color=True,
    )
    selected_digit = styled_fragment("    5    ", fg=STYLE_SELECTED.fg, bg=STYLE_SELECTED.bg, bold=STYLE_SELECTED.bold)
    removed_digit = styled_fragment(
        "5",
        fg=STYLE_REMOVED_CANDIDATE.fg,
        bg=STYLE_CHANGED.bg,
        bold=STYLE_REMOVED_CANDIDATE.bold,
    )
    source_digit = styled_fragment(
        "5",
        fg=STYLE_MAIN_SOURCE_DIGIT.fg,
        bg=STYLE_DECISION_SOURCE.bg,
        bold=STYLE_MAIN_SOURCE_DIGIT.bold,
    )
    pale_candidate = styled_fragment(
        "1",
        fg=STYLE_DECISION_SOURCE.fg,
        bg=STYLE_DECISION_SOURCE.bg,
        bold=STYLE_DECISION_SOURCE.bold,
    )
    if selected_digit not in colored_grid:
        raise AssertionError(f"Expected selected digit to use selected style: {colored_grid}")
    if removed_digit not in colored_grid:
        raise AssertionError(f"Expected removed candidate to use removed style: {colored_grid}")
    if source_digit not in colored_grid:
        raise AssertionError(f"Expected decision source digit to use main source style: {colored_grid}")
    if pale_candidate not in colored_grid:
        raise AssertionError(f"Expected non-involved candidates to use decision source cell style: {colored_grid}")

    xy_candidates = [ALL_DIGITS_MASK] * 81
    pivot = rc_to_i(8, 2)
    xz_pincer = rc_to_i(2, 2)
    yz_pincer = rc_to_i(6, 0)
    xy_candidates[pivot] = bit(1) | bit(6)
    xy_candidates[xz_pincer] = bit(1) | bit(8)
    xy_candidates[yz_pincer] = bit(6) | bit(8)
    xy_grid = render_progress_grid(
        xy_candidates,
        given_cells=set(),
        solved_cells=set(),
        selected_cells=[],
        candidate_eliminations=[Elimination(rc_to_i(0, 0), 8)],
        cause_cells=[pivot, xz_pincer, yz_pincer],
        use_color=True,
        source_digit_roles={
            (pivot, 1): "primary",
            (pivot, 6): "primary",
            (xz_pincer, 1): "primary",
            (yz_pincer, 6): "primary",
            (xz_pincer, 8): "secondary",
            (yz_pincer, 8): "secondary",
        },
    )
    primary_1 = styled_fragment(
        "1",
        fg=STYLE_MAIN_SOURCE_DIGIT.fg,
        bg=STYLE_DECISION_SOURCE.bg,
        bold=STYLE_MAIN_SOURCE_DIGIT.bold,
    )
    primary_6 = styled_fragment(
        "6",
        fg=STYLE_MAIN_SOURCE_DIGIT.fg,
        bg=STYLE_DECISION_SOURCE.bg,
        bold=STYLE_MAIN_SOURCE_DIGIT.bold,
    )
    secondary_8 = styled_fragment(
        "8",
        fg=STYLE_SHARED_SOURCE_DIGIT.fg,
        bg=STYLE_DECISION_SOURCE.bg,
        bold=STYLE_SHARED_SOURCE_DIGIT.bold,
    )
    primary_8 = styled_fragment(
        "8",
        fg=STYLE_MAIN_SOURCE_DIGIT.fg,
        bg=STYLE_DECISION_SOURCE.bg,
        bold=STYLE_MAIN_SOURCE_DIGIT.bold,
    )
    if primary_1 not in xy_grid or primary_6 not in xy_grid:
        raise AssertionError(f"Expected XY-Wing pivot digits to use primary source color: {xy_grid}")
    if secondary_8 not in xy_grid:
        raise AssertionError(f"Expected XY-Wing shared pincer digit to use secondary source color: {xy_grid}")
    if primary_8 in xy_grid:
        raise AssertionError(f"Expected XY-Wing shared pincer digit to avoid primary source color: {xy_grid}")

    if ansi_text("x", fg=31, bold=True, enabled=False) != "x":
        raise AssertionError("Expected disabled ANSI output to return plain text")
    if "\033[" not in ansi_text("x", fg=31, bold=True, enabled=True):
        raise AssertionError("Expected enabled ANSI output to include escape sequence")
    if not wait_for_keypress(False):
        raise AssertionError("Expected disabled keypress wait to continue")

    timing = TechniqueTiming()
    timing.record_run(2.0, True)
    timing.record_use()
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        print_timing_summary({"Naked Single": timing})
    if "Technique timing summary" not in stdout.getvalue():
        raise AssertionError(f"Unexpected timing summary: {stdout.getvalue()}")

    propagation_timing = TechniqueTiming()
    propagation_timing.record_run(0.0, True)
    propagation_timing.record_use()
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        print_timing_summary({"Propagation": propagation_timing, "Naked Single": timing})
    if "Propagation" in stdout.getvalue():
        raise AssertionError(f"Expected propagation to be hidden from timing summary: {stdout.getvalue()}")

    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        print_progress_steps(steps, set(), [ALL_DIGITS_MASK] * 81, "detailed", False, False)
    if "Legend:" not in stdout.getvalue() or "Before step 1" not in stdout.getvalue():
        raise AssertionError(f"Unexpected progress steps output: {stdout.getvalue()}")


def test_benchmark_profile_output() -> None:
    progress("running benchmark smoke with profile buckets")
    result = run_benchmark_command(["--strategy", "fastest", "--limit", "4", "--profile-slowest", "3", "--profile-buckets"])
    if result.returncode != 0:
        raise AssertionError(f"Expected benchmark success, got {result.returncode}: {result.stderr.strip()}")
    required = ["Strategy: fastest", "Profile buckets for fastest", "Slowest technique runs by puzzle", "Technique", "Total ms"]
    missing = [text for text in required if text not in result.stdout]
    if missing:
        raise AssertionError(f"Benchmark output missing {missing}: {result.stdout}")


def test_technique_soundness_oracle() -> None:
    """Validate representative emitted logical moves against current-state solution existence."""
    coverage: Counter[str] = Counter()
    examples: dict[str, str] = {}

    for path in puzzle_fixture_subset(REPRESENTATIVE_PUZZLE_NAMES):
        progress(f"soundness oracle validating {path.name}")
        state = SudokuState.from_board(path.read_text(encoding="utf-8"))
        solver = SoundnessCheckingSolver(path.name, strategy="human")
        result, _ = solver.solve_with_search(state, explain=False)
        if result is None:
            raise AssertionError(f"Expected {path} to solve while running soundness oracle")
        coverage.update(solver.soundness_coverage)
        for technique, example in solver.soundness_examples.items():
            examples.setdefault(technique, example)

    missing = EXPECTED_SOUNDNESS_TECHNIQUES - set(coverage)
    if missing:
        counts = ", ".join(f"{technique}={coverage[technique]}" for technique in sorted(coverage))
        raise AssertionError(
            f"Soundness oracle did not cover expected techniques {sorted(missing)}. "
            f"Covered counts: {counts}"
        )

    unexpected = set(coverage) - EXPECTED_SOUNDNESS_TECHNIQUES
    if unexpected:
        examples_text = ", ".join(f"{technique}: {examples[technique]}" for technique in sorted(unexpected))
        raise AssertionError(f"Soundness oracle covered new techniques; update expected coverage: {examples_text}")
    progress(f"soundness oracle covered {len(coverage)} techniques")


def test_representative_puzzle_fixtures() -> None:
    solver = SudokuSolver(strategy="fastest")
    for path in puzzle_fixture_subset(REPRESENTATIVE_PUZZLE_NAMES):
        progress(f"fastest strategy representative-fixture solve {path.name}")
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


@pytest.mark.slow
def test_technique_soundness_oracle_all_fixtures() -> None:
    """Run the soundness oracle across every puzzle fixture."""
    coverage: Counter[str] = Counter()
    examples: dict[str, str] = {}

    for path in puzzle_fixtures():
        progress(f"full soundness oracle validating {path.name}")
        state = SudokuState.from_board(path.read_text(encoding="utf-8"))
        solver = SoundnessCheckingSolver(path.name, strategy="human")
        result, _ = solver.solve_with_search(state, explain=False)
        if result is None:
            raise AssertionError(f"Expected {path} to solve while running soundness oracle")
        coverage.update(solver.soundness_coverage)
        for technique, example in solver.soundness_examples.items():
            examples.setdefault(technique, example)

    missing = EXPECTED_SOUNDNESS_TECHNIQUES - set(coverage)
    if missing:
        counts = ", ".join(f"{technique}={coverage[technique]}" for technique in sorted(coverage))
        raise AssertionError(
            f"Full soundness oracle did not cover expected techniques {sorted(missing)}. "
            f"Covered counts: {counts}"
        )

    unexpected = set(coverage) - EXPECTED_SOUNDNESS_TECHNIQUES
    if unexpected:
        examples_text = ", ".join(f"{technique}: {examples[technique]}" for technique in sorted(unexpected))
        raise AssertionError(f"Full soundness oracle covered new techniques; update expected coverage: {examples_text}")


@pytest.mark.slow
def test_all_puzzle_fixtures() -> None:
    fixtures = puzzle_fixtures()
    if len(fixtures) != 154:
        raise AssertionError(f"Expected 154 puzzle fixtures in {PUZZLE_DIR}, got {len(fixtures)}")

    solver = SudokuSolver(strategy="fastest")
    for path in fixtures:
        progress(f"fastest strategy full-fixture solve {path.name}")
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
