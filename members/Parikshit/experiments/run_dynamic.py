"""Main experiment: for each seed build a plan, hit it with a traffic event, run every method from the
same damaged plan, log (step, elapsed, cost) -> CSV, print a summary table."""
import argparse
import os
import numpy as np
import pandas as pd
from qorbit.config import CostParams
from qorbit.cost import Evaluator
from qorbit.data.solomon import load_solomon
from qorbit.data.synthetic import make_instance
from qorbit.optimization import greedy_solve, polish_windows
from qorbit.sim.methods import METHODS, Context, run_method
from qorbit.sim.metrics import solution_metrics
from qorbit.traffic import TrafficModel, corridor_event

ap = argparse.ArgumentParser()
ap.add_argument("--solomon", help="Solomon .txt (otherwise synthetic --n)")
ap.add_argument("--n", type=int, default=50)
ap.add_argument("--seeds", type=int, default=5)
ap.add_argument("--factor", type=float, default=3.0)
ap.add_argument("--zones", type=int, default=2, help="number of congested zones")
ap.add_argument("--tw", action="store_true", help="synthetic instances get time windows")
ap.add_argument("--k", type=int, default=5)
ap.add_argument("--solves", type=int, default=40)
ap.add_argument("--methods", default=",".join(METHODS))
ap.add_argument("--out", default="results/run.csv")
ap.add_argument("--no-preopt", action="store_true", help="skip polishing the pre-event plan (NOT recommended: gains then mix traffic repair with generic improvement)")
a = ap.parse_args()

methods = a.methods.split(",")
solomon = bool(a.solomon)
params = CostParams()
rows = []
mrows = []


for seed in range(a.seeds):
    inst = load_solomon(a.solomon) if solomon else make_instance(a.n, seed, time_windows=a.tw)
    t0 = TrafficModel(peak=1.0) if solomon else TrafficModel()
    event = corridor_event(inst, np.random.default_rng(1000 + seed), a.factor, n_zones=a.zones)
    t1 = t0.with_event(event)
    ev0, ev1 = Evaluator(inst, t0, params), Evaluator(inst, t1, params)
    sol0 = greedy_solve(inst, ev0, hard_tw=solomon)
    if not a.no_preopt:
        sol0 = polish_windows(sol0, ev0, k=a.k, hard_tw=solomon)   # locally optimal over every k-window ordering
    c_pre, c_dam = ev0.evaluate(sol0).total_cost, ev1.evaluate(sol0).total_cost
    print(f"seed {seed}: pre-event Rs {c_pre:,.0f}, damaged Rs {c_dam:,.0f} (+{c_dam - c_pre:,.0f})")
    mrows.append(dict(seed=seed, method="(pre_event)", stage="pre_event", **solution_metrics(ev0, sol0)))
    mrows.append(dict(seed=seed, method="(damaged)", stage="damaged", **solution_metrics(ev1, sol0)))
    for m in methods:
        ctx = Context(inst, sol0, ev0, ev1, np.random.default_rng(seed), hard_build=solomon, k=a.k, max_solves=a.solves)
        for r in run_method(m, ctx):
            rows.append(dict(seed=seed, method=m, cost_pre=c_pre, cost_damaged=c_dam, **r))
        mrows.append(dict(seed=seed, method=m, stage="final", **solution_metrics(ev1, ctx.final)))

df = pd.DataFrame(rows)
os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
df.to_csv(a.out, index=False)
pd.DataFrame(mrows).to_csv(a.out.replace(".csv", "_metrics.csv"), index=False)

last = df.sort_values("step").groupby(["seed", "method"]).tail(1).copy()
last["recovered_pct"] = 100 * (last.cost_damaged - last.cost) / (last.cost_damaged - last.cost_pre).clip(lower=1e-9)
acc = df[df.step > 0].groupby(["seed", "method"]).agg(solves=("step", "max"), n_accepted=("accepted", "sum"), n_repaired=("repaired", "sum"))
last = last.drop(columns=["accepted", "repaired"]).merge(acc, on=["seed", "method"], how="left")
summ = last.groupby("method").agg(final_cost=("cost", "mean"), recovered_pct=("recovered_pct", "mean"),
                                  seconds=("elapsed_s", "mean"), solves=("solves", "mean"),
                                  accepted=("n_accepted", "mean"), qubo_repaired=("n_repaired", "mean")).round(2)
print("\nSUMMARY (mean over seeds); recovered_pct = share of the traffic damage won back (100 = back to pre-event cost)")
print(summ.reindex([m for m in methods if m in summ.index]).to_string())
print("\nsaved", a.out)
