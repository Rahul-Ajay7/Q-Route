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
