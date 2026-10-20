"""Standalone route-order QUBO benchmark. All paths stay inside this directory."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import os
from collections import Counter
from pathlib import Path
from time import perf_counter

# Small dense matrices benefit from one BLAS thread; set before importing NumPy.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np

ROOT = Path(__file__).resolve().parent
CASES = ROOT / "test_cases"
RESULTS = ROOT / "results"


def local_path(value):
    # Keep existing CLI filenames working while collecting outputs in results/.
    relative = Path(value)
    path = ((RESULTS if relative.parent == Path(".") else ROOT) / relative).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("All inputs and outputs must stay inside SB+QUBO")
    return path


def case_path(value):
    path = (CASES / value).resolve()
    if not path.is_relative_to(CASES.resolve()):
        raise ValueError("Case inputs must stay inside SB+QUBO/test_cases")
    return path


def load_case(path):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    depot = data["depot"]
    customers = data["customers"]
    nodes = [depot] + customers
    ids = [n["id"] for n in nodes]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate depot/customer IDs")
    matrix = np.asarray(data["base_travel_time_matrix"], dtype=float)
    if matrix.shape != (len(nodes), len(nodes)):
        raise ValueError("Travel matrix must follow [depot, customers in JSON order]")
    if not np.isfinite(matrix).all() or (matrix < 0).any():
        raise ValueError("Travel times must be finite and nonnegative")
    vehicles = data["vehicles"]
    if not vehicles or len({v["id"] for v in vehicles}) != len(vehicles):
        raise ValueError("Expected distinct vehicles")
    for n in nodes:
        values = [float(n.get(k, 0)) for k in
                  ("demand", "ready_time", "service_time")]
        due = float(n.get("due_time", math.inf))
        if not all(math.isfinite(v) and v >= 0 for v in values) or math.isnan(due):
            raise ValueError("Invalid demand or time-window values")
        if due < n.get("ready_time", 0):
            raise ValueError("Due time precedes ready time")
    for v in vehicles:
        if not math.isfinite(float(v["capacity"])) or v["capacity"] < 0:
            raise ValueError("Invalid capacity")
        if v.get("start_depot", depot["id"]) != depot["id"] or v.get(
                "end_depot", depot["id"]) != depot["id"]:
            raise ValueError("Only the supplied single depot is supported")
    for e in data.get("traffic_events", []):
        if e["from"] not in ids or e["to"] not in ids:
            raise ValueError("Traffic event references unknown node")
        m = e.get("multiplier")
        if m is not None and (not math.isfinite(float(m)) or m < 0):
            raise ValueError("Invalid traffic multiplier")
    data["_nodes"] = {n["id"]: n for n in nodes}
    data["_indices"] = {node_id: i for i, node_id in enumerate(ids)}
    data["_matrix"] = matrix
    return data


def travel(data, source, target, departure):
    multiplier = 1.0
    # Latest active event wins for this directed edge; closure is infinity.
    for event in sorted(data.get("traffic_events", []), key=lambda e: e["time"]):
        if (event["from"], event["to"]) == (source, target):
            if event["time"] <= departure < event.get("end_time", math.inf):
                multiplier = event.get("multiplier")
    if multiplier is None:
        return math.inf
    return float(data["_matrix"][data["_indices"][source],
                                 data["_indices"][target]]) * multiplier


def route_metrics(data, route):
    """Synthetic straight-line distance, including both depot legs."""
    depot = data["depot"]["id"]
    sequence = [depot] + list(route) + [depot] if route else []
    distance = sum(math.hypot(data["_nodes"][a]["x"] - data["_nodes"][b]["x"],
                              data["_nodes"][a]["y"] - data["_nodes"][b]["y"])
                   for a, b in zip(sequence, sequence[1:]))
    model = data.get("_fuel_model", {"km_per_unit": 1.0, "liters_per_100km": 10.0,
                                     "price_per_liter": 100.0, "currency": "INR"})
    km = distance * model["km_per_unit"]
    liters = km * model["liters_per_100km"] / 100
    return {"distance": distance, "distance_km": km, "estimated_fuel_liters": liters,
            "estimated_fuel_cost": liters * model["price_per_liter"]}


def objective_cost(data, travel_minutes, distance, fuel_cost):
    if data.get("_objective", "travel_time") == "travel_time":
        return travel_minutes
    weights = data.get("_weights", {"distance": .4, "travel_time": .4, "fuel": .2})
    return (weights["distance"] * distance + weights["travel_time"] * travel_minutes
            + weights["fuel"] * fuel_cost)


def edge_objective(data, source, target, departure):
    minutes = travel(data, source, target, departure)
    if not math.isfinite(minutes):
        return math.inf
    a, b = data["_nodes"][source], data["_nodes"][target]
    distance = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
    model = data.get("_fuel_model", {"km_per_unit": 1., "liters_per_100km": 10.,
                                     "price_per_liter": 100.})
    fuel = distance * model["km_per_unit"] * model["liters_per_100km"] / 100 * model["price_per_liter"]
    return objective_cost(data, minutes, distance, fuel)


def evaluate_route(data, vehicle, route):
    depot = data["depot"]
    clock = max(data.get("simulation", {}).get("start_time", 0),
                depot.get("ready_time", 0))
    cost, load, previous = 0.0, 0.0, depot["id"]
    starts = []
    issues = []
    releases = {e["customer_id"]: e["time"]
                for e in data.get("order_events", []) if e["type"] == "new_order"}
    for customer_id in route:
        node = data["_nodes"][customer_id]
        leg = travel(data, previous, customer_id, clock)
        if not math.isfinite(leg):
            return {"feasible": False, "cost": math.inf,
                    "issues": ["closed_edge"], "starts": starts, "end": math.inf,
                    "travel_minutes": math.inf, **route_metrics(data, route)}
        cost += leg
        clock = max(clock + leg, node.get("ready_time", 0),
                    node.get("release_time", 0), releases.get(customer_id, 0))
        starts.append(clock)
        if clock > node.get("due_time", math.inf) + 1e-9:
            issues.append("time_window")
        clock += node.get("service_time", 0)
        load += node.get("demand", 0)
        previous = customer_id
    if load > vehicle["capacity"] + 1e-9:
        issues.append("capacity")
    if route:
        leg = travel(data, previous, depot["id"], clock)
        clock += leg
        cost += leg
        if not math.isfinite(leg):
            issues.append("closed_edge")
    if clock > depot.get("due_time", math.inf) + 1e-9:
        issues.append("depot_due_time")
    for event in data.get("vehicle_events", []):
        if (route and event["vehicle_id"] == vehicle["id"] and
                event["type"] == "breakdown" and clock > event["time"]):
            issues.append("vehicle_breakdown_requires_reassignment")
    metrics = route_metrics(data, route)
    return {"feasible": not issues,
            "cost": objective_cost(data, cost, metrics["distance"], metrics["estimated_fuel_cost"]),
            "travel_minutes": cost, **metrics, "issues": sorted(set(issues)),
            "starts": starts, "end": clock}


def evaluate_solution(data, routes):
    served = [c for route in routes for c in route]
    expected = {c["id"] for c in data["customers"]}
    counts = Counter(served)
    unserved = sorted(expected - set(served))
    issues = []
    if len(routes) != len(data["vehicles"]):
        issues.append("vehicle_count")
    if unserved:
        issues.append("unserved_customers")
    if any(count != 1 for count in counts.values()) or set(served) - expected:
        issues.append("duplicate_or_unknown_customer")
    details = [evaluate_route(data, v, r)
               for v, r in zip(data["vehicles"], routes)]
    for detail in details:
        issues.extend(detail["issues"])
    return {"feasible": not issues, "cost": sum(d["cost"] for d in details),
            "unserved": unserved, "issues": sorted(set(issues)), "routes": details,
            **{key: sum(d[key] for d in details) for key in
               ("travel_minutes", "distance", "distance_km", "estimated_fuel_liters", "estimated_fuel_cost")}}


def greedy(data):
    remaining = {c["id"] for c in data["customers"]}
    routes = []
    for vehicle in data["vehicles"]:
        route = []
        while remaining:
            candidates = []
            for customer in sorted(remaining):
                result = evaluate_route(data, vehicle, route + [customer])
                if result["feasible"]:
                    candidates.append((result["cost"], customer))
            if not candidates:
                break
            _, chosen = min(candidates)
            route.append(chosen)
            remaining.remove(chosen)
        routes.append(route)
    return routes


def route_qubo(data, customers, before, after, departure, penalty_scale=1.0):
    """E=x.T Q x+offset; x[i,p] assigns customer i to position p."""
    n = len(customers)
    edge = lambda a, b: edge_objective(data, a, b, departure)
    costs = [edge(a, b) for a in [before] + customers
             for b in customers + [after]]
    finite = [v for v in costs if math.isfinite(v)]
    closure_cost = (n + 1) * max([1.0] + finite) * 10
    bounded = lambda a, b: min(edge(a, b), closure_cost)
    penalty = (n + 1) * max(closure_cost if any(
        not math.isfinite(v) for v in costs) else 1.0, max([1.0] + finite)) + 1
    if not math.isfinite(penalty_scale) or penalty_scale < 1:
        raise ValueError("penalty_scale must be finite and at least 1")
    penalty *= penalty_scale
    q = np.zeros((n * n, n * n))
    # A*(sum(x)-1)^2 for every customer and every position.
    for group in ([i * n + p for p in range(n)] for i in range(n)):
        q[group, group] -= penalty
        for a in group:
            for b in group:
                if a != b:
                    q[a, b] += penalty
    for group in ([i * n + p for i in range(n)] for p in range(n)):
        q[group, group] -= penalty
        for a in group:
            for b in group:
                if a != b:
                    q[a, b] += penalty
    for i, customer in enumerate(customers):
        q[i * n, i * n] += bounded(before, customer)
        q[i * n + n - 1, i * n + n - 1] += bounded(customer, after)
        for j, other in enumerate(customers):
            if i == j:
                continue
            for p in range(n - 1):
                a, b = i * n + p, j * n + p + 1
                q[a, b] += bounded(customer, other) / 2
                q[b, a] += bounded(customer, other) / 2
    return q, 2 * n * penalty


def qubo_to_ising(q):
    """x=(s+1)/2; E=constant+h.s+0.5*s.T K s."""
    off = q.copy()
    np.fill_diagonal(off, 0)
    k = off / 2
    h = q.sum(axis=1) / 2
    constant = (q.sum() + np.trace(q)) / 4
    return k, h, constant


def solve_sb(q, samples, steps, rng, warm, dt=0.2, coupling=1.0):
    """Ballistic SB, symplectic Euler, inelastic walls, auxiliary field spin."""
    k, h, _ = qubo_to_ising(q)
    # Minimize 0.5*s.K.s+h.s via maximize 0.5*z.J.z,
    # with s=z[:-1]*z[-1]. This makes linear fields exact.
    size = len(q)
    j = np.zeros((size + 1, size + 1))
    j[:size, :size] = -k
    j[:size, size] = -h
    j[size, :size] = -h
    j /= max(float(np.linalg.norm(j, ord=2)), 1e-12)
    x = rng.uniform(-0.1, 0.1, (samples, size + 1))
    y = rng.uniform(-0.1, 0.1, x.shape)
    x[0, :-1] = (2 * warm - 1) * 0.1
    x[0, -1] = 0.1
    if not math.isfinite(dt) or not 0 < dt <= 0.5:
        raise ValueError("SB time step must be in (0, 0.5]")
    if not math.isfinite(coupling) or not 0 < coupling <= 2:
        raise ValueError("SB coupling must be in (0, 2]")
    for step in range(steps):
        pump = step / max(1, steps - 1)
        y += dt * (-(1 - pump) * x + coupling * (x @ j))
        x += dt * y
        hit = np.abs(x) > 1
        x[hit] = np.sign(x[hit])
        y[hit] = 0
    scores = x[:, :-1] * np.where(x[:, -1:] >= 0, 1, -1)
    return (scores >= 0).astype(np.int8), scores


def solve_sa(q, samples, steps, rng, warm):
    """Binary single-flip Metropolis SA on precisely the same QUBO."""
    size = len(q)
    x = rng.integers(0, 2, (samples, size)).astype(float)
    x[0] = warm
    best = x.copy()
    energy = np.einsum("bi,ij,bj->b", x, q, x)
    best_energy = energy.copy()
    fields = x @ q
    diag = np.diag(q)
    scale = max(1.0, float(np.max(np.abs(q))))
    for step in range(steps):
        temperature = scale * 2 * (0.005 ** (step / max(1, steps - 1)))
        # A sweep attempts one flip per variable per replica.
        for bit in rng.permutation(size):
            change = 1 - 2 * x[:, bit]
            delta = 2 * change * fields[:, bit] + diag[bit]
            accept = (delta <= 0) | (rng.random(samples) <
                                    np.exp(-np.maximum(delta, 0) / temperature))
            actual = change * accept
            x[:, bit] += actual
            energy += delta * accept
            fields += actual[:, None] * q[bit]
        improved = energy < best_energy
        best[improved] = x[improved]
        best_energy[improved] = energy[improved]
    return best.astype(np.int8), best


def decode(bits, n):
    matrix = np.asarray(bits).reshape(n, n)
    if np.all(matrix.sum(axis=0) == 1) and np.all(matrix.sum(axis=1) == 1):
        return list(np.argmax(matrix, axis=0))
    return None


def project(scores, n):
    """Maximum-score one-to-one assignment by DP; does not solve route cost."""
    matrix = np.asarray(scores).reshape(n, n)
    dp = {0: (0.0, [])}
    for position in range(n):
        next_dp = {}
        for mask, (score, order) in dp.items():
            for customer in range(n):
                if mask & (1 << customer):
                    continue
                new_mask = mask | (1 << customer)
                value = score + matrix[customer, position]
                if new_mask not in next_dp or value > next_dp[new_mask][0]:
                    next_dp[new_mask] = (value, order + [customer])
        dp = next_dp
    return dp[(1 << n) - 1][1]


def build_model(data, route, vehicle_index, start, chunk_size, penalty_scale=1.0):
    """Build from the current order and current prefix departure time."""
    block = route[start:start + chunk_size]
    if len(block) < 2:
        return None
    detail = evaluate_route(data, data["vehicles"][vehicle_index], route)
    before = route[start - 1] if start else data["depot"]["id"]
    end = start + len(block)
    after = route[end] if end < len(route) else data["depot"]["id"]
    departure = (detail["starts"][start - 1] +
                 data["_nodes"][before].get("service_time", 0)) if start else max(
                     data.get("simulation", {}).get("start_time", 0),
                     data["depot"].get("ready_time", 0))
    q, offset = route_qubo(data, block, before, after, departure, penalty_scale)
    return vehicle_index, start, block, q, offset


def block_starts(length, chunk_size, stride):
    """Include a full trailing window instead of a singleton remainder."""
    if length < 2:
        return []
    if length <= chunk_size:
        return [0]
    return sorted(set(range(0, length - chunk_size + 1, stride)) |
                  {length - chunk_size})


def prepare_models(data, routes, chunk_size, penalty_scale=1.0):
    models = []
    for vehicle_index, route in enumerate(routes):
        for start in range(0, len(route), chunk_size):
            model = build_model(data, route, vehicle_index, start, chunk_size, penalty_scale)
            if model is not None:
                models.append(model)
    return models


def optimize(data, baseline, models, method, samples, steps, seed, *,
             chunk_size=5, stride=None, passes=1, restarts=1,
             sb_dt=0.2, sb_coupling=1.0, penalty_scale=1.0):
    routes = [r.copy() for r in baseline]
    if method not in ("SB", "SA"):
        raise ValueError("Unknown solver")
    stats = {"subproblems": 0, "raw_valid_samples": 0,
             "projected_samples": 0, "accepted_blocks": 0,
             "solver_calls": 0, "rejected_infeasible_candidates": 0,
             "adaptive_passes_completed": 0, "rebuilt_qubos": 0}

    def apply_model(model, rng, repeats):
        vehicle_index, start, block, q, _ = model
        stats["subproblems"] += 1
        n = len(block)
        warm = np.eye(n).reshape(-1)
        current = evaluate_route(data, data["vehicles"][vehicle_index],
                                 routes[vehicle_index])
        candidates = []
        for _ in range(repeats):
            stats["solver_calls"] += 1
            if method == "SB":
                bits, scores = solve_sb(q, samples, steps, rng, warm, sb_dt, sb_coupling)
            else:
                bits, scores = solve_sa(q, samples, steps, rng, warm)
            for binary, score in zip(bits, scores):
                order = decode(binary, n)
                if order is None:
                    stats["projected_samples"] += 1
                    order = project(score, n)
                else:
                    stats["raw_valid_samples"] += 1
                candidates.append(order)
        # Repeated orders from replicas/restarts need only one full validation.
        for order in dict.fromkeys(tuple(order) for order in candidates):
            candidate = routes[vehicle_index].copy()
            candidate[start:start + n] = [block[i] for i in order]
            result = evaluate_route(data, data["vehicles"][vehicle_index], candidate)
            if not result["feasible"]:
                stats["rejected_infeasible_candidates"] += 1
            if result["feasible"] and result["cost"] < current["cost"] - 1e-9:
                routes[vehicle_index] = candidate
                current = result
                stats["accepted_blocks"] += 1

    # Preserve the original disjoint-block pass and its seeded random stream.
    rng = np.random.default_rng(seed)
    for model in models:
        apply_model(model, rng, 1)
    reference = evaluate_solution(data, routes)
    stats["reference_travel_minutes"] = reference["travel_minutes"]
    stats["reference_objective_cost"] = reference["cost"]
    if stride is not None:
        for pass_index in range(passes):
            previous_accepts = stats["accepted_blocks"]
            for vehicle_index, route in enumerate(routes):
                starts = block_starts(len(route), chunk_size, stride)
                if pass_index % 2:
                    starts.reverse()
                for start in starts:
                    # Overlapping windows must use CURRENT IDs, not baseline IDs.
                    model = build_model(data, routes[vehicle_index], vehicle_index,
                                        start, chunk_size, penalty_scale)
                    stats["rebuilt_qubos"] += 1
                    # Separate restart streams, reproducible from base seed + window.
                    for restart in range(restarts):
                        rng = np.random.default_rng(np.random.SeedSequence(
                            [seed, pass_index + 1, vehicle_index, start, restart]))
                        apply_model(model, rng, 1)
            stats["adaptive_passes_completed"] += 1
            if stats["accepted_blocks"] == previous_accepts:
                break
    count = stats["raw_valid_samples"] + stats["projected_samples"]
    stats["raw_valid_percent"] = 100 * stats["raw_valid_samples"] / count if count else 0.0
    return routes, stats


def case_notes(data, filename):
    notes = []
    if data.get("id") != filename.stem:
        notes.append("filename differs from internal case ID")
    if data.get("prediction_file"):
        notes.append("forecast CSV not used; actual traffic_events evaluated")
    if data.get("order_events"):
        notes.append("offline release-time validation; no online new-order replanning")
    if data.get("vehicle_events"):
        notes.append("breakdown checked; no online reassignment")
    notes.append("QUBO costs frozen within a solve; overlapping windows rebuilt from current routes")
    return "; ".join(notes)


def benchmark(path, args):
    try:
        data = load_case(path)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        return [{"source_file": path.name, "case_id": "", "algorithm": "INPUT",
                 "status": "invalid_input", "feasible": False, "notes": str(exc)}], None
    data["_objective"] = args.objective
    data["_weights"] = {"distance": args.distance_weight, "travel_time": args.time_weight, "fuel": args.fuel_weight}
    data["_fuel_model"] = {"km_per_unit": args.km_per_unit, "liters_per_100km": args.liters_per_100km,
                           "price_per_liter": args.fuel_price, "currency": args.currency}
    start = perf_counter()
    baseline = greedy(data)
    greedy_seconds = perf_counter() - start
    start = perf_counter()
    models = prepare_models(data, baseline, args.chunk_size, args.penalty_scale)
    model_seconds = perf_counter() - start
    baseline_eval = evaluate_solution(data, baseline)
    rows, route_output = [], {}
    case_seed = args.seed + int.from_bytes(
        hashlib.sha256(path.name.encode()).digest()[:4], "big")
    for method in ("GREEDY", "SB", "SA"):
        start = perf_counter()
        if method == "GREEDY":
            routes, stats = baseline, {}
            solver_seconds = 0.0
        else:
            routes, stats = optimize(data, baseline, models, method,
                                     args.samples, args.steps, case_seed,
                                     chunk_size=args.chunk_size, stride=args.stride,
                                     passes=args.passes, restarts=args.restarts,
                                     sb_dt=args.sb_dt, sb_coupling=args.sb_coupling,
                                     penalty_scale=args.penalty_scale)
            solver_seconds = perf_counter() - start
        result = evaluate_solution(data, routes)
        improved = baseline_eval["cost"] - result["cost"]
        rows.append({
            "source_file": path.name, "case_id": data.get("id", ""),
            "title": data.get("title", ""), "algorithm": method,
            "status": "feasible" if result["feasible"] else "incomplete_or_infeasible",
            "feasible": result["feasible"], "customers": len(data["customers"]),
            "served": sum(map(len, routes)), "unserved_ids": json.dumps(result["unserved"]),
            "vehicles_used": sum(bool(r) for r in routes),
            "initial_travel_minutes": baseline_eval["travel_minutes"],
            "final_travel_minutes": result["travel_minutes"],
            "improvement_minutes": baseline_eval["travel_minutes"] - result["travel_minutes"],
            "initial_objective_cost": baseline_eval["cost"], "objective_cost": result["cost"],
            "objective_improvement": improved, "objective": args.objective,
            "distance": result["distance"], "distance_unit": data.get("units", {}).get("distance", "coordinate_units"),
            "distance_km": result["distance_km"], "estimated_fuel_liters": result["estimated_fuel_liters"],
            "estimated_fuel_cost": result["estimated_fuel_cost"],
            **data["_fuel_model"], **{k + "_weight": v for k, v in data["_weights"].items()},
            "greedy_seconds": greedy_seconds,
            "qubo_seconds": 0 if method == "GREEDY" else model_seconds,
            "solver_decode_seconds": solver_seconds,
            "total_seconds": greedy_seconds + (
                0 if method == "GREEDY" else model_seconds + solver_seconds),
            "seed": args.seed, "effective_case_seed": case_seed,
            "samples": args.samples, "steps": args.steps,
            "chunk_size": args.chunk_size, "stride": args.stride,
            "passes": args.passes, "restarts": args.restarts,
            "sb_dt": args.sb_dt, "sb_coupling": args.sb_coupling,
            "penalty_scale": args.penalty_scale, **stats,
            "issues": "; ".join(result["issues"]), "notes": case_notes(data, path)})
        route_output[method] = {"routes": [
            {"vehicle_id": v["id"], "customers": r, **detail}
            for v, r, detail in zip(data["vehicles"], routes, result["routes"])],
            "unserved_ids": result["unserved"], "feasible": result["feasible"]}
    return rows, {"source_file": path.name, "case_id": data.get("id"),
                  "objective": data["_objective"], "weights": data["_weights"],
                  "fuel_model": data["_fuel_model"], "distance_model": "synthetic Euclidean coordinates; km conversion is an assumption",
                  "algorithms": route_output}


def json_safe(value):
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--case", help="Source filename/stem, e.g. TC03 (internal TC01)")
    selection.add_argument("--all", action="store_true")
    parser.add_argument("--objective", choices=("weighted", "travel_time"), default="weighted")
    parser.add_argument("--distance-weight", type=float, default=.4)
    parser.add_argument("--time-weight", type=float, default=.4)
    parser.add_argument("--fuel-weight", type=float, default=.2)
    parser.add_argument("--km-per-unit", type=float, default=1., help="Assumed km per synthetic coordinate unit")
    parser.add_argument("--liters-per-100km", type=float, default=10., help="Example constant consumption assumption")
    parser.add_argument("--fuel-price", type=float, default=100., help="Example price per liter")
    parser.add_argument("--currency", default="INR")
    parser.add_argument("--chunk-size", type=int, default=5)
    parser.add_argument("--samples", type=int, default=16)
    parser.add_argument("--steps", type=int, default=200,
                        help="SB integration steps / SA sweeps (different work per step)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--stride", type=int, default=2,
                        help="Distance between overlapping window starts")
    parser.add_argument("--passes", type=int, default=2,
                        help="Adaptive passes after the original pass; 0 reproduces original search")
    parser.add_argument("--restarts", type=int, default=3,
                        help="Independent seeded solves per adaptive window, for both SB and SA")
    parser.add_argument("--sb-dt", type=float, default=0.2)
    parser.add_argument("--sb-coupling", type=float, default=1.0)
    parser.add_argument("--penalty-scale", type=float, default=1.0,
                        help="Multiplier >=1 retains the assignment penalty bound")
    parser.add_argument("--output", default="sb_results.csv")
    parser.add_argument("--routes-output", default="sb_routes.json")
    parser.add_argument("--no-write", action="store_true", help="Read-only smoke run")
    args = parser.parse_args()
    values = (args.distance_weight, args.time_weight, args.fuel_weight,
              args.km_per_unit, args.liters_per_100km, args.fuel_price)
    if not all(math.isfinite(v) and v >= 0 for v in values) or args.km_per_unit <= 0:
        parser.error("Weights and fuel parameters must be finite and nonnegative; km-per-unit must be positive")
    if args.objective == "weighted" and sum(values[:3]) <= 0:
        parser.error("At least one objective weight must be positive")
    if not 2 <= args.chunk_size <= 8 or args.samples < 1 or args.steps < 1 or args.seed < 0:
        parser.error("chunk-size must be 2..8; samples/steps positive; seed nonnegative")
    if not 1 <= args.stride <= args.chunk_size or args.passes < 0 or args.restarts < 1:
        parser.error("stride must be 1..chunk-size; passes nonnegative; restarts positive")
    if not math.isfinite(args.sb_dt) or not 0 < args.sb_dt <= 0.5:
        parser.error("sb-dt must be finite and in (0, 0.5]")
    if not math.isfinite(args.sb_coupling) or not 0 < args.sb_coupling <= 2:
        parser.error("sb-coupling must be finite and in (0, 2]")
    if not math.isfinite(args.penalty_scale) or args.penalty_scale < 1:
        parser.error("penalty-scale must be finite and >=1")
    try:
        output, route_output = local_path(args.output), local_path(args.routes_output)
        if output == route_output or output.suffix.lower() != ".csv" or route_output.suffix.lower() != ".json":
            raise ValueError("Use distinct CSV and JSON output paths")
        files = sorted(CASES.glob("TC[0-9][0-9].json")) if args.all else [
            case_path(args.case if args.case.endswith(".json") else args.case + ".json")]
        inputs = {p.resolve() for p in CASES.glob("TC[0-9][0-9].json")}
        if output in inputs or route_output in inputs:
            raise ValueError("Outputs cannot overwrite input test cases")
    except ValueError as exc:
        parser.error(str(exc))
    if not files:
        parser.error("No test-case files found")
    rows, details = [], []
    invalid = 0
    for path in files:
        result, detail = benchmark(path, args)
        rows.extend(result)
        if detail:
            details.append(detail)
        else:
            invalid += 1
        for row in result:
            print(f"{row['source_file']} [{row.get('case_id', '')}] "
                  f"{row['algorithm']}: {row['status']} "
                  f"travel={row.get('final_travel_minutes', '-')} "
                  f"objective={row.get('objective_cost', '-')} distance={row.get('distance', '-')} "
                  f"fuel_cost={row.get('estimated_fuel_cost', '-')} "
                  f"unserved={row.get('unserved_ids', '-')} "
                  f"{row.get('issues', '')}")
    print(f"Discovered {len(files)} source files; valid {len(files)-invalid}; invalid {invalid}.")
    if args.all:
        ids = {d["case_id"] for d in details}
        missing = sorted({f"TC{i:02}" for i in range(1, 31)} - ids)
        print("Missing internal case IDs: " + (", ".join(missing) or "none"))
    if not args.no_write:
        output.parent.mkdir(parents=True, exist_ok=True)
        route_output.parent.mkdir(parents=True, exist_ok=True)
        fields = list(dict.fromkeys(k for row in rows for k in row))
        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        route_output.write_text(json.dumps(json_safe(details), indent=2, allow_nan=False),
                                encoding="utf-8")
        print(f"Wrote {output.name} and {route_output.name}")
    return 1 if invalid else 0


if __name__ == "__main__":
    raise SystemExit(main())
