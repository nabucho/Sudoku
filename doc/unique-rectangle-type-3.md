# Unique Rectangle Type 3

## Idea

Unique Rectangle Type 3 combines uniqueness logic with subset logic. Two non-diagonal rectangle corners have extra candidates. Those extra candidates are treated as a virtual cell that must contain at least one extra digit to avoid the deadly rectangle.

That virtual cell can participate in a Naked Subset with other cells in the same unit.

## Why It Works

The rectangle must be prevented by at least one extra candidate in the two special corners. If those extra candidates, together with other cells, form a subset of matching size, the subset digits are locked into that group. They can be removed from other cells in the unit.

## Solver Behavior

`UniqueRectangleType3` looks for rectangle extra-candidate corners that can combine with ordinary cells into a subset. It emits eliminations from the rest of the affected unit.

## Implementation Notes

This technique relies on the unique-solution convention used by human Sudoku solvers. It should not be treated as a proof for arbitrary multi-solution grids.

Type 3 is more expensive than the direct rectangle types because it combines deadly-pattern detection with subset searches. The implementation uses candidate masks and precomputed digit tuples for the rectangle checks, then only builds subset combinations after the virtual-cell condition is present.

## References

- [HoDoKu: Uniqueness](https://hodoku.sourceforge.net/en/tech_ur.php)
