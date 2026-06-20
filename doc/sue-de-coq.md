# Sue de Coq

## Idea

Sue de Coq is a box-line subset-counting technique. It looks at the unsolved cells where a row or column intersects a 3x3 box, then pairs that intersection with companion cells from the same line and from the same box.

When the intersection and its companions contain exactly as many distinct candidates as cells, they form overlapping locked sets. The line companion candidates can be removed from the rest of the line, the box companion candidates can be removed from the rest of the box, and candidates left in the intersection can be removed from both affected houses.

## Why It Works

The intersection cells must take some candidates from the combined candidate pool. The line-only companion set and the box-only companion set force the remaining candidates to split between the two houses. If a candidate is locked into the Sue de Coq pattern inside a line or box, no other cell in that house can contain it.

This is a special case of subset counting and is closely related to Almost Locked Set logic.

## Solver Behavior

`SueDeCoq` implements the basic HoDoKu-style variant: two intersection cells with four candidates or three intersection cells with five candidates, plus one bivalue companion in the line and one bivalue companion in the box. It verifies that the companion candidates are drawn from the intersection and split disjointly, then removes line-locked candidates from the rest of the line and box-locked candidates from the rest of the box.

## References

- [HoDoKu: Sue de Coq](https://hodoku.sourceforge.net/en/tech_misc.php)
- [Sudopedia: Sue de Coq](https://sudopedia.sudocue.net/index.php?title=Sue_de_Coq)
- [SudokuWiki: Sue-De-Coq](https://www.sudokuwiki.org/Print_Sue_De_Coq)
