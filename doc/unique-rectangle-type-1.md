# Unique Rectangle Type 1

## Idea

Unique Rectangle techniques assume the puzzle has a single solution. A Unique Rectangle uses four cells occupying exactly two rows, two columns, and two boxes. If all four cells could resolve to the same two digits, those digits could be swapped to create a second solution.

Type 1 occurs when three corners are restricted to the rectangle pair and the fourth corner has extra candidates.

## Why It Works

If the fourth corner were also reduced to only the rectangle pair, the four cells would form a deadly pattern with two interchangeable solutions. A valid unique puzzle must avoid that state. Therefore the extra-candidate corner must take one of its extra candidates, and the rectangle-pair digits can be removed from that corner.

## Solver Behavior

`UniqueRectangleType1` identifies near-deadly rectangles and eliminates the rectangle digits from the only corner that has additional candidates.

## References

- [HoDoKu: Uniqueness](https://hodoku.sourceforge.net/en/tech_ur.php)
