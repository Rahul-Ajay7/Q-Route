"""Load problem instances from processed files and directories."""

from __future__ import annotations

from typing import Any, Dict

from src.data.preprocessing import Preprocessor
from src.models.problem_instance import ProblemInstance


class InstanceLoader:
    """Load a ProblemInstance from a processed instance file."""

    def __init__(self) -> None:
        self._preprocessor = Preprocessor()

    def load(self, path: str) -> ProblemInstance:
        raise NotImplementedError

    def load_metadata(self, path: str) -> Dict[str, Any]:
        raise NotImplementedError
