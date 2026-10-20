# Experiments

Run commands from the project root with the existing environment.

```powershell
# All current and member tests; no placeholder tests
venv\Scripts\python.exe -B -m pytest -q

# Compare methods on one input, with paired search seeds
venv\Scripts\python.exe -B -m team_benchmark.run --cases TC11.json --seeds 20 21 22 --seconds 1 --methods classical_sa tunnelling_sa qubo_sb hybrid hybrid_v1_cached hybrid_no_qubo --output results/comparison/my_run

# Optional quantum-inspired SB backend inside the current hybrid
venv\Scripts\python.exe -B members/Parikshit/run_hybrid.py members/Rahul/test_cases/TC11.json --seconds 1 --hybrid-backend sb

# Verify current saved results (including original compressed source snapshots)
venv\Scripts\python.exe -B -m team_benchmark.verify_results results/comparison/hybrid_v2_validation
venv\Scripts\python.exe -B -m team_benchmark.verify_results results/comparison/hybrid_v2_budget_check

# Regenerate CSV, PNG and SVG from the recorded JSON
venv\Scripts\python.exe -B -m team_benchmark.plot results/comparison/hybrid_v2_validation

# Convert supplied Solomon text inputs; no download
venv\Scripts\python.exe -B -m team_benchmark.prepare_solomon

# Browse recorded comparisons and route plans
venv\Scripts\python.exe -B -m streamlit run dashboard/app.py
```

Output folders with `runs.json` are protected against overwriting. Use a new
folder for every scientific run. Optimization is offline and sequential; avoid
other heavy jobs during timing. Deadlines are checked between atomic actions,
and actual overruns are recorded. Fixed action counts are for debugging and do
not mean equal computational work.

Current evidence:

- [0.5-second validation](../results/comparison/hybrid_v2_validation/REPORT.md),
  [protocol](../results/comparison/hybrid_v2_validation/protocol.json),
  [CSV](../results/comparison/hybrid_v2_validation/runs.csv).
- [1-second check](../results/comparison/hybrid_v2_budget_check/REPORT.md),
  [protocol](../results/comparison/hybrid_v2_budget_check/protocol.json).
- [Archived evidence and restoration](../results/archive/README.md).

All methods share costs, constraints, initial routes and per-case/seed budgets.
Average paired seed results within cases before comparing cases; preserve
failures, ties and losses. Related supplied fixtures are not independent
real-world holdout data. Hard/soft windows and different budgets are separate
experiments. Do not attribute gains to QUBO when its ablation is competitive.

The supplied `TC14.json` is a CSV index despite its extension. An all-case run
logs it as invalid, continues the valid files and returns exit code 1. TC15,
TC16 and TC25 failed the shared construction in the saved experiments; their
partial routes have no finite quality score.
