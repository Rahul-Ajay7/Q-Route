"""Central parameters. Units: INR, km, hours (clock time = hours since midnight)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class CostParams:
    c_veh: float = 500.0            # INR per used vehicle
    c_d: float = 3.0                # INR per km (wear, tyres)
    c_t: float = 150.0              # INR per hour (driver; waiting included)
    fuel_price: float = 95.0        # INR per litre
    alpha: float = 0.09             # L/km, empty vehicle
    beta: float = 0.5               # extra fuel fraction at full load
    congestion_fuel: float = 0.25   # fuel factor = 1 + k*(m-1)
    lambda_late_per_min: float = 10.0   # INR per minute late (4x driver rate)
    lambda_cap: float = 10_000.0    # INR per unit capacity excess
    hard_time_windows: bool = False  # True -> any lateness makes solution infeasible

    @property
    def lambda_late_per_hour(self) -> float:
        return self.lambda_late_per_min * 60.0


@dataclass(frozen=True)
class QuboParams:
    k: int = 5                      # partition size -> k*k binary variables
    lambda_assign: float = 1.5      # each customer exactly once (normalised costs)
    lambda_position: float = 1.5    # each position exactly one customer
    lambda_capacity: float = 0.0    # 0 for single-route partitions
    lambda_time: float = 1.0        # multiplies late penalty (diagonal term)
