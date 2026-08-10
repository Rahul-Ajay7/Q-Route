"""Parser for the standard CVRPLIB instance format."""

from __future__ import annotations

from typing import Any, Dict


class CVRPLibLoader:
    """Parse .vrp / .txt files from the CVRPLIB repository."""

    def parse(self, path: str) -> Dict[str, Any]:
        raise NotImplementedError

    def load(self, path: str) -> Dict[str, Any]:
        return self.parse(path)
