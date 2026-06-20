"""Base class for logical Sudoku solving techniques."""

from __future__ import annotations

from typing import List

from .moves import Move
from .state import SudokuState


class Technique:
    """Base class for all logical Sudoku solving techniques."""

    name: str = "Technique"
    difficulty: int = 0

    def find_moves(self, state: SudokuState) -> List[Move]:
        """Return all moves this technique can currently find."""
        raise NotImplementedError
