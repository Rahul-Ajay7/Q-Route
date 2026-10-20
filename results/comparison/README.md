# Current comparisons

| Experiment | Report | Data |
|---|---|---|
| All supplied TC files + six Solomon variants, four approaches, five seeds, one second | [Cumulative summary](four_approaches_20261021/SUMMARY.md) | [Aggregate CSV](four_approaches_20261021/aggregate_results.csv), [per-case CSV](four_approaches_20261021/case_results.csv) |
| V2 validation: 22 jointly feasible cases, five seeds, 0.5 seconds | [Report](hybrid_v2_validation/REPORT.md) | [CSV](hybrid_v2_validation/runs.csv), [JSON](hybrid_v2_validation/runs.json) |
| V2 longer-budget check: four cases, five seeds, one second | [Report](hybrid_v2_budget_check/REPORT.md) | [CSV](hybrid_v2_budget_check/runs.csv), [JSON](hybrid_v2_budget_check/runs.json) |

The all-case run has a parent protocol and separate `supplied_cases/` and
`solomon_cases/` outputs; dataset statistics are not pooled. Earlier experiment
folders each contain their frozen `protocol.json`, original manifest, raw runs,
paired comparisons, audit, figures and exact source bytes in `sources.zip`.
CSV is the convenient table; JSON retains full routes and histories.

The latest complete run also has [individual case graphs](four_approaches_20261021/plots/README.md),
a [cumulative comparison](four_approaches_20261021/plots/cumulative_comparison.png),
and a [36-page graph PDF](four_approaches_20261021/plots/ALL_CASES_AND_CUMULATIVE.pdf).

Read [the findings](../../docs/HYBRID_V2.md) for interpretation. Older runs and
member outputs are in [the archive](../archive/README.md). One-off smoke outputs,
console logs and runtime caches have been removed.

The experimental adaptive-removal pilot is [archived](../../docs/history/ADAPTIVE_REMOVAL_PILOT.md),
including code, tests and all results. It is not an active comparison folder.
