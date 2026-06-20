# ALS-XZ

## Idea

ALS-XZ uses two Almost Locked Sets. An Almost Locked Set is `N` unsolved cells in one unit with `N+1` candidates. It is one candidate away from becoming a locked set.

The two ALS groups must share a Restricted Common Candidate, usually called `X`: every instance of `X` in one ALS sees every instance of `X` in the other. If both ALS groups also contain another common digit `Z`, then `Z` can be eliminated from cells that see all possible `Z` placements in both ALS groups.

## Why It Works

Because `X` is restricted common, it cannot be true in both ALS groups. At least one ALS must therefore lose `X` and become a locked set. Since both ALS groups contain `Z`, one of them must lock `Z` into its cells. Any outside cell that sees every possible `Z` in both ALS groups cannot contain `Z`.

## Solver Behavior

`ALSXZ` enumerates ALS groups, finds restricted common candidates, then removes common non-RCC digits from shared peers that see all relevant ALS placements.

## Implementation Notes

ALS-XZ can become expensive because it starts with ALS enumeration and then considers pairs of ALS groups. The solver keeps this technique in the full `human` strategy but omits it from `human-fast`.

The implementation uses compact candidate masks, shared peer checks, and precomputed mask-to-digits lookups to reduce repeated conversion work. It also skips ALS pairs with no useful shared digits before doing restricted-common checks. These optimizations preserve the visible move order and explanation text while cutting the common no-pattern path.

Future work should prefer indexing ALS groups by candidate masks or shared digits so impossible pairs are never visited, rather than making the elimination proof harder to read.

## References

- [HoDoKu: ALS](https://hodoku.sourceforge.net/en/tech_als.php)
- [Sudopedia: ALS-XZ](https://sudopedia.org/wiki/ALS-XZ)
