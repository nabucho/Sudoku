# TODO

## Highest Priority

- Add a technique soundness oracle over all puzzle fixtures. For every emitted move, compare placements and eliminations against a trusted solved grid and fail if a move places the wrong digit or removes the true digit.
- Add per-technique validity tests from real solve paths. Log moves produced during fixture solves, replay them against solved grids, and keep regressions for any unsound logical move.

## Benchmarking and Profiling

- Add `--repeat N` to `test/benchmark.py` and report median, min, and max timings so small optimizations can be judged more reliably.
- Use benchmark output to tune strategy ordering, especially for expensive low-yield techniques such as Avoidable Rectangle, Grouped X-Chain, and large fish variants.
- Keep separate benchmark views for technique discovery, move scoring, applying moves, and overhead.

## Strategy Improvements

- Split full human-style completeness from faster practical solving. Keep `human` as the complete explanatory strategy, and consider adding a `human-fast` or `advanced-fast` strategy that skips very expensive low-yield techniques before search.
- Add structured move diagnostics with technique name, cause cells, changed cells, candidate-count delta, solved-cell delta, and selection score. This should make `fewest-steps` decisions easier to inspect.

## Code Quality

- Continue optimizing high-cost techniques based on full-fixture benchmark data, prioritizing changes that preserve move ordering and explanations.

## Project Tooling

- Consider migrating the custom test runner to `pytest` while preserving the current fixture coverage.
- Add CI configuration for lint, type checking, tests, and benchmark smoke checks.
- Improve packaging metadata so the solver can be installed and imported cleanly in more environments.
