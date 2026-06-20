from __future__ import annotations

from typing import List, Sequence

from .common import (
    BOX_UNITS,
    COL_UNITS,
    ROW_UNITS,
    CellGroup,
    Elimination,
    EliminationKey,
    Move,
    SudokuState,
    Technique,
    bit_count,
    cells_text,
    digits_from_mask,
    elimination_key,
    is_single,
    sized_combinations,
    source_digit_roles_for_cells,
)

SueDeCoqSeenKey = tuple[CellGroup, CellGroup, CellGroup, EliminationKey]
IntersectingLine = tuple[str, int, list[int]]


class SueDeCoq(Technique):
    """Eliminate candidates using box-line disjoint subset counting.

    See `doc/sue-de-coq.md` for the full technique description.
    """

    name = "Sue de Coq"
    difficulty = 8

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        seen: set[SueDeCoqSeenKey] = set[SueDeCoqSeenKey]()

        for box_index, box in enumerate[list[int]](BOX_UNITS):
            for line_name, line_index, line in self._intersecting_lines(box_index):
                intersection = [
                    cell
                    for cell in box
                    if cell in line and not is_single(state.candidate_mask(cell))
                ]
                if len(intersection) < 2:
                    continue

                intersection_mask = self._union_mask(state, intersection)
                if len(intersection) not in (2, 3):
                    continue
                if bit_count(intersection_mask) != len(intersection) + 2:
                    continue

                line_cells = [
                    cell
                    for cell in line
                    if cell not in box and not is_single(state.candidate_mask(cell))
                ]
                box_cells = [
                    cell
                    for cell in box
                    if cell not in line and not is_single(state.candidate_mask(cell))
                ]

                for line_companions in self._basic_companion_groups(state, line_cells, intersection_mask):
                    line_mask = self._union_mask(state, line_companions)
                    for box_companions in self._basic_companion_groups(state, box_cells, intersection_mask):
                        box_mask = self._union_mask(state, box_companions)

                        if line_mask & box_mask:
                            continue

                        pattern_cells = [*intersection, *line_companions, *box_companions]
                        pattern_mask = intersection_mask | line_mask | box_mask
                        if bit_count(pattern_mask) != len(pattern_cells):
                            continue

                        line_elimination_mask = line_mask | (intersection_mask & ~box_mask)
                        box_elimination_mask = box_mask | (intersection_mask & ~line_mask)

                        eliminations = [
                            *self._eliminations(
                                state,
                                line,
                                {*intersection, *line_companions},
                                line_elimination_mask,
                            ),
                            *self._eliminations(
                                state,
                                box,
                                {*intersection, *box_companions},
                                box_elimination_mask,
                            ),
                        ]
                        if not eliminations:
                            continue

                        key = (
                            CellGroup(intersection),
                            CellGroup(line_companions),
                            CellGroup(box_companions),
                            elimination_key(eliminations),
                        )
                        if key in seen:
                            continue
                        seen.add(key)

                        moves.append(
                            Move(
                                technique=self.name,
                                difficulty=self.difficulty,
                                reason=(
                                    f"Sue de Coq at box {box_index + 1} and {line_name} {line_index + 1}: "
                                    f"intersection {cells_text(intersection)} has candidates "
                                    f"{digits_from_mask(intersection_mask)}, with line companions "
                                    f"{cells_text(line_companions)} and box companions {cells_text(box_companions)}."
                                ),
                                eliminations=eliminations,
                                cause_cells=sorted(pattern_cells),
                                source_digit_roles=source_digit_roles_for_cells(
                                    sorted(pattern_cells),
                                    digits_from_mask(pattern_mask),
                                ),
                            )
                        )

        return moves

    def _intersecting_lines(self, box_index: int) -> list[IntersectingLine]:
        box_row = box_index // 3
        box_col = box_index % 3
        rows = [
            ("row", row, ROW_UNITS[row])
            for row in range(box_row * 3, box_row * 3 + 3)
        ]
        cols = [
            ("column", col, COL_UNITS[col])
            for col in range(box_col * 3, box_col * 3 + 3)
        ]
        return rows + cols

    def _basic_companion_groups(
        self,
        state: SudokuState,
        cells: Sequence[int],
        intersection_mask: int,
    ) -> list[CellGroup]:
        return [
            combo
            for combo in sized_combinations(cells, 1)
            if bit_count(state.candidate_mask(combo[0])) == 2
            and (state.candidate_mask(combo[0]) & ~intersection_mask) == 0
        ]

    def _union_mask(self, state: SudokuState, cells: Sequence[int]) -> int:
        mask = 0
        for cell in cells:
            mask |= state.candidate_mask(cell)
        return mask

    def _eliminations(
        self,
        state: SudokuState,
        unit: Sequence[int],
        blocked: set[int],
        mask: int,
    ) -> List[Elimination]:
        return [
            Elimination(cell, digit)
            for cell in unit
            if cell not in blocked and not is_single(state.candidate_mask(cell))
            for digit in digits_from_mask(mask)
            if state.can_place(cell, digit)
        ]
