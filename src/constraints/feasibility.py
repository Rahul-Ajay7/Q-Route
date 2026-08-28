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
