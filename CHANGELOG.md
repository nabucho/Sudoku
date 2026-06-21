# Changelog

All notable changes to this project will be documented in this file.

Dates use `YYYY-MM-DD`.

## Unreleased

No changes yet.

## 1.1.0 - 2026-06-21

### Added

- CLI puzzle-bank sampling from difficulty files or a concrete puzzle-bank file, with configurable puzzle-bank directory support.
- Sudoku Exchange Puzzle Bank submodule documentation and contributor setup notes.

## 1.0.0 - 2026-06-20

### Added

- GitHub Actions CI for regular checks and benchmark smoke validation.
- Scheduled and manually runnable slow-test workflow for full fixture validation.
- Dependabot configuration for GitHub Actions and Python dependency updates.
- Package installation metadata and `sudoku-solver` console script.
- MIT license.
- Public repository support docs and issue templates.

### Changed

- Distribution package name changed to `nabucho-sudoku` to avoid a future PyPI name collision; the `sudoku-solver` CLI command and `sudoku_solver` import package are unchanged.
- Python support floor is Python 3.9.
- Development installation now uses the package `dev` extra.
- Formatting ownership moved from Black to Ruff.

### Removed

- Black development dependency and Black-specific configuration.
