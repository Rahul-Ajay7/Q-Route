import numpy as np
from qorbit.models import Customer, Vehicle, ProblemInstance, Solution
from qorbit.traffic import TrafficModel, TrafficEvent
from qorbit.cost import Evaluator

d = np.array([[0,10,20],[10,0,10],[20,10,0]], float)
inst = ProblemInstance(
    customers={1: Customer(1, 5, 0, 100, 0.1), 2: Customer(2, 5, 0, 100, 0.1)},
    vehicles={1: Vehicle(1, capacity=10, start_time=12.0)},
    dist_km=d, time_h=d/40, zones=np.zeros(3, int))

sol = Solution({1: [1, 2]})
t0 = TrafficModel(peak=1.0)
t1 = t0.with_event(TrafficEvent(frozenset({0}), 11, 15, 2.5))   # traffic jam

print("cost under T0:", round(Evaluator(inst, t0).evaluate(sol).total_cost, 1))
print("cost under T1:", round(Evaluator(inst, t1).evaluate(sol).total_cost, 1))