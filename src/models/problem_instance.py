"""Full problem instance: depot, customers, vehicles, and matrices."""

from __future__ import annotations

from typing import Dict, List

import numpy as np

from src.models.customer import Customer
from src.models.depot import Depot
from src.models.vehicle import Vehicle


class ProblemInstance:
    """Container for all inputs of a CVRPTW problem."""

    def __init__(
        self,
        name: str,
        depot: Depot,
        customers: List[Customer],
        vehicles: List[Vehicle],
        distance_matrix: np.ndarray,
        travel_time_matrix: np.ndarray,
    ) -> None:
        self.name = name
        self.depot = depot
        self.customers = customers
        self.vehicles = vehicles
        self.distance_matrix = distance_matrix
        self.travel_time_matrix = travel_time_matrix
        self.metadata: Dict = {}

    @property
    def num_customers(self) -> int:
        return len(self.customers)

    @property
    def num_vehicles(self) -> int:
        return len(self.vehicles)
