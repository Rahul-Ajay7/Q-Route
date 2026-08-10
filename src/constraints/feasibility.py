"""Aggregate feasibility checker over all constraints."""

from __future__ import annotations

from typing import List

from src.constraints.capacity import CapacityConstraint
from src.constraints.time_windows import TimeWindowConstraint
from src.constraints.vehicle_availability import VehicleAvailabilityConstraint
from src.models.route import Route


class FeasibilityChecker:
    """Validate a solution against all hard constraints."""

    def __init__(self) -> None:
        self._checks = [
            CapacityConstraint(),
            TimeWindowConstraint(),
            VehicleAvailabilityConstraint(),
        ]

    def is_feasible(self, route: Route) -> bool:
        return all(c.is_satisfied(route) for c in self._checks)

    def violations(self, route: Route) -> List[float]:
        return [c.violation(route) for c in self._checks]
