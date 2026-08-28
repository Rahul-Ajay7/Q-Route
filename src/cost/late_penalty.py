"""
src/cost/late_penalty.py

Penalty for arriving after a customer's due time (soft time window
violation). Assumes Customer model has time_window = (ready_time, due_time)
and arrival_time is computed externally (cumulative travel+service time).

NOTE: adjust attribute names below (customer.due_time / customer.ready_time)
to match your actual Customer dataclass field names in src/models/customer.py.
"""

from typing import List


class LatePenalty:

    def __init__(self, penalty_per_minute: float = 10.0,
                 hard_violation_penalty: float = 1000.0,
                 hard_violation_threshold_min: float = 60.0):
        """
        penalty_per_minute: linear cost per minute late.
        hard_violation_penalty: extra flat penalty if lateness exceeds
        threshold (treat as near-infeasible without fully rejecting solution
        during SA/QUBO search).
        """
        self.penalty_per_minute = penalty_per_minute
        self.hard_violation_penalty = hard_violation_penalty
        self.hard_violation_threshold_min = hard_violation_threshold_min

    def stop_penalty(self, arrival_time_min: float, due_time_min: float) -> float:
        lateness = arrival_time_min - due_time_min
        if lateness <= 0:
            return 0.0
        cost = lateness * self.penalty_per_minute
        if lateness > self.hard_violation_threshold_min:
            cost += self.hard_violation_penalty
        return cost

    def route_penalty(self, arrival_times_min: List[float],
                       due_times_min: List[float]) -> float:
        """
        arrival_times_min / due_times_min: parallel lists, one entry per
        customer stop in route order (exclude depot).
        """
        if len(arrival_times_min) != len(due_times_min):
            raise ValueError("arrival_times_min and due_times_min must match length")
        return sum(
            self.stop_penalty(a, d)
            for a, d in zip(arrival_times_min, due_times_min)
        )
