"""Summarize completed four-method datasets without pooling statistical inference."""
import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

from .report import comparisons
from .solvers import METHODS


def mean(values):
    return statistics.mean(values) if values else None


def export_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows, label):
    keys = defaultdict(set)
    for row in rows:
        if row["feasible"]:
            keys[(row["dataset"], row["case"], row["seed"])].add(row["method"])
    joint = {key for key, methods in keys.items() if set(METHODS) <= methods}
    summary, cases = [], []
    for method in METHODS:
        selected = [r for r in rows if r["method"] == method]
        good = [r for r in selected if r["feasible"]]
        common = [r for r in good if (r["dataset"], r["case"], r["seed"]) in joint]
        grouped = defaultdict(list)
        for row in common:
            grouped[(row["dataset"], row["case"])].append(row)
        case_costs = []
        for dataset, case in sorted({(r["dataset"], r["case"]) for r in selected}):
            attempted = [r for r in selected if r["dataset"] == dataset and r["case"] == case]
            successful = [r for r in attempted if r["feasible"]]
            costs = [r["cost"] for r in successful]
            cases.append(dict(dataset=dataset, case=case, method=method,
                              feasible_runs=len(successful), attempted_runs=len(attempted),
                              mean_cost=mean(costs), best_cost=min(costs) if costs else None,
                              mean_optimization_seconds=mean([r["runtime_seconds"] for r in successful])))
        for group in grouped.values():
            case_costs.append(mean([r["cost"] for r in group]))
        summary.append(dict(
            dataset=label, method=method, attempted_runs=len(selected), feasible_runs=len(good),
            failed_runs=len(selected)-len(good), jointly_feasible_seed_pairs=len(common),
            jointly_feasible_cases=len(grouped),
            cumulative_case_mean_cost=sum(case_costs) if case_costs else None,
            mean_feasible_run_cost=mean([r["cost"] for r in good]),
            mean_improvement_from_initial_percent=mean([
                100*(r["initial_cost"]-r["cost"])/max(abs(r["initial_cost"]), 1e-9) for r in good]),
            mean_feasible_optimization_seconds=mean([r["runtime_seconds"] for r in good]),
            total_optimization_seconds=sum(r["runtime_seconds"] for r in selected),
            max_budget_overrun_seconds=max((r.get("budget_overrun_seconds", 0) for r in selected), default=0)))
    return summary, cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Parent containing completed dataset subdirectories")
    args = parser.parse_args()
    root = args.directory
    folders = sorted(p for p in root.iterdir() if p.is_dir() and (p/"runs.json").exists())
    if not folders:
        parser.error("No completed dataset subdirectories")
    all_rows, summaries, case_rows, datasets = [], [], [], {}
    for folder in folders:
        rows = json.loads((folder/"runs.json").read_text(encoding="utf-8"))
        manifest = json.loads((folder/"manifest.json").read_text(encoding="utf-8"))
        invalid = json.loads((folder/"invalid_inputs.json").read_text(encoding="utf-8"))
        audit = json.loads((folder/"audit.json").read_text(encoding="utf-8"))
        assert set(manifest["methods"]) == set(METHODS)
        assert audit["feasible_runs_audited"] == sum(r["feasible"] for r in rows)
        assert audit["declared_source_hashes_verified"] and audit["input_hashes_verified"]
        for row in rows:
            row["dataset"] = folder.name
        dataset_summary, dataset_cases = summarize(rows, folder.name)
        summaries.extend(dataset_summary)
        case_rows.extend(dataset_cases)
        all_rows.extend(rows)
        datasets[folder.name] = dict(
            summary=dataset_summary, paired_comparisons=comparisons(rows), invalid_inputs=invalid,
            failed_cases=sorted({r["case"] for r in rows if not r["feasible"]}),
            feasible_runs_audited=audit["feasible_runs_audited"],
            settings=manifest["settings"], seeds=manifest["seeds"])
    overall, _ = summarize(all_rows, "ALL_DATASETS_DESCRIPTIVE")
    summaries.extend(overall)
    export_csv(root/"aggregate_results.csv", summaries)
    export_csv(root/"case_results.csv", case_rows)
    output = dict(datasets=datasets, overall_descriptive=overall,
                  definitions={
                      "cumulative_case_mean_cost": "Sum across jointly feasible dataset/case groups of seed-mean INR cost. A descriptive basket of cases, not one fleet or an equal-case relative improvement.",
                      "paired_comparisons": "Separate by dataset; seed differences averaged within case. No pooled statistical inference across datasets.",
                      "failed_runs": "Construction failures have no finite quality score; excluded from cost calculations, retained in feasibility counts."})
    (root/"aggregate_results.json").write_text(json.dumps(output, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    text = ["# Four-approach complete test run", "",
            "Methods: Alphonsa / classical SA; Angel / tunnelling SA; Rahul / QUBO+SB; Parikshit / hybrid v2.", "",
            "Five seeds (20–24), hard windows, one second per optimization, identical initialization per case/seed. Hybrid local QUBO backend: classical binary SA. Traffic and costs are synthetic/offline.", "",
            "## Cumulative result", "",
            "Cumulative cost sums seed-averaged costs across jointly feasible cases. It is a descriptive basket, not the cost of one fleet. Large/expensive cases dominate it. Dataset-specific paired relative results below give every case equal weight.", "",
            "| Method | Feasible / attempted | Cumulative case-mean cost (INR) | Mean improvement from initial | Mean feasible runtime (s) |",
            "|---|---:|---:|---:|---:|"]
    for row in overall:
        text.append(f"| {row['method']} | {row['feasible_runs']} / {row['attempted_runs']} | {row['cumulative_case_mean_cost']:.2f} | {row['mean_improvement_from_initial_percent']:.2f}% | {row['mean_feasible_optimization_seconds']:.4f} |")
    for name, data in datasets.items():
        text += ["", f"## {name}", "",
                 f"{data['feasible_runs_audited']} feasible results independently audited; source and input hashes verified.", "",
                 "| Method | Feasible / attempted | Cumulative case-mean cost (INR) |",
                 "|---|---:|---:|"]
        for row in data["summary"]:
            text.append(f"| {row['method']} | {row['feasible_runs']} / {row['attempted_runs']} | {row['cumulative_case_mean_cost']:.2f} |")
        text += ["", "Positive paired reductions favour the hybrid. Intervals: case-bootstrap 95%; tests: two-sided Wilcoxon with Holm correction within this dataset.", "",
                 "| Against | Cases / paired seeds | Hybrid cost reduction | 95% interval | Case wins / ties / losses | Holm p |",
                 "|---|---:|---:|---:|---:|---:|"]
        for paired in data["paired_comparisons"]:
            if not paired["cases"]:
                continue
            lo, hi = paired["ci95"]
            text.append(f"| {paired['vs']} | {paired['cases']} / {paired['seed_pairs']} | {paired['mean_percent']:.2f}% | {lo:.2f}% to {hi:.2f}% | {paired['wins']} / {paired['ties']} / {paired['losses']} | {paired['p_holm']:.4g} |")
        text += ["", "Construction failures: " + (", ".join(data["failed_cases"]) or "none") + ".",
                 "Invalid inputs: " + ("; ".join(f"{r['case']}: {r['error']}" for r in data["invalid_inputs"]) or "none") + ".",
                 f"Detailed outputs: [{name}/REPORT.md]({name}/REPORT.md), [{name}/runs.csv]({name}/runs.csv), [{name}/audit.json]({name}/audit.json)."]
    text += ["", "## Interpretation and files", "",
             "All observations are retained, including failures, ties and losses. Construction failure is not an infeasibility proof. No no-QUBO ablation is included in this four-method run, so it cannot establish a QUBO-specific gain. Related Solomon variants are not independent base instances; supplied fixtures were used previously. These are new executions, not independent real-world holdout evidence. Do not pool dataset-level significance tests or infer quantum advantage.", "",
             "- `aggregate_results.csv` / `.json`: method totals and dataset summaries.",
             "- `case_results.csv`: per-case, per-method seed means and best costs.",
             "- `protocol.json`: declared scope, settings and reproduction commands.",
             "- Each dataset folder: raw routes, CSV, report, plots, audit, manifest and source snapshot.", "",
             "Rebuild this summary with `venv\\Scripts\\python.exe -B -m team_benchmark.summarize " + root.as_posix() + "`."]
    (root/"SUMMARY.md").write_text("\n".join(text)+"\n", encoding="utf-8")
    print(root/"SUMMARY.md")


if __name__ == "__main__":
    main()
