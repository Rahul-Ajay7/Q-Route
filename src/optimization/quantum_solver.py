"""Interface to quantum / QUBO solvers (simulators and hardware)."""

from __future__ import annotations

from typing import Any, Dict


class QuantumSolver:
    """Solve a QUBO using a backend (simulator or QPU)."""

    def __init__(self, backend: str = "simulated", config: Dict[str, Any] | None = None) -> None:
        self.backend = backend
        self.config = config or {}

    def solve(self, q: Any) -> Dict[str, Any]:
        raise NotImplementedError
