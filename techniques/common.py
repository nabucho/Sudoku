from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple


# ============================================================
# Bitmask helpers
# ============================================================

ALL_DIGITS_MASK = 0x1FF  # bits 0..8 => digits 1..9


def bit(d: int) -> int:
    return 1 << (d - 1)


def bits(mask: int) -> Iterable[int]:
    d = 1
    while mask:
        if mask & 1:
            yield d
        mask >>= 1
        d += 1


def bit_count(mask: int) -> int:
    count = 0
    while mask:
        count += mask & 1
        mask >>= 1
    return count


def is_single(mask: int) -> bool:
    return mask != 0 and (mask & (mask - 1)) == 0


def single_digit(mask: int) -> int:
    """Valid only if is_single(mask) is True."""
    return mask.bit_length()


def digits_from_mask(mask: int) -> List[int]:
    return list(bits(mask))


# ============================================================
# Grid topology
# ============================================================

ROWS = range(9)
COLS = range(9)


def rc_to_i(r: int, c: int) -> int:
    return r * 9 + c


def i_to_rc(i: int) -> Tuple[int, int]:
    return divmod(i, 9)


def cell_text(cell: int) -> str:
    r, c = i_to_rc(cell)
    return f"r{r+1}c{c+1}"


ROW_UNITS = [[rc_to_i(r, c) for c in COLS] for r in ROWS]
COL_UNITS = [[rc_to_i(r, c) for r in ROWS] for c in COLS]
BOX_UNITS = [
    [
        rc_to_i(r, c)
        for r in range(br * 3, br * 3 + 3)
        for c in range(bc * 3, bc * 3 + 3)
    ]
    for br in range(3)
    for bc in range(3)
]
ALL_UNITS = ROW_UNITS + COL_UNITS + BOX_UNITS


def unit_text(unit_index: int) -> str:
    if unit_index < 9:
        return f"row {unit_index + 1}"
    if unit_index < 18:
        return f"column {unit_index - 8}"
    return f"box {unit_index - 17}"

CELL_UNITS: List[List[List[int]]] = [[] for _ in range(81)]
for unit in ALL_UNITS:
    for cell in unit:
        CELL_UNITS[cell].append(unit)

PEERS: List[set[int]] = []
for i in range(81):
    s = set()
    for unit in CELL_UNITS[i]:
        s.update(unit)
    s.discard(i)
    PEERS.append(s)

ROW_OF = [i // 9 for i in range(81)]
COL_OF = [i % 9 for i in range(81)]
BOX_OF = [((i // 9) // 3) * 3 + ((i % 9) // 3) for i in range(81)]


# ============================================================
# Move model
# ============================================================

@dataclass(frozen=True)
class Placement:
    cell: int
    digit: int


@dataclass(frozen=True)
class Elimination:
    cell: int
    digit: int


def placement_text(placement: Placement) -> str:
    return f"{cell_text(placement.cell)}={placement.digit}"


def elimination_text(elimination: Elimination) -> str:
    return f"{cell_text(elimination.cell)}!={elimination.digit}"


@dataclass
class Move:
    technique: str
    reason: str
    placements: List[Placement] = field(default_factory=list)
    eliminations: List[Elimination] = field(default_factory=list)
    difficulty: int = 0
    after_candidates: Optional[List[int]] = field(default=None, repr=False)
    changed_cells: List[int] = field(default_factory=list, repr=False)
    cause_cells: List[int] = field(default_factory=list, repr=False)

    def summary(self) -> str:
        if self.reason.startswith(f"{self.technique}:"):
            return self.reason
        return f"{self.technique}: {self.reason}"


# ============================================================
# Sudoku state
# ============================================================

class SudokuState:
    """
    Stores candidates as bitmasks (81 cells).
    Mutation methods:
      - place_digit(cell, digit)
      - eliminate_digit(cell, digit)

    place_digit / eliminate_digit handle peer propagation automatically.
    """

    def __init__(
        self,
        candidates: Optional[List[int]] = None,
        fixed_cells: Optional[Iterable[int]] = None,
        given_cells: Optional[Iterable[int]] = None,
    ):
        self.candidates = candidates[:] if candidates else [ALL_DIGITS_MASK] * 81
        self.fixed_cells = set(fixed_cells or [])
        self.given_cells = set(given_cells or [])

    @classmethod
    def from_board(cls, board: Sequence[Sequence[int]] | str) -> "SudokuState":
        state = cls()
        givens: List[Tuple[int, int]] = []

        if isinstance(board, str):
            chars = [ch for ch in board if ch in "1234567890."]
            if len(chars) != 81:
                raise ValueError("String puzzle must contain exactly 81 digits / dots / zeros.")
            for i, ch in enumerate(chars):
                if ch in "123456789":
                    givens.append((i, int(ch)))
        else:
            if len(board) != 9 or any(len(row) != 9 for row in board):
                raise ValueError("Board must be 9x9.")
            for r in range(9):
                for c in range(9):
                    v = board[r][c]
                    if v:
                        if not 1 <= v <= 9:
                            raise ValueError("Board values must be digits 1..9, 0, or falsey empties.")
                        givens.append((rc_to_i(r, c), v))

        for cell, digit in givens:
            if state.candidates[cell] != ALL_DIGITS_MASK:
                raise ValueError("Invalid Sudoku givens.")
            state.candidates[cell] = bit(digit)
            state.fixed_cells.add(cell)
            state.given_cells.add(cell)

        for cell, digit in givens:
            dmask = bit(digit)
            for peer in PEERS[cell]:
                peer_mask = state.candidates[peer]
                if peer_mask == dmask:
                    raise ValueError("Invalid Sudoku givens.")
                if peer_mask & dmask:
                    state.candidates[peer] = peer_mask & ~dmask

        if not state.consistency_ok():
            raise ValueError("Invalid Sudoku givens.")

        return state

    def clone(self) -> "SudokuState":
        return SudokuState(self.candidates, self.fixed_cells, self.given_cells)

    def solved(self) -> bool:
        return all(is_single(mask) for mask in self.candidates)

    def board(self) -> List[List[int]]:
        out = [[0] * 9 for _ in range(9)]
        for i, mask in enumerate(self.candidates):
            if is_single(mask):
                r, c = i_to_rc(i)
                out[r][c] = single_digit(mask)
        return out

    def pretty(self) -> str:
        lines = []
        for r in range(9):
            if r and r % 3 == 0:
                lines.append("-" * 21)
            row_parts = []
            for c in range(9):
                if c and c % 3 == 0:
                    row_parts.append("|")
                i = rc_to_i(r, c)
                row_parts.append(str(single_digit(self.candidates[i])) if is_single(self.candidates[i]) else ".")
            lines.append(" ".join(row_parts))
        return "\n".join(lines)

    def candidate_mask(self, cell: int) -> int:
        return self.candidates[cell]

    def candidate_digits(self, cell: int) -> List[int]:
        return digits_from_mask(self.candidates[cell])

    def can_place(self, cell: int, digit: int) -> bool:
        return bool(self.candidates[cell] & bit(digit))

    def is_bivalue(self, cell: int) -> bool:
        return bit_count(self.candidates[cell]) == 2

    def is_trivalue(self, cell: int) -> bool:
        return bit_count(self.candidates[cell]) == 3

    def consistency_ok(self) -> bool:
        # no empty cells
        if any(mask == 0 for mask in self.candidates):
            return False

        # each digit must have at least one possible place in each unit
        for unit in ALL_UNITS:
            seen_fixed = set()
            for cell in unit:
                mask = self.candidates[cell]
                if is_single(mask):
                    d = single_digit(mask)
                    if d in seen_fixed:
                        return False
                    seen_fixed.add(d)

            for d in range(1, 10):
                dmask = bit(d)
                if not any(self.candidates[cell] & dmask for cell in unit):
                    return False

        return True

    def eliminate_digit(self, cell: int, digit: int) -> bool:
        """
        Remove one candidate from a cell.
        If the cell becomes single, propagate that single to peers.
        """
        dmask = bit(digit)
        cur = self.candidates[cell]

        if not (cur & dmask):
            return True  # already absent

        new_mask = cur & ~dmask
        if new_mask == 0:
            return False

        self.candidates[cell] = new_mask

        if is_single(new_mask):
            fixed_digit = single_digit(new_mask)
            fixed_mask = bit(fixed_digit)
            self.fixed_cells.add(cell)

            # remove fixed_digit from all peers
            for peer in PEERS[cell]:
                if self.candidates[peer] & fixed_mask:
                    if not self.eliminate_digit(peer, fixed_digit):
                        return False

        return True

    def place_digit(self, cell: int, digit: int) -> bool:
        """
        Set cell to exactly one digit by removing all others,
        then remove that digit from peers.
        """
        if not self.can_place(cell, digit):
            return False

        cur_digits = self.candidate_digits(cell)
        for d in cur_digits:
            if d != digit:
                if not self.eliminate_digit(cell, d):
                    return False

        # ensure peers do not contain the placed digit
        for peer in PEERS[cell]:
            if self.can_place(peer, digit):
                if not self.eliminate_digit(peer, digit):
                    return False

        self.fixed_cells.add(cell)
        return True

    def apply_move(self, move: Move) -> bool:
        """
        Applies placements first, then eliminations.
        """
        for p in move.placements:
            if not self.place_digit(p.cell, p.digit):
                return False

        for e in move.eliminations:
            if not self.eliminate_digit(e.cell, e.digit):
                return False

        return self.consistency_ok()


# ============================================================
# Technique base
# ============================================================

class Technique:
    name: str = "Technique"
    difficulty: int = 0

    def find_moves(self, state: SudokuState) -> List[Move]:
        raise NotImplementedError

# ============================================================

