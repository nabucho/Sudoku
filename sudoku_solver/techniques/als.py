from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .common import (
    ALL_UNITS,
    PEERS,
    CellGroup,
    Elimination,
    EliminationKey,
    IndexDigit,
    Move,
    SudokuState,
    Technique,
    bit_count,
    bits,
    cell_text,
    elimination_key,
    is_single,
    pair_combinations,
    sized_combinations,
    unit_text,
)

PEER_MASKS = [sum(1 << peer for peer in PEERS[cell]) for cell in range(81)]
ALSXZSeenKey = tuple[CellGroup, CellGroup, int, int, EliminationKey]
ALSGroupKey = tuple[CellGroup, int]
ALSWingSeenKey = tuple[
    CellGroup,
    CellGroup,
    CellGroup,
    int,
    int,
    int,
    EliminationKey,
]


@dataclass(frozen=True)
class ALSGroup:
    """Almost Locked Set with precomputed lookup data."""

    cells: CellGroup
    cell_set: frozenset[int]
    cell_mask: int
    mask: int
    unit_index: int
    digit_cells: dict[int, CellGroup]
    digit_cell_masks: dict[int, int]
    digit_peer_masks: dict[int, int]


class ALSXZ(Technique):
    """Find ALS-XZ eliminations using two ALS groups and restricted commons.

    See `doc/als-xz.md` for the full technique description.
    """

    name = "ALS-XZ"
    difficulty = 8

    def __init__(self, max_size: int = 4):
        self.max_size = max_size

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        seen: set[ALSXZSeenKey] = set[ALSXZSeenKey]()
        als_groups = self._als_groups(state)

        for left_index, left in enumerate[ALSGroup](als_groups):
            for right_index, right in enumerate[ALSGroup](als_groups[left_index + 1:], start=left_index + 1):
                if left.cell_mask & right.cell_mask:
                    continue

                common_mask = left.mask & right.mask
                for restricted_digit in self._restricted_common_digits(left, right, common_mask):
                    for eliminated_digit in sorted(set[int](bits(common_mask)) - {restricted_digit}):
                        eliminations = self._eliminations_for_digit(
                            state,
                            left,
                            right,
                            eliminated_digit,
                        )
                        if not eliminations:
                            continue

                        key = (
                            left.cells,
                            right.cells,
                            restricted_digit,
                            eliminated_digit,
                            elimination_key(eliminations),
                        )
                        reverse_key = (
                            right.cells,
                            left.cells,
                            restricted_digit,
                            eliminated_digit,
                            elimination_key(eliminations),
                        )
                        if key in seen or reverse_key in seen:
                            continue
                        seen.add(key)

                        moves.append(
                            Move(
                                technique=self.name,
                                difficulty=self.difficulty,
                                reason=(
                                    f"ALS-XZ: ALS in {unit_text(left.unit_index)} ({', '.join(cell_text(cell) for cell in left.cells)}) "
                                    f"and ALS in {unit_text(right.unit_index)} ({', '.join(cell_text(cell) for cell in right.cells)}) "
                                    f"share restricted common digit {restricted_digit}; eliminate shared digit {eliminated_digit}."
                                ),
                                eliminations=eliminations,
                                cause_cells=sorted(left.cell_set | right.cell_set),
                            )
                        )

        return moves

    def _als_groups(self, state: SudokuState) -> List[ALSGroup]:
        groups: List[ALSGroup] = []
        seen: set[ALSGroupKey] = set[ALSGroupKey]()

        for unit_index, unit in enumerate[list[int]](ALL_UNITS):
            masks_by_cell = {cell: state.candidate_mask(cell) for cell in unit}
            unsolved = [
                cell for cell in unit
                if not is_single(masks_by_cell[cell])
            ]
            for size in range(1, min(self.max_size, len(unsolved)) + 1):
                for cells in sized_combinations(unsolved, size):
                    union_mask = 0
                    for cell in cells:
                        union_mask |= masks_by_cell[cell]
                    if bit_count(union_mask) != size + 1:
                        continue

                    key = (cells, union_mask)
                    if key in seen:
                        continue
                    seen.add(key)
                    digit_cells = {
                        digit: CellGroup(
                            cell for cell in cells if masks_by_cell[cell] & (1 << (digit - 1))
                        )
                        for digit in bits(union_mask)
                    }
                    digit_cell_masks = {
                        digit: sum(1 << cell for cell in digit_cell_group)
                        for digit, digit_cell_group in digit_cells.items()
                    }
                    digit_peer_masks = {
                        digit: self._shared_peer_mask(digit_cell_group)
                        for digit, digit_cell_group in digit_cells.items()
                    }
                    groups.append(
                        ALSGroup(
                            cells=cells,
                            cell_set=frozenset(cells),
                            cell_mask=sum(1 << cell for cell in cells),
                            mask=union_mask,
                            unit_index=unit_index,
                            digit_cells=digit_cells,
                            digit_cell_masks=digit_cell_masks,
                            digit_peer_masks=digit_peer_masks,
                        )
                    )

        return groups

    def _shared_peer_mask(self, cells: CellGroup) -> int:
        """Return bit mask of cells that see every cell in the tuple."""
        if not cells:
            return 0
        peer_mask = PEER_MASKS[cells[0]]
        for cell in cells[1:]:
            peer_mask &= PEER_MASKS[cell]
        return peer_mask

    def _restricted_common_digits(
        self,
        left: ALSGroup,
        right: ALSGroup,
        common_mask: int,
    ) -> List[int]:
        digits: List[int] = []
        for digit in bits(common_mask):
            left_digit_cells = left.digit_cells.get(digit, ())
            right_digit_cells = right.digit_cells.get(digit, ())
            right_digit_mask = right.digit_cell_masks.get(digit, 0)
            left_digit_mask = left.digit_cell_masks.get(digit, 0)
            if (
                left_digit_cells
                and right_digit_cells
                and (right_digit_mask & ~left.digit_peer_masks[digit]) == 0
                and (left_digit_mask & ~right.digit_peer_masks[digit]) == 0
            ):
                digits.append(digit)
        return digits

    def _eliminations_for_digit(
        self,
        state: SudokuState,
        left: ALSGroup,
        right: ALSGroup,
        digit: int,
    ) -> List[Elimination]:
        digit_cells = (*left.digit_cells.get(digit, ()), *right.digit_cells.get(digit, ()))
        if not digit_cells:
            return []

        target_mask = left.digit_peer_masks[digit] & right.digit_peer_masks[digit]
        target_mask &= ~(left.cell_mask | right.cell_mask)
        eliminations: List[Elimination] = []
        while target_mask:
            cell_mask = target_mask & -target_mask
            cell = cell_mask.bit_length() - 1
            if state.can_place(cell, digit):
                eliminations.append(Elimination(cell, digit))
            target_mask &= ~cell_mask
        return eliminations


class ALSWing(ALSXZ):
    """Find ALS-Wing eliminations from a pivot ALS linked to two wing ALS groups.

    See `doc/als-wing.md` for the full technique description.
    """

    name = "ALS-Wing"
    difficulty = 8

    def __init__(self, max_size: int = 3, max_moves: int = 50):
        super().__init__(max_size)
        self.max_moves = max_moves

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        seen: set[ALSWingSeenKey] = set[ALSWingSeenKey]()
        als_groups = self._als_groups(state)
        restricted_links = self._restricted_links(als_groups)

        for pivot_index, pivot in enumerate[ALSGroup](als_groups):
            links = restricted_links.get(pivot_index, [])
            for left_link, right_link in pair_combinations(links):
                left_index, left_digit = left_link
                right_index, right_digit = right_link
                if left_index == right_index or left_digit == right_digit:
                    continue

                left = als_groups[left_index]
                right = als_groups[right_index]
                if left.cell_mask & right.cell_mask:
                    continue

                endpoint_digits = set[int](bits(left.mask & right.mask)) - {left_digit, right_digit}
                for eliminated_digit in sorted(endpoint_digits):
                    eliminations = self._eliminations_for_digit(
                        state,
                        left,
                        right,
                        eliminated_digit,
                    )
                    if not eliminations:
                        continue

                    key = (
                        pivot.cells,
                        left.cells,
                        right.cells,
                        left_digit,
                        right_digit,
                        eliminated_digit,
                        elimination_key(eliminations),
                    )
                    reverse_key = (
                        pivot.cells,
                        right.cells,
                        left.cells,
                        right_digit,
                        left_digit,
                        eliminated_digit,
                        elimination_key(eliminations),
                    )
                    if key in seen or reverse_key in seen:
                        continue
                    seen.add(key)

                    moves.append(
                        Move(
                            technique=self.name,
                            difficulty=self.difficulty,
                            reason=(
                                f"ALS-Wing: pivot ALS in {unit_text(pivot.unit_index)} ({', '.join(cell_text(cell) for cell in pivot.cells)}) "
                                f"links to ALSes in {unit_text(left.unit_index)} and {unit_text(right.unit_index)} "
                                f"through restricted digits {left_digit} and {right_digit}; eliminate {eliminated_digit}."
                            ),
                            eliminations=eliminations,
                            cause_cells=sorted(pivot.cell_set | left.cell_set | right.cell_set),
                        )
                    )
                    if len(moves) >= self.max_moves:
                        return moves

        return moves

    def _restricted_links(
        self,
        als_groups: List[ALSGroup],
    ) -> dict[int, List[IndexDigit]]:
        links: dict[int, List[IndexDigit]] = {}

        for left_index, left in enumerate[ALSGroup](als_groups):
            for right_index, right in enumerate[ALSGroup](als_groups[left_index + 1:], start=left_index + 1):
                if left.cell_mask & right.cell_mask:
                    continue

                common_mask = left.mask & right.mask
                for digit in self._restricted_common_digits(left, right, common_mask):
                    links.setdefault(left_index, []).append((right_index, digit))
                    links.setdefault(right_index, []).append((left_index, digit))

        return links
