# W-Wing

## Idea

A W-Wing uses two bivalue cells with the same pair of candidates, plus a strong link on one of those candidates. Each end of the strong link sees one of the bivalue cells.

The candidate not used by the strong link is eliminated from cells that see both bivalue cells.

## Why It Works

Suppose the two bivalue cells both contain `W` and `X`, and the strong link is on `X`. One endpoint of the strong link must be `X`. If the first endpoint is `X`, the bivalue cell it sees cannot be `X` and must be `W`. If the second endpoint is `X`, the other bivalue cell must be `W`. Either way, at least one bivalue endpoint is `W`, so any cell seeing both cannot be `W`.

## Solver Behavior

`WWing` searches matching bivalue cells and compatible strong links, then removes the non-link digit from shared peers of the two bivalue endpoints.

## References

- [HoDoKu: Wings](https://hodoku.sourceforge.net/en/tech_wings.php)
- [Sudopedia: Techniques](https://sudopedia.org/wiki/Techniques)
