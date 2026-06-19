# BUG+1

## Idea

BUG means Binary Universal Grave. In a BUG state, every unsolved cell is bivalue and every remaining candidate appears exactly twice in every row, column, and box where it appears. Such a state would admit two solutions.

BUG+1 is the near-miss version: exactly one unsolved cell has three candidates. That extra candidate is the value that prevents the deadly BUG pattern.

## Why It Works

If the tri-value cell were reduced to either of its two BUG-compatible candidates, the grid would become a Binary Universal Grave and violate the uniqueness assumption. Therefore the third candidate must be true. Equivalently, the two BUG-compatible candidates can be eliminated from the tri-value cell.

## Solver Behavior

`BUGPlusOne` verifies the near-BUG structure and places the digit in the single tri-value cell that breaks the pattern.

## References

- [HoDoKu: Uniqueness](https://hodoku.sourceforge.net/en/tech_ur.php)
