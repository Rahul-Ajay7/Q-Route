import numpy as np
from qorbit.config import CostParams
from qorbit.cost import Evaluator
from qorbit.data.synthetic import make_instance
from qorbit.models import Solution
from qorbit.optimization import greedy_solve, generate_partitions, rank_partitions
from qorbit.traffic import TrafficModel, TrafficEvent


def test_partitions_cover_and_size():
    sol = Solution({1: list(range(1, 12)), 2: [20, 21], 3: [30, 31, 32]})
    parts = generate_partitions(sol, k=5)
    assert all(p.size <= 5 and p.vehicle_id != 2 for p in parts)     # route of 2 skipped
    covered = {c for p in parts if p.vehicle_id == 1 for c in p.customers}
    assert covered == set(range(1, 12))                              # every customer of route 1 covered
    assert any(p.customers == (30, 31, 32) for p in parts)


def test_trace_matches_evaluate_route():
    inst = make_instance(25, seed=4, time_windows=True)
    tm = TrafficModel().with_event(TrafficEvent(frozenset({4}), 9.0, 12.0, 2.5))
    ev = Evaluator(inst, tm)
    sol = greedy_solve(inst, ev)
    for vid, route in sol.routes.items():
        if not route:
            continue
        rr = ev.evaluate_route(inst.vehicles[vid], route)
        tr = ev.trace_route(inst.vehicles[vid], route)
        assert abs(sum(l["fuel_l"] for l in tr) - rr.fuel_l) < 1e-9
        assert abs(sum(l["late_h"] for l in tr) - rr.late_h) < 1e-9
        assert abs(tr[-1]["arrive"] - rr.end_time) < 1e-9 or rr.end_time >= tr[-1]["arrive"]


def test_scores_zero_without_event_and_positive_with():
    inst = make_instance(40, seed=2)
    ev0 = Evaluator(inst, TrafficModel(peak=1.0))
    sol = greedy_solve(inst, ev0)
    assert all(abs(s.total) < 1e-9 for s in rank_partitions(sol, 5, ev0, ev0))
    zone = int(inst.zones[1])
    ev1 = Evaluator(inst, TrafficModel(peak=1.0).with_event(TrafficEvent(frozenset({zone}), 8.0, 16.0, 3.0)))
    ranked = rank_partitions(sol, 5, ev0, ev1)
    assert ranked[0].total > 0 and ranked[0].total >= ranked[-1].total
