"""State query helpers for candidate positions, peers, and links."""

from __future__ import annotations

from typing import Iterable, List, Sequence

from .bitmask import DIGIT_VALUES, bits, is_single
from .grid import ALL_UNITS, CELL_INDICES, PEERS
from .moves import Elimination
from .state import SudokuState
from .types import CellGroup, CellPair, UnitCandidateCacheKey


class UnitCandidateCache:
    """Per-state cache of candidate positions in units.

    `SudokuState` is mutable, so create a new cache for each state snapshot and
    discard it after the technique run.
    """

    def __init__(self, state: SudokuState):
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
    state: SudokuState,
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


def bivalue_candidate_cells(state: SudokuState) -> List[int]:
    """Return unsolved cells with exactly two candidates."""
    return [cell for cell in CELL_INDICES if state.is_bivalue(cell)]


def bivalue_cells_by_mask(state: SudokuState) -> dict[int, list[int]]:
    """Group bivalue cells by their two-candidate mask."""
    cells_by_mask: dict[int, list[int]] = {}
    for cell in bivalue_candidate_cells(state):
        cells_by_mask.setdefault(state.candidate_mask(cell), []).append(cell)
    return cells_by_mask


def trivalue_candidate_cells(state: SudokuState) -> List[int]:
    """Return unsolved cells with exactly three candidates."""
    return [cell for cell in CELL_INDICES if state.is_trivalue(cell)]


def unsolved_cells(state: SudokuState) -> List[int]:
    """Return cells that are not solved to a single digit."""
    return [cell for cell in CELL_INDICES if not is_single(state.candidate_mask(cell))]


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
    state: SudokuState,
    cells: Iterable[int],
    digit: int,
    blocked: Iterable[int] = (),
) -> List[Elimination]:
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
