"""Performance metrics for solutions."""

from __future__ import annotations

from typing import Any

import numpy as np


class Metrics:
    """Compute gap, runtime, and quality statistics."""

    def cost(self, solution: Any) -> float:
        raise NotImplementedError

    def gap_to_best(self, cost: float, best: float) -> float:
        return (cost - best) / best

    def statistics(self, costs: np.ndarray) -> dict:
        raise NotImplementedError
