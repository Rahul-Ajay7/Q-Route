"""All compared methods behind one interface: run_method(name, ctx) -> rows (list of dicts)."""
from dataclasses import dataclass
import time
import numpy as np
from ..cost import Evaluator
from ..models import ProblemInstance, Solution
from ..optimization import DirectSA, QuboSA, greedy_solve, polish, run_repair


@dataclass
class Context:
    inst: ProblemInstance
    sol0: Solution               # plan built before the event
    ev0: Evaluator               # traffic before the event
    ev1: Evaluator               # traffic after the event (ground truth for every method)
    rng: np.random.Generator
    hard_build: bool = False     # rebuild respects windows when it can (Solomon)
    k: int = 5
    max_solves: int = 40
    time_limit: float | None = None
    final: Solution | None = None     # plan produced by the method (set by run_method)


def _row(step, elapsed, cost, **kw):
    base = dict(step=step, elapsed_s=elapsed, cost=cost, accepted=0, vehicle=-1, score=0.0, n_vars=0, repaired=0)
    base.update(kw)
    return base


def do_nothing(c: Context):
    c.final = c.sol0
    return [_row(0, 0.0, c.ev1.evaluate(c.sol0).objective)]


def _rebuild(c: Context):
    return greedy_solve(c.inst, c.ev1, hard_tw="prefer" if c.hard_build else False)


def greedy_rebuild(c: Context):
    """Throw the plan away and rebuild under the new traffic (on-time insertion preferred when it exists)."""
    t = time.perf_counter()
    sol = _rebuild(c)
    c.final = sol
    return [_row(0, 0.0, c.ev1.evaluate(c.sol0).objective), _row(1, time.perf_counter() - t, c.ev1.evaluate(sol).objective)]


def rebuild_polish(c: Context):
    """Rebuild, then run the same intra-route polish the pre-event plan had: the fair 'recompute everything'."""
    t = time.perf_counter()
    sol = polish(_rebuild(c), c.ev1)
    c.final = sol
    return [_row(0, 0.0, c.ev1.evaluate(c.sol0).objective), _row(1, time.perf_counter() - t, c.ev1.evaluate(sol).objective)]


def _repair(solver, policy):
    def run(c: Context):
        cur, rows = run_repair(c.sol0, c.ev0, c.ev1, solver, c.rng, k=c.k, policy=policy,
                               max_solves=c.max_solves, time_limit=c.time_limit)
        c.final = cur
        return rows
    return run


METHODS = {
    "do_nothing": do_nothing,
    "greedy_rebuild": greedy_rebuild,
    "rebuild_polish": rebuild_polish,
    "direct_sa": _repair(DirectSA(), "score"),
    "qorbit_flip": _repair(QuboSA("flip"), "score"),
    "qorbit_swap": _repair(QuboSA("swap"), "score"),
    "qorbit_random": _repair(QuboSA("swap"), "random"),
}


def run_method(name: str, ctx: Context):
    return METHODS[name](ctx)
