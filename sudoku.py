from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from itertools import combinations
from typing import Iterable, List, Optional, Sequence, Tuple


# ============================================================
# Bitmask helpers
# ============================================================

ALL_DIGITS_MASK = 0x1FF  # bits 0..8 => digits 1..9


def bit(d: int) -> int:
    return 1 << (d - 1)


def bits(mask: int) -> Iterable[int]:
    d = 1
    while mask:
        if mask & 1:
            yield d
        mask >>= 1
        d += 1


def bit_count(mask: int) -> int:
    count = 0
    while mask:
        count += mask & 1
        mask >>= 1
    return count


def is_single(mask: int) -> bool:
    return mask != 0 and (mask & (mask - 1)) == 0


def single_digit(mask: int) -> int:
    """Valid only if is_single(mask) is True."""
    return mask.bit_length()


def digits_from_mask(mask: int) -> List[int]:
    return list(bits(mask))


# ============================================================
# Grid topology
# ============================================================

ROWS = range(9)
COLS = range(9)


def rc_to_i(r: int, c: int) -> int:
    return r * 9 + c


def i_to_rc(i: int) -> Tuple[int, int]:
    return divmod(i, 9)


def cell_text(cell: int) -> str:
    r, c = i_to_rc(cell)
    return f"r{r+1}c{c+1}"


ROW_UNITS = [[rc_to_i(r, c) for c in COLS] for r in ROWS]
COL_UNITS = [[rc_to_i(r, c) for r in ROWS] for c in COLS]
BOX_UNITS = [
    [
        rc_to_i(r, c)
        for r in range(br * 3, br * 3 + 3)
        for c in range(bc * 3, bc * 3 + 3)
    ]
    for br in range(3)
    for bc in range(3)
]
ALL_UNITS = ROW_UNITS + COL_UNITS + BOX_UNITS


def unit_text(unit_index: int) -> str:
    if unit_index < 9:
        return f"row {unit_index + 1}"
    if unit_index < 18:
        return f"column {unit_index - 8}"
    return f"box {unit_index - 17}"

CELL_UNITS: List[List[List[int]]] = [[] for _ in range(81)]
for unit in ALL_UNITS:
    for cell in unit:
        CELL_UNITS[cell].append(unit)

PEERS: List[set[int]] = []
for i in range(81):
    s = set()
    for unit in CELL_UNITS[i]:
        s.update(unit)
    s.discard(i)
    PEERS.append(s)

ROW_OF = [i // 9 for i in range(81)]
COL_OF = [i % 9 for i in range(81)]
BOX_OF = [((i // 9) // 3) * 3 + ((i % 9) // 3) for i in range(81)]


# ============================================================
# Move model
# ============================================================

@dataclass(frozen=True)
class Placement:
    cell: int
    digit: int


@dataclass(frozen=True)
class Elimination:
    cell: int
    digit: int


@dataclass
class Move:
    technique: str
    reason: str
    placements: List[Placement] = field(default_factory=list)
    eliminations: List[Elimination] = field(default_factory=list)
    difficulty: int = 0
    after_candidates: Optional[List[int]] = field(default=None, repr=False)
    changed_cells: List[int] = field(default_factory=list, repr=False)
    cause_cells: List[int] = field(default_factory=list, repr=False)

    def summary(self) -> str:
        if self.reason.startswith(f"{self.technique}:"):
            return self.reason
        return f"{self.technique}: {self.reason}"


# ============================================================
# Sudoku state
# ============================================================

class SudokuState:
    """
    Stores candidates as bitmasks (81 cells).
    Mutation methods:
      - place_digit(cell, digit)
      - eliminate_digit(cell, digit)

    place_digit / eliminate_digit handle peer propagation automatically.
    """

    def __init__(
        self,
        candidates: Optional[List[int]] = None,
        fixed_cells: Optional[Iterable[int]] = None,
        given_cells: Optional[Iterable[int]] = None,
    ):
        self.candidates = candidates[:] if candidates else [ALL_DIGITS_MASK] * 81
        self.fixed_cells = set(fixed_cells or [])
        self.given_cells = set(given_cells or [])

    @classmethod
    def from_board(cls, board: Sequence[Sequence[int]] | str) -> "SudokuState":
        state = cls()
        givens: List[Tuple[int, int]] = []

        if isinstance(board, str):
            chars = [ch for ch in board if ch in "1234567890."]
            if len(chars) != 81:
                raise ValueError("String puzzle must contain exactly 81 digits / dots / zeros.")
            for i, ch in enumerate(chars):
                if ch in "123456789":
                    givens.append((i, int(ch)))
        else:
            if len(board) != 9 or any(len(row) != 9 for row in board):
                raise ValueError("Board must be 9x9.")
            for r in range(9):
                for c in range(9):
                    v = board[r][c]
                    if v:
                        if not 1 <= v <= 9:
                            raise ValueError("Board values must be digits 1..9, 0, or falsey empties.")
                        givens.append((rc_to_i(r, c), v))

        for cell, digit in givens:
            if state.candidates[cell] != ALL_DIGITS_MASK:
                raise ValueError("Invalid Sudoku givens.")
            state.candidates[cell] = bit(digit)
            state.fixed_cells.add(cell)
            state.given_cells.add(cell)

        for cell, digit in givens:
            dmask = bit(digit)
            for peer in PEERS[cell]:
                peer_mask = state.candidates[peer]
                if peer_mask == dmask:
                    raise ValueError("Invalid Sudoku givens.")
                if peer_mask & dmask:
                    state.candidates[peer] = peer_mask & ~dmask

        if not state.consistency_ok():
            raise ValueError("Invalid Sudoku givens.")

        return state

    def clone(self) -> "SudokuState":
        return SudokuState(self.candidates, self.fixed_cells, self.given_cells)

    def solved(self) -> bool:
        return all(is_single(mask) for mask in self.candidates)

    def board(self) -> List[List[int]]:
        out = [[0] * 9 for _ in range(9)]
        for i, mask in enumerate(self.candidates):
            if is_single(mask):
                r, c = i_to_rc(i)
                out[r][c] = single_digit(mask)
        return out

    def pretty(self) -> str:
        lines = []
        for r in range(9):
            if r and r % 3 == 0:
                lines.append("-" * 21)
            row_parts = []
            for c in range(9):
                if c and c % 3 == 0:
                    row_parts.append("|")
                i = rc_to_i(r, c)
                row_parts.append(str(single_digit(self.candidates[i])) if is_single(self.candidates[i]) else ".")
            lines.append(" ".join(row_parts))
        return "\n".join(lines)

    def candidate_mask(self, cell: int) -> int:
        return self.candidates[cell]

    def candidate_digits(self, cell: int) -> List[int]:
        return digits_from_mask(self.candidates[cell])

    def can_place(self, cell: int, digit: int) -> bool:
        return bool(self.candidates[cell] & bit(digit))

    def is_bivalue(self, cell: int) -> bool:
        return bit_count(self.candidates[cell]) == 2

    def is_trivalue(self, cell: int) -> bool:
        return bit_count(self.candidates[cell]) == 3

    def consistency_ok(self) -> bool:
        # no empty cells
        if any(mask == 0 for mask in self.candidates):
            return False

        # each digit must have at least one possible place in each unit
        for unit in ALL_UNITS:
            seen_fixed = set()
            for cell in unit:
                mask = self.candidates[cell]
                if is_single(mask):
                    d = single_digit(mask)
                    if d in seen_fixed:
                        return False
                    seen_fixed.add(d)

            for d in range(1, 10):
                dmask = bit(d)
                if not any(self.candidates[cell] & dmask for cell in unit):
                    return False

        return True

    def eliminate_digit(self, cell: int, digit: int) -> bool:
        """
        Remove one candidate from a cell.
        If the cell becomes single, propagate that single to peers.
        """
        dmask = bit(digit)
        cur = self.candidates[cell]

        if not (cur & dmask):
            return True  # already absent

        new_mask = cur & ~dmask
        if new_mask == 0:
            return False

        self.candidates[cell] = new_mask

        if is_single(new_mask):
            fixed_digit = single_digit(new_mask)
            fixed_mask = bit(fixed_digit)
            self.fixed_cells.add(cell)

            # remove fixed_digit from all peers
            for peer in PEERS[cell]:
                if self.candidates[peer] & fixed_mask:
                    if not self.eliminate_digit(peer, fixed_digit):
                        return False

        return True

    def place_digit(self, cell: int, digit: int) -> bool:
        """
        Set cell to exactly one digit by removing all others,
        then remove that digit from peers.
        """
        if not self.can_place(cell, digit):
            return False

        cur_digits = self.candidate_digits(cell)
        for d in cur_digits:
            if d != digit:
                if not self.eliminate_digit(cell, d):
                    return False

        # ensure peers do not contain the placed digit
        for peer in PEERS[cell]:
            if self.can_place(peer, digit):
                if not self.eliminate_digit(peer, digit):
                    return False

        self.fixed_cells.add(cell)
        return True

    def apply_move(self, move: Move) -> bool:
        """
        Applies placements first, then eliminations.
        """
        for p in move.placements:
            if not self.place_digit(p.cell, p.digit):
                return False

        for e in move.eliminations:
            if not self.eliminate_digit(e.cell, e.digit):
                return False

        return self.consistency_ok()


# ============================================================
# Technique base
# ============================================================

class Technique:
    name: str = "Technique"
    difficulty: int = 0

    def find_moves(self, state: SudokuState) -> List[Move]:
        raise NotImplementedError


# ============================================================
# Basic techniques
# ============================================================

class NakedSingle(Technique):
    name = "Naked Single"
    difficulty = 1

    def find_moves(self, state: SudokuState) -> List[Move]:
        for cell in range(81):
            mask = state.candidate_mask(cell)
            if is_single(mask) and cell not in state.fixed_cells:
                digit = single_digit(mask)
                r, c = i_to_rc(cell)
                return [
                    Move(
                        technique=self.name,
                        difficulty=self.difficulty,
                        reason=f"r{r+1}c{c+1} is forced to {digit}.",
                        placements=[Placement(cell, digit)],
                    )
                ]
        return []


class HiddenSingle(Technique):
    name = "Hidden Single"
    difficulty = 1

    def find_moves(self, state: SudokuState) -> List[Move]:
        for unit_index, unit in enumerate(ALL_UNITS):
            for d in range(1, 10):
                cells = [cell for cell in unit if state.can_place(cell, d)]
                if len(cells) == 1:
                    cell = cells[0]
                    if not is_single(state.candidate_mask(cell)):
                        return [
                            Move(
                                technique=self.name,
                                difficulty=self.difficulty,
                                reason=f"Digit {d} can only go in {cell_text(cell)} within {unit_text(unit_index)}.",
                                placements=[Placement(cell, d)],
                            )
                        ]
        return []


class LockedCandidates(Technique):
    """
    Pointing + claiming.
    """
    name = "Locked Candidates"
    difficulty = 2

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        # Pointing: box -> row / column
        for box_index, box in enumerate(BOX_UNITS):
            for d in range(1, 10):
                cells = [cell for cell in box if state.can_place(cell, d)]
                if len(cells) < 2:
                    continue

                rows = {ROW_OF[cell] for cell in cells}
                cols = {COL_OF[cell] for cell in cells}

                if len(rows) == 1:
                    row = next(iter(rows))
                    eliminations = [
                        Elimination(cell, d)
                        for cell in ROW_UNITS[row]
                        if cell not in box and state.can_place(cell, d)
                    ]
                    if eliminations:
                        moves.append(
                            Move(
                                technique=self.name,
                                difficulty=self.difficulty,
                                reason=f"Pointing: digit {d} in box {box_index+1} is confined to row {row+1}.",
                                eliminations=eliminations,
                                cause_cells=cells,
                            )
                        )

                if len(cols) == 1:
                    col = next(iter(cols))
                    eliminations = [
                        Elimination(cell, d)
                        for cell in COL_UNITS[col]
                        if cell not in box and state.can_place(cell, d)
                    ]
                    if eliminations:
                        moves.append(
                            Move(
                                technique=self.name,
                                difficulty=self.difficulty,
                                reason=f"Pointing: digit {d} in box {box_index+1} is confined to column {col+1}.",
                                eliminations=eliminations,
                                cause_cells=cells,
                            )
                        )

        # Claiming: row / column -> box
        for family_name, unit_list in (("row", ROW_UNITS), ("column", COL_UNITS)):
            for unit_index, unit in enumerate(unit_list):
                for d in range(1, 10):
                    cells = [cell for cell in unit if state.can_place(cell, d)]
                    if len(cells) < 2:
                        continue

                    boxes = {BOX_OF[cell] for cell in cells}
                    if len(boxes) == 1:
                        box_index = next(iter(boxes))
                        box = BOX_UNITS[box_index]
                        eliminations = [
                            Elimination(cell, d)
                            for cell in box
                            if cell not in unit and state.can_place(cell, d)
                        ]
                        if eliminations:
                            moves.append(
                                Move(
                                    technique=self.name,
                                    difficulty=self.difficulty,
                                    reason=f"Claiming: digit {d} in {family_name} {unit_index+1} is confined to box {box_index+1}.",
                                    eliminations=eliminations,
                                    cause_cells=cells,
                                )
                            )

        return moves


class NakedSubset(Technique):
    """
    Generic naked pair / triple / quad.
    """
    def __init__(self, size: int):
        self.size = size
        self.name = {2: "Naked Pair", 3: "Naked Triple", 4: "Naked Quad"}[size]
        self.difficulty = {2: 3, 3: 4, 4: 5}[size]

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for unit in ALL_UNITS:
            candidate_cells = [
                cell
                for cell in unit
                if 2 <= bit_count(state.candidate_mask(cell)) <= self.size
            ]

            for combo in combinations(candidate_cells, self.size):
                union_mask = 0
                for cell in combo:
                    union_mask |= state.candidate_mask(cell)

                if bit_count(union_mask) != self.size:
                    continue

                eliminations: List[Elimination] = []
                for other in unit:
                    if other in combo:
                        continue
                    for d in bits(union_mask):
                        if state.can_place(other, d):
                            eliminations.append(Elimination(other, d))

                if eliminations:
                    combo_text = ", ".join(f"r{i_to_rc(c)[0]+1}c{i_to_rc(c)[1]+1}" for c in combo)
                    digits_text = digits_from_mask(union_mask)
                    moves.append(
                        Move(
                            technique=self.name,
                            difficulty=self.difficulty,
                            reason=f"{self.name}: cells {combo_text} contain only digits {digits_text}.",
                            eliminations=eliminations,
                            cause_cells=list(combo),
                        )
                    )

        return moves


class HiddenSubset(Technique):
    """
    Generic hidden pair / triple / quad.
    """
    def __init__(self, size: int):
        self.size = size
        self.name = {2: "Hidden Pair", 3: "Hidden Triple", 4: "Hidden Quad"}[size]
        self.difficulty = {2: 3, 3: 4, 4: 5}[size]

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for unit in ALL_UNITS:
            cells_by_digit = {
                d: [cell for cell in unit if state.can_place(cell, d)]
                for d in range(1, 10)
            }

            for digits_combo in combinations(range(1, 10), self.size):
                combo_mask = 0
                cells_set = set()
                for d in digits_combo:
                    combo_mask |= bit(d)
                    cells_set.update(cells_by_digit[d])

                cells = [cell for cell in unit if cell in cells_set]
                if len(cells) != self.size:
                    continue

                # each digit must appear at least once in those cells
                if any(not cells_by_digit[d] for d in digits_combo):
                    continue

                eliminations: List[Elimination] = []
                for cell in cells:
                    for d in state.candidate_digits(cell):
                        if d not in digits_combo:
                            eliminations.append(Elimination(cell, d))

                if eliminations:
                    cell_text = ", ".join(f"r{i_to_rc(c)[0]+1}c{i_to_rc(c)[1]+1}" for c in cells)
                    moves.append(
                        Move(
                            technique=self.name,
                            difficulty=self.difficulty,
                            reason=f"{self.name}: digits {list(digits_combo)} are confined to cells {cell_text}.",
                            eliminations=eliminations,
                            cause_cells=cells,
                        )
                    )

        return moves


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


class UniqueRectangleType1(Technique):
    name = "Unique Rectangle Type 1"
    difficulty = 7

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for r1, r2 in combinations(range(9), 2):
            for c1, c2 in combinations(range(9), 2):
                cells = [
                    rc_to_i(r1, c1),
                    rc_to_i(r1, c2),
                    rc_to_i(r2, c1),
                    rc_to_i(r2, c2),
                ]

                # Standard UR rectangle spans exactly two boxes
                boxes = {BOX_OF[cell] for cell in cells}
                if len(boxes) != 2:
                    continue

                masks = [state.candidate_mask(cell) for cell in cells]
                bivalue_masks = [m for m in masks if bit_count(m) == 2]
                if len(bivalue_masks) < 3:
                    continue

                counts = {}
                for m in bivalue_masks:
                    counts[m] = counts.get(m, 0) + 1

                pair_mask = None
                for m, cnt in counts.items():
                    if cnt >= 3 and bit_count(m) == 2:
                        pair_mask = m
                        break

                if pair_mask is None:
                    continue

                pair_cells = [cells[idx] for idx, m in enumerate(masks) if m == pair_mask]
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
                    rr, cc = i_to_rc(odd_cell)
                    moves.append(
                        Move(
                            technique=self.name,
                            difficulty=self.difficulty,
                            reason=(
                                f"Unique Rectangle Type 1 on rows {r1+1},{r2+1} and columns {c1+1},{c2+1}: "
                                f"three corners form deadly pair {pair_digits}, so r{rr+1}c{cc+1} "
                                f"cannot keep both of those digits."
                            ),
                            eliminations=eliminations,
                            cause_cells=cells,
                        )
                    )

        return moves


class UniqueRectangleType2(Technique):
    name = "Unique Rectangle Type 2"
    difficulty = 7

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for r1, r2 in combinations(range(9), 2):
            for c1, c2 in combinations(range(9), 2):
                cells = [
                    rc_to_i(r1, c1),
                    rc_to_i(r1, c2),
                    rc_to_i(r2, c1),
                    rc_to_i(r2, c2),
                ]
                if len({BOX_OF[cell] for cell in cells}) != 2:
                    continue

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
                    eliminations = [
                        Elimination(cell, extra_digit)
                        for cell in (PEERS[extra_cells[0]] & PEERS[extra_cells[1]])
                        if cell not in cells and state.can_place(cell, extra_digit)
                    ]
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
                            )
                        )

        return moves


class UniqueRectangleType4(Technique):
    name = "Unique Rectangle Type 4"
    difficulty = 7

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for r1, r2 in combinations(range(9), 2):
            for c1, c2 in combinations(range(9), 2):
                cells = [
                    rc_to_i(r1, c1),
                    rc_to_i(r1, c2),
                    rc_to_i(r2, c1),
                    rc_to_i(r2, c2),
                ]
                if len({BOX_OF[cell] for cell in cells}) != 2:
                    continue

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
                            cells_for_digit = [cell for cell in unit if state.can_place(cell, strong_digit)]
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
                                    )
                                )

        return moves


class BUGPlusOne(Technique):
    name = "BUG+1"
    difficulty = 7

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        unsolved = [cell for cell in range(81) if not is_single(state.candidate_mask(cell))]
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
                r, c = i_to_rc(cell)
                moves.append(
                    Move(
                        technique=self.name,
                        difficulty=self.difficulty,
                        reason=(
                            f"BUG+1: r{r+1}c{c+1} is the only tri-value cell, "
                            f"so digit {d} must be placed there."
                        ),
                        placements=[Placement(cell, d)],
                        cause_cells=[cell],
                    )
                )

        return moves


class Nishio(Technique):
    name = "Nishio"
    difficulty = 8

    def find_moves(self, state: SudokuState) -> List[Move]:
        moves: List[Move] = []

        for cell in range(81):
            if is_single(state.candidate_mask(cell)):
                continue

            for digit in state.candidate_digits(cell):
                child = state.clone()
                if child.place_digit(cell, digit) and child.consistency_ok():
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
                    )
                )

        return moves


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

class SudokuSolver:
    def __init__(self, techniques: Optional[List[Technique]] = None, strategy: str = "human"):
        self.strategy = strategy
        if techniques is not None:
            self.techniques = techniques
        elif strategy == "fastest":
            self.techniques = self.fast_techniques()
        else:
            self.techniques = self.default_techniques()

    @staticmethod
    def default_techniques() -> List[Technique]:
        return [
            NakedSingle(),
            HiddenSingle(),
            LockedCandidates(),
            NakedSubset(2),
            HiddenSubset(2),
            NakedSubset(3),
            HiddenSubset(3),
            NakedSubset(4),
            HiddenSubset(4),
            Fish(2),   # X-Wing
            FinnedXWing(),
            SimpleColoring(),
            Skyscraper(),
            TwoStringKite(),
            TurbotFish(),
            WWing(),
            RemotePairs(),
            Fish(3),   # Swordfish
            XYWing(),
            Fish(4),   # Jellyfish
            XYZWing(),
            UniqueRectangleType1(),
            UniqueRectangleType2(),
            UniqueRectangleType4(),
            BUGPlusOne(),
            Nishio(),
        ]

    @staticmethod
    def fast_techniques() -> List[Technique]:
        return [
            NakedSingle(),
            HiddenSingle(),
            LockedCandidates(),
            NakedSubset(2),
            HiddenSubset(2),
        ]

    def next_move(self, state: SudokuState) -> Optional[Move]:
        """
        Pick the first valid move according to technique order.
        """
        if self.strategy == "fewest-steps":
            return self._highest_impact_move(state)

        for technique in self.techniques:
            moves = technique.find_moves(state)
            if moves:
                return self._best_move(moves)
        return None

    def _best_move(self, moves: List[Move]) -> Move:
        """
        Simple heuristic:
          - more eliminations / placements first
          - lower difficulty first
        """
        return min(
            moves,
            key=lambda m: (
                -len(m.placements) - len(m.eliminations),
                m.difficulty,
                m.technique,
            )
        )

    def _highest_impact_move(self, state: SudokuState) -> Optional[Move]:
        best_move: Optional[Move] = None
        best_score: Optional[Tuple[int, int, int, int]] = None

        before_solved = sum(1 for mask in state.candidates if is_single(mask))
        before_candidates = sum(bit_count(mask) for mask in state.candidates)

        for technique in self.techniques:
            for move in technique.find_moves(state):
                child = state.clone()
                if not child.apply_move(move):
                    continue

                after_solved = sum(1 for mask in child.candidates if is_single(mask))
                after_candidates = sum(bit_count(mask) for mask in child.candidates)
                score = (
                    after_solved - before_solved,
                    before_candidates - after_candidates,
                    len(move.placements) + len(move.eliminations),
                    -move.difficulty,
                )

                if best_score is None or score > best_score:
                    best_score = score
                    best_move = move

        return best_move

    def _expanded_steps(self, before: SudokuState, after: SudokuState, move: Move) -> List[Move]:
        replay = before.clone()
        steps: List[Move] = []
        forced_queue: List[Tuple[int, int]] = []
        queued_forced: set[int] = set()

        def append_step(step: Move, changed_cells: Iterable[int]) -> None:
            step.after_candidates = replay.candidates[:]
            step.changed_cells = sorted(set(changed_cells))
            steps.append(step)

        def queue_forced_single(cell: int, difficulty: int) -> None:
            if cell not in replay.fixed_cells and cell not in queued_forced and is_single(replay.candidate_mask(cell)):
                forced_queue.append((cell, difficulty))
                queued_forced.add(cell)

        def process_forced_singles() -> bool:
            while forced_queue:
                cell, difficulty = forced_queue.pop(0)
                queued_forced.discard(cell)
                if cell in replay.fixed_cells or not is_single(replay.candidate_mask(cell)):
                    continue
                if not select_forced_single(cell, difficulty):
                    return False
            return True

        def propagate_digit(source_cell: int, digit: int, difficulty: int) -> bool:
            eliminations: List[Elimination] = []
            for peer in sorted(PEERS[source_cell]):
                if not replay.can_place(peer, digit):
                    continue

                new_mask = replay.candidate_mask(peer) & ~bit(digit)
                if new_mask == 0:
                    return False

                replay.candidates[peer] = new_mask
                eliminations.append(Elimination(peer, digit))
                if is_single(new_mask):
                    queue_forced_single(peer, difficulty)

            if eliminations:
                noun = "peer" if len(eliminations) == 1 else "peers"
                step = Move(
                    technique="Propagation",
                    difficulty=difficulty,
                    reason=f"{placement_text(Placement(source_cell, digit))} removes {digit} from {len(eliminations)} {noun}.",
                    eliminations=eliminations,
                )
                step.cause_cells = [source_cell]
                append_step(step, [elimination.cell for elimination in eliminations])

            return True

        def select_digit(cell: int, digit: int, technique: str, reason: str, difficulty: int) -> bool:
            if not replay.can_place(cell, digit):
                return False

            replay.candidates[cell] = bit(digit)
            replay.fixed_cells.add(cell)
            append_step(
                Move(
                    technique=technique,
                    difficulty=difficulty,
                    reason=reason,
                    placements=[Placement(cell, digit)],
                ),
                [cell],
            )

            if not propagate_digit(cell, digit, difficulty):
                return False
            return process_forced_singles()

        def select_forced_single(cell: int, difficulty: int) -> bool:
            digit = single_digit(replay.candidate_mask(cell))
            r, c = i_to_rc(cell)
            return select_digit(
                cell,
                digit,
                "Naked Single",
                f"r{r+1}c{c+1} is forced to {digit}.",
                difficulty,
            )

        def eliminate_digits_group(
            eliminations: Sequence[Elimination],
            technique: str,
            reason: str,
            difficulty: int,
            cause_cells: Optional[Iterable[int]] = None,
        ) -> bool:
            applied: List[Elimination] = []
            changed_cells: List[int] = []

            for elimination in eliminations:
                dmask = bit(elimination.digit)
                cur = replay.candidate_mask(elimination.cell)
                if not (cur & dmask):
                    continue

                new_mask = cur & ~dmask
                if new_mask == 0:
                    return False

                replay.candidates[elimination.cell] = new_mask
                applied.append(elimination)
                changed_cells.append(elimination.cell)
                if is_single(new_mask) and elimination.cell not in replay.fixed_cells:
                    queue_forced_single(elimination.cell, difficulty)

            if applied:
                step = Move(
                    technique=technique,
                    difficulty=difficulty,
                    reason=reason,
                    eliminations=applied,
                )
                step.cause_cells = sorted(set(cause_cells or []))
                append_step(step, changed_cells)

            return True

        for placement in move.placements:
            cell = placement.cell
            digit = placement.digit
            if not replay.can_place(cell, digit):
                return self._coarse_expanded_steps(before, after, move)

            if not select_digit(cell, digit, move.technique, move.reason, move.difficulty):
                return self._coarse_expanded_steps(before, after, move)

        if move.eliminations:
            if not eliminate_digits_group(
                move.eliminations,
                move.technique,
                move.reason,
                move.difficulty,
                move.cause_cells,
            ):
                return self._coarse_expanded_steps(before, after, move)

        if not process_forced_singles():
            return self._coarse_expanded_steps(before, after, move)

        if replay.candidates != after.candidates:
            return self._coarse_expanded_steps(before, after, move)

        return steps

    def _explanation_steps(self, before: SudokuState, after: SudokuState, move: Move, detailed_steps: bool) -> List[Move]:
        if detailed_steps:
            return self._expanded_steps(before, after, move)
        return self._coarse_expanded_steps(before, after, move)

    def _coarse_expanded_steps(self, before: SudokuState, after: SudokuState, move: Move) -> List[Move]:
        changed_cells = {
            cell
            for cell, (before_mask, after_mask) in enumerate(zip(before.candidates, after.candidates))
            if before_mask != after_mask
        }

        full_move = Move(
            technique=move.technique,
            difficulty=move.difficulty,
            reason=move.reason,
            placements=move.placements[:],
            eliminations=move.eliminations[:],
        )
        full_move.cause_cells = move.cause_cells[:]

        known_eliminations = {(elimination.cell, elimination.digit) for elimination in full_move.eliminations}
        for cell, (before_mask, after_mask) in enumerate(zip(before.candidates, after.candidates)):
            removed_mask = before_mask & ~after_mask
            for digit in digits_from_mask(removed_mask):
                key = (cell, digit)
                if key not in known_eliminations:
                    full_move.eliminations.append(Elimination(cell, digit))
                    known_eliminations.add(key)

        full_move.after_candidates = after.candidates[:]
        full_move.changed_cells = sorted(changed_cells)
        steps = [full_move]
        placed_cells = {placement.cell for placement in full_move.placements}

        for cell, (before_mask, after_mask) in enumerate(zip(before.candidates, after.candidates)):
            if cell in placed_cells:
                continue
            if not is_single(before_mask) and is_single(after_mask):
                digit = single_digit(after_mask)
                r, c = i_to_rc(cell)
                implied_move = Move(
                    technique="Naked Single",
                    difficulty=1,
                    reason=f"r{r+1}c{c+1} is forced to {digit}.",
                    placements=[Placement(cell, digit)],
                )
                implied_move.after_candidates = after.candidates[:]
                implied_move.changed_cells = [cell]
                steps.append(implied_move)

        return steps

    def _has_unprocessed_singles(self, state: SudokuState) -> bool:
        return any(
            is_single(state.candidate_mask(cell)) and cell not in state.fixed_cells
            for cell in range(81)
        )

    def solve_logic(
        self,
        state: SudokuState,
        explain: bool = True,
        detailed_steps: bool = True,
    ) -> Tuple[bool, List[Move]]:
        steps: List[Move] = []

        while not state.solved() or (explain and self._has_unprocessed_singles(state)):
            move = self.next_move(state)
            if move is None:
                return False, steps

            before = state.clone() if explain else None
            if not state.apply_move(move):
                return False, steps

            if explain and before is not None:
                steps.extend(self._explanation_steps(before, state, move, detailed_steps))

        return True, steps

    def solve_with_search(
        self,
        state: SudokuState,
        explain: bool = True,
        detailed_steps: bool = True,
    ) -> Tuple[Optional[SudokuState], List[Move]]:
        """
        Logic first; if stuck, use MRV backtracking.
        """
        all_steps: List[Move] = []

        solved_logically, logic_steps = self.solve_logic(state, explain=explain, detailed_steps=detailed_steps)
        all_steps.extend(logic_steps)

        if solved_logically:
            return state, all_steps

        if not state.consistency_ok():
            return None, all_steps

        unsolved_cells = [cell for cell in range(81) if not is_single(state.candidate_mask(cell))]
        if not unsolved_cells:
            return None, all_steps

        # MRV heuristic
        cell = min(unsolved_cells, key=lambda c: bit_count(state.candidate_mask(c)))

        for d in state.candidate_digits(cell):
            child = state.clone()
            guess_move = Move(
                technique="Guess",
                difficulty=99,
                reason=f"MRV guess: try {d} in r{i_to_rc(cell)[0]+1}c{i_to_rc(cell)[1]+1}.",
                placements=[Placement(cell, d)],
            )

            before_guess = child.clone() if explain else None
            if not child.apply_move(guess_move):
                continue
            after_guess = child.clone() if explain else None

            result, child_steps = self.solve_with_search(child, explain=explain, detailed_steps=detailed_steps)
            if result is not None:
                if explain:
                    guess_steps = (
                        self._explanation_steps(before_guess, after_guess, guess_move, detailed_steps)
                        if before_guess and after_guess
                        else [guess_move]
                    )
                    return result, all_steps + guess_steps + child_steps
                return result, all_steps

        return None, all_steps

    def solve_search_first(
        self,
        state: SudokuState,
        explain: bool = True,
        detailed_steps: bool = True,
    ) -> Tuple[Optional[SudokuState], List[Move]]:
        if state.solved():
            return state, []

        if not state.consistency_ok():
            return None, []

        unsolved_cells = [cell for cell in range(81) if not is_single(state.candidate_mask(cell))]
        if not unsolved_cells:
            return None, []

        cell = min(unsolved_cells, key=lambda c: bit_count(state.candidate_mask(c)))

        for d in state.candidate_digits(cell):
            child = state.clone()
            guess_move = Move(
                technique="Guess",
                difficulty=99,
                reason=f"MRV guess: try {d} in r{i_to_rc(cell)[0]+1}c{i_to_rc(cell)[1]+1}.",
                placements=[Placement(cell, d)],
            )

            before_guess = child.clone() if explain else None
            if not child.apply_move(guess_move):
                continue
            after_guess = child.clone() if explain else None

            result, child_steps = self.solve_search_first(child, explain=explain, detailed_steps=detailed_steps)
            if result is not None:
                if explain:
                    guess_steps = (
                        self._explanation_steps(before_guess, after_guess, guess_move, detailed_steps)
                        if before_guess and after_guess
                        else [guess_move]
                    )
                    return result, guess_steps + child_steps
                return result, []

        return None, []


# ============================================================
# Command-line interface
# ============================================================

DEFAULT_PUZZLE = (
    "...8....3"
    "..8.61..."
    "14.37..2."
    "..4.8...7"
    "...7...4."
    "9.6.5..1."
    "2......9."
    ".1......."
    "5......3."
)


def read_puzzle_argument(puzzle: Optional[str], puzzle_file: Optional[str]) -> str:
    if puzzle and puzzle_file:
        raise ValueError("Use either a puzzle argument or --file, not both.")

    if puzzle_file:
        with open(puzzle_file, "r", encoding="utf-8") as handle:
            return handle.read()

    return puzzle or DEFAULT_PUZZLE


def pretty_puzzle(puzzle: str) -> str:
    chars = [ch for ch in puzzle if ch in "1234567890."]
    if len(chars) != 81:
        raise ValueError("String puzzle must contain exactly 81 digits / dots / zeros.")

    lines = []
    for r in range(9):
        if r and r % 3 == 0:
            lines.append("-" * 21)
        row_parts = []
        for c in range(9):
            if c and c % 3 == 0:
                row_parts.append("|")
            ch = chars[rc_to_i(r, c)]
            row_parts.append(ch if ch in "123456789" else ".")
        lines.append(" ".join(row_parts))
    return "\n".join(lines)


def placement_text(placement: Placement) -> str:
    return f"{cell_text(placement.cell)}={placement.digit}"


def elimination_text(elimination: Elimination) -> str:
    return f"{cell_text(elimination.cell)}!={elimination.digit}"


def move_change_details(move: Move) -> List[str]:
    details = [placement_text(placement) for placement in move.placements]
    details.extend(elimination_text(elimination) for elimination in move.eliminations)
    return details


def compact_move_text(move: Move) -> str:
    details = move_change_details(move)
    if details:
        return f"{move.technique}: {', '.join(details)}"
    return move.summary()


def detailed_move_text(move: Move) -> str:
    details = move_change_details(move)
    if details:
        return f"{move.summary()} Changes: {', '.join(details)}"
    return move.summary()


def compact_batch_text(technique: str, moves: Sequence[Move]) -> str:
    placements = [
        placement_text(placement)
        for move in moves
        for placement in move.placements
    ]
    eliminations = [
        elimination_text(elimination)
        for move in moves
        for elimination in move.eliminations
    ]
    details = placements + eliminations
    change_count = len(details)
    noun = "change" if change_count == 1 else "changes"

    if details:
        return f"{technique} ({change_count} {noun}): {', '.join(details)}"

    return f"{technique}: {moves[0].reason}"


def plural_technique_name(technique: str) -> str:
    if technique.endswith("Single"):
        return f"{technique}s"
    if technique == "Guess":
        return "Guesses"
    if technique.endswith("s"):
        return technique
    return f"{technique}s"


def combine_step_group(technique: str, moves: Sequence[Move]) -> Move:
    placements = [
        placement
        for move in moves
        for placement in move.placements
    ]
    eliminations = [
        elimination
        for move in moves
        for elimination in move.eliminations
    ]
    changed_cells = {
        cell
        for move in moves
        for cell in move.changed_cells
    }
    cause_cells = {
        cell
        for move in moves
        for cell in move.cause_cells
    }
    details = [placement_text(placement) for placement in placements]
    details.extend(elimination_text(elimination) for elimination in eliminations)
    change_count = len(details)
    noun = "change" if change_count == 1 else "changes"

    combined = Move(
        technique=technique,
        difficulty=max(move.difficulty for move in moves),
        reason=f"{change_count} {noun}.",
        placements=placements,
        eliminations=eliminations,
    )
    combined.after_candidates = moves[-1].after_candidates[:] if moves[-1].after_candidates is not None else None
    combined.changed_cells = sorted(changed_cells)
    combined.cause_cells = sorted(cause_cells)
    return combined


def steps_for_style(steps: Sequence[Move], style: str) -> List[Move]:
    if style == "detailed":
        return list(steps)

    formatted: List[Move] = []
    i = 0
    while i < len(steps):
        current = steps[i]

        if style == "grouped" and current.technique == "Naked Single":
            group = [current]
            i += 1
            while i < len(steps) and steps[i].technique == "Naked Single":
                group.append(steps[i])
                i += 1
            formatted.append(combine_step_group("Naked Singles", group))
            continue

        if style == "batched":
            group = [current]
            i += 1
            while i < len(steps) and steps[i].technique == current.technique:
                group.append(steps[i])
                i += 1
            technique = current.technique if len(group) == 1 else plural_technique_name(current.technique)
            formatted.append(combine_step_group(technique, group))
            continue

        formatted.append(current)
        i += 1

    return formatted


def group_progress_propagations(steps: Sequence[Move]) -> List[Move]:
    grouped: List[Move] = []
    i = 0
    while i < len(steps):
        current = steps[i]
        if current.technique != "Propagation":
            grouped.append(current)
            i += 1
            continue

        group = [current]
        i += 1
        while i < len(steps) and steps[i].technique == "Propagation":
            group.append(steps[i])
            i += 1

        technique = "Propagation" if len(group) == 1 else "Propagations"
        grouped.append(combine_step_group(technique, group))

    return grouped


def steps_for_progress(steps: Sequence[Move], style: str) -> List[Move]:
    return group_progress_propagations(steps_for_style(steps, style))


def format_steps(steps: Sequence[Move], style: str) -> List[str]:
    styled_steps = steps_for_style(steps, style)
    if style == "detailed":
        return [detailed_move_text(step) for step in styled_steps]
    return [compact_move_text(step) for step in styled_steps]


def ansi_text(text: str, *, fg: Optional[int] = None, bg: Optional[int] = None, bold: bool = False, enabled: bool = True) -> str:
    if not enabled:
        return text

    codes = []
    if bold:
        codes.append("1")
    if fg is not None:
        codes.append(str(fg))
    if bg is not None:
        codes.append(str(bg))
    if not codes:
        return text
    return f"\033[{';'.join(codes)}m{text}\033[0m"


def styled_cell(
    segments: Sequence[Tuple[str, Optional[int], Optional[int], bool]],
    width: int,
    use_color: bool,
    *,
    bg: Optional[int] = None,
) -> str:
    visible_width = sum(len(text) for text, _, _, _ in segments)
    left = max((width - visible_width) // 2, 0)
    right = max(width - visible_width - left, 0)

    parts = []
    if left:
        parts.append(ansi_text(" " * left, bg=bg, enabled=use_color))
    for text, fg, segment_bg, bold in segments:
        parts.append(ansi_text(text, fg=fg, bg=segment_bg if segment_bg is not None else bg, bold=bold, enabled=use_color))
    if right:
        parts.append(ansi_text(" " * right, bg=bg, enabled=use_color))
    return "".join(parts)


def candidate_cell_text(
    mask: int,
    eliminated_digits: set[int],
    fg: int,
    bold: bool,
    cell_width: int,
    use_color: bool,
    *,
    bg: Optional[int] = None,
) -> str:
    if eliminated_digits:
        digits = sorted(set(digits_from_mask(mask)) | eliminated_digits)
        segments = [
            (str(digit), 31 if digit in eliminated_digits else fg, bg, True if digit in eliminated_digits else bold)
            for digit in digits
        ]
        return styled_cell(segments, cell_width, use_color, bg=bg)

    text = str(single_digit(mask)) if is_single(mask) else "".join(str(d) for d in digits_from_mask(mask))
    return ansi_text(text.center(cell_width), fg=fg, bg=bg, bold=bold, enabled=use_color)


def candidate_cell_lines(
    mask: int,
    eliminated_digits: set[int],
    fg: int,
    bold: bool,
    cell_width: int,
    use_color: bool,
    *,
    bg: Optional[int] = None,
) -> List[str]:
    digits = set(digits_from_mask(mask)) | eliminated_digits
    lines = []

    for start in (1, 4, 7):
        segments = []
        for digit in range(start, start + 3):
            if digit != start:
                segments.append((" ", fg, bg, bold))
            if digit in digits:
                digit_fg = 31 if digit in eliminated_digits else fg
                digit_bold = True if digit in eliminated_digits else bold
                segments.append((str(digit), digit_fg, bg, digit_bold))
            else:
                segments.append((" ", fg, bg, bold))
        lines.append(styled_cell(segments, cell_width, use_color, bg=bg))

    return lines


def solved_cell_lines(
    text: str,
    fg: int,
    bold: bool,
    cell_width: int,
    use_color: bool,
    *,
    bg: Optional[int] = None,
) -> List[str]:
    blank = ansi_text(" " * cell_width, bg=bg, enabled=use_color)
    value = ansi_text(text.center(cell_width), fg=fg, bg=bg, bold=bold, enabled=use_color)
    return [blank, value, blank]


def render_progress_grid(
    candidates: Sequence[int],
    given_cells: set[int],
    solved_cells: set[int],
    selected_cells: Iterable[int],
    candidate_eliminations: Iterable[Elimination],
    cause_cells: Iterable[int],
    use_color: bool,
) -> str:
    selected = set(selected_cells)
    candidate_eliminated_digits: dict[int, set[int]] = {}
    for elimination in candidate_eliminations:
        candidate_eliminated_digits.setdefault(elimination.cell, set()).add(elimination.digit)
    candidate_changed = set(candidate_eliminated_digits)
    causes = set(cause_cells)
    lines = []
    cell_width = 9

    for r in range(9):
        if r and r % 3 == 0:
            lines.append("-" * 101)

        row_lines = [[], [], []]
        for c in range(9):
            if c and c % 3 == 0:
                for line_parts in row_lines:
                    line_parts.append("|")

            cell = rc_to_i(r, c)
            mask = candidates[cell]
            display_as_solved = is_single(mask) and (cell in given_cells or cell in solved_cells or cell in selected)
            if display_as_solved:
                text = str(single_digit(mask))
                if cell in given_cells:
                    fg = 37
                elif cell in solved_cells:
                    fg = 32
                else:
                    fg = 36
                bold = cell in given_cells
            else:
                fg = 36
                bold = False

            if cell in candidate_changed and cell in selected:
                cell_lines = candidate_cell_lines(
                        mask,
                        candidate_eliminated_digits[cell],
                        30,
                        True,
                        cell_width,
                        use_color,
                        bg=42,
                    )
            elif cell in candidate_changed and cell in causes:
                cell_lines = candidate_cell_lines(
                        mask,
                        candidate_eliminated_digits[cell],
                        30,
                        True,
                        cell_width,
                        use_color,
                        bg=43,
                    )
            elif cell in candidate_changed:
                cell_lines = candidate_cell_lines(
                        mask,
                        candidate_eliminated_digits[cell],
                        37,
                        True,
                        cell_width,
                        use_color,
                        bg=44,
                    )
            elif cell in causes:
                if display_as_solved:
                    cell_lines = solved_cell_lines(text, 30, True, cell_width, use_color, bg=43)
                else:
                    cell_lines = candidate_cell_lines(mask, set(), 30, True, cell_width, use_color, bg=43)
            elif cell in selected:
                if display_as_solved:
                    cell_lines = solved_cell_lines(text, 30, True, cell_width, use_color, bg=42)
                else:
                    cell_lines = candidate_cell_lines(mask, set(), 30, True, cell_width, use_color, bg=42)
            else:
                if display_as_solved:
                    cell_lines = solved_cell_lines(text, fg, bold, cell_width, use_color)
                else:
                    cell_lines = candidate_cell_lines(mask, set(), fg, bold, cell_width, use_color)

            for subline, rendered_cell in zip(row_lines, cell_lines):
                subline.append(rendered_cell)

        lines.extend(" ".join(row_line) for row_line in row_lines)

    return "\n".join(lines)


def wait_for_keypress(enabled: bool) -> bool:
    if not enabled or not sys.stdin.isatty():
        return True

    print("Press any key for next move, or q to quit...", end="", flush=True)
    try:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            key = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except KeyboardInterrupt:
        print()
        return False
    except Exception:
        try:
            key = input()
        except KeyboardInterrupt:
            print()
            return False
    print()
    return key.lower() != "q" and key != "\x03"


def print_progress_steps(
    steps: Sequence[Move],
    given_cells: set[int],
    initial_candidates: Sequence[int],
    style: str,
    use_color: bool,
    pause_after_move: bool,
) -> None:
    print("Legend:")
    print(
        "  "
        + ansi_text("original clue", fg=37, bold=True, enabled=use_color)
        + "  "
        + ansi_text("solved value", fg=32, enabled=use_color)
        + "  "
        + ansi_text("candidates", fg=36, enabled=use_color)
        + "  "
        + ansi_text("selected this step", fg=30, bg=42, bold=True, enabled=use_color)
        + "  "
        + ansi_text("candidates changed", fg=37, bg=44, bold=True, enabled=use_color)
        + "  "
        + ansi_text("elimination source", fg=30, bg=43, bold=True, enabled=use_color)
        + "  "
        + ansi_text("eliminated candidate", fg=31, bold=True, enabled=use_color)
    )
    print()

    print("Before step 1: candidates")
    solved_cells = set(given_cells)
    print(render_progress_grid(initial_candidates, given_cells, solved_cells, [], [], [], use_color))
    print()

    for i, step in enumerate(steps_for_progress(steps, style), start=1):
        print(f"{i:02d}. {step.summary()}")
        details = move_change_details(step)
        if details:
            print(f"    Changes: {', '.join(details)}")
        if step.after_candidates is None:
            print("No board snapshot available for this step.")
        else:
            selected_cells = {placement.cell for placement in step.placements}
            solved_cells.update(placement.cell for placement in step.placements)
            print(
                render_progress_grid(
                    step.after_candidates,
                    given_cells,
                    solved_cells,
                    selected_cells,
                    step.eliminations,
                    [cell for cell in step.cause_cells if cell not in selected_cells],
                    use_color,
                )
            )
        print()
        if not wait_for_keypress(pause_after_move):
            print("Step-by-step display stopped.")
            return


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Solve a Sudoku puzzle. Empty cells may be written as 0 or .; "
            "non-puzzle characters are ignored."
        )
    )
    parser.add_argument(
        "puzzle",
        nargs="?",
        help="81-character puzzle string, using 0 or . for empty cells.",
    )
    parser.add_argument(
        "-f",
        "--file",
        dest="puzzle_file",
        help="Read the puzzle from a text file.",
    )
    parser.add_argument(
        "--logic-only",
        action="store_true",
        help="Use logical techniques only; do not fall back to search.",
    )
    parser.add_argument(
        "--no-steps",
        action="store_true",
        help="Print only the original and solved boards.",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Print compact step text instead of a colored board after each step.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors in progress output.",
    )
    parser.add_argument(
        "--no-pause",
        action="store_true",
        help="Do not wait for a key press after each progress step.",
    )
    parser.add_argument(
        "--step-style",
        choices=("detailed", "grouped", "batched"),
        default="detailed",
        help=(
            "Choose how solution steps are printed. "
            "Use detailed for one line per move, grouped to collapse forced singles, "
            "or batched to collapse consecutive moves with the same technique."
        ),
    )
    parser.add_argument(
        "--strategy",
        choices=("human", "fewest-steps", "fastest", "search-first"),
        default="human",
        help=(
            "Choose how moves are selected. human uses easy techniques first, "
            "fewest-steps picks the largest-impact logical move, fastest uses cheap "
            "logic before search, and search-first starts with MRV backtracking."
        ),
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        puzzle = read_puzzle_argument(args.puzzle, args.puzzle_file)
        original_puzzle = pretty_puzzle(puzzle)
        state = SudokuState.from_board(puzzle)
    except OSError as exc:
        parser.error(f"Could not read puzzle file: {exc}")
    except ValueError as exc:
        parser.error(str(exc))

    if args.logic_only and args.strategy == "search-first":
        parser.error("--logic-only cannot be used with --strategy search-first.")

    initial_candidates = state.candidates[:]
    solver = SudokuSolver(strategy=args.strategy)
    explain = not args.no_steps
    detailed_steps = args.step_style == "detailed"

    print("Original puzzle:")
    print(original_puzzle)
    print()

    if args.strategy == "search-first":
        result, steps = solver.solve_search_first(state, explain=explain, detailed_steps=detailed_steps)
    elif args.logic_only:
        solved, steps = solver.solve_logic(state, explain=explain, detailed_steps=detailed_steps)
        result: Optional[SudokuState] = state if solved else None
    else:
        result, steps = solver.solve_with_search(state, explain=explain, detailed_steps=detailed_steps)

    if not result:
        print("No solution found.", file=sys.stderr)
        return 1

    print("Solved board:")
    print(result.pretty())

    if explain:
        print()
        print("Steps:")
        if steps:
            if args.no_progress:
                for i, step_text in enumerate(format_steps(steps, args.step_style), start=1):
                    print(f"{i:02d}. {step_text}")
            else:
                print_progress_steps(
                    steps,
                    state.given_cells,
                    initial_candidates,
                    args.step_style,
                    not args.no_color,
                    not args.no_pause,
                )
        else:
            print("Already solved; no steps needed.")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130)
    except BrokenPipeError:
        raise SystemExit(1)
