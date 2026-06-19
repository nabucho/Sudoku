from __future__ import annotations

from itertools import combinations
from typing import List, Tuple

from .common import *


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

def strong_links_for_digit(state: SudokuState, digit: int) -> List[Tuple[int, int]]:
    links = set()
    for unit in ALL_UNITS:
        cells = [cell for cell in unit if state.can_place(cell, digit)]
        if len(cells) == 2:
            links.add(tuple(sorted(cells)))
    return sorted(links)

class SimpleColoring(Technique):
    name = "Simple Coloring"
    difficulty = 6

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for digit in range(1, 10):
            graph = {}
            for a, b in strong_links_for_digit(state, digit):
                graph.setdefault(a, set()).add(b)
                graph.setdefault(b, set()).add(a)

            color = {}
            for start in sorted(graph):
                if start in color:
                    continue

                component = []
                queue = [start]
                color[start] = 0
                valid = True

                while queue and valid:
                    current = queue.pop(0)
                    component.append(current)
                    for neighbor in sorted(graph[current]):
                        next_color = 1 - color[current]
                        if neighbor not in color:
                            color[neighbor] = next_color
                            queue.append(neighbor)
                        elif color[neighbor] != next_color:
                            valid = False
                            break

                if not valid or len(component) < 4:
                    continue

                component_set = set(component)
                for bad_color in (0, 1):
                    same_color_cells = [cell for cell in component if color[cell] == bad_color]
                    if any(b in PEERS[a] for a, b in combinations(same_color_cells, 2)):
                        eliminations = [
                            Elimination(cell, digit)
                            for cell in same_color_cells
                            if state.can_place(cell, digit)
                        ]
                        if eliminations:
                            moves.append(
                                Move(
                                    technique=self.name,
                                    difficulty=self.difficulty,
                                    reason=(
                                        f"Digit {digit} coloring contradiction: two same-color candidates see each other, "
                                        "so that color can be removed."
                                    ),
                                    eliminations=eliminations,
                                    cause_cells=component,
                                )
                            )

                color_zero = {cell for cell in component if color[cell] == 0}
                color_one = {cell for cell in component if color[cell] == 1}
                eliminations = []
                for cell in range(81):
                    if cell in component_set or not state.can_place(cell, digit):
                        continue
                    if (PEERS[cell] & color_zero) and (PEERS[cell] & color_one):
                        eliminations.append(Elimination(cell, digit))

                if eliminations:
                    moves.append(
                        Move(
                            technique=self.name,
                            difficulty=self.difficulty,
                            reason=(
                                f"Digit {digit} candidate sees both colors in a strong-link coloring chain, "
                                f"so {digit} can be removed."
                            ),
                            eliminations=eliminations,
                            cause_cells=component,
                        )
                    )

        return moves

class TurbotFish(Technique):
    name = "Turbot Fish"
    difficulty = 6

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        seen = set()

        for digit in range(1, 10):
            strong_links = strong_links_for_digit(state, digit)
            for link1, link2 in combinations(strong_links, 2):
                if set(link1) & set(link2):
                    continue

                for weak1 in link1:
                    endpoint1 = link1[0] if link1[1] == weak1 else link1[1]
                    for weak2 in link2:
                        if weak2 not in PEERS[weak1]:
                            continue
                        endpoint2 = link2[0] if link2[1] == weak2 else link2[1]
                        if endpoint2 in PEERS[endpoint1]:
                            continue

                        cause_cells = sorted({*link1, *link2})
                        eliminations = [
                            Elimination(cell, digit)
                            for cell in (PEERS[endpoint1] & PEERS[endpoint2])
                            if cell not in cause_cells and state.can_place(cell, digit)
                        ]
                        if not eliminations:
                            continue

                        key = (
                            digit,
                            tuple(cause_cells),
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
                                    f"Turbot Fish on digit {digit}: strong links {cell_text(link1[0])}-{cell_text(link1[1])} "
                                    f"and {cell_text(link2[0])}-{cell_text(link2[1])} are connected by weak link "
                                    f"{cell_text(weak1)}-{cell_text(weak2)}."
                                ),
                                eliminations=eliminations,
                                cause_cells=cause_cells,
                            )
                        )

        return moves


# ============================================================
# Advanced techniques
# ============================================================

class Skyscraper(Technique):
    name = "Skyscraper"
    difficulty = 6

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for d in range(1, 10):
            # Row-based skyscraper
            row_pairs = []
            for r in range(9):
                cols = [c for c in range(9) if state.can_place(rc_to_i(r, c), d)]
                if len(cols) == 2:
                    row_pairs.append((r, cols[0], cols[1]))

            for (r1, a1, a2), (r2, b1, b2) in combinations(row_pairs, 2):
                s1 = {a1, a2}
                s2 = {b1, b2}
                common = s1 & s2
                if len(common) != 1:
                    continue

                common_col = next(iter(common))
                roof1 = (s1 - {common_col}).pop()
                roof2 = (s2 - {common_col}).pop()

                cell1 = rc_to_i(r1, roof1)
                cell2 = rc_to_i(r2, roof2)

                common_peers = PEERS[cell1] & PEERS[cell2]
                eliminations = [
                    Elimination(cell, d)
                    for cell in common_peers
                    if state.can_place(cell, d)
                ]
                if eliminations:
                    moves.append(
                        Move(
                            technique=self.name,
                            difficulty=self.difficulty,
                            reason=(
                                f"Skyscraper on digit {d}: rows {r1+1} and {r2+1} share base column "
                                f"{common_col+1}; roof cells are r{r1+1}c{roof1+1} and r{r2+1}c{roof2+1}."
                            ),
                            eliminations=eliminations,
                            cause_cells=[
                                rc_to_i(r1, a1),
                                rc_to_i(r1, a2),
                                rc_to_i(r2, b1),
                                rc_to_i(r2, b2),
                            ],
                        )
                    )

            # Column-based skyscraper
            col_pairs = []
            for c in range(9):
                rows = [r for r in range(9) if state.can_place(rc_to_i(r, c), d)]
                if len(rows) == 2:
                    col_pairs.append((c, rows[0], rows[1]))

            for (c1, a1, a2), (c2, b1, b2) in combinations(col_pairs, 2):
                s1 = {a1, a2}
                s2 = {b1, b2}
                common = s1 & s2
                if len(common) != 1:
                    continue

                common_row = next(iter(common))
                roof1 = (s1 - {common_row}).pop()
                roof2 = (s2 - {common_row}).pop()

                cell1 = rc_to_i(roof1, c1)
                cell2 = rc_to_i(roof2, c2)

                common_peers = PEERS[cell1] & PEERS[cell2]
                eliminations = [
                    Elimination(cell, d)
                    for cell in common_peers
                    if state.can_place(cell, d)
                ]
                if eliminations:
                    moves.append(
                        Move(
                            technique=self.name,
                            difficulty=self.difficulty,
                            reason=(
                                f"Skyscraper on digit {d}: columns {c1+1} and {c2+1} share base row "
                                f"{common_row+1}; roof cells are r{roof1+1}c{c1+1} and r{roof2+1}c{c2+1}."
                            ),
                            eliminations=eliminations,
                            cause_cells=[
                                rc_to_i(a1, c1),
                                rc_to_i(a2, c1),
                                rc_to_i(b1, c2),
                                rc_to_i(b2, c2),
                            ],
                        )
                    )

        return moves

class TwoStringKite(Technique):
    name = "Two-String Kite"
    difficulty = 6

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for d in range(1, 10):
            row_twos = []
            col_twos = []

            for r in range(9):
                cells = [rc_to_i(r, c) for c in range(9) if state.can_place(rc_to_i(r, c), d)]
                if len(cells) == 2:
                    row_twos.append((r, cells))

            for c in range(9):
                cells = [rc_to_i(r, c) for r in range(9) if state.can_place(rc_to_i(r, c), d)]
                if len(cells) == 2:
                    col_twos.append((c, cells))

            for r, row_cells in row_twos:
                for c, col_cells in col_twos:
                    # Need one row candidate and one column candidate in same box.
                    for row_cell in row_cells:
                        for col_cell in col_cells:
                            if row_cell == col_cell:
                                continue
                            if BOX_OF[row_cell] != BOX_OF[col_cell]:
                                continue

                            # endpoints = the "other" row and column cells
                            row_other = row_cells[0] if row_cells[1] == row_cell else row_cells[1]
                            col_other = col_cells[0] if col_cells[1] == col_cell else col_cells[1]

                            # Row-other and col-other are the kite tips.
                            common_peers = PEERS[row_other] & PEERS[col_other]
                            eliminations = [
                                Elimination(cell, d)
                                for cell in common_peers
                                if state.can_place(cell, d)
                            ]
                            if eliminations:
                                rr1, cc1 = i_to_rc(row_other)
                                rr2, cc2 = i_to_rc(col_other)
                                rrp, ccp = i_to_rc(row_cell)
                                rrc, ccc = i_to_rc(col_cell)

                                moves.append(
                                    Move(
                                        technique=self.name,
                                        difficulty=self.difficulty,
                                        reason=(
                                            f"Two-String Kite on digit {d}: row {r+1} and column {c+1} "
                                            f"are linked via same-box cells r{rrp+1}c{ccp+1} and r{rrc+1}c{ccc+1}; "
                                            f"therefore digit {d} can be removed from cells seeing both "
                                            f"r{rr1+1}c{cc1+1} and r{rr2+1}c{cc2+1}."
                                        ),
                                        eliminations=eliminations,
                                        cause_cells=sorted({*row_cells, *col_cells}),
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


# ============================================================
# Solver engine
# ============================================================

class EmptyRectangle(Technique):
    name = "Empty Rectangle"
    difficulty = 6

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for d in range(1, 10):
            for box_index, box in enumerate(BOX_UNITS):
                box_candidates = [cell for cell in box if state.can_place(cell, d)]
                if len(box_candidates) < 2:
                    continue

                box_rows = sorted({ROW_OF[cell] for cell in box})
                box_cols = sorted({COL_OF[cell] for cell in box})

                for row in box_rows:
                    for col in box_cols:
                        pivot = rc_to_i(row, col)
                        if state.can_place(pivot, d):
                            continue
                        if not all(ROW_OF[cell] == row or COL_OF[cell] == col for cell in box_candidates):
                            continue
                        if not any(ROW_OF[cell] == row for cell in box_candidates):
                            continue
                        if not any(COL_OF[cell] == col for cell in box_candidates):
                            continue

                        row_cells = [cell for cell in ROW_UNITS[row] if state.can_place(cell, d)]
                        if len(row_cells) == 2:
                            inside = [cell for cell in row_cells if cell in box]
                            outside = [cell for cell in row_cells if cell not in box]
                            if inside and outside:
                                outside_col = COL_OF[outside[0]]
                                eliminations = [
                                    Elimination(rc_to_i(target_row, outside_col), d)
                                    for target_row in box_rows
                                    if target_row != row
                                    and rc_to_i(target_row, outside_col) not in box
                                    and state.can_place(rc_to_i(target_row, outside_col), d)
                                ]
                                if eliminations:
                                    moves.append(
                                        Move(
                                            technique=self.name,
                                            difficulty=self.difficulty,
                                            reason=(
                                                f"Empty Rectangle on digit {d}: box {box_index+1} is covered by "
                                                f"row {row+1} and column {col+1}, with a strong row link to "
                                                f"{cell_text(outside[0])}."
                                            ),
                                            eliminations=eliminations,
                                            cause_cells=sorted({*box_candidates, *row_cells}),
                                        )
                                    )

                        col_cells = [cell for cell in COL_UNITS[col] if state.can_place(cell, d)]
                        if len(col_cells) == 2:
                            inside = [cell for cell in col_cells if cell in box]
                            outside = [cell for cell in col_cells if cell not in box]
                            if inside and outside:
                                outside_row = ROW_OF[outside[0]]
                                eliminations = [
                                    Elimination(rc_to_i(outside_row, target_col), d)
                                    for target_col in box_cols
                                    if target_col != col
                                    and rc_to_i(outside_row, target_col) not in box
                                    and state.can_place(rc_to_i(outside_row, target_col), d)
                                ]
                                if eliminations:
                                    moves.append(
                                        Move(
                                            technique=self.name,
                                            difficulty=self.difficulty,
                                            reason=(
                                                f"Empty Rectangle on digit {d}: box {box_index+1} is covered by "
                                                f"row {row+1} and column {col+1}, with a strong column link to "
                                                f"{cell_text(outside[0])}."
                                            ),
                                            eliminations=eliminations,
                                            cause_cells=sorted({*box_candidates, *col_cells}),
                                        )
                                    )

        return moves

