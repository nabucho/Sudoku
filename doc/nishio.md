# Nishio

## Idea

Nishio tests one candidate by assuming it is true and following the consequences. If that assumption leads to contradiction, the candidate can be eliminated.

SudokuWiki frames Nishio as part of the forcing-chain family: it is not random guessing, because only the contradiction branch is used as a logical proof.

## Why It Works

A valid candidate cannot force an impossible grid. If setting a candidate causes an empty cell, duplicate solved digit in a unit, or another consistency failure after logical propagation, the assumption is false. Therefore the original candidate is not part of any solution and may be removed.

Nishio is less pattern-shaped than techniques such as XY-Wing or X-Wing, but it is still a valid contradiction proof when the consequence chain is sound.

## Solver Behavior

`Nishio` tries candidate assumptions in a cloned state and applies logical consequences. When an assumption produces contradiction, the solver emits an elimination for the tested candidate.

## References

- [SudokuWiki: Nishio Forcing Chains](https://www.sudokuwiki.org/Nishio_Forcing_Chains)
