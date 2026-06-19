# Finned Jellyfish

## Idea

A Finned Jellyfish is a size-four fish with extra fin candidates in one box. It is the finned counterpart to Jellyfish and uses the same conditional logic as smaller finned fish.

## Why It Works

If the fin is false, the underlying Jellyfish reserves four cover sets for the fish digit and removes cover candidates outside the base sets. If the fin is true, it removes the fish digit from cells that see the fin. Any candidate eliminated under both alternatives is not part of any valid solution.

## Solver Behavior

`FinnedJellyfish` is implemented as the size-four specialization of the finned fish search. It is advanced and less frequently useful than Finned X-Wing or Finned Swordfish, but it is included in the `human` strategy.

## References

- [HoDoKu: Basic Fish](https://hodoku.sourceforge.net/en/tech_fishb.php)
- [HoDoKu: Solving Techniques Introduction](https://hodoku.sourceforge.net/en/tech_intro.php)
