"""QUBO formulation of the routing problem."""

from __future__ import annotations

from typing import Any, Dict

import numpy as np

from src.models.problem_instance import ProblemInstance


class QUBOModel:
    """Map the CVRPTW problem onto a QUBO matrix."""

    def __init__(self, penalty_weights: Dict[str, float] | None = None) -> None:
        self.penalty_weights = penalty_weights or {}

    def build(self, instance: ProblemInstance) -> np.ndarray:
        raise NotImplementedError

    def to_bqm(self, q: np.ndarray) -> Any:
        raise NotImplementedError
