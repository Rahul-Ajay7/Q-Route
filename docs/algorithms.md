# Algorithms

| Member / method | Implementation |
|---|---|
| Alphonsa / `classical_sa` | Metropolis SA with relocation, swap, reversal, best-state retention and reheating |
| Angel / `tunnelling_sa` | Preserved route proposals and tunnelling-inspired acceptance, adapted to the shared evaluator |
| Rahul / `qubo_sb` | Customer-position window QUBO solved by ballistic simulated bifurcation |
| Parikshit / `hybrid` | Global SA, regret-based cross-vehicle repair, adaptive QUBO calls, temporary exclusion, then further SA |

Construction uses nearest feasible neighbours, then up to eight feasible insertion
restarts if incomplete. It is a heuristic, and failure is not an infeasibility proof.

The local QUBO represents a bounded permutation of an existing route window.
Assignment penalties bound the whole valid surrogate cost. Time/load effects
are approximated; exact capacity, customer coverage and time windows are checked
after decoding. Capacity and all scheduling constraints are not fully encoded
inside the QUBO. Invalid assignment samples are projected to a one-to-one matching.

The hybrid defaults to classical binary QUBO SA. `--hybrid-backend sb` selects
Rahul's quantum-inspired mechanical sampler. All computation runs classically;
no quantum hardware execution or quantum advantage is demonstrated.

The v2 comparison includes an equally cached v1 hybrid, no-repair and no-QUBO
ablations. See [hybrid details and results](HYBRID_V2.md) and
[the model](methodology.md) for assumptions and validation limits.
