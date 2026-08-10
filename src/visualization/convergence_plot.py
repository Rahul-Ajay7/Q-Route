"""Convergence curve plot."""

from __future__ import annotations

from typing import List


class ConvergencePlot:
    """Plot objective value across iterations."""

    def plot(self, history: List[float], ax=None, **kwargs):
        raise NotImplementedError
