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
