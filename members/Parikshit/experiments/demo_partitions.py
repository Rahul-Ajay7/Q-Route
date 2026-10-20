"""Greedy plan -> traffic event -> rank partitions by pressure (which stretch of which route to fix first)."""
import argparse
import numpy as np
from qorbit.config import CostParams
from qorbit.cost import Evaluator
from qorbit.data.synthetic import make_instance
from qorbit.data.solomon import load_solomon
from qorbit.optimization import greedy_solve, rank_partitions
from qorbit.traffic import TrafficModel, corridor_event

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=30)
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--factor", type=float, default=2.5)
ap.add_argument("--k", type=int, default=5)
ap.add_argument("--top", type=int, default=8)
ap.add_argument("--solomon")
a = ap.parse_args()

inst = load_solomon(a.solomon) if a.solomon else make_instance(a.n, a.seed)
solomon = bool(a.solomon)
params = CostParams()
t0 = TrafficModel(peak=1.0) if solomon else TrafficModel()
event = corridor_event(inst, np.random.default_rng(a.seed), a.factor)
t1 = t0.with_event(event)
ev0, ev1 = Evaluator(inst, t0, params), Evaluator(inst, t1, params)
sol = greedy_solve(inst, ev0, hard_tw=solomon)

c0, c1 = ev0.evaluate(sol).total_cost, ev1.evaluate(sol).total_cost
print(f"cost T0 Rs {c0:,.0f} -> T1 Rs {c1:,.0f}  (damage Rs {c1 - c0:,.0f});  event zone {sorted(event.zones)} x{event.factor}")
ranked = rank_partitions(sol, a.k, ev0, ev1)
print(f"\n{len(ranked)} partitions (k={a.k}); top {a.top} by pressure:")
print(f"{'veh':>4} {'positions':>10} {'customers':<28} {'score':>8} {'time':>7} {'fuel':>6} {'late':>7}")
for s in ranked[:a.top]:
    p = s.partition
    print(f"{p.vehicle_id:>4} {f'{p.start}-{p.end - 1}':>10} {str(list(p.customers)):<28} {s.total:>8.0f} {s.time:>7.0f} {s.fuel:>6.0f} {s.late:>7.0f}")
print(f"\npartitions with any pressure: {sum(1 for s in ranked if s.total > 1e-6)} of {len(ranked)}")