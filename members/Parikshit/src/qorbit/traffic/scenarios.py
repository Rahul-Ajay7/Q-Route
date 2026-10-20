"""Seeded traffic events. Same seed -> same disruption for every method."""
import numpy as np
from ..models import ProblemInstance
from .traffic_model import TrafficEvent


def corridor_event(inst: ProblemInstance, rng: np.random.Generator, factor: float = 2.5,
                   start_range=(8.5, 9.5), duration: float = 3.0, n_zones: int = 1) -> TrafficEvent:
    """`n_zones` distinct zones (chosen proportionally to their customer counts) slow by `factor`."""
    zs = inst.zones[1:]
    chosen = set()
    while len(chosen) < min(n_zones, len(set(zs.tolist()))):
        chosen.add(int(rng.choice(zs)))
    start = float(rng.uniform(*start_range))
    return TrafficEvent(frozenset(chosen), start, start + duration, factor)
