"""Stages 1-5 of a run: build routes under T0, hit them with a traffic event, see the damage."""
import argparse
import numpy as np
from qorbit.config import CostParams
from qorbit.cost import Evaluator
from qorbit.data.synthetic import make_instance
from qorbit.data.solomon import load_solomon
from qorbit.optimization import greedy_solve
from qorbit.traffic import TrafficModel, corridor_event

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=30)
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--factor", type=float, default=2.5)
ap.add_argument("--solomon", help="path to a Solomon .txt file (overrides --n)")
ap.add_argument("--soft-tw", action="store_true", help="time windows as penalties (default for synthetic; Solomon defaults to HARD)")
ap.add_argument("--hard-tw", action="store_true", help="force hard time windows")
a = ap.parse_args()

inst = load_solomon(a.solomon) if a.solomon else make_instance(a.n, a.seed)
solomon = bool(a.solomon)
build_hard = a.hard_tw or (solomon and not a.soft_tw)   # plan must respect windows (Solomon default)
params = CostParams()                                    # evaluation: lateness is a penalty, so disruption has a price
t0 = TrafficModel(peak=1.0) if solomon else TrafficModel()   # Solomon windows assume free-flow travel
print(f"initial plan: time windows {'HARD' if build_hard else 'soft'}; traffic T0: {'free-flow' if solomon else 'daily profile'}")
rng = np.random.default_rng(a.seed)
event = corridor_event(inst, rng, a.factor)
t1 = t0.with_event(event)

sol = greedy_solve(inst, Evaluator(inst, t0, params), hard_tw=build_hard)
r0 = Evaluator(inst, t0, params).evaluate(sol)
r1 = Evaluator(inst, t1, params).evaluate(sol)

print(f"customers={len(inst.customers)}  vehicles used={sum(1 for r in sol.routes.values() if r)}  feasible={r0.feasible}")
for vid, route in sol.routes.items():
    if route:
        print(f"  vehicle {vid}: 0 -> {' -> '.join(map(str, route))} -> 0")
print(f"\ncost under T0 (greedy built here): Rs {r0.total_cost:,.0f}")
print(f"event: zone {sorted(event.zones)} x{event.factor} from {event.start:.1f}h to {event.end:.1f}h")
print(f"cost under T1 (do nothing)       : Rs {r1.total_cost:,.0f}  (+{r1.total_cost - r0.total_cost:,.0f})")
print("\nextra cost caused by the event, per vehicle (this is the partition 'pressure' to come):")
rows = sorted(((r1.routes[v].total - r0.routes[v].total, v) for v in r0.routes if r0.routes[v].used), reverse=True)
for extra, v in rows:
    print(f"  vehicle {v}: +Rs {extra:,.0f}")