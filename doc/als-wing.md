# ALS-Wing

## Idea

ALS-Wing is an ALS chain of length three. A central ALS links to one wing ALS through one restricted common candidate and to another wing ALS through a different restricted common candidate. The two wing ALS groups share an elimination digit.

This is also described by HoDoKu as ALS-XY-Wing.

## Why It Works

If the shared elimination digit is not locked in one wing ALS, the restricted common candidate forces the central ALS, which in turn forces the other wing ALS to contain the shared digit. The reverse branch works symmetrically. Therefore one of the wing ALS groups must contain the shared digit, and any cell seeing all shared-digit placements in both wings can be eliminated.

## Solver Behavior

`ALSWing` builds on the ALS-XZ helper logic and searches triples of ALS groups with two different restricted common candidates and a shared wing digit.

## References

- [HoDoKu: ALS](https://hodoku.sourceforge.net/en/tech_als.php)
