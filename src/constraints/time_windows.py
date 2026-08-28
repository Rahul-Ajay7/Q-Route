"""
src/constraints/time_windows.py

Checks whether arrival times at customers fall within their [ready_time,
due_time] windows. Distinguishes hard violation (arrival > due_time, service
not allowed) from waiting (arrival < ready_time, vehicle waits, still feasible).
"""

from typing import List, Tuple


class TimeWindowConstraint:

    def is_stop_feasible(self, arrival_time_min: float,
                          ready_time_min: float, due_time_min: float) -> bool:
        """
        Arriving early is fine (vehicle waits until ready_time).
        Arriving after due_time is a hard violation.
        """
        return arrival_time_min <= due_time_min

    def effective_start_time(self, arrival_time_min: float,
                              ready_time_min: float) -> float:
        """Service can't start before ready_time -- vehicle waits if early."""
        return max(arrival_time_min, ready_time_min)

    def is_route_feasible(self, arrival_times_min: List[float],
                           windows_min: List[Tuple[float, float]]) -> bool:
        """
        arrival_times_min: arrival time at each customer stop, in route order.
        windows_min: parallel list of (ready_time, due_time) tuples.
        """
        if len(arrival_times_min) != len(windows_min):
            raise ValueError("arrival_times_min and windows_min must match length")
        return all(
            self.is_stop_feasible(a, ready, due)
            for a, (ready, due) in zip(arrival_times_min, windows_min)
        )

    def violations(self, arrival_times_min: List[float],
                    windows_min: List[Tuple[float, float]]) -> List[float]:
        """Returns lateness amount per stop (0.0 if on time or early)."""
        return [
            max(0.0, a - due)
            for a, (ready, due) in zip(arrival_times_min, windows_min)
        ]
