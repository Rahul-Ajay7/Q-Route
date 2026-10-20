"""Smooth congestion multiplier m(zone, t) >= 1. tau_ij(t) = tau0_ij * m."""
from dataclasses import dataclass, field
import math


def _smoothstep(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


@dataclass(frozen=True)
class TrafficEvent:
    zones: frozenset
    start: float
    end: float
    factor: float           # e.g. 2.5 = 2.5x slower at full effect
    # Hours to ramp in/out. FIFO (leaving later never arrives earlier) holds when
    # ramp >= 1.5 * (factor - 1) * 1.5 * longest_leg_hours  (smoothstep max slope = 1.5).
    # Default 1.0 h is safe for 2.5x events and legs up to ~0.45 h; raise it for longer legs.
    ramp: float = 1.0

    def multiplier(self, zone: int, t: float) -> float:
        if zone not in self.zones:
            return 1.0
        w = min(_smoothstep((t - self.start) / self.ramp),
                _smoothstep((self.end - t) / self.ramp))
        return 1.0 + (self.factor - 1.0) * w


@dataclass
class TrafficModel:
    peak: float = 1.8                       # max daily-profile multiplier
    morning: tuple = (9.0, 1.0)             # (centre h, sigma h)
    evening: tuple = (18.0, 1.2)
    sensitivity: dict = field(default_factory=dict)   # zone -> scale of daily profile
    events: list = field(default_factory=list)

    def _profile(self, t: float) -> float:
        g = lambda c, s: math.exp(-0.5 * ((t - c) / s) ** 2)
        return 1.0 + (self.peak - 1.0) * max(g(*self.morning), g(*self.evening))

    def multiplier(self, zone: int, t: float) -> float:
        base = 1.0 + self.sensitivity.get(zone, 1.0) * (self._profile(t) - 1.0)
        for e in self.events:
            base *= e.multiplier(zone, t)
        return base

    def leg_multiplier(self, zone_i: int, zone_j: int, t: float) -> float:
        return 0.5 * (self.multiplier(zone_i, t) + self.multiplier(zone_j, t))

    def with_event(self, event: TrafficEvent) -> "TrafficModel":
        """Return a new model with the event added (T0 -> T1)."""
        return TrafficModel(self.peak, self.morning, self.evening,
                            dict(self.sensitivity), [*self.events, event])
