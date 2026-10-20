"""Parameter studies for Q-ORBIT.
  --sweep validity : % of QUBO samples that decode to a valid ordering WITHOUT repair, per penalty weight lambda
  --sweep lambda   : recovery and repair rate of the full repair loop per lambda (flip variant)
  --sweep k        : recovery and runtime per partition size k (swap variant and direct SA)
usage: python experiments/run_sweeps.py --sweep k --solomon data/solomon/R101.txt --seeds 6 --solves 15"""
import argparse
import os
import time
import numpy as np
import pandas as pd
from qorbit.config import CostParams, QuboParams
from qorbit.cost import Evaluator
from qorbit.data.solomon import load_solomon
from qorbit.data.synthetic import make_instance
from qorbit.optimization import (DirectSA, QuboSA, SAParams, anneal_qubo, build_qubo, decode, greedy_solve,
                                 polish_windows, rank_partitions, run_repair)
from qorbit.traffic import TrafficModel, corridor_event

ap = argparse.ArgumentParser()
ap.add_argument("--sweep", required=True, choices=["validity", "lambda", "k"])
ap.add_argument("--solomon")
ap.add_argument("--n", type=int, default=60)
ap.add_argument("--tw", action="store_true")
ap.add_argument("--seeds", type=int, default=6)
ap.add_argument("--solves", type=int, default=15)
ap.add_argument("--factor", type=float, default=3.0)
ap.add_argument("--zones", type=int, default=2)
ap.add_argument("--k", type=int, default=5)
ap.add_argument("--lambdas", default="0.5,1,1.5,2,3")
ap.add_argument("--ks", default="4,5,6,7,8")
ap.add_argument("--samples", type=int, default=60, help="QUBO samples per lambda for --sweep validity")
a = ap.parse_args()
solomon = bool(a.solomon)
os.makedirs("results", exist_ok=True)


def scenario(seed, k):
    inst = load_solomon(a.solomon) if solomon else make_instance(a.n, seed, time_windows=a.tw)
    t0 = TrafficModel(peak=1.0) if solomon else TrafficModel()
    event = corridor_event(inst, np.random.default_rng(1000 + seed), a.factor, n_zones=a.zones)
    ev0, ev1 = Evaluator(inst, t0, CostParams()), Evaluator(inst, t0.with_event(event), CostParams())
    sol0 = polish_windows(greedy_solve(inst, ev0, hard_tw=solomon), ev0, k=k, hard_tw=solomon)
    return inst, sol0, ev0, ev1


def recovery(sol0, ev0, ev1, final):
    pre, dam = ev0.evaluate(sol0).total_cost, ev1.evaluate(sol0).total_cost
    return 100 * (dam - final) / max(dam - pre, 1e-9)


rows = []
if a.sweep == "validity":
    sa = SAParams(300, 6, 0.98)                 # cheaper than production settings: validity is what is measured
    inst, sol0, ev0, ev1 = scenario(0, a.k)
    parts = [s.partition for s in rank_partitions(sol0, a.k, ev0, ev1) if s.partition.size == a.k][:3]
    for lam in [float(x) for x in a.lambdas.split(",")]:
        valid = total = 0
        for part in parts:
            q = build_qubo(sol0, part, ev1, QuboParams(lambda_assign=lam, lambda_position=lam))
            for s in range(max(1, a.samples // len(parts))):
                x, _, _ = anneal_qubo(q, np.random.default_rng(s), sa, "flip")
                total += 1
                valid += not decode(x, q)[1]
        rows.append(dict(lam=lam, samples=total, valid_pct=100 * valid / total))
        print(f"lambda {lam:>4}: {100 * valid / total:5.1f}% of {total} samples decode to a valid ordering without repair")
    out = "results/sweep_validity.csv"
elif a.sweep == "lambda":
    for lam in [float(x) for x in a.lambdas.split(",")]:
        for seed in range(a.seeds):
            inst, sol0, ev0, ev1 = scenario(seed, a.k)
            solver = QuboSA("flip", qp=QuboParams(lambda_assign=lam, lambda_position=lam))
            t = time.perf_counter()
            cur, r = run_repair(sol0, ev0, ev1, solver, np.random.default_rng(seed), k=a.k, max_solves=a.solves)
            rows.append(dict(lam=lam, seed=seed, rec=recovery(sol0, ev0, ev1, r[-1]["cost"]),
                             repaired=sum(x["repaired"] for x in r), solves=len(r) - 1, seconds=time.perf_counter() - t))
        d = pd.DataFrame(rows); d = d[d.lam == lam]
        print(f"lambda {lam:>4}: recovered {d.rec.mean():5.1f}%  repaired decodes {d.repaired.sum()} of {d.solves.sum()}  {d.seconds.mean():.1f}s/run")
    out = "results/sweep_lambda.csv"
else:
    for k in [int(x) for x in a.ks.split(",")]:
        for seed in range(a.seeds):
            inst, sol0, ev0, ev1 = scenario(seed, k)
            for name, solver in (("qorbit_swap", QuboSA("swap")), ("direct_sa", DirectSA())):
                t = time.perf_counter()
                cur, r = run_repair(sol0, ev0, ev1, solver, np.random.default_rng(seed), k=k, max_solves=a.solves)
                rows.append(dict(k=k, vars=k * k, method=name, seed=seed, rec=recovery(sol0, ev0, ev1, r[-1]["cost"]),
                                 seconds=time.perf_counter() - t, solves=len(r) - 1))
        d = pd.DataFrame(rows); d = d[d.k == k]
        print(f"k={k} ({k * k:>2} vars): " + "   ".join(f"{m} {g.rec.mean():5.1f}% in {g.seconds.mean():5.1f}s" for m, g in d.groupby("method")))
    out = "results/sweep_k.csv"
pd.DataFrame(rows).to_csv(out, index=False)
print("saved", out)