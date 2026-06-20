# Avoidable Rectangle

## Idea

Avoidable Rectangle is related to Unique Rectangle, but some rectangle cells are already solved. If none of the solved rectangle cells are original givens, then placing the remaining cells in a certain way could create an avoidable non-unique pattern.

The name reflects puzzle construction: if the final rectangle would allow a swap, a valid puzzle maker would have needed to give one of those cells as a clue.

## Why It Works

When the solved rectangle values are not givens, they could be exchanged with the remaining rectangle values without violating Sudoku rules. To preserve uniqueness, the candidate that would complete that exchangeable pattern must be eliminated from the unsolved rectangle cell.

## Solver Behavior

`AvoidableRectangle` applies conservative rectangle checks involving givens and solved cells, then removes candidates that would complete an avoidable uniqueness pattern.

## Implementation Notes

This technique relies on the unique-solution convention and on the distinction between original givens and values solved later. It should not be treated as a proof for arbitrary multi-solution grids or for grids where given-cell metadata has been lost.

Avoidable Rectangle is intentionally late in the full `human` strategy and omitted from `human-fast`. It has a relatively high scan cost and low observed yield, so future optimization should focus on prefiltering non-given rectangle shapes and solved-corner patterns before testing candidate pairs.

## References

- [HoDoKu: Uniqueness](https://hodoku.sourceforge.net/en/tech_ur.php)
