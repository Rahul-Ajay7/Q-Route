"""Predefined traffic profiles (peak, off-peak, weekday, weekend)."""

from __future__ import annotations

from typing import Dict


class TrafficProfiles:
    """Named congestion curves by time of day."""

    PROFILES: Dict[str, dict] = {
        "free_flow": {"peak_factor": 1.0, "peak_hours": []},
        "urban_peak": {"peak_factor": 2.2, "peak_hours": [(7, 9), (17, 19)]},
        "weekend": {"peak_factor": 1.2, "peak_hours": [(11, 14)]},
    }

    def get(self, name: str) -> dict:
        return self.PROFILES[name]
