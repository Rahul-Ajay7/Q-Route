"""Paired, case-level analysis: seeds are repetitions, not independent instances."""
import math
import numpy as np
from scipy.stats import wilcoxon


def comparisons(rows, target="hybrid"):
    methods = sorted({r["method"] for r in rows if r["method"] != target})
    pairs = []
    for method in methods:
        lookup = {(r["case"], r["seed"], r["method"]): r for r in rows}
        cases = sorted({r["case"] for r in rows})
        diffs, seed_pairs = [], 0
        for case in cases:
            case_diffs = []
            for seed in sorted({r["seed"] for r in rows if r["case"] == case}):
                a = lookup.get((case, seed, target))
                b = lookup.get((case, seed, method))
                if a and b and a["feasible"] and b["feasible"]:
                    case_diffs.append(100*(b["cost"]-a["cost"])/max(abs(b["cost"]), 1e-9))
            if case_diffs:
                diffs.append(float(np.mean(case_diffs)))
                seed_pairs += len(case_diffs)
        if not diffs:
            pairs.append(dict(vs=method, cases=0, seed_pairs=0, mean_percent=None,
                              ci95=None, p=None, wins=0, ties=0, losses=0))
            continue
        values = np.array(diffs)
        rng = np.random.default_rng(20261021)
        boot = rng.choice(values, (10000, len(values)), replace=True).mean(axis=1)
        # Case resampling still assumes distinct case files are independent draws;
        # hand-crafted or related fixtures may violate that assumption.
        p = float(wilcoxon(values, alternative="two-sided").pvalue) if np.any(abs(values)>1e-9) else 1.0
        pairs.append(dict(vs=method, cases=len(values), seed_pairs=seed_pairs,
                          mean_percent=float(values.mean()), ci95=np.quantile(boot, [.025, .975]).tolist(), p=p,
                          wins=int(sum(values > 1e-9)), ties=int(sum(abs(values) <= 1e-9)),
                          losses=int(sum(values < -1e-9))))
    ordered = sorted([r for r in pairs if r["p"] is not None], key=lambda r: r["p"])
    running = 0.0
    for i, row in enumerate(ordered):
        running = max(running, min(1.0, row["p"]*(len(ordered)-i)))
        row["p_holm"] = running
    return pairs


def markdown(rows, invalid, manifest):
    text = ["# Controlled team comparison", "",
            "Exploratory offline benchmark. Lower INR cost is better. These results do not prove universal superiority.", "",
            f"Window policy: **{manifest['window_policy']}**. Optimization budget: **{manifest['settings']['seconds']} seconds per run**; identical initial routes per case/seed.", "",
            "Construction is shared and timed separately. Solver timing includes QUBO building, decoding, projection, and dynamic validation. Atomic actions may overrun the deadline; overruns are recorded.", "",
            "Current methods share bounded route caching; hybrid_v1_cached uses the old search with the same cache, while hybrid_legacy retains the old uncached implementation. The revised hybrid adds regret-based cross-vehicle repair and adaptive refinement intervals. These are new runs; historical output files are not pooled.", "",
            "| Method | Feasible / attempted | Mean improvement vs own shared initial (%) | Mean optimization seconds | Max budget overrun (s) |", "|---|---:|---:|---:|---:|"]
    for method in dict.fromkeys(r["method"] for r in rows):
        runs = [r for r in rows if r["method"] == method]
        good = [r for r in runs if r["feasible"]]
        imp = np.mean([100*(r["initial_cost"]-r["cost"])/max(r["initial_cost"], 1e-9) for r in good]) if good else math.nan
        secs = np.mean([r["runtime_seconds"] for r in runs])
        over = max(r.get("budget_overrun_seconds", 0) for r in runs)
        text.append(f"| {method} | {len(good)} / {len(runs)} | {imp:.2f} | {secs:.4f} | {over:.4f} |")
    text += ["", "## Hybrid paired comparisons", "",
             "Positive difference favours the hybrid. First average paired relative cost differences across seeds within each case; then compare cases. CI uses a case-level bootstrap; p-values use two-sided Wilcoxon and Holm correction across all comparisons.", "",
             "| Against | Cases / paired seeds | Hybrid cost reduction % (95% CI) | Case wins / ties / losses | Holm p |",
             "|---|---:|---:|---:|---:|"]
    paired = comparisons(rows)
    for row in paired:
        if not row["cases"]:
            text.append(f"| {row['vs']} | 0 | unavailable | — | — |")
            continue
        lo, hi = row["ci95"]
        text.append(f"| {row['vs']} | {row['cases']} / {row['seed_pairs']} | {row['mean_percent']:.2f} ({lo:.2f}, {hi:.2f}) | {row['wins']} / {row['ties']} / {row['losses']} | {row['p_holm']:.4g} |")
    main = [r for r in paired if r["vs"] in ("classical_sa", "tunnelling_sa", "qubo_sb")]
    supported = len(main) == 3 and all(r["cases"] >= 10 and r["mean_percent"] > 0 and
                                         r["ci95"][0] > 0 and r.get("p_holm", 1) < .05 for r in main)
    text += ["", "## Interpretation", "",
             ("This run supports lower mean hybrid cost against all three primary methods on this suite under this budget. Independent held-out instances and longer budgets are still required."
              if supported else "This run does **not establish that the hybrid beats all three primary methods**. Report the tradeoffs and paired losses; do not claim an overall win."), "",
             "All reported feasible routes passed a separate accounting/constraint audit. Construction failures are NO_FEASIBLE_INITIAL_SOLUTION, not infeasibility proofs; partial-route costs are excluded from quality comparisons.", "",
             "The paired table uses jointly feasible runs; see feasibility counts before interpreting it. Shared construction currently gives every method the same coverage failures. Hand-crafted related fixtures are not independent evidence of general performance; bootstrap intervals do not resolve dataset bias.", "",
             "Traffic and orders are known offline. No live API, mid-route frozen prefix, breakdown rescue, or online order insertion is implemented. QUBO coefficients approximate time/load propagation and use full-route acceptance. Window reordering alone cannot change vehicle assignments; global SA can.", "",
             "Angel's benchmark adapter reuses her original proposal code and tunnelling acceptance form with the common evaluator, initialization, and budget. It is not a rerun of her original standalone solver. QUBO+SA is a reference/ablation, not Angel's assigned method.", "",
             "Results depend on wall-clock scheduling. Use max_actions with a generous seconds limit for deterministic debugging, not as an assertion of equal computational work."]
    if invalid:
        text += ["", "## Invalid inputs (excluded, never silently repaired)", ""]
        text += [f"- {r['case']}: {r['error']}" for r in invalid]
    return "\n".join(text)+"\n"
