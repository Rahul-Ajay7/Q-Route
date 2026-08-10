"""Vehicle operating cost."""

from __future__ import annotations

from src.models.route import Route


class OperatingCost:
    """Cost of using a vehicle (fixed + per-time)."""

    def compute(self, route: Route) -> float:
        raise NotImplementedError
