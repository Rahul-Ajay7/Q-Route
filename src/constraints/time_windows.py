"""Customer time-window constraint."""

from __future__ import annotations

from src.models.route import Route


class TimeWindowConstraint:
    """Check that each customer is served inside its time window."""

    def is_satisfied(self, route: Route) -> bool:
        raise NotImplementedError

    def violation(self, route: Route) -> float:
        raise NotImplementedError
