"""Convert raw inputs into processed distance / travel-time matrices."""

from __future__ import annotations

from typing import Any, Dict


class Preprocessor:
    """Build distance and travel-time matrices from raw coordinates."""

    def build_distance_matrix(self, coords) -> Any:
        raise NotImplementedError

    def build_travel_time_matrix(self, distances, traffic) -> Any:
        raise NotImplementedError

    def save_matrices(self, data: Dict[str, Any], out_dir: str) -> None:
        raise NotImplementedError
