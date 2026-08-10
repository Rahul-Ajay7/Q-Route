"""Simulated annealing metaheuristic."""

from __future__ import annotations

from src.cost.objective import ObjectiveFunction
from src.models.problem_instance import ProblemInstance
from src.optimization.solution import Solution


class SimulatedAnnealing:
    """Improve an initial solution via simulated annealing."""

    def __init__(
        self,
        objective: ObjectiveFunction,
        initial_temp: float = 100.0,
        cooling_rate: float = 0.98,
        max_iterations: int = 10000,
    ) -> None:
        self.objective = objective
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.max_iterations = max_iterations

    def solve(self, instance: ProblemInstance, initial: Solution | None = None) -> Solution:
        raise NotImplementedError
