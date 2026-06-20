from __future__ import annotations

from typing import List

from .coloring import strong_links_for_digit
from .common import (
    BOX_OF,
    BOX_UNITS,
    COL_OF,
    COL_UNITS,
    DIGIT_VALUES,
    PEERS,
    ROW_OF,
    ROW_UNITS,
    Elimination,
    Move,
    SudokuState,
    Technique,
    UnitCandidateCache,
    cell_text,
    pair_combinations,
    rc_to_i,
    shared_peer_eliminations,
)


class TurbotFish(Technique):
    """Find Turbot Fish eliminations from connected single-digit links.

    See `doc/turbot-fish.md` for the full technique description.
    """

    name = "Turbot Fish"
    difficulty = 6

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        seen: set[tuple[int, tuple[int, ...], tuple[tuple[int, int], ...]]] = set[
            tuple[int, tuple[int, ...], tuple[tuple[int, int], ...]]
        ]()
        candidate_cache = UnitCandidateCache(state)

        for digit in DIGIT_VALUES:
            strong_links = strong_links_for_digit(state, digit, candidate_cache)
            for link1, link2 in pair_combinations(strong_links):
                if set[int](link1) & set[int](link2):
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
                        eliminations = shared_peer_eliminations(state, (endpoint1, endpoint2), digit, blocked=cause_cells)
                        if not eliminations:
                            continue

                        key = (
                            digit,
                            tuple[int, ...](cause_cells),
                            tuple[tuple[int, int], ...](
                                sorted((elimination.cell, elimination.digit) for elimination in eliminations)
                            ),
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
    """Find Skyscraper eliminations from two parallel strong links.

    See `doc/skyscraper.md` for the full technique description.
    """

    name = "Skyscraper"
    difficulty = 6

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for digit in DIGIT_VALUES:
            # Row-based skyscraper
            row_pairs: list[tuple[int, int, int]] = []
            for r in range(9):
                cols = [c for c in range(9) if state.can_place(rc_to_i(r, c), digit)]
                if len(cols) == 2:
                    row_pairs.append((r, cols[0], cols[1]))

            for (r1, a1, a2), (r2, b1, b2) in pair_combinations(row_pairs):
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

                eliminations = shared_peer_eliminations(state, (cell1, cell2), digit)
                if eliminations:
                    moves.append(
                        Move(
                            technique=self.name,
                            difficulty=self.difficulty,
                            reason=(
                                f"Skyscraper on digit {digit}: rows {r1+1} and {r2+1} share base column "
                                f"{common_col+1}; roof cells are {cell_text(cell1)} and {cell_text(cell2)}."
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
            col_pairs: list[tuple[int, int, int]] = []
            for c in range(9):
                rows = [r for r in range(9) if state.can_place(rc_to_i(r, c), digit)]
                if len(rows) == 2:
                    col_pairs.append((c, rows[0], rows[1]))

            for (c1, a1, a2), (c2, b1, b2) in pair_combinations(col_pairs):
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

                eliminations = shared_peer_eliminations(state, (cell1, cell2), digit)
                if eliminations:
                    moves.append(
                        Move(
                            technique=self.name,
                            difficulty=self.difficulty,
                            reason=(
                                f"Skyscraper on digit {digit}: columns {c1+1} and {c2+1} share base row "
                                f"{common_row+1}; roof cells are {cell_text(cell1)} and {cell_text(cell2)}."
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
    """Find Two-String Kite eliminations using row and column strong links.

    See `doc/two-string-kite.md` for the full technique description.
    """

    name = "Two-String Kite"
    difficulty = 6

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for digit in DIGIT_VALUES:
            row_twos: list[tuple[int, list[int]]] = []
            col_twos: list[tuple[int, list[int]]] = []

            for r in range(9):
                cells = [rc_to_i(r, c) for c in range(9) if state.can_place(rc_to_i(r, c), digit)]
                if len(cells) == 2:
                    row_twos.append((r, cells))

            for c in range(9):
                cells = [rc_to_i(r, c) for r in range(9) if state.can_place(rc_to_i(r, c), digit)]
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
                            eliminations = shared_peer_eliminations(state, (row_other, col_other), digit)
                            if eliminations:
                                moves.append(
                                    Move(
                                        technique=self.name,
                                        difficulty=self.difficulty,
                                        reason=(
                                            f"Two-String Kite on digit {digit}: row {r+1} and column {c+1} "
                                            f"are linked via same-box cells {cell_text(row_cell)} and {cell_text(col_cell)}; "
                                            f"therefore digit {digit} can be removed from cells seeing both "
                                            f"{cell_text(row_other)} and {cell_text(col_other)}."
                                        ),
                                        eliminations=eliminations,
                                        cause_cells=sorted({*row_cells, *col_cells}),
                                    )
                                )

        return moves


class EmptyRectangle(Technique):
    """Find Empty Rectangle eliminations using box cover and strong links.

    See `doc/empty-rectangle.md` for the full technique description.
    """

    name = "Empty Rectangle"
    difficulty = 6

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        candidate_cache = UnitCandidateCache(state)

        for digit in DIGIT_VALUES:
            for box_index, box in enumerate[list[int]](BOX_UNITS):
                box_candidates = candidate_cache.unsolved_cells_with_candidate(box, digit)
                if len(box_candidates) < 2:
                    continue

                box_rows = sorted({ROW_OF[cell] for cell in box})
                box_cols = sorted({COL_OF[cell] for cell in box})

                for eri_row in box_rows:
                    for eri_col in box_cols:
                        eri = rc_to_i(eri_row, eri_col)
                        if state.can_place(eri, digit):
                            continue
                        if not all(ROW_OF[cell] == eri_row or COL_OF[cell] == eri_col for cell in box_candidates):
                            continue
                        if not any(ROW_OF[cell] == eri_row for cell in box_candidates):
                            continue
                        if not any(COL_OF[cell] == eri_col for cell in box_candidates):
                            continue

                        for strong_row in range(9):
                            if strong_row in box_rows:
                                continue
                            row_cells = candidate_cache.unsolved_cells_with_candidate(
                                ROW_UNITS[strong_row],
                                digit,
                            )
                            if len(row_cells) != 2:
                                continue
                            near = [cell for cell in row_cells if COL_OF[cell] == eri_col]
                            if len(near) != 1:
                                continue
                            far = row_cells[0] if row_cells[1] == near[0] else row_cells[1]
                            target = rc_to_i(eri_row, COL_OF[far])
                            if target in box or not state.can_place(target, digit):
                                continue
                            moves.append(
                                Move(
                                    technique=self.name,
                                    difficulty=self.difficulty,
                                    reason=(
                                        f"Empty Rectangle on digit {digit}: box {box_index+1} is covered by "
                                        f"row {eri_row+1} and column {eri_col+1}; strong row link "
                                        f"{cell_text(near[0])}-{cell_text(far)} eliminates {digit} from {cell_text(target)}."
                                    ),
                                    eliminations=[Elimination(target, digit)],
                                    cause_cells=sorted({*box_candidates, *row_cells}),
                                )
                            )

                        for strong_col in range(9):
                            if strong_col in box_cols:
                                continue
                            col_cells = candidate_cache.unsolved_cells_with_candidate(
                                COL_UNITS[strong_col],
                                digit,
                            )
                            if len(col_cells) != 2:
                                continue
                            near = [cell for cell in col_cells if ROW_OF[cell] == eri_row]
                            if len(near) != 1:
                                continue
                            far = col_cells[0] if col_cells[1] == near[0] else col_cells[1]
                            target = rc_to_i(ROW_OF[far], eri_col)
                            if target in box or not state.can_place(target, digit):
                                continue
                            moves.append(
                                Move(
                                    technique=self.name,
                                    difficulty=self.difficulty,
                                    reason=(
                                        f"Empty Rectangle on digit {digit}: box {box_index+1} is covered by "
                                        f"row {eri_row+1} and column {eri_col+1}; strong column link "
                                        f"{cell_text(near[0])}-{cell_text(far)} eliminates {digit} from {cell_text(target)}."
                                    ),
                                    eliminations=[Elimination(target, digit)],
                                    cause_cells=sorted({*box_candidates, *col_cells}),
                                )
                            )

        return moves

