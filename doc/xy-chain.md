# XY-Chain

## Idea

An XY-Chain is a chain through bivalue cells. Each step moves from one candidate in a bivalue cell to the other candidate in the same cell, then through a peer relationship to the same candidate in another bivalue cell.

The chain starts and ends on the same digit. Targets that see both endpoints can have that digit removed.

## Why It Works

Inside a bivalue cell, if one candidate is false, the other must be true. Between peer cells, the same digit cannot be true in both. Alternating these strong and weak implications creates a chain where one endpoint or the other must contain the shared digit.

Any target seeing both endpoints is eliminated regardless of which endpoint is true.

## Solver Behavior

`XYChain` builds alternating relationships between bivalue cells and searches for endpoint pairs with the same digit. It then removes that digit from common peers of the endpoints.

## References

- [HoDoKu: Wings](https://hodoku.sourceforge.net/en/tech_wings.php)
- [Sudopedia: Techniques](https://sudopedia.org/wiki/Techniques)
