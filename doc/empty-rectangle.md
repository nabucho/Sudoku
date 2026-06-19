# Empty Rectangle

## Idea

Empty Rectangle is a single-digit box-line chain pattern. In one box, candidates for a digit are restricted to the union of one row segment and one column segment, leaving an "empty" corner of the rectangle. A strong link outside the box can use that geometry to eliminate a candidate.

SudokuWiki notes that Empty Rectangles can be re-expressed as Grouped X-Cycles, which is why this pattern sits naturally beside other single-digit chain methods.

## Why It Works

The box restriction creates an Empty Rectangle intersection: if the digit is not placed in one arm of the box pattern, it must be placed in the other. When that implication is connected to a strong link in a row or column, both possible branches remove the same external target candidate.

The elimination is valid only when the target is seen by the relevant box-line implication and the external strong-link endpoint.

## Solver Behavior

`EmptyRectangle` uses conservative geometry checks to avoid unsound eliminations. It emits eliminations only when the box candidates, line relationship, and strong link jointly prove the target cannot contain the digit.

## References

- [SudokuWiki: Empty Rectangles](https://www.sudokuwiki.org/Print_Empty_Rectangles)
- [Sudopedia: Techniques](https://sudopedia.org/wiki/Techniques)
