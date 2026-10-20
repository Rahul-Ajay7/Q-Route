import numpy as np
from qorbit.config import CostParams
from qorbit.models import Customer, Vehicle, ProblemInstance, Solution
from qorbit.traffic import TrafficModel, TrafficEvent
from qorbit.cost import Evaluator


def make():
    # depot(0) - c1 - c2 on a line: 10 km each hop, 40 km/h free flow
    d = np.array([[0, 10, 20], [10, 0, 10], [20, 10, 0]], float)
    inst = ProblemInstance(
        customers={1: Customer(1, 5, 0, 100, 0.0), 2: Customer(2, 5, 0, 100, 0.0)},
        vehicles={1: Vehicle(1, 10, start_time=12.0)},
        dist_km=d, time_h=d / 40.0, zones=np.zeros(3, int))
    return inst


def flat():
    return TrafficModel(peak=1.0)


def test_hand_computed_cost():
    ev = Evaluator(make(), flat())
    res = ev.evaluate(Solution({1: [1, 2]}))
    p = CostParams()
    D, T = 40.0, 1.0
    F = 10 * p.alpha * (1 + p.beta * 10 / 10) + 10 * p.alpha * (1 + p.beta * 5 / 10) + 20 * p.alpha
    expected = p.c_veh + p.c_d * D + p.c_t * T + p.fuel_price * F
    assert res.feasible and abs(res.total_cost - expected) < 1e-6


def test_traffic_raises_cost_and_keeps_fifo():
    inst = make()
    base = Evaluator(inst, flat()).evaluate(Solution({1: [1, 2]})).total_cost
    ev_t = TrafficEvent(frozenset({0}), 11.0, 14.0, 2.5)
    jam = Evaluator(inst, flat().with_event(ev_t)).evaluate(Solution({1: [1, 2]})).total_cost
    assert jam > base
    tm = flat().with_event(ev_t)   # FIFO: departing later never arrives earlier
    ts = np.linspace(10, 16, 600)
    arr = [t + 0.25 * tm.multiplier(0, t) for t in ts]
    assert all(b >= a for a, b in zip(arr, arr[1:]))


def test_hard_constraints():
    ev = Evaluator(make(), flat())
    assert not ev.evaluate(Solution({1: [1]})).feasible            # customer 2 missing
    assert not ev.evaluate(Solution({1: [1, 1, 2]})).feasible      # duplicate
    inst = make(); inst.customers[2] = Customer(2, 50, 0, 100, 0)
    r = Evaluator(inst, flat()).evaluate(Solution({1: [1, 2]}))
    assert not r.feasible and r.objective == float("inf")


def test_late_penalty_soft_vs_hard():
    inst = make(); inst.customers[2] = Customer(2, 5, 0, 11.9, 0)  # arrives 12.5 -> 0.6 h late
    soft = Evaluator(inst, flat()).evaluate(Solution({1: [1, 2]}))
    assert soft.feasible and abs(soft.breakdown["late"] - 0.6 * 600) < 1e-6
    hard = Evaluator(inst, flat(), CostParams(hard_time_windows=True)).evaluate(Solution({1: [1, 2]}))
    assert not hard.feasible