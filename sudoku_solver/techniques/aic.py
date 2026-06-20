from __future__ import annotations

from typing import List, TypeVar

from .common import (
    ALL_UNITS,
    BOX_UNITS,
    CELL_INDICES,
    COL_OF,
    DIGIT_VALUES,
    ROW_OF,
    CellDigit,
    CellGroup,
    Elimination,
    EliminationKey,
    Move,
    SudokuState,
    Technique,
    UnitCandidateCache,
    cell_text,
    elimination_key,
    is_single,
    pair_combinations,
    shared_peer_eliminations,
    zip_pairs,
)

CandidateNode = CellDigit
GroupedNode = tuple[int, CellGroup]
LinkNode = TypeVar("LinkNode", CandidateNode, GroupedNode)
LinkSeenKey = tuple[tuple[LinkNode, ...], EliminationKey]
CandidateSeenKey = tuple[tuple[CandidateNode, ...], EliminationKey]
GroupedSeenKey = tuple[tuple[GroupedNode, ...], EliminationKey]
CELL_BIT_MASKS = [1 << cell for cell in CELL_INDICES]
UNIT_CELL_MASKS = [
    sum(CELL_BIT_MASKS[cell] for cell in unit)
    for unit in ALL_UNITS
]


def _add_link(links: dict[LinkNode, set[LinkNode]], left: LinkNode, right: LinkNode) -> None:
    """Add an undirected graph link between two candidate nodes."""
    links.setdefault(left, set[LinkNode]()).add(right)
    links.setdefault(right, set[LinkNode]()).add(left)


def _sorted_link_map(links: dict[LinkNode, set[LinkNode]]) -> dict[LinkNode, tuple[LinkNode, ...]]:
    """Return a deterministic adjacency map sorted once before chain search."""
    return {
        node: tuple(sorted(neighbors))
        for node, neighbors in links.items()
    }


def _cells_mask(cells: CellGroup) -> int:
    """Return a bit mask for a tuple of cells."""
    return sum(CELL_BIT_MASKS[cell] for cell in cells)


def _is_duplicate_elimination(
    seen: set[LinkSeenKey],
    path: list[LinkNode],
    eliminations: List[Elimination],
) -> bool:
    eliminations_key = elimination_key(eliminations)
    path_key = tuple[LinkNode, ...](path)
    reverse_path_key = tuple[LinkNode, ...](reversed(path))
    key = (path_key, eliminations_key)
    reverse_key = (reverse_path_key, eliminations_key)
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
    return shared_peer_eliminations(state, (start_cell, end_cell), digit, blocked=(start_cell, end_cell))


def _grouped_common_peer_eliminations(
    state: SudokuState,
    start_cells: CellGroup,
    end_cells: CellGroup,
    digit: int,
) -> List[Elimination]:
    grouped_cells = (*start_cells, *end_cells)
    return shared_peer_eliminations(state, grouped_cells, digit, blocked=grouped_cells)


def _next_link_type(link_type: str) -> str:
    return "weak" if link_type == "strong" else "strong"


class AIC(Technique):
    """Find Alternating Inference Chain eliminations from strong-ended chains.

    See `doc/aic.md` for the full technique description.
    """

    name = "AIC"
    difficulty = 8

    def __init__(self, max_edges: int = 7):
        self.max_edges = max_edges

    def find_moves(self, state: SudokuState) -> List[Move]:
        strong_links, weak_links = self._build_links(state)
        moves: List[Move] = []
        seen: set[CandidateSeenKey] = set[CandidateSeenKey]()

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
        candidate_cache = UnitCandidateCache(state)

        # Cell links: bivalue cells are strong; all candidate pairs in a cell are weak.
        for cell in CELL_INDICES:
            if is_single(state.candidate_mask(cell)):
                continue

            nodes = [(cell, digit) for digit in state.candidate_digits(cell)]
            for left, right in pair_combinations(nodes):
                _add_link(weak_links, left, right)
                if len(nodes) == 2:
                    _add_link(strong_links, left, right)

        # Unit links: conjugate digit pairs are strong; all same-digit unit pairs are weak.
        for unit in ALL_UNITS:
            for digit in DIGIT_VALUES:
                nodes = [
                    (cell, digit)
                    for cell in candidate_cache.unsolved_cells_with_candidate(unit, digit)
                ]
                for left, right in pair_combinations(nodes):
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
        seen: set[CandidateSeenKey],
        moves: List[Move],
    ) -> None:
        if len(edge_types) >= self.max_edges:
            return

        links = strong_links if next_link_type == "strong" else weak_links
        following_link_type = _next_link_type(next_link_type)

        for next_node in sorted(links.get(current, set[CandidateNode]())):
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
        seen: set[CandidateSeenKey],
        moves: List[Move],
    ) -> None:
        start_cell, start_digit = path[0]
        end_cell, end_digit = path[-1]
        eliminations: List[Elimination] = []

        if start_digit == end_digit and start_cell != end_cell:
            path_cells = {cell for cell, _ in path}
            eliminations = _candidate_common_peer_eliminations(state, start_cell, end_cell, start_digit)
            eliminations = [
                elimination
                for elimination in eliminations
                if elimination.cell not in path_cells
            ]
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
                source_digit_roles={
                    (cell, digit): "primary"
                    for cell, digit in path
                },
            )
        )

    def _chain_text(self, path: List[CandidateNode], edge_types: List[str]) -> str:
        parts = [self._node_text(path[0])]
        for edge_type, node in zip_pairs(edge_types, path[1:]):
            marker = "=" if edge_type == "strong" else "-"
            parts.append(f"{marker} {self._node_text(node)}")
        return " ".join(parts)

    def _node_text(self, node: CandidateNode) -> str:
        cell, digit = node
        return f"{cell_text(cell)}#{digit}"


class XChain(AIC):
    """Find single-digit AIC eliminations, also known as X-Chains.

    See `doc/x-chain.md` for the full technique description.
    """

    name = "X-Chain"
    difficulty = 7

    def _build_links(
        self,
        state: SudokuState,
    ) -> tuple[dict[CandidateNode, set[CandidateNode]], dict[CandidateNode, set[CandidateNode]]]:
        strong_links: dict[CandidateNode, set[CandidateNode]] = {}
        weak_links: dict[CandidateNode, set[CandidateNode]] = {}
        candidate_cache = UnitCandidateCache(state)

        for unit in ALL_UNITS:
            for digit in DIGIT_VALUES:
                nodes = [
                    (cell, digit)
                    for cell in candidate_cache.unsolved_cells_with_candidate(unit, digit)
                ]
                for left, right in pair_combinations(nodes):
                    _add_link(weak_links, left, right)
                if len(nodes) == 2:
                    _add_link(strong_links, nodes[0], nodes[1])

        return strong_links, weak_links

    def _append_eliminations(
        self,
        state: SudokuState,
        path: List[CandidateNode],
        edge_types: List[str],
        seen: set[CandidateSeenKey],
        moves: List[Move],
    ) -> None:
        start_cell, digit = path[0]
        end_cell, end_digit = path[-1]
        if digit != end_digit or start_cell == end_cell:
            return

        path_cells = {cell for cell, _ in path}
        eliminations = _candidate_common_peer_eliminations(state, start_cell, end_cell, digit)
        eliminations = [
            elimination
            for elimination in eliminations
            if elimination.cell not in path_cells
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
                reason=(
                    f"X-Chain on digit {digit}: strong-ended alternating chain {chain_text} "
                    "proves at least one endpoint true."
                ),
                eliminations=eliminations,
                cause_cells=sorted({cell for cell, _ in path}),
                source_digit_roles={
                    (cell, digit): "primary"
                    for cell, digit in path
                },
            )
        )


class GroupedAIC(Technique):
    """Find AIC eliminations that allow grouped candidate nodes.

    See `doc/grouped-aic.md` for the full technique description.
    """

    name = "Grouped AIC"
    difficulty = 8

    def __init__(self, max_edges: int = 7, max_moves: int = 50):
        self.max_edges = max_edges
        self.max_moves = max_moves

    def find_moves(self, state: SudokuState) -> List[Move]:
        return self._find_grouped_moves(state, include_cell_links=True)

    def _find_grouped_moves(self, state: SudokuState, *, include_cell_links: bool) -> List[Move]:
        candidate_cache = UnitCandidateCache(state)
        strong_links, weak_links, node_masks = self._build_links(
            state,
            include_cell_links=include_cell_links,
            candidate_cache=candidate_cache,
        )
        sorted_strong_links = _sorted_link_map(strong_links)
        sorted_weak_links = _sorted_link_map(weak_links)
        moves: List[Move] = []
        seen: set[GroupedSeenKey] = set[GroupedSeenKey]()

        for start in sorted(sorted_strong_links):
            if len(moves) >= self.max_moves:
                break
            self._extend_chain(
                state,
                start,
                "strong",
                [start],
                [],
                sorted_strong_links,
                sorted_weak_links,
                node_masks[start],
                node_masks,
                seen,
                moves,
            )

        return moves

    def _build_links(
        self,
        state: SudokuState,
        *,
        include_cell_links: bool,
        candidate_cache: UnitCandidateCache,
    ) -> tuple[dict[GroupedNode, set[GroupedNode]], dict[GroupedNode, set[GroupedNode]], dict[GroupedNode, int]]:
        nodes_by_digit, node_masks = self._grouped_nodes_by_digit(state, candidate_cache)
        strong_links: dict[GroupedNode, set[GroupedNode]] = {}
        weak_links: dict[GroupedNode, set[GroupedNode]] = {}

        for digit, nodes in nodes_by_digit.items():
            for unit_index, unit in enumerate[list[int]](ALL_UNITS):
                unit_mask = UNIT_CELL_MASKS[unit_index]
                unit_candidate_cells = candidate_cache.unsolved_cells_with_candidate(unit, digit)
                unit_candidate_mask = sum(CELL_BIT_MASKS[cell] for cell in unit_candidate_cells)
                if len(unit_candidate_cells) < 2:
                    continue

                unit_nodes = [
                    node for node in nodes
                    if not (node_masks[node] & ~unit_mask) and node_masks[node] & unit_candidate_mask
                ]
                for left, right in pair_combinations(unit_nodes):
                    left_mask = node_masks[left]
                    right_mask = node_masks[right]
                    if left_mask & right_mask:
                        continue
                    _add_link(weak_links, left, right)
                    if left_mask | right_mask == unit_candidate_mask:
                        _add_link(strong_links, left, right)

        if include_cell_links:
            for cell in CELL_INDICES:
                if is_single(state.candidate_mask(cell)):
                    continue
                cell_nodes = [
                    (digit, (cell,))
                    for digit in state.candidate_digits(cell)
                ]
                for left, right in pair_combinations(cell_nodes):
                    _add_link(weak_links, left, right)
                    if len(cell_nodes) == 2:
                        _add_link(strong_links, left, right)

        return strong_links, weak_links, node_masks

    def _grouped_nodes_by_digit(
        self,
        state: SudokuState,
        candidate_cache: UnitCandidateCache,
    ) -> tuple[dict[int, set[GroupedNode]], dict[GroupedNode, int]]:
        nodes_by_digit: dict[int, set[GroupedNode]] = {
            digit: set[GroupedNode]() for digit in DIGIT_VALUES
        }
        node_masks: dict[GroupedNode, int] = {}

        for digit in DIGIT_VALUES:
            for cell in CELL_INDICES:
                if state.can_place(cell, digit):
                    node: GroupedNode = (digit, (cell,))
                    nodes_by_digit[digit].add(node)
                    node_masks[node] = CELL_BIT_MASKS[cell]

            for box in BOX_UNITS:
                box_candidates = candidate_cache.unsolved_cells_with_candidate(box, digit)
                for row in sorted({ROW_OF[cell] for cell in box}):
                    cells = CellGroup(sorted(cell for cell in box_candidates if ROW_OF[cell] == row))
                    if len(cells) > 1:
                        node = (digit, cells)
                        nodes_by_digit[digit].add(node)
                        node_masks[node] = _cells_mask(cells)
                for col in sorted({COL_OF[cell] for cell in box}):
                    cells = CellGroup(sorted(cell for cell in box_candidates if COL_OF[cell] == col))
                    if len(cells) > 1:
                        node = (digit, cells)
                        nodes_by_digit[digit].add(node)
                        node_masks[node] = _cells_mask(cells)

        return nodes_by_digit, node_masks

    def _extend_chain(
        self,
        state: SudokuState,
        current: GroupedNode,
        next_link_type: str,
        path: List[GroupedNode],
        edge_types: List[str],
        strong_links: dict[GroupedNode, tuple[GroupedNode, ...]],
        weak_links: dict[GroupedNode, tuple[GroupedNode, ...]],
        path_cell_mask: int,
        node_masks: dict[GroupedNode, int],
        seen: set[GroupedSeenKey],
        moves: List[Move],
    ) -> None:
        if len(edge_types) >= self.max_edges or len(moves) >= self.max_moves:
            return

        links = strong_links if next_link_type == "strong" else weak_links
        following_link_type = _next_link_type(next_link_type)

        for next_node in links.get(current, ()):
            if len(moves) >= self.max_moves:
                return
            if next_node in path:
                continue

            next_path = path + [next_node]
            next_edge_types = edge_types + [next_link_type]
            next_path_cell_mask = path_cell_mask | node_masks[next_node]

            if next_link_type == "strong" and len(next_edge_types) >= 3:
                self._append_eliminations(state, next_path, next_edge_types, next_path_cell_mask, seen, moves)

            self._extend_chain(
                state,
                next_node,
                following_link_type,
                next_path,
                next_edge_types,
                strong_links,
                weak_links,
                next_path_cell_mask,
                node_masks,
                seen,
                moves,
            )

    def _append_eliminations(
        self,
        state: SudokuState,
        path: List[GroupedNode],
        edge_types: List[str],
        path_cell_mask: int,
        seen: set[GroupedSeenKey],
        moves: List[Move],
    ) -> None:
        start_digit, start_cells = path[0]
        end_digit, end_cells = path[-1]
        eliminations: List[Elimination] = []

        if start_digit == end_digit and set[int](start_cells) != set[int](end_cells):
            eliminations = _grouped_common_peer_eliminations(state, start_cells, end_cells, start_digit)
            eliminations = [
                elimination
                for elimination in eliminations
                if not (path_cell_mask & CELL_BIT_MASKS[elimination.cell])
            ]
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
                source_digit_roles={
                    (cell, digit): "primary"
                    for digit, cells in path
                    for cell in cells
                },
            )
        )

    def _chain_text(self, path: List[GroupedNode], edge_types: List[str]) -> str:
        parts = [self._node_text(path[0])]
        for edge_type, node in zip_pairs(edge_types, path[1:]):
            marker = "=" if edge_type == "strong" else "-"
            parts.append(f"{marker} {self._node_text(node)}")
        return " ".join(parts)

    def _node_text(self, node: GroupedNode) -> str:
        digit, cells = node
        if len(cells) == 1:
            return f"{cell_text(cells[0])}#{digit}"
        return f"{{{','.join(cell_text(cell) for cell in cells)}}}#{digit}"


class GroupedXChain(GroupedAIC):
    """Find grouped single-digit chain eliminations.

    See `doc/grouped-x-chain.md` for the full technique description.
    """

    name = "Grouped X-Chain"
    difficulty = 7

    def find_moves(self, state: SudokuState) -> List[Move]:
        return self._find_grouped_moves(state, include_cell_links=False)
