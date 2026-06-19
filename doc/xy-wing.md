# XY-Wing

## Idea

An XY-Wing uses three bivalue cells. The pivot contains candidates `X` and `Y`. One pincer sees the pivot and contains `X` and `Z`; the other pincer sees the pivot and contains `Y` and `Z`.

The pincers do not need to see each other. The elimination target must see both pincers.

## Why It Works

If the pivot is `X`, the `XZ` pincer cannot be `X`, so it must be `Z`. If the pivot is `Y`, the `YZ` pincer cannot be `Y`, so it must be `Z`. In every case, at least one pincer is `Z`. Any cell that sees both pincers cannot contain `Z`.

This is equivalent to a short XY-Chain, but the three-cell pattern is easier to spot.

## Solver Behavior

`XYWing` searches bivalue pivots and compatible bivalue pincers, then removes the shared pincer digit from common peers of the pincers.

## References

- [HoDoKu: Wings](https://hodoku.sourceforge.net/en/tech_wings.php)
