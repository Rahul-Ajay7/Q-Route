"""Random instances so experiments run without downloading anything."""
import math
import numpy as np
from ..models import Customer, Vehicle, ProblemInstance
from ..traffic import assign_grid_zones


def make_instance(n: int = 30, seed: int = 0, n_vehicles: int | None = None, capacity: float = 50.0,
                  extent_km: float = 30.0, grid: int = 3, speed_kmh: float = 40.0,
                  time_windows: bool = False, service_h: float = 0.1, start_time: float = 8.0) -> ProblemInstance:
    rng = np.random.default_rng(seed)
    xy = rng.uniform(0, extent_km, size=(n + 1, 2))
    xy[0] = (extent_km / 2, extent_km / 2)                      # depot in the middle
    dist = np.linalg.norm(xy[:, None] - xy[None], axis=2)
    demand = rng.integers(1, 10, size=n + 1).astype(float)
    if n_vehicles is None:
        n_vehicles = math.ceil(demand[1:].sum() / capacity) + 2
    customers = {}
    for i in range(1, n + 1):
        ready, due = (0.0, math.inf)
        if time_windows:
            ready = float(rng.uniform(start_time, start_time + 6)); due = ready + 2.0
        customers[i] = Customer(i, demand[i], ready, due, service_h)
    vehicles = {v: Vehicle(v, capacity, start_time) for v in range(1, n_vehicles + 1)}
    return ProblemInstance(customers, vehicles, dist, dist / speed_kmh,
                           assign_grid_zones(xy, grid), coords=xy)