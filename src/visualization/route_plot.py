"""Static route plot."""

from __future__ import annotations

from src.optimization.solution import Solution


class RoutePlot:
    """Draw routes on a 2D plane."""

    def plot(self, solution: Solution, ax=None, **kwargs):
        raise NotImplementedError
