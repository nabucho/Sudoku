from __future__ import annotations

from itertools import combinations
from typing import List, Tuple

from .common import *


class UniqueRectangleType1(Technique):
    name = "Unique Rectangle Type 1"
    difficulty = 7

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for r1, r2 in combinations(range(9), 2):
            for c1, c2 in combinations(range(9), 2):
                cells = [
                    rc_to_i(r1, c1),
                    rc_to_i(r1, c2),
                    rc_to_i(r2, c1),
                    rc_to_i(r2, c2),
                ]

                # Standard UR rectangle spans exactly two boxes
                boxes = {BOX_OF[cell] for cell in cells}
                if len(boxes) != 2:
                    continue

                masks = [state.candidate_mask(cell) for cell in cells]
                bivalue_masks = [m for m in masks if bit_count(m) == 2]
                if len(bivalue_masks) < 3:
                    continue

                counts = {}
                for m in bivalue_masks:
                    counts[m] = counts.get(m, 0) + 1

                pair_mask = None
                for m, cnt in counts.items():
                    if cnt >= 3 and bit_count(m) == 2:
                        pair_mask = m
                        break

                if pair_mask is None:
                    continue

                pair_cells = [cells[idx] for idx, m in enumerate(masks) if m == pair_mask]
                if len(pair_cells) != 3:
                    continue

                odd_cell = [cell for cell in cells if cell not in pair_cells][0]
                odd_mask = state.candidate_mask(odd_cell)

                # Odd cell must be a superset of the deadly pair
                if (odd_mask & pair_mask) != pair_mask:
                    continue
                if odd_mask == pair_mask:
                    continue

                pair_digits = digits_from_mask(pair_mask)
                eliminations = [
                    Elimination(odd_cell, d)
                    for d in pair_digits
                    if state.can_place(odd_cell, d)
                ]
                if eliminations:
                    rr, cc = i_to_rc(odd_cell)
                    moves.append(
                        Move(
                            technique=self.name,
                            difficulty=self.difficulty,
                            reason=(
                                f"Unique Rectangle Type 1 on rows {r1+1},{r2+1} and columns {c1+1},{c2+1}: "
                                f"three corners form deadly pair {pair_digits}, so r{rr+1}c{cc+1} "
                                f"cannot keep both of those digits."
                            ),
                            eliminations=eliminations,
                            cause_cells=cells,
                        )
                    )

        return moves

class UniqueRectangleType2(Technique):
    name = "Unique Rectangle Type 2"
    difficulty = 7

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for r1, r2 in combinations(range(9), 2):
            for c1, c2 in combinations(range(9), 2):
                cells = [
                    rc_to_i(r1, c1),
                    rc_to_i(r1, c2),
                    rc_to_i(r2, c1),
                    rc_to_i(r2, c2),
                ]
                if len({BOX_OF[cell] for cell in cells}) != 2:
                    continue

                masks = {cell: state.candidate_mask(cell) for cell in cells}
                for pair_mask in {mask for mask in masks.values() if bit_count(mask) == 2}:
                    pair_cells = [cell for cell in cells if masks[cell] == pair_mask]
                    extra_cells = [
                        cell
                        for cell in cells
                        if cell not in pair_cells and (masks[cell] & pair_mask) == pair_mask
                    ]
                    if len(pair_cells) != 2 or len(extra_cells) != 2:
                        continue

                    extra_masks = [masks[cell] & ~pair_mask for cell in extra_cells]
                    if any(bit_count(mask) != 1 for mask in extra_masks):
                        continue
                    if extra_masks[0] != extra_masks[1]:
                        continue

                    extra_digit = single_digit(extra_masks[0])
                    eliminations = [
                        Elimination(cell, extra_digit)
                        for cell in (PEERS[extra_cells[0]] & PEERS[extra_cells[1]])
                        if cell not in cells and state.can_place(cell, extra_digit)
                    ]
                    if eliminations:
                        pair_digits = digits_from_mask(pair_mask)
                        moves.append(
                            Move(
                                technique=self.name,
                                difficulty=self.difficulty,
                                reason=(
                                    f"Unique Rectangle Type 2 on {', '.join(cell_text(cell) for cell in cells)}: "
                                    f"deadly pair {pair_digits} has extra digit {extra_digit} in two corners."
                                ),
                                eliminations=eliminations,
                                cause_cells=cells,
                            )
                        )

        return moves

class UniqueRectangleType4(Technique):
    name = "Unique Rectangle Type 4"
    difficulty = 7

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for r1, r2 in combinations(range(9), 2):
            for c1, c2 in combinations(range(9), 2):
                cells = [
                    rc_to_i(r1, c1),
                    rc_to_i(r1, c2),
                    rc_to_i(r2, c1),
                    rc_to_i(r2, c2),
                ]
                if len({BOX_OF[cell] for cell in cells}) != 2:
                    continue

                masks = {cell: state.candidate_mask(cell) for cell in cells}
                for pair_mask in {mask for mask in masks.values() if bit_count(mask) == 2}:
                    pair_digits = digits_from_mask(pair_mask)
                    pair_cells = [cell for cell in cells if masks[cell] == pair_mask]
                    floor_cells = [
                        cell
                        for cell in cells
                        if cell not in pair_cells and (masks[cell] & pair_mask) == pair_mask and masks[cell] != pair_mask
                    ]
                    if len(pair_cells) != 2 or len(floor_cells) != 2:
                        continue

                    shared_units = [
                        unit
                        for unit in CELL_UNITS[floor_cells[0]]
                        if floor_cells[1] in unit
                    ]
                    for unit in shared_units:
                        for strong_digit in pair_digits:
                            cells_for_digit = [cell for cell in unit if state.can_place(cell, strong_digit)]
                            if sorted(cells_for_digit) != sorted(floor_cells):
                                continue

                            other_digit = pair_digits[0] if pair_digits[1] == strong_digit else pair_digits[1]
                            eliminations = [
                                Elimination(cell, other_digit)
                                for cell in floor_cells
                                if state.can_place(cell, other_digit)
                            ]
                            if eliminations:
                                moves.append(
                                    Move(
                                        technique=self.name,
                                        difficulty=self.difficulty,
                                        reason=(
                                            f"Unique Rectangle Type 4 on {', '.join(cell_text(cell) for cell in cells)}: "
                                            f"{strong_digit} is strongly linked in the two non-bivalue corners, "
                                            f"so {other_digit} can be removed from them."
                                        ),
                                        eliminations=eliminations,
                                        cause_cells=cells,
                                    )
                                )

        return moves

class BUGPlusOne(Technique):
    name = "BUG+1"
    difficulty = 7

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        unsolved = [cell for cell in range(81) if not is_single(state.candidate_mask(cell))]
        if not unsolved:
            return moves

        tri_cells = [cell for cell in unsolved if bit_count(state.candidate_mask(cell)) == 3]
        other_bad = [
            cell for cell in unsolved
            if bit_count(state.candidate_mask(cell)) not in (2, 3)
        ]

        if len(tri_cells) != 1 or other_bad:
            return moves

        cell = tri_cells[0]
        row = ROW_OF[cell]
        col = COL_OF[cell]
        box = BOX_OF[cell]

        for d in state.candidate_digits(cell):
            row_count = sum(1 for c in ROW_UNITS[row] if state.can_place(c, d))
            col_count = sum(1 for c in COL_UNITS[col] if state.can_place(c, d))
            box_count = sum(1 for c in BOX_UNITS[box] if state.can_place(c, d))

            if row_count == 3 and col_count == 3 and box_count == 3:
                r, c = i_to_rc(cell)
                moves.append(
                    Move(
                        technique=self.name,
                        difficulty=self.difficulty,
                        reason=(
                            f"BUG+1: r{r+1}c{c+1} is the only tri-value cell, "
                            f"so digit {d} must be placed there."
                        ),
                        placements=[Placement(cell, d)],
                        cause_cells=[cell],
                    )
                )

        return moves

class Nishio(Technique):
    name = "Nishio"
    difficulty = 8

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for cell in range(81):
            if is_single(state.candidate_mask(cell)):
                continue

            for digit in state.candidate_digits(cell):
                child = state.clone()
                if child.place_digit(cell, digit) and child.consistency_ok():
                    continue

                moves.append(
                    Move(
                        technique=self.name,
                        difficulty=self.difficulty,
                        reason=(
                            f"Assuming {placement_text(Placement(cell, digit))} leads to a contradiction, "
                            f"so {digit} can be removed from {cell_text(cell)}."
                        ),
                        eliminations=[Elimination(cell, digit)],
                        cause_cells=[cell],
                    )
                )

        return moves

