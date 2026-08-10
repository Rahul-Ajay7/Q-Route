"""Compare solver performance across instances."""

from __future__ import annotations

from typing import Dict


class Comparison:
    """Build comparison tables between solvers."""

    def build_table(self, results: Dict) -> object:
        raise NotImplementedError
