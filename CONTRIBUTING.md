# Contributing

Thanks for helping improve the Sudoku solver. Contributions are welcome when they preserve correctness, explainability, and maintainability.

## Development Setup

Use Python 3.9 or newer.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
```

Run the solver from the installed console script or compatibility wrapper:

```sh
.venv/bin/sudoku-solver --file test/puzzles/hard_01 --no-progress --no-pause
python3 sudoku.py --file test/puzzles/hard_01 --no-progress --no-pause
```

## Quality Gates

Run the regular checks before opening a pull request:

```sh
make check PYTHON=.venv/bin/python
```

For broad solver changes, strategy-order changes, shared-helper changes, or release preparation, also run:

```sh
make test-all PYTHON=.venv/bin/python
```

Formatting and import cleanup are handled by Ruff:

```sh
make format PYTHON=.venv/bin/python
make format-check PYTHON=.venv/bin/python
```

## Technique Changes

When adding or changing a solving technique:

- keep `find_moves()` side-effect free;
- return `Move` objects with clear reasons, difficulty, placements or eliminations, and cause cells where useful;
- add or update the matching page in `doc/`;
- add a synthetic `.sdkc` fixture for isolated coverage;
- add online/reference fixtures when preserving a known external example;
- run focused tests with `pytest test/run_tests.py -k synthetic` and broader checks when the behavior affects solving paths.

Use `doc/developer-notes.md` for the full technique contract, shared-helper guidance, and testing strategy.

## Fixtures

Synthetic fixtures under `test/synthetic/` should target one technique directly and state the expected placements or eliminations. Online fixtures under `test/online/` should preserve source references where possible. Full puzzle fixtures under `test/puzzles/` should include provenance in `test/PUZZLE_SOURCES.md`.

## Performance Changes

Use benchmark data before optimizing. For high-cost technique work, start with:

```sh
python3 test/benchmark.py --strategy human --profile-slowest 10 --profile-buckets
```

Prefer small, measurable changes that preserve move ordering and explanations.

## Pull Requests

Keep pull requests focused. Include:

- a concise summary of the behavioral or tooling change;
- tests run;
- any intentionally skipped slow checks;
- screenshots or command output snippets only when they clarify user-facing changes.
