# Controlled team comparison

Exploratory offline benchmark. Lower INR cost is better. These results do not prove universal superiority.

Window policy: **hard**. Optimization budget: **1.0 seconds per run**; identical initial routes per case/seed.

Construction is shared and timed separately. Solver timing includes QUBO building, decoding, projection, and dynamic validation. Atomic actions may overrun the deadline; overruns are recorded.

Current methods share bounded route caching; hybrid_v1_cached uses the old search with the same cache, while hybrid_legacy retains the old uncached implementation. The revised hybrid adds regret-based cross-vehicle repair and adaptive refinement intervals. These are new runs; historical output files are not pooled.

| Method | Feasible / attempted | Mean improvement vs own shared initial (%) | Mean optimization seconds | Max budget overrun (s) |
|---|---:|---:|---:|---:|
| classical_sa | 25 / 30 | 11.24 | 0.8335 | 0.0006 |
| tunnelling_sa | 25 / 30 | 13.55 | 0.8335 | 0.0004 |
| qubo_sb | 25 / 30 | 0.11 | 0.8340 | 0.0042 |
| hybrid | 25 / 30 | 13.95 | 0.8335 | 0.0002 |

## Hybrid paired comparisons

Positive difference favours the hybrid. First average paired relative cost differences across seeds within each case; then compare cases. CI uses a case-level bootstrap; p-values use two-sided Wilcoxon and Holm correction across all comparisons.

| Against | Cases / paired seeds | Hybrid cost reduction % (95% CI) | Case wins / ties / losses | Holm p |
|---|---:|---:|---:|---:|
| classical_sa | 5 / 25 | 3.18 (0.01, 6.59) | 4 / 0 / 1 | 0.625 |
| qubo_sb | 5 / 25 | 13.84 (7.26, 20.43) | 5 / 0 / 0 | 0.1875 |
| tunnelling_sa | 5 / 25 | 0.52 (-1.96, 3.08) | 3 / 0 / 2 | 0.8125 |

## Interpretation

This run does **not establish that the hybrid beats all three primary methods**. Report the tradeoffs and paired losses; do not claim an overall win.

All reported feasible routes passed a separate accounting/constraint audit. Construction failures are NO_FEASIBLE_INITIAL_SOLUTION, not infeasibility proofs; partial-route costs are excluded from quality comparisons.

The paired table uses jointly feasible runs; see feasibility counts before interpreting it. Shared construction currently gives every method the same coverage failures. Hand-crafted related fixtures are not independent evidence of general performance; bootstrap intervals do not resolve dataset bias.

Traffic and orders are known offline. No live API, mid-route frozen prefix, breakdown rescue, or online order insertion is implemented. QUBO coefficients approximate time/load propagation and use full-route acceptance. Window reordering alone cannot change vehicle assignments; global SA can.

Angel's benchmark adapter reuses her original proposal code and tunnelling acceptance form with the common evaluator, initialization, and budget. It is not a rerun of her original standalone solver. QUBO+SA is a reference/ablation, not Angel's assigned method.

Results depend on wall-clock scheduling. Use max_actions with a generous seconds limit for deterministic debugging, not as an assertion of equal computational work.
