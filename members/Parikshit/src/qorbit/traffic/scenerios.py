"""Seeded traffic events. Same seed -> same disruption for every method."""
import numpy as np
from ..models import ProblemInstance
from .traffic_model import TrafficEvent


def corridor_event(inst: ProblemInstance, rng: np.random.Generator, factor: float = 2.5,
                   start_range=(8.5, 9.5), duration: float = 3.0) -> TrafficEvent:
    """One zone (chosen proportionally to its customer count) slows by `factor`."""
    zone = int(rng.choice(inst.zones[1:]))
    start = float(rng.uniform(*start_range))
    return TrafficEvent(frozenset({zone}), start, start + duration, factor)