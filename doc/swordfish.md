# Swordfish

## Idea

Swordfish is a size-three basic fish. For one digit, three rows can have all candidates confined to the same three columns, or three columns can have all candidates confined to the same three rows.

Not every intersection has to contain the fish digit. The essential condition is that each base set has at least one candidate and all base candidates are covered by the same three cover sets.

## Why It Works

The three base rows each need one placement of the fish digit. Since all legal placements in those rows lie in three cover columns, those columns must receive the digit from the base rows. Any extra candidate in the cover columns outside the base rows would make it impossible for the fish placements to satisfy the row and column constraints together.

## Solver Behavior

The solver implements Swordfish through `Fish(3)`. It searches both row-base and column-base forms and groups all resulting cover-set eliminations into a single step.

## References

- [HoDoKu: Basic Fish](https://hodoku.sourceforge.net/en/tech_fishb.php)
