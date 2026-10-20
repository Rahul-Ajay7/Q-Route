# Shared benchmark

This is the implemented comparison pipeline. Member entry points call the same
model, constraints and timed runner. All current methods receive the same
initial routes per case/seed and the same bounded complete-route cache.

Start with [experiment commands](../docs/experiments.md),
[the model](../docs/methodology.md), or [current hybrid results](../docs/HYBRID_V2.md).

```powershell
# Fresh paired comparison
venv\Scripts\python.exe -B -m team_benchmark.run --cases TC11.json --seeds 20 21 22 --seconds 1 --output results/comparison/my_run

# Current hybrid with the optional SB local sampler
venv\Scripts\python.exe -B members/Parikshit/run_hybrid.py members/Rahul/test_cases/TC11.json --seconds 1 --hybrid-backend sb

# All tests
venv\Scripts\python.exe -B -m pytest -q

# Verify exact recorded sources and independently resimulate saved routes
venv\Scripts\python.exe -B -m team_benchmark.verify_results results/comparison/hybrid_v2_validation
```

Use `--help` for all search settings. `--methods` selects main methods and
ablations; `--ablations` adds every reference. `--soft-windows` changes the
optimization problem and must be analyzed separately. The default local hybrid
backend is classical binary SA; `--hybrid-backend sb` selects ballistic SB for
v2 variants. V1 reference variants retain their original binary SA backend.

The runner writes `runs.json`, a manifest with source/input hashes,
`sources.zip`, paired statistics and a report. `python -m team_benchmark.plot`
exports CSV/PNG/SVG after a run. Existing recorded-run folders cannot be
overwritten. Construction failures have no finite score. Full scans include
invalid TC14 and exit 1 after logging that input error and finishing valid cases.

The fixed monetary assumptions use synthetic km, input minutes, model-estimated
fuel and INR costs. Traffic is known offline and evaluated at departure; temporary
closures can be waited out. No live dispatch, executed-prefix freezing, road
detour search or breakdown rescue is implemented. QUBO coefficients approximate
time/load propagation; full dynamic evaluation decides acceptance.

Tiny exact enumeration, assignment-energy tests and independent route audits
check mathematical/feasibility properties. They do not establish general
optimality. Paired case-level statistics, recorded failures and ablations support
scoped empirical claims; a competitive no-QUBO version prevents attributing
improvement to QUBO. [Historical evidence](../results/archive/README.md) is retained
separately from current v2 outputs.
