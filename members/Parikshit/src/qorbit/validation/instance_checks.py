"""Instance validation: (1) is the data well-formed? (2) can a feasible solution exist at all?

Issue levels
  error       data is malformed (wrong matrix size, NaN, negative demand, ready > due, bad ids ...)
  infeasible  data is fine but NO solution can exist (demand > every vehicle, total demand > fleet capacity,
              window unreachable under hard windows, ...)
  warning     suspicious but allowed (asymmetric matrix, window unreachable when windows are soft)
Free-flow travel is used for the reachability screens, so they are best-case: passing them does not prove
feasibility, failing them proves infeasibility."""
from dataclasses import dataclass
import numpy as np
from ..models import ProblemInstance


@dataclass(frozen=True)
class Issue:
    level: str
    code: str
    message: str


def errors_of(issues):
    return [i for i in issues if i.level == "error"]


def check_instance(inst: ProblemInstance, hard_tw: bool = False) -> list[Issue]:
    out: list[Issue] = []
    add = lambda lvl, code, msg: out.append(Issue(lvl, code, msg))
    n = len(inst.customers)

    # ---- ids ----
    ids = sorted(inst.customers)
    if ids != list(range(1, n + 1)):
        add("error", "customer_ids", f"customer ids must be exactly 1..{n} (0 is the depot); got {ids[:5]}...")
    for key, cu in inst.customers.items():
        if key != cu.id:
            add("error", "id_mismatch", f"customer stored under key {key} has id {cu.id}")

    # ---- matrices ----
    for name, M in (("dist_km", inst.dist_km), ("time_h", inst.time_h)):
        M = np.asarray(M, dtype=float)
        if M.shape != (n + 1, n + 1):
            add("error", f"{name}_shape", f"{name} has shape {M.shape}, expected {(n + 1, n + 1)}")
            continue
        if not np.isfinite(M).all():
            add("error", f"{name}_nan", f"{name} contains NaN or infinite values")
            continue
        if (M < 0).any():
            add("error", f"{name}_negative", f"{name} contains negative entries")
            continue
        if np.abs(np.diag(M)).max() > 1e-9:
            add("warning", f"{name}_diag", f"{name} has non-zero diagonal entries")
        if not np.allclose(M, M.T, atol=1e-6):
            add("warning", f"{name}_asymmetric", f"{name} is asymmetric (allowed; one-way roads)")
    if len(inst.zones) != n + 1:
        add("error", "zones_length", f"zones has length {len(inst.zones)}, expected {n + 1}")

    # ---- customers ----
    for cu in inst.customers.values():
        if cu.demand < 0:
            add("error", "demand_negative", f"customer {cu.id}: negative demand {cu.demand}")
        if cu.service < 0:
            add("error", "service_negative", f"customer {cu.id}: negative service time")
        if cu.ready > cu.due:
            add("error", "window_inverted", f"customer {cu.id}: ready {cu.ready} > due {cu.due}")

    # ---- vehicles ----
    for v in inst.vehicles.values():
        if v.capacity <= 0:
            add("error", "capacity_nonpositive", f"vehicle {v.id}: capacity {v.capacity} must be > 0")
    if n > 0 and not inst.vehicles:
        add("infeasible", "no_vehicles", f"{n} customers but no vehicles")

    if errors_of(out) or n == 0 or not inst.vehicles:
        return out

    # ---- can a solution exist? (best-case screens) ----
    max_cap = max(v.capacity for v in inst.vehicles.values())
    total_cap = sum(v.capacity for v in inst.vehicles.values())
    total_dem = sum(c.demand for c in inst.customers.values())
    for cu in inst.customers.values():
        if cu.demand > max_cap:
            add("infeasible", "demand_exceeds_capacity",
                f"customer {cu.id}: demand {cu.demand} exceeds the largest vehicle capacity {max_cap}")
    if total_dem > total_cap + 1e-9:
        add("infeasible", "fleet_capacity", f"total demand {total_dem} exceeds total fleet capacity {total_cap}")

    t_start = min(v.start_time for v in inst.vehicles.values())
    lvl = "infeasible" if hard_tw else "warning"
    suffix = "under hard time windows" if hard_tw else "(soft windows: it will be served late)"
    for cu in inst.customers.values():
        arrive = t_start + inst.time_h[0, cu.id]
        if arrive > cu.due + 1e-9:
            add(lvl, "window_unreachable",
                f"customer {cu.id}: earliest arrival {arrive:.3f} h is after due {cu.due:.3f} h {suffix}")
            continue
        back = max(arrive, cu.ready) + cu.service + inst.time_h[cu.id, 0]
        if back > inst.depot_due + 1e-9:
            add(lvl, "depot_deadline",
                f"customer {cu.id}: earliest return {back:.3f} h is after depot closing {inst.depot_due:.3f} h {suffix}")
    return out
