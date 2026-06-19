# XYZ-Wing

## Idea

XYZ-Wing is a close relative of XY-Wing. The pivot contains three candidates `X`, `Y`, and `Z`. One pincer contains `X` and `Z`; the other contains `Y` and `Z`. Both pincers see the pivot.

Because the pivot can itself be `Z`, eliminations are limited to cells that see the pivot and both pincers.

## Why It Works

If the pivot is `Z`, every target seeing the pivot cannot be `Z`. If the pivot is `X`, the `XZ` pincer becomes `Z`. If the pivot is `Y`, the `YZ` pincer becomes `Z`. Therefore one of the pivot or pincers is always `Z`, and any cell seeing all relevant cells cannot contain `Z`.

## Solver Behavior

`XYZWing` scans trivalue pivots and bivalue pincers. It eliminates the shared candidate from common peers that see the pivot and both pincers.

## References

- [HoDoKu: Wings](https://hodoku.sourceforge.net/en/tech_wings.php)
