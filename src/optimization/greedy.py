"""Greedy construction heuristic."""

from __future__ import annotations

from src.cost.objective import ObjectiveFunction
from src.models.problem_instance import ProblemInstance
from src.optimization.solution import Solution


class GreedySolver:
    """Construct routes with a cheapest-insertion greedy heuristic."""

    def __init__(self, objective: ObjectiveFunction) -> None:
        self.objective = objective

    def solve(self, instance: ProblemInstance) -> Solution:
        raise NotImplementedError
