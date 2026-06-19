# Simple Coloring

## Idea

Simple Coloring is a single-digit chain technique. For one digit, the solver finds conjugate pairs: units where the digit has exactly two possible cells. Those strong links are colored alternately, creating a two-color cluster.

The colors represent parity. In each strong link, exactly one endpoint is true, so connected endpoints must alternate truth values.

## Why It Works

Two common deductions come from a single cluster:

- Color wrap: if two candidates of the same color see each other, that color cannot be true anywhere in the cluster.
- Color trap: if an uncolored candidate sees both colors, one of those colored candidates must be true, so the uncolored candidate can be eliminated.

Both deductions rely on the fact that a conjugate-link cluster has only two possible parity states.

## Solver Behavior

`SimpleColoring` builds strong-link graphs per digit, colors each connected component, and emits eliminations from same-color contradictions or cells that see both colors.

## References

- [Sudopedia: Coloring](https://sudopedia.sudocue.net/index.php?title=Coloring)
- [Sudopedia: Techniques](https://sudopedia.org/wiki/Techniques)
