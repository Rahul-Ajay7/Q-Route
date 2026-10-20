# Hybrid v2: efficiency and cross-vehicle refinement

This is the current implementation behind `members/Parikshit/run_hybrid.py`.
Historical v1 evidence is preserved in `results/archive/v1-comparisons.zip`
and is not pooled with the current runs.

## Changes

1. **Cache complete route evaluations.** A per-run bounded LRU cache keys each
   result by vehicle index and the full customer order. Only changed or evicted
   routes are simulated again. Every change still propagates load, traffic,
   waiting, service windows, and depot return through the entire affected route.
   The problem is immutable during a run. Live traffic changes would require a
   new cache/problem snapshot. Capacity and customer-coverage checks are retained.

2. **Apply that cache to the baselines too.** Classical SA, Angel's adapter,
   QUBO+SB, and current hybrid variants receive the same optimization. Cached
   reference search is tested against the uncached reference with fixed action
   limits to confirm the routes and costs do not change. Angel's submitted file
   and Rahul's SB backend are unchanged.

3. **Use cross-vehicle destroy-and-repair.** On stagnation, remove up to the
   configured window size of customers, then reinsert using regret-2 priorities
   and exact feasible insertion costs. Periodically try emptying a short route
   to save its fixed operating cost. Other attempts select customers around
   expensive detours. Customer membership can change between vehicles.

4. **Bound repair effort.** Rank positions geometrically, examine up to three
   positions in each of four candidate vehicles, and allow at most 160 exact
   insertion evaluations per attempt. Check the outer deadline before each such
   evaluation. Abort incomplete repairs without exposing partial routes as
   feasible candidates. This is a heuristic shortlist, not exhaustive insertion.

5. **Use sustained, adaptive stagnation.** Start refinement after `3 * plateau`
   actions without a new best. Successful refinement restores this interval;
   failures double it up to `24 * plateau`. A failed QUBO call also postpones
   further calls by an exponentially increasing number of refinement cycles,
   capped at eight. Global SA continues between refinements.

6. **Target avoidable detours.** QUBO windows are ranked by geometric removal
   detours, rather than simply choosing the route with the largest total cost.
   Attempt history and temporary customer exclusion remain in place. Selected
   repair customers also enter temporary exclusion.

7. **Expose both local backends.** `--hybrid-backend sa` is the default classical
   binary QUBO sampler; `--hybrid-backend sb` uses Rahul's existing ballistic SB.
   Full dynamic feasibility and true monetary cost decide acceptance for both.
   QUBO remains a frozen-time/load surrogate; it is not an exact CVRPTW encoding.

8. **Measure actual work.** Results record route simulations/cache hits, repair
   and QUBO wall time, accepted repairs, QUBO failures, and predicted versus actual
   candidate improvement. These diagnostics help distinguish surrogate errors
   from sampler failures. Atomic sampler calls can still overrun a deadline;
   overruns are explicitly recorded.

## Comparators and ablations

| Method name | Meaning |
|---|---|
| `hybrid` | Current v2, with caching, repair, adaptive trigger, exclusion, and QUBO |
| `hybrid_v1_cached` | Old search schedule with the same cache as current methods |
| `hybrid_legacy` | Original full-fleet evaluator and old search schedule |
| `hybrid_no_repair` | V2 without cross-vehicle destroy-and-repair |
| `hybrid_no_qubo` | V2 with classical repair but no QUBO calls |
| `hybrid_no_adaptation` | V2 with a fixed refinement interval and no QUBO failure backoff |
| `hybrid_no_tabu` | V2 without temporary customer exclusion |
| `hybrid_random` | V2 with random eligible QUBO window selection |

The meaning of a v2 ablation must not be confused with the old v1 ablation of
the same name. Source hashes, implementation versions, and separate directories
identify the experiments. A v2 improvement over `hybrid_legacy` alone cannot
establish a search-strategy benefit: use `hybrid_v1_cached` for that comparison.
If the no-QUBO version is competitive, do not attribute the gain to QUBO.

## Experiments and reproduction

Development used TC03, TC08, and TC11, seeds 0, 1, and 2, with 0.25-second
budgets. These are development observations, not final performance evidence.

The frozen validation protocol is
[`protocol.json`](../results/comparison/hybrid_v2_validation/protocol.json).
Validation excludes those three development files, uses search seeds 10..14,
and compares seven methods at 0.5 seconds per eligible run. Invalid input and
shared construction failures are retained. These related supplied fixtures
were used in earlier v1 experiments; this is not a genuinely independent
real-world holdout. No parameter updates are made after validation starts.

```powershell
# Run the current hybrid, using either backend
venv\Scripts\python.exe -B members/Parikshit/run_hybrid.py members/Rahul/test_cases/TC11.json --seconds 1 --hybrid-backend sa
venv\Scripts\python.exe -B members/Parikshit/run_hybrid.py members/Rahul/test_cases/TC11.json --seconds 1 --hybrid-backend sb

# A fresh comparison; existing output directories with runs are protected
venv\Scripts\python.exe -B -m team_benchmark.run --cases TC11.json --seeds 10 11 12 --seconds 1 --methods classical_sa tunnelling_sa qubo_sb hybrid hybrid_v1_cached hybrid_no_qubo --output results/comparison/my_v2_run

# Tests
venv\Scripts\python.exe -B -m pytest -q
```

Reports:

- [Development archive](../results/archive/development.zip).
- [Validation run](../results/comparison/hybrid_v2_validation/REPORT.md), generated
  on completion, with raw routes, histories, hashes, and original source snapshots.

The numerical conclusion must follow those reports. Lower costs in selected
development examples do not establish an overall advantage or quantum advantage.

## Completed 0.5-second validation

There were 25 valid case files after excluding the three development cases and
the invalid TC14 file. Three cases (TC15, TC16, TC25) failed shared construction.
Across the remaining 22 cases, five seeds and seven methods produced **770
feasible results**; all passed an independent post-run route/accounting audit.
The 105 construction failures have no finite quality scores. Exact recorded source snapshots and input hashes were verified. Cleanup
changes infrastructure and test locations; the numeric solver sources remain
unchanged. The audit distinguishes current files from preserved snapshots.

Positive reductions below mean lower v2 cost. Differences are paired by case
and seed, averaged over seeds within cases, then over cases.

| Comparator | V2 mean cost reduction | Case-bootstrap 95% interval | Holm p |
|---|---:|---:|---:|
| Old hybrid, equally cached | 3.16% | 1.96% to 4.42% | 0.0009822 |
| Classical SA, cached | 1.50% | 0.84% to 2.22% | 0.0009822 |
| Angel's tunnelling SA, cached | 1.11% | 0.60% to 1.69% | 0.0009822 |
| QUBO+SB, cached | 8.12% | 5.98% to 10.30% | 0.0005314 |
| V2 without cross-vehicle repair | 1.66% | 0.88% to 2.56% | 0.0009822 |
| V2 without QUBO | -0.41% | -1.04% to 0.12% | 0.3627 |

The updated full pipeline improves mean cost over all three primary comparators
and the old equally cached hybrid on this supplied suite and declared budget.
These related fixtures are not independent real-world evidence, and atomic
actions have recorded deadline overruns. The largest v2 overrun was 17.7 ms;
the old cached hybrid's largest was 34.6 ms. Interpret close comparisons with
those timing limits in mind.

The classical repair produced 196 accepted improvements from 796 attempts.
QUBO calls fell from 1,857 in the old cached hybrid to 278 in v2, with only three
accepted QUBO candidate improvements after the classical repair stage. Thus the
observed pipeline improvement must not be described as a quantum/QUBO advantage.
The no-QUBO version was slightly cheaper on average, with an interval crossing
zero for its difference from the full v2 pipeline.

Raw evidence is in [the validation directory](../results/comparison/hybrid_v2_validation),
including `runs.json`, `REPORT.md`, `paired_comparisons.json`, `audit.json`, and
original `sources.zip` snapshots. New CSV and plot exports belong in that directory.

## Additional budget check

[A separate protocol](../results/comparison/hybrid_v2_budget_check/protocol.json)
selects TC06, TC17, TC18 and TC20 by size and constraint coverage, uses the same
five seeds, and increases the budget to one second without changing the algorithm.
It includes all primary methods, the old cached hybrid, and v2 without QUBO.
Results are kept in [a separate report](../results/comparison/hybrid_v2_budget_check/REPORT.md)
and must not be pooled with the 0.5-second observations as independent samples.

All 120 one-second results were feasible and passed independent audits; recorded
source snapshots and input hashes matched. Mean v2 cost reductions were 1.71% versus the
old cached hybrid, 1.07% versus classical SA, 0.81% versus Angel's method, and
11.19% versus QUBO+SB. Four cases provide little statistical power: the
Holm-adjusted tests do not establish superiority. The no-QUBO variant remained
cheaper by 0.67% on average. The longest v2 deadline overrun in this check was
about 0.1 ms. These results support the same practical tradeoff without proving
a QUBO-specific benefit.

At the v2 algorithm release, 72 checks passed, including eight legacy
placeholders. Cleanup removed those placeholders; the centralized suite now
passes 134 substantive tests, including the original member suites and dashboard. Substantive new checks cover cache/full-evaluator equality,
reference search sequence preservation, feasible cross-vehicle repair, interrupted
repair rejection, cache eviction, strict exclusion, adaptive backoff, and both
local QUBO samplers. The SB-backed member CLI also completed an audited smoke run.
