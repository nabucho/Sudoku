# Unique Rectangle Type 2

## Idea

Unique Rectangle Type 2 occurs when two non-diagonal corners of a possible rectangle have the same extra candidate. To avoid the deadly rectangle, at least one of those extra candidates must be true.

## Why It Works

If neither extra candidate were true, the rectangle would collapse to the two rectangle digits in all four corners, creating a non-unique solution pattern. Since at least one extra candidate must be placed, any cell that sees both extra-candidate corners cannot contain that extra digit.

## Solver Behavior

`UniqueRectangleType2` searches non-diagonal extra-candidate corners and removes the shared extra digit from common peers of those corners.

## References

- [HoDoKu: Uniqueness](https://hodoku.sourceforge.net/en/tech_ur.php)
