"""Statistics for one or more run_dynamic CSVs: mean, median, variability, runtime, improvement rate,
bootstrap CI and paired tests (Wilcoxon + wins/ties/losses).
usage: python experiments/analyze_results.py results/mine.csv [results/other.csv ...] [--ref qorbit_flip]"""
import os
import sys
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

args = [a for a in sys.argv[1:] if not a.startswith("--")]
ref = "qorbit_flip"
if "--ref" in sys.argv:
    ref = sys.argv[sys.argv.index("--ref") + 1]
    args.remove(ref)
if not args:
    sys.exit(__doc__)

df = pd.concat([pd.read_csv(p).assign(source=p) for p in args], ignore_index=True)
df["case"] = df.source + ":" + df.seed.astype(str)          # one (file, seed) = one scenario
last = df.sort_values("step").groupby(["case", "method"]).tail(1).copy()
last["rec"] = 100 * (last.cost_damaged - last.cost) / (last.cost_damaged - last.cost_pre).clip(lower=1e-9)
last["improved"] = (last.cost < last.cost_damaged - 1e-9).astype(int)
steps = df[df.step > 0].groupby(["case", "method"]).agg(solves=("step", "max"), n_accepted=("accepted", "sum"))
last = last.drop(columns=["accepted"]).merge(steps, on=["case", "method"], how="left")
rng = np.random.default_rng(0)


def boot_ci(x, n=2000):
    x = np.asarray(x, float)
    m = [rng.choice(x, len(x)).mean() for _ in range(n)]
    return np.percentile(m, 2.5), np.percentile(m, 97.5)


order = [m for m in ["do_nothing", "greedy_rebuild", "rebuild_polish", "direct_sa", "qorbit_flip", "qorbit_swap", "qorbit_random"]
         if m in set(last.method)]
lines = [f"## Recovery of traffic damage ({last.case.nunique()} scenarios; recovered % = share of the damage won back)\n",
         "| method | mean | 95% CI | median | std | IQR | min..max | improved | runtime s | solves | accepted/solve |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
for m in order:
    d = last[last.method == m]
    lo, hi = boot_ci(d.rec)
    q1, q3 = np.percentile(d.rec, [25, 75])
    has = d.solves.notna().any()
    sv = f"{d.solves.mean():.0f}" if has else "n/a"
    ac = f"{(d.n_accepted / d.solves).mean():.3f}" if has else "n/a"
    lines.append(f"| {m} | {d.rec.mean():.1f} | {lo:.1f}..{hi:.1f} | {d.rec.median():.1f} | {d.rec.std():.1f} | {q1:.1f}..{q3:.1f} | "
                 f"{d.rec.min():.1f}..{d.rec.max():.1f} | {100 * d.improved.mean():.0f}% | {d.elapsed_s.mean():.2f} | {sv} | {ac} |")

piv = last.pivot(index="case", columns="method", values="rec")
lines += [f"\n## Paired comparison of `{ref}` against the others (same scenarios)\n",
          "| vs | mean diff (pp) | wins / ties / losses | Wilcoxon p |", "|---|---|---|---|"]
for m in order:
    if m == ref or ref not in piv or m not in piv:
        continue
    diff = (piv[ref] - piv[m]).dropna()
    try:
        p = wilcoxon(diff).pvalue if (diff != 0).any() else 1.0
    except ValueError:
        p = float("nan")
    lines.append(f"| {m} | {diff.mean():+.2f} | {(diff > 1e-9).sum()} / {(diff.abs() <= 1e-9).sum()} / {(diff < -1e-9).sum()} | {p:.3f} |")
lines.append("\nWilcoxon drops tied pairs, so with many ties it has little power; read wins/ties/losses alongside it.")

# ---- what changed in distance, time, fuel, lateness (not only total cost) ----
import os
mets = []
for p_ in args:
    mp = p_.replace(".csv", "_metrics.csv")
    if os.path.exists(mp):
        mets.append(pd.read_csv(mp).assign(source=p_))
if mets:
    M = pd.concat(mets, ignore_index=True)
    M["case"] = M.source + ":" + M.seed.astype(str)
    cols = ["distance_km", "route_hours", "fuel_l", "late_min", "vehicles", "cost"]
    base = M[M.stage == "damaged"].set_index("case")[cols]
    pre = M[M.stage == "pre_event"].set_index("case")[cols]
    lines += ["\n## Effect on distance, route time, fuel and lateness (mean per scenario)\n",
              f"Damage = (damaged plan) - (pre-event plan); a method's change = (its final plan) - (damaged plan). Negative change = improvement.\n",
              "| | distance km | route hours | fuel L | lateness min | vehicles | total cost INR |", "|---|---|---|---|---|---|---|",
              "| pre-event plan (absolute) | " + " | ".join(f"{pre[c].mean():.1f}" for c in cols) + " |",
              "| damage caused by the event | " + " | ".join(f"{(base[c] - pre[c]).mean():+.1f}" for c in cols) + " |"]
    for m in order:
        d = M[(M.stage == "final") & (M.method == m)].set_index("case")[cols]
        if len(d):
            lines.append(f"| {m}: change vs damaged | " + " | ".join(f"{(d[c] - base.loc[d.index, c]).mean():+.2f}" for c in cols) + " |")
    lines.append("\nCost components of the damage (mean INR): " + ", ".join(
        f"{c.replace('cost_', '')} {(M[M.stage == 'damaged'].set_index('case')[c] - M[M.stage == 'pre_event'].set_index('case')[c]).mean():+.0f}"
        for c in ["cost_distance", "cost_time", "cost_fuel", "cost_late", "cost_vehicle"]))
text = "\n".join(lines)
print(text)
os.makedirs("results", exist_ok=True)
open("results/stats.md", "w").write(text + "\n")
print("\nsaved results/stats.md")
