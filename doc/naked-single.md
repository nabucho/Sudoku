# Naked Single

## Idea

A Naked Single is the simplest candidate-based placement. After all givens and previous placements have removed impossible digits, one unsolved cell has exactly one candidate left. Because every solved Sudoku cell must contain one digit, that remaining candidate must be placed.

This is called "naked" because the value is visible directly in the cell's candidate list. It does not depend on counting where a digit can appear in a row, column, or box; it depends only on the target cell having no other legal alternatives.

## Why It Works

Sudoku's row, column, and box constraints remove candidates from each cell. If a cell has one candidate, every other digit would violate at least one of those constraints. Placing the final candidate cannot remove a valid solution because any solution must already put that digit in that cell.

After placement, the digit is propagated to peers: the same digit is removed from every cell in the same row, column, and box. That propagation can create more Naked Singles.

## Solver Behavior

The solver's `NakedSingle` technique scans every unsolved cell for a one-bit candidate mask. It emits a placement move with the standard forced-cell explanation. Detailed progress mode then shows the placement and the peer eliminations caused by propagation.

## Implementation Notes

`NakedSingle` intentionally returns the first forced placement it finds rather than every naked single on the board. Singles are extremely frequent, and applying one placement can immediately change many peer candidates, so this keeps the main solve loop simple and cheap.

When detailed explanation is enabled, implied singles created by propagation are still shown as replay steps. The timing summary may therefore show naked-single usage both from direct technique selection and from detailed replay of forced consequences.

## References

- [HoDoKu: Singles](https://hodoku.sourceforge.net/en/tech_singles.php)
