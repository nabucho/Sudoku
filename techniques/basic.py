from __future__ import annotations

from itertools import combinations
from typing import List, Tuple

from .common import *


class NakedSingle(Technique):
    name = "Naked Single"
    difficulty = 1

    def find_moves(self, state: SudokuState) -> List[Move]:
        for cell in range(81):
            mask = state.candidate_mask(cell)
            if is_single(mask) and cell not in state.fixed_cells:
                digit = single_digit(mask)
                r, c = i_to_rc(cell)
                return [
                    Move(
                        technique=self.name,
                        difficulty=self.difficulty,
                        reason=f"r{r+1}c{c+1} is forced to {digit}.",
                        placements=[Placement(cell, digit)],
                    )
                ]
        return []

class HiddenSingle(Technique):
    name = "Hidden Single"
    difficulty = 1

    def find_moves(self, state: SudokuState) -> List[Move]:
        for unit_index, unit in enumerate(ALL_UNITS):
            for d in range(1, 10):
                cells = [cell for cell in unit if state.can_place(cell, d)]
                if len(cells) == 1:
                    cell = cells[0]
                    if not is_single(state.candidate_mask(cell)):
                        return [
                            Move(
                                technique=self.name,
                                difficulty=self.difficulty,
                                reason=f"Digit {d} can only go in {cell_text(cell)} within {unit_text(unit_index)}.",
                                placements=[Placement(cell, d)],
                            )
                        ]
        return []

class LockedCandidates(Technique):
    """
    Pointing + claiming.
    """
    name = "Locked Candidates"
    difficulty = 2

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        # Pointing: box -> row / column
        for box_index, box in enumerate(BOX_UNITS):
            for d in range(1, 10):
                cells = [cell for cell in box if state.can_place(cell, d)]
                if len(cells) < 2:
                    continue

                rows = {ROW_OF[cell] for cell in cells}
                cols = {COL_OF[cell] for cell in cells}

                if len(rows) == 1:
                    row = next(iter(rows))
                    eliminations = [
                        Elimination(cell, d)
                        for cell in ROW_UNITS[row]
                        if cell not in box and state.can_place(cell, d)
                    ]
                    if eliminations:
                        moves.append(
                            Move(
                                technique=self.name,
                                difficulty=self.difficulty,
                                reason=f"Pointing: digit {d} in box {box_index+1} is confined to row {row+1}.",
                                eliminations=eliminations,
                                cause_cells=cells,
                            )
                        )

                if len(cols) == 1:
                    col = next(iter(cols))
                    eliminations = [
                        Elimination(cell, d)
                        for cell in COL_UNITS[col]
                        if cell not in box and state.can_place(cell, d)
                    ]
                    if eliminations:
                        moves.append(
                            Move(
                                technique=self.name,
                                difficulty=self.difficulty,
                                reason=f"Pointing: digit {d} in box {box_index+1} is confined to column {col+1}.",
                                eliminations=eliminations,
                                cause_cells=cells,
                            )
                        )

        # Claiming: row / column -> box
        for family_name, unit_list in (("row", ROW_UNITS), ("column", COL_UNITS)):
            for unit_index, unit in enumerate(unit_list):
                for d in range(1, 10):
                    cells = [cell for cell in unit if state.can_place(cell, d)]
                    if len(cells) < 2:
                        continue

                    boxes = {BOX_OF[cell] for cell in cells}
                    if len(boxes) == 1:
                        box_index = next(iter(boxes))
                        box = BOX_UNITS[box_index]
                        eliminations = [
                            Elimination(cell, d)
                            for cell in box
                            if cell not in unit and state.can_place(cell, d)
                        ]
                        if eliminations:
                            moves.append(
                                Move(
                                    technique=self.name,
                                    difficulty=self.difficulty,
                                    reason=f"Claiming: digit {d} in {family_name} {unit_index+1} is confined to box {box_index+1}.",
                                    eliminations=eliminations,
                                    cause_cells=cells,
                                )
                            )

        return moves

class NakedSubset(Technique):
    """
    Generic naked pair / triple / quad.
    """
    def __init__(self, size: int):
        self.size = size
        self.name = {2: "Naked Pair", 3: "Naked Triple", 4: "Naked Quad"}[size]
        self.difficulty = {2: 3, 3: 4, 4: 5}[size]

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for unit in ALL_UNITS:
            candidate_cells = [
                cell
                for cell in unit
                if 2 <= bit_count(state.candidate_mask(cell)) <= self.size
            ]

            for combo in combinations(candidate_cells, self.size):
                union_mask = 0
                for cell in combo:
                    union_mask |= state.candidate_mask(cell)

                if bit_count(union_mask) != self.size:
                    continue

                eliminations: List[Elimination] = []
                for other in unit:
                    if other in combo:
                        continue
                    for d in bits(union_mask):
                        if state.can_place(other, d):
                            eliminations.append(Elimination(other, d))

                if eliminations:
                    combo_text = ", ".join(f"r{i_to_rc(c)[0]+1}c{i_to_rc(c)[1]+1}" for c in combo)
                    digits_text = digits_from_mask(union_mask)
                    moves.append(
                        Move(
                            technique=self.name,
                            difficulty=self.difficulty,
                            reason=f"{self.name}: cells {combo_text} contain only digits {digits_text}.",
                            eliminations=eliminations,
                            cause_cells=list(combo),
                        )
                    )

        return moves

class HiddenSubset(Technique):
    """
    Generic hidden pair / triple / quad.
    """
    def __init__(self, size: int):
        self.size = size
        self.name = {2: "Hidden Pair", 3: "Hidden Triple", 4: "Hidden Quad"}[size]
        self.difficulty = {2: 3, 3: 4, 4: 5}[size]

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for unit in ALL_UNITS:
            cells_by_digit = {
                d: [cell for cell in unit if state.can_place(cell, d)]
                for d in range(1, 10)
            }

            for digits_combo in combinations(range(1, 10), self.size):
                combo_mask = 0
                cells_set = set()
                for d in digits_combo:
                    combo_mask |= bit(d)
                    cells_set.update(cells_by_digit[d])

                cells = [cell for cell in unit if cell in cells_set]
                if len(cells) != self.size:
                    continue

                # each digit must appear at least once in those cells
                if any(not cells_by_digit[d] for d in digits_combo):
                    continue

                eliminations: List[Elimination] = []
                for cell in cells:
                    for d in state.candidate_digits(cell):
                        if d not in digits_combo:
                            eliminations.append(Elimination(cell, d))

                if eliminations:
                    cell_text = ", ".join(f"r{i_to_rc(c)[0]+1}c{i_to_rc(c)[1]+1}" for c in cells)
                    moves.append(
                        Move(
                            technique=self.name,
                            difficulty=self.difficulty,
                            reason=f"{self.name}: digits {list(digits_combo)} are confined to cells {cell_text}.",
                            eliminations=eliminations,
                            cause_cells=cells,
                        )
                    )

        return moves

