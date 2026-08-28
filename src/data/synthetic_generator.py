"""
src/data/synthetic_generator.py

Generates random CVRPTW problem instances for testing solvers without
needing real CVRPLIB data. Produces plain dicts -- wrap into your
ProblemInstance/Customer/Vehicle dataclasses in instance_loader.py or
directly where consumed, adjusting field names to match src/models/*.py.
"""

import random
from typing import Dict, List, Tuple


class SyntheticGenerator:

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate(self, num_customers: int = 20, num_vehicles: int = 4,
                 area_size: float = 100.0, vehicle_capacity: float = 100.0,
                 demand_range: Tuple[int, int] = (5, 25),
                 depot_coord: Tuple[float, float] = None,
                 time_horizon_min: float = 480.0,
                 window_width_min: Tuple[float, float] = (30, 90),
                 service_time_min: float = 10.0) -> Dict:
        """
        Returns a plain-dict instance:
        {
            "depot": {"coord": (x,y)},
            "customers": [
                {"id": int, "coord": (x,y), "demand": float,
                 "ready_time": float, "due_time": float,
                 "service_time": float},
                ...
            ],
            "vehicles": [
                {"id": int, "capacity": float,
                 "shift_window": (start_min, end_min)},
                ...
            ],
        }
        """
        depot_coord = depot_coord or (area_size / 2, area_size / 2)

        customers = []
        for cid in range(1, num_customers + 1):
            coord = (self.rng.uniform(0, area_size), self.rng.uniform(0, area_size))
            demand = self.rng.randint(*demand_range)
            ready = self.rng.uniform(0, time_horizon_min - window_width_min[1])
            width = self.rng.uniform(*window_width_min)
            due = min(ready + width, time_horizon_min)
            customers.append({
                "id": cid,
                "coord": coord,
                "demand": demand,
                "ready_time": round(ready, 1),
                "due_time": round(due, 1),
                "service_time": service_time_min,
            })

        vehicles = [
            {
                "id": vid,
                "capacity": vehicle_capacity,
                "shift_window": (0.0, time_horizon_min),
            }
            for vid in range(1, num_vehicles + 1)
        ]

        return {
            "depot": {"coord": depot_coord},
            "customers": customers,
            "vehicles": vehicles,
        }

    def generate_lat_lon(self, num_customers: int = 20, num_vehicles: int = 4,
                          center: Tuple[float, float] = (13.0827, 80.2707),
                          radius_km: float = 15.0, **kwargs) -> Dict:
        """
        Same as generate() but produces real-world (lat, lon) coordinates
        scattered around a center point (default: Chennai). Use this when
        feeding into OSRM/Google traffic clients, which need real coords.
        1 degree lat ~= 111 km. Approximate, fine for demo purposes.
        """
        deg_radius = radius_km / 111.0
        lat_c, lon_c = center

        instance = self.generate(num_customers=num_customers, num_vehicles=num_vehicles,
                                  area_size=1.0, **kwargs)

        # overwrite coords with real lat/lon scattered around center
        import math
        instance["depot"]["coord"] = center
        for c in instance["customers"]:
            r = self.rng.uniform(0, deg_radius)
            theta = self.rng.uniform(0, 2 * math.pi)
            c["coord"] = (lat_c + r * math.cos(theta), lon_c + r * math.sin(theta))

        return instance
