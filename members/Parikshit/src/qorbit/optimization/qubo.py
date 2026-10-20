"""Local QUBO for one partition.

Variables x[i,p] = 1 if partition customer i sits in slot p (index a = i*k + p).
Energy:  E(x) = diag.x + 0.5 x.W.x + const
  objective part : linearised leg costs (departure times taken from the CURRENT solution, load = 0
                   i.e. beta = 0 in the surrogate) + lambda_time * estimated lateness (diagonal)
  penalty part   : lam1 * sum_i (sum_p x_ip - 1)^2 + lam2 * sum_p (sum_i x_ip - 1)^2
All objective coefficients are divided by the largest one, so they lie in [0, 1] and lam = 1.5 is
always larger than the most any single violation could save.
The boundaries (customer before / after the window) stay fixed."""
from dataclasses import dataclass
import numpy as np
from ..config import QuboParams
from ..cost import Evaluator
from ..models import Solution
from .partition import Partition


@dataclass
class LocalQubo:
    customers: tuple
    k: int
    diag: np.ndarray
    W: np.ndarray
    const: float
    scale: float
    lin: np.ndarray      # [i, p]    normalised cost of customer i in slot p (entry leg / exit leg / lateness)
    pair: np.ndarray     # [i, j, p] normalised cost of leg i(slot p) -> j(slot p+1)

    @property
    def n(self) -> int:
        return self.k * self.k

    def energy(self, x: np.ndarray) -> float:
        return float(self.diag @ x + 0.5 * x @ self.W @ x + self.const)

    def x_from_order(self, order) -> np.ndarray:
        x = np.zeros(self.n)
        for p, c in enumerate(order):
            x[self.customers.index(c) * self.k + p] = 1.0
        return x

    def model_cost(self, order) -> float:
        """Normalised surrogate route cost of an ordering (what the QUBO minimises, without penalties)."""
        idx = [self.customers.index(c) for c in order]
        cost = sum(self.lin[i, p] for p, i in enumerate(idx))
        cost += sum(self.pair[idx[p], idx[p + 1], p] for p in range(self.k - 1))
        return float(cost)


def build_qubo(sol: Solution, part: Partition, ev: Evaluator, qp: QuboParams = QuboParams()) -> LocalQubo:
    inst, k = ev.inst, part.size
    route = sol.routes[part.vehicle_id]
    veh = inst.vehicles[part.vehicle_id]
    cap = veh.capacity
    prev = route[part.start - 1] if part.start > 0 else 0
    nxt = route[part.end] if part.end < len(route) else 0
    legs = ev.trace_route(veh, route)
    dep = [legs[part.start + p]["depart"] for p in range(k + 1)]     # dep[p]: departure from the node before slot p
    occupant = [prev] + list(route[part.start:part.end])             # occupant[p]: node before slot p (current solution)
    cs = part.customers

    lin = np.zeros((k, k))
    pair = np.zeros((k, k, max(k - 1, 1)))
    for i, c in enumerate(cs):
        cu = inst.customers[c]
        for p in range(k):
            v = 0.0
            if p == 0:
                v += ev.leg_cost(prev, c, dep[0], 0.0, cap)
            if p == k - 1:
                v += ev.leg_cost(c, nxt, dep[k], 0.0, cap)
            arr = dep[p] + ev.leg_time(occupant[p], c, dep[p])[0]
            v += qp.lambda_time * ev.p.lambda_late_per_hour * max(0.0, arr - cu.due)
            lin[i, p] = v
    for p in range(k - 1):
        for i, ci in enumerate(cs):
            for j, cj in enumerate(cs):
                if i != j:
                    pair[i, j, p] = ev.leg_cost(ci, cj, dep[p + 1], 0.0, cap)

    scale = max(np.abs(lin).max(), np.abs(pair).max(), 1e-9)
    lin, pair = lin / scale, pair / scale

    n = k * k
    diag = np.zeros(n)
    W = np.zeros((n, n))
    for i in range(k):
        for p in range(k):
            diag[i * k + p] += lin[i, p]
    for p in range(k - 1):
        for i in range(k):
            for j in range(k):
                if i != j:
                    a, b = i * k + p, j * k + p + 1
                    W[a, b] += pair[i, j, p]
                    W[b, a] += pair[i, j, p]
    l1, l2 = qp.lambda_assign, qp.lambda_position
    for i in range(k):                                  # each customer exactly once
        for p in range(k):
            diag[i * k + p] -= l1
            for q in range(p + 1, k):
                W[i * k + p, i * k + q] += 2 * l1
                W[i * k + q, i * k + p] += 2 * l1
    for p in range(k):                                  # each slot exactly one customer
        for i in range(k):
            diag[i * k + p] -= l2
            for j in range(i + 1, k):
                W[i * k + p, j * k + p] += 2 * l2
                W[j * k + p, i * k + p] += 2 * l2
    return LocalQubo(cs, k, diag, W, k * (l1 + l2), scale, lin, pair)
