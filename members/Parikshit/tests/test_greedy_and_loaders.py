import os
import numpy as np
from qorbit.cost import Evaluator
from qorbit.data.synthetic import make_instance
from qorbit.data.solomon import load_solomon
from qorbit.optimization import greedy_solve
from qorbit.traffic import TrafficModel, corridor_event

HERE = os.path.dirname(__file__)


def test_greedy_feasible_complete_deterministic():
    for tw in (False, True):
        inst = make_instance(40, seed=3, time_windows=tw)
        ev = Evaluator(inst, TrafficModel())
        s1, s2 = greedy_solve(inst, ev), greedy_solve(inst, ev)
        assert s1.routes == s2.routes
        res = ev.evaluate(s1)
        assert res.feasible, res.violations
        assert sorted(s1.visited()) == sorted(inst.customers)


def test_event_raises_cost():
    inst = make_instance(30, seed=1)
    sol = greedy_solve(inst, Evaluator(inst, TrafficModel()))
    ev1 = corridor_event(inst, np.random.default_rng(1))
    c0 = Evaluator(inst, TrafficModel()).evaluate(sol).total_cost
    c1 = Evaluator(inst, TrafficModel().with_event(ev1)).evaluate(sol).total_cost
    assert c1 >= c0


def test_solomon_parse_and_flat_distance():
    inst = load_solomon(os.path.join(HERE, "data", "mini_solomon.txt"))
    assert len(inst.customers) == 2 and inst.vehicles[1].capacity == 20
    assert abs(inst.dist_km[0, 1] - 5.0) < 1e-9 and abs(inst.time_h[0, 1] - 5 / 60) < 1e-9
    from qorbit.models import Solution
    res = Evaluator(inst, TrafficModel(peak=1.0)).evaluate(Solution({1: [1, 2]}))
    assert abs(res.routes[1].distance_km - (5 + 5 + 10)) < 1e-9     # 0->1->2->0 = 5+5+10