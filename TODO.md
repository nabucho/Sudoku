# TODO

## Benchmarking and Profiling

- Add `--repeat N` to `test/benchmark.py` and report median, min, and max timings so small optimizations can be judged more reliably.

## Strategy Improvements

- Add structured move diagnostics with technique name, cause cells, changed cells, candidate-count delta, solved-cell delta, and selection score. This should make `fewest-steps` decisions easier to inspect.

## Code Quality

- Continue optimizing high-cost techniques based on full-fixture benchmark data, prioritizing changes that preserve move ordering and explanations.
- Optimize `Grouped AIC` further: it is still the largest discovery cost after recent mask lookup work. Profile whether duplicate path exploration, endpoint elimination checks, or grouped node/link construction dominates, then add narrowly scoped pruning or caches.
- Optimize `Nishio`: it is costly but high-yield, so preserve ordering and behavior while reducing speculative search overhead. Prioritize caching per `(candidate state, assumed cell, digit)` and reusing consistency-validation results within a technique run.
- Add a cheap usefulness gate for `Grouped X-Chain`: current benchmark runs it 63 times with 0 uses, so skip or defer it when no grouped strong-link components can produce an endpoint-pair elimination.
- Add prefilters for `Avoidable Rectangle`: current benchmark shows one use but high average scan cost. Precompute non-given rectangles and solved-corner patterns before trying every digit pair.
- Review remaining `ALS-XZ` pair scans: it is much faster now but still a top cost. Consider indexing ALS groups by candidate mask/shared digits so pairs with no restricted-common possibility are never visited.
- Consider a low-risk `Nishio` benchmark before coding: because it is high-yield, compare optimized variants against full soundness and `--logic-only` behavior before changing strategy order.

## Public Repository Readiness

- Add repository URLs to `pyproject.toml` once the public GitHub location is known.
- Add README badges for CI status, license, and supported Python versions after the repository URL is stable.
