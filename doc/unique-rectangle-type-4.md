# Unique Rectangle Type 4

## Idea

Unique Rectangle Type 4 focuses on the two rectangle digits rather than the extra candidates. If one rectangle digit is strongly restricted in a unit containing the extra-candidate corners, the other rectangle digit can be removed from those corners.

## Why It Works

To keep the puzzle unique, the rectangle cannot resolve into a swappable pair. If one rectangle digit is forced to appear in one of the two extra-candidate corners within a row, column, or box, then allowing the other rectangle digit in those same corners would preserve the deadly ambiguity. The other rectangle digit can therefore be eliminated.

## Solver Behavior

`UniqueRectangleType4` searches for strong-link style restrictions on one rectangle digit and removes the opposite rectangle digit from the relevant corners.

## Implementation Notes

This technique relies on the unique-solution convention used by human Sudoku solvers. It should not be treated as a proof for arbitrary multi-solution grids.

Type 4 is ordered before Types 2 and 3 because it is relatively cheap and benchmark data showed it was worth checking earlier. The implementation uses precomputed rectangle shapes plus mask lookup tables for repeated pair and extra-candidate checks.

## References

- [HoDoKu: Uniqueness](https://hodoku.sourceforge.net/en/tech_ur.php)
