# Q-ORBIT: complete project record and upgrade history

Last updated: **21 October 2026**. Repository folder: `Q-Route`.

This document brings together the project purpose, member contributions, implemented
methods, model, code layout, upgrade history, experiments, results, verification,
cleanup, and remaining work. It describes the repository as it stands on the date
above. Future upgrades should be appended to the history and reflected in the
current-state sections; this file does not update itself automatically.

Git records the first two development dates below. Later stages are reconstructed
from the team review, protocols, experiment artifacts, cleanup records, and this
working session. Their sequence is recorded without inventing individual release
dates or commit IDs. Team upgrades were developed together in the working tree;
their stage labels do not represent separate Git releases. Consult Git history
for the integration commit and later publication history.

## Latest development status

As of 21 October 2026, the four methods, hybrid v2, complete-case execution,
audits, graphs and reports are implemented. The latest published development
commit is [`efd2cc0`](https://github.com/Rahul-Ajay7/Q-Route/commit/efd2cc0)
on `main` in `Rahul-Ajay7/Q-Route`. This subsequent documentation refresh is
local until separately committed and pushed.

| Deliverable | Completed status / evidence |
|---|---|
| Four member methods | Classical SA, Angel's tunnelling SA, Rahul's QUBO+SB, Parikshit's adaptive hybrid v2 |
| Full case coverage | All 29 supplied TC JSON-named files and six converted Solomon variants scanned |
| Latest execution | Five seeds (20–24), 1 second per optimization, hard windows; 680 attempts |
| Final-route verification | 600 feasible results independently audited; source/input hashes verified |
| Failures retained | 80 construction failures; TC14 separately invalid; no finite failure scores |
| Individual graphs | 35 pages: 30 feasible case comparisons and five explicit failure/invalid pages |
| Cumulative figures | Separate supplied, Solomon and overall panels; PNG and SVG |
| Reports | 12-page method PDF, 36-page graph PDF, detailed run reports and CSVs |
| Test suite | 134 active production tests; the eight experimental checks and their recorded 142-test run are preserved in the pilot archive |
| Adaptive-removal experiment | Archived after mixed three-case findings; v2 remains the default |
| Research status | Hybrid has lowest latest cumulative cost; no demonstrated QUBO-specific or quantum advantage |

The latest cumulative costs sum seed-mean costs across 30 jointly feasible
dataset/case groups:

| Approach | Cumulative cost (synthetic INR) |
|---|---:|
| Parikshit / hybrid v2 | **431,735.22** |
| Angel / tunnelling SA | 436,543.37 |
| Alphonsa / classical SA | 444,502.59 |
| Rahul / QUBO+SB | 499,156.33 |

These are descriptive totals across a basket of cases, with expensive cases
dominating; they are not one fleet's operating bill or pooled statistical proof.
The latest run is a rerun of supplied fixtures, not an independent holdout.

Quick evidence: [latest summary](../results/comparison/four_approaches_20261021/SUMMARY.md),
[per-case CSV](../results/comparison/four_approaches_20261021/case_results.csv),
[graph index](../results/comparison/four_approaches_20261021/plots/README.md),
[cumulative graph](../results/comparison/four_approaches_20261021/plots/cumulative_comparison.png),
[graph PDF](../results/comparison/four_approaches_20261021/plots/ALL_CASES_AND_CUMULATIVE.pdf),
and [method PDF](FOUR_APPROACHES.pdf).

The method PDF describes the implementation and earlier frozen v2 evaluation.
The latest complete rerun and its 680 attempts are documented in the separate
summary and graph PDF; the older method PDF's numerical section has not been
silently replaced.

## Contents

1. [Purpose and current status](#1-purpose-and-current-status)
2. [Team contributions and attribution](#2-team-contributions-and-attribution)
3. [Problem model and assumptions](#3-problem-model-and-assumptions)
4. [Current optimization pipeline](#4-current-optimization-pipeline)
5. [Implementation and project layout](#5-implementation-and-project-layout)
6. [Upgrade history](#6-upgrade-history)
7. [Experiment history and measured results](#7-experiment-history-and-measured-results)
8. [Testing and reproducibility](#8-testing-and-reproducibility)
9. [Cleanup and preserved evidence](#9-cleanup-and-preserved-evidence)
10. [Running the project](#10-running-the-project)
11. [Limitations and next upgrades](#11-limitations-and-next-upgrades)
12. [Recording future upgrades](#12-recording-future-upgrades)

## 1. Purpose and current status

Q-ORBIT studies traffic-aware **Capacitated Vehicle Routing with Time Windows
(CVRPTW)**. The task is to assign customers to vehicles and order their visits,
minimizing operating cost while satisfying vehicle capacity, customer coverage,
service windows, and depot-return constraints.

The proposed method combines feasible greedy construction, global simulated
annealing (SA), local customer-position QUBOs, and further SA. The current v2
adds cross-vehicle destroy-and-repair and adaptive refinement scheduling.

The project now has four runnable member entry points, a shared comparison
framework, independent route audits, reproducible experiment artifacts, a
recorded-results dashboard, and a centralized test suite.

The main v2 validation supports lower average hybrid cost than the three primary
baselines on the supplied cases at the declared budget. **It does not establish
universal superiority, a QUBO-specific benefit, or quantum advantage.** The
no-QUBO variant was slightly cheaper on average. Earlier mixed results remain
available rather than being replaced by the improved results.

## 2. Team contributions and attribution

| Member | Assigned/current method | Entry point | Submission and implementation status |
|---|---|---|---|
| Alphonsa | Classical SA | `members/Alphonsa/classical_sa.py` | No original submission was available; a shared-baseline implementation was added with user authorization. Alphonsa's review is pending. |
| Angel | Tunnelling-inspired SA | `members/Angel/run_tunnelling.py` | Original `saq_cvrptw.py` preserved; adapter reuses proposal logic and tunnelling acceptance with the shared evaluator. |
| Rahul | QUBO + simulated bifurcation (SB) | `members/Rahul/run_comparison.py` | Original ballistic SB backend retained; common-evaluator comparison added. Original standalone backend remains in `run_sb.py`. |
| Parikshit | Hybrid SA + local QUBO refinement | `members/Parikshit/run_hybrid.py` | Original `qorbit` package retained; shared hybrid pipeline added and subsequently upgraded to v2. |

These entry points delegate to shared code so costs, constraints, initialization,
and comparison fixes apply consistently. Newly added adapters and the shared
framework should be distinguished from each member's original submission.

Angel's supplied code implements tunnelling-inspired route SA, despite an earlier
QUBO+SA role description. The user explicitly requested retaining that method.
The benchmark's `qubo_sa` reference is therefore **not Angel's method**.

Angel's unchanged original source has recorded SHA-256:

```text
7840ac4ca487e1a67230a80a56a8f747b7b7657bfd974223a71346becc30747c
```

Parikshit's original study concerned local traffic-damage repair. It did not
already contain the full global-SA plateau/refinement/recombination cycle and
temporary customer exclusion described in the team proposal. The original study
and its generated evidence remain separate from the shared implementation.

See [member guide](../members/README.md) and
[historical code review](history/TEAM_CODE_REVIEW.md).

## 3. Problem model and assumptions

The shared comparison uses these rules:

- Every customer appears exactly once across the fleet.
- Assigned demand must not exceed the vehicle's capacity.
- Every used vehicle starts at its depot and returns within the depot deadline.
- Service respects ready times, release times, and applicable new-order times.
- The main experiments use hard service-start deadlines. Soft windows are a
  separately selectable problem with lateness penalties.
- Directed traffic events affect travel at departure. Temporary closures can be
  waited out until an event boundary opens the edge.
- Traffic and orders are known offline during optimization.

The monetary objective is:

```text
total cost = fixed cost per used vehicle
           + distance rate × total distance
           + time rate × total route duration
           + fuel price × estimated fuel
           + lateness rate × total lateness
```

All terms are in INR using explicitly synthetic cost assumptions. Route duration
includes driving, waiting, and service. Fuel depends on remaining load and
congestion. Distances are synthetic kilometres, times are input minutes, and
fuel is model-estimated litres. Hard-window feasible solutions have zero lateness.
Actual coefficient values and experiment settings belong to the saved manifests
and model implementation, rather than an assumed universal operating tariff.

Structural violations such as missing/duplicate/unknown customers or incorrect
fleet structure must not receive a valid quality score. A failed construction
is recorded as `NO_FEASIBLE_INITIAL_SOLUTION`; it does not prove that the input
instance is mathematically infeasible.

Existing commercial and open-source fleet-routing tools address this problem.
The research contribution being tested is this particular hybrid's quality and
runtime tradeoff, rather than the existence of multi-vehicle routing software.
See [methodology](methodology.md) for the detailed model and references.

## 4. Current optimization pipeline

1. **Load and validate the instance.** Adapt the supplied case to the common
   problem representation and preserve input identity and hashes.
2. **Construct a feasible initial solution.** Use nearest feasible neighbours,
   followed by up to eight feasible-insertion restarts if necessary. Every
   method receives the same initial routes for a given case and seed.
3. **Run global SA.** Relocate customers across vehicles, swap customers, and
   reverse route segments. Retain the best complete feasible solution.
4. **Detect sustained stagnation.** Start refinement after `3 × plateau`
   actions without a new best. Back off after failed refinement.
5. **Attempt cross-vehicle repair.** Remove customers around expensive detours
   or attempt to empty a short route. Reinsert using regret-2 priorities and
   exact feasible insertion costs. Discard incomplete repairs.
6. **Select a local QUBO window.** Rank eligible windows using avoidable detours,
   respecting temporary customer exclusions and attempted-window history.
7. **Build and sample the QUBO.** Binary `x(i,p)` means customer `i` occupies
   position `p`. Encode entry, exit, adjacency, approximate timing costs, and
   one-customer/one-position assignment penalties.
8. **Decode and validate.** Project invalid assignment matrices to one-to-one
   assignments when needed, reconstruct the full route, and recompute exact
   dynamic costs and constraints. Retain only feasible improvements.
9. **Resume global SA.** Continue between refinements until the time, action,
   or configured cycle limits apply; return the best feasible solution.
10. **Audit and record.** Independently resimulate final routes and save the
    settings, routes, diagnostics, source/input provenance, and comparisons.

The default local QUBO sampler is **classical binary SA**. The optional `sb`
backend uses Rahul's ballistic simulated bifurcation implementation. Neither
backend executes on quantum hardware.

The QUBO is a bounded route-ordering surrogate: it approximates departure times
and loads, and does not encode the entire CVRPTW exactly. Cross-vehicle assignment
changes come from global SA and classical repair. Exact full-route evaluation,
rather than surrogate energy alone, determines acceptance.

Current default settings, unless overridden:

| Setting | Value |
|---|---:|
| Optimization time | 1 second |
| Maximum actions | 1,000,000 |
| Local window | 5 customers / 25 assignment variables |
| QUBO samples | 8 |
| QUBO steps | 40 |
| Base plateau | 50 actions |
| Temporary exclusion | 2 refinement cycles |
| Maximum refinement cycles | 20 |
| Cooling | 0.995 |
| Hybrid backend | `sa` |

Repair examines a bounded geometric shortlist: up to three insertion positions
in each of four candidate vehicles, with at most 160 exact insertion evaluations
per repair attempt. Failed refinement expands the trigger interval up to
`24 × plateau`; unsuccessful QUBO calls add backoff up to eight refinement cycles.
These limits control overhead and do not perform exhaustive neighbourhood search.

## 5. Implementation and project layout

| Location | Responsibility |
|---|---|
| `members/` | Four member entry points, preserved original implementations, member tests and inputs |
| `team_benchmark/problem.py` | Input adaptation, route simulation, traffic, constraints, monetary cost |
| `team_benchmark/solvers.py` | Settings, baseline/reference search, sampler integration and dispatch |
| `team_benchmark/hybrid.py` | Adaptive hybrid search and cross-vehicle repair |
| `team_benchmark/cached.py` | Bounded complete-route evaluation cache |
| `team_benchmark/run.py` | Common initialization, timed runs and experiment outputs |
| `team_benchmark/audit.py`, `exact.py`, `verify_results.py` | Independent final accounting, tiny exact oracles and saved-result verification |
| `team_benchmark/report.py`, `plot.py` | Paired statistics, reports, CSV and figures |
| `team_benchmark/provenance.py`, `layout.py` | Source snapshots and historical path resolution |
| `src/` | Working original domain, data, cost, constraints, greedy/SA, routing and traffic utilities |
| `tests/` | Shared algorithm, provenance, layout, original SA and dashboard tests |
| `dashboard/app.py` | Read-only Streamlit experiment table, cost chart and route viewer |
| `data/comparison/solomon/` | Converted free-flow and synthetic-congestion Solomon inputs |
| `results/comparison/` | Frozen v2 validation, budget check and latest complete four-method run |
| `results/archive/` | Verified historical, development and member-artifact ZIPs |
| `docs/` | Current guides, this master record and historical findings |
| `pytest.ini` | Central test collection, including original member suites |
| `requirements.txt`, `requirements-dev.txt` | Runtime and test dependencies |

The dashboard reads saved results; it does not launch optimizations or fetch
traffic. It shows failed construction explicitly and does not graph partial
route costs as successful solutions. Existing network clients in `src/` do not
make the shared benchmark a validated live-traffic system.

## 6. Upgrade history

### Stage 0 — Initial scaffold: 10 August 2026

Git commit `80ea520`: initial Q-ORBIT project scaffold. This established the
repository skeleton; later review found that several scaffold interfaces and
tests were placeholders rather than implemented features.

### Stage 1 — Original core implementation: 28 August 2026

Git commit `a70ad50`: cost, constraint, data, and optimization modules plus a
generated code reference. This supplied the original working core on which the
later team integration could build. The generated reference was later removed
as a duplicate of source code and experiment snapshots.

### Stage 2 — Submission preservation and team separation

Recorded in the team work reviewed on 21 October 2026:

- Preserved Angel's submitted tunnelling-inspired SA.
- Imported and separated Parikshit's supplied `qorbit` project.
- Created Alphonsa's role location and, after authorization, implemented the
  missing classical-SA baseline; member review remains pending.
- Preserved Rahul's QUBO/SB backend and original test cases.
- Added member adapters instead of presenting standalone outputs with different
  objectives as directly comparable results.

### Stage 3 — Correctness fixes and common comparison framework

The submitted implementations differed in objective units, hard/soft windows,
traffic treatment, initialization, and search scope. The shared framework added
one INR evaluator, common constraints, identical initial routes, timed search,
independent audits, tiny exact checks, and source/input manifests.

Specific changes recorded in the review:

| Earlier issue | Implemented correction |
|---|---|
| Root SA could not relocate into an unused vehicle | Include unused vehicles, including the single-customer case |
| Omitting earlier unused fleet slots could shift vehicle assignment | Preserve and validate explicit `vehicle_index` |
| Duplicate/unknown customers or malformed fleet structure could score misleadingly | Reject structural violations rather than accepting their cost |
| Angel standalone precheck, raw objective and ID assumptions prevented fair comparison | Shared adapter bypasses those components while preserving the submitted file |
| Original QUBO penalty adequacy was not guaranteed by normalization alone | Bound the whole valid surrogate cost before setting assignment penalties |
| Repeated expensive-window selection restricted exploration | Track attempted windows and cycle through eligible alternatives |
| Partial construction could be confused with a feasible result | Explicit failure status and no finite partial-route score |
| Invalid JSON-named input could contaminate a suite | Log and exclude invalid input, finish valid cases, return an error status |

Eight root placeholder tests remained at this stage and were explicitly excluded
from substantive validation claims. They were removed in the cleanup stage.

### Stage 4 — First complete shared hybrid and v1 evaluation

Implemented feasible construction → global SA → plateau-triggered local QUBO →
full-route validation/recombination → further SA, with temporary customer exclusion.
Added references and ablations to test whether QUBO, selection, or exclusion
explained any improvement.

The full supplied suite and additional Solomon checks were run and audited.
V1 beat the route-only QUBO+SB comparator, but did not beat both global-SA
baselines. These mixed findings motivated improvements rather than a claim of
success. Full results remain in the historical archive and Section 7 below.

### Stage 5 — Project layout reorganization

Moved member work under `members/`, with Rahul's former `SB+QUBO` work under
`members/Rahul/`. Separated shared comparison code, documentation, datasets, and
results. Added path migration mappings so recorded input/source paths could
still be resolved. Historical naming is retained in provenance where necessary.

See [project layout](PROJECT_LAYOUT.md) and [path migration](PATH_MIGRATION.json).

### Stage 6 — Hybrid v2 improvements

- Added a bounded per-run LRU cache keyed by vehicle and full customer order.
  The same optimization was applied to all current baselines for fairness.
- Added regret-2 cross-vehicle destroy-and-repair, including attempts to remove
  a vehicle's fixed cost by emptying a short route.
- Bounded insertion search and checked deadlines before exact evaluations;
  incomplete repairs cannot escape as feasible candidates.
- Replaced frequent fixed refinements with sustained stagnation, adaptive
  intervals, and exponential backoff after failed QUBO attempts.
- Ranked QUBO windows by avoidable detours, retaining attempted-window tracking
  and strict temporary customer exclusion.
- Exposed both binary-SA and SB local backends.
- Added diagnostics for simulations/cache hits, repair/QUBO time, failures,
  accepted improvements, and predicted versus actual candidate gains.
- Added equally cached v1 and no-repair/no-QUBO comparisons to isolate effects.

Cache validity assumes a fixed problem/traffic snapshot during a run. A live
traffic update would require invalidation or a new problem/cache snapshot.

Development used TC03, TC08 and TC11, seeds 0–2, at 0.25 seconds. These development
observations were separated from the frozen validation rather than counted as
final evidence.

### Stage 7 — Frozen v2 validation and longer-budget check

Ran the main 0.5-second validation using new seeds 10–14 and excluding development
files; then a separate four-case, 1-second check with the same frozen algorithm
and search parameters. Retained failures, invalid input, raw routes, diagnostics,
statistics, source snapshots and input hashes. Independently audited all 890
feasible current results. Quantitative outcomes are in Section 7.

### Stage 8 — Repository cleanup and working results viewer

- Removed unimplemented solver/loader/benchmark/visualization interfaces, unused
  experiment scripts/configuration templates, and eight `assert True` tests.
- Removed one-off smoke outputs, caches, console logs, generated package metadata,
  empty buckets, an empty presentation placeholder and duplicated source-reference
  documentation.
- Consolidated methodology documents and moved historical reports into
  `docs/history/`.
- Moved shared tests from production code into `tests/benchmark/`; added one
  root pytest configuration covering shared, root and original member tests.
- Replaced placeholder dashboard pages with the working recorded-results viewer.
- Pruned unused runtime dependency declarations and added `requirements-dev.txt`.
- Compressed historical artifacts into three SHA-256-verified archives before
  removing loose originals.
- Replaced loose current source snapshots with `sources.zip`; updated verification
  to support both compressed and older snapshot formats without executing
  archived code.
- Rewrote the README, layout, architecture, algorithm and experiment guides.

Post-cleanup verification recorded **134 substantive passing tests**, a successful
temporary end-to-end comparison, archive verification, documentation-link checks,
and re-audits of the 770 + 120 current feasible results. Cleanup did not rerun the
scientific benchmarks or change their recorded numerical results.

### Stage 9 — Unified project record: 21 October 2026

Added this document to collect project details and all recoverable upgrade stages
in one location. Linked it from the root README and documentation index. This is
a documentation update; it makes no algorithm or benchmark-result changes.

### Stage 10 — Four-approach PDF and GitHub delivery: 21 October 2026

Added [FOUR_APPROACHES.pdf](FOUR_APPROACHES.pdf), a detailed 12-page explanation
of all four methods, shared constraints/objective, acceptance laws, QUBO encoding,
ballistic SB, hybrid v2 repair/adaptation, measured results, and limitations.
The [editable source](FOUR_APPROACHES.md) and
[rebuild script](tools/build_approaches_pdf.py) are retained alongside it.
The generator uses the existing matplotlib dependency. Linked the report from
the root README and documentation index. Re-ran all 134 substantive tests
successfully. The user requested committing and pushing the integrated project
to the configured GitHub repository; the delivery commit is recorded in Git.
No new scientific benchmark was run for the report.

### Stage 11 — Complete four-approach execution: 21 October 2026

Ran every supplied TC JSON-named file and all six converted Solomon variants
with the four primary approaches, five seeds (20–24), hard windows, and one
second per optimization. There were 680 recorded attempts: 600 independently
audited feasible results and 80 shared construction failures. TC14 was separately
recorded as invalid. TC15, TC16, TC25 and R101's traffic variant failed shared
construction; these are not infeasibility proofs.

Saved raw routes, source snapshots, manifests, audits, CSVs, plots and reports
under `results/comparison/four_approaches_20261021/`. Added a summary exporter
with separate dataset-level paired comparisons and descriptive cumulative
cost totals. The [summary](../results/comparison/four_approaches_20261021/SUMMARY.md)
contains the complete new results; earlier benchmark numbers remain unchanged.
This run includes previously used development cases, so it is a full rerun,
not an independent holdout evaluation. No no-QUBO ablation was requested or run.

On the supplied suite, hybrid paired mean cost reductions were 1.02% versus
classical SA, 0.90% versus tunnelling SA and 8.79% versus QUBO+SB. On the five
feasible Solomon variants, reductions were 3.18%, 0.52% and 13.84% respectively;
the small Solomon dataset did not establish superiority under adjusted tests.

The sum of seed-averaged costs over all 30 jointly feasible dataset/case groups
was INR 431,735.22 for hybrid, 436,543.37 for tunnelling SA, 444,502.59 for
classical SA and 499,156.33 for QUBO+SB. This is a descriptive basket of cases;
expensive cases dominate it. It is not a single fleet's cost or a pooled
statistical comparison. Saved source and input hashes passed verification.

### Stage 12 — Individual and cumulative graphs: 21 October 2026

Added `team_benchmark/plot_cases.py` to render the saved complete-run evidence.
Created 35 individual case PNGs (30 successful comparisons and five explicit
invalid/construction-failure pages), a cumulative PNG/SVG with separate supplied,
Solomon and overall panels, and one 36-page vector PDF containing every case
plus the cumulative graph. Seed-mean bars show individual seed dots and sample
standard deviations; these whiskers are not confidence intervals. Failed cases
have no cost bars. No optimization was rerun and recorded costs are unchanged.
See the [graph index](../results/comparison/four_approaches_20261021/plots/README.md).

### Stage 13 — Results and graphs published to GitHub: 21 October 2026

Published the integrated project and 12-page method report as commit
[`82f1300`](https://github.com/Rahul-Ajay7/Q-Route/commit/82f1300).
Then published all complete-run evidence, cumulative/per-case exporters,
35 case PNGs, cumulative PNG/SVG, the 36-page graph PDF and updated guides as
[`efd2cc0`](https://github.com/Rahul-Ajay7/Q-Route/commit/efd2cc0).
Both pushes to `Rahul-Ajay7/Q-Route` on `main` completed successfully. The
working tree was clean after the results push. Publication did not rerun the
scientific experiments or change their cost values.

### Stage 14 — Development documentation refreshed: 21 October 2026

Added a current-status snapshot to this master record, including case coverage,
verification counts, cumulative totals, graph/report locations and published
commit IDs. Updated the README, documentation index, architecture, experiment
commands and project layout to reflect the new exporters and complete-run
artifacts. Kept the frozen validation, complete rerun and historical results
distinct. This is a documentation-only update; no solver, benchmark data or
generated PDF content changed. Local documentation links were checked.

### Stage 15 — Adaptive-removal pilot tried and archived: 21 October 2026

Created the isolated adaptive-removal implementation, compared it with v2,
uniform selection and matched no-QUBO controls on three cases and ten seeds,
and audited all 150 runs. The full suite passed 142 tests with eight new
experimental checks. The small gain over v2 was accompanied by losses to
uniform selection and in the matched no-QUBO control; no production promotion
was justified. The user then requested archiving the experiment.

Saved both experimental modules, the test file and complete pilot results in
`results/archive/adaptive-removal-pilot-20261021.zip`. Verified all 16 files
byte-for-byte before removing the loose originals. Updated active links to a
[historical summary](history/ADAPTIVE_REMOVAL_PILOT.md), retaining the protocol,
source snapshots, raw runs, diagnostics, audit and figures in the archive.
Production v2 and the main dispatcher remain unchanged. Active test collection
returns to 134 tests; the archived eight can be inspected separately.

## 7. Experiment history and measured results

### Experimental adaptive removal pilot — 21 October 2026

Created an isolated `team_benchmark/experimental_adaptive.py`, leaving production
v2 unchanged. Compared v2, adaptive removal, uniform operator selection, and
matched v2/adaptive no-QUBO controls on TC06, TC18 and TC20, ten seeds (30–39),
one second per method: 150 feasible, independently audited results. Source/input
hashes verified. All 142 tests passed, including eight new experimental checks.

Adaptive removal lowered paired mean cost by 0.302% versus v2 (two case wins,
one loss), but was 0.332% worse than uniform selection. Adaptive no-QUBO was
0.652% worse than v2 no-QUBO. These three familiar cases do not establish
superiority or a learning/QUBO-specific gain. Kept v2 as the default.
The experimental code, tests and all pilot evidence have since been archived.
See the [historical findings and restoration guide](history/ADAPTIVE_REMOVAL_PILOT.md)
and [complete archive](../results/archive/adaptive-removal-pilot-20261021.zip).

Cost reductions below are paired by case and seed, averaged over seeds within
each case, then averaged across cases. Positive values mean lower hybrid cost;
negative values mean the comparator was cheaper. Different budgets, versions,
and related dataset variants must not be pooled as independent samples.

### V1 supplied-suite comparison — historical

28 valid cases × 5 seeds × 8 methods = **1,120 attempts**. There were 1,000
feasible runs, all audited. TC15, TC16 and TC25 failed shared construction.
TC14 was excluded as invalid input.

| Comparator | Mean v1 hybrid cost reduction | Case-bootstrap 95% interval | Holm-adjusted p |
|---|---:|---:|---:|
| Classical SA | -0.25% | -0.65% to +0.12% | 0.7439 |
| Angel's tunnelling SA | -0.89% | -1.56% to -0.32% | 0.04452 |
| QUBO+SB | +6.13% | +4.22% to +8.12% | 0.0003574 |
| Hybrid without QUBO | -0.45% | -0.98% to +0.09% | 0.3496 |

Conclusion: the first shared hybrid did not outperform both global-SA baselines.
Evidence: [historical summary](history/TEAM_COMPARISON_SUMMARY.md) and
[`v1-comparisons.zip`](../results/archive/v1-comparisons.zip).

### V1 Solomon checks — historical

C101, R101 and RC101 were converted into free-flow and synthetic directed-traffic
variants. Five seeds, four methods and 1-second budgets produced 120 attempts;
100 were feasible and independently audited. R101's traffic variant failed shared
construction for all methods/seeds. This was not an infeasibility proof.

| Comparator | Mean v1 hybrid cost reduction | Case-bootstrap 95% interval | Holm-adjusted p |
|---|---:|---:|---:|
| Classical SA | +0.68% | -0.45% to +1.99% | 0.3125 |
| Angel's tunnelling SA | -1.17% | -1.87% to -0.53% | 0.1875 |
| QUBO+SB | +5.02% | +2.73% to +7.56% | 0.1875 |

Five jointly feasible variants from three underlying base instances are too few
for broad conclusions. These checks do not establish v2 performance on Solomon.

### V2 main validation — current

After excluding three development files and invalid TC14, 25 valid files remained.
Five seeds and seven methods produced **875 attempts: 770 feasible results and
105 shared construction failures**. The 22 successfully constructed cases provide
110 paired seeds per method. Budget: 0.5 seconds per optimization; initialization
is shared and timed separately.

| Comparator | Mean v2 hybrid cost reduction | Case-bootstrap 95% interval | Holm-adjusted p |
|---|---:|---:|---:|
| Equally cached v1 hybrid | +3.16% | +1.96% to +4.42% | 0.0009822 |
| Classical SA | +1.50% | +0.84% to +2.22% | 0.0009822 |
| Angel's tunnelling SA | +1.11% | +0.60% to +1.69% | 0.0009822 |
| QUBO+SB | +8.12% | +5.98% to +10.30% | 0.0005314 |
| V2 without cross-vehicle repair | +1.66% | +0.88% to +2.56% | 0.0009822 |
| V2 without QUBO | -0.41% | -1.04% to +0.12% | 0.3627 |

The v2 hybrid supports lower average cost than the three primary comparators on
this supplied suite and budget. It does not show that its QUBO stage caused that
gain. Classical repair accepted 196 improvements in 796 attempts. QUBO calls
dropped from 1,857 in equally cached v1 to 278 in v2; only three v2 QUBO candidates
were accepted improvements after the repair stage.

All 770 feasible routes passed independent audits. Maximum recorded hybrid budget
overrun was 17.7 ms; equally cached v1 reached 34.6 ms. Wall-clock differences and
atomic actions remain relevant when interpreting close results.

Evidence: [report](../results/comparison/hybrid_v2_validation/REPORT.md),
[CSV](../results/comparison/hybrid_v2_validation/runs.csv),
[protocol](../results/comparison/hybrid_v2_validation/protocol.json),
[paired statistics](../results/comparison/hybrid_v2_validation/paired_comparisons.json),
[audit](../results/comparison/hybrid_v2_validation/audit.json).

### V2 longer-budget check — current

TC06, TC17, TC18 and TC20 × five seeds × six methods produced **120 feasible,
audited results**, at 1 second per optimization. The algorithm and search settings
were otherwise frozen.

| Comparator | Mean v2 hybrid cost reduction | Case-bootstrap 95% interval | Holm-adjusted p |
|---|---:|---:|---:|
| Equally cached v1 hybrid | +1.71% | +0.25% to +3.85% | 1 |
| Classical SA | +1.07% | +0.13% to +2.01% | 1 |
| Angel's tunnelling SA | +0.81% | +0.27% to +1.18% | 1 |
| QUBO+SB | +11.19% | +5.84% to +15.24% | 0.625 |
| V2 without QUBO | -0.67% | -1.36% to -0.06% | 1 |

The adjusted tests do not establish superiority with only four cases. The
no-QUBO variant again had lower average cost. The largest hybrid overrun was
approximately 0.1 ms.

Evidence: [report](../results/comparison/hybrid_v2_budget_check/REPORT.md),
[protocol](../results/comparison/hybrid_v2_budget_check/protocol.json),
[audit](../results/comparison/hybrid_v2_budget_check/audit.json).

## 8. Testing and reproducibility

The latest recorded centralized run passed **134 substantive tests**, including
the original member suites and the dashboard. At the v2 algorithm release an
earlier count was 72 checks, including eight placeholders. Those counts have
different collection scopes; 72 versus 134 is not a like-for-like quality metric.

Meaningful checks cover:

- Tiny exact enumeration (including TC03 and TC30) and assignment-energy properties.
- Customer coverage, capacity, windows, traffic timing and monetary accounting.
- Empty-vehicle relocation and preservation of vehicle slots.
- Cached/full-evaluator equality, reference search sequence preservation and eviction.
- Feasible cross-vehicle repair and rejection of interrupted partial repairs.
- Strict customer exclusion, adaptive backoff and both local sampler backends.
- Historical path resolution, compressed snapshot integrity and path-escape rejection.
- Dashboard loading and explicit display of construction failures.

Every experiment retains the applicable protocol/settings, source/input hashes,
raw routes, diagnostics and results. Current experiment folders contain:

| Artifact | Purpose |
|---|---|
| `protocol.json` | Declared cases, seeds, settings and selection policy |
| `manifest.json` | Run metadata and exact source/input identities |
| `sources.zip` | Original source bytes captured for that experiment |
| `runs.json` | Detailed recorded runs, routes and diagnostics |
| `runs.csv` | Tabular export for inspection |
| `paired_comparisons.json`, `REPORT.md` | Paired summaries, intervals and tests |
| `audit.json` | Independent accounting/constraint verification |
| `invalid_inputs.json` | Excluded invalid input records |
| `comparison.png`, `comparison.svg` | Saved comparison figures |

The verifier can use preserved source snapshots when the current files differ
because of later infrastructure changes or moves. Verifying snapshot bytes does
not execute those snapshots and is distinct from replaying historical experiments.

Case-level bootstrap intervals and two-sided Wilcoxon tests with Holm correction
are used for paired comparisons. They cannot remove dataset bias. Related supplied
fixtures and repeated seeds are not independent real-world holdout instances.

## 9. Cleanup and preserved evidence

Historical artifacts were compressed and verified before loose originals were
removed. Approximately **23.1 MiB became 4.5 MiB** across three archives:

| Archive | Files | Contents |
|---|---:|---|
| `results/archive/v1-comparisons.zip` | 57 | V1 supplied suite, Solomon checks and earlier pilot |
| `results/archive/development.zip` | 26 | Hybrid v2 development observations |
| `results/archive/member-artifacts.zip` | 79 | Original member-generated reports/results and obsolete migration tools |

The [archive index](../results/archive/INDEX.json) records archive SHA-256 values;
each ZIP contains an internal index of original paths, byte counts and file
hashes. Negative and mixed results are included.

The former `results/comparison/full_suite/runs.csv` is historical v1 evidence
inside `v1-comparisons.zip`. The active CSV is
[`hybrid_v2_validation/runs.csv`](../results/comparison/hybrid_v2_validation/runs.csv).

Original source, meaningful tests and inputs were retained, including Angel's
unchanged submission and Parikshit's original package. The local `venv`, Git
history and license were retained. No commit, push or deployment was performed
as part of the cleanup.

See [cleanup explanation](CLEANUP.md), [removed/moved path ledger](CLEANUP_RECORD.json),
and [archive restoration instructions](../results/archive/README.md).

## 10. Running the project

Run from the repository root in PowerShell. These commands use the existing local
environment. For a fresh environment, install `requirements.txt` for runtime or
`requirements-dev.txt` for runtime plus tests.

```powershell
# Inspect all available comparison settings
venv\Scripts\python.exe -B -m team_benchmark.run --help

# Run one current hybrid case
venv\Scripts\python.exe -B members/Parikshit/run_hybrid.py members/Rahul/test_cases/TC11.json --seconds 1

# Select the optional SB local QUBO sampler
venv\Scripts\python.exe -B members/Parikshit/run_hybrid.py members/Rahul/test_cases/TC11.json --seconds 1 --hybrid-backend sb

# New paired comparison; choose an unused output folder
venv\Scripts\python.exe -B -m team_benchmark.run --cases TC11.json --seeds 20 21 22 --seconds 1 --methods classical_sa tunnelling_sa qubo_sb hybrid hybrid_v1_cached hybrid_no_qubo --output results/comparison/my_run

# Export CSV and plots for that new run
venv\Scripts\python.exe -B -m team_benchmark.plot results/comparison/my_run

# Run all substantive tests
venv\Scripts\python.exe -B -m pytest -q

# Independently verify both retained current experiments
venv\Scripts\python.exe -B -m team_benchmark.verify_results results/comparison/hybrid_v2_validation
venv\Scripts\python.exe -B -m team_benchmark.verify_results results/comparison/hybrid_v2_budget_check

# Browse recorded experiments, costs and route plans
venv\Scripts\python.exe -B -m streamlit run dashboard/app.py
```

Folders already containing recorded runs are protected against overwriting.
All-case scans encounter TC14, which contains CSV rather than JSON: they log the
error, complete valid cases, and return exit status 1. Fixed-action runs help
debug deterministically but do not represent equal computational work. Avoid
other heavy workloads during timed comparisons.

Runtime dependencies currently declared are NumPy, pandas, matplotlib, Streamlit,
requests and SciPy. Development requirements add pytest. Member-specific original
dependency declarations remain with their preserved projects.

## 11. Limitations and next upgrades

Completed work must be distinguished from these outstanding research tasks:

1. **Establish the value of QUBO.** Diagnose surrogate error, assignment projection,
   sampling failures and overhead. Compare against equally budgeted classical
   window search and no-QUBO repair. Retain a new QUBO change only if controlled
   validation supports it; do not tune until a preferred conclusion appears.
2. **Improve feasible construction independently.** Investigate TC15, TC16 and
   TC25 without treating heuristic failure as infeasibility. Apply any revised
   initialization equally across methods and rerun comparisons as a new version.
3. **Evaluate external validity.** Use independently held-out instances, a mature
   external VRP baseline, more sizes and constraints, and longer declared budgets.
   Current v2 evidence is mainly related supplied fixtures with very short budgets.
4. **Measure runtime tradeoffs.** Record actual time and atomic-action overruns;
   distinguish cache efficiency from better search using equally cached controls.
5. **Obtain Alphonsa's review.** Her current baseline was implemented for the role,
   rather than submitted by her. A later replacement needs preserved provenance.
6. **Build an online simulator before operational claims.** Live traffic updates,
   executed-prefix freezing, mid-route order insertion and breakdown rescue are
   not implemented/validated by this offline benchmark. Breakdown inputs currently
   use conservative whole-route invalidation when completion exceeds failure time.
7. **Replace synthetic operating assumptions when data exists.** Validate distance,
   fuel and cost estimates against an actual delivery setting before claiming
   real savings.

The defensible current conclusion is that v2 improves mean cost over the three
primary baselines on the stated supplied validation suite and budget. The results
do not prove general optimality or attribute the gain to quantum computation.

## 12. Recording future upgrades

Append a stage whenever an algorithm, model, dataset, interface, layout, or
evaluation changes. Update the current-state sections when an old description
no longer applies. Keep historical numbers associated with their original
version, protocol and source snapshot.

Use this template for the next entry:

```text
Stage / version:
Date and author:
Problem or motivation:
Files and behavior changed:
Preserved original / compatibility impact:
Tests and checks actually executed:
Experiment protocol and fresh output directory:
Measured results, failures and tradeoffs:
Limitations / work remaining:
Commit or source-manifest reference, if available:
```

Do not rewrite historical failures as successes, reuse old benchmark numbers for
changed solver code, or label a planned improvement as completed. The saved
protocols, manifests, raw runs, audits and archives remain the underlying evidence
for this consolidated record.
