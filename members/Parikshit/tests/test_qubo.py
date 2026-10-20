import itertools
import numpy as np
from qorbit.cost import Evaluator
from qorbit.data.synthetic import make_instance
from qorbit.optimization import (greedy_solve, rank_partitions, build_qubo, decode, anneal_qubo, SAParams)
from qorbit.traffic import TrafficModel, TrafficEvent


def setup():
    inst = make_instance(40, seed=2, time_windows=True)
    ev0 = Evaluator(inst, TrafficModel(peak=1.0))
    sol = greedy_solve(inst, ev0)
    zone = int(inst.zones[1])
    ev1 = Evaluator(inst, TrafficModel(peak=1.0).with_event(TrafficEvent(frozenset({zone}), 8.0, 16.0, 3.0)))
    top = [s for s in rank_partitions(sol, 5, ev0, ev1) if s.partition.size == 5][0].partition
    return sol, ev1, top, build_qubo(sol, top, ev1)


def brute(q):
    best = (np.inf, None)
    for order in itertools.permutations(q.customers):
        e = q.energy(q.x_from_order(order))
        best = min(best, (e, order))
    return best


def test_valid_permutations_have_zero_penalty():
    _, _, _, q = setup()
    for order in itertools.islice(itertools.permutations(q.customers), 30):
        x = q.x_from_order(order)
        assert abs(q.energy(x) - q.model_cost(order)) < 1e-9      # penalties vanish on permutations


def test_swap_sa_finds_brute_force_optimum():
    _, _, _, q = setup()
    e_opt, _ = brute(q)
    for seed in range(8):
        x, e, _ = anneal_qubo(q, np.random.default_rng(seed), SAParams(), "swap")
        assert abs(e - e_opt) < 1e-9


def test_flip_sa_mostly_valid_and_near_optimal():
    _, _, _, q = setup()
    e_opt, _ = brute(q)
    repaired, hits = 0, 0
    for seed in range(10):
        x, e, _ = anneal_qubo(q, np.random.default_rng(seed), SAParams(600, 10, 0.99), "flip")
        order, rep = decode(x, q)
        repaired += rep
        hits += abs(q.energy(q.x_from_order(order)) - e_opt) < 1e-6
    print("repaired", repaired, "optimal", hits, "of 10")
    assert repaired <= 1 and hits >= 8


def test_decoder_repairs_invalid():
    _, _, _, q = setup()
    x = np.zeros(q.n)                       # nothing selected
    order, rep = decode(x, q)
    assert rep and sorted(order) == sorted(q.customers)
    x = q.x_from_order(q.customers); x[1] = 1.0   # one extra bit
    order, rep = decode(x, q)
    assert sorted(order) == sorted(q.customers)
