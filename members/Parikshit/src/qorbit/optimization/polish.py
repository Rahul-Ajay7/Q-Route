"""Intra-route local search (2-opt reversal + relocate, first improvement) on the TRUE route cost.
Used to make the pre-event plan locally optimal, so that later 'recovery' measures the response to
traffic and does not reward fixing greedy's own inefficiencies."""
from ..cost import Evaluator
from ..models import Solution


def polish(sol: Solution, ev: Evaluator, hard_tw: bool = False) -> Solution:
    out = sol.copy()
    for vid, route in out.routes.items():
        if len(route) < 3:
            continue
        veh = ev.inst.vehicles[vid]
        r = list(route)
        base = ev.evaluate_route(veh, r)
        best, late0 = base.total, base.late_h
        improved = True
        while improved:
            improved = False
            n = len(r)
            cands = []
            for i in range(n):
                for j in range(i + 1, n):
                    cands.append(r[:i] + r[i:j + 1][::-1] + r[j + 1:])
                    c = r[:]; c.insert(j, c.pop(i)); cands.append(c)
                    c = r[:]; c.insert(i, c.pop(j)); cands.append(c)
            for c in cands:
                rr = ev.evaluate_route(veh, c)
                if rr.total < best - 1e-9 and (not hard_tw or rr.late_h <= late0 + 1e-9):
                    r, best, late0, improved = c, rr.total, rr.late_h, True
                    break
        out.routes[vid] = r
    return out


def polish_windows(sol: Solution, ev: Evaluator, k: int = 5, hard_tw: bool = False, max_passes: int = 10) -> Solution:
    """Make the plan optimal over EVERY ordering of EVERY k-window (exactly the neighbourhood the repair
    methods search). Afterwards, any gain under new traffic is caused by the traffic change."""
    import itertools
    from .partition import generate_partitions
    out = polish(sol, ev, hard_tw)
    for _ in range(max_passes):
        improved = False
        for part in generate_partitions(out, k):
            veh = ev.inst.vehicles[part.vehicle_id]
            route = out.routes[part.vehicle_id]
            pre, post, cur = route[:part.start], route[part.end:], route[part.start:part.end]
            base = ev.evaluate_route(veh, route)
            best, late0, best_order = base.total, base.late_h, cur
            for perm in itertools.permutations(cur):
                rr = ev.evaluate_route(veh, pre + list(perm) + post)
                if rr.total < best - 1e-9 and (not hard_tw or rr.late_h <= late0 + 1e-9):
                    best, best_order = rr.total, list(perm)
            if best_order != cur:
                out.routes[part.vehicle_id][part.start:part.end] = best_order
                improved = True
        if not improved:
            break
    return out
