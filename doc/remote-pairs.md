# Remote Pairs

## Idea

Remote Pairs are a specialized XY-Chain where every cell in the chain has the same two candidates. The candidates alternate along a chain of bivalue cells.

Because the same pair repeats, the chain can be viewed as two-coloring a pair of digits rather than a single digit.

## Why It Works

Adjacent bivalue cells in the chain see each other, so they cannot contain the same digit from the pair. This forces alternating values along the chain. If two chain endpoints have the same parity, at least one of them must take each candidate in the pair depending on the branch. Cells that see both endpoints cannot contain candidates contradicted by the endpoint alternatives.

## Solver Behavior

`RemotePairs` searches connected chains of bivalue cells with identical candidate pairs and removes candidates from cells that see both endpoints when the alternating parity proves the removal.

## References

- [Sudopedia: Techniques](https://sudopedia.org/wiki/Techniques)
