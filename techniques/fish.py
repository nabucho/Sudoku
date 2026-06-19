from __future__ import annotations

from itertools import combinations
from typing import List

from .common import (
    BOX_OF,
    BOX_UNITS,
    COL_OF,
    COL_UNITS,
    Elimination,
    Move,
    ROW_OF,
    ROW_UNITS,
    SudokuState,
    Technique,
    rc_to_i,
)


class Fish(Technique):
    """
    size=2 => X-Wing
    size=3 => Swordfish
    size=4 => Jellyfish
    """
    def __init__(self, size: int):
        self.size = size
        self.name = {2: "X-Wing", 3: "Swordfish", 4: "Jellyfish"}[size]
        self.difficulty = {2: 5, 3: 6, 4: 7}[size]

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for d in range(1, 10):
            # Row-based fish
            row_patterns = []
            for r in range(9):
                cols = [c for c in range(9) if state.can_place(rc_to_i(r, c), d)]
                if 2 <= len(cols) <= self.size:
                    row_patterns.append((r, tuple(cols)))

            for combo in combinations(row_patterns, self.size):
                rows = [r for r, _ in combo]
                cols_union = sorted(set(c for _, cols in combo for c in cols))
                if len(cols_union) != self.size:
                    continue

                eliminations = []
                for c in cols_union:
                    for r in range(9):
                        if r not in rows:
                            cell = rc_to_i(r, c)
                            if state.can_place(cell, d):
                                eliminations.append(Elimination(cell, d))

                if eliminations:
                    cause_cells = [
                        rc_to_i(r, c)
                        for r, cols in combo
                        for c in cols
                    ]
                    moves.append(
                        Move(
                            technique=self.name,
                            difficulty=self.difficulty,
                            reason=f"{self.name}: digit {d} forms a row-based fish on rows {[r+1 for r in rows]} and columns {[c+1 for c in cols_union]}.",
                            eliminations=eliminations,
                            cause_cells=cause_cells,
                        )
                    )

            # Column-based fish
            col_patterns = []
            for c in range(9):
                rows = [r for r in range(9) if state.can_place(rc_to_i(r, c), d)]
                if 2 <= len(rows) <= self.size:
                    col_patterns.append((c, tuple(rows)))

            for combo in combinations(col_patterns, self.size):
                cols = [c for c, _ in combo]
                rows_union = sorted(set(r for _, rows in combo for r in rows))
                if len(rows_union) != self.size:
                    continue

                eliminations = []
                for r in rows_union:
                    for c in range(9):
                        if c not in cols:
                            cell = rc_to_i(r, c)
                            if state.can_place(cell, d):
                                eliminations.append(Elimination(cell, d))

                if eliminations:
                    cause_cells = [
                        rc_to_i(r, c)
                        for c, rows in combo
                        for r in rows
                    ]
                    moves.append(
                        Move(
                            technique=self.name,
                            difficulty=self.difficulty,
                            reason=f"{self.name}: digit {d} forms a column-based fish on columns {[c+1 for c in cols]} and rows {[r+1 for r in rows_union]}.",
                            eliminations=eliminations,
                            cause_cells=cause_cells,
                        )
                    )

        return moves


class FinnedXWing(Technique):
    name = "Finned X-Wing"
    difficulty = 6

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for d in range(1, 10):
            row_cols = {
                row: [col for col in range(9) if state.can_place(rc_to_i(row, col), d)]
                for row in range(9)
            }
            for base_row, base_cols in row_cols.items():
                if len(base_cols) != 2:
                    continue

                base_set = set(base_cols)
                for fin_row, fin_cols in row_cols.items():
                    if fin_row == base_row or len(fin_cols) <= 2:
                        continue
                    fin_set = set(fin_cols)
                    fins = sorted(fin_set - base_set)
                    if not fins or not base_set.issubset(fin_set):
                        continue

                    fin_boxes = {BOX_OF[rc_to_i(fin_row, col)] for col in fins}
                    if len(fin_boxes) != 1:
                        continue
                    fin_box = next(iter(fin_boxes))
                    attached_cols = [
                        col for col in base_cols
                        if BOX_OF[rc_to_i(fin_row, col)] == fin_box
                    ]
                    if len(attached_cols) != 1:
                        continue

                    target_col = attached_cols[0]
                    eliminations = [
                        Elimination(cell, d)
                        for cell in (set(BOX_UNITS[fin_box]) & set(COL_UNITS[target_col]))
                        if ROW_OF[cell] not in (base_row, fin_row)
                        and COL_OF[cell] not in fins
                        and state.can_place(cell, d)
                    ]
                    if eliminations:
                        moves.append(
                            Move(
                                technique=self.name,
                                difficulty=self.difficulty,
                                reason=(
                                    f"Finned X-Wing on digit {d}: rows {base_row+1} and {fin_row+1} use "
                                    f"columns {[col+1 for col in base_cols]} with fins in box {fin_box+1}."
                                ),
                                eliminations=eliminations,
                                cause_cells=[
                                    rc_to_i(base_row, col)
                                    for col in base_cols
                                ] + [
                                    rc_to_i(fin_row, col)
                                    for col in fin_cols
                                ],
                            )
                        )

            col_rows = {
                col: [row for row in range(9) if state.can_place(rc_to_i(row, col), d)]
                for col in range(9)
            }
            for base_col, base_rows in col_rows.items():
                if len(base_rows) != 2:
                    continue

                base_set = set(base_rows)
                for fin_col, fin_rows in col_rows.items():
                    if fin_col == base_col or len(fin_rows) <= 2:
                        continue
                    fin_set = set(fin_rows)
                    fins = sorted(fin_set - base_set)
                    if not fins or not base_set.issubset(fin_set):
                        continue

                    fin_boxes = {BOX_OF[rc_to_i(row, fin_col)] for row in fins}
                    if len(fin_boxes) != 1:
                        continue
                    fin_box = next(iter(fin_boxes))
                    attached_rows = [
                        row for row in base_rows
                        if BOX_OF[rc_to_i(row, fin_col)] == fin_box
                    ]
                    if len(attached_rows) != 1:
                        continue

                    target_row = attached_rows[0]
                    eliminations = [
                        Elimination(cell, d)
                        for cell in (set(BOX_UNITS[fin_box]) & set(ROW_UNITS[target_row]))
                        if COL_OF[cell] not in (base_col, fin_col)
                        and ROW_OF[cell] not in fins
                        and state.can_place(cell, d)
                    ]
                    if eliminations:
                        moves.append(
                            Move(
                                technique=self.name,
                                difficulty=self.difficulty,
                                reason=(
                                    f"Finned X-Wing on digit {d}: columns {base_col+1} and {fin_col+1} use "
                                    f"rows {[row+1 for row in base_rows]} with fins in box {fin_box+1}."
                                ),
                                eliminations=eliminations,
                                cause_cells=[
                                    rc_to_i(row, base_col)
                                    for row in base_rows
                                ] + [
                                    rc_to_i(row, fin_col)
                                    for row in fin_rows
                                ],
                            )
                        )

        return moves


class FinnedSwordfish(Technique):
    def __init__(self, size: int = 3):
        self.size = size
        self.name = {3: "Finned Swordfish", 4: "Finned Jellyfish"}[size]
        self.difficulty = {3: 7, 4: 8}[size]

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        seen = set()

        for digit in range(1, 10):
            row_patterns = [
                (row, [col for col in range(9) if state.can_place(rc_to_i(row, col), digit)])
                for row in range(9)
            ]
            row_patterns = [(row, cols) for row, cols in row_patterns if 2 <= len(cols) <= self.size + 2]
            for combo in combinations(row_patterns, self.size):
                rows = [row for row, _ in combo]
                union_cols = sorted({col for _, cols in combo for col in cols})
                if len(union_cols) <= self.size:
                    continue

                for fish_cols in combinations(union_cols, self.size):
                    fish_col_set = set(fish_cols)
                    if any(not (set(cols) & fish_col_set) for _, cols in combo):
                        continue
                    if any(not any(col in cols for _, cols in combo) for col in fish_cols):
                        continue

                    fins = [
                        rc_to_i(row, col)
                        for row, cols in combo
                        for col in cols
                        if col not in fish_col_set
                    ]
                    if not fins:
                        continue
                    fin_boxes = {BOX_OF[cell] for cell in fins}
                    if len(fin_boxes) != 1:
                        continue

                    fin_box = next(iter(fin_boxes))
                    eliminations = [
                        Elimination(cell, digit)
                        for col in fish_cols
                        for cell in set(COL_UNITS[col]) & set(BOX_UNITS[fin_box])
                        if ROW_OF[cell] not in rows and state.can_place(cell, digit)
                    ]
                    if not eliminations:
                        continue

                    cause_cells = [
                        rc_to_i(row, col)
                        for row, cols in combo
                        for col in cols
                    ]
                    key = (
                        "row",
                        digit,
                        tuple(rows),
                        tuple(fish_cols),
                        tuple(sorted(fins)),
                        tuple(sorted((elimination.cell, elimination.digit) for elimination in eliminations)),
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    moves.append(
                        Move(
                            technique=self.name,
                            difficulty=self.difficulty,
                            reason=(
                                f"{self.name} on digit {digit}: rows {[row+1 for row in rows]} use "
                                f"columns {[col+1 for col in fish_cols]} with fins in box {fin_box+1}."
                            ),
                            eliminations=eliminations,
                            cause_cells=cause_cells,
                        )
                    )

            col_patterns = [
                (col, [row for row in range(9) if state.can_place(rc_to_i(row, col), digit)])
                for col in range(9)
            ]
            col_patterns = [(col, rows) for col, rows in col_patterns if 2 <= len(rows) <= self.size + 2]
            for combo in combinations(col_patterns, self.size):
                cols = [col for col, _ in combo]
                union_rows = sorted({row for _, rows in combo for row in rows})
                if len(union_rows) <= self.size:
                    continue

                for fish_rows in combinations(union_rows, self.size):
                    fish_row_set = set(fish_rows)
                    if any(not (set(rows) & fish_row_set) for _, rows in combo):
                        continue
                    if any(not any(row in rows for _, rows in combo) for row in fish_rows):
                        continue

                    fins = [
                        rc_to_i(row, col)
                        for col, rows in combo
                        for row in rows
                        if row not in fish_row_set
                    ]
                    if not fins:
                        continue
                    fin_boxes = {BOX_OF[cell] for cell in fins}
                    if len(fin_boxes) != 1:
                        continue

                    fin_box = next(iter(fin_boxes))
                    eliminations = [
                        Elimination(cell, digit)
                        for row in fish_rows
                        for cell in set(ROW_UNITS[row]) & set(BOX_UNITS[fin_box])
                        if COL_OF[cell] not in cols and state.can_place(cell, digit)
                    ]
                    if not eliminations:
                        continue

                    cause_cells = [
                        rc_to_i(row, col)
                        for col, rows in combo
                        for row in rows
                    ]
                    key = (
                        "col",
                        digit,
                        tuple(cols),
                        tuple(fish_rows),
                        tuple(sorted(fins)),
                        tuple(sorted((elimination.cell, elimination.digit) for elimination in eliminations)),
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    moves.append(
                        Move(
                            technique=self.name,
                            difficulty=self.difficulty,
                            reason=(
                                f"{self.name} on digit {digit}: columns {[col+1 for col in cols]} use "
                                f"rows {[row+1 for row in fish_rows]} with fins in box {fin_box+1}."
                            ),
                            eliminations=eliminations,
                            cause_cells=cause_cells,
                        )
                    )

        return moves


class FinnedJellyfish(FinnedSwordfish):
    def __init__(self):
        super().__init__(4)

