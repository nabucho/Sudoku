# Two-String Kite

## Idea

A Two-String Kite is a single-digit pattern using one strong link in a row and one strong link in a column. One endpoint from each link shares a box, creating a weak connection; the other endpoints form the elimination sources.

Like Skyscraper, it is a named form of Turbot Fish and can be expressed as an X-Chain.

## Why It Works

The row strong link requires the digit in one of its endpoints. The column strong link requires the same digit in one of its endpoints. Because the linked endpoints in the box cannot both be true, at least one of the two outside endpoints must be true. Any cell that sees both outside endpoints cannot contain the digit.

## Solver Behavior

`TwoStringKite` searches one row strong link and one column strong link per digit. When their inner endpoints share a box, the solver eliminates the digit from shared peers of the outer endpoints.

## References

- [Sudopedia: Techniques](https://sudopedia.org/wiki/Techniques)
- [Sudopedia: Turbot Fish](https://sudopedia.sudocue.net/index.php?title=Turbot_Fish)
