"""python -m team_benchmark.run --help"""
import argparse
from dataclasses import asdict
import hashlib
import json
import math
import platform
from pathlib import Path
import time

import numpy as np

from .problem import Problem, ROOT
from .solvers import METHODS, ABLATIONS, Settings, solve
from .audit import audit
from .report import markdown, comparisons
from .provenance import write_sources


def safe(value):
    if isinstance(value, dict):
        return {str(k): safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def save(path, value):
    Path(path).write_text(json.dumps(safe(value), indent=2, allow_nan=False)+"\n", encoding="utf-8")


def parser():
    ap = argparse.ArgumentParser(description="Fair offline team CVRPTW comparison; no predetermined winner")
    ap.add_argument("--cases-dir", type=Path, default=ROOT / "members/Rahul/test_cases")
    ap.add_argument("--cases", nargs="+", help="Case filenames (default every TC*.json)")
    ap.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2, 3, 4])
    ap.add_argument("--methods", nargs="+", choices=METHODS+ABLATIONS, default=list(METHODS))
    ap.add_argument("--ablations", action="store_true")
    ap.add_argument("--seconds", type=float, default=1.0)
    ap.add_argument("--max-actions", type=int, default=1000000)
    ap.add_argument("--window", type=int, default=5)
    ap.add_argument("--samples", type=int, default=8)
    ap.add_argument("--qubo-steps", type=int, default=40)
    ap.add_argument("--plateau", type=int, default=50)
    ap.add_argument("--hybrid-backend", choices=("sa","sb"), default="sa")
    ap.add_argument("--soft-windows", action="store_true", help="Penalize lateness rather than reject; changes the problem")
    ap.add_argument("--output", type=Path, default=ROOT / "results/comparison/latest")
    return ap


def main(argv=None):
    ap = parser()
    a = ap.parse_args(argv)
    cfg = Settings(seconds=a.seconds, max_actions=a.max_actions, window=a.window,
                   samples=a.samples, qubo_steps=a.qubo_steps, plateau=a.plateau,
                   hybrid_backend=a.hybrid_backend)
    cfg.validate()
    if any(s < 0 for s in a.seeds):
        ap.error("Seeds must be nonnegative")
    if len(set(a.seeds)) != len(a.seeds):
        ap.error("Duplicate seeds are not independent repetitions")
    paths = ([a.cases_dir / name for name in a.cases] if a.cases else sorted(a.cases_dir.glob("TC*.json")))
    if not paths:
        ap.error("No input cases found")
    if len({p.resolve() for p in paths}) != len(paths):
        ap.error("Duplicate input cases")
    methods = list(dict.fromkeys(a.methods + (list(ABLATIONS) if a.ablations else [])))
    out = a.output.resolve()
    # Experiment outputs cannot overwrite source cases or source code.
    if out == ROOT or any(p.resolve().is_relative_to(out) for p in paths):
        ap.error("Output directory must not contain input cases or be the repository root")
    out.mkdir(parents=True, exist_ok=True)
    if (out/"runs.json").exists():
        ap.error("Output already contains recorded runs; choose a new output directory")
    source_paths = list((ROOT / "team_benchmark").glob("*.py")) + [ROOT/"members/Rahul/run_sb.py", ROOT/"members/Angel/saq_cvrptw.py"]
    source_hashes=write_sources(ROOT,source_paths,out/"sources.zip")
    manifest = dict(settings=asdict(cfg), methods=methods, seeds=a.seeds,
                    window_policy="soft" if a.soft_windows else "hard",
                    python=platform.python_version(), numpy=np.__version__, platform=platform.platform(),
                    source_sha256=source_hashes,
                    input_sha256={}, construction="nearest-neighbour then up to 8 insertion restarts",
                    traffic="offline, departure-dependent; wait through closures; latest active event wins",
                    cost_units="INR; synthetic coordinate km, input time minutes")
    rows, invalid = [], []
    for path in paths:
        try:
            manifest["input_sha256"][str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
            problem = Problem.load(path, not a.soft_windows)
        except (ValueError, KeyError, TypeError, OSError) as exc:
            invalid.append(dict(case=path.name, error=str(exc)))
            print(f"{path.name}: INVALID INPUT: {exc}", flush=True)
            continue
        for seed in a.seeds:
            start = time.perf_counter()
            initial = problem.initial(seed)
            construction_seconds = time.perf_counter()-start
            if problem.evaluate(initial)["feasible"]:
                audit(problem, initial)
            # Rotate method execution order by seed to reduce fixed-order timing bias.
            offset = seed % len(methods)
            order = methods[offset:] + methods[:offset]
            for method in order:
                result = solve(problem, initial, method, seed, cfg)
                result.update(case=path.name, case_id=problem.data.get("id", path.stem),
                              construction_seconds=construction_seconds,
                              total_seconds=construction_seconds+result["runtime_seconds"])
                if result["feasible"]:
                    checked = audit(problem, result["routes"])
                    for key, value in checked.items():
                        actual = result["cost"] if key == "cost" else result["metrics"][key]
                        assert math.isclose(actual, value, rel_tol=1e-10, abs_tol=1e-7), (key, actual, value)
                    result["independent_audit_passed"] = True
                    assert result["cost"] <= result["initial_cost"]+1e-7
                rows.append(result)
                cost = f"{result['cost']:.2f}" if result["cost"] is not None else "unavailable"
                print(f"{path.name} seed={seed} {method}: {result['status']} cost={cost} t={result['runtime_seconds']:.3f}s", flush=True)
            # Persist each completed case/seed, so interrupted long runs retain evidence.
            save(out / "runs.json", rows)
        save(out / "manifest.json", manifest)
    save(out / "runs.json", rows)
    save(out / "invalid_inputs.json", invalid)
    save(out / "manifest.json", manifest)
    save(out / "paired_comparisons.json", comparisons(rows))
    (out / "REPORT.md").write_text(markdown(rows, invalid, manifest), encoding="utf-8")
    print(f"Report: {out / 'REPORT.md'}", flush=True)
    return 1 if invalid else 0


if __name__ == "__main__":
    raise SystemExit(main())
