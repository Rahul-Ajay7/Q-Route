# Controlled team comparison

Exploratory offline benchmark. Lower INR cost is better. These results do not prove universal superiority.

Window policy: **hard**. Optimization budget: **0.5 seconds per run**; identical initial routes per case/seed.

Construction is shared and timed separately. Solver timing includes QUBO building, decoding, projection, and dynamic validation. Atomic actions may overrun the deadline; overruns are recorded.

Current methods share bounded route caching; hybrid_v1_cached uses the old search with the same cache, while hybrid_legacy retains the old uncached implementation. The revised hybrid adds regret-based cross-vehicle repair and adaptive refinement intervals. These are new runs; historical output files are not pooled.

| Method | Feasible / attempted | Mean improvement vs own shared initial (%) | Mean optimization seconds | Max budget overrun (s) |
|---|---:|---:|---:|---:|
| hybrid | 110 / 125 | 10.11 | 0.4405 | 0.0177 |
| hybrid_v1_cached | 110 / 125 | 7.15 | 0.4440 | 0.0346 |
| hybrid_no_qubo | 110 / 125 | 10.41 | 0.4401 | 0.0005 |
| hybrid_no_repair | 110 / 125 | 8.57 | 0.4403 | 0.0097 |
| classical_sa | 110 / 125 | 8.73 | 0.4401 | 0.0008 |
| tunnelling_sa | 110 / 125 | 9.09 | 0.4400 | 0.0002 |
| qubo_sb | 110 / 125 | 2.17 | 0.4412 | 0.0155 |

## Hybrid paired comparisons

Positive difference favours the hybrid. First average paired relative cost differences across seeds within each case; then compare cases. CI uses a case-level bootstrap; p-values use two-sided Wilcoxon and Holm correction across all comparisons.

| Against | Cases / paired seeds | Hybrid cost reduction % (95% CI) | Case wins / ties / losses | Holm p |
|---|---:|---:|---:|---:|
| classical_sa | 22 / 110 | 1.50 (0.84, 2.22) | 17 / 5 / 0 | 0.0009822 |
| hybrid_no_qubo | 22 / 110 | -0.41 (-1.04, 0.12) | 7 / 8 / 7 | 0.3627 |
| hybrid_no_repair | 22 / 110 | 1.66 (0.88, 2.56) | 18 / 4 / 0 | 0.0009822 |
| hybrid_v1_cached | 22 / 110 | 3.16 (1.96, 4.42) | 18 / 4 / 0 | 0.0009822 |
| qubo_sb | 22 / 110 | 8.12 (5.98, 10.30) | 20 / 2 / 0 | 0.0005314 |
| tunnelling_sa | 22 / 110 | 1.11 (0.60, 1.69) | 16 / 6 / 0 | 0.0009822 |

## Interpretation

This run supports lower mean hybrid cost against all three primary methods on this suite under this budget. Independent held-out instances and longer budgets are still required.

All reported feasible routes passed a separate accounting/constraint audit. Construction failures are NO_FEASIBLE_INITIAL_SOLUTION, not infeasibility proofs; partial-route costs are excluded from quality comparisons.

The paired table uses jointly feasible runs; see feasibility counts before interpreting it. Shared construction currently gives every method the same coverage failures. Hand-crafted related fixtures are not independent evidence of general performance; bootstrap intervals do not resolve dataset bias.

Traffic and orders are known offline. No live API, mid-route frozen prefix, breakdown rescue, or online order insertion is implemented. QUBO coefficients approximate time/load propagation and use full-route acceptance. Window reordering alone cannot change vehicle assignments; global SA can.

Angel's benchmark adapter reuses her original proposal code and tunnelling acceptance form with the common evaluator, initialization, and budget. It is not a rerun of her original standalone solver. QUBO+SA is a reference/ablation, not Angel's assigned method.

Results depend on wall-clock scheduling. Use max_actions with a generous seconds limit for deterministic debugging, not as an assertion of equal computational work.

## Invalid inputs (excluded, never silently repaired)

- TC14.json: Expecting value: line 1 column 1 (char 0)
