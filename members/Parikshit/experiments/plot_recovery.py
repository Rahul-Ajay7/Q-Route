"""Plots: (1) recovery curves vs local solves and vs seconds, (2) final recovery box plot."""
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

path = sys.argv[1] if len(sys.argv) > 1 else "results/run.csv"
out = sys.argv[2] if len(sys.argv) > 2 else "results/figures/recovery.png"
df = pd.read_csv(path)
df["rec"] = 100 * (df.cost_damaged - df.cost) / (df.cost_damaged - df.cost_pre).clip(lower=1e-9)
order = [m for m in ["do_nothing", "greedy_rebuild", "rebuild_polish", "direct_sa", "qorbit_flip", "qorbit_swap", "qorbit_random"] if m in set(df.method)]
colors = dict(zip(order, ["#888888", "#d95f02", "#a6761d", "#1b9e77", "#7570b3", "#e7298a", "#66a61e"]))
seeds = sorted(df.seed.unique())

def curve(sub, xcol, grid):
    ys = []
    for s in seeds:
        d = sub[sub.seed == s].sort_values(xcol)
        idx = np.searchsorted(d[xcol].values, grid, side="right") - 1
        ys.append(d.rec.values[np.clip(idx, 0, None)])
    return np.array(ys)

fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
smax = int(df[df.method.isin(["direct_sa", "qorbit_flip", "qorbit_swap", "qorbit_random"])].step.max())
tmax = df[df.method.isin(["direct_sa", "qorbit_flip", "qorbit_swap", "qorbit_random"])].elapsed_s.max()
for m in order:
    sub = df[df.method == m]
    if m in ("greedy_rebuild", "rebuild_polish"):
        final = sub[sub.step == 1]
        for a_ in ax:
            a_.axhline(final.rec.mean(), color=colors[m], ls="--", label=m + " (final)")
        continue
    for a_, xcol, grid in ((ax[0], "step", np.arange(0, smax + 1)), (ax[1], "elapsed_s", np.linspace(0, tmax, 200))):
        y = curve(sub, xcol, grid)
        a_.plot(grid, np.nanmean(y, axis=0), color=colors[m], label=m, lw=2)
        if m != "do_nothing":
            a_.fill_between(grid, np.nanpercentile(y, 25, axis=0), np.nanpercentile(y, 75, axis=0), color=colors[m], alpha=0.12)
ax[0].set_xlabel("local solves after the traffic event"); ax[1].set_xlabel("optimisation time after the event (s)")
for a_ in ax:
    a_.set_ylabel("% of traffic damage recovered"); a_.grid(alpha=.3)
ax[0].legend(); ax[0].set_title(f"Cost recovery ({len(seeds)} seeds, mean and IQR)")
plt.tight_layout(); plt.savefig(out, dpi=140)

last = df.sort_values("step").groupby(["seed", "method"]).tail(1)
fig, a_ = plt.subplots(figsize=(8, 4.5))
a_.boxplot([last[last.method == m].rec.values for m in order], labels=order, showmeans=True)
a_.set_ylabel("% of damage recovered (final)"); a_.grid(alpha=.3); plt.xticks(rotation=20); plt.tight_layout()
plt.savefig(out.replace(".png", "_box.png"), dpi=140)
print("saved", out, "and", out.replace(".png", "_box.png"))
