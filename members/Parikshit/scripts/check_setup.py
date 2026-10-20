"""Run from the project root:  python scripts/check_setup.py
Lists missing files, stale files (old versions), and stray junk."""
import os
import sys

# path -> text that must appear inside (None = just must exist)
EXPECTED = {
    "pyproject.toml": None,
    "src/qorbit/__init__.py": None,
    "src/qorbit/config.py": None,
    "src/qorbit/models/__init__.py": None,
    "src/qorbit/models/core.py": "coords",
    "src/qorbit/traffic/__init__.py": "corridor_event",
    "src/qorbit/traffic/traffic_model.py": "ramp: float = 1.0",
    "src/qorbit/traffic/zones.py": None,
    "src/qorbit/traffic/scenarios.py": None,
    "src/qorbit/cost/__init__.py": None,
    "src/qorbit/cost/objective.py": "def trace_route",
    "src/qorbit/data/__init__.py": None,
    "src/qorbit/data/synthetic.py": None,
    "src/qorbit/data/solomon.py": None,
    "src/qorbit/optimization/__init__.py": "build_initial",
    "src/qorbit/optimization/splice.py": None,
    "src/qorbit/optimization/qubo.py": None,
    "src/qorbit/optimization/qubo_decoder.py": None,
    "src/qorbit/optimization/simulated_annealing.py": None,
    "src/qorbit/optimization/local_solvers.py": None,
    "src/qorbit/optimization/repair.py": None,
    "src/qorbit/optimization/polish.py": "polish_windows",
    "src/qorbit/sim/__init__.py": None,
    "src/qorbit/sim/methods.py": "rebuild_polish",
    "experiments/run_dynamic.py": "polish_windows",
    "experiments/plot_recovery.py": None,
    "tests/test_qubo.py": None,
    "tests/test_repair.py": "polished_plan",
    "src/qorbit/validation/__init__.py": "check_instance",
    "src/qorbit/validation/instance_checks.py": None,
    "src/qorbit/optimization/initial.py": None,
    "src/qorbit/sim/metrics.py": None,
    "tests/test_metrics.py": None,
    "experiments/analyze_results.py": None,
    "experiments/run_sweeps.py": None,
    "experiments/inspect_json_case.py": None,
    "experiments/check_instance_file.py": None,
    "tests/test_validation_evaluator.py": None,
    "tests/test_validation_edge_cases.py": None,
    "src/qorbit/optimization/partition.py": None,
    "src/qorbit/optimization/scorer.py": None,
    "src/qorbit/optimization/greedy.py": "unassigned",
    "experiments/demo_greedy_traffic.py": "build_hard",
    "experiments/demo_partitions.py": None,
    "tests/test_partitions.py": None,
    "scripts/fetch_solomon.py": "raw.githubusercontent.com",
    "scripts/make_solomon_like.py": None,
    "tests/test_objective.py": "p.alpha * (1 + p.beta",
    "tests/test_greedy_and_loaders.py": None,
    "tests/data/mini_solomon.txt": None,
    "data/solomon/R101.txt": None,
    "data/solomon/C101.txt": None,
    "data/solomon/RC101.txt": None,
}
JUNK_NAMES = ("Zone.Identifier",)

problems = 0
for path, marker in EXPECTED.items():
    if not os.path.exists(path):
        print("MISSING", path); problems += 1
    elif os.path.getsize(path) == 0 and not path.endswith("__init__.py"):
        print("EMPTY  ", path, "(0 bytes; the content was never saved. Re-create or re-download it)"); problems += 1
    elif path.startswith("data/solomon/") and os.path.getsize(path) < 2000:
        print("TOOSMALL", path, f"({os.path.getsize(path)} bytes; a real Solomon file is several KB)"); problems += 1
    elif marker and marker not in open(path, errors="ignore").read():
        print("STALE  ", path, "(old version; replace it)"); problems += 1

for root, dirs, files in os.walk("."):
    if ".venv" in root or "__pycache__" in root or ".git" in root:
        continue
    for d in dirs:
        if "{" in d:
            print("JUNK   ", os.path.join(root, d), "(delete this folder)"); problems += 1
    for f in files:
        if f.startswith("test_") and f.endswith(".py") and not os.path.normpath(root).startswith("tests"):
            print("STRAY  ", os.path.join(root, f), "(test files belong in tests/; pytest breaks on duplicates)"); problems += 1
    for f in files:
        if any(j in f for j in JUNK_NAMES):
            print("JUNK   ", os.path.join(root, f), "(delete)"); problems += 1
    for f in files:
        if root.endswith("solomon") and f.lower() in {"r101.txt", "c101.txt", "rc101.txt"} and f not in {"R101.txt", "C101.txt", "RC101.txt"}:
            print("RENAME ", os.path.join(root, f), "-> exact capitals, e.g. RC101.txt"); problems += 1

print("\nAll good." if not problems else f"\n{problems} problem(s) found.")
sys.exit(1 if problems else 0)
