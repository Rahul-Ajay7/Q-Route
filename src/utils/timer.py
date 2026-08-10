"""Execution timer."""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator


class Timer:
    """Simple elapsed-time context manager."""

    def __init__(self) -> None:
        self.start_time: float = 0.0
        self.elapsed: float = 0.0

    def start(self) -> None:
        self.start_time = time.perf_counter()

    def stop(self) -> float:
        self.elapsed = time.perf_counter() - self.start_time
        return self.elapsed

    @contextmanager
    def time(self) -> Iterator["Timer"]:
        self.start()
        try:
            yield self
        finally:
            self.stop()
