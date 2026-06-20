# Developer Notes

This document records the structure and conventions used while building the solver. It is intended for maintainers adding techniques, changing move selection, or refactoring shared solver code.

## Design Goals

The project favors human-readable logical solving first, with search as a fallback. Techniques should return explainable `Move` objects, and the solver should be able to replay those moves into detailed progress steps without hiding candidate propagation.

The code is organized to keep the command-line interface thin, the library API importable, and solving techniques independent enough to test directly. Shared behavior belongs in `sudoku_solver/techniques/common.py` when it is used by multiple techniques or by both techniques and the solver.

## Code Structure

`sudoku.py`
: Compatibility entry point that delegates to the CLI module.

`cli.py`
: Argument parsing, file/string puzzle loading, output selection, and process-level error handling.

`sudoku_solver/solver.py`
: Solver orchestration. It selects techniques, records timing, scores moves, applies logical solving, and falls back to MRV search when enabled.

`sudoku_solver/strategies.py`
: Strategy definitions and technique orderings.

`sudoku_solver/explanation.py`
: Replay logic that expands a selected move into display-ready steps, including propagation and implied naked singles.

`sudoku_solver/visualization.py`
: Text and ANSI progress rendering.

`sudoku_solver/techniques/common.py`
: Shared Sudoku model, grid topology, typed utility helpers, move dataclasses, candidate simulation, and the `Technique` base class.

`sudoku_solver/techniques/*.py`
: Logical technique implementations grouped by family: basics, fish, chains, wings, uniqueness, ALS, and miscellaneous techniques.

`test/`
: In-process CLI tests, technique fixture tests, puzzle fixture tests, visualization tests, timing tests, and benchmark checks.

## Solver Flow

1. A puzzle is parsed into `SudokuState`, whose 81 cells are represented as candidate bitmasks.
2. `SudokuSolver.next_move()` asks techniques for available moves in strategy order.
3. `_best_move()` scores candidate moves by immediate board impact within a single technique result set.
4. `SudokuState.apply_move()` applies placements before eliminations, propagating solved singles to peers.
5. `explanation_steps()` replays the before/after state to show placements, eliminations, propagation, and implied naked singles.
6. If logical solving stalls and search is enabled, MRV backtracking tries the cell with the fewest candidates.

The solver keeps timing in `TechniqueTiming`. A technique run is counted when `find_moves()` is called; a technique use is counted only when one of its moves is selected. Propagation and implied naked singles are also recorded when they appear in detailed replay.

## Technique Contract

Each technique subclasses `Technique` and implements:

```python
def find_moves(self, state: SudokuState) -> List[Move]:
    ...
```

Techniques should inspect `state` and return possible `Move` objects without mutating the state. A move should include:

- `technique`: stable display name.
- `difficulty`: relative human-style difficulty used for deterministic scoring.
- `reason`: concise explanation suitable for CLI output.
- `placements` and/or `eliminations`: the actual board change.
- `cause_cells`: cells that justify or visualize the move.

Prefer returning all reasonable moves found by a technique. The solver decides which move to use when multiple moves are available.

## Shared Helpers

Use `UnitCandidateCache` when a technique repeatedly asks where a digit can appear in many units. `SudokuState` is mutable, so create the cache inside one `find_moves()` call and discard it afterward.

Use `shared_peer_eliminations()` for common-peer candidate removals, and `elimination_key()` for deduplication keys. This keeps tuple-key construction consistent and typed.

Use shared structural aliases from `common.py` when a tuple shape appears in more than one module. Current shared aliases include `CellGroup`, `CellPair`, `CellDigit`, `IndexDigit`, `IndexedCellGroup`, `MaskTransition`, and `EliminationKey`.

Use `pair_combinations()`, `sized_combinations()`, and `zip_pairs()` instead of direct `itertools.combinations()` or `zip()` when the iterator shape matters to type checking. The casts are centralized in `common.py`.

Use `apply_move_to_candidates()`, `place_digit_in_candidates()`, `eliminate_digit_from_candidates()`, and `candidates_consistency_ok()` for local candidate-mask simulation. These helpers are shared by move scoring and Nishio-style speculative checks so behavior stays aligned with `SudokuState` propagation.

## Candidate Bitmask Rules

Candidate masks use bit 0 for digit 1 through bit 8 for digit 9. Use helpers instead of open-coding bit operations where possible:

- `bit(digit)` for one digit.
- `bits(mask)` for iteration.
- `digits_from_mask(mask)` when a list is useful.
- `is_single(mask)` and `single_digit(mask)` for solved cells.
- `bit_count(mask)` for Python-version-compatible population counts.

Do not use `int.bit_count()` directly; the project keeps compatibility through the shared helper.

## Typing And Style

The code intentionally uses explicit collection typing in places where it improves IDE and mypy clarity. Examples include `set[int](...)`, `CellGroup(...)`, `enumerate[int](...)`, and typed helper wrappers around iterators.

Prefer:

- Explicit return types on public helpers and technique methods.
- Typed empty collections, for example `moves: List[Move] = []` or `seen: set[SeenKey] = set[SeenKey]()`.
- Shared aliases from `common.py` for repeated structural tuple shapes, such as groups of cells or `(cell, digit)` pairs.
- Technique-local `SeenKey` aliases for long deduplication key shapes that only make sense within one technique.
- Precise alias names for pairs. Use `CellPair` only for two cells, `CellDigit` for `(cell, digit)`, `IndexDigit` for `(index, digit)`, and `MaskTransition` for `(before_mask, after_mask)`.
- Shared helpers and aliases for repeated typed tuple construction.

Avoid:

- Repeating complex tuple constructors at call sites when a named helper or alias explains the intent.
- Creating local aliases for structural tuple shapes already covered by `common.py`.
- Using a broad alias such as `CellPair` for non-cell-pair data just because the runtime shape is `tuple[int, int]`.
- Over-defensive guards that hide impossible states instead of preserving solver invariants.
- Technique-to-technique dependencies unless the dependency is clearly technique-specific. General helpers should live in `common.py`.

## Comments And Docstrings

Use docstrings for modules, classes, public helpers, and technique classes. Technique docstrings should mention the corresponding page in `doc/` when one exists.

Use comments sparingly. Good comments explain a Sudoku concept, an invariant, or a non-obvious optimization. Avoid comments that restate the next line of code, such as “remove digit from peers” immediately before a loop that does exactly that.

Section comments are useful in large shared modules like `common.py`, where related constants, helpers, model classes, and base classes are grouped.

## Testing Guidelines

Run the standard checks after meaningful changes:

```sh
make lint
make typecheck
make test
```

Use focused tests while developing:

- Direct technique tests for new logic.
- Synthetic `.sdkc` candidate-state fixtures for patterns that are hard to reach from a puzzle.
- Online/reference fixtures when a known published example exists.
- CLI and visualization tests when output behavior changes.

When adding or changing a technique, update or add documentation in `doc/`, ensure the technique appears in an appropriate strategy when intended, and add at least one direct or fixture-backed test.

## Performance Guidelines

Most techniques run many times during solving, so avoid unnecessary `SudokuState.clone()` calls, repeated peer/unit scans, and repeated set conversions in hot paths.

Prefer:

- `UnitCandidateCache` for repeated unit candidate lookups.
- Precomputed module-level constants for stable grid relationships.
- Integer masks for frequent set-like cell operations in chain and fish logic.
- Local candidate-list simulation for speculative checks.

Benchmark changes that touch shared helpers or high-cost techniques:

```sh
python3 test/benchmark.py --strategy human --profile-slowest 10
```

Do not trade clear technique logic for micro-optimizations unless benchmark data shows the hot path matters.

## Adding A Technique

1. Add the implementation to the technique-family module that best matches the logic.
2. Keep `find_moves()` side-effect free.
3. Use shared helpers for peers, candidate positions, deduplication keys, and candidate simulation.
4. Add the technique to `strategies.py` if it should be used by a strategy.
5. Add documentation under `doc/` and link it from `doc/index.md` and `README.md` when appropriate.
6. Add direct tests or candidate-state fixtures.
7. Run lint, typecheck, and tests.

## Commit Hygiene

Keep commits focused by intent: tooling, documentation, fixtures, behavior changes, refactors, and optimizations should usually be separated. Commit messages in this repository use concise imperative summaries, for example `Simplify shared solver helpers`.
