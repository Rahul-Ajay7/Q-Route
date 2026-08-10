"""Customer entity: demand, location, and time window."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass
class Customer:
    """A customer requiring service within a time window."""

    customer_id: int
    x: float
    y: float
    demand: float
    ready_time: float
    due_time: float
    service_time: float = 0.0

    @property
    def location(self) -> Tuple[float, float]:
        return (self.x, self.y)
