# Developer Notes

This document records the structure and conventions used while building the solver. It is intended for maintainers adding techniques, changing move selection, or refactoring shared solver code.

## Design Goals

The project favors human-readable logical solving first, with search as a fallback. Techniques should return explainable `Move` objects, and the solver should be able to replay those moves into detailed progress steps without hiding candidate propagation.

The code is organized to keep the command-line interface thin, the library API importable, and solving techniques independent enough to test directly. Shared behavior belongs in the `sudoku_solver/techniques/common/` package when it is used by multiple techniques or by both techniques and the solver.

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

`sudoku_solver/techniques/common/`
: Shared Sudoku model, grid topology, typed utility helpers, move dataclasses, candidate simulation, and the `Technique` base class. Its `__init__.py` is a compatibility facade for existing `sudoku_solver.techniques.common` imports.

`sudoku_solver/techniques/common/bitmask.py`
: Candidate mask helpers and precomputed 9-bit lookup tables.

`sudoku_solver/techniques/common/grid.py`
: Row, column, box, peer, and coordinate topology.

`sudoku_solver/techniques/common/moves.py`
: Move, placement, elimination, timing, and explanation-step dataclasses.

`sudoku_solver/techniques/common/simulation.py`
: Local candidate-list propagation and consistency helpers used by scoring and speculative checks.

`sudoku_solver/techniques/common/state.py`
: Mutable `SudokuState` implementation.

`sudoku_solver/techniques/common/queries.py`
: Candidate-position caches, strong links, shared-peer eliminations, and other state queries.

`sudoku_solver/techniques/common/types.py`, `iter_utils.py`, and `technique.py`
: Structural aliases, typed iterator wrappers, and the `Technique` base class.

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

The solver keeps timing in `TechniqueTiming`. A technique run is counted when `find_moves()` is called; a technique use is counted only when one of its moves is selected. The summary's `Found` percentage means runs that returned at least one candidate move, which can be higher than `Used` under strategies such as `fewest-steps` that scan many techniques and select only one move. Propagation and implied naked singles are also recorded when they appear in detailed replay.

`solve_logic()`, `solve_with_search()`, and `solve_search_first()` mutate the `SudokuState` passed to them. Callers that need to preserve the original candidate grid should pass a clone. Search uses MRV backtracking as a pragmatic completeness fallback; search steps are reported as `Guess` rather than as human techniques.

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
- `cause_cells`: cells that justify or visualize the move when the proof depends on source cells.
- `source_digit_roles`: optional per-cell/per-digit highlighting metadata for techniques where the displayed source digits matter.

Prefer returning all reasonable moves found by a technique. The solver decides which move to use when multiple moves are available.

There are a few intentional exceptions and limits:

- `NakedSingle` and `HiddenSingle` return the first forced placement they find. This keeps the most common solving loop cheap and predictable; detailed replay still shows propagation and implied singles that follow from the selected placement.
- Chain techniques cap search depth or emitted move count where unrestricted enumeration becomes expensive. These caps make interactive CLI behavior predictable but mean `--logic-only` can miss very long valid chains.
- Timing on a returned `Move` is discovery timing for the whole technique call, not a true per-move cost when a technique returns multiple alternatives.
- Uniqueness techniques assume a uniquely solvable puzzle. They are sound under the standard human-solver uniqueness convention, but they are not intended for arbitrary multi-solution grids.

## Shared Helpers

Use `UnitCandidateCache` when a technique repeatedly asks where a digit can appear in many units. `SudokuState` is mutable, so create the cache inside one `find_moves()` call and discard it afterward. This is used by singles, subsets, coloring, chains, AIC variants, and Unique Rectangle Type 4.

Use `shared_peer_eliminations()` for common-peer candidate removals, and `elimination_key()` for deduplication keys. This keeps tuple-key construction consistent and typed.

Use shared structural aliases from `common/types.py` when a tuple shape appears in more than one module. Current shared aliases include `CellGroup`, `CellPair`, `CellDigit`, `IndexDigit`, `IndexedCellGroup`, `MaskTransition`, and `EliminationKey`.

Use `pair_combinations()`, `sized_combinations()`, and `zip_pairs()` instead of direct `itertools.combinations()` or `zip()` when the iterator shape matters to type checking. The casts are centralized in `common/iter_utils.py`.

Use `apply_move_to_candidates()` when scoring a candidate `Move` without cloning a full `SudokuState`. Use `place_digit_in_candidates()` and `candidates_consistency_ok()` for Nishio-style speculative checks. `eliminate_digit_from_candidates()` is the low-level elimination primitive used by those helpers rather than a common direct technique API. Keeping local simulation on these helpers keeps move scoring, tests, and speculative checks aligned with `SudokuState` propagation.

## Candidate Bitmask Rules

Candidate masks use bit 0 for digit 1 through bit 8 for digit 9. Use helpers for digit-candidate masks and candidate interpretation:

- `bit(digit)` when constructing or testing a one-digit candidate mask. This is used heavily by `SudokuState`, candidate simulation, replay, wing techniques, and tests.
- `bits(mask)` for lightweight iteration when tuple/list conversion is not needed.
- `digits_from_mask(mask)` when a list is useful.
- `is_single(mask)` and `single_digit(mask)` for solved cells.
- `bit_count(mask)` for Python-version-compatible population counts.

Open-coded shifts are acceptable for structural masks that are not digit candidates, such as row/column line masks or cell-set masks in fish, ALS, and AIC code.

Do not use `int.bit_count()` directly; use `bit_count()` or `MASK_BIT_COUNTS` so behavior stays consistent with the current test environment and lookup-table optimizations.

For hot paths that receive normal 9-bit Sudoku masks, prefer the precomputed lookup tables:

- `MASK_DIGITS[mask]` when repeated digit iteration would allocate lists.
- `MASK_BIT_COUNTS[mask]` when filtering masks by size.
- `MASK_INDEXES[mask]` when translating row/column bitsets into indexes.

Keep the helper functions for public readability and for defensive behavior around unusual masks; use the tables in inner loops where benchmarks show the conversion cost matters.

## Soundness And Completeness

Correctness is checked at several levels:

- Synthetic `.sdkc` fixtures exercise each implemented technique in isolation.
- Online/reference fixtures exercise known examples from external Sudoku sources.
- `SoundnessCheckingSolver` validates emitted moves by asking whether the current branch still has a solution after applying the opposite constraint.
- Slow tests run the human-strategy oracle across every puzzle fixture and a separate full-corpus solve using the `fastest` strategy.

The soundness oracle validates branch-local move soundness, not full strategy completeness. A technique can be sound but still fail to find a harder or longer pattern because of ordering, search caps, or intentionally limited propagation. The oracle also depends on the backtracking solver as its truth source, so changes to search should be treated as high-risk and verified with the slow tests.

Representative soundness runs use a smaller puzzle set than the slow oracle so regular tests remain fast. When adding a technique, add a synthetic fixture first, then extend oracle coverage when a real puzzle path naturally exercises the technique or when a focused branch-state oracle test is practical.

## Typing And Style

The code intentionally uses explicit collection typing in places where it improves IDE and mypy clarity. Examples include `set[int](...)`, `CellGroup(...)`, `enumerate[int](...)`, and typed helper wrappers around iterators.

Prefer:

- Explicit return types on public helpers and technique methods.
- Typed empty collections, for example `moves: List[Move] = []` or `seen: set[SeenKey] = set[SeenKey]()`.
- Shared aliases from `common/types.py` for repeated structural tuple shapes, such as groups of cells or `(cell, digit)` pairs.
- Technique-local `SeenKey` aliases for long deduplication key shapes that only make sense within one technique.
- Precise alias names for pairs. Use `CellPair` only for two cells, `CellDigit` for `(cell, digit)`, `IndexDigit` for `(index, digit)`, and `MaskTransition` for `(before_mask, after_mask)`.
- Shared helpers and aliases for repeated typed tuple construction.

Avoid:

- Repeating complex tuple constructors at call sites when a named helper or alias explains the intent.
- Creating local aliases for structural tuple shapes already covered by `common/types.py`.
- Using a broad alias such as `CellPair` for non-cell-pair data just because the runtime shape is `tuple[int, int]`.
- Over-defensive guards that hide impossible states instead of preserving solver invariants.
- Technique-to-technique dependencies unless the dependency is clearly technique-specific. General helpers should live in `sudoku_solver/techniques/common/`.

## Comments And Docstrings

Use docstrings for modules, classes, public helpers, and technique classes. Technique docstrings should mention the corresponding page in `doc/` when one exists.

Use comments sparingly. Good comments explain a Sudoku concept, an invariant, or a non-obvious optimization. Avoid comments that restate the next line of code, such as “remove digit from peers” immediately before a loop that does exactly that.

Section comments are useful in larger shared modules, where related constants, helpers, model classes, and base classes are grouped.

## Testing Guidelines

The pytest suite lives in `test/run_tests.py`. It is intentionally layered rather than purely unit-test based, because Sudoku techniques are easiest to break in three different ways: a local pattern can be detected incorrectly, a correct move can be selected at the wrong point in a solve path, or a correct move can be explained/rendered incorrectly.

Run the standard checks after meaningful changes:

```sh
make lint
make typecheck
make test
```

Use `make test-all` before releases, broad refactors, strategy-order changes, search changes, or changes to shared candidate propagation. Regular `make test` skips tests marked `slow` so day-to-day feedback stays fast.

### Test Layers

The suite uses these layers:

- Direct technique tests for new logic.
- Candidate-state fixtures for isolated technique behavior.
- CLI tests that exercise argument parsing, strategy selection, output modes, and error handling.
- Visualization tests that check step grouping, ANSI styling, source-digit highlighting, and removed-candidate rendering.
- Timing and scoring tests that protect technique run/use semantics and `fewest-steps` selection behavior.
- Puzzle fixture tests that verify strategies can solve representative or full puzzle sets.
- Soundness oracle tests that validate logical moves against the current branch's solution space.
- Benchmark smoke tests that keep profiling output and timing buckets usable.

Direct tests are best for small invariants and regressions that can be expressed in code. Fixture tests are better for real Sudoku patterns because they preserve the exact candidate grid that made the pattern possible.

### Candidate Fixtures

Synthetic fixtures in `test/synthetic/` are candidate-grid snapshots designed to exercise one named technique in isolation. Each `.sdkc` file records the technique name, expected placements or eliminations, fixed/given metadata, and a 9x9 candidate grid. `test_synthetic_technique_fixtures()` also checks that each technique in `default_techniques()` has fixture coverage, so adding a technique should normally include a new synthetic fixture.

Online fixtures in `test/online/` use the same `.sdkc` format but are transcribed from public technique examples such as HoDoKu. Use them when there is a known external example worth preserving as a reference; use synthetic fixtures when the goal is focused regression coverage or a pattern is difficult to reach from a full puzzle.

Full puzzle fixtures in `test/puzzles/` exercise strategy integration. Regular tests use `REPRESENTATIVE_PUZZLE_NAMES`, a deliberately small set chosen to cover many techniques and common failure modes quickly. Slow tests run the full fixture corpus through the soundness oracle with `human` and through solve regression with `fastest`; treat them as pre-release coverage.

### Soundness Oracle

`SoundnessCheckingSolver` wraps normal solving and validates every emitted logical move. For a placement, it checks whether a solution still exists after removing that placed digit from the cell. For an elimination, it checks whether a solution still exists after forcing the eliminated digit into the cell. If the opposite constraint still allows a solution, the move was not logically forced on that branch.

The oracle is a soundness check, not a completeness proof. It can prove that emitted moves are safe, but it does not prove every possible human technique variant is implemented or that `--logic-only` will solve every puzzle. The oracle uses the backtracking search solver as its truth source, so changes to `solve_search_first()`, candidate propagation, or consistency validation should run the slow oracle tests.

Representative oracle tests intentionally cover fewer puzzle paths than the slow oracle. Keep `EXPECTED_SOUNDNESS_TECHNIQUES` aligned with the techniques naturally exercised by the representative set, and add comments or docs if a technique is fixture-only rather than branch-oracle covered.

### What To Run

Use focused commands while developing:

- `pytest test/run_tests.py -k synthetic` after changing a technique fixture or expected move signature.
- `pytest test/run_tests.py -k online` after changing behavior covered by external examples.
- `pytest test/run_tests.py -k soundness` after changing move generation, candidate propagation, or consistency checks.
- `pytest test/run_tests.py -k visualization` after changing explanation metadata or ANSI rendering.
- `python3 test/benchmark.py --strategy human --profile-slowest 10 --profile-buckets` after changing shared helpers, strategy order, or high-cost techniques.

When adding or changing a technique, update or add documentation in `doc/`, ensure the technique appears in an appropriate strategy when intended, and add at least one direct or fixture-backed test.

## Performance Guidelines

Most techniques run many times during solving, so avoid unnecessary `SudokuState.clone()` calls, repeated peer/unit scans, and repeated set conversions in hot paths.

Prefer:

- `UnitCandidateCache` for repeated unit candidate lookups.
- Precomputed module-level constants for stable grid relationships.
- Integer masks for frequent set-like cell operations in chain and fish logic.
- Local candidate-list simulation for speculative checks.
- Precomputed mask lookup tables for repeated 9-bit mask-to-digits, bit-count, or index conversion.
- Per-run caches or precomputed lists/maps for candidate positions, ALS groups, strong-link maps, or sorted adjacency lists when the data is scoped to one immutable state snapshot.

Benchmark changes that touch shared helpers or high-cost techniques:

```sh
python3 test/benchmark.py --strategy human --profile-slowest 10
```

Do not trade clear technique logic for micro-optimizations unless benchmark data shows the hot path matters.

The current strategy ordering and several implementations reflect benchmark-driven tradeoffs:

- `human-fast` skips expensive late techniques before search to improve default CLI latency while keeping broad human-style explanations.
- `human` keeps the complete explanatory technique set, including low-yield advanced methods, for users who prefer logic breadth over speed.
- `Grouped AIC`, `Nishio`, `Grouped X-Chain`, `Avoidable Rectangle`, and `ALS-XZ` are known high-cost areas. Optimize them with before/after benchmark evidence and keep their explanations stable.
- Prefer prefilters that avoid constructing expensive structures when a pattern is impossible over broad rewrites that obscure Sudoku logic.

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
