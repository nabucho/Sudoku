# Sudoku Solver

A Python Sudoku solver with human-style logical techniques, MRV backtracking, step-by-step explanations, colored progress rendering, timing statistics, tests, and benchmark tooling.

The solver accepts puzzles as an 81-character string or a text file. Empty cells can be written as `.` or `0`; whitespace and other non-puzzle characters are ignored.

## Quick Start

Run the default puzzle:

```sh
python3 sudoku.py
```

Solve a puzzle from a file:

```sh
python3 sudoku.py --file test/puzzles/hard_01
```

Solve an inline puzzle string:

```sh
python3 sudoku.py "...8....3..8.61...14.37..2...4.8...7...7...4.9.6.5..1.2......9..1.......5......3."
```

Print text steps without progress boards:

```sh
python3 sudoku.py --file test/puzzles/diabolical_01 --no-progress --no-pause
```

Run the automated tests:

```sh
python3 -m pytest
```

Run benchmark timing:

```sh
python3 test/benchmark.py --strategy human --profile-slowest 10
```

## Development

Install development tools:

```sh
make install-dev
```

Common checks:

```sh
make test
make coverage
make typecheck
make lint
make check
```

Coverage reports use `coverage.py`; `make coverage` prints a terminal report and `make coverage-html` writes `htmlcov/`. Type checking uses `mypy` with project settings from `pyproject.toml`.

See [Developer Notes](doc/developer-notes.md) for code structure, solver flow, style guidelines, and maintenance conventions.

## CLI Usage

```text
python3 sudoku.py [PUZZLE] [--file PATH] [--strategy STRATEGY] [--step-style STYLE]
                  [--logic-only] [--no-steps] [--no-progress] [--no-color] [--no-pause]
```

## Library Usage

Import `SudokuSolver` from the library module when using the solver from Python code:

```python
from sudoku_solver.solver import SudokuSolver
from sudoku_solver.techniques.common import SudokuState

state = SudokuState.from_board("..." * 27)
solver = SudokuSolver(strategy="human")
result, steps = solver.solve_with_search(state)
```

## Parameters

`PUZZLE`
: Optional 81-cell puzzle string. Use `.` or `0` for empty cells.

`-f, --file PATH`
: Read the puzzle from a text file. Use either `PUZZLE` or `--file`, not both.

`--strategy {human,fewest-steps,fastest,balanced,search-first}`
: Select how moves are chosen. Defaults to `human`.

`--logic-only`
: Use logical techniques only. If logic gets stuck, the solver exits with `No solution found.` This cannot be combined with `--strategy search-first`.

`--step-style {detailed,grouped,batched}`
: Select how explanation steps are grouped. Defaults to `detailed`.

`--no-steps`
: Print only the original and solved boards. Timing summary is still printed.

`--no-progress`
: Print compact text step lines instead of a colored progress board after each step.

`--no-color`
: Disable ANSI colors in progress output.

`--no-pause`
: Do not wait for a key press after each progress step. Interactive progress can also be stopped with `q` or `Ctrl+C`.

## Step Styles

`detailed`
: Shows individual placements, eliminations, and propagation steps.

`grouped`
: Groups consecutive naked singles while keeping other moves separate.

`batched`
: Groups consecutive moves that use the same technique.

## Strategies

`human`
: Uses the full ordered set of logical techniques, from simple singles through advanced chain and uniqueness methods. If logic is exhausted, search is used unless `--logic-only` is set.

`fewest-steps`
: Evaluates available logical moves and selects the one with the highest immediate impact.

`fastest`
: Uses a small set of cheap techniques before search: Hidden Single, Naked Single, Naked Pair, Locked Candidates, and Hidden Pair.

`balanced`
: Uses cheap techniques plus selected wing techniques to avoid guesses more often while staying faster than the full `human` strategy.

`search-first`
: Starts directly with MRV backtracking. This is useful for fast solving without human-style logical explanations.

## Techniques

The solver implements the techniques below. The `human` and `fewest-steps` strategies can use the full logical set, `fastest` and `balanced` use smaller subsets, and `search-first` starts with MRV backtracking. See [Technique Documentation](doc/index.md) for one page per implemented logical technique with references to HoDoKu, SudokuWiki, and Sudopedia.

[`Naked Single`](doc/naked-single.md)
: Places a digit when a cell has only one candidate.

[`Hidden Single`](doc/hidden-single.md)
: Places a digit when it has only one possible cell in a row, column, or box.

[`Locked Candidates`](doc/locked-candidates.md)
: Removes candidates using pointing and claiming interactions between boxes and rows or columns.

Naked Subsets
: [Naked Pair](doc/naked-subsets.md), [Naked Triple](doc/naked-subsets.md), and [Naked Quad](doc/naked-subsets.md) remove digits when a set of cells contains exactly the same number of candidates.

Hidden Subsets
: [Hidden Pair](doc/hidden-subsets.md), [Hidden Triple](doc/hidden-subsets.md), and [Hidden Quad](doc/hidden-subsets.md) remove extra candidates when a set of digits is confined to the same set of cells.

Fish
: Uses [X-Wing](doc/x-wing.md), [Swordfish](doc/swordfish.md), and [Jellyfish](doc/jellyfish.md) patterns to remove candidates from intersecting rows or columns.

Finned Fish
: Handles [Finned X-Wing](doc/finned-x-wing.md), [Finned Swordfish](doc/finned-swordfish.md), and [Finned Jellyfish](doc/finned-jellyfish.md) patterns where a fin restricts eliminations.

Coloring
: [Simple Coloring](doc/simple-coloring.md) and [Multi-Coloring](doc/multi-coloring.md) color conjugate links for one digit to find contradictions or shared eliminations.

Single-Digit Chains
: [Skyscraper](doc/skyscraper.md), [Two-String Kite](doc/two-string-kite.md), [Turbot Fish](doc/turbot-fish.md), and [Empty Rectangle](doc/empty-rectangle.md) use strong links and common peers to eliminate candidates.

Wings And Bivalue Chains
: [XY-Wing](doc/xy-wing.md), [XYZ-Wing](doc/xyz-wing.md), [W-Wing](doc/w-wing.md), [XY-Chain](doc/xy-chain.md), and [Remote Pairs](doc/remote-pairs.md) use bivalue or trivalue candidate relationships.

Uniqueness
: [Unique Rectangle Type 1](doc/unique-rectangle-type-1.md), [Type 2](doc/unique-rectangle-type-2.md), [Type 3](doc/unique-rectangle-type-3.md), [Type 4](doc/unique-rectangle-type-4.md), [Avoidable Rectangle](doc/avoidable-rectangle.md), and [BUG+1](doc/bug-plus-one.md) avoid deadly patterns or non-unique solutions.

Subset Counting
:: [Sue de Coq](doc/sue-de-coq.md) eliminates candidates by combining a box-line intersection with companion cells from the same line and box.

Almost Locked Sets
: [ALS-XZ](doc/als-xz.md) and [ALS-Wing](doc/als-wing.md) eliminate candidates using restricted common digits.

Alternating Inference Chains
: [AIC](doc/aic.md), [X-Chain](doc/x-chain.md), [Grouped AIC](doc/grouped-aic.md), and [Grouped X-Chain](doc/grouped-x-chain.md) use strong and weak links between candidate nodes.

[`Nishio`](doc/nishio.md)
: Tests a candidate logically and eliminates it if assuming it leads to contradiction.

Search
: MRV backtracking is available as the fallback for non-`--logic-only` runs and as the first step of the `search-first` strategy. It is reported as `Guess` in step output rather than as a human logical technique.

## Progress Rendering

When progress output is enabled, the board shows a 3x3 candidate mini-grid inside unsolved cells.

Color legend:

- Original clues are bold white.
- Solved values are green.
- Current-step selections use a green background.
- Candidate changes use a blue background.
- Elimination source cells use a yellow background.
- Eliminated candidates are red.

## Timing Summary

Each technique call is timed in milliseconds. At the end of a solve, the timing summary reports:

- how many times a technique was used;
- how many times it was attempted;
- found percentage, meaning attempted runs that returned at least one candidate move;
- total elapsed time;
- average elapsed time.

## Benchmarking

`test/benchmark.py` benchmarks strategies across all puzzle fixtures under `test/puzzles/`.

Examples:

```sh
python3 test/benchmark.py
python3 test/benchmark.py --strategy fastest
python3 test/benchmark.py --strategy human --strategy balanced
python3 test/benchmark.py --strategy fewest-steps --profile-buckets
python3 test/benchmark.py --profile-slowest 20
```

Benchmark options:

`--strategy STRATEGY`
: Benchmark one strategy. Can be passed more than once.

`--profile-slowest N`
: Print the `N` slowest per-puzzle technique timing rows across selected strategies.

`--profile-buckets`
: Print aggregate wall-time buckets for technique discovery, move scoring, applying moves, and benchmark/solver overhead.

## Project Layout

`sudoku.py`
: Thin compatibility wrapper that keeps `python3 sudoku.py` working.

`cli.py`
: Command-line parser, input handling, and terminal output orchestration.

`sudoku_solver/solver.py`
: Clean library API containing `SudokuSolver`.

`sudoku_solver/strategies.py`
: Strategy-to-technique ordering.

`sudoku_solver/explanation.py`
: Replay logic that expands solver moves into explanation steps.

`sudoku_solver/visualization.py`
: Text and colored progress rendering.

`pyproject.toml`
: Project metadata plus Black, Ruff, coverage, mypy, and pytest configuration.

`requirements-dev.txt`
: Development tool dependencies for formatting, linting, coverage, and type checking.

`Makefile`
: Common development commands for tests, coverage, type checking, linting, formatting, and cleanup.

`sudoku_solver/techniques/`
: Human-style solving technique implementations and shared model helpers.

`test/run_tests.py`
: Pytest-based automated tests.

`test/benchmark.py`
: Timing and profiling script.
