"""
src/constraints/vehicle_availability.py

Checks a route's total duration fits within the vehicle's shift/availability
window (e.g. driver can only work 8am-6pm).
"""

from typing import Tuple


class VehicleAvailabilityConstraint:

    def is_feasible(self, route_start_min: float, route_end_min: float,
                     shift_window_min: Tuple[float, float]) -> bool:
        """
        route_start_min: time vehicle departs depot.
        route_end_min: time vehicle returns to depot (after last stop + return leg).
        shift_window_min: (shift_start, shift_end) for this vehicle.
        """
        shift_start, shift_end = shift_window_min
        return route_start_min >= shift_start and route_end_min <= shift_end

    def overtime_amount(self, route_end_min: float,
                         shift_window_min: Tuple[float, float]) -> float:
        """Returns 0.0 if within shift, else minutes over shift end."""
        _, shift_end = shift_window_min
        return max(0.0, route_end_min - shift_end)

    def route_duration_min(self, route_start_min: float, route_end_min: float) -> float:
        return route_end_min - route_start_min
