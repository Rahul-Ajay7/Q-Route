"""Route entity: ordered sequence of customers served by one vehicle."""

from __future__ import annotations

from typing import List

from src.models.customer import Customer


class Route:
    """An ordered tour for a single vehicle."""

    def __init__(self, vehicle_id: int, customers: List[Customer] | None = None) -> None:
        self.vehicle_id = vehicle_id
        self.customers: List[Customer] = customers or []

    def add(self, customer: Customer) -> None:
        self.customers.append(customer)

    def total_demand(self) -> float:
        return sum(c.demand for c in self.customers)

    def __len__(self) -> int:
        return len(self.customers)
