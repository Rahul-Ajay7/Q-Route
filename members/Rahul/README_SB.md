# Rahul: QUBO + simulated bifurcation

`run_sb.py` is the preserved original route-window QUBO benchmark and contains
the SB and binary SA backends used by the team comparison. `test_cases/` retains
the original supplied JSON inputs, traffic files and indexes. `test_sb.py` checks
energies, decoding and routing constraints.

From the project root:

```powershell
# Common-evaluator comparison entry point
venv\Scripts\python.exe -B members/Rahul/run_comparison.py members/Rahul/test_cases/TC11.json --seconds 1

# Original standalone benchmark, without writing outputs
venv\Scripts\python.exe -B members/Rahul/run_sb.py --case TC11 --no-write
```

The standalone script's original objective and fixed assignments differ from
the shared team benchmark. Do not mix its historical scores with current ones.
It recreates its `results/` directory when writing new outputs. The optional
`visualize_results.py` reads those generated results after a standalone run.

Older generated results, plots, reports and the obsolete comparison migration
script are preserved in [the member artifacts archive](../../results/archive/member-artifacts.zip).
The source backend itself is unchanged. See [the shared protocol](../../team_benchmark/README.md).
