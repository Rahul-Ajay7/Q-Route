# Four-approach complete test run

Methods: Alphonsa / classical SA; Angel / tunnelling SA; Rahul / QUBO+SB; Parikshit / hybrid v2.

Five seeds (20–24), hard windows, one second per optimization, identical initialization per case/seed. Hybrid local QUBO backend: classical binary SA. Traffic and costs are synthetic/offline.

## Cumulative result

Cumulative cost sums seed-averaged costs across jointly feasible cases. It is a descriptive basket, not the cost of one fleet. Large/expensive cases dominate it. Dataset-specific paired relative results below give every case equal weight.

| Method | Feasible / attempted | Cumulative case-mean cost (INR) | Mean improvement from initial | Mean feasible runtime (s) |
|---|---:|---:|---:|---:|
| classical_sa | 150 / 170 | 444502.59 | 10.34% | 1.0000 |
| tunnelling_sa | 150 / 170 | 436543.37 | 10.82% | 1.0000 |
| qubo_sb | 150 / 170 | 499156.33 | 2.14% | 1.0006 |
| hybrid | 150 / 170 | 431735.22 | 11.58% | 1.0001 |

## solomon_cases

100 feasible results independently audited; source and input hashes verified.

| Method | Feasible / attempted | Cumulative case-mean cost (INR) |
|---|---:|---:|
| classical_sa | 25 / 30 | 264903.85 |
| tunnelling_sa | 25 / 30 | 257222.90 |
| qubo_sb | 25 / 30 | 302169.57 |
| hybrid | 25 / 30 | 254264.75 |

Positive paired reductions favour the hybrid. Intervals: case-bootstrap 95%; tests: two-sided Wilcoxon with Holm correction within this dataset.

| Against | Cases / paired seeds | Hybrid cost reduction | 95% interval | Case wins / ties / losses | Holm p |
|---|---:|---:|---:|---:|---:|
| classical_sa | 5 / 25 | 3.18% | 0.01% to 6.59% | 4 / 0 / 1 | 0.625 |
| qubo_sb | 5 / 25 | 13.84% | 7.26% to 20.43% | 5 / 0 / 0 | 0.1875 |
| tunnelling_sa | 5 / 25 | 0.52% | -1.96% to 3.08% | 3 / 0 / 2 | 0.8125 |

Construction failures: R101_traffic.json.
Invalid inputs: none.
Detailed outputs: [solomon_cases/REPORT.md](solomon_cases/REPORT.md), [solomon_cases/runs.csv](solomon_cases/runs.csv), [solomon_cases/audit.json](solomon_cases/audit.json).

## supplied_cases

500 feasible results independently audited; source and input hashes verified.

| Method | Feasible / attempted | Cumulative case-mean cost (INR) |
|---|---:|---:|
| classical_sa | 125 / 140 | 179598.73 |
| tunnelling_sa | 125 / 140 | 179320.47 |
| qubo_sb | 125 / 140 | 196986.76 |
| hybrid | 125 / 140 | 177470.47 |

Positive paired reductions favour the hybrid. Intervals: case-bootstrap 95%; tests: two-sided Wilcoxon with Holm correction within this dataset.

| Against | Cases / paired seeds | Hybrid cost reduction | 95% interval | Case wins / ties / losses | Holm p |
|---|---:|---:|---:|---:|---:|
| classical_sa | 25 / 125 | 1.02% | 0.34% to 1.95% | 12 / 10 / 3 | 0.006286 |
| qubo_sb | 25 / 125 | 8.79% | 6.47% to 11.10% | 22 / 3 / 0 | 0.0001203 |
| tunnelling_sa | 25 / 125 | 0.90% | 0.21% to 1.89% | 12 / 8 / 5 | 0.01477 |

Construction failures: TC15.json, TC16.json, TC25.json.
Invalid inputs: TC14.json: Expecting value: line 1 column 1 (char 0).
Detailed outputs: [supplied_cases/REPORT.md](supplied_cases/REPORT.md), [supplied_cases/runs.csv](supplied_cases/runs.csv), [supplied_cases/audit.json](supplied_cases/audit.json).

## Interpretation and files

All observations are retained, including failures, ties and losses. Construction failure is not an infeasibility proof. No no-QUBO ablation is included in this four-method run, so it cannot establish a QUBO-specific gain. Related Solomon variants are not independent base instances; supplied fixtures were used previously. These are new executions, not independent real-world holdout evidence. Do not pool dataset-level significance tests or infer quantum advantage.

- `aggregate_results.csv` / `.json`: method totals and dataset summaries.
- `case_results.csv`: per-case, per-method seed means and best costs.
- `protocol.json`: declared scope, settings and reproduction commands.
- Each dataset folder: raw routes, CSV, report, plots, audit, manifest and source snapshot.

Rebuild this summary with `venv\Scripts\python.exe -B -m team_benchmark.summarize results/comparison/four_approaches_20261021`.
