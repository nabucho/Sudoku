# X-Wing

## Idea

An X-Wing is a size-two basic fish. For one digit, two base rows can have all of their candidates confined to the same two columns, or two base columns can have all candidates confined to the same two rows.

The four base-cover intersections form the corners of a rectangle. The digit must occupy opposite corners, though the exact diagonal is not known yet.

## Why It Works

If the base sets are rows, each row must place the digit in one of the two cover columns. Because both rows use the same two columns, the digit must occupy those columns inside the base rows. Any other candidate for that digit in the cover columns would conflict with one of the forced placements, so it can be eliminated.

The same reasoning works with rows and columns exchanged.

## Solver Behavior

The solver implements X-Wing through `Fish(2)`. It considers row-based and column-based fish and emits all eliminations from the cover sets as one move.

## References

- [HoDoKu: Basic Fish](https://hodoku.sourceforge.net/en/tech_fishb.php)
