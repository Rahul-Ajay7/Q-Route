# Controlled team comparison

Exploratory offline benchmark. Lower INR cost is better. These results do not prove universal superiority.

Window policy: **hard**. Optimization budget: **1.0 seconds per run**; identical initial routes per case/seed.

Construction is shared and timed separately. Solver timing includes QUBO building, decoding, projection, and dynamic validation. Atomic actions may overrun the deadline; overruns are recorded.

Current methods share bounded route caching; hybrid_v1_cached uses the old search with the same cache, while hybrid_legacy retains the old uncached implementation. The revised hybrid adds regret-based cross-vehicle repair and adaptive refinement intervals. These are new runs; historical output files are not pooled.

| Method | Feasible / attempted | Mean improvement vs own shared initial (%) | Mean optimization seconds | Max budget overrun (s) |
|---|---:|---:|---:|---:|
| classical_sa | 125 / 140 | 10.16 | 0.8929 | 0.0001 |
| tunnelling_sa | 125 / 140 | 10.27 | 0.8929 | 0.0002 |
| qubo_sb | 125 / 140 | 2.54 | 0.8934 | 0.0016 |
| hybrid | 125 / 140 | 11.11 | 0.8929 | 0.0079 |

## Hybrid paired comparisons

Positive difference favours the hybrid. First average paired relative cost differences across seeds within each case; then compare cases. CI uses a case-level bootstrap; p-values use two-sided Wilcoxon and Holm correction across all comparisons.

| Against | Cases / paired seeds | Hybrid cost reduction % (95% CI) | Case wins / ties / losses | Holm p |
|---|---:|---:|---:|---:|
| classical_sa | 25 / 125 | 1.02 (0.34, 1.95) | 12 / 10 / 3 | 0.006286 |
| qubo_sb | 25 / 125 | 8.79 (6.47, 11.10) | 22 / 3 / 0 | 0.0001203 |
| tunnelling_sa | 25 / 125 | 0.90 (0.21, 1.89) | 12 / 8 / 5 | 0.01477 |

## Interpretation

This run supports lower mean hybrid cost against all three primary methods on this suite under this budget. Independent held-out instances and longer budgets are still required.

All reported feasible routes passed a separate accounting/constraint audit. Construction failures are NO_FEASIBLE_INITIAL_SOLUTION, not infeasibility proofs; partial-route costs are excluded from quality comparisons.

The paired table uses jointly feasible runs; see feasibility counts before interpreting it. Shared construction currently gives every method the same coverage failures. Hand-crafted related fixtures are not independent evidence of general performance; bootstrap intervals do not resolve dataset bias.

Traffic and orders are known offline. No live API, mid-route frozen prefix, breakdown rescue, or online order insertion is implemented. QUBO coefficients approximate time/load propagation and use full-route acceptance. Window reordering alone cannot change vehicle assignments; global SA can.

Angel's benchmark adapter reuses her original proposal code and tunnelling acceptance form with the common evaluator, initialization, and budget. It is not a rerun of her original standalone solver. QUBO+SA is a reference/ablation, not Angel's assigned method.

Results depend on wall-clock scheduling. Use max_actions with a generous seconds limit for deterministic debugging, not as an assertion of equal computational work.

## Invalid inputs (excluded, never silently repaired)

- TC14.json: Expecting value: line 1 column 1 (char 0)
