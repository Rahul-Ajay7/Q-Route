"""Vehicle availability (shift window) constraint."""

from __future__ import annotations

from src.models.route import Route


class VehicleAvailabilityConstraint:
    """Check that a route fits within the vehicle's shift window."""

    def is_satisfied(self, route: Route) -> bool:
        raise NotImplementedError

    def violation(self, route: Route) -> float:
        raise NotImplementedError
