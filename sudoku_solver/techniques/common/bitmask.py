"""Candidate digit bitmask helpers and lookup tables."""

from __future__ import annotations

from typing import Iterable, List

ALL_DIGITS_MASK = 0x1FF  # bits 0..8 => digits 1..9
DIGIT_VALUES = range(1, 10)
MASK_DIGITS = [tuple(digit + 1 for digit in range(9) if mask & (1 << digit)) for mask in range(1 << 9)]
MASK_BIT_COUNTS = [len(digits) for digits in MASK_DIGITS]
MASK_INDEXES = [tuple(index for index in range(9) if mask & (1 << index)) for mask in range(1 << 9)]


def bit(digit: int) -> int:
    """Return the candidate bitmask for a single Sudoku digit."""
    return 1 << (digit - 1)


def bits(mask: int) -> Iterable[int]:
    """Yield all digit values present in a candidate bitmask."""
    digit = 1
    while mask:
        if mask & 1:
            yield digit
        mask >>= 1
        digit += 1


def bit_count(mask: int) -> int:
    """Return the number of candidate digits present in a bitmask."""
    if 0 <= mask < len(MASK_BIT_COUNTS):
        return MASK_BIT_COUNTS[mask]
    count = 0
    while mask:
        count += mask & 1
        mask >>= 1
    return count


def is_single(mask: int) -> bool:
    """Return whether a candidate bitmask contains exactly one digit."""
    return mask != 0 and (mask & (mask - 1)) == 0


def single_digit(mask: int) -> int:
    """Valid only if is_single(mask) is True."""
    return mask.bit_length()


def digits_from_mask(mask: int) -> List[int]:
    """Return all digits present in a candidate bitmask as a list."""
    if 0 <= mask < len(MASK_DIGITS):
        return list(MASK_DIGITS[mask])
    return list[int](bits(mask))
