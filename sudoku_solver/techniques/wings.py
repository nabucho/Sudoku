from __future__ import annotations

from typing import List

from .common import (
    DIGIT_VALUES,
    PEERS,
    Move,
    SudokuState,
    Technique,
    UnitCandidateCache,
    bit,
    bit_count,
    bivalue_candidate_cells,
    bivalue_cells_by_mask,
    cell_text,
    digits_from_mask,
    elimination_key,
    other_bivalue_digit,
    pair_combinations,
    shared_peer_eliminations,
    single_digit,
    strong_links_for_digit,
    trivalue_candidate_cells,
)


class XYWing(Technique):
    """Find XY-Wing eliminations from a bivalue pivot and two pincers.

    See `doc/xy-wing.md` for the full technique description.
    """

    name = "XY-Wing"
    difficulty = 6

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        bivalue = bivalue_candidate_cells(state)

        for pivot in bivalue:
            pivot_mask = state.candidate_mask(pivot)
            x, y = digits_from_mask(pivot_mask)

            x_mask = bit(x)
            y_mask = bit(y)

            xz_peers: list[int] = []
            yz_peers: list[int] = []

            for peer in PEERS[pivot]:
                if not state.is_bivalue(peer):
                    continue
                peer_mask = state.candidate_mask(peer)

                if (peer_mask & x_mask) and not (peer_mask & y_mask):
                    if bit_count(peer_mask) == 2:
                        xz_peers.append(peer)

                if (peer_mask & y_mask) and not (peer_mask & x_mask):
                    if bit_count(peer_mask) == 2:
                        yz_peers.append(peer)

            for xz_pincer in xz_peers:
                z_mask = state.candidate_mask(xz_pincer) & ~x_mask
                if bit_count(z_mask) != 1:
                    continue
                z = single_digit(z_mask)

                for yz_pincer in yz_peers:
                    if xz_pincer == yz_pincer:
                        continue
                    if state.candidate_mask(yz_pincer) != (y_mask | z_mask):
                        continue

                    eliminations = shared_peer_eliminations(state, (xz_pincer, yz_pincer), z, blocked={pivot})
                    if eliminations:
                        moves.append(
                            Move(
                                technique=self.name,
                                difficulty=self.difficulty,
                                reason=(
                                    f"Pivot {cell_text(pivot)} is {{{x},{y}}}; pincers "
                                    f"{cell_text(xz_pincer)}={digits_from_mask(state.candidate_mask(xz_pincer))} and "
                                    f"{cell_text(yz_pincer)}={digits_from_mask(state.candidate_mask(yz_pincer))}, "
                                    f"so digit {z} can be eliminated from common peers."
                                ),
                                eliminations=eliminations,
                                cause_cells=[pivot, xz_pincer, yz_pincer],
                            )
                        )

        return moves


class XYZWing(Technique):
    """Find XYZ-Wing eliminations from a trivalue pivot and two pincers.

    See `doc/xyz-wing.md` for the full technique description.
    """

    name = "XYZ-Wing"
    difficulty = 7

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        pivots = trivalue_candidate_cells(state)
        bivalue = set[int](bivalue_candidate_cells(state))

        for pivot in pivots:
            pivot_digits = digits_from_mask(state.candidate_mask(pivot))
            if len(pivot_digits) != 3:
                continue

            x, y, z = pivot_digits
            x_mask, y_mask, z_mask = bit(x), bit(y), bit(z)

            xz_peers = [
                peer for peer in (PEERS[pivot] & bivalue)
                if state.candidate_mask(peer) == (x_mask | z_mask)
            ]
            yz_peers = [
                peer for peer in (PEERS[pivot] & bivalue)
                if state.candidate_mask(peer) == (y_mask | z_mask)
            ]

            for xz_pincer in xz_peers:
                for yz_pincer in yz_peers:
                    if xz_pincer == yz_pincer:
                        continue

                    eliminations = shared_peer_eliminations(state, (pivot, xz_pincer, yz_pincer), z)
                    if eliminations:
                        moves.append(
                            Move(
                                technique=self.name,
                                difficulty=self.difficulty,
                                reason=(
                                    f"Pivot {cell_text(pivot)} is {{{x},{y},{z}}}; pincers "
                                    f"{cell_text(xz_pincer)} are {{{x},{z}}} and {cell_text(yz_pincer)} are "
                                    f"{{{y},{z}}}, so digit {z} can be removed from cells seeing all three."
                                ),
                                eliminations=eliminations,
                                cause_cells=[pivot, xz_pincer, yz_pincer],
                            )
                            )

        return moves


class XYChain(Technique):
    """Find eliminations from alternating chains through bivalue cells.

    See `doc/xy-chain.md` for the full technique description.
    """

    name = "XY-Chain"
    difficulty = 7

    def __init__(self, max_length: int = 8):
        self.max_length = max_length

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        seen: set[tuple[int, int, tuple[int, ...], tuple[tuple[int, int], ...]]] = set[
            tuple[int, int, tuple[int, ...], tuple[tuple[int, int], ...]]
        ]()
        bivalue = bivalue_candidate_cells(state)
        bivalue_set = set[int](bivalue)

        for start in bivalue:
            start_digits = digits_from_mask(state.candidate_mask(start))
            for eliminated_digit in start_digits:
                next_digit = other_bivalue_digit(start_digits, eliminated_digit)
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
        bivalue_cell_set: set[int],
        seen: set[tuple[int, int, tuple[int, ...], tuple[tuple[int, int], ...]]],
        moves: List[Move],
    ) -> None:
        if len(path) >= self.max_length:
            return

        next_cells = sorted((PEERS[current] & bivalue_cell_set) - set[int](path))
        for next_cell in next_cells:
            next_mask = state.candidate_mask(next_cell)
            if not (next_mask & bit(needed_digit)):
                continue

            next_digits = digits_from_mask(next_mask)
            if len(next_digits) != 2:
                continue
            next_needed = other_bivalue_digit(next_digits, needed_digit)
            next_path = path + [next_cell]

            if next_needed == eliminated_digit and len(next_path) >= 3:
                eliminations = shared_peer_eliminations(state, (start, next_cell), eliminated_digit, blocked=next_path)
                if not eliminations:
                    continue

                key = (
                    eliminated_digit,
                    min(start, next_cell),
                    tuple[int, ...](sorted(next_path)),
                    elimination_key(eliminations),
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
                bivalue_cell_set,
                seen,
                moves,
            )


class WWing(Technique):
    """Find W-Wing eliminations from matching bivalue cells and a strong link.

    See `doc/w-wing.md` for the full technique description.
    """

    name = "W-Wing"
    difficulty = 6

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        candidate_cache = UnitCandidateCache(state)
        strong_links_by_digit = {
            digit: strong_links_for_digit(state, digit, candidate_cache)
            for digit in DIGIT_VALUES
        }

        for pair_mask, cells in bivalue_cells_by_mask(state).items():
            pair_digits = digits_from_mask(pair_mask)
            for first_wing_cell, second_wing_cell in pair_combinations(cells):
                if second_wing_cell in PEERS[first_wing_cell]:
                    continue

                for link_digit in pair_digits:
                    eliminated_digit = other_bivalue_digit(pair_digits, link_digit)
                    for first_link_cell, second_link_cell in strong_links_by_digit[link_digit]:
                        linked = (
                            (first_link_cell in PEERS[first_wing_cell] and second_link_cell in PEERS[second_wing_cell])
                            or (second_link_cell in PEERS[first_wing_cell] and first_link_cell in PEERS[second_wing_cell])
                        )
                        if not linked:
                            continue

                        eliminations = shared_peer_eliminations(
                            state,
                            (first_wing_cell, second_wing_cell),
                            eliminated_digit,
                            blocked=(first_wing_cell, second_wing_cell),
                        )
                        if eliminations:
                            moves.append(
                                Move(
                                    technique=self.name,
                                    difficulty=self.difficulty,
                                    reason=(
                                        f"W-Wing: {cell_text(first_wing_cell)} and {cell_text(second_wing_cell)} are both {pair_digits}, "
                                        f"linked by a strong {link_digit} link between {cell_text(first_link_cell)} and {cell_text(second_link_cell)}; "
                                        f"remove {eliminated_digit} from common peers."
                                    ),
                                    eliminations=eliminations,
                                    cause_cells=sorted({first_wing_cell, second_wing_cell, first_link_cell, second_link_cell}),
                                )
                            )

        return moves


class RemotePairs(Technique):
    """Find Remote Pairs eliminations from alternating bivalue chains.

    See `doc/remote-pairs.md` for the full technique description.
    """

    name = "Remote Pairs"
    difficulty = 6

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        for pair_mask, cells in bivalue_cells_by_mask(state).items():
            if len(cells) < 4:
                continue

            cell_set = set[int](cells)
            graph = {cell: sorted(PEERS[cell] & cell_set) for cell in cells}
            color: dict[int, int] = {}

            for start in cells:
                if start in color:
                    continue

                component: list[int] = []
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
                for first_endpoint, second_endpoint in pair_combinations(component):
                    if color[first_endpoint] == color[second_endpoint]:
                        continue

                    eliminations = [
                        elimination
                        for digit in pair_digits
                        for elimination in shared_peer_eliminations(
                            state,
                            (first_endpoint, second_endpoint),
                            digit,
                            blocked=(first_endpoint, second_endpoint),
                        )
                    ]

                    if eliminations:
                        moves.append(
                            Move(
                                technique=self.name,
                                difficulty=self.difficulty,
                                reason=(
                                    f"Remote Pairs: alternating {pair_digits} chain connects "
                                    f"{cell_text(first_endpoint)} and {cell_text(second_endpoint)}; common peers cannot keep those digits."
                                ),
                                eliminations=eliminations,
                                cause_cells=component,
                            )
                        )

        return moves

