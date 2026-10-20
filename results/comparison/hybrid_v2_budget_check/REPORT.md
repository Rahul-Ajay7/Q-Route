# Controlled team comparison

Exploratory offline benchmark. Lower INR cost is better. These results do not prove universal superiority.

Window policy: **hard**. Optimization budget: **1.0 seconds per run**; identical initial routes per case/seed.

Construction is shared and timed separately. Solver timing includes QUBO building, decoding, projection, and dynamic validation. Atomic actions may overrun the deadline; overruns are recorded.

Current methods share bounded route caching; hybrid_v1_cached uses the old search with the same cache, while hybrid_legacy retains the old uncached implementation. The revised hybrid adds regret-based cross-vehicle repair and adaptive refinement intervals. These are new runs; historical output files are not pooled.

| Method | Feasible / attempted | Mean improvement vs own shared initial (%) | Mean optimization seconds | Max budget overrun (s) |
|---|---:|---:|---:|---:|
| hybrid_v1_cached | 20 / 20 | 11.52 | 1.0000 | 0.0001 |
| hybrid_no_qubo | 20 / 20 | 13.59 | 1.0000 | 0.0001 |
| classical_sa | 20 / 20 | 12.06 | 1.0000 | 0.0001 |
| tunnelling_sa | 20 / 20 | 12.29 | 1.0000 | 0.0001 |
| qubo_sb | 20 / 20 | 2.05 | 1.0006 | 0.0019 |
| hybrid | 20 / 20 | 13.03 | 1.0000 | 0.0001 |

## Hybrid paired comparisons

Positive difference favours the hybrid. First average paired relative cost differences across seeds within each case; then compare cases. CI uses a case-level bootstrap; p-values use two-sided Wilcoxon and Holm correction across all comparisons.

| Against | Cases / paired seeds | Hybrid cost reduction % (95% CI) | Case wins / ties / losses | Holm p |
|---|---:|---:|---:|---:|
| classical_sa | 4 / 20 | 1.07 (0.13, 2.01) | 3 / 1 / 0 | 1 |
| hybrid_no_qubo | 4 / 20 | -0.67 (-1.36, -0.06) | 0 / 1 / 3 | 1 |
| hybrid_v1_cached | 4 / 20 | 1.71 (0.25, 3.85) | 3 / 1 / 0 | 1 |
| qubo_sb | 4 / 20 | 11.19 (5.84, 15.24) | 4 / 0 / 0 | 0.625 |
| tunnelling_sa | 4 / 20 | 0.81 (0.27, 1.18) | 3 / 1 / 0 | 1 |

## Interpretation

This run does **not establish that the hybrid beats all three primary methods**. Report the tradeoffs and paired losses; do not claim an overall win.

All reported feasible routes passed a separate accounting/constraint audit. Construction failures are NO_FEASIBLE_INITIAL_SOLUTION, not infeasibility proofs; partial-route costs are excluded from quality comparisons.

The paired table uses jointly feasible runs; see feasibility counts before interpreting it. Shared construction currently gives every method the same coverage failures. Hand-crafted related fixtures are not independent evidence of general performance; bootstrap intervals do not resolve dataset bias.

Traffic and orders are known offline. No live API, mid-route frozen prefix, breakdown rescue, or online order insertion is implemented. QUBO coefficients approximate time/load propagation and use full-route acceptance. Window reordering alone cannot change vehicle assignments; global SA can.

Angel's benchmark adapter reuses her original proposal code and tunnelling acceptance form with the common evaluator, initialization, and budget. It is not a rerun of her original standalone solver. QUBO+SA is a reference/ablation, not Angel's assigned method.

Results depend on wall-clock scheduling. Use max_actions with a generous seconds limit for deterministic debugging, not as an assertion of equal computational work.
