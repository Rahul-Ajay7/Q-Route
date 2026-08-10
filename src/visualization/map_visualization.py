"""Interactive map visualization (folium / mapbox)."""

from __future__ import annotations

from src.optimization.solution import Solution


class MapVisualization:
    """Render routes on an interactive map."""

    def render(self, solution: Solution, output_path: str) -> None:
        raise NotImplementedError
