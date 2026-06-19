# Multi-Coloring

## Idea

Multi-Coloring extends Simple Coloring by considering multiple two-color clusters for the same digit. Each cluster still represents alternating truth values, but weak links between clusters can create deductions that are not visible inside one cluster.

Sudopedia also describes this style as Color Wing logic: two clusters can be bridged by candidates that see each other, making particular colors mutually exclusive.

## Why It Works

If one color in cluster A sees one color in cluster B, those two colors cannot both be true. That relationship can force the opposite colors to cover shared targets. Any candidate that sees the forced alternatives can be eliminated.

Multi-Coloring is closely related in power to X-Chains because both use alternating single-digit strong and weak relationships.

## Solver Behavior

`MultiColoring` colors multiple conjugate-link components for a digit and searches bridge relationships between components. It emits grouped eliminations when a candidate is ruled out by the connected color logic.

## References

- [Sudopedia: Multi-Colors](https://sudopedia.sudocue.net/index.php?title=Multi-Colors)
- [Sudopedia: Coloring](https://sudopedia.sudocue.net/index.php?title=Coloring)
