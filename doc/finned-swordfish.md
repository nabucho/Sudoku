# Finned Swordfish

## Idea

A Finned Swordfish is a size-three fish where the base candidates almost fit three cover sets, except for one or more fin candidates in a single box. The fins block ordinary Swordfish eliminations, but restricted eliminations remain valid where a target sees the fin and lies in the relevant cover set.

## Why It Works

There are two possibilities: the fin is false and the Swordfish operates normally, or the fin is true and removes the fish digit from cells that see it. A target candidate can be eliminated only when both branches remove it. This makes Finned Swordfish weaker than a pure Swordfish but still logically sound.

## Solver Behavior

`FinnedSwordfish` searches size-three finned fish. It keeps the eliminations conservative by requiring target cells to be visible from the fin region.

## References

- [HoDoKu: Basic Fish](https://hodoku.sourceforge.net/en/tech_fishb.php)
- [HoDoKu: Solving Techniques Introduction](https://hodoku.sourceforge.net/en/tech_intro.php)
