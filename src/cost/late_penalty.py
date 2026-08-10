"""Late arrival penalty."""

from __future__ import annotations

from src.models.route import Route


class LatePenalty:
    """Penalty for violating customer due times."""

    def compute(self, route: Route) -> float:
        raise NotImplementedError
