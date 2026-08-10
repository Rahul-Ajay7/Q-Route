"""Solution representation: set of routes with cost."""

from __future__ import annotations

from typing import List

from src.models.route import Route


class Solution:
    """A candidate solution to the routing problem."""

    def __init__(self, routes: List[Route]) -> None:
        self.routes = routes
        self.cost: float = float("inf")
        self.feasible: bool = False

    def total_cost(self) -> float:
        return self.cost

    def num_routes(self) -> int:
        return len(self.routes)

    def __repr__(self) -> str:
        return f"Solution(routes={len(self.routes)}, cost={self.cost:.2f}, feasible={self.feasible})"
