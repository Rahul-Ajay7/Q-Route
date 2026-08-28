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
