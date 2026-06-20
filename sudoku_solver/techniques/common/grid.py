"""Sudoku grid topology and cell-coordinate formatting helpers."""

from __future__ import annotations

from typing import Iterable, List, Tuple

ROW_INDICES = range(9)
COLUMN_INDICES = range(9)
CELL_INDICES = range(81)


def rc_to_i(row: int, col: int) -> int:
    """Convert zero-based row and column coordinates to a cell index."""
    return row * 9 + col


def i_to_rc(cell: int) -> Tuple[int, int]:
    """Convert a cell index to zero-based row and column coordinates."""
    return divmod(cell, 9)


def cell_text(cell: int) -> str:
    """Format a cell index as a human-readable coordinate, such as r1c1."""
    r, c = i_to_rc(cell)
    return f"r{r+1}c{c+1}"


def cells_text(cells: Iterable[int]) -> str:
    """Format multiple cell indices as comma-separated coordinates."""
    return ", ".join(cell_text(cell) for cell in cells)


def forced_cell_reason(cell: int, digit: int) -> str:
    """Return the standard explanation text for a forced placement."""
    return f"{cell_text(cell)} is forced to {digit}."


ROW_UNITS = [[rc_to_i(row, col) for col in COLUMN_INDICES] for row in ROW_INDICES]
COL_UNITS = [[rc_to_i(row, col) for row in ROW_INDICES] for col in COLUMN_INDICES]
BOX_UNITS = [
    [
        rc_to_i(row, col)
        for row in range(br * 3, br * 3 + 3)
        for col in range(bc * 3, bc * 3 + 3)
    ]
    for br in range(3)
    for bc in range(3)
]
ALL_UNITS = ROW_UNITS + COL_UNITS + BOX_UNITS


def unit_text(unit_index: int) -> str:
    """Format an ALL_UNITS index as row, column, or box text."""
    if unit_index < 9:
        return f"row {unit_index + 1}"
    if unit_index < 18:
        return f"column {unit_index - 8}"
    return f"box {unit_index - 17}"


CELL_UNITS: List[List[List[int]]] = [[] for _ in CELL_INDICES]
CELL_UNIT_INDICES: List[List[int]] = [[] for _ in CELL_INDICES]
for unit_index, unit in enumerate[List[int]](ALL_UNITS):
    for cell in unit:
        CELL_UNITS[cell].append(unit)
        CELL_UNIT_INDICES[cell].append(unit_index)

PEERS: List[set[int]] = []
for cell in CELL_INDICES:
    peers: set[int] = set[int]()
    for unit in CELL_UNITS[cell]:
        peers.update(unit)
    peers.discard(cell)
    PEERS.append(peers)

ROW_OF = [cell // 9 for cell in CELL_INDICES]
COL_OF = [cell % 9 for cell in CELL_INDICES]
BOX_OF = [((cell // 9) // 3) * 3 + ((cell % 9) // 3) for cell in CELL_INDICES]
