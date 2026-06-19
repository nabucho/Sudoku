from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple


# ============================================================
# Bitmask helpers
# ============================================================

ALL_DIGITS_MASK = 0x1FF  # bits 0..8 => digits 1..9
DIGIT_VALUES = range(1, 10)


def bit(digit: int) -> int:
    return 1 << (digit - 1)


def bits(mask: int) -> Iterable[int]:
    digit = 1
    while mask:
        if mask & 1:
            yield digit
        mask >>= 1
        digit += 1


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

ROW_INDICES = range(9)
COLUMN_INDICES = range(9)
CELL_INDICES = range(81)


def rc_to_i(row: int, col: int) -> int:
    return row * 9 + col


def i_to_rc(cell: int) -> Tuple[int, int]:
    return divmod(cell, 9)


def cell_text(cell: int) -> str:
    r, c = i_to_rc(cell)
    return f"r{r+1}c{c+1}"


def cells_text(cells: Iterable[int]) -> str:
    return ", ".join(cell_text(cell) for cell in cells)


def forced_cell_reason(cell: int, digit: int) -> str:
    return f"{cell_text(cell)} is forced to {digit}."


ROW_UNITS = [[rc_to_i(row, col) for col in COLUMN_INDICES] for row in ROW_INDICES]
COL_UNITS = [[rc_to_i(row, col) for row in ROW_INDICES] for col in COLUMN_INDICES]
BOX_UNITS = [
    [
        rc_to_i(row, col)
        for row in range(br * 3, br * 3 + 3)
        for col in range(bc * 3, bc * 3 + 3)
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

CELL_UNITS: List[List[List[int]]] = [[] for _ in CELL_INDICES]
for unit in ALL_UNITS:
    for cell in unit:
        CELL_UNITS[cell].append(unit)

PEERS: List[set[int]] = []
for cell in CELL_INDICES:
    peers = set()
    for unit in CELL_UNITS[cell]:
        peers.update(unit)
    peers.discard(cell)
    PEERS.append(peers)

ROW_OF = [cell // 9 for cell in CELL_INDICES]
COL_OF = [cell % 9 for cell in CELL_INDICES]
BOX_OF = [((cell // 9) // 3) * 3 + ((cell % 9) // 3) for cell in CELL_INDICES]


def cells_with_candidate(state: "SudokuState", unit: Sequence[int], digit: int) -> List[int]:
    return [cell for cell in unit if state.can_place(cell, digit)]


def bivalue_candidate_cells(state: "SudokuState") -> List[int]:
    return [cell for cell in CELL_INDICES if state.is_bivalue(cell)]


def trivalue_candidate_cells(state: "SudokuState") -> List[int]:
    return [cell for cell in CELL_INDICES if state.is_trivalue(cell)]


def unsolved_cells(state: "SudokuState") -> List[int]:
    return [cell for cell in CELL_INDICES if not is_single(state.candidate_mask(cell))]


def shared_peers(cells: Iterable[int]) -> set[int]:
    cells = list(cells)
    if not cells:
        return set()
    peers = PEERS[cells[0]].copy()
    for cell in cells[1:]:
        peers &= PEERS[cell]
    return peers


def shared_peer_eliminations(
    state: "SudokuState",
    cells: Iterable[int],
    digit: int,
    blocked: Iterable[int] = (),
) -> List["Elimination"]:
    blocked_cells = set(blocked)
    return [
        Elimination(cell, digit)
        for cell in sorted(shared_peers(cells) - blocked_cells)
        if state.can_place(cell, digit)
    ]


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


@dataclass
class TechniqueTiming:
    attempts: int = 0
    successes: int = 0
    used: int = 0
    total_ms: float = 0.0
    successful_ms: float = 0.0

    def record_run(self, elapsed_ms: float, successful: bool) -> None:
        self.attempts += 1
        self.total_ms += elapsed_ms
        if successful:
            self.successes += 1
            self.successful_ms += elapsed_ms

    def record_use(self) -> None:
        self.used += 1

    @property
    def average_ms(self) -> float:
        return self.total_ms / self.attempts if self.attempts else 0.0

    @property
    def success_percent(self) -> float:
        return (self.successes / self.attempts * 100.0) if self.attempts else 0.0


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
    cause_cells: List[int] = field(default_factory=list, repr=False)
    timing_ms: float = field(default=0.0, repr=False)

    def summary(self) -> str:
        if self.reason.startswith(f"{self.technique}:"):
            return self.reason
        return f"{self.technique}: {self.reason}"


@dataclass
class ExplanationStep:
    move: Move
    after_candidates: Optional[List[int]] = field(default=None, repr=False)
    changed_cells: List[int] = field(default_factory=list, repr=False)

    @property
    def technique(self) -> str:
        return self.move.technique

    @property
    def reason(self) -> str:
        return self.move.reason

    @property
    def placements(self) -> List[Placement]:
        return self.move.placements

    @property
    def eliminations(self) -> List[Elimination]:
        return self.move.eliminations

    @property
    def difficulty(self) -> int:
        return self.move.difficulty

    @property
    def cause_cells(self) -> List[int]:
        return self.move.cause_cells

    @property
    def timing_ms(self) -> float:
        return self.move.timing_ms

    def summary(self) -> str:
        return self.move.summary()


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
            for cell, ch in enumerate(chars):
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
        return SudokuState(self.candidates, self.fixed_cells, self.given_cells)

    def solved(self) -> bool:
        return all(is_single(mask) for mask in self.candidates)

    def board(self) -> List[List[int]]:
        out = [[0] * 9 for _ in range(9)]
        for cell, mask in enumerate(self.candidates):
            if is_single(mask):
                row, col = i_to_rc(cell)
                out[row][col] = single_digit(mask)
        return out

    def pretty(self) -> str:
        lines = []
        for row in range(9):
            if row and row % 3 == 0:
                lines.append("-" * 21)
            row_parts = []
            for col in range(9):
                if col and col % 3 == 0:
                    row_parts.append("|")
                cell = rc_to_i(row, col)
                row_parts.append(str(single_digit(self.candidates[cell])) if is_single(self.candidates[cell]) else ".")
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
                    digit = single_digit(mask)
                    if digit in seen_fixed:
                        return False
                    seen_fixed.add(digit)

            for digit in DIGIT_VALUES:
                digit_mask = bit(digit)
                if not any(self.candidates[cell] & digit_mask for cell in unit):
                    return False

        return True

    def eliminate_digit(self, cell: int, digit: int) -> bool:
        """
        Remove one candidate from a cell.
        If the cell becomes single, propagate that single to peers.
        """
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

        current_digits = self.candidate_digits(cell)
        for candidate_digit in current_digits:
            if candidate_digit != digit:
                if not self.eliminate_digit(cell, candidate_digit):
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

