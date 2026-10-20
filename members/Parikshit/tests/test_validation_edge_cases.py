"""Basic, infeasible and edge cases: the solver must REPORT problems, never silently drop customers."""
import itertools
import math
import os
import numpy as np
import pytest
from qorbit.cost import Evaluator
from qorbit.data.solomon import load_solomon
from qorbit.data.synthetic import make_instance
from qorbit.models import Customer, ProblemInstance, Solution, Vehicle
from qorbit.optimization import (DirectSA, QuboSA, SAParams, anneal_qubo, build_initial, build_qubo, decode,
                                 generate_partitions, greedy_solve, run_repair)
from qorbit.traffic import TrafficEvent, TrafficModel
from qorbit.validation import check_instance, errors_of

HERE = os.path.dirname(__file__)


def line(demands=(5, 5), due=(1e9, 1e9), cap=10.0, n_veh=1):
    d = np.array([[0, 10, 20], [10, 0, 10], [20, 10, 0]], float)
    cust = {i + 1: Customer(i + 1, demands[i], 0.0, due[i], 0.1) for i in range(2)}
    veh = {v: Vehicle(v, cap, 8.0) for v in range(1, n_veh + 1)}
    return ProblemInstance(cust, veh, d, d / 40.0, np.zeros(3, int))


def ev(inst):
    return Evaluator(inst, TrafficModel(peak=1.0))


def codes(issues, level=None):
    return {i.code for i in issues if level is None or i.level == level}


# ---------------- basic / edge ----------------
def test_empty_instance_is_feasible_zero_cost():
    inst = ProblemInstance({}, {1: Vehicle(1, 10.0)}, np.zeros((1, 1)), np.zeros((1, 1)), np.zeros(1, int))
    rep = build_initial(inst, ev(inst))
    assert rep.status == "feasible" and rep.cost == 0 and rep.unassigned == []


def test_single_customer_and_exact_capacity():
    inst = line(demands=(10, 0), cap=10.0)
    rep = build_initial(inst, ev(inst))
    assert rep.status == "feasible" and sorted(rep.solution.visited()) == [1, 2]


def test_every_customer_is_routed_exactly_once():
    inst = make_instance(60, seed=5, time_windows=True)
    rep = build_initial(inst, ev(inst), hard_tw=False)
    assert rep.status == "feasible"
    assert sorted(rep.solution.visited()) == sorted(inst.customers)


# ---------------- infeasible cases are reported, not hidden ----------------
def test_demand_larger_than_any_vehicle_is_reported():
    inst = line(demands=(5, 50), cap=10.0)
    assert "demand_exceeds_capacity" in codes(check_instance(inst), "infeasible")
    rep = build_initial(inst, ev(inst))
    assert rep.status == "infeasible" and rep.unassigned == [2]
    assert "exceeds" in rep.reasons[2]
    assert rep.solution.visited() == [1]                       # the feasible part is kept, 2 is reported
    res = ev(inst).evaluate(rep.solution)                       # and the evaluator also refuses the partial plan
    assert not res.feasible and res.objective == math.inf
    assert any("customer 2 not visited" in v for v in res.violations)


def test_total_demand_exceeding_fleet_capacity_is_reported():
    inst = line(demands=(8, 8), cap=10.0)
    assert "fleet_capacity" in codes(check_instance(inst), "infeasible")
    rep = build_initial(inst, ev(inst))
    assert rep.status == "infeasible" and len(rep.unassigned) == 1


def test_no_vehicles_is_reported():
    inst = line(n_veh=1); inst.vehicles = {}
    assert "no_vehicles" in codes(check_instance(inst), "infeasible")
    rep = build_initial(inst, ev(inst))
    assert rep.status == "infeasible" and sorted(rep.unassigned) == [1, 2]


def test_unreachable_window_hard_vs_soft():
    inst = line(due=(8.1, 1e9))                                  # arrival is 8.25 at the earliest
    assert "window_unreachable" in codes(check_instance(inst, hard_tw=True), "infeasible")
    assert "window_unreachable" in codes(check_instance(inst, hard_tw=False), "warning")
    hard = build_initial(inst, ev(inst), hard_tw=True)
    assert hard.status == "infeasible" and hard.unassigned == [1]
    soft = build_initial(inst, ev(inst), hard_tw=False)
    assert soft.status == "feasible" and soft.solution.visited().count(1) == 1   # served late, with a penalty
    assert ev(inst).evaluate(soft.solution).breakdown["late"] > 0


def test_greedy_raises_when_not_asked_to_collect_unassigned():
    with pytest.raises(RuntimeError):
        greedy_solve(line(demands=(5, 50)), ev(line(demands=(5, 50))))


def test_evaluator_rejects_bad_solutions():
    inst = line(); e = ev(inst)
    assert not e.evaluate(Solution({1: [1]})).feasible                    # customer 2 missing
    assert not e.evaluate(Solution({1: [1, 1, 2]})).feasible              # duplicate
    assert not e.evaluate(Solution({1: [1, 2, 99]})).feasible             # unknown customer
    assert not e.evaluate(Solution({1: [1, 2], 7: []})).feasible          # unknown vehicle


# ---------------- malformed data ----------------
def bad(**kw):
    inst = line()
    for k, v in kw.items():
        setattr(inst, k, v)
    return inst


@pytest.mark.parametrize("inst,code", [
    (bad(dist_km=np.zeros((2, 2))), "dist_km_shape"),
    (bad(time_h=np.array([[0, np.nan, 1], [1, 0, 1], [1, 1, 0]])), "time_h_nan"),
    (bad(dist_km=-np.ones((3, 3))), "dist_km_negative"),
    (bad(zones=np.zeros(2, int)), "zones_length"),
    (bad(customers={1: Customer(1, 5, 9.0, 8.0, 0.1), 2: Customer(2, 5, 0, 9, 0.1)}), "window_inverted"),
    (bad(customers={1: Customer(1, -5, 0, 9, 0.1), 2: Customer(2, 5, 0, 9, 0.1)}), "demand_negative"),
    (bad(customers={1: Customer(1, 5, 0, 9, 0.1), 3: Customer(3, 5, 0, 9, 0.1)}), "customer_ids"),
    (bad(vehicles={1: Vehicle(1, 0.0, 8.0)}), "capacity_nonpositive"),
])
def test_malformed_instances_are_flagged_and_not_solved(inst, code):
    assert code in codes(check_instance(inst), "error")
    rep = build_initial(inst, ev(inst))
    assert rep.status == "invalid_instance" and len(rep.unassigned) == len(inst.customers)


# ---------------- partition / QUBO edge cases ----------------
def test_short_routes_make_no_or_one_partition():
    sol = Solution({1: [], 2: [1], 3: [2, 3], 4: [4, 5, 6], 5: list(range(7, 13))})
    parts = generate_partitions(sol, k=5)
    assert {p.vehicle_id for p in parts} == {4, 5}
    assert [p.size for p in parts if p.vehicle_id == 4] == [3]


def test_smallest_qubo_size_3_matches_brute_force():
    inst = make_instance(12, seed=1)
    e = Evaluator(inst, TrafficModel())
    sol = Solution({1: list(range(1, 13))})
    sol = Solution({1: [1, 2, 3], 2: [4, 5, 6, 7, 8, 9, 10, 11, 12]})
    part = [p for p in generate_partitions(sol, 5) if p.vehicle_id == 1][0]
    q = build_qubo(sol, part, e)
    assert q.n == 9
    best = min(q.energy(q.x_from_order(o)) for o in itertools.permutations(q.customers))
    x, en, _ = anneal_qubo(q, np.random.default_rng(0), SAParams(100, 4, 0.95), "swap")
    assert en == pytest.approx(best)
    order, repaired = decode(x, q)
    assert sorted(order) == sorted(q.customers) and not repaired


# ---------------- repair never loses a customer or raises cost ----------------
@pytest.mark.parametrize("seed", range(6))
def test_repair_preserves_customers_and_never_worsens(seed):
    inst = make_instance(30, seed=seed, time_windows=True)
    ev0 = Evaluator(inst, TrafficModel(peak=1.0))
    sol = greedy_solve(inst, ev0)
    ev1 = Evaluator(inst, TrafficModel(peak=1.0).with_event(TrafficEvent(frozenset({int(inst.zones[1])}), 8.0, 16.0, 3.0)))
    start = ev1.evaluate(sol).objective
    for solver in (DirectSA(SAParams(30, 2, 0.9)), QuboSA("swap", SAParams(30, 2, 0.9))):
        cur, rows = run_repair(sol, ev0, ev1, solver, np.random.default_rng(seed), k=5, max_solves=6)
        assert sorted(cur.visited()) == sorted(inst.customers)
        costs = [r["cost"] for r in rows]
        assert costs[0] == start and all(b <= a + 1e-9 for a, b in zip(costs, costs[1:]))


# ---------------- real benchmark file ----------------
R101 = os.path.join(HERE, "..", "data", "solomon", "R101.txt")


@pytest.mark.skipif(not os.path.exists(R101) or os.path.getsize(R101) == 0, reason="R101.txt not present")
def test_r101_is_loaded_and_validated_correctly():
    inst = load_solomon(R101)
    assert len(inst.customers) == 100 and len(inst.vehicles) == 25 and inst.vehicles[1].capacity == 200
    assert tuple(inst.coords[0]) == (35, 35) and tuple(inst.coords[1]) == (41, 49)
    assert sum(c.demand for c in inst.customers.values()) == 1458
    assert inst.dist_km[0, 1] == pytest.approx(math.hypot(6, 14))
    assert inst.time_h[0, 1] == pytest.approx(math.hypot(6, 14) / 60)
    assert inst.customers[1].due - inst.customers[1].ready == pytest.approx(10 / 60)
    assert not errors_of(check_instance(inst, hard_tw=True))
    assert not codes(check_instance(inst, hard_tw=True), "infeasible")
    rep = build_initial(inst, Evaluator(inst, TrafficModel(peak=1.0)), hard_tw=True)
    assert rep.status == "feasible" and sorted(rep.solution.visited()) == sorted(inst.customers)
