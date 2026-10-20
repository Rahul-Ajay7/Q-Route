"""Hand-calculated checks of travel time, traffic events, capacity, time windows and cost accounting,
plus a naive independent re-implementation compared against the real evaluator on random cases."""
import math
import numpy as np
import pytest
from qorbit.config import CostParams
from qorbit.cost import Evaluator
from qorbit.data.synthetic import make_instance
from qorbit.models import Customer, ProblemInstance, Solution, Vehicle
from qorbit.traffic import TrafficEvent, TrafficModel

P = CostParams()


def line(demands=(5, 5), ready=(0, 0), due=(1e9, 1e9), service=(0.1, 0.1), cap=10.0, start=8.0,
         depot_due=math.inf, zones=(0, 0, 0), n_veh=1):
    """depot(0) - c1 - c2 on a line, 10 km hops, 40 km/h => 0.25 h per hop; depot-c2 = 20 km."""
    d = np.array([[0, 10, 20], [10, 0, 10], [20, 10, 0]], float)
    cust = {i + 1: Customer(i + 1, demands[i], ready[i], due[i], service[i]) for i in range(2)}
    veh = {v: Vehicle(v, cap, start) for v in range(1, n_veh + 1)}
    return ProblemInstance(cust, veh, d, d / 40.0, np.array(zones), depot_due=depot_due)


def ev_for(inst, tm=None, params=P):
    return Evaluator(inst, tm or TrafficModel(peak=1.0), params)


def route(inst, r, ev=None):
    ev = ev or ev_for(inst)
    return ev.evaluate_route(inst.vehicles[1], r)


# ---------------- travel time / service / waiting ----------------
def test_single_customer_timing():
    r = route(line(), [1])
    assert r.distance_km == pytest.approx(20)
    assert r.arrivals == [pytest.approx(8.25)]
    assert r.end_time == pytest.approx(8.6)           # 8.25 + 0.1 service + 0.25 back
    assert r.duration_h == pytest.approx(0.6)


def test_early_arrival_waits_for_ready_time_and_waiting_is_paid():
    inst = line(ready=(9.0, 0))
    r = route(inst, [1])
    assert r.arrivals == [pytest.approx(8.25)]
    assert r.end_time == pytest.approx(9.35)           # waits to 9.0, +0.1 service, +0.25 back
    assert r.duration_h == pytest.approx(1.35)
    assert r.cost["time"] == pytest.approx(P.c_t * 1.35)
    assert r.late_h == 0


# ---------------- time windows ----------------
def test_lateness_penalty():
    r = route(line(due=(8.2, 1e9)), [1])               # arrives 8.25, 0.05 h = 3 min late
    assert r.late_h == pytest.approx(0.05)
    assert r.cost["late"] == pytest.approx(3 * P.lambda_late_per_min)


def test_arriving_exactly_on_due_is_not_late():
    r = route(line(due=(8.25, 1e9)), [1])
    assert r.late_h == pytest.approx(0, abs=1e-12)


def test_depot_closing_time_penalised():
    r = route(line(depot_due=8.5), [1])                # back at 8.6 -> 6 min late
    assert r.late_h == pytest.approx(0.1)
    assert r.cost["late"] == pytest.approx(6 * P.lambda_late_per_min)


def test_hard_windows_flag_marks_infeasible():
    inst = line(due=(8.2, 1e9))
    soft = ev_for(inst).evaluate(Solution({1: [1, 2]}))
    hard = ev_for(inst, params=CostParams(hard_time_windows=True)).evaluate(Solution({1: [1, 2]}))
    assert soft.feasible and not hard.feasible


# ---------------- capacity ----------------
def test_capacity_boundary():
    ok = ev_for(line(demands=(5, 5), cap=10)).evaluate(Solution({1: [1, 2]}))
    over = ev_for(line(demands=(5, 5.001), cap=10)).evaluate(Solution({1: [1, 2]}))
    assert ok.feasible and ok.routes[1].cap_excess == 0
    assert not over.feasible and over.routes[1].cap_excess == pytest.approx(0.001)
    assert over.objective == math.inf


# ---------------- traffic events: closed-form multiplier ----------------
def ss(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


@pytest.mark.parametrize("t,expected", [(9, 1.0), (10, 1.0), (10.5, 1.5), (11, 2.0), (12, 2.0), (13, 2.0),
                                         (13.5, 1.5), (14, 1.0), (15, 1.0)])
def test_event_multiplier_profile(t, expected):
    e = TrafficEvent(frozenset({0}), 10.0, 14.0, 2.0, ramp=1.0)
    assert e.multiplier(0, t) == pytest.approx(expected)
    assert e.multiplier(1, t) == 1.0                    # other zones untouched


def test_leg_multiplier_is_average_of_endpoint_zones():
    tm = TrafficModel(peak=1.0).with_event(TrafficEvent(frozenset({0}), 10, 14, 2.0, 1.0))
    assert tm.leg_multiplier(0, 1, 12.0) == pytest.approx(1.5)
    assert tm.leg_multiplier(0, 0, 12.0) == pytest.approx(2.0)
    assert tm.leg_multiplier(1, 1, 12.0) == pytest.approx(1.0)


def test_daily_profile_and_sensitivity():
    tm = TrafficModel(peak=1.8, sensitivity={1: 0.5})
    assert tm.multiplier(0, 9.0) == pytest.approx(1.8)
    assert tm.multiplier(1, 9.0) == pytest.approx(1.4)
    assert tm.multiplier(0, 3.0) == pytest.approx(1.0, abs=1e-6)


def test_travel_time_depends_on_departure_time_and_fuel_scales():
    inst = line(start=12.0)
    tm = TrafficModel(peak=1.0).with_event(TrafficEvent(frozenset({0}), 10, 14, 2.0, 1.0))
    r = route(inst, [1], ev_for(inst, tm))
    # depot->c1 departs 12.0 (m=2): 0.5 h; service 0.1; c1->depot departs 12.6 (m=2): 0.5 h
    assert r.arrivals == [pytest.approx(12.5)]
    assert r.end_time == pytest.approx(13.1)
    fuel = 10 * P.alpha * (1 + P.beta * 0.5) * 1.25 + 10 * P.alpha * 1.25
    assert r.fuel_l == pytest.approx(fuel)
    # same route before the event starts: free flow
    r0 = route(line(start=8.0), [1], ev_for(inst, tm))
    assert r0.end_time == pytest.approx(8.6)


# ---------------- cost accounting ----------------
def test_cost_is_sum_of_components_and_empty_vehicles_are_free():
    inst = line(n_veh=3)
    res = ev_for(inst).evaluate(Solution({1: [1], 2: [2], 3: []}))
    assert res.feasible
    assert res.breakdown["vehicle"] == pytest.approx(2 * P.c_veh)       # unused vehicle costs nothing
    assert res.total_cost == pytest.approx(sum(res.breakdown.values()))
    assert res.routes[1].total + res.routes[2].total == pytest.approx(res.total_cost)


# ---------------- independent naive evaluator vs the real one ----------------
def ref_multiplier(events, zone, t):
    m = 1.0
    for zs, s, e, f, ramp in events:
        if zone in zs:
            m *= 1 + (f - 1) * min(ss((t - s) / ramp), ss((e - t) / ramp))
    return m


def ref_route(inst, events, veh, r, p=P):
    t, pos = veh.start_time, 0
    load = sum(inst.customers[c].demand for c in r)
    dist = fuel = late = 0.0
    for c in r + [0]:
        m = 0.5 * (ref_multiplier(events, inst.zones[pos], t) + ref_multiplier(events, inst.zones[c], t))
        d = inst.dist_km[pos, c]
        dist += d
        fuel += d * p.alpha * (1 + p.beta * load / veh.capacity) * (1 + p.congestion_fuel * (m - 1))
        t += inst.time_h[pos, c] * m
        if c == 0:
            late += max(0.0, t - inst.depot_due)
        else:
            cu = inst.customers[c]
            late += max(0.0, t - cu.due)
            t = max(t, cu.ready) + cu.service
            load -= cu.demand
        pos = c
    return dist, fuel, late, t


def test_real_evaluator_matches_naive_reimplementation_on_random_cases():
    rng = np.random.default_rng(7)
    for case in range(60):
        inst = make_instance(int(rng.integers(8, 16)), seed=case, time_windows=True)
        events = []
        for _ in range(int(rng.integers(0, 3))):
            s = float(rng.uniform(8, 11))
            events.append((frozenset(int(z) for z in rng.choice(9, 2, replace=False)), s, s + float(rng.uniform(2, 4)),
                           float(rng.uniform(1.2, 3.0)), 1.0))
        tm = TrafficModel(peak=1.0)
        for zs, s, e, f, ramp in events:
            tm = tm.with_event(TrafficEvent(zs, s, e, f, ramp))
        ev = Evaluator(inst, tm)
        ids = list(inst.customers); rng.shuffle(ids)
        cuts = sorted(rng.choice(range(1, len(ids)), 2, replace=False))
        for chunk in (ids[:cuts[0]], ids[cuts[0]:cuts[1]], ids[cuts[1]:]):
            veh = inst.vehicles[1]
            rr = ev.evaluate_route(veh, list(chunk))
            dist, fuel, late, end = ref_route(inst, events, veh, list(chunk))
            assert rr.distance_km == pytest.approx(dist, rel=1e-9)
            assert rr.fuel_l == pytest.approx(fuel, rel=1e-9)
            assert rr.late_h == pytest.approx(late, abs=1e-9)
            assert rr.end_time == pytest.approx(end, rel=1e-9)


def test_fifo_holds_for_single_events_with_default_ramp():
    """Leaving later never arrives earlier (events <= 2.5x, free-flow legs <= 0.4 h, default ramp 1 h)."""
    rng = np.random.default_rng(3)
    for _ in range(40):
        s, f = float(rng.uniform(8, 11)), float(rng.uniform(1.2, 2.5))
        tm = TrafficModel(peak=1.0).with_event(TrafficEvent(frozenset({0}), s, s + 3.5, f))
        tau = float(rng.uniform(0.05, 0.4))
        ts = np.linspace(s - 1, s + 5, 800)
        arr = [t + tau * tm.leg_multiplier(0, 0, t) for t in ts]
        assert all(b >= a - 1e-12 for a, b in zip(arr, arr[1:]))
