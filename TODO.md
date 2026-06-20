# TODO

## Benchmarking and Profiling

- Add `--repeat N` to `test/benchmark.py` and report median, min, and max timings so small optimizations can be judged more reliably.

## Strategy Improvements

- Add structured move diagnostics with technique name, cause cells, changed cells, candidate-count delta, solved-cell delta, and selection score. This should make `fewest-steps` decisions easier to inspect.

## Code Quality

- Continue optimizing high-cost techniques based on full-fixture benchmark data, prioritizing changes that preserve move ordering and explanations.
- Optimize `Nishio`: it is costly but high-yield, so preserve ordering and behavior while reducing speculative search overhead and repeated candidate-state validation.
- Add prefilters for `Grouped X-Chain`, `Avoidable Rectangle`, and large fish variants so zero- or low-yield scans can be skipped when candidate distribution cannot support the pattern.
- Review unique rectangle type ordering and prechecks: Type 4 currently yields moves while Type 2/3 are often scanned without success.

## Project Tooling

- Add CI configuration for lint, type checking, tests, and benchmark smoke checks.
- Improve packaging metadata so the solver can be installed and imported cleanly in more environments.
