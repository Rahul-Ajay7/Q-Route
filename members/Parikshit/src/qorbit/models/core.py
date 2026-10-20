from dataclasses import dataclass, field
import numpy as np


@dataclass(frozen=True)
class Customer:
    id: int                 # node index, 1..n (0 is the depot)
    demand: float
    ready: float = 0.0      # a_i (hours)
    due: float = float("inf")   # b_i (hours)
    service: float = 0.0    # hours


@dataclass(frozen=True)
class Vehicle:
    id: int
    capacity: float
    start_time: float = 8.0


@dataclass
class ProblemInstance:
    """Node 0 = depot. Matrices are (n+1)x(n+1), free-flow values."""
    customers: dict[int, Customer]
    vehicles: dict[int, Vehicle]
    dist_km: np.ndarray
    time_h: np.ndarray          # free-flow travel time (hours)
    zones: np.ndarray           # zone id per node (length n+1)
    depot_due: float = float("inf")
    coords: np.ndarray | None = None   # optional (n+1)x2 km coordinates, for plotting


@dataclass
class Solution:
    routes: dict[int, list[int]] = field(default_factory=dict)  # vehicle id -> customer ids

    def copy(self) -> "Solution":
        return Solution({v: list(r) for v, r in self.routes.items()})

    def visited(self) -> list[int]:
        return [c for r in self.routes.values() for c in r]