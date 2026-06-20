from __future__ import annotations

from typing import List

from .common import (
    ALL_UNITS,
    BOX_OF,
    BOX_UNITS,
    CELL_INDICES,
    CELL_UNITS,
    COL_OF,
    COL_UNITS,
    DIGIT_VALUES,
    ROW_OF,
    ROW_UNITS,
    CellGroup,
    Elimination,
    EliminationKey,
    Move,
    Placement,
    SudokuState,
    Technique,
    UnitCandidateCache,
    bit_count,
    candidates_consistency_ok,
    cell_text,
    digits_from_mask,
    elimination_key,
    is_single,
    pair_combinations,
    place_digit_in_candidates,
    placement_text,
    rc_to_i,
    shared_peer_eliminations,
    single_digit,
    sized_combinations,
    source_digit_roles_for_cells,
    unit_text,
    unsolved_cells,
    zip_pairs,
)

RECTANGLES = [
    (
        [
            rc_to_i(r1, c1),
            rc_to_i(r1, c2),
            rc_to_i(r2, c1),
            rc_to_i(r2, c2),
        ],
        r1,
        r2,
        c1,
        c2,
    )
    for r1, r2 in pair_combinations(range(9))
    for c1, c2 in pair_combinations(range(9))
    if len(
        {
            BOX_OF[rc_to_i(r1, c1)],
            BOX_OF[rc_to_i(r1, c2)],
            BOX_OF[rc_to_i(r2, c1)],
            BOX_OF[rc_to_i(r2, c2)],
        }
    )
    == 2
]
UniqueRectangleType3SeenKey = tuple[CellGroup, CellGroup, int, int, EliminationKey]
AvoidableRectangleSeenKey = tuple[CellGroup, int, int]


class UniqueRectangleType1(Technique):
    """Eliminate deadly-pair digits from the only non-pair rectangle corner.

    See `doc/unique-rectangle-type-1.md` for the full technique description.
    """

    name = "Unique Rectangle Type 1"
    difficulty = 7

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for cells, r1, r2, c1, c2 in RECTANGLES:
            masks = [state.candidate_mask(cell) for cell in cells]
            bivalue_masks = [m for m in masks if bit_count(m) == 2]
            if len(bivalue_masks) < 3:
                continue

            counts: dict[int, int] = {}
            for m in bivalue_masks:
                counts[m] = counts.get(m, 0) + 1

            pair_mask = None
            for m, cnt in counts.items():
                if cnt >= 3 and bit_count(m) == 2:
                    pair_mask = m
                    break

            if pair_mask is None:
                continue

            pair_cells = [cells[idx] for idx, m in enumerate[int](masks) if m == pair_mask]
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
                moves.append(
                    Move(
                        technique=self.name,
                        difficulty=self.difficulty,
                        reason=(
                            f"Unique Rectangle Type 1 on rows {r1+1},{r2+1} and columns {c1+1},{c2+1}: "
                            f"three corners form deadly pair {pair_digits}, so {cell_text(odd_cell)} "
                            f"cannot keep both of those digits."
                        ),
                        eliminations=eliminations,
                        cause_cells=cells,
                        source_digit_roles=source_digit_roles_for_cells(cells, pair_digits),
                    )
                )

        return moves


class UniqueRectangleType2(Technique):
    """Eliminate a shared extra digit from peers of two extra-candidate corners.

    See `doc/unique-rectangle-type-2.md` for the full technique description.
    """

    name = "Unique Rectangle Type 2"
    difficulty = 7

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for cells, _, _, _, _ in RECTANGLES:
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
                eliminations = shared_peer_eliminations(
                    state,
                    (extra_cells[0], extra_cells[1]),
                    extra_digit,
                    blocked=cells,
                )
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
                            source_digit_roles={
                                **source_digit_roles_for_cells(cells, pair_digits),
                                **source_digit_roles_for_cells(extra_cells, [extra_digit], "secondary"),
                            },
                        )
                    )

        return moves


class UniqueRectangleType3(Technique):
    """Use extra candidates in a unique rectangle as a subset pattern.

    See `doc/unique-rectangle-type-3.md` for the full technique description.
    """

    name = "Unique Rectangle Type 3"
    difficulty = 7

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        seen: set[UniqueRectangleType3SeenKey] = set[UniqueRectangleType3SeenKey]()

        for cells, _, _, _, _ in RECTANGLES:
            masks = {cell: state.candidate_mask(cell) for cell in cells}
            for pair_mask in {mask for mask in masks.values() if bit_count(mask) == 2}:
                pair_cells = [cell for cell in cells if masks[cell] == pair_mask]
                floor_cells = [
                    cell
                    for cell in cells
                    if cell not in pair_cells and (masks[cell] & pair_mask) == pair_mask and masks[cell] != pair_mask
                ]
                if len(pair_cells) != 2 or len(floor_cells) != 2:
                    continue

                shared_units = [
                    (unit_index, unit)
                    for unit_index, unit in enumerate[list[int]](ALL_UNITS)
                    if floor_cells[0] in unit and floor_cells[1] in unit
                ]
                extra_mask = (masks[floor_cells[0]] | masks[floor_cells[1]]) & ~pair_mask
                subset_size = bit_count(extra_mask)
                if subset_size < 2:
                    continue

                for unit_index, unit in shared_units:
                    subset_candidates = [
                        cell
                        for cell in unit
                        if cell not in cells
                        and not is_single(state.candidate_mask(cell))
                        and state.candidate_mask(cell) & extra_mask
                        and (state.candidate_mask(cell) & ~extra_mask) == 0
                    ]
                    for helpers in sized_combinations(subset_candidates, subset_size - 1):
                        union_mask = extra_mask
                        for helper in helpers:
                            union_mask |= state.candidate_mask(helper)
                        if union_mask != extra_mask:
                            continue

                        subset_cells = set[int](floor_cells) | set[int](helpers)
                        eliminations = [
                            Elimination(cell, digit)
                            for cell in unit
                            if cell not in subset_cells
                            for digit in digits_from_mask(extra_mask)
                            if state.can_place(cell, digit)
                        ]
                        if not eliminations:
                            continue

                        key = (
                            CellGroup(cells),
                            CellGroup(sorted(helpers)),
                            unit_index,
                            extra_mask,
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
                                    f"Unique Rectangle Type 3 on {', '.join(cell_text(cell) for cell in cells)}: "
                                    f"extra digits {digits_from_mask(extra_mask)} form a naked subset in {unit_text(unit_index)}."
                                ),
                                eliminations=eliminations,
                                cause_cells=sorted({*cells, *helpers}),
                                source_digit_roles=source_digit_roles_for_cells(
                                    sorted({*floor_cells, *helpers}),
                                    digits_from_mask(extra_mask),
                                ),
                            )
                        )

        return moves


class UniqueRectangleType4(Technique):
    """Use strong links to remove one deadly-pair digit from rectangle corners.

    See `doc/unique-rectangle-type-4.md` for the full technique description.
    """

    name = "Unique Rectangle Type 4"
    difficulty = 7

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        candidate_cache = UnitCandidateCache(state)

        for cells, _, _, _, _ in RECTANGLES:
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
                        cells_for_digit = candidate_cache.unsolved_cells_with_candidate(
                            unit,
                            strong_digit,
                        )
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
                                    source_digit_roles={
                                        **source_digit_roles_for_cells(cells, pair_digits),
                                        **source_digit_roles_for_cells(floor_cells, [strong_digit], "secondary"),
                                    },
                                )
                            )

        return moves


class AvoidableRectangle(Technique):
    """Avoid non-given rectangle patterns that would allow non-unique solutions.

    See `doc/avoidable-rectangle.md` for the full technique description.
    """

    name = "Avoidable Rectangle"
    difficulty = 7

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        seen: set[AvoidableRectangleSeenKey] = set[AvoidableRectangleSeenKey]()

        for cells, _, _, _, _ in RECTANGLES:
            if any(cell in state.given_cells for cell in cells):
                continue

            for digit_a, digit_b in pair_combinations(DIGIT_VALUES):
                patterns = (
                    (digit_a, digit_b, digit_b, digit_a),
                    (digit_b, digit_a, digit_a, digit_b),
                )
                for pattern in patterns:
                    solved_corners = [
                        cell
                        for cell, expected_digit in zip_pairs(cells, pattern)
                        if is_single(state.candidate_mask(cell))
                        and single_digit(state.candidate_mask(cell)) == expected_digit
                    ]
                    if len(solved_corners) != 3:
                        continue

                    target_index = next(
                        index
                        for index, cell in enumerate[int](cells)
                        if cell not in solved_corners
                    )
                    target = cells[target_index]
                    target_digit = pattern[target_index]
                    if is_single(state.candidate_mask(target)):
                        continue
                    if not state.can_place(target, target_digit):
                        continue

                    key = (CellGroup(cells), target, target_digit)
                    if key in seen:
                        continue
                    seen.add(key)

                    moves.append(
                        Move(
                            technique=self.name,
                            difficulty=self.difficulty,
                            reason=(
                                f"Avoidable Rectangle on {', '.join(cell_text(cell) for cell in cells)}: "
                                f"placing {target_digit} in {cell_text(target)} would complete a non-given "
                                f"{digit_a}/{digit_b} deadly rectangle."
                            ),
                            eliminations=[Elimination(target, target_digit)],
                            cause_cells=cells,
                            source_digit_roles=source_digit_roles_for_cells(cells, [digit_a, digit_b]),
                        )
                    )

        return moves


class BUGPlusOne(Technique):
    """Place the correcting digit in the only tri-value cell of a BUG pattern.

    See `doc/bug-plus-one.md` for the full technique description.
    """

    name = "BUG+1"
    difficulty = 7

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        unsolved = unsolved_cells(state)
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
                moves.append(
                    Move(
                        technique=self.name,
                        difficulty=self.difficulty,
                        reason=(
                            f"BUG+1: {cell_text(cell)} is the only tri-value cell, "
                            f"so digit {d} must be placed there."
                        ),
                        placements=[Placement(cell, d)],
                        cause_cells=[cell],
                        source_digit_roles=source_digit_roles_for_cells([cell], [d]),
                    )
                )

        return moves


class Nishio(Technique):
    """Eliminate candidates whose assumption leads to contradiction.

    See `doc/nishio.md` for the full technique description.
    """

    name = "Nishio"
    difficulty = 8

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for cell in CELL_INDICES:
            cell_mask = state.candidate_mask(cell)
            if is_single(cell_mask):
                continue

            for digit in digits_from_mask(cell_mask):
                candidates = state.candidates[:]
                if place_digit_in_candidates(candidates, cell, digit) and candidates_consistency_ok(candidates):
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
                        source_digit_roles=source_digit_roles_for_cells([cell], [digit]),
                    )
                )

        return moves

