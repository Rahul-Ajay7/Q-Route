"""Vehicle entity: capacity, availability, and operating costs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Vehicle:
    """A delivery vehicle with capacity and availability window."""

    vehicle_id: int
    capacity: float
    start_time: float
    end_time: float
    cost_per_km: float = 1.0
    cost_per_hour: float = 10.0

    @property
    def available_window(self) -> tuple:
        return (self.start_time, self.end_time)
