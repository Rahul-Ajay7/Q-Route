"""Greedy insertion: customers taken in a fixed order, each inserted at the feasible
(vehicle, position) with the lowest incremental true cost."""
from ..cost import Evaluator
from ..models import ProblemInstance, Solution


def greedy_solve(inst: ProblemInstance, ev: Evaluator, hard_tw=None, unassigned: list | None = None) -> Solution:
    """hard_tw: True  -> only window-feasible insertions (raises if a customer has none)
                False -> windows are penalties (cheapest insertion by true cost)
                "prefer" -> window-feasible insertion when one exists, otherwise cheapest soft insertion
                None  -> follow ev.p.hard_time_windows.
    unassigned: if a list is passed, customers that cannot be placed are APPENDED to it (and left out of the
    routes) instead of raising. Callers must then report them; see optimization.initial.build_initial."""
    if hard_tw is None:
        hard_tw = ev.p.hard_time_windows
    routes = {v: [] for v in inst.vehicles}
    cost = {v: 0.0 for v in inst.vehicles}

    def trial(vid, route):
        rr = ev.evaluate_route(inst.vehicles[vid], route)
        if rr.cap_excess > 0:
            return None
        return rr.total, rr.late_h <= 1e-9

    # earliest deadline first; ties (e.g. no windows) -> farthest from depot first
    order = sorted(inst.customers, key=lambda c: (inst.customers[c].due, -inst.dist_km[0, c]))
    for c in order:
        best = None                                   # (late_flag, delta, vid, pos, new_cost)
        for vid in inst.vehicles:
            r = routes[vid]
            for pos in range(len(r) + 1):
                t = trial(vid, r[:pos] + [c] + r[pos:])
                if t is None:
                    continue
                total, on_time = t
                if hard_tw is True and not on_time:
                    continue
                late = 0 if (on_time or hard_tw != "prefer") else 1     # "prefer": on-time beats cheaper-but-late
                delta = total - cost[vid]
                if best is None or (late, delta) < (best[0], best[1] - 1e-12):
                    best = (late, delta, vid, pos, total)
        if best is None:
            if unassigned is not None:
                unassigned.append(c)
                continue
            raise RuntimeError(f"no feasible insertion for customer {c}; add vehicles or capacity")
        _, _, vid, pos, new = best
        routes[vid].insert(pos, c)
        cost[vid] = new
    return Solution(routes)
