"""Local solvers: given a partition, propose a new ordering of its customers.
All return a LocalResult; acceptance is decided later by the full-solution evaluation."""
from dataclasses import dataclass
import math
import numpy as np
from ..config import QuboParams
from .qubo import build_qubo
from .qubo_decoder import decode
from .simulated_annealing import SAParams, anneal_qubo, _t0


@dataclass
class LocalResult:
    order: tuple
    n_vars: int = 0
    repaired: bool = False
    energy_evals: int = 0


def _propose(cur, rng):
    n = len(cur)
    c = list(cur)
    m = rng.integers(3)
    i, j = sorted(rng.choice(n, 2, replace=False))
    if m == 0:
        c[i], c[j] = c[j], c[i]
    elif m == 1:
        c[i:j + 1] = c[i:j + 1][::-1]
    else:
        c.insert(j, c.pop(i))
    return c


class DirectSA:
    """Baseline 3: same partitions, SA directly on the ordering, energy = TRUE route cost. No QUBO."""
    name = "direct_sa"

    def __init__(self, sa: SAParams = SAParams()):
        self.sa = sa

    def __call__(self, sol, part, ev, rng) -> LocalResult:
        veh = ev.inst.vehicles[part.vehicle_id]
        route = sol.routes[part.vehicle_id]
        pre, post = route[:part.start], route[part.end:]
        cost = lambda order: ev.evaluate_route(veh, pre + list(order) + post).total
        n = len(part.customers)
        best, best_e, evals = list(part.customers), cost(part.customers), 1
        for r in range(self.sa.restarts):
            cur = list(part.customers) if r == 0 else list(rng.permutation(part.customers))
            e = cost(cur); evals += 1
            probe = []
            for _ in range(20):
                probe.append(cost(_propose(cur, rng)) - e); evals += 1
            T = _t0(probe, self.sa.p_accept0)
            for _s in range(self.sa.sweeps):
                for _m in range(n):
                    cand = _propose(cur, rng)
                    e2 = cost(cand); evals += 1
                    d = e2 - e
                    if d <= 0 or rng.random() < math.exp(-d / T):
                        cur, e = cand, e2
                        if e < best_e - 1e-9:
                            best, best_e = cur[:], e
                T *= self.sa.cool
        return LocalResult(tuple(best), 0, False, evals)


class QuboSA:
    """Q-ORBIT local solver: build QUBO -> classical SA -> decode (Hungarian repair if invalid)."""
    def __init__(self, variant="flip", sa: SAParams | None = None, qp: QuboParams = QuboParams()):
        # plain bit-flip SA must climb penalty barriers between valid orderings, so it needs more
        # annealing (600 sweeps, slow cooling: optimal in 20/20 brute-force checks); swap moves do not.
        self.sa = sa or (SAParams(600, 10, 0.99) if variant == "flip" else SAParams(100, 4, 0.95))
        self.variant, self.qp = variant, qp
        self.name = f"qubo_{variant}"

    def __call__(self, sol, part, ev, rng) -> LocalResult:
        q = build_qubo(sol, part, ev, self.qp)
        x, _, nev = anneal_qubo(q, rng, self.sa, self.variant)
        order, repaired = decode(x, q)
        return LocalResult(order, q.n, repaired, nev)
