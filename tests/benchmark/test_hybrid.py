"""Caching must preserve exact dynamic costs; repair must preserve feasibility."""
import copy
import math
import time

import numpy as np
import pytest

from team_benchmark.problem import Problem
from team_benchmark.cached import CachedProblem
from team_benchmark.hybrid import destroy_repair, select_repair_window
from team_benchmark.solvers import Settings, solve, solve_reference, neighbor
from .test_team import data
from team_benchmark.audit import audit


def test_cache_matches_full_evaluator_after_many_route_changes():
    d = data(6,3)
    d['traffic_events'] = [dict(time=0,end_time=4,**{'from':7,'to':17},multiplier=None),
                           dict(time=5,end_time=50,**{'from':17,'to':27},multiplier=3)]
    p = Problem(d,hard_windows=False)
    cached = CachedProblem(p,limit=25)
    routes = [list(p.ids),[],[]]
    rng = np.random.default_rng(3)
    for _ in range(100):
        routes = neighbor(routes,rng)
        assert cached.evaluate(routes) == p.evaluate(routes)
        assert len(cached.cache)<=25


def test_unchanged_routes_are_not_resimulated_and_vehicle_is_in_cache_key():
    p = Problem(data(4,2))
    cached = CachedProblem(p)
    routes = [[17,27],[37,47]]
    cached.evaluate(routes)
    assert cached.route_simulations==2
    cached.evaluate([[27,17],[37,47]])
    assert cached.route_simulations==3
    assert cached.route_cache_hits==1
    cached.evaluate([[37,47],[27,17]])
    assert cached.route_simulations==5


@pytest.mark.parametrize('routes',[[[17],[]],[[17,17,27,37,47],[]],[[999],[]],[[17,27,37,47]]])
def test_cache_preserves_rejection_of_invalid_coverage(routes):
    p = Problem(data(4,2))
    assert CachedProblem(p).evaluate(routes) == p.evaluate(routes)


def test_repair_can_eliminate_a_route_without_losing_customers():
    p = CachedProblem(Problem(data(4,2)))
    initial = [[17,27,37],[47]]
    original = copy.deepcopy(initial)
    candidate = destroy_repair(p,initial,[47],time.perf_counter()+30)
    assert candidate is not None
    assert sum(bool(r) for r in candidate)==1
    assert p.evaluate(candidate)['cost']<p.evaluate(initial)['cost']
    assert audit(p,candidate)['cost']==pytest.approx(p.evaluate(candidate)['cost'])
    assert initial==original


def test_repair_respects_capacity_and_returns_no_partial_solution_on_timeout():
    d = data(2,2)
    for v in d['vehicles']:
        v['capacity']=1
    p = CachedProblem(Problem(d))
    initial = [[17],[27]]
    candidate = destroy_repair(p,initial,[17],time.perf_counter()+30)
    assert candidate is not None and p.evaluate(candidate)['feasible']
    assert sum(bool(r) for r in candidate)==2
    assert destroy_repair(p,initial,[17],time.perf_counter()-1) is None
    assert destroy_repair(p,initial,[17],time.perf_counter()+30,max_evaluations=0) is None
    with pytest.raises(ValueError):
        destroy_repair(p,initial,[17,17],time.perf_counter()+30)


def test_cache_changes_only_work_not_reference_search_sequence():
    p = Problem(data(6,2))
    initial = [list(reversed(p.ids)),[]]
    cfg = Settings(seconds=30,max_actions=100,plateau=3,samples=3,qubo_steps=5)
    for method in ('classical_sa','tunnelling_sa','qubo_sb','hybrid'):
        a=solve_reference(p,initial,method,5,cfg)
        b=solve_reference(CachedProblem(p),initial,method,5,cfg)
        assert a['routes']==b['routes'] and a['cost']==b['cost']


@pytest.mark.parametrize('backend',['sa','sb'])
def test_adaptive_solver_runs_both_samplers_and_exclusion_is_strict(backend):
    p = Problem(data(6,2))
    initial = [list(p.ids),[]]
    cfg=Settings(seconds=30,max_actions=100,plateau=1,samples=3,qubo_steps=5,window=3,
                 hybrid_backend=backend)
    r=solve(p,initial,'hybrid_no_repair',seed=4,settings=cfg)
    assert r['stats']['qubo_calls']>0
    assert r['stats']['route_cache_hits']>0
    assert r['feasible']
    assert r['cost']==pytest.approx(audit(p,r['routes'])['cost'])
    assert all(not set(s['customers'])&set(s['excluded']) for s in r['selections'])


def test_window_selection_avoids_tabu_and_tried_blocks():
    p=Problem(data(6,1))
    routes=[list(p.ids)]
    excluded={17,27}
    pick=select_repair_window(p,routes,3,excluded,set(),np.random.default_rng(0))
    vi,start,end=pick
    assert not set(routes[vi][start:end])&excluded
    attempted={(vi,tuple(routes[vi][start:end]))}
    assert select_repair_window(p,routes,3,excluded,attempted,np.random.default_rng(0))!=pick


def test_adaptive_failure_backoff_reduces_qubo_calls():
    p=Problem(data(2,1))
    initial=[list(p.ids)]
    cfg=Settings(seconds=30,max_actions=150,plateau=1,window=2,samples=2,qubo_steps=3,cycles=20)
    adapted=solve(p,initial,'hybrid_no_repair',0,cfg)
    fixed=solve(p,initial,'hybrid_no_adaptation',0,cfg)
    assert adapted['stats']['qubo_calls']<fixed['stats']['qubo_calls']
    assert adapted['cost']<=p.evaluate(initial)['cost']
