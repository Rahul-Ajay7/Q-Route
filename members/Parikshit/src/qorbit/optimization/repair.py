"""The repair loop shared by Direct SA and Q-ORBIT: score -> pick partition -> local solve ->
splice -> FULL-solution evaluation -> accept only if feasible and cheaper."""
import time
import numpy as np
from ..cost import Evaluator
from ..models import Solution
from .partition import generate_partitions
from .scorer import rank_partitions
from .splice import splice


def run_repair(sol0: Solution, ev0: Evaluator, ev1: Evaluator, solver, rng: np.random.Generator, *,
               k: int = 5, policy: str = "score", max_solves: int = 40, time_limit: float | None = None,
               retries: int = 2, eps: float = 1e-6):
    """ev0 = traffic before the event (used only to score pressure), ev1 = current traffic.
    Returns (final solution, rows). rows[0] is the damaged starting point."""
    t_start = time.perf_counter()
    cur = sol0.copy()
    cost = ev1.evaluate(cur).objective
    rows = [dict(step=0, elapsed_s=0.0, cost=cost, accepted=0, vehicle=-1, score=0.0, n_vars=0, repaired=0)]
    tries: dict = {}
    for step in range(1, max_solves + 1):
        if time_limit is not None and time.perf_counter() - t_start > time_limit:
            break
        key = lambda p: (p.vehicle_id, p.start, p.end, p.customers)
        if policy == "score":
            cands = [s for s in rank_partitions(cur, k, ev0, ev1) if tries.get(key(s.partition), 0) < retries]   # highest pressure first, then the rest
            if not cands:
                break
            pick, score = cands[0].partition, cands[0].total
        else:
            parts = [p for p in generate_partitions(cur, k) if tries.get(key(p), 0) < retries]
            if not parts:
                break
            pick, score = parts[int(rng.integers(len(parts)))], 0.0
        res = solver(cur, pick, ev1, rng)
        cand = splice(cur, pick, res.order)
        ev = ev1.evaluate(cand)
        accepted = int(ev.feasible and ev.objective < cost - 1e-9)
        if accepted:
            cur, cost = cand, ev.objective
            tries = {k_: v for k_, v in tries.items() if k_[0] != pick.vehicle_id}   # that route changed
        else:
            tries[key(pick)] = tries.get(key(pick), 0) + 1
        rows.append(dict(step=step, elapsed_s=time.perf_counter() - t_start, cost=cost, accepted=accepted,
                         vehicle=pick.vehicle_id, score=score, n_vars=res.n_vars, repaired=int(res.repaired)))
    return cur, rows
