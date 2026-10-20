"""Single-case entrypoint shared by the member folders."""
import argparse
import json
from pathlib import Path
import time

from .problem import Problem
from .solvers import Settings, solve
from .audit import audit
from .run import safe


def main(method):
    ap = argparse.ArgumentParser(description=f"{method}: common CVRPTW objective and constraints")
    ap.add_argument("input", type=Path)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--seconds", type=float, default=1.0)
    ap.add_argument("--soft-windows", action="store_true")
    ap.add_argument("--hybrid-backend", choices=("sa","sb"), default="sa")
    ap.add_argument("--output", type=Path)
    a = ap.parse_args()
    problem = Problem.load(a.input, not a.soft_windows)
    started = time.perf_counter()
    initial = problem.initial(a.seed)
    construction = time.perf_counter()-started
    result = solve(problem, initial, method, a.seed, Settings(seconds=a.seconds,hybrid_backend=a.hybrid_backend))
    result["construction_seconds"] = construction
    if result["feasible"]:
        audit(problem, result["routes"])
        result["independent_audit_passed"] = True
    output = json.dumps(safe(result), indent=2, allow_nan=False)+"\n"
    if a.output:
        if a.output.resolve() == a.input.resolve():
            ap.error("Output cannot overwrite the input")
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(output, encoding="utf-8")
    print(output)

