# Turbot Fish

## Idea

Turbot Fish is a family of short single-digit chains built from strong links and weak links. Skyscraper and Two-String Kite are common named shapes in this family.

The pattern proves that at least one of two endpoint candidates must be true. A candidate that sees both endpoints can therefore be removed.

## Why It Works

The chain alternates between strong and weak relationships on the same digit. Strong links say at least one endpoint must be true; weak links say two visible candidates cannot both be true. Following the alternation from one endpoint to the other creates a forced alternative pair.

If a target cell sees both endpoints, either branch of the alternative removes the target candidate.

## Solver Behavior

`TurbotFish` searches short single-digit strong-link chains and uses shared peer elimination at the endpoints. More general single-digit chains are handled later by `XChain` and `GroupedXChain`.

## References

- [Sudopedia: Turbot Fish](https://sudopedia.sudocue.net/index.php?title=Turbot_Fish)
- [Sudopedia: Techniques](https://sudopedia.org/wiki/Techniques)
