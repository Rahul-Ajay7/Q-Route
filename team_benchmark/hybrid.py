"""Adaptive global SA with bounded cross-vehicle repair and optional QUBO refinement."""
from dataclasses import asdict
import math
import time

import numpy as np

from .problem import sb


class RepairBudget:
    """Bound exact insertion evaluations and check the outer deadline frequently."""
    def __init__(self, deadline, max_evaluations=160):
        self.deadline = deadline
        self.remaining = max_evaluations

    def consume(self):
        if self.remaining <= 0 or time.perf_counter() >= self.deadline:
            return False
        self.remaining -= 1
        return True


def detour(problem, route, pos):
    c = route[pos]
    before = route[pos-1] if pos else problem.depot
    after = route[pos+1] if pos+1 < len(route) else problem.depot
    return problem.dist[before,c] + problem.dist[c,after] - problem.dist[before,after]


def insertion_options(problem, routes, c, budget):
    """Geometric shortlist, ranked finally by exact time/load-dependent route cost."""
    shortlist = []
    demand = problem.nodes[c].get("demand", 0)
    for vi, route in enumerate(routes):
        if sum(problem.nodes[x].get("demand",0) for x in route)+demand > problem.vehicles[vi]["capacity"]+1e-9:
            continue
        positions = []
        for pos in range(len(route)+1):
            a = route[pos-1] if pos else problem.depot
            b = route[pos] if pos < len(route) else problem.depot
            positions.append((problem.dist[a,c]+problem.dist[c,b]-problem.dist[a,b],pos))
        positions.sort()
        shortlist.append((positions[0][0],vi,positions[:3]))
    options = []
    for _, vi, positions in sorted(shortlist)[:4]:
        route = routes[vi]
        old = problem.route(vi,route)["cost"]
        for _,pos in positions:
            if not budget.consume():
                return None
            candidate = route[:pos]+[c]+route[pos:]
            detail = problem.route(vi,candidate)
            if detail["feasible"]:
                options.append((detail["cost"]-old,vi,pos))
    return sorted(options)


def destroy_repair(problem, routes, removed, deadline, max_evaluations=160):
    """Regret-2 insertion across vehicles; return no candidate on any interruption.

    Partial solutions never reach the solver's best state. Only the original
    customer set is removed and reinserted; boundaries/vehicle membership may change.
    """
    if len(set(removed)) != len(removed) or not set(removed) <= set(problem.ids):
        raise ValueError("Removed IDs must be distinct known customers")
    selected = set(removed)
    trial = [[c for c in route if c not in selected] for route in routes]
    pending = list(removed)
    budget = RepairBudget(deadline,max_evaluations)
    while pending:
        choices = []
        for c in pending:
            options = insertion_options(problem,trial,c,budget)
            if options is None or not options:
                return None
            regret = options[1][0]-options[0][0] if len(options)>1 else math.inf
            choices.append((regret,-options[0][0],c,options[0]))
        _,_,c,(_,vi,pos) = max(choices)
        trial[vi].insert(pos,c)
        pending.remove(c)
    return trial if problem.evaluate(trial)["feasible"] else None


def repair_customers(problem, routes, k, excluded, rng, cycle):
    eligible = [(vi,r) for vi,r in enumerate(routes) if r and not set(r)&excluded and len(r)<=k]
    # Periodically try eliminating a short route, including its fixed vehicle cost.
    if eligible and cycle % 3 == 0:
        _,r = min(eligible,key=lambda x:(len(x[1]),x[0]))
        return r[:]
    ranked = sorted(((detour(problem,r,i),c) for r in routes for i,c in enumerate(r)
                     if c not in excluded), reverse=True)
    if not ranked:
        return []
    # Mix expensive detours with a geographic neighbourhood of an expensive customer.
    anchor = ranked[int(rng.integers(min(3,len(ranked))))][1]
    pool = [c for _,c in ranked[:max(k*2,k)]]
    pool.sort(key=lambda c:(problem.dist[anchor,c],c))
    return pool[:min(k,len(pool))]


def select_repair_window(problem, routes, k, excluded, attempted, rng, random_selection=False):
    candidates = []
    for vi,r in enumerate(routes):
        for start in range(len(r)-1):
            end = start
            while end < min(len(r),start+k) and r[end] not in excluded:
                end += 1
            if end-start < 2 or (vi,tuple(r[start:end])) in attempted:
                continue
            # Avoidable geometric detour, rather than total route size/cost.
            score = sum(detour(problem,r,i) for i in range(start,end))
            candidates.append((score,vi,start,end))
    if not candidates:
        return None
    pick = candidates[int(rng.integers(len(candidates)))] if random_selection else max(candidates)
    return pick[1:]


def solve_adaptive(problem, initial, method, seed, cfg):
    # Import lazily to keep the legacy/reference implementation independently callable.
    from .solvers import neighbor, build_qubo
    rng = np.random.default_rng(seed)
    started = time.perf_counter()
    deadline = started+cfg.seconds
    score = problem.evaluate(initial)
    if not score["feasible"]:
        return dict(method=method,status="NO_FEASIBLE_INITIAL_SOLUTION",seed=seed,
                    routes=[r[:] for r in initial],cost=None,feasible=False,issues=score["issues"],
                    runtime_seconds=time.perf_counter()-started,settings=asdict(cfg),history=[])
    current = [r[:] for r in initial]
    best = [r[:] for r in initial]
    current_cost = best_cost = score["cost"]
    history = [dict(seconds=0.0,cost=best_cost,action="initial")]
    stats = dict(actions=0,route_evaluations=0,sa_moves=0,qubo_calls=0,raw_valid=0,projected=0,
                 accepted_qubo=0,hybrid_cycles=0,max_action_seconds=0.0,repair_calls=0,
                 accepted_repairs=0,qubo_failures=0,repair_seconds=0.0,qubo_seconds=0.0,
                 surrogate_candidates=0,surrogate_infeasible=0)
    temp0 = max(1.0,best_cost/max(1,len(problem.ids))*0.2)
    temp = temp0
    stale = cycle = 0
    interval = cfg.plateau*3
    next_qubo_cycle = 0
    qubo_failure_streak = 0
    tabu, attempted, selections = {},set(),[]
    surrogate_observations = []

    def record(routes,cost,action):
        nonlocal best,best_cost,stale
        if cost < best_cost-1e-9:
            best,best_cost = [r[:] for r in routes],cost
            stale = 0
            history.append(dict(seconds=time.perf_counter()-started,cost=cost,action=action))

    while stats["actions"] < cfg.max_actions and time.perf_counter() < deadline:
        begin = time.perf_counter()
        stats["actions"] += 1
        if stale >= interval and cycle < cfg.cycles:
            current,current_cost = [r[:] for r in best],best_cost
            prior = best_cost
            excluded = {c for c,expiry in tabu.items() if expiry>cycle}
            selected = []
            if method != "hybrid_no_repair":
                removed = repair_customers(problem,current,cfg.window,excluded,rng,cycle)
                if removed:
                    repair_begin = time.perf_counter()
                    stats["repair_calls"] += 1
                    candidate = destroy_repair(problem,current,removed,deadline)
                    selected.extend(removed)
                    if candidate is not None:
                        value = problem.evaluate(candidate)
                        if value["cost"] < current_cost-1e-9:
                            current,current_cost = candidate,value["cost"]
                            stats["accepted_repairs"] += 1
                            record(current,current_cost,"repair")
                    stats["repair_seconds"] += time.perf_counter()-repair_begin
            if (method != "hybrid_no_qubo" and cycle>=next_qubo_cycle
                    and time.perf_counter()<deadline):
                pick = select_repair_window(problem,current,cfg.window,excluded,attempted,rng,
                                             method=="hybrid_random")
                if pick is None and attempted:
                    attempted.clear()
                    pick = select_repair_window(problem,current,cfg.window,excluded,attempted,rng,
                                                 method=="hybrid_random")
                if pick is not None:
                    qubo_begin = time.perf_counter()
                    vi,start,end = pick
                    q,_,block = build_qubo(problem,current,vi,start,end)
                    attempted.add((vi,tuple(block)))
                    selections.append(dict(cycle=cycle,customers=block[:],excluded=sorted(excluded)))
                    selected.extend(block)
                    warm = np.eye(len(block)).ravel()
                    backend = sb.solve_sb if cfg.hybrid_backend=="sb" else sb.solve_sa
                    stats["qubo_calls"] += 1
                    bits,scores = backend(q,cfg.samples,cfg.qubo_steps,rng,warm)
                    orders = []
                    for binary,values in zip(bits,scores):
                        order = sb.decode(binary,len(block))
                        if order is None:
                            order = sb.project(values,len(block))
                            stats["projected"] += 1
                        else:
                            stats["raw_valid"] += 1
                        orders.append(tuple(order))
                    before = current_cost
                    warm_energy = float(warm@q@warm)
                    for order in dict.fromkeys(orders):
                        # Bound sampler output validation as well as the search loop.
                        if time.perf_counter()>=deadline:
                            break
                        candidate = [r[:] for r in current]
                        candidate[vi][start:end] = [block[i] for i in order]
                        value = problem.evaluate(candidate)
                        assignment = np.zeros((len(block),len(block)))
                        for pos,i in enumerate(order):
                            assignment[i,pos] = 1
                        x = assignment.ravel()
                        surrogate_observations.append(dict(predicted_gain=warm_energy-float(x@q@x),
                                                           actual_gain=before-value["cost"] if value["feasible"] else None,
                                                           feasible=value["feasible"]))
                        stats["surrogate_candidates"] += 1
                        stats["surrogate_infeasible"] += int(not value["feasible"])
                        stats["route_evaluations"] += len(candidate)
                        if value["feasible"] and value["cost"] < current_cost-1e-9:
                            current,current_cost = candidate,value["cost"]
                            stats["accepted_qubo"] += 1
                            record(current,current_cost,"qubo")
                    if current_cost >= before-1e-9:
                        qubo_failure_streak += 1
                        stats["qubo_failures"] += 1
                    else:
                        qubo_failure_streak = 0
                    next_qubo_cycle = cycle+(1 if method=="hybrid_no_adaptation" else min(8,2**qubo_failure_streak))
                    stats["qubo_seconds"] += time.perf_counter()-qubo_begin
            if method != "hybrid_no_tabu":
                for c in selected:
                    tabu[c] = cycle+cfg.tabu_cycles+1
            if method != "hybrid_no_adaptation":
                interval = cfg.plateau*3 if best_cost<prior-1e-9 else min(cfg.plateau*24,interval*2)
            cycle += 1
            stats["hybrid_cycles"] = cycle
            stale = 0
            temp = temp0
        else:
            candidate = neighbor(current,rng)
            value = problem.evaluate(candidate)
            stats["route_evaluations"] += len(candidate)
            stats["sa_moves"] += 1
            delta = value["cost"]-current_cost
            if value["feasible"] and (delta<=0 or rng.random()<math.exp(-delta/max(temp,1e-9))):
                current,current_cost = candidate,value["cost"]
            stale += 1
            record(current,current_cost,"sa")
            temp = max(temp0*.001,temp*cfg.cooling)
            # Reheat after long stagnation even when the refinement cap is exhausted.
            if cycle>=cfg.cycles and stale>=interval:
                current,current_cost = [r[:] for r in best],best_cost
                temp,stale = temp0,0
        stats["max_action_seconds"] = max(stats["max_action_seconds"],time.perf_counter()-begin)
    elapsed = time.perf_counter()-started
    final = problem.evaluate(best)
    stats["refinement_interval_final"] = interval
    return dict(method=method,status="FEASIBLE",seed=seed,feasible=final["feasible"],cost=final["cost"],
                initial_cost=score["cost"],routes=best,
                metrics={k:final[k] for k in ("distance","travel_minutes","duration_minutes","fuel_liters","lateness_minutes")},
                runtime_seconds=elapsed,budget_overrun_seconds=max(0.0,elapsed-cfg.seconds),
                settings=asdict(cfg),stats=stats,history=history,selections=selections,
                implementation="adaptive-v2",surrogate_observations=surrogate_observations)
