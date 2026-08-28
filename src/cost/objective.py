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
