# Alphonsa: classical simulated annealing

`classical_sa.py` is the newly implemented role baseline. It calls the shared
team evaluator and optimizer, using Metropolis acceptance, relocation across
vehicles, swaps, reversals, best-state retention, and reheating after stagnation.
No QUBO or quantum-inspired acceptance is used. Alphonsa's original code was not
present when this version was implemented; she can review or replace the search
implementation later while retaining the comparison contract.

See [the shared protocol](../../team_benchmark/README.md) for commands, assumptions,
constraints, and benchmark results.
