Synthetic technique fixtures
============================

Each `.sdkc` file stores one candidate-grid snapshot that is intended to
exercise a single solving technique. The snapshots are deliberately isolated
from the normal puzzle fixtures so direct technique tests can assert a specific
placement or elimination without depending on the full solver strategy order.

Format
------

- `technique` names the technique instance from `default_techniques()`.
- `source` and `source_step` record where the candidate topology was derived.
- `placements` and `eliminations` define the expected move signature.
- `fixed` and `given` preserve state metadata used by techniques that need it.
- `candidates` contains nine rows of nine candidate masks. Each mask is the
  digits still available in that cell, for example `27` means candidates 2 and
  7.
