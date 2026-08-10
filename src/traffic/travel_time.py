"""Travel-time computation from distances and congestion."""

from __future__ import annotations

from typing import Any

import numpy as np


class TravelTime:
    """Compute edge travel times under current traffic conditions."""

    def compute(
        self,
        distance_matrix: np.ndarray,
        speeds: Any,
        congestion: Any,
        departure_time: float,
    ) -> np.ndarray:
        raise NotImplementedError
