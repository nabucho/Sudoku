# Skyscraper

## Idea

A Skyscraper is a single-digit pattern built from two parallel strong links, usually in two rows or two columns. The links are weakly connected at one end, and the other ends become the elimination sources.

It is often described as a named Turbot Fish pattern and can also be represented as an X-Chain.

## Why It Works

Each strong link must contain the digit at one endpoint. If the connected base endpoints cannot both be true, at least one of the two far endpoints must be true. Any candidate that sees both far endpoints cannot be the digit.

The geometry makes the logic easier to spot than a generic chain: two "towers" connected at the base leave the tops as a forced alternative pair.

## Solver Behavior

`Skyscraper` searches for two strong links on the same digit with compatible row/column geometry and removes the digit from shared peers of the far endpoints.

## References

- [Sudopedia: Techniques](https://sudopedia.org/wiki/Techniques)
- [Sudopedia: Turbot Fish](https://sudopedia.sudocue.net/index.php?title=Turbot_Fish)
