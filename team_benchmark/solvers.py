"""Controlled team implementations; no winner-dependent tuning or fallback.

SA can change vehicle assignments. QUBO methods reorder bounded route windows.
Hybrid combines those two neighbourhoods when SA stops improving.
"""
from dataclasses import dataclass, asdict
import math
import time
import runpy

import numpy as np

from .problem import sb, ROOT

METHODS = ("classical_sa", "tunnelling_sa", "qubo_sb", "hybrid")
ABLATIONS = ("qubo_sa", "hybrid_no_tabu", "hybrid_random", "hybrid_no_qubo",
             "hybrid_legacy", "hybrid_v1_cached", "hybrid_no_repair", "hybrid_no_adaptation")


@dataclass(frozen=True)
class Settings:
    seconds: float = 1.0
    max_actions: int = 1000000
    window: int = 5
    samples: int = 8
    qubo_steps: int = 40
    plateau: int = 50
    tabu_cycles: int = 2
    cycles: int = 20
    cooling: float = 0.995
    hybrid_backend: str = "sa"

    def validate(self):
        if not math.isfinite(self.seconds) or self.seconds <= 0:
            raise ValueError("seconds must be finite and positive")
        if not 2 <= self.window <= 8:
            raise ValueError("window must be 2..8")
        if not 0 < self.cooling <= 1:
            raise ValueError("cooling must be in (0,1]")
        if any(getattr(self, k) < 1 for k in ("max_actions", "samples", "qubo_steps", "plateau", "cycles")):
            raise ValueError("Search limits must be positive")
        if self.tabu_cycles < 0:
            raise ValueError("tabu_cycles cannot be negative")
        if self.hybrid_backend not in ("sa", "sb"):
            raise ValueError("hybrid_backend must be sa or sb")


def neighbor(routes, rng):
    """Relocate (including to an unused vehicle), swap, or intra-route reversal."""
    candidate = [r[:] for r in routes]
    nonempty = [i for i, r in enumerate(candidate) if r]
    if not nonempty:
        return candidate
    a = int(rng.choice(nonempty))
    p = int(rng.integers(len(candidate[a])))
    op = int(rng.integers(3))
    if op == 0:
        c = candidate[a].pop(p)
        b = int(rng.integers(len(candidate)))
        q = int(rng.integers(len(candidate[b]) + 1))
        candidate[b].insert(q, c)
    elif op == 1:
        b = int(rng.choice(nonempty))
        q = int(rng.integers(len(candidate[b])))
        candidate[a][p], candidate[b][q] = candidate[b][q], candidate[a][p]
    else:
        q = int(rng.integers(len(candidate[a])))
        p, q = sorted((p, q))
        candidate[a][p:q + 1] = reversed(candidate[a][p:q + 1])
    return candidate


def select_window(problem, routes, k, excluded, rng, random_selection=False, attempted=None):
    """Worst monetary-cost route, then most costly eligible contiguous window.

    Exclusion is strict: a selected window cannot contain a tabu customer.
    Long routes are bounded to k customers to avoid quadratic variable growth.
    """
    candidates = []
    for vi, r in enumerate(routes):
        if len(r) < 2:
            continue
        detail = problem.route(vi, r)
        # Splitting into eligible contiguous runs allows selection while other customers are tabu.
        for start in range(len(r) - 1):
            if r[start] in excluded:
                continue
            end = start
            while end < min(len(r), start + k) and r[end] not in excluded:
                end += 1
            if end - start < 2:
                continue
            ids = r[start:end]
            if attempted is not None and (vi, tuple(ids)) in attempted:
                continue
            before = r[start - 1] if start else problem.depot
            after = r[end] if end < len(r) else problem.depot
            seq = [before] + ids + [after]
            pressure = sum(problem.dist[a, b] for a, b in zip(seq, seq[1:]))
            candidates.append((detail["cost"], pressure, vi, start, end))
    if not candidates:
        return None
    selected = candidates[int(rng.integers(len(candidates)))] if random_selection else max(candidates)
    return selected[2:]


def build_qubo(problem, routes, vi, start, end):
    """Frozen-time/load surrogate; full dynamic evaluation decides acceptance.

    Each valid permutation's energy equals its surrogate cost. A safe assignment
    penalty exceeds an upper bound on every feasible permutation's cost.
    Time-window propagation and changing load cannot be represented exactly by
    these pairwise coefficients; they are checked after decoding.
    """
    route = routes[vi]
    block = route[start:end]
    n = len(block)
    detail = problem.route(vi, route)
    departure = detail["departures"][start]
    before = route[start - 1] if start else problem.depot
    after = route[end] if end < len(route) else problem.depot
    p = problem.costs
    load = sum(problem.nodes[c].get("demand", 0) for c in route[start:])
    cap = max(problem.vehicles[vi]["capacity"], 1e-9)

    def edge(a, b):
        tt, wait, multiplier = problem.leg(a, b, departure)
        d = problem.dist[a, b]
        liters = d * p.liters_per_km * (1 + p.load_premium * load / cap) * (
            1 + p.congestion_premium * max(0, multiplier - 1))
        return d * p.distance_per_km + (tt + wait) * p.driver_per_minute + liters * p.fuel_per_liter

    edges = {(a, b): edge(a, b) for a in [before] + block for b in block + [after]}
    maximum = max([1.0] + [c for c in edges.values() if math.isfinite(c)])
    closure = (n + 1) * maximum * 10
    bounded = {ab: min(c, closure) for ab, c in edges.items()}
    lin = np.zeros((n, n))
    for i, c in enumerate(block):
        for pos in range(n):
            occupant = before if pos == 0 else block[pos-1]
            tt, wait, _ = problem.leg(occupant, c, detail["departures"][start+pos])
            arrival = detail["departures"][start+pos] + tt + wait
            service = max(arrival, problem.nodes[c].get("ready_time", 0), problem.release[c])
            extra = ((service-arrival)*p.driver_per_minute +
                     max(0.0, service-problem.nodes[c].get("due_time", math.inf))*p.late_per_minute)
            lin[i, pos] = min(extra, closure) if math.isfinite(extra) else closure
            if pos == 0:
                lin[i, pos] += bounded[before, c]
            if pos == n-1:
                lin[i, pos] += bounded[c, after]
    # Every valid assignment has n linear terms and n-1 nonnegative edge terms.
    # An invalid assignment incurs at least one penalty, even if its objective is zero.
    penalty = n*float(lin.max()) + (n-1)*max(bounded.values()) + 1
    q = np.zeros((n*n, n*n))
    groups = [[i*n+p for p in range(n)] for i in range(n)] + [
        [i*n+p for i in range(n)] for p in range(n)]
    for group in groups:
        q[group, group] -= penalty
        for a in group:
            for b in group:
                if a != b:
                    q[a, b] += penalty
    for i, c in enumerate(block):
        for pos in range(n):
            q[i*n+pos, i*n+pos] += lin[i, pos]
        for j, other in enumerate(block):
            if i == j:
                continue
            for pos in range(n - 1):
                a, b = i*n+pos, j*n+pos+1
                q[a, b] += bounded[c, other] / 2
                q[b, a] += bounded[c, other] / 2
    return q, 2*n*penalty, block


def solve_reference(problem, initial, method, seed=0, settings=None):
    if method not in METHODS + ABLATIONS:
        raise ValueError(f"Unknown method: {method}")
    cfg = settings or Settings()
    cfg.validate()
    rng = np.random.default_rng(seed)
    started = time.perf_counter()
    initial_score = problem.evaluate(initial)
    if not initial_score["feasible"]:
        return dict(method=method, status="NO_FEASIBLE_INITIAL_SOLUTION", seed=seed,
                    routes=[r[:] for r in initial], cost=None, feasible=False,
                    issues=initial_score["issues"], runtime_seconds=time.perf_counter()-started,
                    settings=asdict(cfg), history=[])
    current = [r[:] for r in initial]
    current_cost = initial_score["cost"]
    best = [r[:] for r in current]
    best_cost = current_cost
    history = [dict(seconds=0.0, cost=best_cost, action="initial")]
    stats = dict(actions=0, route_evaluations=0, sa_moves=0, qubo_calls=0,
                 raw_valid=0, projected=0, accepted_qubo=0, hybrid_cycles=0,
                 max_action_seconds=0.0)
    # Same objective-based temperature scale for the two global SA methods.
    temperature = max(1.0, best_cost / max(1, len(problem.ids)) * 0.2)
    initial_temperature = temperature
    angel = None
    if method == "tunnelling_sa":
        # Preserve the submitted source and reuse its move generator unchanged.
        cls = runpy.run_path(str(ROOT / "members/Angel/saq_cvrptw.py"))["SAQCVRPTW"]
        angel = cls(problem.data, seed=seed)
    stale = cycle = 0
    tabu = {}
    is_hybrid = method.startswith("hybrid")
    selections = []
    attempted = set()
    deadline = started + cfg.seconds
    while stats["actions"] < cfg.max_actions and time.perf_counter() < deadline:
        action_start = time.perf_counter()
        stats["actions"] += 1
        use_qubo = method in ("qubo_sa", "qubo_sb") or (
            is_hybrid and stale >= cfg.plateau and cycle < cfg.cycles)
        action = "sa"
        if use_qubo:
            # QUBO refinement starts from the best known complete solution.
            current, current_cost = [r[:] for r in best], best_cost
            excluded = {c for c, expiry in tabu.items() if expiry > cycle}
            pick = select_window(problem, current, cfg.window, excluded, rng,
                                 method == "hybrid_random", attempted)
            if pick is None and attempted:
                attempted.clear()
                pick = select_window(problem, current, cfg.window, excluded, rng,
                                     method == "hybrid_random", attempted)
            if pick is not None:
                vi, start, end = pick
                block = current[vi][start:end]
                attempted.add((vi, tuple(block)))
                selections.append(dict(cycle=cycle, customers=block[:], excluded=sorted(excluded)))
                if method == "hybrid_no_qubo":
                    # Same selection/reset trigger, but perturb with an ordinary permutation.
                    orders = [list(rng.permutation(len(block)))]
                    action = "restart"
                else:
                    q, _, block = build_qubo(problem, current, vi, start, end)
                    stats["qubo_calls"] += 1
                    backend = sb.solve_sb if method == "qubo_sb" else sb.solve_sa
                    bits, scores = backend(q, cfg.samples, cfg.qubo_steps, rng, np.eye(len(block)).ravel())
                    orders = []
                    for binary, score in zip(bits, scores):
                        order = sb.decode(binary, len(block))
                        if order is None:
                            order = sb.project(score, len(block))
                            stats["projected"] += 1
                        else:
                            stats["raw_valid"] += 1
                        orders.append(order)
                    action = "qubo"
                # Evaluate unique decoded candidates using the full physical objective.
                for order in dict.fromkeys(tuple(o) for o in orders):
                    candidate = [r[:] for r in current]
                    candidate[vi][start:end] = [block[i] for i in order]
                    detail = problem.evaluate(candidate)
                    stats["route_evaluations"] += len(candidate)
                    if detail["feasible"] and detail["cost"] < current_cost - 1e-9:
                        current, current_cost = candidate, detail["cost"]
                        stats["accepted_qubo"] += int(action == "qubo")
                if is_hybrid and method != "hybrid_no_tabu":
                    for c in block:
                        tabu[c] = cycle + cfg.tabu_cycles + 1
            cycle += 1
            stats["hybrid_cycles"] = cycle if is_hybrid else 0
            stale = 0
            temperature = initial_temperature
        else:
            if angel is not None:
                candidate, width = angel.proposal(current)
            else:
                candidate = neighbor(current, rng)
            detail = problem.evaluate(candidate)
            stats["route_evaluations"] += len(candidate)
            stats["sa_moves"] += 1
            delta = detail["cost"] - current_cost
            exponent = (-width * math.sqrt(max(0.0, delta) / max(temperature, 1e-9))
                        if angel is not None else -max(0.0, delta) / max(temperature, 1e-9))
            if detail["feasible"] and (delta <= 0 or rng.random() < math.exp(exponent)):
                current, current_cost = candidate, detail["cost"]
            temperature = max(initial_temperature * 0.001, temperature * cfg.cooling)
            stale += 1
            # Baseline SA also gets reheating after stagnation; avoid a frozen strawman.
            if method in ("classical_sa", "tunnelling_sa") and stale >= cfg.plateau:
                temperature = initial_temperature
                current, current_cost = [r[:] for r in best], best_cost
                stale = 0
        if current_cost < best_cost - 1e-9:
            best, best_cost = [r[:] for r in current], current_cost
            stale = 0
            history.append(dict(seconds=time.perf_counter()-started, cost=best_cost, action=action))
        stats["max_action_seconds"] = max(stats["max_action_seconds"], time.perf_counter()-action_start)
    elapsed = time.perf_counter()-started
    final = problem.evaluate(best)
    return dict(method=method, status="FEASIBLE", seed=seed, feasible=final["feasible"],
                cost=final["cost"], initial_cost=initial_score["cost"], routes=best,
                metrics={k: final[k] for k in ("distance", "travel_minutes", "duration_minutes",
                                              "fuel_liters", "lateness_minutes")},
                runtime_seconds=elapsed, budget_overrun_seconds=max(0.0, elapsed-cfg.seconds),
                settings=asdict(cfg), stats=stats, history=history, selections=selections)


def solve(problem, initial, method, seed=0, settings=None):
    """Apply the same route-cache optimization to all current methods.

    hybrid_legacy preserves the old full-fleet work; hybrid_v1_cached isolates
    the old search schedule with the same cache as every current baseline.
    """
    from .cached import CachedProblem
    from .hybrid import solve_adaptive
    if method not in METHODS+ABLATIONS:
        raise ValueError(f"Unknown method: {method}")
    cfg = settings or Settings()
    cfg.validate()
    base = "hybrid" if method in ("hybrid_legacy", "hybrid_v1_cached") else method
    working = problem if method=="hybrid_legacy" else CachedProblem(problem)
    if method.startswith("hybrid") and method not in ("hybrid_legacy", "hybrid_v1_cached"):
        result = solve_adaptive(working,initial,method,seed,cfg)
    else:
        result = solve_reference(working,initial,base,seed,cfg)
        result["implementation"] = "reference-v1"
    result["method"] = method
    if "stats" in result and isinstance(working,CachedProblem):
        result["stats"].update(route_simulations=working.route_simulations,
                               route_cache_hits=working.route_cache_hits)
    return result
