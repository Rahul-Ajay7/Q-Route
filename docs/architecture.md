# Architecture

The implemented pipeline lives in `team_benchmark/`:

- `problem.py`: input adaptation, traffic-dependent route simulation and INR objective.
- `cached.py`: bounded per-run cache keyed by vehicle and complete customer order.
- `solvers.py`: common settings, original/reference search and method dispatch.
- `hybrid.py`: adaptive global SA, cross-vehicle repair and local QUBO refinement.
- `run.py`: shared construction, timed comparisons, manifests and source archives.
- `audit.py`, `exact.py`, `verify_results.py`: independent accounting, tiny exact oracles and saved-run verification.
- `report.py`, `plot.py`: paired statistics, reports, CSV and figures.
- `provenance.py`, `layout.py`: compact source snapshots and historical path resolution.

```text
TC JSON / converted Solomon JSON
  -> common Problem and feasible construction
  -> same initial routes for every method/seed
  -> solver search with common evaluator and budget
  -> independent final audit
  -> JSON, manifest, source archive, CSV, report and plots
  -> read-only Streamlit results viewer
```

Member entry points delegate to this pipeline. Angel's original proposal code
and Rahul's original SB/SA samplers are reused without changing their source.
Parikshit's original `qorbit` package remains independently testable in his folder.

`src/` retains working original data loaders, domain models, constraints, costs,
road/traffic clients, greedy routing, SA and utility code. Empty comparison,
visualization, and QUBO interface scaffolds have been removed. No runtime API
is advertised for those unimplemented classes.

The dashboard reads recorded files and draws coordinate routes; it performs
no optimization, online dispatch, or external traffic requests.
