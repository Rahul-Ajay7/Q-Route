"""Run solvers across experiment configurations."""

from __future__ import annotations

from typing import Dict, List


class BenchmarkRunner:
    """Execute all configured solvers on a set of instances."""

    def run(self, configs: List[Dict]) -> Dict:
        raise NotImplementedError
