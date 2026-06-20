# TODO

## Benchmarking and Profiling

- Add `--repeat N` to `test/benchmark.py` and report median, min, and max timings so small optimizations can be judged more reliably.

## Strategy Improvements

- Add structured move diagnostics with technique name, cause cells, changed cells, candidate-count delta, solved-cell delta, and selection score. This should make `fewest-steps` decisions easier to inspect.

## Code Quality

- Continue optimizing high-cost techniques based on full-fixture benchmark data, prioritizing changes that preserve move ordering and explanations.

## Project Tooling

- Add CI configuration for lint, type checking, tests, and benchmark smoke checks.
- Improve packaging metadata so the solver can be installed and imported cleanly in more environments.
