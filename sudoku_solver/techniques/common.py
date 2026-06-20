"""Shared Sudoku model, grid topology, and technique helper utilities.

This module is intentionally dependency-light because every solving technique
uses it. Public helpers use row-major cell indices from 0 to 80 and candidate
bitmasks where bit 0 represents digit 1 and bit 8 represents digit 9.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Iterable, Iterator, List, Optional, Sequence, Tuple, TypeVar, cast

T = TypeVar("T")
U = TypeVar("U")
CellGroup = tuple[int, ...]
CellPair = tuple[int, int]
CellDigit = tuple[int, int]
SourceDigitRole = str
SourceDigitRoles = dict[CellDigit, SourceDigitRole]
IndexDigit = tuple[int, int]
IndexedCellGroup = tuple[int, CellGroup]
MaskTransition = tuple[int, int]

# ============================================================
# Bitmask helpers
# ============================================================

ALL_DIGITS_MASK = 0x1FF  # bits 0..8 => digits 1..9
DIGIT_VALUES = range(1, 10)


def bit(digit: int) -> int:
    """Return the candidate bitmask for a single Sudoku digit."""
    return 1 << (digit - 1)


def bits(mask: int) -> Iterable[int]:
    """Yield all digit values present in a candidate bitmask."""
    digit = 1
    while mask:
        if mask & 1:
            yield digit
        mask >>= 1
        digit += 1


def bit_count(mask: int) -> int:
    """Return the number of candidate digits present in a bitmask."""
    count = 0
    while mask:
        count += mask & 1
        mask >>= 1
    return count


def is_single(mask: int) -> bool:
    """Return whether a candidate bitmask contains exactly one digit."""
    return mask != 0 and (mask & (mask - 1)) == 0


def single_digit(mask: int) -> int:
    """Valid only if is_single(mask) is True."""
    return mask.bit_length()


def digits_from_mask(mask: int) -> List[int]:
    """Return all digits present in a candidate bitmask as a list."""
    return list[int](bits(mask))


# ============================================================
# Typed iteration helpers
# ============================================================

def pair_combinations(items: Iterable[T]) -> Iterator[tuple[T, T]]:
    """Return typed 2-item combinations from an iterable."""
    return cast(Iterator[tuple[T, T]], combinations(items, 2))


def sized_combinations(items: Iterable[T], size: int) -> Iterator[tuple[T, ...]]:
    """Return typed combinations for a runtime-selected combination size."""
    return cast(Iterator[tuple[T, ...]], combinations(items, size))


def zip_pairs(left: Iterable[T], right: Iterable[U]) -> Iterator[tuple[T, U]]:
    """Return typed pairs from two iterables."""
    return zip(left, right)


# ============================================================
# Grid topology
# ============================================================

ROW_INDICES = range(9)
COLUMN_INDICES = range(9)
CELL_INDICES = range(81)


def rc_to_i(row: int, col: int) -> int:
    """Convert zero-based row and column coordinates to a cell index."""
    return row * 9 + col


def i_to_rc(cell: int) -> Tuple[int, int]:
    """Convert a cell index to zero-based row and column coordinates."""
    return divmod(cell, 9)


def cell_text(cell: int) -> str:
    """Format a cell index as a human-readable coordinate, such as r1c1."""
    r, c = i_to_rc(cell)
    return f"r{r+1}c{c+1}"


def cells_text(cells: Iterable[int]) -> str:
    """Format multiple cell indices as comma-separated coordinates."""
    return ", ".join(cell_text(cell) for cell in cells)


def forced_cell_reason(cell: int, digit: int) -> str:
    """Return the standard explanation text for a forced placement."""
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
    """Format an ALL_UNITS index as row, column, or box text."""
    if unit_index < 9:
        return f"row {unit_index + 1}"
    if unit_index < 18:
        return f"column {unit_index - 8}"
    return f"box {unit_index - 17}"

CELL_UNITS: List[List[List[int]]] = [[] for _ in CELL_INDICES]
CELL_UNIT_INDICES: List[List[int]] = [[] for _ in CELL_INDICES]
for unit_index, unit in enumerate[List[int]](ALL_UNITS):
    for cell in unit:
        CELL_UNITS[cell].append(unit)
        CELL_UNIT_INDICES[cell].append(unit_index)

PEERS: List[set[int]] = []
for cell in CELL_INDICES:
    peers: set[int] = set[int]()
    for unit in CELL_UNITS[cell]:
        peers.update(unit)
    peers.discard(cell)
    PEERS.append(peers)

ROW_OF = [cell // 9 for cell in CELL_INDICES]
COL_OF = [cell % 9 for cell in CELL_INDICES]
BOX_OF = [((cell // 9) // 3) * 3 + ((cell % 9) // 3) for cell in CELL_INDICES]


# ============================================================
# Candidate lookup helpers
# ============================================================

UnitCandidateCacheKey = tuple[CellGroup, bool]


class UnitCandidateCache:
    """Per-state cache of candidate positions in units.

    `SudokuState` is mutable, so create a new cache for each state snapshot and
    discard it after the technique run.
    """

    def __init__(self, state: "SudokuState"):
        self.state = state
        self._positions: dict[UnitCandidateCacheKey, dict[int, List[int]]] = {}

    def candidate_positions(self, unit: Sequence[int], *, include_solved: bool = True) -> dict[int, List[int]]:
        """Return candidate cells by digit for one unit."""
        key = (CellGroup(unit), include_solved)
        if key not in self._positions:
            positions: dict[int, List[int]] = {digit: [] for digit in DIGIT_VALUES}
            for cell in unit:
                mask = self.state.candidate_mask(cell)
                if not include_solved and is_single(mask):
                    continue
                for digit in bits(mask):
                    positions[digit].append(cell)
            self._positions[key] = positions
        return self._positions[key]

    def cells_with_candidate(self, unit: Sequence[int], digit: int, *, include_solved: bool = True) -> List[int]:
        """Return cached candidate cells for a digit in one unit."""
        return self.candidate_positions(unit, include_solved=include_solved)[digit]

    def unsolved_cells_with_candidate(self, unit: Sequence[int], digit: int) -> List[int]:
        """Return cached unsolved cells for a digit in one unit."""
        return self.cells_with_candidate(unit, digit, include_solved=False)


def strong_links_for_digit(
    state: "SudokuState",
    digit: int,
    candidate_cache: UnitCandidateCache | None = None,
) -> List[CellPair]:
    """Return conjugate-pair strong links for one candidate digit."""
    cache = candidate_cache or UnitCandidateCache(state)
    links: set[CellPair] = set[CellPair]()
    for unit in ALL_UNITS:
        cells = cache.unsolved_cells_with_candidate(unit, digit)
        if len(cells) == 2:
            first_cell, second_cell = sorted(cells)
            links.add((first_cell, second_cell))
    return sorted(links)


def bivalue_candidate_cells(state: "SudokuState") -> List[int]:
    """Return unsolved cells with exactly two candidates."""
    return [cell for cell in CELL_INDICES if state.is_bivalue(cell)]


def bivalue_cells_by_mask(state: "SudokuState") -> dict[int, list[int]]:
    """Group bivalue cells by their two-candidate mask."""
    cells_by_mask: dict[int, list[int]] = {}
    for cell in bivalue_candidate_cells(state):
        cells_by_mask.setdefault(state.candidate_mask(cell), []).append(cell)
    return cells_by_mask


def trivalue_candidate_cells(state: "SudokuState") -> List[int]:
    """Return unsolved cells with exactly three candidates."""
    return [cell for cell in CELL_INDICES if state.is_trivalue(cell)]


def unsolved_cells(state: "SudokuState") -> List[int]:
    """Return cells that are not solved to a single digit."""
    return [cell for cell in CELL_INDICES if not is_single(state.candidate_mask(cell))]


# ============================================================
# Peer and elimination helpers
# ============================================================

def shared_peers(cells: Iterable[int]) -> set[int]:
    """Return cells that see every cell in the given collection."""
    cells = list[int](cells)
    if not cells:
        return set[int]()
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
    """Return candidate eliminations from peers shared by all given cells.

    Args:
        state: Sudoku state to inspect.
        cells: Source cells whose shared peers should be considered.
        digit: Candidate digit to eliminate.
        blocked: Cells that must not be used as elimination targets.

    Returns:
        Eliminations for shared peers that still contain the candidate digit.
    """
    blocked_cells = set[int](blocked)
    return [
        Elimination(cell, digit)
        for cell in sorted(shared_peers(cells) - blocked_cells)
        if state.can_place(cell, digit)
    ]


def other_bivalue_digit(digits: Sequence[int], known_digit: int) -> int:
    """Return the other digit from a two-digit candidate sequence."""
    return digits[0] if digits[1] == known_digit else digits[1]


# ============================================================
# Move model
# ============================================================

@dataclass(frozen=True)
class Placement:
    """A solved digit placement produced by a technique or guess."""

    cell: int
    digit: int


@dataclass(frozen=True)
class Elimination:
    """A candidate removal produced by a technique or propagation."""

    cell: int
    digit: int


@dataclass
class TechniqueTiming:
    """Aggregated timing counters for a solving technique."""

    attempts: int = 0
    successes: int = 0
    used: int = 0
    total_ms: float = 0.0
    successful_ms: float = 0.0

    def record_run(self, elapsed_ms: float, successful: bool) -> None:
        """Record one technique attempt and whether it found at least one move."""
        self.attempts += 1
        self.total_ms += elapsed_ms
        if successful:
            self.successes += 1
            self.successful_ms += elapsed_ms

    def record_use(self) -> None:
        """Record that a found move from this technique was selected."""
        self.used += 1

    @property
    def average_ms(self) -> float:
        return self.total_ms / self.attempts if self.attempts else 0.0

    @property
    def success_percent(self) -> float:
        return (self.successes / self.attempts * 100.0) if self.attempts else 0.0


# Text formatting helpers used by explanations and CLI rendering.
def placement_text(placement: Placement) -> str:
    return f"{cell_text(placement.cell)}={placement.digit}"


def elimination_text(elimination: Elimination) -> str:
    return f"{cell_text(elimination.cell)}!={elimination.digit}"


def source_digit_roles_for_cells(
    cells: Iterable[int],
    digits: Iterable[int],
    role: SourceDigitRole = "primary",
) -> SourceDigitRoles:
    """Return source-digit metadata for every cell/digit combination."""
    return {
        (cell, digit): role
        for cell in cells
        for digit in digits
    }


@dataclass
class Move:
    """A logical solver action before it is expanded for display.

    Techniques return moves containing placements, eliminations, explanatory
    text, difficulty, and cause cells. Rendering-specific state such as board
    snapshots belongs to :class:`ExplanationStep`.
    """

    technique: str
    reason: str
    placements: List[Placement] = field(default_factory=list)
    eliminations: List[Elimination] = field(default_factory=list)
    difficulty: int = 0
    cause_cells: List[int] = field(default_factory=list, repr=False)
    source_digit_roles: SourceDigitRoles = field(default_factory=dict, repr=False)
    timing_ms: float = field(default=0.0, repr=False)

    def summary(self) -> str:
        if self.reason.startswith(f"{self.technique}:"):
            return self.reason
        return f"{self.technique}: {self.reason}"


# ============================================================
# Move key and candidate simulation helpers
# ============================================================

EliminationKey = tuple[CellDigit, ...]


def elimination_key(eliminations: Sequence[Elimination], *, sorted_key: bool = False) -> EliminationKey:
    """Return a typed, hashable key for a sequence of eliminations."""
    pairs = ((elimination.cell, elimination.digit) for elimination in eliminations)
    return tuple[CellDigit, ...](sorted(pairs) if sorted_key else pairs)


def candidate_totals(candidates: Sequence[int]) -> tuple[int, int]:
    """Return solved-cell and total-candidate counts."""
    return (
        sum(1 for mask in candidates if is_single(mask)),
        sum(bit_count(mask) for mask in candidates),
    )


def eliminate_digit_from_candidates(
    candidates: list[int],
    cell: int,
    digit: int,
    changed_cells: set[int] | None = None,
) -> bool:
    """Remove one candidate from a local candidate-mask list."""
    digit_mask = bit(digit)
    current_mask = candidates[cell]
    if not (current_mask & digit_mask):
        return True

    new_mask = current_mask & ~digit_mask
    if new_mask == 0:
        return False

    candidates[cell] = new_mask
    if changed_cells is not None:
        changed_cells.add(cell)
    if is_single(new_mask):
        fixed_digit = single_digit(new_mask)
        fixed_mask = bit(fixed_digit)
        for peer in PEERS[cell]:
            if candidates[peer] & fixed_mask:
                if not eliminate_digit_from_candidates(candidates, peer, fixed_digit, changed_cells):
                    return False
    return True


def place_digit_in_candidates(
    candidates: list[int],
    cell: int,
    digit: int,
    changed_cells: set[int] | None = None,
) -> bool:
    """Place a digit in a local candidate-mask list."""
    digit_mask = bit(digit)
    if not (candidates[cell] & digit_mask):
        return False

    for candidate_digit in digits_from_mask(candidates[cell]):
        if candidate_digit != digit:
            if not eliminate_digit_from_candidates(candidates, cell, candidate_digit, changed_cells):
                return False

    for peer in PEERS[cell]:
        if candidates[peer] & digit_mask:
            if not eliminate_digit_from_candidates(candidates, peer, digit, changed_cells):
                return False
    return True


def _candidate_unit_consistency_ok(candidates: Sequence[int], unit: Sequence[int]) -> bool:
    """Return whether one unit has no duplicate singles and no missing digit."""
    seen_fixed: set[int] = set[int]()
    for cell in unit:
        mask = candidates[cell]
        if mask == 0:
            return False
        if is_single(mask):
            digit = single_digit(mask)
            if digit in seen_fixed:
                return False
            seen_fixed.add(digit)

    for digit in DIGIT_VALUES:
        digit_mask = bit(digit)
        if not any(candidates[cell] & digit_mask for cell in unit):
            return False
    return True


def candidates_consistency_ok(candidates: Sequence[int]) -> bool:
    """Return whether local candidate masks satisfy Sudoku invariants."""
    for unit in ALL_UNITS:
        if not _candidate_unit_consistency_ok(candidates, unit):
            return False
    return True


def changed_candidates_consistency_ok(candidates: Sequence[int], changed_cells: set[int]) -> bool:
    """Return whether units touched by changed cells remain consistent."""
    checked_units: set[int] = set[int]()
    for cell in changed_cells:
        for unit_index in CELL_UNIT_INDICES[cell]:
            if unit_index in checked_units:
                continue
            checked_units.add(unit_index)
            if not _candidate_unit_consistency_ok(candidates, ALL_UNITS[unit_index]):
                return False
    return True


def apply_move_to_candidates(candidates: list[int], move: Move, *, validate_all: bool = True) -> bool:
    """Apply a move to candidate masks without cloning a full SudokuState."""
    changed_cells: set[int] = set[int]()
    for placement in move.placements:
        if not place_digit_in_candidates(candidates, placement.cell, placement.digit, changed_cells):
            return False

    for elimination in move.eliminations:
        if not eliminate_digit_from_candidates(candidates, elimination.cell, elimination.digit, changed_cells):
            return False

    if validate_all:
        return candidates_consistency_ok(candidates)
    return changed_candidates_consistency_ok(candidates, changed_cells)


@dataclass
class ExplanationStep:
    """A display-ready step with board snapshot metadata.

    Explanation steps wrap a :class:`Move` and add the candidate grid state
    after applying that step plus the cells changed by the step.
    """

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
    def source_digit_roles(self) -> SourceDigitRoles:
        return self.move.source_digit_roles

    @property
    def timing_ms(self) -> float:
        return self.move.timing_ms

    def summary(self) -> str:
        return self.move.summary()


# ============================================================
# Sudoku state
# ============================================================

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


# ============================================================
# Technique base
# ============================================================

class Technique:
    """Base class for all logical Sudoku solving techniques."""

    name: str = "Technique"
    difficulty: int = 0

    def find_moves(self, state: SudokuState) -> List[Move]:
        """Return all moves this technique can currently find."""
        raise NotImplementedError
