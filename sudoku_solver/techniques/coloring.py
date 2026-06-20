from __future__ import annotations

from itertools import combinations
from typing import List, Tuple

from .common import (
    ALL_UNITS,
    CELL_INDICES,
    DIGIT_VALUES,
    PEERS,
    Elimination,
    Move,
    SudokuState,
    Technique,
    UnitCandidateCache,
    cell_text,
)


def strong_links_for_digit(
    state: SudokuState,
    digit: int,
    candidate_cache: UnitCandidateCache | None = None,
) -> List[Tuple[int, int]]:
    """Return conjugate-pair strong links for one candidate digit."""
    cache = candidate_cache or UnitCandidateCache(state)
    links: set[tuple[int, int]] = set()
    for unit in ALL_UNITS:
        cells = cache.unsolved_cells_with_candidate(unit, digit)
        if len(cells) == 2:
            first_cell, second_cell = sorted(cells)
            links.add((first_cell, second_cell))
    return sorted(links)

class SimpleColoring(Technique):
    """Use two-color conjugate-link graphs to find contradictions.

    See `doc/simple-coloring.md` for the full technique description.
    """

    name = "Simple Coloring"
    difficulty = 6

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        candidate_cache = UnitCandidateCache(state)

        for digit in DIGIT_VALUES:
            graph: dict[int, set[int]] = {}
            for a, b in strong_links_for_digit(state, digit, candidate_cache):
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
                for cell in CELL_INDICES:
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


class MultiColoring(Technique):
    """Use interactions between colored components for eliminations.

    See `doc/multi-coloring.md` for the full technique description.
    """

    name = "Multi-Coloring"
    difficulty = 7

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []
        seen = set()
        candidate_cache = UnitCandidateCache(state)

        for digit in DIGIT_VALUES:
            graph: dict[int, set[int]] = {}
            for a, b in strong_links_for_digit(state, digit, candidate_cache):
                graph.setdefault(a, set()).add(b)
                graph.setdefault(b, set()).add(a)

            components = []
            global_color = {}
            for start in sorted(graph):
                if start in global_color:
                    continue

                component = []
                queue = [start]
                global_color[start] = 0
                valid = True
                while queue and valid:
                    current = queue.pop(0)
                    component.append(current)
                    for neighbor in sorted(graph[current]):
                        next_color = 1 - global_color[current]
                        if neighbor not in global_color:
                            global_color[neighbor] = next_color
                            queue.append(neighbor)
                        elif global_color[neighbor] != next_color:
                            valid = False
                            break

                if valid and len(component) >= 4:
                    components.append(component)

            for left_index, left_component in enumerate(components):
                left_set = set(left_component)
                for right_component in components[left_index + 1:]:
                    right_set = set(right_component)
                    for left_color in (0, 1):
                        left_link_cells = [cell for cell in left_component if global_color[cell] == left_color]
                        left_opposite = {cell for cell in left_component if global_color[cell] != left_color}
                        for right_color in (0, 1):
                            right_link_cells = [cell for cell in right_component if global_color[cell] == right_color]
                            right_opposite = {cell for cell in right_component if global_color[cell] != right_color}

                            weak_links = [
                                (left_cell, right_cell)
                                for left_cell in left_link_cells
                                for right_cell in right_link_cells
                                if right_cell in PEERS[left_cell]
                            ]
                            if not weak_links:
                                continue

                            eliminations = []
                            for cell in CELL_INDICES:
                                if cell in left_set or cell in right_set or not state.can_place(cell, digit):
                                    continue
                                if (PEERS[cell] & left_opposite) and (PEERS[cell] & right_opposite):
                                    eliminations.append(Elimination(cell, digit))

                            if not eliminations:
                                continue

                            key = (
                                digit,
                                tuple(sorted(left_component)),
                                tuple(sorted(right_component)),
                                left_color,
                                right_color,
                                tuple((elimination.cell, elimination.digit) for elimination in eliminations),
                            )
                            if key in seen:
                                continue
                            seen.add(key)

                            link_text = ", ".join(
                                f"{cell_text(left_cell)}-{cell_text(right_cell)}"
                                for left_cell, right_cell in weak_links[:3]
                            )
                            moves.append(
                                Move(
                                    technique=self.name,
                                    difficulty=self.difficulty,
                                    reason=(
                                        f"Multi-Coloring on digit {digit}: weak link(s) {link_text} connect "
                                        "two colored strong-link components, so candidates seeing the opposite colors can be removed."
                                    ),
                                    eliminations=eliminations,
                                    cause_cells=sorted(left_set | right_set),
                                )
                            )

        return moves

