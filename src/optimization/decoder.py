"""Decode raw QUBO samples into feasible routes."""

from __future__ import annotations

from typing import Any, Dict, List

from src.optimization.solution import Solution


class QUBODecoder:
    """Map binary QUBO samples to Solution objects."""

    def decode(self, sample: Dict[str, Any], instance: Any) -> Solution:
        raise NotImplementedError

    def decode_batch(self, samples: List[Dict[str, Any]], instance: Any) -> List[Solution]:
        raise NotImplementedError
