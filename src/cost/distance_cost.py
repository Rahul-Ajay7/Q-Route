"""Distance-based travel cost."""

from __future__ import annotations

from src.models.route import Route


class DistanceCost:
    """Cost proportional to total route distance."""

    def compute(self, route: Route) -> float:
        raise NotImplementedError
