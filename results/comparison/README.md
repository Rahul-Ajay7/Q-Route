# Current comparisons

| Experiment | Report | Data |
|---|---|---|
| V2 validation: 22 jointly feasible cases, five seeds, 0.5 seconds | [Report](hybrid_v2_validation/REPORT.md) | [CSV](hybrid_v2_validation/runs.csv), [JSON](hybrid_v2_validation/runs.json) |
| V2 longer-budget check: four cases, five seeds, one second | [Report](hybrid_v2_budget_check/REPORT.md) | [CSV](hybrid_v2_budget_check/runs.csv), [JSON](hybrid_v2_budget_check/runs.json) |

Each folder contains the frozen `protocol.json`, original manifest, raw runs,
paired comparisons, audit, figures and exact source bytes in `sources.zip`.
CSV is the convenient table; JSON retains full routes and histories.

Read [the findings](../../docs/HYBRID_V2.md) for interpretation. Older runs and
member outputs are in [the archive](../archive/README.md). One-off smoke outputs,
console logs and runtime caches have been removed.
