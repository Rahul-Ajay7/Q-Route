"""Depot entity: origin and destination of all routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass
class Depot:
    """Central depot where vehicles start and end."""

    depot_id: int
    x: float
    y: float
    return_to_depot: bool = True

    @property
    def location(self) -> Tuple[float, float]:
        return (self.x, self.y)
