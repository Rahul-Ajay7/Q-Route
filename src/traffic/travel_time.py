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
