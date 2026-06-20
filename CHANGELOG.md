# Changelog

All notable changes to this project will be documented in this file.

This project follows a simple pre-1.0 changelog style. Dates use `YYYY-MM-DD`.

## Unreleased

### Added

- GitHub Actions CI for regular checks and benchmark smoke validation.
- Scheduled and manually runnable slow-test workflow for full fixture validation.
- Dependabot configuration for GitHub Actions and Python dependency updates.
- Package installation metadata and `sudoku-solver` console script.
- MIT license.
- Public repository support docs and issue templates.

### Changed

- Python support floor is Python 3.9.
- Development installation now uses the package `dev` extra.
- Formatting ownership moved from Black to Ruff.

### Removed

- Black development dependency and Black-specific configuration.
