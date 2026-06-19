"""Compatibility wrapper for the Sudoku solver library and CLI.

Import `SudokuSolver` from `sudoku_solver.solver` for the clean library API. This module
keeps `from sudoku import SudokuSolver` and `python3 sudoku.py` working for
existing users.
"""

from __future__ import annotations

import sys

from sudoku_solver.solver import SudokuSolver

__all__ = ["SudokuSolver"]


if __name__ == "__main__":
    from cli import main

    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130)
    except BrokenPipeError:
        raise SystemExit(1)
