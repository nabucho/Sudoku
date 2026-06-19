from __future__ import annotations

from itertools import combinations
from typing import List, Tuple

from .common import *


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
                        pr, pc = i_to_rc(pivot)
                        ar, ac = i_to_rc(a)
                        br, bc = i_to_rc(b)
                        moves.append(
                            Move(
                                technique=self.name,
                                difficulty=self.difficulty,
                                reason=(
                                    f"Pivot r{pr+1}c{pc+1} is {{{x},{y}}}; pincers "
                                    f"r{ar+1}c{ac+1}={digits_from_mask(state.candidate_mask(a))} and "
                                    f"r{br+1}c{bc+1}={digits_from_mask(state.candidate_mask(b))}, "
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
                            pr, pc = i_to_rc(pivot)
                            ar, ac = i_to_rc(a)
                            br, bc = i_to_rc(b)
                            moves.append(
                                Move(
                                    technique=self.name,
                                    difficulty=self.difficulty,
                                    reason=(
                                        f"Pivot r{pr+1}c{pc+1} is {{{x},{y},{z}}}; pincers "
                                        f"r{ar+1}c{ac+1} are {{{x},{z}}} and r{br+1}c{bc+1} are "
                                        f"{{{y},{z}}}, so digit {z} can be removed from cells seeing all three."
                                    ),
                                    eliminations=eliminations,
                                    cause_cells=[pivot, a, b],
                                )
                            )

        return moves

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

