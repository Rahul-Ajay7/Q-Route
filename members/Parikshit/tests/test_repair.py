import numpy as np
from qorbit.cost import Evaluator
from qorbit.data.synthetic import make_instance
from qorbit.optimization import (DirectSA, QuboSA, greedy_solve, run_repair, generate_partitions, splice)
from qorbit.traffic import TrafficModel, TrafficEvent


def scenario(seed=1):
    inst = make_instance(50, seed=seed)
    ev0 = Evaluator(inst, TrafficModel(peak=1.0))
    sol = greedy_solve(inst, ev0)
    zone = int(inst.zones[1])
    ev1 = Evaluator(inst, TrafficModel(peak=1.0).with_event(TrafficEvent(frozenset({zone}), 8.0, 16.0, 3.0)))
    return inst, sol, ev0, ev1


def test_splice_keeps_customers():
    inst, sol, _, _ = scenario()
    part = generate_partitions(sol, 5)[0]
    new = splice(sol, part, list(reversed(part.customers)))
    assert sorted(new.visited()) == sorted(sol.visited())


def test_repair_methods_never_worse_and_stay_valid():
    inst, sol, ev0, ev1 = scenario()
    start = ev1.evaluate(sol).objective
    for solver in (DirectSA(), QuboSA("flip"), QuboSA("swap")):
        cur, rows = run_repair(sol, ev0, ev1, solver, np.random.default_rng(0), k=5, max_solves=8)
        res = ev1.evaluate(cur)
        assert res.feasible and sorted(cur.visited()) == sorted(inst.customers)
        costs = [r["cost"] for r in rows]
        assert costs[0] == start and all(b <= a + 1e-9 for a, b in zip(costs, costs[1:]))


def test_polish_never_worse_and_complete():
    from qorbit.optimization import polish
    inst, sol, ev0, _ = scenario(3)
    new = polish(sol, ev0)
    assert sorted(new.visited()) == sorted(sol.visited())
    assert ev0.evaluate(new).total_cost <= ev0.evaluate(sol).total_cost + 1e-9


def test_polished_plan_has_nothing_left_to_fix_without_traffic_change():
    from qorbit.optimization import polish_windows
    inst, sol, ev0, _ = scenario()
    plan = polish_windows(sol, ev0, k=5)
    start = ev0.evaluate(plan).objective
    assert start <= ev0.evaluate(sol).objective + 1e-9
    _, rows = run_repair(plan, ev0, ev0, DirectSA(), np.random.default_rng(0), k=5, max_solves=10)
    assert abs(rows[-1]["cost"] - start) < 1e-6          # no change in traffic -> nothing to recover
