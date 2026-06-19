# Hidden Subsets

## Idea

Hidden Subsets are the counterpart to Naked Subsets. In one unit, if `N` digits can appear only in the same `N` cells, those cells must contain those digits in some order. Any other candidates in those cells can be removed.

The subset is "hidden" because the target cells may contain many extra candidates before the technique is applied.

## Why It Works

Every digit must appear once in the unit. If two digits are limited to two cells, those cells must become those two digits. The same logic extends to triples and quads. Extra candidates in the subset cells would leave too few cells for the confined digits, so the extras cannot be part of any valid solution.

## Solver Behavior

The solver uses `HiddenSubset(size)` for sizes 2, 3, and 4. It scans each unit for digit combinations whose possible cells match the subset size, then removes all non-subset candidates from those cells.

## References

- [HoDoKu: Hidden Subsets](https://hodoku.sourceforge.net/en/tech_hidden.php)
