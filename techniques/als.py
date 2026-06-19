from __future__ import annotations

from itertools import combinations
from typing import List

from .common import *


class ALSXZ(Technique):
    name = "ALS-XZ"
    difficulty = 8

    def __init__(self, max_size: int = 4):
        self.max_size = max_size

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        seen = set()
        als_groups = self._als_groups(state)

        for left_index, left in enumerate(als_groups):
            for right in als_groups[left_index + 1:]:
                left_cells, left_mask, left_unit = left
                right_cells, right_mask, right_unit = right
                if set(left_cells) & set(right_cells):
                    continue

                common_digits = set(digits_from_mask(left_mask & right_mask))
                for restricted_digit in common_digits:
                    left_restricted = [
                        cell for cell in left_cells
                        if state.can_place(cell, restricted_digit)
                    ]
                    right_restricted = [
                        cell for cell in right_cells
                        if state.can_place(cell, restricted_digit)
                    ]
                    if not left_restricted or not right_restricted:
                        continue
                    if not all(right_cell in PEERS[left_cell] for left_cell in left_restricted for right_cell in right_restricted):
                        continue

                    for eliminated_digit in sorted(common_digits - {restricted_digit}):
                        eliminations = self._eliminations_for_digit(
                            state,
                            left_cells,
                            right_cells,
                            eliminated_digit,
                        )
                        if not eliminations:
                            continue

                        key = (
                            tuple(left_cells),
                            tuple(right_cells),
                            restricted_digit,
                            eliminated_digit,
                            tuple((elimination.cell, elimination.digit) for elimination in eliminations),
                        )
                        reverse_key = (
                            tuple(right_cells),
                            tuple(left_cells),
                            restricted_digit,
                            eliminated_digit,
                            tuple((elimination.cell, elimination.digit) for elimination in eliminations),
                        )
                        if key in seen or reverse_key in seen:
                            continue
                        seen.add(key)

                        moves.append(
                            Move(
                                technique=self.name,
                                difficulty=self.difficulty,
                                reason=(
                                    f"ALS-XZ: ALS in {unit_text(left_unit)} ({', '.join(cell_text(cell) for cell in left_cells)}) "
                                    f"and ALS in {unit_text(right_unit)} ({', '.join(cell_text(cell) for cell in right_cells)}) "
                                    f"share restricted common digit {restricted_digit}; eliminate shared digit {eliminated_digit}."
                                ),
                                eliminations=eliminations,
                                cause_cells=sorted({*left_cells, *right_cells}),
                            )
                        )

        return moves

    def _als_groups(self, state: SudokuState) -> List[tuple[tuple[int, ...], int, int]]:
        groups = []
        seen = set()

        for unit_index, unit in enumerate(ALL_UNITS):
            unsolved = [
                cell for cell in unit
                if not is_single(state.candidate_mask(cell))
            ]
            for size in range(1, min(self.max_size, len(unsolved)) + 1):
                for cells in combinations(unsolved, size):
                    union_mask = 0
                    for cell in cells:
                        union_mask |= state.candidate_mask(cell)
                    if bit_count(union_mask) != size + 1:
                        continue

                    key = (tuple(sorted(cells)), union_mask)
                    if key in seen:
                        continue
                    seen.add(key)
                    groups.append((tuple(sorted(cells)), union_mask, unit_index))

        return groups

    def _eliminations_for_digit(
        self,
        state: SudokuState,
        left_cells: tuple[int, ...],
        right_cells: tuple[int, ...],
        digit: int,
    ) -> List[Elimination]:
        digit_cells = [
            cell for cell in (*left_cells, *right_cells)
            if state.can_place(cell, digit)
        ]
        if not digit_cells:
            return []

        common_peers = set(range(81))
        for cell in digit_cells:
            common_peers &= PEERS[cell]

        blocked = set(left_cells) | set(right_cells)
        return [
            Elimination(cell, digit)
            for cell in sorted(common_peers - blocked)
            if state.can_place(cell, digit)
        ]
