"""Generate synthetic customers, vehicles, and traffic profiles."""

from __future__ import annotations

from typing import Any, Dict


class SyntheticGenerator:
    """Create random CVRPTW instances and traffic conditions."""

    def generate_customers(self, n: int, seed: int) -> Any:
        raise NotImplementedError

    def generate_vehicles(self, n: int, capacity: float, seed: int) -> Any:
        raise NotImplementedError

    def generate_traffic(self, grid_size: int, seed: int) -> Any:
        raise NotImplementedError

    def generate_instance(self, config: Dict[str, Any]) -> Any:
        raise NotImplementedError
