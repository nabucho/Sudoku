from __future__ import annotations

from typing import List

from .common import (
    ALL_UNITS,
    BOX_OF,
    BOX_UNITS,
    CELL_INDICES,
    COL_OF,
    COL_UNITS,
    DIGIT_VALUES,
    ROW_OF,
    ROW_UNITS,
    Elimination,
    Move,
    Placement,
    SudokuState,
    Technique,
    UnitCandidateCache,
    bit_count,
    bits,
    cell_text,
    cells_text,
    digits_from_mask,
    forced_cell_reason,
    is_single,
    single_digit,
    sized_combinations,
    source_digit_roles_for_cells,
    unit_text,
)


class NakedSingle(Technique):
    """Place a digit when a cell has exactly one candidate.

    See `doc/naked-single.md` for the full technique description.
    """

    name = "Naked Single"
    difficulty = 1

    def find_moves(self, state: SudokuState) -> List[Move]:
        for cell in CELL_INDICES:
            mask = state.candidate_mask(cell)
            if is_single(mask) and cell not in state.fixed_cells:
                digit = single_digit(mask)
                return [
                    Move(
                        technique=self.name,
                        difficulty=self.difficulty,
                        reason=forced_cell_reason(cell, digit),
                        placements=[Placement(cell, digit)],
                    )
                ]
        return []


class HiddenSingle(Technique):
    """Place a digit when it has only one possible cell in a unit.

    See `doc/hidden-single.md` for the full technique description.
    """

    name = "Hidden Single"
    difficulty = 1

    def find_moves(self, state: SudokuState) -> List[Move]:
        candidate_cache = UnitCandidateCache(state)
        for unit_index, unit in enumerate[list[int]](ALL_UNITS):
            for digit in DIGIT_VALUES:
                cells = candidate_cache.cells_with_candidate(unit, digit)
                if len(cells) == 1:
                    cell = cells[0]
                    if not is_single(state.candidate_mask(cell)):
                        return [
                            Move(
                                technique=self.name,
                                difficulty=self.difficulty,
                                reason=f"Digit {digit} can only go in {cell_text(cell)} within {unit_text(unit_index)}.",
                                placements=[Placement(cell, digit)],
                            )
                        ]
        return []


class LockedCandidates(Technique):
    """Remove candidates using pointing and claiming box-line interactions.

    See `doc/locked-candidates.md` for the full technique description.
    """

    name = "Locked Candidates"
    difficulty = 2

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        candidate_cache = UnitCandidateCache(state)

        # Pointing: box -> row / column
        for box_index, box in enumerate[list[int]](BOX_UNITS):
            for digit in DIGIT_VALUES:
                cells = candidate_cache.cells_with_candidate(box, digit)
                if len(cells) < 2:
                    continue

                rows = {ROW_OF[cell] for cell in cells}
                cols = {COL_OF[cell] for cell in cells}

                if len(rows) == 1:
                    row = next(iter(rows))
                    eliminations = [
                        Elimination(cell, digit)
                        for cell in ROW_UNITS[row]
                        if cell not in box and state.can_place(cell, digit)
                    ]
                    if eliminations:
                        moves.append(
                            Move(
                                technique=self.name,
                                difficulty=self.difficulty,
                                reason=f"Pointing: digit {digit} in box {box_index+1} is confined to row {row+1}.",
                                eliminations=eliminations,
                                cause_cells=cells,
                                source_digit_roles=source_digit_roles_for_cells(cells, [digit]),
                            )
                        )

                if len(cols) == 1:
                    col = next(iter(cols))
                    eliminations = [
                        Elimination(cell, digit)
                        for cell in COL_UNITS[col]
                        if cell not in box and state.can_place(cell, digit)
                    ]
                    if eliminations:
                        moves.append(
                            Move(
                                technique=self.name,
                                difficulty=self.difficulty,
                                reason=f"Pointing: digit {digit} in box {box_index+1} is confined to column {col+1}.",
                                eliminations=eliminations,
                                cause_cells=cells,
                                source_digit_roles=source_digit_roles_for_cells(cells, [digit]),
                            )
                        )

        # Claiming: row / column -> box
        for family_name, unit_list in (("row", ROW_UNITS), ("column", COL_UNITS)):
            for unit_index, unit in enumerate[list[int]](unit_list):
                for digit in DIGIT_VALUES:
                    cells = candidate_cache.cells_with_candidate(unit, digit)
                    if len(cells) < 2:
                        continue

                    boxes = {BOX_OF[cell] for cell in cells}
                    if len(boxes) == 1:
                        box_index = next(iter(boxes))
                        box = BOX_UNITS[box_index]
                        eliminations = [
                            Elimination(cell, digit)
                            for cell in box
                            if cell not in unit and state.can_place(cell, digit)
                        ]
                        if eliminations:
                            moves.append(
                                Move(
                                    technique=self.name,
                                    difficulty=self.difficulty,
                                    reason=f"Claiming: digit {digit} in {family_name} {unit_index+1} is confined to box {box_index+1}.",
                                    eliminations=eliminations,
                                    cause_cells=cells,
                                    source_digit_roles=source_digit_roles_for_cells(cells, [digit]),
                                )
                            )

        return moves


class NakedSubset(Technique):
    """Remove candidates using a naked pair, triple, or quad.

    See `doc/naked-subsets.md` for the full technique description.
    """

    def __init__(self, size: int):
        self.size = size
        self.name = {2: "Naked Pair", 3: "Naked Triple", 4: "Naked Quad"}[size]
        self.difficulty = {2: 3, 3: 4, 4: 5}[size]

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for unit in ALL_UNITS:
            subset_cells = [
                cell
                for cell in unit
                if 2 <= bit_count(state.candidate_mask(cell)) <= self.size
            ]

            for combo in sized_combinations(subset_cells, self.size):
                union_mask = 0
                for cell in combo:
                    union_mask |= state.candidate_mask(cell)

                if bit_count(union_mask) != self.size:
                    continue

                eliminations: List[Elimination] = []
                for other in unit:
                    if other in combo:
                        continue
                    for digit in bits(union_mask):
                        if state.can_place(other, digit):
                            eliminations.append(Elimination(other, digit))

                if eliminations:
                    digits_text = digits_from_mask(union_mask)
                    moves.append(
                        Move(
                            technique=self.name,
                            difficulty=self.difficulty,
                            reason=f"{self.name}: cells {cells_text(combo)} contain only digits {digits_text}.",
                            eliminations=eliminations,
                            cause_cells=list[int](combo),
                            source_digit_roles=source_digit_roles_for_cells(combo, digits_text),
                        )
                    )

        return moves


class HiddenSubset(Technique):
    """Remove extra candidates from a hidden pair, triple, or quad.

    See `doc/hidden-subsets.md` for the full technique description.
    """

    def __init__(self, size: int):
        self.size = size
        self.name = {2: "Hidden Pair", 3: "Hidden Triple", 4: "Hidden Quad"}[size]
        self.difficulty = {2: 3, 3: 4, 4: 5}[size]

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        candidate_cache = UnitCandidateCache(state)

        for unit in ALL_UNITS:
            cells_by_digit = candidate_cache.candidate_positions(unit, include_solved=False)
            eligible_digits = [
                digit
                for digit in DIGIT_VALUES
                if 1 <= len(cells_by_digit[digit]) <= self.size
            ]
            if len(eligible_digits) < self.size:
                continue

            for digits_combo in sized_combinations(eligible_digits, self.size):
                cells_set: set[int] = set[int]()
                for digit in digits_combo:
                    cells_set.update(cells_by_digit[digit])
                    if len(cells_set) > self.size:
                        break

                if len(cells_set) != self.size:
                    continue

                cells = [cell for cell in unit if cell in cells_set]

                eliminations: List[Elimination] = []
                for cell in cells:
                    for digit in state.candidate_digits(cell):
                        if digit not in digits_combo:
                            eliminations.append(Elimination(cell, digit))

                if eliminations:
                    moves.append(
                        Move(
                            technique=self.name,
                            difficulty=self.difficulty,
                            reason=f"{self.name}: digits {list[int](digits_combo)} are confined to cells {cells_text(cells)}.",
                            eliminations=eliminations,
                            cause_cells=cells,
                            source_digit_roles=source_digit_roles_for_cells(cells, digits_combo),
                        )
                    )

        return moves

