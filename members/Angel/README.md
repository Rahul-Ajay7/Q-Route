# Angel: tunnelling-inspired SA

The submitted `saq_cvrptw.py` is preserved byte-for-byte. `run_tunnelling.py`
adapts its original proposal generator and acceptance formula to the shared
evaluator, initialization, deadline, temperature scaling, and reheating policy.
It does not relabel Angel's method as QUBO+SA.

Known issues remain in the preserved standalone code: the direct-trip precheck
can reject feasible traffic-dependent cases, IDs are assumed to index the matrix,
the documented normalization is unused, and the final check reuses its own evaluator.
The shared benchmark bypasses those components. Original standalone results
should not be mixed with common-evaluator results.

See [the shared protocol](../../team_benchmark/README.md).
