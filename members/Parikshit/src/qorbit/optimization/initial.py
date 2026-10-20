"""Initial-solution entry point that REPORTS infeasibility instead of raising or silently dropping customers."""
from dataclasses import dataclass, field
import math
from ..cost import Evaluator
from ..models import ProblemInstance, Solution
from ..validation import Issue, check_instance, errors_of
from .greedy import greedy_solve


@dataclass
class SolveReport:
    status: str                  # "feasible" | "infeasible" | "invalid_instance"
    solution: Solution
    unassigned: list = field(default_factory=list)
    issues: list = field(default_factory=list)
    reasons: dict = field(default_factory=dict)      # unassigned customer -> why
    cost: float = math.inf       # total cost of a feasible plan, else inf
    partial_cost: float = math.nan   # cost of what was built (informational only)


def build_initial(inst: ProblemInstance, ev: Evaluator, hard_tw=False) -> SolveReport:
    issues = check_instance(inst, hard_tw=(hard_tw is True))
    empty = Solution({v: [] for v in inst.vehicles})
    if errors_of(issues):
        return SolveReport("invalid_instance", empty, sorted(inst.customers), issues,
                           {c: "instance data is malformed" for c in inst.customers})
    unassigned: list = []
    sol = greedy_solve(inst, ev, hard_tw=hard_tw, unassigned=unassigned)
    visited = sol.visited()
    # internal invariants: every customer is either routed exactly once or reported, never lost
    assert len(visited) == len(set(visited)), "greedy visited a customer twice"
    assert not (set(visited) & set(unassigned)), "customer both routed and unassigned"
    assert set(visited) | set(unassigned) == set(inst.customers), "customer silently dropped"

    max_cap = max((v.capacity for v in inst.vehicles.values()), default=0)
    reasons = {}
    for c in unassigned:
        if inst.customers[c].demand > max_cap:
            reasons[c] = f"demand {inst.customers[c].demand} exceeds every vehicle capacity ({max_cap})"
        else:
            reasons[c] = "no vehicle can take it without breaking capacity or (hard) time windows"
    res = ev.evaluate(sol)                      # reports unassigned customers as 'not visited' violations
    if unassigned:
        return SolveReport("infeasible", sol, sorted(unassigned), issues, reasons, math.inf, res.total_cost)
    status = "feasible" if res.feasible else "infeasible"
    return SolveReport(status, sol, [], issues, {}, res.objective, res.total_cost)
