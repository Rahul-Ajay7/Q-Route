"""Weighted combination of all cost components."""

from __future__ import annotations

from typing import Dict

from src.cost.distance_cost import DistanceCost
from src.cost.late_penalty import LatePenalty
from src.cost.operating_cost import OperatingCost
from src.cost.traffic_cost import TrafficCost
from src.models.route import Route


class ObjectiveFunction:
    """Evaluate total weighted cost of a solution."""

    def __init__(self, weights: Dict[str, float] | None = None) -> None:
        self.weights = weights or {}
        self._distance = DistanceCost()
        self._traffic = TrafficCost()
        self._operating = OperatingCost()
        self._late = LatePenalty()

    def evaluate(self, route: Route) -> float:
        raise NotImplementedError
