import pytest
from qorbit.cost import Evaluator
from qorbit.data.synthetic import make_instance
from qorbit.optimization import greedy_solve
from qorbit.sim.metrics import solution_metrics
from qorbit.traffic import TrafficModel


def test_metrics_components_add_up_to_total_cost():
    inst = make_instance(30, seed=2, time_windows=True)
    ev = Evaluator(inst, TrafficModel())
    sol = greedy_solve(inst, ev)
    m = solution_metrics(ev, sol)
    assert m["cost"] == pytest.approx(m["cost_vehicle"] + m["cost_distance"] + m["cost_time"] + m["cost_fuel"] + m["cost_late"])
    assert m["vehicles"] == sum(1 for r in sol.routes.values() if r)
    assert m["distance_km"] > 0 and m["route_hours"] > 0 and m["fuel_l"] > 0
