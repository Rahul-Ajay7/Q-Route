"""Route animation."""

from __future__ import annotations

from typing import List


class Animation:
    """Animate route construction or vehicle movement."""

    def animate(self, frames: List, output_path: str, **kwargs) -> None:
        raise NotImplementedError
