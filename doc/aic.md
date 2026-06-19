# AIC

## Idea

An Alternating Inference Chain connects candidates with alternating strong and weak links. Links can be inside a bivalue cell, across a unit where a digit has two positions, or through other logical relationships.

A strong link means at least one endpoint must be true. A weak link means both endpoints cannot be true. Alternating these links creates implications that can prove eliminations or placements.

## Why It Works

In a chain that starts and ends with strong inference, at least one endpoint must be true. If both endpoints are the same digit in cells that share peers, any candidate seeing both endpoints can be removed. In loop forms, contradictions or off-chain eliminations arise from the same alternating strong/weak structure.

AICs generalize many named patterns, including X-Chains, XY-Chains, and some Empty Rectangle or grouped-chain deductions.

## Solver Behavior

`AIC` builds candidate-node links from bivalue cells and bilocation units, searches alternating chains, and emits eliminations proved by compatible endpoints.

## References

- [SudokuWiki: Alternating Inference Chains](https://www.sudokuwiki.org/Alternating_Inference_Chains)
- [Sudopedia: Techniques](https://sudopedia.org/wiki/Techniques)
