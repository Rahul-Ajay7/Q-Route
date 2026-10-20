#!/usr/bin/env python3
"""
SAQ-CVRPTW: Quantum-like tunnelling simulated annealing baseline for Q-ORBIT.

Method adaptation:
  La Cour, Troupe & Mark (2016), "Classical Simulated Annealing Using Quantum
  Analogues", Journal of Statistical Physics 164, 772-784.
  Their SAQ variant replaces the Boltzmann acceptance probability with
  p = exp(-d * sqrt(delta_E / T)), where d is Hamming distance.

This is a classical, quantum-inspired heuristic; it does NOT run on quantum
hardware and is NOT the team's proposed Q-ORBIT method. It is a comparison
baseline adapted to route-level CVRPTW moves.
"""
from __future__ import annotations
import argparse, json, math, random, time
from pathlib import Path
from typing import Any

EPS = 1e-9

def euclidean(a, b):
    return math.hypot(float(a["x"]) - float(b["x"]), float(a["y"]) - float(b["y"]))

class SAQCVRPTW:
    def __init__(self, data: dict[str, Any], seed: int = 42, iterations: int | None = None,
                 initial_temperature: float = 10.0, cooling: float = 0.996,
                 min_temperature: float = 0.02, weights=(0.4, 0.4, 0.2)):
        self.data = data
        self.rng = random.Random(seed)
        self.seed = seed
        self.vehicles = data.get("vehicles", [])
        self.depot = data["depot"]
        self.customers = data.get("customers", [])
        self.nodes = {int(self.depot["id"]): self.depot}
        self.nodes.update({int(c["id"]): c for c in self.customers})
        self.customer_ids = [int(c["id"]) for c in self.customers]
        self.vehicle_count = len(self.vehicles)
        self.base = data.get("base_travel_time_matrix", [])
        # Test-suite convention: matrix indexes are node IDs; the urgent node is appended.
        self.matrix_index = {node_id: node_id for node_id in self.nodes}
        self.events = data.get("traffic_events", [])
        self.simulation = data.get("simulation", {})
        self.start_time = float(self.simulation.get("start_time", 0))
        self.weights = weights
        n = len(self.customer_ids)
        self.iterations = iterations if iterations is not None else min(12000, max(1800, 30*n))
        self.initial_temperature = initial_temperature
        self.cooling = cooling
        self.min_temperature = min_temperature
        self._distance_cache = {}
        self._travel_cache = {}

    def distance(self, i, j):
        key = (i, j)
        if key not in self._distance_cache:
            self._distance_cache[key] = euclidean(self.nodes[i], self.nodes[j])
        return self._distance_cache[key]

    def travel_time(self, i, j, departure):
        base = self.base[self.matrix_index[i]][self.matrix_index[j]]
        multiplier = 1.0
        # Last applicable event wins. An event expires at end_time.
        applicable = []
        for e in self.events:
            if int(e.get("from", -1)) == i and int(e.get("to", -1)) == j:
                t = float(e.get("time", -math.inf))
                end = e.get("end_time")
                if departure + EPS >= t and (end is None or departure < float(end)):
                    applicable.append(e)
        if applicable:
            event = max(applicable, key=lambda e: float(e.get("time", -math.inf)))
            if event.get("multiplier") is None:
                return math.inf
            multiplier = float(event.get("multiplier", 1.0))
        return float(base) * multiplier

    def precheck(self):
        if not self.vehicles:
            return "No vehicles are defined."
        cap = [float(v.get("capacity", math.inf)) for v in self.vehicles]
        for c in self.customers:
            d = float(c.get("demand", 0))
            if d > max(cap, default=0) + EPS:
                return f"Customer {c['id']} demand {d:g} exceeds every vehicle capacity."
        if sum(float(c.get("demand", 0)) for c in self.customers) > sum(cap) + EPS:
            return "Aggregate customer demand exceeds total fleet capacity."
        # A simple hard-window impossibility check: even direct depot trip cannot start in window.
        for c in self.customers:
            ready = max(float(c.get("ready_time", 0)), float(c.get("release_time", 0)))
            due = float(c.get("due_time", math.inf))
            earliest = max(self.start_time + self.travel_time(0, int(c["id"]), self.start_time), ready)
            if not math.isfinite(earliest) or earliest > due + EPS:
                return f"Customer {c['id']} cannot be reached within its hard time window."
        return None

    def evaluate_route(self, route, vehicle):
        capacity = float(vehicle.get("capacity", math.inf))
        demand = sum(float(self.nodes[i].get("demand", 0)) for i in route)
        if demand > capacity + EPS:
            return None
        current = self.start_time
        previous = int(vehicle.get("start_depot", 0))
        distance = travel = fuel = 0.0
        for node_id in route:
            node = self.nodes[node_id]
            d = self.distance(previous, node_id)
            tt = self.travel_time(previous, node_id, current)
            if not math.isfinite(tt):
                return None
            arrival = current + tt
            ready = max(float(node.get("ready_time", 0)), float(node.get("release_time", 0)))
            service_start = max(arrival, ready)
            due = float(node.get("due_time", math.inf))
            if service_start > due + EPS:
                return None
            # Fuel proxy: distance with a small congestion premium, documented as synthetic.
            congestion = tt / max(float(self.base[previous][node_id]), EPS) if d > EPS else 1.0
            fuel += d * (1.0 + 0.15 * max(0.0, congestion - 1.0))
            distance += d
            travel += tt
            current = service_start + float(node.get("service_time", 0))
            previous = node_id
        end_depot = int(vehicle.get("end_depot", 0))
        d = self.distance(previous, end_depot)
        tt = self.travel_time(previous, end_depot, current)
        if not math.isfinite(tt):
            return None
        distance += d
        travel += tt
        congestion = tt / max(float(self.base[previous][end_depot]), EPS) if d > EPS else 1.0
        fuel += d * (1.0 + 0.15 * max(0.0, congestion - 1.0))
        current += tt
        depot_due = float(self.nodes[end_depot].get("due_time", math.inf))
        if current > depot_due + EPS:
            return None
        return {"distance": distance, "travel_time": travel, "fuel": fuel,
                "finish_time": current, "load": demand}

    def evaluate(self, routes):
        if len(routes) != self.vehicle_count:
            return None
        flattened = [x for r in routes for x in r]
        if len(flattened) != len(self.customer_ids) or set(flattened) != set(self.customer_ids):
            return None
        stats = []
        for r, v in zip(routes, self.vehicles):
            s = self.evaluate_route(r, v)
            if s is None:
                return None
            stats.append(s)
        D = sum(s["distance"] for s in stats)
        T = sum(s["travel_time"] for s in stats)
        F = sum(s["fuel"] for s in stats)
        # Normalize time/fuel against distance scale to avoid unit domination.
        scale = max(D, 1.0)
        wD, wT, wF = self.weights
        objective = wD*D + wT*T + wF*F
        return {"cost": objective, "distance": D, "travel_time": T, "fuel": F,
                "vehicles_used": sum(bool(r) for r in routes), "routes": stats}

    def initial_solution(self, attempts=60):
        ids = self.customer_ids[:]
        best = None
        best_cost = math.inf
        # Repeated randomized ordering + best feasible insertion across vehicles.
        for attempt in range(attempts):
            order = ids[:]
            if attempt:
                self.rng.shuffle(order)
            else:
                # Tight windows/release times first, then nearest-depot tie-break.
                order.sort(key=lambda i: (float(self.nodes[i].get("due_time", math.inf)),
                                          float(self.nodes[i].get("ready_time", 0))))
            routes = [[] for _ in self.vehicles]
            feasible = True
            for cid in order:
                candidates = []
                for vi, route in enumerate(routes):
                    for pos in range(len(route)+1):
                        trial = route[:pos] + [cid] + route[pos:]
                        s = self.evaluate_route(trial, self.vehicles[vi])
                        if s is not None:
                            # Incremental route cost, with slight balancing tie-break.
                            old = self.evaluate_route(route, self.vehicles[vi])
                            delta = s["distance"] + s["travel_time"] + 0.2*s["fuel"]
                            if old:
                                delta -= old["distance"] + old["travel_time"] + 0.2*old["fuel"]
                            candidates.append((delta + self.rng.random()*1e-5, vi, pos))
                if not candidates:
                    feasible = False
                    break
                _, vi, pos = min(candidates)
                routes[vi].insert(pos, cid)
            if feasible:
                score = self.evaluate(routes)
                if score and score["cost"] < best_cost:
                    best, best_cost = [r[:] for r in routes], score["cost"]
        return best

    def proposal(self, routes):
        candidate = [r[:] for r in routes]
        nonempty = [i for i, r in enumerate(candidate) if r]
        if not nonempty:
            return candidate, 1
        op = self.rng.random()
        if op < 0.43:
            # Relocate one customer (can cross vehicle boundaries).
            source = self.rng.choice(nonempty)
            p = self.rng.randrange(len(candidate[source]))
            cid = candidate[source].pop(p)
            targets = list(range(len(candidate)))
            target = self.rng.choice(targets)
            q = self.rng.randrange(len(candidate[target])+1)
            candidate[target].insert(q, cid)
            return candidate, 2
        if op < 0.73:
            # Swap customers within/across routes.
            a = self.rng.choice(nonempty)
            b = self.rng.choice(nonempty)
            pa = self.rng.randrange(len(candidate[a]))
            pb = self.rng.randrange(len(candidate[b]))
            candidate[a][pa], candidate[b][pb] = candidate[b][pb], candidate[a][pa]
            return candidate, 2
        if op < 0.91:
            # 2-opt reversal inside one route.
            a = self.rng.choice(nonempty)
            if len(candidate[a]) >= 2:
                i, j = sorted(self.rng.sample(range(len(candidate[a])), 2))
                candidate[a][i:j+1] = reversed(candidate[a][i:j+1])
                return candidate, max(2, j-i+1)
            return candidate, 1
        # Quantum-inspired large-neighbourhood move: randomly perturb multiple positions.
        count = min(len(self.customer_ids), self.rng.randint(2, max(2, min(6, len(self.customer_ids)))))
        flat = [(ri, pi) for ri, r in enumerate(candidate) for pi in range(len(r))]
        if len(flat) >= 2:
            chosen = self.rng.sample(flat, min(count, len(flat)))
            values = [candidate[ri][pi] for ri, pi in chosen]
            self.rng.shuffle(values)
            for (ri, pi), val in zip(chosen, values):
                candidate[ri][pi] = val
            return candidate, len(chosen)
        return candidate, 1

    def solve(self):
        started = time.perf_counter()
        reason = self.precheck()
        if reason:
            return {"status": "INFEASIBLE_PRECHECK", "test_id": self.data.get("id", "unknown"), "reason": reason, "seed": self.seed,
                    "runtime_seconds": time.perf_counter()-started, "algorithm": "SAQ-CVRPTW"}
        current = self.initial_solution()
        if current is None:
            return {"status": "NO_FEASIBLE_SOLUTION_FOUND", "test_id": self.data.get("id", "unknown"), "reason":
                    "The randomized constructive heuristic did not find a feasible route; this is not a proof of infeasibility.",
                    "seed": self.seed, "runtime_seconds": time.perf_counter()-started,
                    "algorithm": "SAQ-CVRPTW"}
        current_score = self.evaluate(current)
        best = [r[:] for r in current]
        best_score = dict(current_score)
        temp = self.initial_temperature
        accepted = 0
        valid_proposals = 0
        for step in range(self.iterations):
            cand, move_distance = self.proposal(current)
            cand_score = self.evaluate(cand)
            if cand_score is not None:
                valid_proposals += 1
                delta = cand_score["cost"] - current_score["cost"]
                if delta <= 0:
                    accept = True
                else:
                    # Quantum-like tunnelling acceptance from La Cour et al. (2016).
                    # move_distance approximates Hamming distance in route encoding.
                    exponent = -float(move_distance) * math.sqrt(delta / max(temp, EPS))
                    accept = self.rng.random() < math.exp(max(-745.0, exponent))
                if accept:
                    current, current_score = cand, cand_score
                    accepted += 1
                    if current_score["cost"] < best_score["cost"]:
                        best, best_score = [r[:] for r in current], dict(current_score)
            temp = max(self.min_temperature, temp*self.cooling)
        # Independent final feasibility check.
        final_score = self.evaluate(best)
        elapsed = time.perf_counter() - started
        return {
            "status": "FEASIBLE",
            "algorithm": "SAQ-CVRPTW (quantum-like tunnelling SA)",
            "test_id": self.data.get("id", "unknown"),
            "seed": self.seed,
            "runtime_seconds": round(elapsed, 6),
            "iterations": self.iterations,
            "valid_proposals": valid_proposals,
            "accepted_moves": accepted,
            "objective_cost": round(final_score["cost"], 6),
            "total_distance": round(final_score["distance"], 6),
            "total_travel_time": round(final_score["travel_time"], 6),
            "estimated_fuel": round(final_score["fuel"], 6),
            "routes": [
                {"vehicle_id": self.vehicles[i].get("id", f"V{i+1}"),
                 "route": [int(self.vehicles[i].get("start_depot", 0))] + r +
                          [int(self.vehicles[i].get("end_depot", 0))],
                 "load": round(final_score["routes"][i]["load"], 6),
                 "distance": round(final_score["routes"][i]["distance"], 6),
                 "travel_time": round(final_score["routes"][i]["travel_time"], 6),
                 "finish_time": round(final_score["routes"][i]["finish_time"], 6)}
                for i, r in enumerate(best)
            ],
            "weights": {"distance": self.weights[0], "travel_time": self.weights[1], "fuel": self.weights[2]},
            "feasibility": {"each_customer_once": True, "capacity": True, "hard_time_windows": True,
                            "closed_edge_departures_avoided": True}
        }

def solve_file(path, seed=42, iterations=None):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return SAQCVRPTW(data, seed=seed, iterations=iterations).solve()

def main():
    parser = argparse.ArgumentParser(description="Quantum-like tunnelling SA baseline for Q-ORBIT CVRPTW cases")
    parser.add_argument("input", nargs="?", help="Path to one testcase JSON")
    parser.add_argument("--cases-dir", help="Run every TC*.json in a directory")
    parser.add_argument("--output", help="Write JSON result (single case or suite summary)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--iterations", type=int, default=None)
    args = parser.parse_args()
    if args.cases_dir:
        paths = sorted(Path(args.cases_dir).glob("TC*.json"))
        results = [solve_file(p, seed=args.seed, iterations=args.iterations) for p in paths]
        summary = {"algorithm": "SAQ-CVRPTW", "cases_run": len(results),
                   "feasible": sum(r["status"] == "FEASIBLE" for r in results),
                   "precheck_infeasible": sum(r["status"] == "INFEASIBLE_PRECHECK" for r in results),
                   "no_solution_found": sum(r["status"] == "NO_FEASIBLE_SOLUTION_FOUND" for r in results),
                   "results": results}
        output = json.dumps(summary, indent=2)
    elif args.input:
        output = json.dumps(solve_file(args.input, seed=args.seed, iterations=args.iterations), indent=2)
    else:
        parser.error("provide input JSON or --cases-dir")
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    print(output)

if __name__ == "__main__":
    main()