# Team implementation and measured results

Historical v1 writeup. Current implementation and results are documented in
[hybrid v2](../HYBRID_V2.md). Older evidence links open the containing ZIP;
see [archive instructions](../../results/archive/README.md). Statements about
placeholder modules and tests describe the project before cleanup.

These numbers describe the original v1 implementation. Current v2 code and
separate evaluation are documented in [HYBRID_V2.md](../HYBRID_V2.md).

21 October 2026. These are exploratory offline experiments, not a universal
superiority or quantum-advantage claim.

## Implemented roles

| Member | Implementation |
|---|---|
| Alphonsa | New classical SA with global relocation, swaps, reversal, best-state retention, reheating |
| Angel | Submitted tunnelling-inspired SA preserved byte-for-byte; common-evaluator adapter reuses its proposals and tunnelling acceptance form |
| Rahul | Existing ballistic SB backend under a common QUBO, decoder, constraints, and INR objective |
| Parikshit | New global SA -> plateau -> worst-route bounded-window QUBO+SA -> customer exclusion -> further global SA cycle |

All methods share initialization and full dynamic evaluation. The hybrid's
local sampler is classical binary SA on a QUBO. A QUBO formulation does not by
itself demonstrate quantum computation or quantum advantage. The implementation
therefore does not substantiate wording that implies quantum-hardware execution
or a physically quantum annealing sampler.

Original Angel, SB, and Parikshit source/result files remain available. Root
greedy/SA code received targeted structural fixes; the complete review is in
[TEAM_CODE_REVIEW.md](TEAM_CODE_REVIEW.md).

## Main suite: all supplied JSON-named cases

28 valid JSON cases, five search seeds, four main methods plus four references/
ablations, 0.5-second optimization budgets: **1,120 recorded runs**. There were
**1,000 feasible runs**, each independently audited. Every method had 125 feasible
case/seed runs out of 140 attempts. TC15, TC16, and TC25 failed shared construction.
TC14 contains CSV text despite its extension, was logged as invalid, and is
excluded; the suite's exit status 1 intentionally reports that input error.

The table below averages paired relative differences over seeds within a case,
then averages cases. Positive values mean lower hybrid cost. These numbers are
not obtained by subtracting aggregate percentage improvements from initialization.

| Comparator | Mean hybrid cost reduction | Case-bootstrap 95% interval | Holm-adjusted p |
|---|---:|---:|---:|
| Classical SA | -0.25% | -0.65% to +0.12% | 0.7439 |
| Angel's tunnelling SA | -0.89% | -1.56% to -0.32% | 0.04452 |
| QUBO+SB | +6.13% | +4.22% to +8.12% | 0.0003574 |
| Hybrid without QUBO | -0.45% | -0.98% to +0.09% | 0.3496 |

The hybrid improves over QUBO+SB on this suite/budget, but does not beat both
global SA methods. These results also do not establish that QUBO refinement
contributes beyond the classical search/restart mechanism. Removing exclusion
or using random window selection was competitive; their intervals include zero.

Full evidence: [report](../../results/archive/v1-comparisons.zip),
[raw runs](../../results/archive/v1-comparisons.zip),
[CSV](../../results/archive/v1-comparisons.zip),
[plot](../../results/archive/v1-comparisons.zip),
[provenance manifest](../../results/archive/v1-comparisons.zip), and
[post-run audit](../../results/archive/v1-comparisons.zip).

## Additional 100-customer Solomon checks

The supplied C101, R101 and RC101 text files were converted without a download,
each with a free-flow and synthetic directed-corridor variant. Five seeds,
four methods, 1-second budgets produced **120 runs**. Of these **100 were feasible**;
all passed independent audits. Shared construction failed on every R101 traffic
variant seed. This is a heuristic construction failure, not a proof that the
traffic-modified instance is infeasible.

| Comparator | Mean hybrid cost reduction | Case-bootstrap 95% interval | Holm-adjusted p |
|---|---:|---:|---:|
| Classical SA | +0.68% | -0.45% to +1.99% | 0.3125 |
| Angel's tunnelling SA | -1.17% | -1.87% to -0.53% | 0.1875 |
| QUBO+SB | +5.02% | +2.73% to +7.56% | 0.1875 |

Only five jointly feasible variants of three underlying base instances remain.
The related variants are not independent broad evidence, and the small sample
does not establish superiority. Angel's method had lower seed-averaged cost than
the hybrid on each of those five variants. Do not pool these checks with the main
suite as independent observations or infer a time-budget effect across different
datasets.

Full evidence: [report](../../results/archive/v1-comparisons.zip),
[raw runs](../../results/archive/v1-comparisons.zip),
[CSV](../../results/archive/v1-comparisons.zip),
[plot](../../results/archive/v1-comparisons.zip), and
[audit](../../results/archive/v1-comparisons.zip).

## Validation and practical limits

- All 1,100 feasible runs passed independent coverage, capacity, timing, traffic,
  and monetary-accounting audits. Source and input hashes matched the manifests.
- Exact enumeration proved the optimum for TC03 and TC30; all methods reached it.
  This proves nothing about optimality or superiority on larger cases.
- The executed test suites passed: 26 shared tests, 16 SB tests, 3 root SA regression
  tests, and 67 existing Parikshit tests. Eight additional legacy root tests remain
  placeholders and are not substantive validation.
- All four member command-line entry points passed individual smoke checks.
- Hard and soft windows must be analyzed separately. These runs use hard windows.
  Default costs are synthetic INR assumptions, not measured delivery operating costs.
- Traffic is known offline. No live traffic feed, executed-prefix freezing,
  online new-order insertion, or breakdown rescue has been validated.
- Deadline checks occur between atomic actions; measured overruns are recorded.
  The largest main-method overrun in the main suite was about 5.5 ms for QUBO+SB.
  The QUBO+SA reference had a larger maximum overrun of about 34.4 ms.

## Defensible conclusion

The current hybrid is a working, reproducible implementation with stronger
evaluation than the original incomparable scripts. It outperformed the route-only
QUBO+SB comparator on the main supplied suite under the recorded budget. It did
**not** demonstrate an overall advantage over classical SA and Angel's tunnelling
SA, or a clear benefit from its QUBO stage.

Before a stronger claim, investigate surrogate error and QUBO overhead, freeze
any revised settings before testing, improve construction independently of the
method comparison, and test longer budgets on genuinely held-out instances with
a mature external VRP baseline. Preserve these negative/mixed results when
reporting subsequent improvements. Reproduction commands and model details are
in [the shared protocol](../../team_benchmark/README.md).
