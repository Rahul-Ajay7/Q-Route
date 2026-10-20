# Q-ORBIT

Traffic-aware capacitated vehicle routing with time windows. The current hybrid
combines global simulated annealing, cross-vehicle repair, and adaptive QUBO refinement.

## Start here

- [Remaining tasks and review checklist](docs/TODO.md).
- [Complete project details and upgrade history](docs/PROJECT_MASTER_RECORD.md).
- [Latest all-case four-approach run and cumulative results](results/comparison/four_approaches_20261021/SUMMARY.md).
- [All case graphs and cumulative graph PDF](results/comparison/four_approaches_20261021/plots/README.md).
- [Detailed four-approach PDF](docs/FOUR_APPROACHES.pdf) ([editable source](docs/FOUR_APPROACHES.md)).
- [Current results and hybrid implementation](docs/HYBRID_V2.md).
- [Current comparison CSV](results/comparison/hybrid_v2_validation/runs.csv).
- [Member projects](members/README.md).
- [Project map](docs/PROJECT_LAYOUT.md).
- [Model and assumptions](docs/methodology.md).

## Run from the project root

```powershell
# Existing local environment
venv\Scripts\python.exe -B members/Parikshit/run_hybrid.py members/Rahul/test_cases/TC11.json --seconds 1

# New comparison: use a fresh output name
venv\Scripts\python.exe -B -m team_benchmark.run --seeds 10 11 12 --seconds 1 --output results/comparison/my_run

# View recorded comparisons, costs and route plans
venv\Scripts\python.exe -B -m streamlit run dashboard/app.py

# All substantive tests, including the member suites and dashboard
venv\Scripts\python.exe -B -m pytest -q

# Audit the retained validation evidence
venv\Scripts\python.exe -B -m team_benchmark.verify_results results/comparison/hybrid_v2_validation
```

For a new environment, install `requirements.txt`; use `requirements-dev.txt`
for tests. The existing `venv` is kept in place. The dashboard reads saved data;
it does not run optimizations or call traffic services.

## Layout

| Folder | Contents |
|---|---|
| `members/` | Alphonsa, Angel, Rahul, and Parikshit implementations and original inputs |
| `team_benchmark/` | Shared model, solvers, runner, plots and audits |
| `tests/` | Shared algorithm and application tests; member tests remain with their code |
| `results/comparison/` | Frozen v2 evaluations and complete four-method TC/Solomon rerun |
| `results/archive/` | Verified compressed historical/development/member evidence |
| `data/comparison/` | Converted Solomon comparison inputs |
| `dashboard/` | Working recorded-results viewer |
| `src/` | Working original routing, cost, data and traffic utilities |
| `docs/` | Architecture, algorithms, methodology, experiments and findings |

On the supplied validation cases the revised hybrid improved mean cost over the
three primary baselines. The no-QUBO variant remained competitive; these results
do not demonstrate a quantum advantage or universal superiority.

The latest complete rerun scanned 29 supplied TC files and six Solomon variants
with four methods, five seeds and a one-second budget: 600 independently audited
feasible results, 80 construction failures and one separately invalid input.
The [development record](docs/PROJECT_MASTER_RECORD.md#latest-development-status)
tracks the results, graphs, publication commits and remaining research work.

Angel's original source and the original numerical experiment data are preserved.
Obsolete outputs are compressed rather than presented as current results. See
[cleanup details](docs/CLEANUP.md) and [archive instructions](results/archive/README.md).
The supplied `TC14.json` is actually a CSV index: full-suite runs record it as
invalid and exit 1 after processing the valid cases.

See [LICENSE](LICENSE).
