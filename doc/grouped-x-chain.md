# Grouped X-Chain

## Idea

Grouped X-Chain extends X-Chain by allowing a node to represent a small group of candidates rather than one cell. A group is usually two or three candidates in the same unit, commonly aligned in a way similar to pointing pairs or triples.

The grouped node participates in the same single-digit strong and weak inference logic as an ordinary candidate node.

## Why It Works

If a group acts as one side of an inference, the digit must be in one of the cells of that group when the group is true. A target candidate that sees every possible placement represented by a true endpoint can be eliminated. Alternating grouped and single nodes lets the chain express deductions that ordinary X-Chains miss.

## Solver Behavior

`GroupedXChain` specializes grouped AIC logic to one digit. It builds grouped nodes from row/column/box candidate structures and applies endpoint eliminations when a target sees the necessary grouped placements.

## Implementation Notes

Grouped X-Chain is intentionally placed at the end of the full `human` strategy. It is expensive relative to its observed yield on the fixture corpus, and it is omitted from `human-fast`.

The implementation inherits the grouped-chain search limits used by grouped AIC. This keeps runtime bounded but means `--logic-only` can miss rare longer grouped X-Chain deductions. Future optimizations should prefer cheap usefulness gates before graph construction, for example checking whether grouped strong-link components can produce an endpoint-pair elimination at all.

## References

- [SudokuWiki: Grouped X-Cycles](https://www.sudokuwiki.org/Print_Grouped_X_Cycles)
- [SudokuWiki: Alternating Inference Chains](https://www.sudokuwiki.org/Alternating_Inference_Chains)
