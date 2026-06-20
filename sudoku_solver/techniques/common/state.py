"""Mutable Sudoku state backed by candidate bitmasks."""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

from .bitmask import ALL_DIGITS_MASK, bit, bit_count, digits_from_mask, is_single, single_digit
from .grid import PEERS, i_to_rc, rc_to_i
from .moves import Move
from .simulation import candidates_consistency_ok


class SudokuState:
    """Mutable Sudoku grid state backed by 81 candidate bitmasks.

    `place_digit()` and `eliminate_digit()` update candidates and propagate
    solved singles to peer cells. `fixed_cells` tracks cells already committed
    as solved, while `given_cells` tracks original puzzle clues.
    """

    def __init__(
        self,
        candidates: Optional[List[int]] = None,
        fixed_cells: Optional[Iterable[int]] = None,
        given_cells: Optional[Iterable[int]] = None,
    ):
        self.candidates = candidates[:] if candidates else [ALL_DIGITS_MASK] * 81
        self.fixed_cells = set[int](fixed_cells or [])
        self.given_cells = set[int](given_cells or [])

    @classmethod
    def from_board(cls, board: Sequence[Sequence[int]] | str) -> "SudokuState":
        """Build a state from a 9x9 board or puzzle string.

        Args:
            board: A 9x9 sequence or string containing 81 digits, dots, or
                zeros. Dots and zeros represent empty cells.

        Raises:
            ValueError: If the board shape or givens are invalid.
        """
        state = cls()
        givens: List[Tuple[int, int]] = []

        if isinstance(board, str):
            chars = [ch for ch in board if ch in "1234567890."]
            if len(chars) != 81:
                raise ValueError("String puzzle must contain exactly 81 digits / dots / zeros.")
            for cell, ch in enumerate[str](chars):
                if ch in "123456789":
                    givens.append((cell, int(ch)))
        else:
            if len(board) != 9 or any(len(row) != 9 for row in board):
                raise ValueError("Board must be 9x9.")
            for row in range(9):
                for col in range(9):
                    value = board[row][col]
                    if value:
                        if not 1 <= value <= 9:
                            raise ValueError("Board values must be digits 1..9, 0, or falsey empties.")
                        givens.append((rc_to_i(row, col), value))

        for cell, digit in givens:
            if state.candidates[cell] != ALL_DIGITS_MASK:
                raise ValueError("Invalid Sudoku givens.")
            state.candidates[cell] = bit(digit)
            state.fixed_cells.add(cell)
            state.given_cells.add(cell)

        for cell, digit in givens:
            digit_mask = bit(digit)
            for peer in PEERS[cell]:
                peer_mask = state.candidates[peer]
                if peer_mask == digit_mask:
                    raise ValueError("Invalid Sudoku givens.")
                if peer_mask & digit_mask:
                    state.candidates[peer] = peer_mask & ~digit_mask

        if not state.consistency_ok():
            raise ValueError("Invalid Sudoku givens.")

        return state

    def clone(self) -> "SudokuState":
        """Return a copy suitable for speculative solving."""
        return SudokuState(self.candidates, self.fixed_cells, self.given_cells)

    def solved(self) -> bool:
        """Return whether every cell is solved to one digit."""
        return all(is_single(mask) for mask in self.candidates)

    def board(self) -> List[List[int]]:
        """Return the current solved digits as a 9x9 integer grid."""
        out = [[0] * 9 for _ in range(9)]
        for cell, mask in enumerate[int](self.candidates):
            if is_single(mask):
                row, col = i_to_rc(cell)
                out[row][col] = single_digit(mask)
        return out

    def pretty(self) -> str:
        """Return a simple text rendering of solved digits and empty cells."""
        lines: list[str] = []
        for row in range(9):
            if row and row % 3 == 0:
                lines.append("-" * 21)
            row_parts: list[str] = []
            for col in range(9):
                if col and col % 3 == 0:
                    row_parts.append("|")
                cell = rc_to_i(row, col)
                row_parts.append(str(single_digit(self.candidates[cell])) if is_single(self.candidates[cell]) else ".")
            lines.append(" ".join(row_parts))
        return "\n".join(lines)

    def candidate_mask(self, cell: int) -> int:
        """Return the candidate bitmask for one cell."""
        return self.candidates[cell]

    def candidate_digits(self, cell: int) -> List[int]:
        """Return candidate digits for one cell."""
        return digits_from_mask(self.candidates[cell])

    def can_place(self, cell: int, digit: int) -> bool:
        """Return whether a digit is still a candidate for a cell."""
        return bool(self.candidates[cell] & bit(digit))

    def is_bivalue(self, cell: int) -> bool:
        return bit_count(self.candidates[cell]) == 2

    def is_trivalue(self, cell: int) -> bool:
        return bit_count(self.candidates[cell]) == 3

    def consistency_ok(self) -> bool:
        """Return whether the current candidates satisfy Sudoku invariants."""
        return candidates_consistency_ok(self.candidates)

    def eliminate_digit(self, cell: int, digit: int) -> bool:
        """Remove one candidate and propagate if the cell becomes solved."""
        digit_mask = bit(digit)
        current_mask = self.candidates[cell]

        if not (current_mask & digit_mask):
            return True  # already absent

        new_mask = current_mask & ~digit_mask
        if new_mask == 0:
            return False

        self.candidates[cell] = new_mask

        if is_single(new_mask):
            fixed_digit = single_digit(new_mask)
            fixed_mask = bit(fixed_digit)
            self.fixed_cells.add(cell)

            for peer in PEERS[cell]:
                if self.candidates[peer] & fixed_mask:
                    if not self.eliminate_digit(peer, fixed_digit):
                        return False

        return True

    def place_digit(self, cell: int, digit: int) -> bool:
        """Place a digit in a cell and remove it from all peers."""
        if not self.can_place(cell, digit):
            return False

        current_digits = self.candidate_digits(cell)
        for candidate_digit in current_digits:
            if candidate_digit != digit:
                if not self.eliminate_digit(cell, candidate_digit):
                    return False

        for peer in PEERS[cell]:
            if self.can_place(peer, digit):
                if not self.eliminate_digit(peer, digit):
                    return False

        self.fixed_cells.add(cell)
        return True

    def apply_move(self, move: Move) -> bool:
        """Apply placements first, then eliminations, and validate state."""
        for p in move.placements:
            if not self.place_digit(p.cell, p.digit):
                return False

        for e in move.eliminations:
            if not self.eliminate_digit(e.cell, e.digit):
                return False

        return self.consistency_ok()
