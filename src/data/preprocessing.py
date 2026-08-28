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
