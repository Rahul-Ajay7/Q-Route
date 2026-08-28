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
