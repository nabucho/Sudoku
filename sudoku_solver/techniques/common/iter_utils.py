"""Typed wrappers around common iterator helpers."""

from __future__ import annotations

from itertools import combinations
from typing import Iterable, Iterator, TypeVar, cast

T = TypeVar("T")
U = TypeVar("U")


def pair_combinations(items: Iterable[T]) -> Iterator[tuple[T, T]]:
    """Return typed 2-item combinations from an iterable."""
    return cast(Iterator[tuple[T, T]], combinations(items, 2))


def sized_combinations(items: Iterable[T], size: int) -> Iterator[tuple[T, ...]]:
    """Return typed combinations for a runtime-selected combination size."""
    return cast(Iterator[tuple[T, ...]], combinations(items, size))


def zip_pairs(left: Iterable[T], right: Iterable[U]) -> Iterator[tuple[T, U]]:
    """Return typed pairs from two iterables."""
    return zip(left, right)
