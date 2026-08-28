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
