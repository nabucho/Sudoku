"""Candidate-list simulation and consistency helpers."""

from __future__ import annotations

from typing import Sequence

from .bitmask import DIGIT_VALUES, bit, bit_count, digits_from_mask, is_single, single_digit
from .grid import ALL_UNITS, CELL_UNIT_INDICES, PEERS
from .moves import Move


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
