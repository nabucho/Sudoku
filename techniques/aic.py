from __future__ import annotations

from itertools import combinations
from typing import List

from .common import (
    ALL_UNITS,
    BOX_UNITS,
    CELLS,
    COL_OF,
    DIGITS,
    Elimination,
    Move,
    ROW_OF,
    SudokuState,
    Technique,
    candidate_cells,
    cell_text,
    common_peer_eliminations,
    is_single,
)

CandidateNode = tuple[int, int]
GroupedNode = tuple[int, tuple[int, ...]]


def _add_link(links: dict, left, right) -> None:
    links.setdefault(left, set()).add(right)
    links.setdefault(right, set()).add(left)


def _is_duplicate_elimination(seen: set, path: list, eliminations: List[Elimination]) -> bool:
    elimination_key = tuple((elimination.cell, elimination.digit) for elimination in eliminations)
    path_key = tuple(path)
    reverse_path_key = tuple(reversed(path))
    key = (path_key, elimination_key)
    reverse_key = (reverse_path_key, elimination_key)
    if key in seen or reverse_key in seen:
        return True
    seen.add(key)
    return False


def _candidate_common_peer_eliminations(
    state: SudokuState,
    start_cell: int,
    end_cell: int,
    digit: int,
) -> List[Elimination]:
    return common_peer_eliminations(state, (start_cell, end_cell), digit, blocked=(start_cell, end_cell))


def _grouped_common_peer_eliminations(
    state: SudokuState,
    start_cells: tuple[int, ...],
    end_cells: tuple[int, ...],
    digit: int,
) -> List[Elimination]:
    grouped_cells = (*start_cells, *end_cells)
    return common_peer_eliminations(state, grouped_cells, digit, blocked=grouped_cells)


def _next_link_type(link_type: str) -> str:
    return "weak" if link_type == "strong" else "strong"


class AIC(Technique):
    name = "AIC"
    difficulty = 8

    def __init__(self, max_edges: int = 7):
        self.max_edges = max_edges

    def find_moves(self, state: SudokuState) -> List[Move]:
        strong_links, weak_links = self._build_links(state)
        moves: List[Move] = []
        seen = set()

        for start in sorted(strong_links):
            self._extend_chain(
                state,
                start,
                "strong",
                [start],
                [],
                strong_links,
                weak_links,
                seen,
                moves,
            )

        return moves

    def _build_links(
        self,
        state: SudokuState,
    ) -> tuple[dict[CandidateNode, set[CandidateNode]], dict[CandidateNode, set[CandidateNode]]]:
        strong_links: dict[CandidateNode, set[CandidateNode]] = {}
        weak_links: dict[CandidateNode, set[CandidateNode]] = {}

        # Cell links: bivalue cells are strong; all candidate pairs in a cell are weak.
        for cell in CELLS:
            if is_single(state.candidate_mask(cell)):
                continue

            nodes = [(cell, digit) for digit in state.candidate_digits(cell)]
            for left, right in combinations(nodes, 2):
                _add_link(weak_links, left, right)
                if len(nodes) == 2:
                    _add_link(strong_links, left, right)

        # Unit links: conjugate digit pairs are strong; all same-digit unit pairs are weak.
        for unit in ALL_UNITS:
            for digit in DIGITS:
                nodes = [(cell, digit) for cell in candidate_cells(state, unit, digit)]
                for left, right in combinations(nodes, 2):
                    _add_link(weak_links, left, right)
                if len(nodes) == 2:
                    _add_link(strong_links, nodes[0], nodes[1])

        return strong_links, weak_links

    def _extend_chain(
        self,
        state: SudokuState,
        current: CandidateNode,
        next_link_type: str,
        path: List[CandidateNode],
        edge_types: List[str],
        strong_links: dict[CandidateNode, set[CandidateNode]],
        weak_links: dict[CandidateNode, set[CandidateNode]],
        seen: set[tuple[tuple[CandidateNode, ...], tuple[tuple[int, int], ...]]],
        moves: List[Move],
    ) -> None:
        if len(edge_types) >= self.max_edges:
            return

        links = strong_links if next_link_type == "strong" else weak_links
        following_link_type = _next_link_type(next_link_type)

        for next_node in sorted(links.get(current, set())):
            if next_node in path:
                continue

            next_path = path + [next_node]
            next_edge_types = edge_types + [next_link_type]

            if next_link_type == "strong" and len(next_edge_types) >= 3:
                self._append_eliminations(state, next_path, next_edge_types, seen, moves)

            self._extend_chain(
                state,
                next_node,
                following_link_type,
                next_path,
                next_edge_types,
                strong_links,
                weak_links,
                seen,
                moves,
            )

    def _append_eliminations(
        self,
        state: SudokuState,
        path: List[CandidateNode],
        edge_types: List[str],
        seen: set[tuple[tuple[CandidateNode, ...], tuple[tuple[int, int], ...]]],
        moves: List[Move],
    ) -> None:
        start_cell, start_digit = path[0]
        end_cell, end_digit = path[-1]
        eliminations: List[Elimination] = []

        if start_digit == end_digit and start_cell != end_cell:
            eliminations = _candidate_common_peer_eliminations(state, start_cell, end_cell, start_digit)
        elif start_cell == end_cell and start_digit != end_digit:
            endpoint_digits = {start_digit, end_digit}
            eliminations = [
                Elimination(start_cell, digit)
                for digit in state.candidate_digits(start_cell)
                if digit not in endpoint_digits
            ]

        if not eliminations:
            return

        if _is_duplicate_elimination(seen, path, eliminations):
            return

        chain_text = self._chain_text(path, edge_types)
        moves.append(
            Move(
                technique=self.name,
                difficulty=self.difficulty,
                reason=f"AIC: strong-ended alternating chain {chain_text} proves at least one endpoint true.",
                eliminations=eliminations,
                cause_cells=sorted({cell for cell, _ in path}),
            )
        )

    def _chain_text(self, path: List[CandidateNode], edge_types: List[str]) -> str:
        parts = [self._node_text(path[0])]
        for edge_type, node in zip(edge_types, path[1:]):
            marker = "=" if edge_type == "strong" else "-"
            parts.append(f"{marker} {self._node_text(node)}")
        return " ".join(parts)

    def _node_text(self, node: CandidateNode) -> str:
        cell, digit = node
        return f"{cell_text(cell)}#{digit}"


class XChain(AIC):
    name = "X-Chain"
    difficulty = 7

    def _build_links(
        self,
        state: SudokuState,
    ) -> tuple[dict[CandidateNode, set[CandidateNode]], dict[CandidateNode, set[CandidateNode]]]:
        strong_links: dict[CandidateNode, set[CandidateNode]] = {}
        weak_links: dict[CandidateNode, set[CandidateNode]] = {}

        for unit in ALL_UNITS:
            for digit in DIGITS:
                nodes = [(cell, digit) for cell in candidate_cells(state, unit, digit)]
                for left, right in combinations(nodes, 2):
                    _add_link(weak_links, left, right)
                if len(nodes) == 2:
                    _add_link(strong_links, nodes[0], nodes[1])

        return strong_links, weak_links

    def _append_eliminations(
        self,
        state: SudokuState,
        path: List[CandidateNode],
        edge_types: List[str],
        seen: set[tuple[tuple[CandidateNode, ...], tuple[tuple[int, int], ...]]],
        moves: List[Move],
    ) -> None:
        start_cell, digit = path[0]
        end_cell, end_digit = path[-1]
        if digit != end_digit or start_cell == end_cell:
            return

        eliminations = _candidate_common_peer_eliminations(state, start_cell, end_cell, digit)
        if not eliminations:
            return

        if _is_duplicate_elimination(seen, path, eliminations):
            return

        chain_text = self._chain_text(path, edge_types)
        moves.append(
            Move(
                technique=self.name,
                difficulty=self.difficulty,
                reason=(
                    f"X-Chain on digit {digit}: strong-ended alternating chain {chain_text} "
                    "proves at least one endpoint true."
                ),
                eliminations=eliminations,
                cause_cells=sorted({cell for cell, _ in path}),
            )
        )


class GroupedAIC(Technique):
    name = "Grouped AIC"
    difficulty = 8

    def __init__(self, max_edges: int = 7, max_moves: int = 50):
        self.max_edges = max_edges
        self.max_moves = max_moves

    def find_moves(self, state: SudokuState) -> List[Move]:
        return self._find_grouped_moves(state, include_cell_links=True)

    def _find_grouped_moves(self, state: SudokuState, *, include_cell_links: bool) -> List[Move]:
        strong_links, weak_links = self._build_links(state, include_cell_links=include_cell_links)
        moves: List[Move] = []
        seen = set()

        for start in sorted(strong_links):
            if len(moves) >= self.max_moves:
                break
            self._extend_chain(
                state,
                start,
                "strong",
                [start],
                [],
                strong_links,
                weak_links,
                seen,
                moves,
            )

        return moves

    def _build_links(
        self,
        state: SudokuState,
        *,
        include_cell_links: bool,
    ) -> tuple[dict[GroupedNode, set[GroupedNode]], dict[GroupedNode, set[GroupedNode]]]:
        nodes_by_digit = self._grouped_nodes_by_digit(state)
        strong_links: dict[GroupedNode, set[GroupedNode]] = {}
        weak_links: dict[GroupedNode, set[GroupedNode]] = {}

        for digit, nodes in nodes_by_digit.items():
            for unit in ALL_UNITS:
                unit_cells = frozenset(unit)
                unit_candidates = frozenset(cell for cell in unit if state.can_place(cell, digit))
                if len(unit_candidates) < 2:
                    continue

                unit_nodes = [
                    node for node in nodes
                    if set(node[1]).issubset(unit_cells) and set(node[1]) & unit_candidates
                ]
                for left, right in combinations(unit_nodes, 2):
                    left_cells = set(left[1])
                    right_cells = set(right[1])
                    if left_cells & right_cells:
                        continue
                    _add_link(weak_links, left, right)
                    if frozenset(left_cells | right_cells) == unit_candidates:
                        _add_link(strong_links, left, right)

        if include_cell_links:
            for cell in CELLS:
                if is_single(state.candidate_mask(cell)):
                    continue
                cell_nodes = [
                    (digit, (cell,))
                    for digit in state.candidate_digits(cell)
                ]
                for left, right in combinations(cell_nodes, 2):
                    _add_link(weak_links, left, right)
                    if len(cell_nodes) == 2:
                        _add_link(strong_links, left, right)

        return strong_links, weak_links

    def _grouped_nodes_by_digit(self, state: SudokuState) -> dict[int, set[GroupedNode]]:
        nodes_by_digit: dict[int, set[GroupedNode]] = {digit: set() for digit in DIGITS}

        for digit in DIGITS:
            for cell in CELLS:
                if state.can_place(cell, digit):
                    nodes_by_digit[digit].add((digit, (cell,)))

            for box in BOX_UNITS:
                for row in sorted({ROW_OF[cell] for cell in box}):
                    cells = tuple(sorted(cell for cell in box if ROW_OF[cell] == row and state.can_place(cell, digit)))
                    if len(cells) > 1:
                        nodes_by_digit[digit].add((digit, cells))
                for col in sorted({COL_OF[cell] for cell in box}):
                    cells = tuple(sorted(cell for cell in box if COL_OF[cell] == col and state.can_place(cell, digit)))
                    if len(cells) > 1:
                        nodes_by_digit[digit].add((digit, cells))

        return nodes_by_digit

    def _extend_chain(
        self,
        state: SudokuState,
        current: GroupedNode,
        next_link_type: str,
        path: List[GroupedNode],
        edge_types: List[str],
        strong_links: dict[GroupedNode, set[GroupedNode]],
        weak_links: dict[GroupedNode, set[GroupedNode]],
        seen: set[tuple[tuple[GroupedNode, ...], tuple[tuple[int, int], ...]]],
        moves: List[Move],
    ) -> None:
        if len(edge_types) >= self.max_edges or len(moves) >= self.max_moves:
            return

        links = strong_links if next_link_type == "strong" else weak_links
        following_link_type = _next_link_type(next_link_type)

        for next_node in sorted(links.get(current, set())):
            if len(moves) >= self.max_moves:
                return
            if next_node in path:
                continue

            next_path = path + [next_node]
            next_edge_types = edge_types + [next_link_type]
            if next_link_type == "strong" and len(next_edge_types) >= 3:
                self._append_eliminations(state, next_path, next_edge_types, seen, moves)

            self._extend_chain(
                state,
                next_node,
                following_link_type,
                next_path,
                next_edge_types,
                strong_links,
                weak_links,
                seen,
                moves,
            )

    def _append_eliminations(
        self,
        state: SudokuState,
        path: List[GroupedNode],
        edge_types: List[str],
        seen: set[tuple[tuple[GroupedNode, ...], tuple[tuple[int, int], ...]]],
        moves: List[Move],
    ) -> None:
        start_digit, start_cells = path[0]
        end_digit, end_cells = path[-1]
        eliminations: List[Elimination] = []

        if start_digit == end_digit and set(start_cells) != set(end_cells):
            eliminations = _grouped_common_peer_eliminations(state, start_cells, end_cells, start_digit)
        elif len(start_cells) == 1 and start_cells == end_cells and start_digit != end_digit:
            endpoint_digits = {start_digit, end_digit}
            cell = start_cells[0]
            eliminations = [
                Elimination(cell, digit)
                for digit in state.candidate_digits(cell)
                if digit not in endpoint_digits
            ]

        if not eliminations:
            return

        if _is_duplicate_elimination(seen, path, eliminations):
            return

        chain_text = self._chain_text(path, edge_types)
        moves.append(
            Move(
                technique=self.name,
                difficulty=self.difficulty,
                reason=f"{self.name}: grouped strong-ended alternating chain {chain_text} proves at least one endpoint true.",
                eliminations=eliminations,
                cause_cells=sorted({cell for _, cells in path for cell in cells}),
            )
        )

    def _chain_text(self, path: List[GroupedNode], edge_types: List[str]) -> str:
        parts = [self._node_text(path[0])]
        for edge_type, node in zip(edge_types, path[1:]):
            marker = "=" if edge_type == "strong" else "-"
            parts.append(f"{marker} {self._node_text(node)}")
        return " ".join(parts)

    def _node_text(self, node: GroupedNode) -> str:
        digit, cells = node
        if len(cells) == 1:
            return f"{cell_text(cells[0])}#{digit}"
        return f"{{{','.join(cell_text(cell) for cell in cells)}}}#{digit}"


class GroupedXChain(GroupedAIC):
    name = "Grouped X-Chain"
    difficulty = 7

    def find_moves(self, state: SudokuState) -> List[Move]:
        return self._find_grouped_moves(state, include_cell_links=False)
