# Grouped AIC

## Idea

Grouped AIC generalizes Alternating Inference Chains by allowing some nodes to represent candidate groups. A grouped node can stand for several possible placements of one digit in a row, column, or box, provided the group behaves coherently in the chain.

Grouped chains are useful when a deduction depends on a pointing-style group rather than a single candidate cell.

## Why It Works

The chain still alternates strong and weak inference. A grouped node is true if the digit appears in one of its represented cells. A target candidate can be eliminated when it sees every possible placement represented by a true grouped endpoint or when the alternating chain proves the target incompatible with all branches.

## Solver Behavior

`GroupedAIC` constructs both single candidate nodes and grouped candidate nodes, links them through strong and weak relationships, then emits eliminations supported by the endpoint visibility rules.

## Implementation Notes

Grouped AIC is one of the most expensive discovery techniques in the full `human` strategy. The solver keeps it late in the order and limits both chain depth and the number of emitted moves so interactive solves do not spend most of their time enumerating equivalent grouped paths.

The implementation precomputes grouped node masks, sorts link adjacency once, and carries mutable path state during search to avoid repeated list and set construction. These optimizations are intentionally local to the search loop; the surrounding code keeps the grouped-node logic explicit because correctness is more important than squeezing every allocation out of an advanced technique.

The tradeoff is completeness: very long grouped chains or chains beyond the move cap may be skipped. That is acceptable for this solver because MRV search remains available unless `--logic-only` is requested.

## References

- [SudokuWiki: Grouped X-Cycles](https://www.sudokuwiki.org/Print_Grouped_X_Cycles)
- [SudokuWiki: Alternating Inference Chains](https://www.sudokuwiki.org/Alternating_Inference_Chains)
