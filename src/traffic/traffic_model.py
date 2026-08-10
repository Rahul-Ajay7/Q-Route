"""Dynamic traffic model over the road network."""

from __future__ import annotations

from typing import Any, Dict


class TrafficModel:
    """Hold and query time-dependent congestion factors."""

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        self.config = config or {}

    def congestion_factor(self, edge: Any, time: float) -> float:
        raise NotImplementedError

    def speed_at(self, edge: Any, time: float) -> float:
        raise NotImplementedError
