# Finned X-Wing

## Idea

A Finned X-Wing is an almost-X-Wing with one or more extra candidates, called fins, in the same box as one end of the pattern. The fin prevents the full X-Wing elimination, but it still proves eliminations in cells that see both the fin area and the opposite fish corner.

## Why It Works

Either the normal X-Wing is true, or one of the fins is true. If the X-Wing is true, cover-set candidates outside the base rows or columns are eliminated as usual. If a fin is true, cells that see the fin cannot contain the fish digit. Therefore any target that is eliminated in both cases is safe to remove.

This is a conditional fish deduction: it preserves only eliminations supported by both the base fish and the fin alternative.

## Solver Behavior

`FinnedXWing` searches size-two fish patterns with a fin restricted to one box. It emits only eliminations that are visible from the fin cells and compatible with the fish cover sets.

## References

- [HoDoKu: Basic Fish](https://hodoku.sourceforge.net/en/tech_fishb.php)
- [Sudoku Bliss: Advanced Sudoku Strategies](https://sudokubliss.com/guides/sudoku-advanced-strategies)
