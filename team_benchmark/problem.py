"""One monetary objective and constraint policy for every team method.

Coordinates represent synthetic km; input clock/travel times are minutes.
This is an offline planning model: events and orders are known in advance.
"""
from dataclasses import dataclass, asdict
from collections import Counter
import importlib.util
import math
from pathlib import Path

import numpy as np

from .layout import ROOT, MEMBERS

_spec = importlib.util.spec_from_file_location("team_sb_backend", MEMBERS / "Rahul/run_sb.py")
sb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sb)


@dataclass(frozen=True)
class Costs:
    distance_per_km: float = 3.0
    driver_per_minute: float = 2.5
    fuel_per_liter: float = 95.0
    liters_per_km: float = 0.09
    load_premium: float = 0.5
    congestion_premium: float = 0.25
    late_per_minute: float = 10.0
    vehicle_fixed: float = 500.0


class Problem:
    def __init__(self, data, hard_windows=True, costs=None):
        self.data = data
        self.hard_windows = hard_windows
        self.costs = costs or Costs()
        if any(not math.isfinite(v) or v < 0 for v in asdict(self.costs).values()):
            raise ValueError("Cost parameters must be finite and nonnegative")
        self.depot = data["depot"]["id"]
        self.vehicles = data["vehicles"]
        self.nodes = data["_nodes"]
        self.ids = tuple(c["id"] for c in data["customers"])
        self.start = max(float(data.get("simulation", {}).get("start_time", 0)),
                         float(data["depot"].get("ready_time", 0)))
        self.release = {c: float(self.nodes[c].get("release_time", 0)) for c in self.ids}
        for e in data.get("order_events", []):
            if e.get("type") == "new_order":
                c = e["customer_id"]
                if c not in self.release:
                    raise ValueError("New-order event references unknown customer")
                self.release[c] = max(self.release[c], float(e["time"]))
        self.edges = {}
        for e in data.get("traffic_events", []):
            if e.get("end_time") is not None and e["end_time"] < e["time"]:
                raise ValueError("Traffic event ends before it starts")
            self.edges.setdefault((e["from"], e["to"]), []).append(e)
        for events in self.edges.values():
            events.sort(key=lambda e: e["time"])
        self.dist = {(a, b): math.hypot(self.nodes[a]["x"] - self.nodes[b]["x"],
                                       self.nodes[a]["y"] - self.nodes[b]["y"])
                     for a in self.nodes for b in self.nodes}
        if not all(math.isfinite(d) for d in self.dist.values()):
            raise ValueError("Coordinates must be finite")

    @classmethod
    def load(cls, path, hard_windows=True):
        return cls(sb.load_case(Path(path)), hard_windows)

    def leg(self, a, b, departure):
        """Wait at the current node through a temporary closure, if necessary.

        Latest active directed event wins. Open edges depart immediately;
        searching strategic waits for cheaper future congestion is out of scope.
        """
        events = self.edges.get((a, b), [])
        now = departure
        boundaries = sorted({float(t) for e in events for t in (e["time"], e.get("end_time"))
                             if t is not None and t > now})
        for _ in range(len(boundaries) + 1):
            multiplier = 1.0
            for e in events:
                end = math.inf if e.get("end_time") is None else e["end_time"]
                if e["time"] <= now < end:
                    multiplier = e.get("multiplier")
            if multiplier is not None:
                idx = self.data["_indices"]
                base = float(self.data["_matrix"][idx[a], idx[b]])
                return base * multiplier, now - departure, multiplier
            future = [t for t in boundaries if t > now]
            if not future:
                return math.inf, 0.0, 1.0
            now = future[0]
        return math.inf, 0.0, 1.0

    def route(self, vi, route):
        v, p = self.vehicles[vi], self.costs
        issues = []
        load = sum(self.nodes[c].get("demand", 0) for c in route)
        if load > v["capacity"] + 1e-9:
            issues.append("capacity")
        clock, previous = self.start, self.depot
        distance = travel = fuel = lateness = 0.0
        starts, departures = [], []
        for c in list(route) + ([self.depot] if route else []):
            departures.append(clock)
            tt, wait, multiplier = self.leg(previous, c, clock)
            if not math.isfinite(tt):
                issues.append("closed_edge")
                clock = travel = math.inf
                break
            d = self.dist[previous, c]
            fuel += d * p.liters_per_km * (1 + p.load_premium * load / max(v["capacity"], 1e-9)) * (
                1 + p.congestion_premium * max(0, multiplier - 1))
            distance += d
            travel += tt
            clock += wait + tt
            node = self.nodes[c]
            if c != self.depot:
                clock = max(clock, node.get("ready_time", 0), self.release[c])
                starts.append(clock)
            late = max(0, clock - node.get("due_time", math.inf))
            lateness += late
            if self.hard_windows and late > 1e-9:
                issues.append("time_window")
            if c != self.depot:
                clock += node.get("service_time", 0)
                load -= node.get("demand", 0)
            previous = c
        for e in self.data.get("vehicle_events", []):
            if (route and e.get("vehicle_id") == v["id"] and e.get("type") == "breakdown"
                    and clock > e["time"]):
                issues.append("breakdown_requires_online_reassignment")
        duration = clock - self.start if route else 0.0
        breakdown = {"distance": distance * p.distance_per_km,
                     "driver": duration * p.driver_per_minute,
                     "fuel": fuel * p.fuel_per_liter,
                     "lateness": lateness * p.late_per_minute,
                     "vehicle": p.vehicle_fixed if route else 0.0}
        return dict(feasible=not issues, cost=sum(breakdown.values()), breakdown=breakdown,
                    distance=distance, travel_minutes=travel, duration_minutes=duration,
                    fuel_liters=fuel, lateness_minutes=lateness, issues=issues,
                    starts=starts, departures=departures, end=clock)

    def evaluate(self, routes):
        counts = Counter(c for r in routes for c in r)
        issues = []
        if len(routes) != len(self.vehicles):
            issues.append("vehicle_count")
        if counts != Counter(self.ids):
            issues.append("customer_coverage")
        if set(counts) - set(self.ids) or len(routes) != len(self.vehicles):
            return dict(feasible=False, cost=math.inf, issues=issues, routes=[])
        details = [self.route(i, r) for i, r in enumerate(routes)]
        for r in details:
            issues.extend(r["issues"])
        feasible = not issues
        return dict(feasible=feasible, cost=sum(r["cost"] for r in details) if feasible else math.inf,
                    issues=sorted(set(issues)), routes=details,
                    **{key: sum(r[key] for r in details) for key in
                       ("distance", "travel_minutes", "duration_minutes", "fuel_liters", "lateness_minutes")})

    def initial(self, seed=0, attempts=8):
        """Nearest-neighbour construction, then feasible insertion restarts if incomplete.

        Construction is shared, charged separately, and identical for all methods.
        Failure is explicitly not a proof of infeasibility.
        """
        rng = np.random.default_rng(seed)
        routes = [[] for _ in self.vehicles]
        remaining = set(self.ids)
        for vi in range(len(routes)):
            while remaining:
                prev = routes[vi][-1] if routes[vi] else self.depot
                choices = sorted(remaining, key=lambda c: (self.dist[prev, c], c))
                chosen = next((c for c in choices if self.route(vi, routes[vi] + [c])["feasible"]), None)
                if chosen is None:
                    break
                routes[vi].append(chosen)
                remaining.remove(chosen)
        if not remaining:
            return routes
        best = routes
        for attempt in range(attempts):
            order = list(self.ids)
            if attempt:
                rng.shuffle(order)
            else:
                order.sort(key=lambda c: self.nodes[c].get("due_time", math.inf))
            trial = [[] for _ in routes]
            for c in order:
                choices = []
                for vi, r in enumerate(trial):
                    old = self.route(vi, r)["cost"]
                    for pos in range(len(r) + 1):
                        detail = self.route(vi, r[:pos] + [c] + r[pos:])
                        if detail["feasible"]:
                            choices.append((detail["cost"] - old, vi, pos))
                if not choices:
                    break
                _, vi, pos = min(choices)
                trial[vi].insert(pos, c)
            if self.evaluate(trial)["feasible"]:
                return trial
            if sum(map(len, trial)) > sum(map(len, best)):
                best = trial
        return best
