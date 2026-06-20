"""Shared structural type aliases for Sudoku solver helpers."""

from __future__ import annotations

CellGroup = tuple[int, ...]
CellPair = tuple[int, int]
CellDigit = tuple[int, int]
SourceDigitRole = str
SourceDigitRoles = dict[CellDigit, SourceDigitRole]
IndexDigit = tuple[int, int]
IndexedCellGroup = tuple[int, CellGroup]
MaskTransition = tuple[int, int]
UnitCandidateCacheKey = tuple[CellGroup, bool]
EliminationKey = tuple[CellDigit, ...]
