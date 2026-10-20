# Archived adaptive-removal pilot

Archived on 21 October 2026 at the user's request. **Hybrid v2 remains the
active implementation.** The experimental solver, runner, eight tests and
complete pilot evidence are in
[`adaptive-removal-pilot-20261021.zip`](../../results/archive/adaptive-removal-pilot-20261021.zip).
All 16 archived files were verified byte-for-byte before the loose originals
were removed. Archive and per-file hashes are retained.

The experiment added four customer-removal strategies with learned weights:
the existing selector, worst detours, geographic neighbours and tight windows.
It retained v2's reinsertion, SA, QUBO, constraints, caching and runtime limits.
Production `team_benchmark/hybrid.py` and its dispatcher were never modified.

The pilot compared v2, adaptive selection, uniform selection and matched
no-QUBO controls on TC06, TC18 and TC20, ten seeds (30–39), at one second per
method. All 150 solutions passed independent audits. The test suite passed
142 tests while the eight experimental tests were present; archiving removes
those eight from active collection, restoring the 134-test production suite.

| Comparison | Adaptive mean cost reduction | Case wins / ties / losses |
|---|---:|---:|
| Adaptive vs v2 | +0.302% | 2 / 0 / 1 |
| Adaptive vs uniform selection | -0.332% | 1 / 0 / 2 |
| Adaptive no-QUBO vs v2 no-QUBO | -0.652% | 1 / 0 / 2 |

The small improvement over v2 did not establish that learning helped. Uniform
selection performed better, and the matched no-QUBO comparison regressed.
Three previously used cases cannot establish general superiority. The
experiment was archived rather than promoted or discarded.

The ZIP preserves original project-relative paths for the two experimental
modules, their test file, and the whole pilot results folder. That folder
contains `FINDINGS.md`, `REPORT.md`, raw runs, per-case/operator CSVs, paired
statistics, protocol, manifest, exact `sources.zip`, audit and PNG/SVG graph.

Restore for inspection into an isolated folder from the repository root:

```powershell
Expand-Archive -LiteralPath results/archive/adaptive-removal-pilot-20261021.zip -DestinationPath results/restored-adaptive-pilot
venv\Scripts\python.exe -B -m team_benchmark.verify_results results/restored-adaptive-pilot/results/comparison/adaptive_removal_pilot_20261021
```

The verifier checks preserved source bytes and resimulates routes against the
original inputs; it does not execute archived solver code. Restoration does
not install the experiment into active source or tests. Inspect the restored
findings and runner before intentionally reusing the experiment.
