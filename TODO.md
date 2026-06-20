# TODO

## Benchmarking and Profiling

- Add `--repeat N` to `test/benchmark.py` and report median, min, and max timings so small optimizations can be judged more reliably.
- Use benchmark output to tune strategy ordering, especially for expensive low-yield techniques such as Avoidable Rectangle, Grouped X-Chain, and large fish variants.
- Keep separate benchmark views for technique discovery, move scoring, applying moves, and overhead.

## Strategy Improvements

- Add structured move diagnostics with technique name, cause cells, changed cells, candidate-count delta, solved-cell delta, and selection score. This should make `fewest-steps` decisions easier to inspect.

## Code Quality

- Continue optimizing high-cost techniques based on full-fixture benchmark data, prioritizing changes that preserve move ordering and explanations.

## Project Tooling

- Add CI configuration for lint, type checking, tests, and benchmark smoke checks.
- Improve packaging metadata so the solver can be installed and imported cleanly in more environments.
