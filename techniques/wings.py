from __future__ import annotations

from itertools import combinations
from typing import List

from .common import (
    ALL_UNITS,
    Elimination,
    Move,
    PEERS,
    SudokuState,
    Technique,
    bit,
    bit_count,
    cell_text,
    digits_from_mask,
    single_digit,
)


class XYWing(Technique):
    name = "XY-Wing"
    difficulty = 6

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        bivalue_cells = [cell for cell in range(81) if state.is_bivalue(cell)]

        for pivot in bivalue_cells:
            pivot_mask = state.candidate_mask(pivot)
            x, y = digits_from_mask(pivot_mask)

            x_mask = bit(x)
            y_mask = bit(y)

            xz_peers = []
            yz_peers = []

            for peer in PEERS[pivot]:
                if not state.is_bivalue(peer):
                    continue
                pm = state.candidate_mask(peer)

                # xz pincer: contains x but not y
                if (pm & x_mask) and not (pm & y_mask):
                    if bit_count(pm) == 2:
                        xz_peers.append(peer)

                # yz pincer: contains y but not x
                if (pm & y_mask) and not (pm & x_mask):
                    if bit_count(pm) == 2:
                        yz_peers.append(peer)

            for a in xz_peers:
                z_mask = state.candidate_mask(a) & ~x_mask
                if bit_count(z_mask) != 1:
                    continue
                z = single_digit(z_mask)

                for b in yz_peers:
                    if a == b:
                        continue
                    if state.candidate_mask(b) != (y_mask | z_mask):
                        continue

                    common = (PEERS[a] & PEERS[b]) - {pivot}
                    eliminations = [
                        Elimination(cell, z)
                        for cell in common
                        if state.can_place(cell, z)
                    ]
                    if eliminations:
                        moves.append(
                            Move(
                                technique=self.name,
                                difficulty=self.difficulty,
                                reason=(
                                    f"Pivot {cell_text(pivot)} is {{{x},{y}}}; pincers "
                                    f"{cell_text(a)}={digits_from_mask(state.candidate_mask(a))} and "
                                    f"{cell_text(b)}={digits_from_mask(state.candidate_mask(b))}, "
                                    f"so digit {z} can be eliminated from common peers."
                                ),
                                eliminations=eliminations,
                                cause_cells=[pivot, a, b],
                            )
                        )

        return moves


class XYZWing(Technique):
    name = "XYZ-Wing"
    difficulty = 7

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        pivots = [cell for cell in range(81) if state.is_trivalue(cell)]
        bivalue_cells = {cell for cell in range(81) if state.is_bivalue(cell)}

        for pivot in pivots:
            pivot_digits = digits_from_mask(state.candidate_mask(pivot))
            if len(pivot_digits) != 3:
                continue

            for x, y, z in combinations(pivot_digits, 3):
                x_mask, y_mask, z_mask = bit(x), bit(y), bit(z)

                xz_peers = [
                    peer for peer in (PEERS[pivot] & bivalue_cells)
                    if state.candidate_mask(peer) == (x_mask | z_mask)
                ]
                yz_peers = [
                    peer for peer in (PEERS[pivot] & bivalue_cells)
                    if state.candidate_mask(peer) == (y_mask | z_mask)
                ]

                for a in xz_peers:
                    for b in yz_peers:
                        if a == b:
                            continue

                        common = PEERS[pivot] & PEERS[a] & PEERS[b]
                        eliminations = [
                            Elimination(cell, z)
                            for cell in common
                            if state.can_place(cell, z)
                        ]
                        if eliminations:
                            moves.append(
                                Move(
                                    technique=self.name,
                                    difficulty=self.difficulty,
                                    reason=(
                                        f"Pivot {cell_text(pivot)} is {{{x},{y},{z}}}; pincers "
                                        f"{cell_text(a)} are {{{x},{z}}} and {cell_text(b)} are "
                                        f"{{{y},{z}}}, so digit {z} can be removed from cells seeing all three."
                                    ),
                                    eliminations=eliminations,
                                    cause_cells=[pivot, a, b],
                                )
                            )

        return moves


class XYChain(Technique):
    name = "XY-Chain"
    difficulty = 7

    def __init__(self, max_length: int = 8):
        self.max_length = max_length

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        seen = set()
        bivalue_cells = [cell for cell in range(81) if state.is_bivalue(cell)]
        bivalue_set = set(bivalue_cells)

        for start in bivalue_cells:
            start_digits = digits_from_mask(state.candidate_mask(start))
            for eliminated_digit in start_digits:
                next_digit = start_digits[0] if start_digits[1] == eliminated_digit else start_digits[1]
                self._extend_chain(
                    state,
                    start,
                    start,
                    eliminated_digit,
                    next_digit,
                    [start],
                    bivalue_set,
                    seen,
                    moves,
                )

        return moves

    def _extend_chain(
        self,
        state: SudokuState,
        start: int,
        current: int,
        eliminated_digit: int,
        needed_digit: int,
        path: List[int],
        bivalue_cells: set[int],
        seen: set[tuple[int, int, tuple[int, ...], tuple[tuple[int, int], ...]]],
        moves: List[Move],
    ) -> None:
        if len(path) >= self.max_length:
            return

        next_cells = sorted((PEERS[current] & bivalue_cells) - set(path))
        for next_cell in next_cells:
            next_mask = state.candidate_mask(next_cell)
            if not (next_mask & bit(needed_digit)):
                continue

            next_digits = digits_from_mask(next_mask)
            if len(next_digits) != 2:
                continue
            next_needed = next_digits[0] if next_digits[1] == needed_digit else next_digits[1]
            next_path = path + [next_cell]

            if next_needed == eliminated_digit and len(next_path) >= 3:
                common_peers = (PEERS[start] & PEERS[next_cell]) - set(next_path)
                eliminations = [
                    Elimination(cell, eliminated_digit)
                    for cell in sorted(common_peers)
                    if state.can_place(cell, eliminated_digit)
                ]
                if not eliminations:
                    continue

                key = (
                    eliminated_digit,
                    min(start, next_cell),
                    tuple(sorted(next_path)),
                    tuple((elimination.cell, elimination.digit) for elimination in eliminations),
                )
                if key in seen:
                    continue
                seen.add(key)

                chain_text = " -> ".join(cell_text(cell) for cell in next_path)
                moves.append(
                    Move(
                        technique=self.name,
                        difficulty=self.difficulty,
                        reason=(
                            f"XY-Chain on digit {eliminated_digit}: chain {chain_text} "
                            "forces one endpoint to contain the digit, so common peers cannot."
                        ),
                        eliminations=eliminations,
                        cause_cells=next_path,
                    )
                )
                continue

            self._extend_chain(
                state,
                start,
                next_cell,
                eliminated_digit,
                next_needed,
                next_path,
                bivalue_cells,
                seen,
                moves,
            )


class WWing(Technique):
    name = "W-Wing"
    difficulty = 6

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        bivalue_by_mask = {}
        strong_links_by_digit = {
            d: [
                tuple(cells)
                for unit in ALL_UNITS
                for cells in ([cell for cell in unit if state.can_place(cell, d)],)
                if len(cells) == 2
            ]
            for d in range(1, 10)
        }

        for cell in range(81):
            if state.is_bivalue(cell):
                bivalue_by_mask.setdefault(state.candidate_mask(cell), []).append(cell)

        for pair_mask, cells in bivalue_by_mask.items():
            pair_digits = digits_from_mask(pair_mask)
            for a, b in combinations(cells, 2):
                if b in PEERS[a]:
                    continue

                for link_digit in pair_digits:
                    eliminated_digit = pair_digits[0] if pair_digits[1] == link_digit else pair_digits[1]
                    for p, q in strong_links_by_digit[link_digit]:
                        linked = (
                            (p in PEERS[a] and q in PEERS[b])
                            or (q in PEERS[a] and p in PEERS[b])
                        )
                        if not linked:
                            continue

                        eliminations = [
                            Elimination(cell, eliminated_digit)
                            for cell in (PEERS[a] & PEERS[b])
                            if cell not in (a, b) and state.can_place(cell, eliminated_digit)
                        ]
                        if eliminations:
                            moves.append(
                                Move(
                                    technique=self.name,
                                    difficulty=self.difficulty,
                                    reason=(
                                        f"W-Wing: {cell_text(a)} and {cell_text(b)} are both {pair_digits}, "
                                        f"linked by a strong {link_digit} link between {cell_text(p)} and {cell_text(q)}; "
                                        f"remove {eliminated_digit} from common peers."
                                    ),
                                    eliminations=eliminations,
                                    cause_cells=sorted({a, b, p, q}),
                                )
                            )

        return moves


class RemotePairs(Technique):
    name = "Remote Pairs"
    difficulty = 6

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        cells_by_mask = {}

        for cell in range(81):
            if state.is_bivalue(cell):
                cells_by_mask.setdefault(state.candidate_mask(cell), []).append(cell)

        for pair_mask, cells in cells_by_mask.items():
            if len(cells) < 4:
                continue

            cell_set = set(cells)
            graph = {cell: sorted(PEERS[cell] & cell_set) for cell in cells}
            color = {}

            for start in cells:
                if start in color:
                    continue

                component = []
                queue = [start]
                color[start] = 0
                valid_component = True
                while queue and valid_component:
                    current = queue.pop(0)
                    component.append(current)
                    for neighbor in graph[current]:
                        next_color = 1 - color[current]
                        if neighbor not in color:
                            color[neighbor] = next_color
                            queue.append(neighbor)
                        elif color[neighbor] != next_color:
                            valid_component = False
                            break

                if not valid_component or len(component) < 4:
                    continue

                pair_digits = digits_from_mask(pair_mask)
                for a, b in combinations(component, 2):
                    if color[a] == color[b]:
                        continue

                    eliminations = []
                    for cell in (PEERS[a] & PEERS[b]) - {a, b}:
                        for digit in pair_digits:
                            if state.can_place(cell, digit):
                                eliminations.append(Elimination(cell, digit))

                    if eliminations:
                        moves.append(
                            Move(
                                technique=self.name,
                                difficulty=self.difficulty,
                                reason=(
                                    f"Remote Pairs: alternating {pair_digits} chain connects "
                                    f"{cell_text(a)} and {cell_text(b)}; common peers cannot keep those digits."
                                ),
                                eliminations=eliminations,
                                cause_cells=component,
                            )
                        )

        return moves

