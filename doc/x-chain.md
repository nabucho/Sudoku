# X-Chain

## Idea

An X-Chain is an Alternating Inference Chain restricted to one digit. It connects candidate positions for that digit using strong and weak links across rows, columns, and boxes.

Because all nodes represent the same digit, X-Chains are easier to reason about than general AICs.

## Why It Works

The chain alternates strong and weak links. If the chain endpoints form a strong-ended relationship, at least one endpoint must contain the digit. Any candidate for that digit that sees both endpoints is impossible.

Closed or near-closed forms are often called X-Cycles in SudokuWiki terminology.

## Solver Behavior

`XChain` specializes the AIC search to one digit at a time, looking for endpoint eliminations on shared peers.

## Implementation Notes

X-Chain shares the bounded-chain philosophy used by AIC. The limit favors common explanatory chains and predictable timing over exhaustive enumeration of every possible longer chain.

Because this is a single-digit technique, it remains cheaper than general AIC and grouped chains, but it should still be benchmarked when changing link construction, endpoint checks, or chain depth.

## References

- [SudokuWiki: Alternating Inference Chains](https://www.sudokuwiki.org/Alternating_Inference_Chains)
- [Sudopedia: Techniques](https://sudopedia.org/wiki/Techniques)
