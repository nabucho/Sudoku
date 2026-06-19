# Hidden Single

## Idea

A Hidden Single places a digit when that digit has only one possible cell in a unit. The target cell may still contain several candidates, so the placement is "hidden" among other local possibilities.

The unit can be a row, column, or box. For example, if digit 6 appears as a candidate in only one cell of row 3, then row 3 must place 6 there even if that cell also lists other candidates.

## Why It Works

Every row, column, and box must contain each digit exactly once. If a digit has only one legal location in a unit, all valid solutions must use that location. Other candidates in the same cell are removed because the cell is now solved.

Hidden Singles are often found by scanning one digit at a time across a unit. This is the same logic human solvers use when cross-hatching boxes and rows or columns.

## Solver Behavior

The solver's `HiddenSingle` technique scans every unit and digit. When exactly one cell in the unit can still hold that digit, it emits a placement move whose explanation names the unit that proves the selection.

## References

- [HoDoKu: Singles](https://hodoku.sourceforge.net/en/tech_singles.php)
