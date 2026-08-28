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
