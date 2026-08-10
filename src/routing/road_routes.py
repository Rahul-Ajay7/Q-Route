"""Real-road route helpers."""

from __future__ import annotations

from typing import List, Tuple

import numpy as np


class RoadRoutes:
    """Build road-network distance / time matrices via OSRM."""

    def build_distance_matrix(self, coords: List[Tuple[float, float]]) -> np.ndarray:
        raise NotImplementedError

    def build_travel_time_matrix(self, coords: List[Tuple[float, float]]) -> np.ndarray:
        raise NotImplementedError
