# Locked Candidates

## Idea

Locked Candidates use the intersection between a box and a row or column. There are two common forms:

- Pointing: all candidates for a digit inside one box lie on the same row or column.
- Claiming: all candidates for a digit inside one row or column lie inside the same box.

In either case, the digit is "locked" into the intersection, so matching candidates outside the intersection can be removed.

## Why It Works

For pointing, a box must contain the digit somewhere. If every possible location in that box lies on one row, then that row's copy of the digit must be inside the box. The digit can be removed from the rest of the row outside the box.

For claiming, a row or column must contain the digit somewhere. If every possible location in that line lies inside one box, then the box's copy of the digit must be in that line. The digit can be removed from the rest of the box.

## Solver Behavior

The solver's `LockedCandidates` technique implements both pointing and claiming. It groups eliminations from one locked relationship into a single move, and marks the source cells as causes in progress output.

## References

- [HoDoKu: Intersections](https://hodoku.sourceforge.net/en/tech_intersections.php)
