"""Ground-truth evaluator C(R). Every method is judged by this and nothing else."""
from dataclasses import dataclass, field
import math
from ..config import CostParams
from ..models import ProblemInstance, Solution, Vehicle
from ..traffic import TrafficModel


@dataclass
class RouteResult:
    vehicle_id: int
    used: bool = False
    distance_km: float = 0.0
    duration_h: float = 0.0
    fuel_l: float = 0.0
    late_h: float = 0.0
    cap_excess: float = 0.0
    end_time: float = 0.0
    arrivals: list = field(default_factory=list)   # arrival time at each customer
    cost: dict = field(default_factory=dict)       # cost breakdown in INR

    @property
    def total(self) -> float:
        return sum(self.cost.values())


@dataclass
class SolutionResult:
    total_cost: float
    feasible: bool
    violations: list
    breakdown: dict
    routes: dict

    @property
    def objective(self) -> float:
        """Use for accept/reject: infeasible solutions are never acceptable."""
        return self.total_cost if self.feasible else math.inf


class Evaluator:
    def __init__(self, inst: ProblemInstance, traffic: TrafficModel, params: CostParams = CostParams()):
        self.inst, self.traffic, self.p = inst, traffic, params

    # ---- building blocks (also used by the QUBO builder for linearised leg costs) ----
    def leg_time(self, i: int, j: int, depart: float) -> tuple[float, float]:
        m = self.traffic.leg_multiplier(self.inst.zones[i], self.inst.zones[j], depart)
        return self.inst.time_h[i, j] * m, m

    def leg_fuel(self, i: int, j: int, load: float, cap: float, m: float) -> float:
        d = self.inst.dist_km[i, j]
        return d * self.p.alpha * (1 + self.p.beta * load / cap) * (1 + self.p.congestion_fuel * (m - 1))

    def leg_cost(self, i: int, j: int, depart: float, load: float, cap: float) -> float:
        """INR for one leg (distance + driving time + fuel), excluding waiting/penalties."""
        tt, m = self.leg_time(i, j, depart)
        return (self.p.c_d * self.inst.dist_km[i, j] + self.p.c_t * tt
                + self.p.fuel_price * self.leg_fuel(i, j, load, cap, m))

    # ---- route / solution ----
    def evaluate_route(self, veh: Vehicle, route: list[int], start_time: float | None = None) -> RouteResult:
        r = RouteResult(veh.id)
        if not route:
            return r
        inst, p = self.inst, self.p
        t0 = veh.start_time if start_time is None else start_time
        t = t0
        r.used = True
        load = sum(inst.customers[c].demand for c in route)
        r.cap_excess = max(0.0, load - veh.capacity)
        pos = 0
        for c in route + [0]:
            tt, m = self.leg_time(pos, c, t)
            r.distance_km += inst.dist_km[pos, c]
            r.fuel_l += self.leg_fuel(pos, c, load, veh.capacity, m)
            arrive = t + tt
            if c == 0:
                r.late_h += max(0.0, arrive - inst.depot_due)
                t = arrive
            else:
                cu = inst.customers[c]
                r.arrivals.append(arrive)
                r.late_h += max(0.0, arrive - cu.due)
                t = max(arrive, cu.ready) + cu.service     # wait if early
                load -= cu.demand
            pos = c
        r.end_time = t
        r.duration_h = t - t0
        r.cost = {
            "vehicle": p.c_veh,
            "distance": p.c_d * r.distance_km,
            "time": p.c_t * r.duration_h,
            "fuel": p.fuel_price * r.fuel_l,
            "late": p.lambda_late_per_hour * r.late_h,
            "capacity": p.lambda_cap * r.cap_excess,
        }
        return r

    def trace_route(self, veh: Vehicle, route: list[int], start_time: float | None = None) -> list[dict]:
        """Per-leg trace of a route (same logic as evaluate_route). Leg l goes from route[l-1]
        (or depot) to route[l] (or depot when l == len(route)). Used by the partition scorer."""
        if not route:
            return []
        inst = self.inst
        t = veh.start_time if start_time is None else start_time
        load = sum(inst.customers[c].demand for c in route)
        pos, legs = 0, []
        for l, c in enumerate(route + [0]):
            tt, m = self.leg_time(pos, c, t)
            arrive = t + tt
            fuel = self.leg_fuel(pos, c, load, veh.capacity, m)
            if c == 0:
                late, nxt = max(0.0, arrive - inst.depot_due), arrive
            else:
                cu = inst.customers[c]
                late = max(0.0, arrive - cu.due)
                nxt = max(arrive, cu.ready) + cu.service
                load -= cu.demand
            legs.append(dict(leg=l, frm=pos, to=c, depart=t, arrive=arrive, travel_h=tt, mult=m,
                             fuel_l=fuel, late_h=late))
            t, pos = nxt, c
        return legs

    def evaluate(self, sol: Solution) -> SolutionResult:
        violations = []
        visited = sol.visited()
        expected = set(self.inst.customers)
        seen = set()
        for c in visited:
            if c not in expected:
                violations.append(f"unknown customer {c}")
            elif c in seen:
                violations.append(f"customer {c} visited more than once")
            seen.add(c)
        for c in expected - seen:
            violations.append(f"customer {c} not visited")
        for v in sol.routes:
            if v not in self.inst.vehicles:
                violations.append(f"unknown vehicle {v}")

        breakdown = {k: 0.0 for k in ("vehicle", "distance", "time", "fuel", "late", "capacity")}
        results = {}
        for vid, route in sol.routes.items():
            if vid not in self.inst.vehicles or any(c not in expected for c in route):
                continue
            rr = self.evaluate_route(self.inst.vehicles[vid], route)
            results[vid] = rr
            for k, v in rr.cost.items():
                breakdown[k] += v
            if rr.cap_excess > 0:
                violations.append(f"vehicle {vid} over capacity by {rr.cap_excess:g}")
            if self.p.hard_time_windows and rr.late_h > 1e-9:
                violations.append(f"vehicle {vid} violates time windows")
        return SolutionResult(sum(breakdown.values()), not violations, violations, breakdown, results)