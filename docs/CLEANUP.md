# Project cleanup

The active project contains working member implementations, the shared pipeline,
meaningful tests, original inputs, two current evaluations and a recorded-results
dashboard. Historical results are retained as evidence without filling the
active source/output directories.

## Removed or consolidated

- Unused `NotImplementedError` solver, loader, comparison and visualization stubs.
- Nonfunctional root experiment scripts and their unused configuration templates.
- Eight `assert True` placeholder tests.
- Old placeholder dashboard pages/components, replaced by a single working viewer.
- One-off smoke outputs, console logs, Python caches and generated package metadata.
- Empty data/output buckets and the empty presentation placeholder.
- The generated full-source reference document, which duplicated code snapshots.
- Duplicate methodology documents, consolidated into [methodology.md](methodology.md).
- Test modules mixed with production code, moved into `tests/benchmark/`.

Working original `src/` utilities remain. Original member code and inputs remain;
Angel's submitted file is unchanged. User-facing architecture, algorithm,
experiment and methodology guides were updated to describe the actual code.

## Preserved evidence

Older comparison, development and member-generated artifacts were compressed into
three [labelled archives](../results/archive/README.md). Every stored file's bytes
were verified by SHA-256 before its loose original was removed. Approximately
23.1 MiB of historical artifacts now occupy 4.5 MiB. The archive index records
paths, sizes and hashes, including negative and mixed results.

Current v2 validation and budget-check JSON/CSV, protocols, manifests and figures
remain directly accessible. Exact source snapshots now use `sources.zip` instead
of loose duplicate source trees. The verifier supports both formats and reports
whether it used current code or preserved source bytes.

The previous `results/comparison/full_suite/runs.csv` was v1; it is now inside
`results/archive/v1-comparisons.zip`. The current table is
[hybrid_v2_validation/runs.csv](../results/comparison/hybrid_v2_validation/runs.csv).

## Checks

`venv\Scripts\python.exe -B -m pytest -q` runs the centralized substantive suite,
including both original member suites, cache/repair/provenance checks and the
Streamlit viewer. All 134 tests passed after the cleanup. The saved current
evaluations are independently re-audited, and archive hashes are checked.

[CLEANUP_RECORD.json](CLEANUP_RECORD.json) records paths removed/moved during
cleanup. [PATH_MIGRATION.json](PATH_MIGRATION.json) resolves older input/source
locations. The existing local environment and Git history were retained.
