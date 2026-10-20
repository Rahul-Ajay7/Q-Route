"""Validate one instance file BEFORE running any optimisation.
usage: python experiments/check_instance_file.py data/solomon/R101.txt [--soft]
Reports malformed data, provable infeasibility, and what the greedy initial solver does with it."""
import sys
import numpy as np
from qorbit.cost import Evaluator
from qorbit.data.solomon import load_solomon
from qorbit.optimization import build_initial
from qorbit.traffic import TrafficModel
from qorbit.validation import check_instance

args = [a for a in sys.argv[1:] if not a.startswith("--")]
soft = "--soft" in sys.argv
if not args:
    sys.exit(__doc__)
path = args[0]
if path.lower().endswith(".json"):
    sys.exit("JSON cases are not supported yet: send one example (e.g. TC01.json) and its schema so the "
             "adapter can map its fields and node IDs onto ProblemInstance.")
inst = load_solomon(path)
hard = not soft
n = len(inst.customers)
dem = [c.demand for c in inst.customers.values()]
width = [c.due - c.ready for c in inst.customers.values()]
print(f"{path}\n  customers {n}, vehicles {len(inst.vehicles)}, capacity {max(v.capacity for v in inst.vehicles.values()):g}, "
      f"total demand {sum(dem):g}, windows {'HARD' if hard else 'soft'}")
print(f"  tightest window {min(width) * 60:.0f} min, median {np.median(width) * 60:.0f} min")
issues = check_instance(inst, hard_tw=hard)
for lvl in ("error", "infeasible", "warning"):
    sel = [i for i in issues if i.level == lvl]
    print(f"  {lvl.upper():10} {len(sel)}")
    for i in sel[:5]:
        print(f"      [{i.code}] {i.message}")
    if len(sel) > 5:
        print(f"      ... and {len(sel) - 5} more")
rep = build_initial(inst, Evaluator(inst, TrafficModel(peak=1.0)), hard_tw=True if hard else False)
used = sum(1 for r in rep.solution.routes.values() if r)
print(f"\n  greedy initial solution: {rep.status.upper()}, vehicles used {used}, unassigned {len(rep.unassigned)}")
for c, why in list(rep.reasons.items())[:5]:
    print(f"      customer {c}: {why}")
if rep.status == "feasible":
    print(f"      cost Rs {rep.cost:,.0f}")
sys.exit(0 if rep.status == "feasible" else 1)
