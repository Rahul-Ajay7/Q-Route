"""Structural regressions in the original root SA implementation."""
import math

from src.optimization.neighborhood import NeighborhoodOperators
from src.optimization.simulated_annealing import SolutionEvaluator, routes_from_greedy
from src.optimization.greedy import GreedySolver


def test_relocate_can_use_an_empty_vehicle():
    ops = NeighborhoodOperators(seed=1)
    candidates = [ops.random_neighbor([[1], []]) for _ in range(20)]
    assert any(r == [[], [1]] for r in candidates)
    assert all(sorted(r[0]+r[1]) == [1] for r in candidates)


def test_greedy_conversion_preserves_vehicle_slot_when_first_vehicle_unused():
    instance = dict(customers=[dict(id=1,demand=5,ready_time=0,due_time=100,service_time=0)],
                    vehicles=[dict(id='small',capacity=1,shift_window=[0,100]),
                              dict(id='large',capacity=10,shift_window=[0,100])])
    result=GreedySolver().solve(instance, [[0,60],[60,0]])
    assert result['routes'][0]['vehicle_id'] == 'large'
    assert routes_from_greedy(result,2) == [[],[1]]


def test_duplicate_unknown_and_wrong_fleet_are_rejected():
    instance = dict(customers=[dict(id=1,demand=1,ready_time=0,due_time=100,service_time=0)],
                    vehicles=[dict(id=1,capacity=10,shift_window=[0,100])])
    ev=SolutionEvaluator(instance,[[0,1],[1,0]],[[0,60],[60,0]])
    assert math.isfinite(ev.solution_cost([[1]]))
    assert ev.solution_cost([[1,1]]) == math.inf
    assert ev.solution_cost([[2]]) == math.inf
    assert ev.solution_cost([[1],[]]) == math.inf
