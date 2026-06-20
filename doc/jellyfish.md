# Jellyfish

## Idea

Jellyfish is a size-four basic fish. For one digit, four rows have all candidates confined to four columns, or four columns have all candidates confined to four rows.

Jellyfish is less common than X-Wing and Swordfish, but it follows the same base-set and cover-set model.

## Why It Works

The four base sets must contain four placements of the fish digit. If every possible placement in the base sets lies within four cover sets, those cover sets are reserved for the fish placements. Any matching candidate in a cover set but outside the base sets would conflict with at least one required placement and can be removed.

## Solver Behavior

The solver implements Jellyfish through `Fish(4)`. Larger basic fish are not included because they are unnecessary in standard 9x9 Sudoku: a larger fish has a complementary smaller fish.

## Implementation Notes

Fish techniques use row and column bitmasks for candidate positions. The implementation filters candidate masks by precomputed bit counts and translates masks to row or column indexes through lookup tables, avoiding repeated set construction in the common no-fish path.

Jellyfish is included in the full `human` strategy for completeness but is omitted from `human-fast` because it is rare and later search is usually cheaper than scanning large fish patterns on every step.

## References

- [HoDoKu: Basic Fish](https://hodoku.sourceforge.net/en/tech_fishb.php)
