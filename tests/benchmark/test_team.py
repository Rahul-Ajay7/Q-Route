"""Constraint/accounting oracles and solver invariants, independent of who wins."""
import copy
import itertools
import json
import math

import numpy as np
import pytest

from team_benchmark.problem import Problem, sb
from team_benchmark.solvers import METHODS, ABLATIONS, Settings, solve, neighbor, build_qubo, select_window
from team_benchmark.audit import audit
from team_benchmark.exact import exact_small
from team_benchmark.report import comparisons


def data(n=4, m=2):
    nodes = [dict(id=i*10+7, x=i, y=(i%2)*2, demand=1 if i else 0,
                  ready_time=0, due_time=10000, service_time=1 if i else 0) for i in range(n+1)]
    matrix = np.array([[math.hypot(a['x']-b['x'], a['y']-b['y']) for b in nodes] for a in nodes])
    return dict(id="tiny", depot=nodes[0], customers=nodes[1:],
                vehicles=[dict(id=f"v{i}", capacity=100, start_depot=7, end_depot=7) for i in range(m)],
                base_travel_time_matrix=matrix.tolist(), _matrix=matrix,
                _nodes={c['id']: c for c in nodes}, _indices={c['id']: i for i,c in enumerate(nodes)})


def test_noncontiguous_ids_and_file_loader(tmp_path):
    d = data()
    path = tmp_path/'case.json'
    path.write_text(json.dumps({k:v for k,v in d.items() if not k.startswith('_')}))
    p = Problem.load(path)
    routes = p.initial()
    score = p.evaluate(routes)
    assert score['feasible']
    assert score['cost'] == pytest.approx(audit(p, routes)['cost'])


def test_temporary_closure_waits_and_expires():
    d = data(1, 1)
    d['traffic_events'] = [dict(time=0, end_time=5, **{'from':7,'to':17}, multiplier=None)]
    p = Problem(d)
    tt, wait, mult = p.leg(7,17,0)
    assert wait == 5 and mult == 1
    assert p.leg(17,7,0)[1] == 0
    result = p.evaluate([[17]])
    assert result['feasible']
    assert result['duration_minutes'] == pytest.approx(5+2*tt+1)
    assert result['cost'] == pytest.approx(audit(p, [[17]])['cost'])


def test_newer_event_can_reopen_permanently_closed_edge():
    d = data(1, 1)
    d['traffic_events'] = [dict(time=0, **{'from':7,'to':17}, multiplier=None),
                           dict(time=3, **{'from':7,'to':17}, multiplier=2)]
    p = Problem(d)
    assert p.leg(7,17,0)[1:] == (3, 2)
    assert p.evaluate([[17]])['cost'] == pytest.approx(audit(p, [[17]])['cost'])


def test_permanent_closure_does_not_become_feasible():
    d = data(1, 1)
    d['traffic_events'] = [dict(time=0, **{'from':7,'to':17}, multiplier=None)]
    p = Problem(d)
    assert not p.evaluate([[17]])['feasible']
    with pytest.raises(AssertionError):
        audit(p, [[17]])


@pytest.mark.parametrize('routes', [[[17],[27]], [[17,17,27,37,47],[]], [[999,17,27,37,47],[]], [[17,27,37,47]]])
def test_bad_customer_coverage_or_fleet_is_rejected(routes):
    p = Problem(data())
    assert not p.evaluate(routes)['feasible']
    with pytest.raises(AssertionError):
        audit(p, routes)


def test_soft_hard_windows_release_and_capacity():
    d = data(1,1)
    d['customers'][0]['due_time'] = 2
    d['order_events'] = [dict(type='new_order', customer_id=17, time=10)]
    hard, soft = Problem(d), Problem(d, hard_windows=False)
    assert not hard.evaluate([[17]])['feasible']
    result = soft.evaluate([[17]])
    assert result['feasible'] and result['lateness_minutes'] == 8
    assert result['cost'] == pytest.approx(audit(soft, [[17]])['cost'])
    d['vehicles'][0]['capacity'] = 0
    assert not Problem(d, hard_windows=False).evaluate([[17]])['feasible']


def test_zero_customers_and_breakdown():
    p = Problem(data(0,2))
    assert p.evaluate([[],[]])['cost'] == 0
    d = data(1,1)
    d['vehicle_events'] = [dict(type='breakdown',vehicle_id='v0',time=0)]
    assert not Problem(d).evaluate([[17]])['feasible']


def test_neighborhood_can_open_unused_vehicle_and_preserves_coverage():
    rng = np.random.default_rng(20)
    routes = [[17,27],[]]
    candidates = [neighbor(routes,rng) for _ in range(100)]
    assert any(c[1] for c in candidates)
    assert all(sorted(c[0]+c[1]) == [17,27] for c in candidates)
    assert routes == [[17,27],[]]


def test_qubo_assignment_penalty_exceeds_invalid_global_minimum():
    p = Problem(data(2,1))
    q, offset, block = build_qubo(p,[list(p.ids)],0,0,2)
    valid, invalid = [], []
    for bits in itertools.product((0,1), repeat=4):
        x = np.array(bits)
        e = x@q@x+offset
        (valid if sb.decode(x,2) is not None else invalid).append(e)
    assert min(valid) < min(invalid)


def test_window_scheduler_explores_beyond_already_attempted_windows():
    p = Problem(data(6, 2))
    routes = [list(p.ids), []]
    rng = np.random.default_rng(1)
    first = select_window(p, routes, 3, set(), rng)
    vi, start, end = first
    seen = {(vi, tuple(routes[vi][start:end]))}
    second = select_window(p, routes, 3, set(), rng, attempted=seen)
    assert second is not None and second != first


def test_qubo_surrogate_matches_direct_frozen_edge_calculation():
    p = Problem(data(3,1))
    routes = [list(p.ids)]
    q, offset, block = build_qubo(p,routes,0,0,3)
    load = sum(p.nodes[c]['demand'] for c in block)
    for order in itertools.permutations(range(3)):
        x = np.zeros((3,3))
        for pos,i in enumerate(order):
            x[i,pos]=1
        seq=[p.depot]+[block[i] for i in order]+[p.depot]
        expected=0
        for a,b in zip(seq,seq[1:]):
            tt,wait,m=p.leg(a,b,0)
            d=p.dist[a,b]
            expected += d*p.costs.distance_per_km+(tt+wait)*p.costs.driver_per_minute+d*p.costs.liters_per_km*(1+p.costs.load_premium*load/100)*p.costs.fuel_per_liter
        assert x.ravel()@q@x.ravel()+offset == pytest.approx(expected)


@pytest.mark.parametrize('method', METHODS+ABLATIONS)
def test_methods_preserve_feasibility_best_cost_and_deterministic_action_limit(method):
    p = Problem(data(6,2))
    initial = [list(reversed(p.ids)),[]]
    original = copy.deepcopy(initial)
    cfg = Settings(seconds=30,max_actions=20,plateau=2,samples=3,qubo_steps=5,window=3)
    a,b = [solve(p, initial, method, seed=7,settings=cfg) for _ in range(2)]
    assert initial == original
    assert a['feasible'] and a['cost'] <= p.evaluate(initial)['cost']+1e-9
    assert a['routes'] == b['routes'] and a['cost'] == b['cost']
    assert a['cost'] == pytest.approx(audit(p,a['routes'])['cost'])
    assert all(x['cost'] >= y['cost'] for x,y in zip(a['history'],a['history'][1:]))
    assert a['cost'] >= exact_small(p)['cost']-1e-7
    for selection in a['selections']:
        assert not set(selection['customers']) & set(selection['excluded'])


def test_failed_construction_has_no_finite_quality_score():
    d = data(1,1)
    d['customers'][0]['demand'] = 101
    p = Problem(d)
    result = solve(p,p.initial(),'classical_sa')
    assert result['status'] == 'NO_FEASIBLE_INITIAL_SOLUTION'
    assert result['cost'] is None and not result['feasible']


def test_exact_oracle_proves_tiny_optimum_only():
    p = Problem(data(2,1))
    result = exact_small(p)
    assert result['proven_optimal']
    expected = min(p.evaluate([list(o)])['cost'] for o in itertools.permutations(p.ids))
    assert result['cost'] == expected
    with pytest.raises(ValueError):
        exact_small(Problem(data(8,1)))


def test_statistics_average_seeds_within_case():
    rows=[]
    for seed in range(5):
        rows += [dict(case='one',seed=seed,method='hybrid',cost=90,feasible=True),
                 dict(case='one',seed=seed,method='classical_sa',cost=100,feasible=True)]
    r=comparisons(rows)[0]
    assert r['cases'] == 1 and r['seed_pairs'] == 5
    assert r['mean_percent'] == pytest.approx(10)
    assert r['p_holm'] >= r['p']


def test_settings_reject_bad_budgets():
    for cfg in (Settings(seconds=0),Settings(seconds=math.nan), Settings(window=9),Settings(qubo_steps=0)):
        with pytest.raises(ValueError):
            cfg.validate()
