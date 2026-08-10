"""OSRM HTTP client."""

from __future__ import annotations

from typing import Any, Dict


class OSRMClient:
    """Query OSRM for route distance and duration."""

    def __init__(self, base_url: str = "http://localhost:5000") -> None:
        self.base_url = base_url

    def route(self, coords: list) -> Dict[str, Any]:
        raise NotImplementedError

    def table(self, coords: list) -> Dict[str, Any]:
        raise NotImplementedError
