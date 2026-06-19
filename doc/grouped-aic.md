# Grouped AIC

## Idea

Grouped AIC generalizes Alternating Inference Chains by allowing some nodes to represent candidate groups. A grouped node can stand for several possible placements of one digit in a row, column, or box, provided the group behaves coherently in the chain.

Grouped chains are useful when a deduction depends on a pointing-style group rather than a single candidate cell.

## Why It Works

The chain still alternates strong and weak inference. A grouped node is true if the digit appears in one of its represented cells. A target candidate can be eliminated when it sees every possible placement represented by a true grouped endpoint or when the alternating chain proves the target incompatible with all branches.

## Solver Behavior

`GroupedAIC` constructs both single candidate nodes and grouped candidate nodes, links them through strong and weak relationships, then emits eliminations supported by the endpoint visibility rules.

## References

- [SudokuWiki: Grouped X-Cycles](https://www.sudokuwiki.org/Print_Grouped_X_Cycles)
- [SudokuWiki: Alternating Inference Chains](https://www.sudokuwiki.org/Alternating_Inference_Chains)
