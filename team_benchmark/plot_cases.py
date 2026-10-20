"""Create per-case and cumulative graphs from saved four-method runs."""
import argparse
import json
import os
from pathlib import Path
import statistics
import tempfile

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "qorbit-mpl"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.ticker import StrMethodFormatter

from .solvers import METHODS

LABELS = ["Alphonsa\nClassical SA", "Angel\nTunnelling SA", "Rahul\nQUBO+SB", "Parikshit\nHybrid v2"]
COLORS = ["#5078a0", "#a778ad", "#dd9d48", "#27856b"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    root = args.directory
    protocol = json.loads((root/"protocol.json").read_text(encoding="utf-8"))
    aggregates = json.loads((root/"aggregate_results.json").read_text(encoding="utf-8"))
    output = root/"plots"
    output.mkdir(exist_ok=True)
    links = []
    count = 0
    with PdfPages(output/"ALL_CASES_AND_CUMULATIVE.pdf", metadata={
        "Title": "Q-ORBIT: every case and cumulative four-method comparison"}) as pdf:
        for dataset, declaration in protocol["datasets"].items():
            rows = json.loads((root/dataset/"runs.json").read_text(encoding="utf-8"))
            invalid = {r["case"]: r["error"] for r in json.loads(
                (root/dataset/"invalid_inputs.json").read_text(encoding="utf-8"))}
            folder = output/"per_case"/dataset
            folder.mkdir(parents=True, exist_ok=True)
            links += ["", f"## {dataset}", ""]
            for case in declaration["cases"]:
                selected = [r for r in rows if r["case"] == case]
                fig, ax = plt.subplots(figsize=(10, 6.5), layout="constrained")
                fig.suptitle(f"{dataset} / {case}", fontsize=16, weight="bold")
                if any(r["feasible"] for r in selected):
                    for i, method in enumerate(METHODS):
                        attempts = sorted((r for r in selected if r["method"] == method), key=lambda r: r["seed"])
                        good = [r for r in attempts if r["feasible"]]
                        costs = [r["cost"] for r in good]
                        if not costs:
                            ax.text(i, 0.05, "No feasible score", transform=ax.get_xaxis_transform(), ha="center")
                            continue
                        avg = statistics.mean(costs)
                        sd = statistics.stdev(costs) if len(costs) > 1 else 0
                        ax.bar(i, avg, yerr=sd, capsize=5, width=.62, color=COLORS[i], alpha=.8)
                        offsets = [(j-(len(costs)-1)/2)*.055 for j in range(len(costs))]
                        ax.scatter([i+v for v in offsets], costs, color="#233343", s=24, zorder=4)
                        ax.annotate(f"{avg:,.2f}\n{len(good)}/{len(attempts)} feasible",
                                    (i, max(costs+[avg+sd])), xytext=(0, 9), textcoords="offset points",
                                    ha="center", va="bottom", fontsize=9)
                    ax.set_xticks(range(4), LABELS)
                    ax.set_ylabel("Full operating cost (synthetic INR) — lower is better")
                    ax.set_ylim(bottom=0, top=ax.get_ylim()[1]*1.18)
                    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
                    ax.grid(axis="y", alpha=.2)
                    ax.set_axisbelow(True)
                    ax.set_title("Bars: seed means • whiskers: ±1 sample SD • dots: individual seeds", fontsize=10)
                else:
                    ax.axis("off")
                    reason = ("INVALID INPUT\n"+invalid[case] if case in invalid else
                              "NO FEASIBLE INITIAL SOLUTION\nShared construction failed for all four methods and five seeds.")
                    ax.text(.5, .58, reason, ha="center", va="center", transform=ax.transAxes,
                            fontsize=14, wrap=True, color="#9a453b")
                    ax.text(.5, .30, "No finite quality score is available.\nThis is not a zero-cost result or an infeasibility proof.",
                            ha="center", transform=ax.transAxes, fontsize=11)
                fig.supxlabel("Five seeds (20–24) • hard windows • 1 s per optimization • shared initial routes", fontsize=9)
                filename = folder/(Path(case).stem+".png")
                fig.savefig(filename, dpi=160)
                pdf.savefig(fig)
                plt.close(fig)
                links.append(f"- [{case}]({filename.relative_to(output).as_posix()})")
                count += 1
        fig, axes = plt.subplots(1, 3, figsize=(15, 6), layout="constrained")
        groups = [(name, aggregates["datasets"][name]["summary"]) for name in protocol["datasets"]]
        groups.append(("All datasets (descriptive)", aggregates["overall_descriptive"]))
        for ax, (name, summary) in zip(axes, groups):
            lookup = {r["method"]: r for r in summary}
            costs = [lookup[m]["cumulative_case_mean_cost"] for m in METHODS]
            ax.bar(range(4), costs, color=COLORS)
            ax.set_xticks(range(4), ["Classical\nSA", "Tunnelling\nSA", "QUBO+SB", "Hybrid\nv2"])
            ax.set_title(name.replace("_", " "), fontsize=12)
            ax.set_ylim(0, max(costs)*1.18)
            ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
            ax.grid(axis="y", alpha=.2)
            ax.set_axisbelow(True)
            for i, cost in enumerate(costs):
                ax.annotate(f"{cost:,.2f}", (i, cost), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=8)
        axes[0].set_ylabel("Sum of per-case seed-mean costs (synthetic INR)")
        fig.suptitle("Cumulative four-approach cost — lower is better", fontsize=17, weight="bold")
        fig.supxlabel("30 jointly feasible dataset/case groups; failed/invalid cases have no cost.\nDescriptive case basket: expensive cases dominate. Dataset-level statistical inference remains separate.", fontsize=10)
        fig.savefig(output/"cumulative_comparison.png", dpi=180)
        fig.savefig(output/"cumulative_comparison.svg")
        pdf.savefig(fig)
        plt.close(fig)
    index = ["# Comparison graphs", "",
             f"{count} individual case pages (including explicit invalid/construction-failure pages), plus one cumulative page.", "",
             "[Complete PDF](ALL_CASES_AND_CUMULATIVE.pdf) · [Cumulative PNG](cumulative_comparison.png) · [Cumulative SVG](cumulative_comparison.svg)", "",
             "Per-case bars are seed means; whiskers are one sample standard deviation, not confidence intervals. Dots show individual seeds. No optimizer was rerun to create these figures.",
             "Cumulative totals sum per-case seed means over jointly feasible cases. They are not the operating cost of a single fleet. See [the full summary](../SUMMARY.md) for paired statistics and limitations."]
    (output/"README.md").write_text("\n".join(index+links)+"\n", encoding="utf-8")
    print(f"Created {count} per-case PNGs, cumulative PNG/SVG and a {count+1}-page PDF in {output}")


if __name__ == "__main__":
    main()
