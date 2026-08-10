"""Traffic-induced travel-time cost."""

from __future__ import annotations

from src.models.route import Route


class TrafficCost:
    """Cost reflecting congestion on traveled edges."""

    def compute(self, route: Route) -> float:
        raise NotImplementedError
