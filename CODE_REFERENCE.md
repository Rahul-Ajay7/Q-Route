# Q-Route Source Code Reference

This file aggregates all Python source modules in src/, each with its file path and full code, for quick reference.

## src/benchmarking/benchmark_runner.py

```python
"""Run solvers across experiment configurations."""

from __future__ import annotations

from typing import Dict, List


class BenchmarkRunner:
    """Execute all configured solvers on a set of instances."""

    def run(self, configs: List[Dict]) -> Dict:
        raise NotImplementedError
```

## src/benchmarking/comparison.py

```python
"""Compare solver performance across instances."""

from __future__ import annotations

from typing import Dict


class Comparison:
    """Build comparison tables between solvers."""

    def build_table(self, results: Dict) -> object:
        raise NotImplementedError
```

## src/benchmarking/metrics.py

```python
"""Performance metrics for solutions."""

from __future__ import annotations

from typing import Any

import numpy as np


class Metrics:
    """Compute gap, runtime, and quality statistics."""

    def cost(self, solution: Any) -> float:
        raise NotImplementedError

    def gap_to_best(self, cost: float, best: float) -> float:
        return (cost - best) / best

    def statistics(self, costs: np.ndarray) -> dict:
        raise NotImplementedError
```

## src/benchmarking/report_generator.py

```python
"""Generate result reports and tables."""

from __future__ import annotations

from typing import Dict


class ReportGenerator:
    """Export comparison results to CSV / Markdown / LaTeX."""

    def to_csv(self, results: Dict, path: str) -> None:
        raise NotImplementedError

    def to_markdown(self, results: Dict, path: str) -> None:
        raise NotImplementedError

    def to_latex(self, results: Dict, path: str) -> None:
        raise NotImplementedError
```

## src/constraints/capacity.py

```python
"""
src/constraints/capacity.py

Checks total demand assigned to a route does not exceed vehicle capacity.
"""

from typing import List


class CapacityConstraint:

    def is_feasible(self, demands: List[float], vehicle_capacity: float) -> bool:
        """
        demands: list of customer demand values in route order (exclude depot).
        vehicle_capacity: max load the vehicle can carry.
        """
        return sum(demands) <= vehicle_capacity

    def total_load(self, demands: List[float]) -> float:
        return sum(demands)

    def violation_amount(self, demands: List[float], vehicle_capacity: float) -> float:
        """Returns 0.0 if feasible, else amount of overload (for soft penalty use)."""
        overload = self.total_load(demands) - vehicle_capacity
        return max(0.0, overload)

    def check_fleet(self, route_demands: List[List[float]],
                     vehicle_capacities: List[float]) -> List[bool]:
        """
        route_demands: list of demand-lists, one per vehicle/route.
        vehicle_capacities: parallel list of capacities.
        Returns list of bool feasibility per route.
        """
        if len(route_demands) != len(vehicle_capacities):
            raise ValueError("route_demands and vehicle_capacities must match length")
        return [
            self.is_feasible(demands, cap)
            for demands, cap in zip(route_demands, vehicle_capacities)
        ]
```

## src/constraints/feasibility.py

```python
"""
src/constraints/feasibility.py

Aggregates capacity, time window, and vehicle availability checks into a
single feasibility verdict for a route or full solution. Used by solvers
(greedy, SA, QUBO decoder) to reject/penalize infeasible candidates.
"""

from typing import List, Tuple, Dict
from src.constraints.capacity import CapacityConstraint
from src.constraints.time_windows import TimeWindowConstraint
from src.constraints.vehicle_availability import VehicleAvailabilityConstraint


class FeasibilityChecker:

    def __init__(self):
        self.capacity = CapacityConstraint()
        self.time_windows = TimeWindowConstraint()
        self.availability = VehicleAvailabilityConstraint()

    def check_route(self, demands: List[float], vehicle_capacity: float,
                     arrival_times_min: List[float],
                     windows_min: List[Tuple[float, float]],
                     route_start_min: float, route_end_min: float,
                     shift_window_min: Tuple[float, float]) -> Dict:
        """
        Runs all three constraint checks on a single route.
        Returns dict: {feasible: bool, violations: {...}}
        """
        capacity_ok = self.capacity.is_feasible(demands, vehicle_capacity)
        time_ok = self.time_windows.is_route_feasible(arrival_times_min, windows_min)
        avail_ok = self.availability.is_feasible(route_start_min, route_end_min, shift_window_min)

        return {
            "feasible": capacity_ok and time_ok and avail_ok,
            "violations": {
                "capacity_overload": self.capacity.violation_amount(demands, vehicle_capacity),
                "time_window_lateness": self.time_windows.violations(arrival_times_min, windows_min),
                "overtime_min": self.availability.overtime_amount(route_end_min, shift_window_min),
            },
        }

    def check_solution(self, route_checks: List[Dict]) -> Dict:
        """
        route_checks: list of dicts, each output from check_route() for one
        route in the solution.
        Returns overall feasibility (all routes must be feasible) + per-route detail.
        """
        all_feasible = all(rc["feasible"] for rc in route_checks)
        return {
            "feasible": all_feasible,
            "routes": route_checks,
            "num_infeasible_routes": sum(1 for rc in route_checks if not rc["feasible"]),
        }
```

## src/constraints/time_windows.py

```python
"""
src/constraints/time_windows.py

Checks whether arrival times at customers fall within their [ready_time,
due_time] windows. Distinguishes hard violation (arrival > due_time, service
not allowed) from waiting (arrival < ready_time, vehicle waits, still feasible).
"""

from typing import List, Tuple


class TimeWindowConstraint:

    def is_stop_feasible(self, arrival_time_min: float,
                          ready_time_min: float, due_time_min: float) -> bool:
        """
        Arriving early is fine (vehicle waits until ready_time).
        Arriving after due_time is a hard violation.
        """
        return arrival_time_min <= due_time_min

    def effective_start_time(self, arrival_time_min: float,
                              ready_time_min: float) -> float:
        """Service can't start before ready_time -- vehicle waits if early."""
        return max(arrival_time_min, ready_time_min)

    def is_route_feasible(self, arrival_times_min: List[float],
                           windows_min: List[Tuple[float, float]]) -> bool:
        """
        arrival_times_min: arrival time at each customer stop, in route order.
        windows_min: parallel list of (ready_time, due_time) tuples.
        """
        if len(arrival_times_min) != len(windows_min):
            raise ValueError("arrival_times_min and windows_min must match length")
        return all(
            self.is_stop_feasible(a, ready, due)
            for a, (ready, due) in zip(arrival_times_min, windows_min)
        )

    def violations(self, arrival_times_min: List[float],
                    windows_min: List[Tuple[float, float]]) -> List[float]:
        """Returns lateness amount per stop (0.0 if on time or early)."""
        return [
            max(0.0, a - due)
            for a, (ready, due) in zip(arrival_times_min, windows_min)
        ]
```

## src/constraints/vehicle_availability.py

```python
"""
src/constraints/vehicle_availability.py

Checks a route's total duration fits within the vehicle's shift/availability
window (e.g. driver can only work 8am-6pm).
"""

from typing import Tuple


class VehicleAvailabilityConstraint:

    def is_feasible(self, route_start_min: float, route_end_min: float,
                     shift_window_min: Tuple[float, float]) -> bool:
        """
        route_start_min: time vehicle departs depot.
        route_end_min: time vehicle returns to depot (after last stop + return leg).
        shift_window_min: (shift_start, shift_end) for this vehicle.
        """
        shift_start, shift_end = shift_window_min
        return route_start_min >= shift_start and route_end_min <= shift_end

    def overtime_amount(self, route_end_min: float,
                         shift_window_min: Tuple[float, float]) -> float:
        """Returns 0.0 if within shift, else minutes over shift end."""
        _, shift_end = shift_window_min
        return max(0.0, route_end_min - shift_end)

    def route_duration_min(self, route_start_min: float, route_end_min: float) -> float:
        return route_end_min - route_start_min
```

## src/cost/distance_cost.py

```python
"""
src/cost/distance_cost.py

Distance-based cost component. Uses Euclidean distance by default;
can be swapped for real road distance (OSRM) if precomputed matrix given.
"""

import math
from typing import Tuple


class DistanceCost:

    def __init__(self, cost_per_km: float = 1.0):
        self.cost_per_km = cost_per_km

    def euclidean_km(self, coord_a: Tuple[float, float],
                      coord_b: Tuple[float, float]) -> float:
        """Straight-line distance in km. Coords as (x, y) or (lat, lon)
        in already-projected/flat units. For real lat/lon use haversine_km."""
        dx = coord_a[0] - coord_b[0]
        dy = coord_a[1] - coord_b[1]
        return math.sqrt(dx * dx + dy * dy)

    def haversine_km(self, coord_a: Tuple[float, float],
                      coord_b: Tuple[float, float]) -> float:
        """Great-circle distance in km for real (lat, lon) coordinates."""
        lat1, lon1 = map(math.radians, coord_a)
        lat2, lon2 = map(math.radians, coord_b)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = (math.sin(dlat / 2) ** 2
             + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))
        r_earth_km = 6371.0
        return r_earth_km * c

    def route_distance_km(self, route_coords, use_haversine: bool = False) -> float:
        """
        route_coords: ordered list of (x,y) or (lat,lon) points including
        depot at start and end.
        Returns total distance in km for the route.
        """
        if len(route_coords) < 2:
            return 0.0
        dist_fn = self.haversine_km if use_haversine else self.euclidean_km
        total = 0.0
        for i in range(len(route_coords) - 1):
            total += dist_fn(route_coords[i], route_coords[i + 1])
        return total

    def cost(self, distance_km: float) -> float:
        """Convert distance to monetary/cost units."""
        return distance_km * self.cost_per_km
```

## src/cost/late_penalty.py

```python
"""
src/cost/late_penalty.py

Penalty for arriving after a customer's due time (soft time window
violation). Assumes Customer model has time_window = (ready_time, due_time)
and arrival_time is computed externally (cumulative travel+service time).

NOTE: adjust attribute names below (customer.due_time / customer.ready_time)
to match your actual Customer dataclass field names in src/models/customer.py.
"""

from typing import List


class LatePenalty:

    def __init__(self, penalty_per_minute: float = 10.0,
                 hard_violation_penalty: float = 1000.0,
                 hard_violation_threshold_min: float = 60.0):
        """
        penalty_per_minute: linear cost per minute late.
        hard_violation_penalty: extra flat penalty if lateness exceeds
        threshold (treat as near-infeasible without fully rejecting solution
        during SA/QUBO search).
        """
        self.penalty_per_minute = penalty_per_minute
        self.hard_violation_penalty = hard_violation_penalty
        self.hard_violation_threshold_min = hard_violation_threshold_min

    def stop_penalty(self, arrival_time_min: float, due_time_min: float) -> float:
        lateness = arrival_time_min - due_time_min
        if lateness <= 0:
            return 0.0
        cost = lateness * self.penalty_per_minute
        if lateness > self.hard_violation_threshold_min:
            cost += self.hard_violation_penalty
        return cost

    def route_penalty(self, arrival_times_min: List[float],
                       due_times_min: List[float]) -> float:
        """
        arrival_times_min / due_times_min: parallel lists, one entry per
        customer stop in route order (exclude depot).
        """
        if len(arrival_times_min) != len(due_times_min):
            raise ValueError("arrival_times_min and due_times_min must match length")
        return sum(
            self.stop_penalty(a, d)
            for a, d in zip(arrival_times_min, due_times_min)
        )
```

## src/cost/objective.py

```python
"""
src/cost/objective.py

Aggregates distance, traffic, late penalty, and operating cost into a
single weighted objective value. Weights loaded from config/weights.yaml.
This is the function solvers (greedy, SA, QUBO) minimize.
"""

from typing import Dict, List
from src.cost.distance_cost import DistanceCost
from src.cost.traffic_cost import TrafficCost
from src.cost.late_penalty import LatePenalty
from src.cost.operating_cost import OperatingCost


class ObjectiveFunction:

    def __init__(self, weights: Dict[str, float] = None):
        """
        weights: dict with keys 'distance', 'traffic', 'late_penalty',
        'operating'. Defaults to equal-ish weighting if not provided --
        override via config/weights.yaml in production.
        """
        default_weights = {
            "distance": 1.0,
            "traffic": 1.0,
            "late_penalty": 2.0,   # weighted higher, service-quality critical
            "operating": 1.0,
        }
        self.weights = {**default_weights, **(weights or {})}

        self.distance_cost = DistanceCost()
        self.traffic_cost = TrafficCost()
        self.late_penalty = LatePenalty()
        self.operating_cost = OperatingCost()

    def route_cost_breakdown(self, route_coords: List, leg_travel_time_infos: List[Dict],
                              arrival_times_min: List[float], due_times_min: List[float],
                              route_duration_hours: float, use_haversine: bool = True,
                              vehicle_fixed_cost: float = None,
                              vehicle_cost_per_hour: float = None) -> Dict[str, float]:
        """
        Returns individual weighted cost components for ONE route, plus total.
        Use this for debugging/reporting (dashboard results page).
        """
        distance_km = self.distance_cost.route_distance_km(route_coords, use_haversine)
        c_distance = self.distance_cost.cost(distance_km)
        c_traffic = self.traffic_cost.route_cost(leg_travel_time_infos)
        c_late = self.late_penalty.route_penalty(arrival_times_min, due_times_min)
        c_operating = self.operating_cost.vehicle_cost(
            route_duration_hours, vehicle_fixed_cost, vehicle_cost_per_hour
        )

        weighted = {
            "distance": self.weights["distance"] * c_distance,
            "traffic": self.weights["traffic"] * c_traffic,
            "late_penalty": self.weights["late_penalty"] * c_late,
            "operating": self.weights["operating"] * c_operating,
        }
        weighted["total"] = sum(weighted.values())
        return weighted

    def route_cost(self, *args, **kwargs) -> float:
        """Convenience: total scalar cost only (what solvers minimize)."""
        return self.route_cost_breakdown(*args, **kwargs)["total"]

    def solution_cost(self, per_route_breakdowns: List[Dict[str, float]]) -> Dict[str, float]:
        """
        Aggregate cost across all routes in a Solution.
        per_route_breakdowns: list of dicts from route_cost_breakdown().
        """
        keys = ["distance", "traffic", "late_penalty", "operating", "total"]
        totals = {k: sum(b[k] for b in per_route_breakdowns) for k in keys}
        return totals
```

## src/cost/operating_cost.py

```python
"""
src/cost/operating_cost.py

Vehicle operating cost: fixed cost per vehicle used + variable cost per
hour of operation (driver wages, fuel idle time etc). Adjust attribute
names to match your Vehicle dataclass (fixed_cost, cost_per_hour).
"""

from typing import List


class OperatingCost:

    def __init__(self, default_fixed_cost: float = 50.0,
                 default_cost_per_hour: float = 15.0):
        self.default_fixed_cost = default_fixed_cost
        self.default_cost_per_hour = default_cost_per_hour

    def vehicle_cost(self, route_duration_hours: float,
                      fixed_cost: float = None,
                      cost_per_hour: float = None) -> float:
        """
        route_duration_hours: total time vehicle is out (depot to depot).
        Pass fixed_cost/cost_per_hour explicitly if Vehicle object has
        its own rates; else defaults used.
        """
        fixed = fixed_cost if fixed_cost is not None else self.default_fixed_cost
        rate = cost_per_hour if cost_per_hour is not None else self.default_cost_per_hour
        return fixed + (route_duration_hours * rate)

    def fleet_cost(self, route_durations_hours: List[float],
                    fixed_costs: List[float] = None,
                    costs_per_hour: List[float] = None) -> float:
        """
        Sum operating cost across all used vehicles (routes). Only include
        vehicles that actually have a non-empty route -- unused vehicles
        cost nothing.
        """
        n = len(route_durations_hours)
        fixed_costs = fixed_costs or [None] * n
        costs_per_hour = costs_per_hour or [None] * n
        return sum(
            self.vehicle_cost(d, f, c)
            for d, f, c in zip(route_durations_hours, fixed_costs, costs_per_hour)
        )
```

## src/cost/traffic_cost.py

```python
"""
src/cost/traffic_cost.py

Traffic-based cost component. Penalizes routes/segments that hit high
congestion, using the congestion_factor produced by TravelTime.
"""

from typing import List, Dict


class TrafficCost:

    def __init__(self, cost_per_congestion_unit: float = 5.0):
        """
        cost_per_congestion_unit: cost applied per unit of congestion
        above free-flow (congestion_factor - 1.0), per route leg.
        """
        self.cost_per_congestion_unit = cost_per_congestion_unit

    def leg_cost(self, travel_time_info: Dict) -> float:
        """
        travel_time_info: dict from TravelTime.compute(), must contain
        'congestion_factor'.
        Cost is 0 at free-flow (factor=1.0), grows linearly above that.
        """
        factor = travel_time_info.get("congestion_factor", 1.0)
        excess_congestion = max(0.0, factor - 1.0)
        return excess_congestion * self.cost_per_congestion_unit

    def route_cost(self, leg_travel_time_infos: List[Dict]) -> float:
        """
        leg_travel_time_infos: list of TravelTime.compute() dicts, one
        per leg in the route (depot->c1, c1->c2, ..., cn->depot).
        """
        return sum(self.leg_cost(info) for info in leg_travel_time_infos)
```

## src/data/cvrplib_loader.py

```python
"""
src/data/cvrplib_loader.py

Parses CVRPLIB .vrp instance files (Set A/B format) into the same plain-dict
structure produced by SyntheticGenerator, so both feed solvers identically.

CVRPLIB format reference: sections NODE_COORD_SECTION, DEMAND_SECTION,
DEPOT_SECTION, CAPACITY. Standard CVRPLIB Set A/B files do NOT include
time windows -- if absent, default wide windows covering full horizon
are assigned so the same CVRPTW pipeline still works.
"""

import re
from typing import Dict, Tuple


class CVRPLibLoader:

    def load(self, filepath: str, default_time_horizon_min: float = 480.0,
              default_service_time_min: float = 10.0,
              vehicles_override: int = None) -> Dict:
        with open(filepath, "r") as f:
            content = f.read()

        capacity = self._parse_capacity(content)
        num_vehicles = vehicles_override or self._parse_num_vehicles(content)
        coords = self._parse_section(content, "NODE_COORD_SECTION")
        demands = self._parse_section(content, "DEMAND_SECTION")
        depot_id = self._parse_depot_id(content)

        customers = []
        depot_coord = None
        for node_id, (x, y) in coords.items():
            if node_id == depot_id:
                depot_coord = (x, y)
                continue
            demand = demands.get(node_id, 0.0)
            customers.append({
                "id": node_id,
                "coord": (x, y),
                "demand": demand,
                "ready_time": 0.0,
                "due_time": default_time_horizon_min,
                "service_time": default_service_time_min,
            })

        if depot_coord is None:
            raise ValueError(f"Depot node {depot_id} not found in NODE_COORD_SECTION")

        vehicles = [
            {
                "id": vid,
                "capacity": capacity,
                "shift_window": (0.0, default_time_horizon_min),
            }
            for vid in range(1, num_vehicles + 1)
        ]

        return {
            "depot": {"coord": depot_coord},
            "customers": customers,
            "vehicles": vehicles,
        }

    def _parse_capacity(self, content: str) -> float:
        match = re.search(r"CAPACITY\s*:\s*(\d+)", content)
        if not match:
            raise ValueError("CAPACITY field not found in .vrp file")
        return float(match.group(1))

    def _parse_num_vehicles(self, content: str) -> int:
        """
        CVRPLIB filenames often encode vehicle count e.g. A-n32-k5.vrp = k5
        means 5 vehicles. Try COMMENT field first, else default to 1
        (caller should override via vehicles_override if known from filename).
        """
        match = re.search(r"No of trucks:\s*(\d+)", content)
        if match:
            return int(match.group(1))
        return 1

    def _parse_depot_id(self, content: str) -> int:
        section = content.split("DEPOT_SECTION")[1] if "DEPOT_SECTION" in content else ""
        for line in section.strip().splitlines():
            line = line.strip()
            if line and line != "-1":
                return int(line)
        return 1  # CVRPLIB convention: node 1 is usually depot

    def _parse_section(self, content: str, section_name: str) -> Dict[int, Tuple]:
        result = {}
        if section_name not in content:
            return result
        section = content.split(section_name)[1]
        # stop at next SECTION keyword or EOF marker
        for stop_kw in ["_SECTION", "DEPOT_SECTION", "EOF"]:
            if stop_kw in section and stop_kw != section_name:
                idx = section.find(stop_kw)
                if idx > 0:
                    section = section[:idx]
                    break

        for line in section.strip().splitlines():
            parts = line.split()
            if not parts or not parts[0].lstrip("-").isdigit():
                continue
            node_id = int(parts[0])
            if section_name == "NODE_COORD_SECTION" and len(parts) >= 3:
                result[node_id] = (float(parts[1]), float(parts[2]))
            elif section_name == "DEMAND_SECTION" and len(parts) >= 2:
                result[node_id] = float(parts[1])
        return result
```

## src/data/instance_loader.py

```python
"""Load problem instances from processed files and directories."""

from __future__ import annotations

from typing import Any, Dict

from src.data.preprocessing import Preprocessor
from src.models.problem_instance import ProblemInstance


class InstanceLoader:
    """Load a ProblemInstance from a processed instance file."""

    def __init__(self) -> None:
        self._preprocessor = Preprocessor()

    def load(self, path: str) -> ProblemInstance:
        raise NotImplementedError

    def load_metadata(self, path: str) -> Dict[str, Any]:
        raise NotImplementedError
```

## src/data/preprocessing.py

```python
"""
src/data/preprocessing.py

Builds distance and travel-time matrices for a problem instance (from
SyntheticGenerator or CVRPLibLoader output). Node 0 = depot, nodes 1..N =
customers, in the order given in instance["customers"].

Two modes:
- Euclidean (fast, no API calls) -- use for CVRPLIB benchmark instances
  which have abstract x,y coords, not real lat/lon.
- Real traffic-aware (uses TravelTime -> Google/OSRM/synthetic fallback)
  -- use for lat/lon instances (generate_lat_lon) where you want the
  traffic factor demoed.
"""

from typing import Dict, List
from src.cost.distance_cost import DistanceCost
from src.traffic.travel_time import TravelTime


class Preprocessor:

    def __init__(self, use_real_traffic: bool = False,
                 google_api_key: str = None):
        self.distance_cost = DistanceCost()
        self.travel_time = TravelTime(use_real_traffic=use_real_traffic,
                                       google_api_key=google_api_key)

    def _all_coords(self, instance: Dict) -> List:
        """Node 0 = depot, then customers in order."""
        coords = [instance["depot"]["coord"]]
        coords.extend(c["coord"] for c in instance["customers"])
        return coords

    def build_distance_matrix(self, instance: Dict, use_haversine: bool = False) -> List[List[float]]:
        """
        Returns NxN Euclidean/haversine distance matrix in km.
        Fast, no network calls. Use for CVRPLIB (abstract coords) or as
        the base distance before applying traffic factor.
        """
        coords = self._all_coords(instance)
        n = len(coords)
        dist_fn = (self.distance_cost.haversine_km if use_haversine
                   else self.distance_cost.euclidean_km)
        matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j:
                    matrix[i][j] = dist_fn(coords[i], coords[j])
        return matrix

    def build_travel_time_matrix(self, instance: Dict, departure_hour: int = 9,
                                  avg_speed_kmh: float = 40.0,
                                  use_haversine: bool = True) -> Dict:
        """
        Returns dict with:
        - travel_time_s: NxN matrix of travel time in seconds (traffic-aware
          if use_real_traffic=True and coords are real lat/lon)
        - sources: NxN matrix noting which source was used per leg
          (google_traffic / osrm_freeflow+synthetic / synthetic)

        WARNING: real traffic mode makes 1 API call per pair -- for N nodes
        that's N*(N-1) calls. Fine for small demo instances (<15 nodes).
        For larger instances, batch via OSRMClient.table() or Google's
        multi-origin/destination matrix call instead of pairwise looping.
        """
        coords = self._all_coords(instance)
        n = len(coords)
        distance_matrix = self.build_distance_matrix(instance, use_haversine)

        travel_time_s = [[0.0] * n for _ in range(n)]
        sources = [[None] * n for _ in range(n)]

        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                result = self.travel_time.compute(
                    coord_from=coords[i],
                    coord_to=coords[j],
                    euclidean_distance_km=distance_matrix[i][j],
                    departure_hour=departure_hour,
                    avg_speed_kmh=avg_speed_kmh,
                )
                travel_time_s[i][j] = result["travel_time_s"]
                sources[i][j] = result["source"]

        return {
            "travel_time_s": travel_time_s,
            "distance_km": distance_matrix,
            "sources": sources,
        }
```

## src/data/synthetic_generator.py

```python
"""
src/data/synthetic_generator.py

Generates random CVRPTW problem instances for testing solvers without
needing real CVRPLIB data. Produces plain dicts -- wrap into your
ProblemInstance/Customer/Vehicle dataclasses in instance_loader.py or
directly where consumed, adjusting field names to match src/models/*.py.
"""

import random
from typing import Dict, List, Tuple


class SyntheticGenerator:

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate(self, num_customers: int = 20, num_vehicles: int = 4,
                 area_size: float = 100.0, vehicle_capacity: float = 100.0,
                 demand_range: Tuple[int, int] = (5, 25),
                 depot_coord: Tuple[float, float] = None,
                 time_horizon_min: float = 480.0,
                 window_width_min: Tuple[float, float] = (30, 90),
                 service_time_min: float = 10.0) -> Dict:
        """
        Returns a plain-dict instance:
        {
            "depot": {"coord": (x,y)},
            "customers": [
                {"id": int, "coord": (x,y), "demand": float,
                 "ready_time": float, "due_time": float,
                 "service_time": float},
                ...
            ],
            "vehicles": [
                {"id": int, "capacity": float,
                 "shift_window": (start_min, end_min)},
                ...
            ],
        }
        """
        depot_coord = depot_coord or (area_size / 2, area_size / 2)

        customers = []
        for cid in range(1, num_customers + 1):
            coord = (self.rng.uniform(0, area_size), self.rng.uniform(0, area_size))
            demand = self.rng.randint(*demand_range)
            ready = self.rng.uniform(0, time_horizon_min - window_width_min[1])
            width = self.rng.uniform(*window_width_min)
            due = min(ready + width, time_horizon_min)
            customers.append({
                "id": cid,
                "coord": coord,
                "demand": demand,
                "ready_time": round(ready, 1),
                "due_time": round(due, 1),
                "service_time": service_time_min,
            })

        vehicles = [
            {
                "id": vid,
                "capacity": vehicle_capacity,
                "shift_window": (0.0, time_horizon_min),
            }
            for vid in range(1, num_vehicles + 1)
        ]

        return {
            "depot": {"coord": depot_coord},
            "customers": customers,
            "vehicles": vehicles,
        }

    def generate_lat_lon(self, num_customers: int = 20, num_vehicles: int = 4,
                          center: Tuple[float, float] = (13.0827, 80.2707),
                          radius_km: float = 15.0, **kwargs) -> Dict:
        """
        Same as generate() but produces real-world (lat, lon) coordinates
        scattered around a center point (default: Chennai). Use this when
        feeding into OSRM/Google traffic clients, which need real coords.
        1 degree lat ~= 111 km. Approximate, fine for demo purposes.
        """
        deg_radius = radius_km / 111.0
        lat_c, lon_c = center

        instance = self.generate(num_customers=num_customers, num_vehicles=num_vehicles,
                                  area_size=1.0, **kwargs)

        # overwrite coords with real lat/lon scattered around center
        import math
        instance["depot"]["coord"] = center
        for c in instance["customers"]:
            r = self.rng.uniform(0, deg_radius)
            theta = self.rng.uniform(0, 2 * math.pi)
            c["coord"] = (lat_c + r * math.cos(theta), lon_c + r * math.sin(theta))

        return instance
```

## src/models/customer.py

```python
"""Customer entity: demand, location, and time window."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass
class Customer:
    """A customer requiring service within a time window."""

    customer_id: int
    x: float
    y: float
    demand: float
    ready_time: float
    due_time: float
    service_time: float = 0.0

    @property
    def location(self) -> Tuple[float, float]:
        return (self.x, self.y)
```

## src/models/depot.py

```python
"""Depot entity: origin and destination of all routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass
class Depot:
    """Central depot where vehicles start and end."""

    depot_id: int
    x: float
    y: float
    return_to_depot: bool = True

    @property
    def location(self) -> Tuple[float, float]:
        return (self.x, self.y)
```

## src/models/problem_instance.py

```python
"""Full problem instance: depot, customers, vehicles, and matrices."""

from __future__ import annotations

from typing import Dict, List

import numpy as np

from src.models.customer import Customer
from src.models.depot import Depot
from src.models.vehicle import Vehicle


class ProblemInstance:
    """Container for all inputs of a CVRPTW problem."""

    def __init__(
        self,
        name: str,
        depot: Depot,
        customers: List[Customer],
        vehicles: List[Vehicle],
        distance_matrix: np.ndarray,
        travel_time_matrix: np.ndarray,
    ) -> None:
        self.name = name
        self.depot = depot
        self.customers = customers
        self.vehicles = vehicles
        self.distance_matrix = distance_matrix
        self.travel_time_matrix = travel_time_matrix
        self.metadata: Dict = {}

    @property
    def num_customers(self) -> int:
        return len(self.customers)

    @property
    def num_vehicles(self) -> int:
        return len(self.vehicles)
```

## src/models/route.py

```python
"""Route entity: ordered sequence of customers served by one vehicle."""

from __future__ import annotations

from typing import List

from src.models.customer import Customer


class Route:
    """An ordered tour for a single vehicle."""

    def __init__(self, vehicle_id: int, customers: List[Customer] | None = None) -> None:
        self.vehicle_id = vehicle_id
        self.customers: List[Customer] = customers or []

    def add(self, customer: Customer) -> None:
        self.customers.append(customer)

    def total_demand(self) -> float:
        return sum(c.demand for c in self.customers)

    def __len__(self) -> int:
        return len(self.customers)
```

## src/models/vehicle.py

```python
"""Vehicle entity: capacity, availability, and operating costs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Vehicle:
    """A delivery vehicle with capacity and availability window."""

    vehicle_id: int
    capacity: float
    start_time: float
    end_time: float
    cost_per_km: float = 1.0
    cost_per_hour: float = 10.0

    @property
    def available_window(self) -> tuple:
        return (self.start_time, self.end_time)
```

## src/optimization/decoder.py

```python
"""Decode raw QUBO samples into feasible routes."""

from __future__ import annotations

from typing import Any, Dict, List

from src.optimization.solution import Solution


class QUBODecoder:
    """Map binary QUBO samples to Solution objects."""

    def decode(self, sample: Dict[str, Any], instance: Any) -> Solution:
        raise NotImplementedError

    def decode_batch(self, samples: List[Dict[str, Any]], instance: Any) -> List[Solution]:
        raise NotImplementedError
```

## src/optimization/greedy.py

```python
"""
src/optimization/greedy.py

Greedy construction heuristic for CVRPTW: nearest-feasible-neighbor
insertion. For each vehicle, repeatedly picks the closest unassigned
customer that doesn't violate capacity or time window, until no
feasible customer remains, then moves to the next vehicle.

Operates on plain-dict instances (as produced by SyntheticGenerator /
CVRPLibLoader) and a travel-time matrix (as produced by Preprocessor).
Node indexing convention: 0 = depot, 1..N = customers in instance["customers"]
order -- matches Preprocessor._all_coords().

This is a fast, greedy baseline -- NOT optimal. Feeds into SimulatedAnnealing
as the initial solution to improve.
"""

from typing import Dict, List
from src.constraints.feasibility import FeasibilityChecker


class GreedySolver:

    def __init__(self):
        self.feasibility = FeasibilityChecker()

    def solve(self, instance: Dict, travel_time_s: List[List[float]]) -> Dict:
        """
        instance: plain-dict from SyntheticGenerator/CVRPLibLoader.
        travel_time_s: NxN matrix (seconds) from Preprocessor, node 0=depot.

        Returns dict:
        {
            "routes": [
                {
                    "vehicle_id": int,
                    "customer_ids": [ids in visit order],
                    "node_indices": [1-based indices into travel_time_s],
                    "arrival_times_min": [...],
                    "departure_times_min": [...],
                    "load": float,
                    "route_start_min": float,
                    "route_end_min": float,
                },
                ...
            ],
            "unrouted_customer_ids": [ids that couldn't be placed -- means
                                       infeasible instance for given fleet],
        }
        """
        customers = instance["customers"]
        vehicles = instance["vehicles"]
        n = len(customers)

        # index maps: node_index (1..n) <-> customer dict
        idx_to_customer = {i + 1: c for i, c in enumerate(customers)}
        unassigned = set(idx_to_customer.keys())

        routes = []

        for vehicle in vehicles:
            if not unassigned:
                break

            capacity = vehicle["capacity"]
            shift_start, shift_end = vehicle["shift_window"]

            route_nodes = []
            arrival_times = []
            departure_times = []
            current_node = 0  # depot
            current_time = shift_start
            load = 0.0

            while True:
                best_next = None
                best_dist = float("inf")

                for node_idx in unassigned:
                    customer = idx_to_customer[node_idx]
                    demand = customer["demand"]

                    if load + demand > capacity:
                        continue

                    travel_s = travel_time_s[current_node][node_idx]
                    travel_min = travel_s / 60.0
                    raw_arrival = current_time + travel_min
                    arrival = max(raw_arrival, customer["ready_time"])

                    if arrival > customer["due_time"]:
                        continue  # would be late, skip

                    service_end = arrival + customer["service_time"]
                    return_travel_min = travel_time_s[node_idx][0] / 60.0
                    if service_end + return_travel_min > shift_end:
                        continue  # can't get back to depot in time

                    if travel_s < best_dist:
                        best_dist = travel_s
                        best_next = node_idx
                        best_arrival = arrival
                        best_departure = service_end

                if best_next is None:
                    break  # no feasible customer left for this vehicle

                route_nodes.append(best_next)
                arrival_times.append(round(best_arrival, 2))
                departure_times.append(round(best_departure, 2))
                load += idx_to_customer[best_next]["demand"]
                current_node = best_next
                current_time = best_departure
                unassigned.remove(best_next)

            if route_nodes:
                return_travel_min = travel_time_s[current_node][0] / 60.0
                route_end = current_time + return_travel_min
                routes.append({
                    "vehicle_id": vehicle["id"],
                    "customer_ids": [idx_to_customer[i]["id"] for i in route_nodes],
                    "node_indices": route_nodes,
                    "arrival_times_min": arrival_times,
                    "departure_times_min": departure_times,
                    "load": load,
                    "route_start_min": shift_start,
                    "route_end_min": round(route_end, 2),
                })

        unrouted_ids = [idx_to_customer[i]["id"] for i in unassigned]

        return {
            "routes": routes,
            "unrouted_customer_ids": unrouted_ids,
        }
```

## src/optimization/neighborhood.py

```python
"""
src/optimization/neighborhood.py

Local search neighborhood operators for CVRPTW solutions. A solution here
is represented as a list of routes, each route a plain list of node
indices (1..N, depot=0 implicit at start/end, NOT included in the list).

Operators:
- swap_within_route: swap two customers in the same route
- relocate_within_route: move a customer to a different position in same route
- two_opt_within_route: reverse a segment (classic 2-opt)
- relocate_between_routes: move a customer from one route to another
- swap_between_routes: swap customers between two different routes

random_neighbor() picks a random move type and applies it, returning a
new solution (deep-copied) -- used by SimulatedAnnealing each iteration.
"""

import copy
import random
from typing import List


class NeighborhoodOperators:

    def __init__(self, seed: int = None):
        self.rng = random.Random(seed)

    def swap_within_route(self, route: List[int], i: int, j: int) -> List[int]:
        new_route = route[:]
        new_route[i], new_route[j] = new_route[j], new_route[i]
        return new_route

    def relocate_within_route(self, route: List[int], i: int, j: int) -> List[int]:
        new_route = route[:]
        node = new_route.pop(i)
        new_route.insert(j, node)
        return new_route

    def two_opt_within_route(self, route: List[int], i: int, j: int) -> List[int]:
        if i > j:
            i, j = j, i
        new_route = route[:i] + route[i:j + 1][::-1] + route[j + 1:]
        return new_route

    def relocate_between_routes(self, routes: List[List[int]], r1: int, i: int,
                                 r2: int, j: int) -> List[List[int]]:
        new_routes = copy.deepcopy(routes)
        node = new_routes[r1].pop(i)
        new_routes[r2].insert(j, node)
        return new_routes

    def swap_between_routes(self, routes: List[List[int]], r1: int, i: int,
                             r2: int, j: int) -> List[List[int]]:
        new_routes = copy.deepcopy(routes)
        new_routes[r1][i], new_routes[r2][j] = new_routes[r2][j], new_routes[r1][i]
        return new_routes

    def random_neighbor(self, routes: List[List[int]]) -> List[List[int]]:
        """
        Applies one random move to a copy of routes. Automatically picks
        a move type that's structurally valid given current route lengths
        (e.g. won't attempt 2-opt on a route with <2 customers).
        Returns a NEW routes list -- original is untouched.
        """
        routes = copy.deepcopy(routes)
        non_empty = [idx for idx, r in enumerate(routes) if len(r) >= 1]
        multi = [idx for idx, r in enumerate(routes) if len(r) >= 2]

        possible_moves = []
        if multi:
            possible_moves += ["swap_within", "relocate_within", "two_opt_within"]
        if len(non_empty) >= 2:
            possible_moves += ["relocate_between", "swap_between"]

        if not possible_moves:
            return routes  # nothing to mutate (e.g. all routes empty/singleton)

        move = self.rng.choice(possible_moves)

        if move == "swap_within":
            r = self.rng.choice(multi)
            i, j = self.rng.sample(range(len(routes[r])), 2)
            routes[r] = self.swap_within_route(routes[r], i, j)

        elif move == "relocate_within":
            r = self.rng.choice(multi)
            i, j = self.rng.sample(range(len(routes[r])), 2)
            routes[r] = self.relocate_within_route(routes[r], i, j)

        elif move == "two_opt_within":
            r = self.rng.choice(multi)
            i, j = self.rng.sample(range(len(routes[r])), 2)
            routes[r] = self.two_opt_within_route(routes[r], i, j)

        elif move == "relocate_between":
            r1, r2 = self.rng.sample(non_empty, 2) if len(non_empty) >= 2 else (non_empty[0], non_empty[0])
            if len(routes[r1]) == 0:
                return routes
            i = self.rng.randrange(len(routes[r1]))
            j = self.rng.randrange(len(routes[r2]) + 1)
            routes = self.relocate_between_routes(routes, r1, i, r2, j)

        elif move == "swap_between":
            candidates = [idx for idx in non_empty if len(routes[idx]) >= 1]
            if len(candidates) < 2:
                return routes
            r1, r2 = self.rng.sample(candidates, 2)
            i = self.rng.randrange(len(routes[r1]))
            j = self.rng.randrange(len(routes[r2]))
            routes = self.swap_between_routes(routes, r1, i, r2, j)

        return routes
```

## src/optimization/quantum_solver.py

```python
"""Interface to quantum / QUBO solvers (simulators and hardware)."""

from __future__ import annotations

from typing import Any, Dict


class QuantumSolver:
    """Solve a QUBO using a backend (simulator or QPU)."""

    def __init__(self, backend: str = "simulated", config: Dict[str, Any] | None = None) -> None:
        self.backend = backend
        self.config = config or {}

    def solve(self, q: Any) -> Dict[str, Any]:
        raise NotImplementedError
```

## src/optimization/qubo_model.py

```python
"""QUBO formulation of the routing problem."""

from __future__ import annotations

from typing import Any, Dict

import numpy as np

from src.models.problem_instance import ProblemInstance


class QUBOModel:
    """Map the CVRPTW problem onto a QUBO matrix."""

    def __init__(self, penalty_weights: Dict[str, float] | None = None) -> None:
        self.penalty_weights = penalty_weights or {}

    def build(self, instance: ProblemInstance) -> np.ndarray:
        raise NotImplementedError

    def to_bqm(self, q: np.ndarray) -> Any:
        raise NotImplementedError
```

## src/optimization/simulated_annealing.py

```python
"""
src/optimization/simulated_annealing.py

Simulated Annealing metaheuristic for CVRPTW. Takes a starting solution
(e.g. from GreedySolver) and improves it via random neighborhood moves,
accepting worse solutions probabilistically (classic SA) to escape local
optima. Uses soft penalties for capacity/time-window/overtime violations
so SA can explore through infeasible territory rather than getting stuck.

Solution format used internally: list of routes, each route a plain list
of node indices (1..N), depot=0 implicit. Convert to/from GreedySolver's
richer dict format at the boundary (see routes_from_greedy / to_greedy_format).
"""

import math
import random
import copy
from typing import Dict, List, Tuple

from src.cost.distance_cost import DistanceCost
from src.cost.late_penalty import LatePenalty
from src.cost.operating_cost import OperatingCost
from src.constraints.capacity import CapacityConstraint
from src.constraints.vehicle_availability import VehicleAvailabilityConstraint
from src.optimization.neighborhood import NeighborhoodOperators


class SolutionEvaluator:
    """Simulates a fixed route order and computes total weighted cost,
    including soft penalties for constraint violations."""

    def __init__(self, instance: Dict, distance_km_matrix: List[List[float]],
                 travel_time_s_matrix: List[List[float]],
                 weights: Dict[str, float] = None):
        self.instance = instance
        self.distance_km_matrix = distance_km_matrix
        self.travel_time_s_matrix = travel_time_s_matrix
        self.customers = instance["customers"]
        self.idx_to_customer = {i + 1: c for i, c in enumerate(self.customers)}

        default_weights = {
            "distance": 1.0,
            "late_penalty": 2.0,
            "operating": 1.0,
            "capacity_violation": 50.0,
            "overtime_violation": 20.0,
            "unrouted_penalty": 500.0,
        }
        self.weights = {**default_weights, **(weights or {})}

        self.distance_cost = DistanceCost()
        self.late_penalty = LatePenalty()
        self.operating_cost = OperatingCost()
        self.capacity = CapacityConstraint()
        self.availability = VehicleAvailabilityConstraint()

    def simulate_route(self, vehicle: Dict, node_sequence: List[int]) -> Dict:
        """Forward-simulate a fixed customer order for one vehicle.
        Returns timing/load info needed for cost + feasibility checks."""
        shift_start, shift_end = vehicle["shift_window"]
        current_node = 0
        current_time = shift_start
        load = 0.0
        arrival_times = []
        due_times = []
        distance_km = 0.0

        for node_idx in node_sequence:
            customer = self.idx_to_customer[node_idx]
            travel_min = self.travel_time_s_matrix[current_node][node_idx] / 60.0
            distance_km += self.distance_km_matrix[current_node][node_idx]
            raw_arrival = current_time + travel_min
            arrival = max(raw_arrival, customer["ready_time"])
            arrival_times.append(arrival)
            due_times.append(customer["due_time"])
            current_time = arrival + customer["service_time"]
            load += customer["demand"]
            current_node = node_idx

        # return to depot
        return_min = self.travel_time_s_matrix[current_node][0] / 60.0
        distance_km += self.distance_km_matrix[current_node][0]
        route_end = current_time + return_min

        return {
            "arrival_times_min": arrival_times,
            "due_times_min": due_times,
            "load": load,
            "route_end_min": route_end,
            "distance_km": distance_km,
        }

    def route_cost(self, vehicle: Dict, node_sequence: List[int]) -> float:
        if not node_sequence:
            return 0.0
        sim = self.simulate_route(vehicle, node_sequence)

        c_distance = self.distance_cost.cost(sim["distance_km"])
        c_late = self.late_penalty.route_penalty(sim["arrival_times_min"], sim["due_times_min"])
        route_duration_hours = (sim["route_end_min"] - vehicle["shift_window"][0]) / 60.0
        c_operating = self.operating_cost.vehicle_cost(route_duration_hours)

        demands = [self.idx_to_customer[n]["demand"] for n in node_sequence]
        c_capacity_violation = self.capacity.violation_amount(demands, vehicle["capacity"])
        c_overtime = self.availability.overtime_amount(sim["route_end_min"], vehicle["shift_window"])

        total = (self.weights["distance"] * c_distance
                 + self.weights["late_penalty"] * c_late
                 + self.weights["operating"] * c_operating
                 + self.weights["capacity_violation"] * c_capacity_violation
                 + self.weights["overtime_violation"] * c_overtime)
        return total

    def solution_cost(self, routes: List[List[int]]) -> float:
        vehicles = self.instance["vehicles"]
        total = 0.0
        routed_ids = set()
        for vehicle, node_seq in zip(vehicles, routes):
            total += self.route_cost(vehicle, node_seq)
            routed_ids.update(node_seq)

        all_ids = set(self.idx_to_customer.keys())
        num_unrouted = len(all_ids - routed_ids)
        total += num_unrouted * self.weights["unrouted_penalty"]
        return total


class SimulatedAnnealing:

    def __init__(self, evaluator: SolutionEvaluator,
                 initial_temp: float = 1000.0, cooling_rate: float = 0.995,
                 min_temp: float = 1.0, max_iterations: int = 5000,
                 seed: int = None):
        self.evaluator = evaluator
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.min_temp = min_temp
        self.max_iterations = max_iterations
        self.ops = NeighborhoodOperators(seed=seed)
        self.rng = random.Random(seed)

    def solve(self, initial_routes: List[List[int]]) -> Dict:
        """
        initial_routes: list of node-index lists, one per vehicle (from
        GreedySolver output, converted via routes_from_greedy()).

        Returns dict: {best_routes, best_cost, cost_history}
        """
        current_routes = copy.deepcopy(initial_routes)
        current_cost = self.evaluator.solution_cost(current_routes)

        best_routes = copy.deepcopy(current_routes)
        best_cost = current_cost

        temp = self.initial_temp
        cost_history = [current_cost]

        iteration = 0
        while temp > self.min_temp and iteration < self.max_iterations:
            candidate_routes = self.ops.random_neighbor(current_routes)
            candidate_cost = self.evaluator.solution_cost(candidate_routes)

            delta = candidate_cost - current_cost
            if delta < 0 or self.rng.random() < math.exp(-delta / temp):
                current_routes = candidate_routes
                current_cost = candidate_cost

                if current_cost < best_cost:
                    best_routes = copy.deepcopy(current_routes)
                    best_cost = current_cost

            cost_history.append(current_cost)
            temp *= self.cooling_rate
            iteration += 1

        return {
            "best_routes": best_routes,
            "best_cost": best_cost,
            "cost_history": cost_history,
            "iterations_run": iteration,
        }


def routes_from_greedy(greedy_solution: Dict, num_vehicles: int) -> List[List[int]]:
    """
    Converts GreedySolver output (list of route dicts, one per USED vehicle)
    into a fixed-length list of node-index lists, one per vehicle slot
    (empty list if that vehicle was unused by greedy).
    """
    routes = [[] for _ in range(num_vehicles)]
    for i, route in enumerate(greedy_solution["routes"]):
        if i < num_vehicles:
            routes[i] = route["node_indices"][:]
    return routes
```

## src/optimization/solution.py

```python
"""Solution representation: set of routes with cost."""

from __future__ import annotations

from typing import List

from src.models.route import Route


class Solution:
    """A candidate solution to the routing problem."""

    def __init__(self, routes: List[Route]) -> None:
        self.routes = routes
        self.cost: float = float("inf")
        self.feasible: bool = False

    def total_cost(self) -> float:
        return self.cost

    def num_routes(self) -> int:
        return len(self.routes)

    def __repr__(self) -> str:
        return f"Solution(routes={len(self.routes)}, cost={self.cost:.2f}, feasible={self.feasible})"
```

## src/routing/osrm_client.py

```python
"""
src/routing/osrm_client.py

Real road distance + geometry via OSRM public demo server (or self-hosted).
NOTE: OSRM public server has NO live traffic. Duration returned is free-flow
estimate only. Use this for real road distance/route shape. For traffic-
adjusted duration, use google_traffic_client.py instead.
"""

import requests
import time
from typing import List, Tuple, Optional


class OSRMClient:
    """
    Query OSRM HTTP API for real road routing.

    Public server: http://router.project-osrm.org (rate-limited, free-flow only)
    Self-hosted: point base_url to your local OSRM instance for reliability.
    """

    def __init__(self, base_url: str = "http://router.project-osrm.org",
                 profile: str = "driving", timeout: int = 10,
                 max_retries: int = 3):
        self.base_url = base_url.rstrip("/")
        self.profile = profile
        self.timeout = timeout
        self.max_retries = max_retries

    def route(self, coord_from: Tuple[float, float],
              coord_to: Tuple[float, float]) -> Optional[dict]:
        """
        Get route between two points.
        coord_from / coord_to: (lat, lon)
        Returns dict with distance_m, duration_s, geometry (list of lat/lon)
        or None if request fails after retries.
        """
        lon1, lat1 = coord_from[1], coord_from[0]
        lon2, lat2 = coord_to[1], coord_to[0]
        url = (f"{self.base_url}/route/v1/{self.profile}/"
               f"{lon1},{lat1};{lon2},{lat2}")
        params = {"overview": "full", "geometries": "geojson"}

        for attempt in range(self.max_retries):
            try:
                resp = requests.get(url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                if data.get("code") != "Ok":
                    return None
                route = data["routes"][0]
                coords = route["geometry"]["coordinates"]  # [lon, lat] pairs
                geometry = [(lat, lon) for lon, lat in coords]
                return {
                    "distance_m": route["distance"],
                    "duration_s": route["duration"],  # free-flow, no traffic
                    "geometry": geometry,
                }
            except (requests.RequestException, KeyError, IndexError):
                if attempt < self.max_retries - 1:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                return None
        return None

    def table(self, coords: List[Tuple[float, float]]) -> Optional[dict]:
        """
        Batch distance/duration matrix for N points in one call.
        coords: list of (lat, lon). Returns dict with distances_m and
        durations_s matrices (NxN), free-flow only.
        Use this instead of calling route() in a loop -- far fewer requests.
        """
        coord_str = ";".join(f"{lon},{lat}" for lat, lon in coords)
        url = f"{self.base_url}/table/v1/{self.profile}/{coord_str}"
        params = {"annotations": "distance,duration"}

        for attempt in range(self.max_retries):
            try:
                resp = requests.get(url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                if data.get("code") != "Ok":
                    return None
                return {
                    "distances_m": data["distances"],
                    "durations_s": data["durations"],
                }
            except (requests.RequestException, KeyError):
                if attempt < self.max_retries - 1:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                return None
        return None
```

## src/routing/road_routes.py

```python
"""Real-road route helpers."""

from __future__ import annotations

from typing import List, Tuple

import numpy as np


class RoadRoutes:
    """Build road-network distance / time matrices via OSRM."""

    def build_distance_matrix(self, coords: List[Tuple[float, float]]) -> np.ndarray:
        raise NotImplementedError

    def build_travel_time_matrix(self, coords: List[Tuple[float, float]]) -> np.ndarray:
        raise NotImplementedError
```

## src/traffic/google_traffic_client.py

```python
"""
src/traffic/google_traffic_client.py

Real traffic-aware travel time via Google Distance Matrix API.
Requires GOOGLE_MAPS_API_KEY. Falls back to None on any failure --
caller (travel_time.py) should fall back to synthetic profile.

Cost note: Distance Matrix API is paid past free tier. Batch requests
(multiple origins/destinations per call) to minimize calls -- one call
per route-leg is expensive at scale.
"""

import os
import requests
from typing import List, Tuple, Optional


class GoogleTrafficClient:

    BASE_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"

    def __init__(self, api_key: Optional[str] = None, timeout: int = 10):
        self.api_key = api_key or os.environ.get("GOOGLE_MAPS_API_KEY")
        self.timeout = timeout

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def duration_matrix(self, origins: List[Tuple[float, float]],
                         destinations: List[Tuple[float, float]],
                         departure_time: str = "now") -> Optional[dict]:
        """
        origins/destinations: list of (lat, lon)
        departure_time: "now" or unix timestamp (must be future/present,
        Google traffic model needs a real departure time, not past).
        Returns dict with duration_s (free-flow) and duration_in_traffic_s
        (traffic-adjusted) matrices, shape len(origins) x len(destinations).
        """
        if not self.is_configured():
            return None

        origins_str = "|".join(f"{lat},{lon}" for lat, lon in origins)
        dests_str = "|".join(f"{lat},{lon}" for lat, lon in destinations)

        params = {
            "origins": origins_str,
            "destinations": dests_str,
            "departure_time": departure_time,
            "traffic_model": "best_guess",
            "key": self.api_key,
        }

        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != "OK":
                return None

            n_o, n_d = len(origins), len(destinations)
            duration_s = [[None] * n_d for _ in range(n_o)]
            duration_in_traffic_s = [[None] * n_d for _ in range(n_o)]
            distance_m = [[None] * n_d for _ in range(n_o)]

            for i, row in enumerate(data["rows"]):
                for j, elem in enumerate(row["elements"]):
                    if elem.get("status") != "OK":
                        continue
                    duration_s[i][j] = elem["duration"]["value"]
                    distance_m[i][j] = elem["distance"]["value"]
                    # duration_in_traffic only present if departure_time set
                    if "duration_in_traffic" in elem:
                        duration_in_traffic_s[i][j] = elem["duration_in_traffic"]["value"]
                    else:
                        duration_in_traffic_s[i][j] = elem["duration"]["value"]

            return {
                "duration_s": duration_s,
                "duration_in_traffic_s": duration_in_traffic_s,
                "distance_m": distance_m,
            }
        except (requests.RequestException, KeyError, IndexError):
            return None
```

## src/traffic/traffic_model.py

```python
"""Dynamic traffic model over the road network."""

from __future__ import annotations

from typing import Any, Dict


class TrafficModel:
    """Hold and query time-dependent congestion factors."""

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        self.config = config or {}

    def congestion_factor(self, edge: Any, time: float) -> float:
        raise NotImplementedError

    def speed_at(self, edge: Any, time: float) -> float:
        raise NotImplementedError
```

## src/traffic/traffic_profiles.py

```python
"""
src/traffic/traffic_profiles.py

Synthetic congestion multipliers by hour-of-day. Used as fallback when
real traffic APIs (Google) are unavailable, and as the multiplier applied
on top of OSRM's free-flow duration.
"""


class TrafficProfiles:

    # hour (0-23) -> congestion multiplier vs free-flow
    DEFAULT_PROFILE = {
        0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.05,
        6: 1.2, 7: 1.7, 8: 2.0, 9: 1.6, 10: 1.2, 11: 1.15,
        12: 1.25, 13: 1.2, 14: 1.15, 15: 1.2, 16: 1.4,
        17: 1.9, 18: 2.1, 19: 1.7, 20: 1.3, 21: 1.1,
        22: 1.05, 23: 1.0,
    }

    def __init__(self, profile: dict = None):
        self.profile = profile or self.DEFAULT_PROFILE

    def get_factor(self, hour: int) -> float:
        hour = int(hour) % 24
        return self.profile.get(hour, 1.0)
```

## src/traffic/travel_time.py

```python
"""
src/traffic/travel_time.py

Computes travel time between two points. Tries real traffic source first
(Google Distance Matrix), falls back to OSRM free-flow, falls back to
synthetic profile multiplier if no internet/API key. Demo never breaks.
"""

from typing import Tuple, Optional
from src.traffic.traffic_profiles import TrafficProfiles
from src.traffic.google_traffic_client import GoogleTrafficClient
from src.routing.osrm_client import OSRMClient


class TravelTime:

    def __init__(self, use_real_traffic: bool = True,
                 google_api_key: Optional[str] = None,
                 osrm_base_url: str = "http://router.project-osrm.org"):
        self.use_real_traffic = use_real_traffic
        self.google_client = GoogleTrafficClient(api_key=google_api_key)
        self.osrm_client = OSRMClient(base_url=osrm_base_url)
        self.profiles = TrafficProfiles()

    def compute(self, coord_from: Tuple[float, float],
                coord_to: Tuple[float, float],
                euclidean_distance_km: float,
                departure_hour: int,
                avg_speed_kmh: float = 40.0) -> dict:
        """
        Returns dict: {travel_time_s, distance_km, source, congestion_factor}
        source in {"google_traffic", "osrm_freeflow", "synthetic"}
        """
        # 1. Try real traffic-aware duration (Google)
        if self.use_real_traffic and self.google_client.is_configured():
            result = self.google_client.duration_matrix(
                [coord_from], [coord_to], departure_time="now"
            )
            if result and result["duration_in_traffic_s"][0][0] is not None:
                duration_s = result["duration_in_traffic_s"][0][0]
                free_flow_s = result["duration_s"][0][0]
                distance_km = result["distance_m"][0][0] / 1000.0
                congestion_factor = (duration_s / free_flow_s
                                     if free_flow_s else 1.0)
                return {
                    "travel_time_s": duration_s,
                    "distance_km": distance_km,
                    "source": "google_traffic",
                    "congestion_factor": round(congestion_factor, 3),
                }

        # 2. Try OSRM real road distance (free-flow only), apply synthetic
        #    congestion multiplier on top since OSRM has no live traffic
        if self.use_real_traffic:
            route = self.osrm_client.route(coord_from, coord_to)
            if route:
                congestion_factor = self.profiles.get_factor(departure_hour)
                travel_time_s = route["duration_s"] * congestion_factor
                return {
                    "travel_time_s": travel_time_s,
                    "distance_km": route["distance_m"] / 1000.0,
                    "source": "osrm_freeflow+synthetic_congestion",
                    "congestion_factor": congestion_factor,
                }

        # 3. Full fallback: pure synthetic (no API/internet needed)
        congestion_factor = self.profiles.get_factor(departure_hour)
        base_time_s = (euclidean_distance_km / avg_speed_kmh) * 3600.0
        travel_time_s = base_time_s * congestion_factor
        return {
            "travel_time_s": travel_time_s,
            "distance_km": euclidean_distance_km,
            "source": "synthetic",
            "congestion_factor": congestion_factor,
        }
```

## src/utils/helpers.py

```python
"""General helper functions."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import numpy as np


def ensure_dir(path: str) -> str:
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


def save_json(data: Any, path: str) -> None:
    ensure_dir(os.path.dirname(path))
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def load_json(path: str) -> Any:
    with open(path) as f:
        return json.load(f)


def hash_string(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def set_seed(seed: int) -> None:
    np.random.seed(seed)
```

## src/utils/logger.py

```python
"""Logging setup."""

from __future__ import annotations

import logging
import sys


def get_logger(name: str = "qorbit") -> logging.Logger:
    """Return a configured logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
```

## src/utils/timer.py

```python
"""Execution timer."""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator


class Timer:
    """Simple elapsed-time context manager."""

    def __init__(self) -> None:
        self.start_time: float = 0.0
        self.elapsed: float = 0.0

    def start(self) -> None:
        self.start_time = time.perf_counter()

    def stop(self) -> float:
        self.elapsed = time.perf_counter() - self.start_time
        return self.elapsed

    @contextmanager
    def time(self) -> Iterator["Timer"]:
        self.start()
        try:
            yield self
        finally:
            self.stop()
```

## src/visualization/animation.py

```python
"""Route animation."""

from __future__ import annotations

from typing import List


class Animation:
    """Animate route construction or vehicle movement."""

    def animate(self, frames: List, output_path: str, **kwargs) -> None:
        raise NotImplementedError
```

## src/visualization/convergence_plot.py

```python
"""Convergence curve plot."""

from __future__ import annotations

from typing import List


class ConvergencePlot:
    """Plot objective value across iterations."""

    def plot(self, history: List[float], ax=None, **kwargs):
        raise NotImplementedError
```

## src/visualization/map_visualization.py

```python
"""Interactive map visualization (folium / mapbox)."""

from __future__ import annotations

from src.optimization.solution import Solution


class MapVisualization:
    """Render routes on an interactive map."""

    def render(self, solution: Solution, output_path: str) -> None:
        raise NotImplementedError
```

## src/visualization/route_plot.py

```python
"""Static route plot."""

from __future__ import annotations

from src.optimization.solution import Solution


class RoutePlot:
    """Draw routes on a 2D plane."""

    def plot(self, solution: Solution, ax=None, **kwargs):
        raise NotImplementedError
```


