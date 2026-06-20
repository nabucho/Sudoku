# Naked Subsets

## Idea

Naked Subsets generalize Naked Pairs, Naked Triples, and Naked Quads. In one unit, if `N` cells contain only `N` different candidates between them, those candidates must occupy those cells in some order.

The cells do not all need to contain every digit in the subset. A naked triple, for example, can be made from candidate sets `{1,2}`, `{1,3}`, and `{2,3}` because the union is exactly three digits across exactly three cells.

## Why It Works

The selected `N` cells must be filled by `N` digits. If their combined candidates contain only those `N` digits, no other digit can occupy those cells. Conversely, those `N` digits have no capacity left to appear elsewhere in the same row, column, or box. They can therefore be removed from other cells in the unit.

## Solver Behavior

The solver uses the generic `NakedSubset(size)` implementation for sizes 2, 3, and 4. Strategy output names them as Naked Pair, Naked Triple, or Naked Quad depending on size. Eliminations from the subset are grouped into one move.

## Implementation Notes

The subset implementation uses candidate masks and combination helpers to keep pair, triple, and quad logic shared. Quads are included in the full human-style technique list for completeness, but they are naturally lower-yield and later than cheaper subset sizes.

When optimizing this family, preserve the generic size-based implementation unless benchmark data shows a specific size needs specialized handling.

## References

- [HoDoKu: Naked Subsets](https://hodoku.sourceforge.net/en/tech_naked.php)
