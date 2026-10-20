# Parikshit: adaptive hybrid

`run_hybrid.py` runs the current shared hybrid: initial construction, global SA,
cross-vehicle regret repair, adaptive QUBO refinement, temporary exclusion, and
further global SA. See [v2 details](../../docs/HYBRID_V2.md) and
[current results](../../results/comparison/hybrid_v2_validation/REPORT.md).

The original `src/qorbit` package, data loaders, experiments, scripts and 67 tests
remain here. Its older traffic-repair study uses a different model and should
not be pooled with the new team experiments. Its historical generated outputs,
old patch scripts and logs are in [the archive](../../results/archive/member-artifacts.zip).
`run_experiments.sh` can regenerate original package outputs in a new `results/`
folder when its Python environment is configured.

The root `pytest.ini` includes this package's source path and test suite. Use
`venv\Scripts\python.exe -B -m pytest -q` from the project root to run all tests.
