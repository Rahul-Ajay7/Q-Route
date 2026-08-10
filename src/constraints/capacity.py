"""Vehicle capacity constraint."""

from __future__ import annotations

from src.models.route import Route


class CapacityConstraint:
    """Check that route demand does not exceed vehicle capacity."""

    def is_satisfied(self, route: Route) -> bool:
        raise NotImplementedError

    def violation(self, route: Route) -> float:
        raise NotImplementedError
