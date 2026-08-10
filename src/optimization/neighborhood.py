"""Local-search neighborhood operators."""

from __future__ import annotations

from src.optimization.solution import Solution


class NeighborhoodOperators:
    """Relocate, swap, and 2-opt moves."""

    def relocate(self, solution: Solution) -> Solution:
        raise NotImplementedError

    def swap(self, solution: Solution) -> Solution:
        raise NotImplementedError

    def two_opt(self, solution: Solution) -> Solution:
        raise NotImplementedError
