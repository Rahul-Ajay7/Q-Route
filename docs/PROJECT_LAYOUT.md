# Project layout

```text
Q-Route/
  members/
    Alphonsa/              Classical SA entry point
    Angel/                 Original tunnelling SA and common-evaluator adapter
    Rahul/                 Original QUBO/SB backend, tests and TC inputs
    Parikshit/             Hybrid entry point and original qorbit package/data/tests
  team_benchmark/          Shared evaluator, cache, hybrid, samplers, runner and audits
  tests/
    benchmark/             Mathematical, constraint, cache, repair and provenance tests
    test_sa.py             Original routing regressions
    test_dashboard.py      Results viewer smoke test
  results/
    comparison/
      hybrid_v2_validation/   Main retained validation, data, figures and sources.zip
      hybrid_v2_budget_check/ Four-case longer-budget check
      four_approaches_20261021/ All TC + Solomon runs, cumulative and per-case summaries
    archive/               Historical/member/development evidence in verified ZIPs
  data/comparison/solomon/  Converted free-flow and congestion instances
  dashboard/app.py         Read-only recorded-results viewer
  src/                     Working original utilities; unused scaffolds removed
  docs/                    Current documentation and historical writeups
  venv/                    Existing local environment, unchanged
  pytest.ini               One test configuration for the entire project
  requirements.txt         Runtime dependencies
  requirements-dev.txt     Runtime dependencies plus pytest
```

Start with the [root README](../README.md), [member guide](../members/README.md),
[current results](HYBRID_V2.md), or [experiment commands](experiments.md).

## Evidence and older paths

The current numeric results and manifests retain their original contents.
Exact original source bytes are stored in each experiment's `sources.zip`.
The verifier supports compressed snapshots and older `.sources/` directories,
and distinguishes current-source matches from historical-source matches.

Older v1 reports, raw runs, and source snapshots are in
[`results/archive/v1-comparisons.zip`](../results/archive/v1-comparisons.zip).
Original member outputs and development runs have their own labelled archives.
See [archive restoration and verification](../results/archive/README.md).

[PATH_MIGRATION.json](PATH_MIGRATION.json) resolves historical input/source paths;
[CLEANUP_RECORD.json](CLEANUP_RECORD.json) records the latest removed/moved paths.
The previous `full_suite/runs.csv` tab refers to v1; use the
[current validation CSV](../results/comparison/hybrid_v2_validation/runs.csv).
