"""Basic and finned fish techniques for row/column candidate patterns."""

from __future__ import annotations

from typing import List

from .common import (
    BOX_OF,
    BOX_UNITS,
    COL_OF,
    COL_UNITS,
    DIGIT_VALUES,
    MASK_BIT_COUNTS,
    MASK_INDEXES,
    ROW_OF,
    ROW_UNITS,
    CellGroup,
    Elimination,
    EliminationKey,
    Move,
    SudokuState,
    Technique,
    elimination_key,
    rc_to_i,
    sized_combinations,
    source_digit_roles_for_cells,
)

LINE_MASK = (1 << 9) - 1
FinnedFishSeenKey = tuple[
    str,
    int,
    CellGroup,
    CellGroup,
    CellGroup,
    EliminationKey,
]
BOX_COL_CELLS = [
    [CellGroup(cell for cell in BOX_UNITS[box] if COL_OF[cell] == col) for col in range(9)]
    for box in range(9)
]
BOX_ROW_CELLS = [
    [CellGroup(cell for cell in BOX_UNITS[box] if ROW_OF[cell] == row) for row in range(9)]
    for box in range(9)
]
BOX_COL_MASKS = [
    sum(1 << col for col in {COL_OF[cell] for cell in BOX_UNITS[box]})
    for box in range(9)
]
BOX_ROW_MASKS = [
    sum(1 << row for row in {ROW_OF[cell] for cell in BOX_UNITS[box]})
    for box in range(9)
]


def _indexes_from_mask(mask: int) -> CellGroup:
    """Return zero-based row/column indexes represented by a bit mask."""
    return CellGroup(MASK_INDEXES[mask])


def _mask_combinations(mask: int, size: int):
    """Yield bit masks containing `size` selected bits from `mask`."""
    if size < 0 or MASK_BIT_COUNTS[mask] < size:
        return
    if size == 0:
        yield 0
        return
    for indexes in sized_combinations(_indexes_from_mask(mask), size):
        yield sum(1 << index for index in indexes)


def _candidate_line_masks(state: SudokuState, digit: int) -> tuple[list[int], list[int]]:
    """Return row column-masks and column row-masks for a candidate digit."""
    row_masks = [0] * 9
    col_masks = [0] * 9
    for row in range(9):
        for col in range(9):
            if state.can_place(rc_to_i(row, col), digit):
                row_masks[row] |= 1 << col
                col_masks[col] |= 1 << row
    return row_masks, col_masks


class Fish(Technique):
    """Find X-Wing, Swordfish, or Jellyfish candidate eliminations.

    See `doc/x-wing.md`, `doc/swordfish.md`, and `doc/jellyfish.md` for
    the full technique descriptions.
    """

    def __init__(self, size: int):
        self.size = size
        self.name = {2: "X-Wing", 3: "Swordfish", 4: "Jellyfish"}[size]
        self.difficulty = {2: 5, 3: 6, 4: 7}[size]

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for digit in DIGIT_VALUES:
            row_masks, col_masks = _candidate_line_masks(state, digit)

            # Row-based fish
            row_patterns = [
                (row, mask)
                for row, mask in enumerate[int](row_masks)
                if 2 <= MASK_BIT_COUNTS[mask] <= self.size
            ]

            for combo in sized_combinations(row_patterns, self.size):
                fish_row_indexes = [row for row, _ in combo]
                fish_rows_mask = sum(1 << row for row in fish_row_indexes)
                fish_col_mask = 0
                for _, col_mask in combo:
                    fish_col_mask |= col_mask
                if MASK_BIT_COUNTS[fish_col_mask] != self.size:
                    continue
                fish_cols = _indexes_from_mask(fish_col_mask)

                eliminations = []
                for col in fish_cols:
                    for row in range(9):
                        if not (fish_rows_mask & (1 << row)):
                            cell = rc_to_i(row, col)
                            if state.can_place(cell, digit):
                                eliminations.append(Elimination(cell, digit))

                if eliminations:
                    cause_cells = [
                        rc_to_i(row, col)
                        for row, col_mask in combo
                        for col in _indexes_from_mask(col_mask)
                    ]
                    moves.append(
                        Move(
                            technique=self.name,
                            difficulty=self.difficulty,
                            reason=f"{self.name}: digit {digit} forms a row-based fish on rows {[row+1 for row in fish_row_indexes]} and columns {[col+1 for col in fish_cols]}.",
                            eliminations=eliminations,
                            cause_cells=cause_cells,
                            source_digit_roles=source_digit_roles_for_cells(cause_cells, [digit]),
                        )
                    )

            # Column-based fish
            col_patterns = [
                (col, mask)
                for col, mask in enumerate[int](col_masks)
                if 2 <= MASK_BIT_COUNTS[mask] <= self.size
            ]

            for combo in sized_combinations(col_patterns, self.size):
                fish_col_indexes = [col for col, _ in combo]
                fish_cols_mask = sum(1 << col for col in fish_col_indexes)
                fish_row_mask = 0
                for _, row_mask in combo:
                    fish_row_mask |= row_mask
                if MASK_BIT_COUNTS[fish_row_mask] != self.size:
                    continue
                fish_rows = _indexes_from_mask(fish_row_mask)

                eliminations = []
                for row in fish_rows:
                    for col in range(9):
                        if not (fish_cols_mask & (1 << col)):
                            cell = rc_to_i(row, col)
                            if state.can_place(cell, digit):
                                eliminations.append(Elimination(cell, digit))

                if eliminations:
                    cause_cells = [
                        rc_to_i(row, col)
                        for col, row_mask in combo
                        for row in _indexes_from_mask(row_mask)
                    ]
                    moves.append(
                        Move(
                            technique=self.name,
                            difficulty=self.difficulty,
                            reason=f"{self.name}: digit {digit} forms a column-based fish on columns {[col+1 for col in fish_col_indexes]} and rows {[row+1 for row in fish_rows]}.",
                            eliminations=eliminations,
                            cause_cells=cause_cells,
                            source_digit_roles=source_digit_roles_for_cells(cause_cells, [digit]),
                        )
                    )

        return moves


class FinnedXWing(Technique):
    """Find Finned X-Wing eliminations where a fin restricts targets.

    See `doc/finned-x-wing.md` for the full technique description.
    """

    name = "Finned X-Wing"
    difficulty = 6

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for d in DIGIT_VALUES:
            row_cols = {
                row: [col for col in range(9) if state.can_place(rc_to_i(row, col), d)]
                for row in range(9)
            }
            for base_row, base_cols in row_cols.items():
                if len(base_cols) != 2:
                    continue

                base_set = set[int](base_cols)
                for fin_row, fin_cols in row_cols.items():
                    if fin_row == base_row or len(fin_cols) <= 2:
                        continue
                    fin_set = set[int](fin_cols)
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
                        for cell in (set[int](BOX_UNITS[fin_box]) & set[int](COL_UNITS[target_col]))
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
                                source_digit_roles=source_digit_roles_for_cells(
                                    [
                                        rc_to_i(base_row, col)
                                        for col in base_cols
                                    ] + [
                                        rc_to_i(fin_row, col)
                                        for col in fin_cols
                                    ],
                                    [d],
                                ),
                            )
                        )

            col_rows = {
                col: [row for row in range(9) if state.can_place(rc_to_i(row, col), d)]
                for col in range(9)
            }
            for base_col, base_rows in col_rows.items():
                if len(base_rows) != 2:
                    continue

                base_set = set[int](base_rows)
                for fin_col, fin_rows in col_rows.items():
                    if fin_col == base_col or len(fin_rows) <= 2:
                        continue
                    fin_set = set[int](fin_rows)
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
                        for cell in (set[int](BOX_UNITS[fin_box]) & set[int](ROW_UNITS[target_row]))
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
                                source_digit_roles=source_digit_roles_for_cells(
                                    [
                                        rc_to_i(row, base_col)
                                        for row in base_rows
                                    ] + [
                                        rc_to_i(row, fin_col)
                                        for row in fin_rows
                                    ],
                                    [d],
                                ),
                            )
                        )

        return moves


class FinnedSwordfish(Technique):
    """Find Finned Swordfish or Finned Jellyfish eliminations.

    See `doc/finned-swordfish.md` for the full technique description.
    """

    def __init__(self, size: int = 3):
        self.size = size
        self.name = {3: "Finned Swordfish", 4: "Finned Jellyfish"}[size]
        self.difficulty = {3: 7, 4: 8}[size]

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        seen: set[FinnedFishSeenKey] = set[FinnedFishSeenKey]()

        for digit in DIGIT_VALUES:
            row_masks, col_masks = _candidate_line_masks(state, digit)
            row_patterns = [
                (row, mask)
                for row, mask in enumerate[int](row_masks)
                if 2 <= MASK_BIT_COUNTS[mask] <= self.size + 2
            ]
            for combo in sized_combinations(row_patterns, self.size):
                rows = [row for row, _ in combo]
                rows_mask = sum(1 << row for row in rows)
                union_col_mask = 0
                for _, col_mask in combo:
                    union_col_mask |= col_mask
                if MASK_BIT_COUNTS[union_col_mask] <= self.size:
                    continue

                for fin_box in range(9):
                    required_fish_col_mask = 0
                    allowed_fin_col_mask = BOX_COL_MASKS[fin_box]
                    allowed_fin_row_mask = BOX_ROW_MASKS[fin_box]
                    for row, col_mask in combo:
                        allowed_mask = allowed_fin_col_mask if allowed_fin_row_mask & (1 << row) else 0
                        required_fish_col_mask |= col_mask & ~allowed_mask
                    if MASK_BIT_COUNTS[required_fish_col_mask] > self.size:
                        continue

                    optional_col_mask = union_col_mask & ~required_fish_col_mask
                    needed_cols = self.size - MASK_BIT_COUNTS[required_fish_col_mask]
                    for extra_col_mask in _mask_combinations(optional_col_mask, needed_cols):
                        fish_col_mask = required_fish_col_mask | extra_col_mask
                        if MASK_BIT_COUNTS[fish_col_mask] != self.size:
                            continue
                        if any(not (col_mask & fish_col_mask) for _, col_mask in combo):
                            continue

                        fins = [
                            rc_to_i(row, col)
                            for row, col_mask in combo
                            for col in _indexes_from_mask(col_mask & ~fish_col_mask & LINE_MASK)
                        ]
                        if not fins:
                            continue

                        fish_cols = _indexes_from_mask(fish_col_mask)
                        eliminations = [
                            Elimination(cell, digit)
                            for col in fish_cols
                            for cell in BOX_COL_CELLS[fin_box][col]
                            if not (rows_mask & (1 << ROW_OF[cell])) and state.can_place(cell, digit)
                        ]
                        if not eliminations:
                            continue

                        cause_cells = [
                            rc_to_i(row, col)
                            for row, col_mask in combo
                            for col in _indexes_from_mask(col_mask)
                        ]
                        key = (
                            "row",
                            digit,
                            CellGroup(rows),
                            CellGroup(fish_cols),
                            CellGroup(sorted(fins)),
                            elimination_key(eliminations, sorted_key=True),
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
                                source_digit_roles=source_digit_roles_for_cells(cause_cells, [digit]),
                            )
                        )

            col_patterns = [
                (col, mask)
                for col, mask in enumerate[int](col_masks)
                if 2 <= MASK_BIT_COUNTS[mask] <= self.size + 2
            ]
            for combo in sized_combinations(col_patterns, self.size):
                cols = [col for col, _ in combo]
                cols_mask = sum(1 << col for col in cols)
                union_row_mask = 0
                for _, row_mask in combo:
                    union_row_mask |= row_mask
                if MASK_BIT_COUNTS[union_row_mask] <= self.size:
                    continue

                for fin_box in range(9):
                    required_fish_row_mask = 0
                    allowed_fin_row_mask = BOX_ROW_MASKS[fin_box]
                    allowed_fin_col_mask = BOX_COL_MASKS[fin_box]
                    for col, row_mask in combo:
                        allowed_mask = allowed_fin_row_mask if allowed_fin_col_mask & (1 << col) else 0
                        required_fish_row_mask |= row_mask & ~allowed_mask
                    if MASK_BIT_COUNTS[required_fish_row_mask] > self.size:
                        continue

                    optional_row_mask = union_row_mask & ~required_fish_row_mask
                    needed_rows = self.size - MASK_BIT_COUNTS[required_fish_row_mask]
                    for extra_row_mask in _mask_combinations(optional_row_mask, needed_rows):
                        fish_row_mask = required_fish_row_mask | extra_row_mask
                        if MASK_BIT_COUNTS[fish_row_mask] != self.size:
                            continue
                        if any(not (row_mask & fish_row_mask) for _, row_mask in combo):
                            continue

                        fins = [
                            rc_to_i(row, col)
                            for col, row_mask in combo
                            for row in _indexes_from_mask(row_mask & ~fish_row_mask & LINE_MASK)
                        ]
                        if not fins:
                            continue

                        fish_rows = _indexes_from_mask(fish_row_mask)
                        eliminations = [
                            Elimination(cell, digit)
                            for row in fish_rows
                            for cell in BOX_ROW_CELLS[fin_box][row]
                            if not (cols_mask & (1 << COL_OF[cell])) and state.can_place(cell, digit)
                        ]
                        if not eliminations:
                            continue

                        cause_cells = [
                            rc_to_i(row, col)
                            for col, row_mask in combo
                            for row in _indexes_from_mask(row_mask)
                        ]
                        key = (
                            "col",
                            digit,
                            CellGroup(cols),
                            CellGroup(fish_rows),
                            CellGroup(sorted(fins)),
                            elimination_key(eliminations, sorted_key=True),
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
                                source_digit_roles=source_digit_roles_for_cells(cause_cells, [digit]),
                            )
                        )

        return moves


class FinnedJellyfish(FinnedSwordfish):
    """Specialized finned fish technique for size-four Jellyfish patterns.

    See `doc/finned-jellyfish.md` for the full technique description.
    """

    def __init__(self):
        super().__init__(4)

