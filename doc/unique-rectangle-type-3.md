# Unique Rectangle Type 3

## Idea

Unique Rectangle Type 3 combines uniqueness logic with subset logic. Two non-diagonal rectangle corners have extra candidates. Those extra candidates are treated as a virtual cell that must contain at least one extra digit to avoid the deadly rectangle.

That virtual cell can participate in a Naked Subset with other cells in the same unit.

## Why It Works

The rectangle must be prevented by at least one extra candidate in the two special corners. If those extra candidates, together with other cells, form a subset of matching size, the subset digits are locked into that group. They can be removed from other cells in the unit.

## Solver Behavior

`UniqueRectangleType3` looks for rectangle extra-candidate corners that can combine with ordinary cells into a subset. It emits eliminations from the rest of the affected unit.

## References

- [HoDoKu: Uniqueness](https://hodoku.sourceforge.net/en/tech_ur.php)
