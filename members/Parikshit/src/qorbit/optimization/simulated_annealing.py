"""Classical simulated annealing on a LocalQubo (no quantum anything)."""
from dataclasses import dataclass
import math
import numpy as np
from .qubo import LocalQubo


@dataclass(frozen=True)
class SAParams:
    sweeps: int = 100          # temperature steps per restart
    restarts: int = 4
    cool: float = 0.95         # geometric cooling per sweep
    p_accept0: float = 0.8     # start temperature: ~80% of worsening moves accepted


def _t0(deltas, p0):
    pos = [d for d in deltas if d > 1e-12]
    return -float(np.mean(pos)) / math.log(p0) if pos else 1e-3


def anneal_qubo(q: LocalQubo, rng: np.random.Generator, sa: SAParams, variant: str = "flip"):
    """variant 'flip': plain single-bit flips on the QUBO (can leave the valid-permutation space).
       variant 'swap': swap two slots (stays one-hot valid), still scored with the QUBO energy.
    Returns (best x, best energy, number of energy updates)."""
    n, k = q.n, q.k
    best_x, best_e, n_eval = None, math.inf, 0
    for _ in range(sa.restarts):
        if variant == "flip":
            x = (rng.random(n) < 1.0 / k).astype(float)
            field = q.diag + q.W @ x
            e = q.energy(x)
            T = _t0((1 - 2 * x) * field, sa.p_accept0)
            for _s in range(sa.sweeps):
                for a in rng.permutation(n):
                    d = (1 - 2 * x[a]) * field[a]
                    n_eval += 1
                    if d <= 0 or rng.random() < math.exp(-d / T):
                        x_old = x[a]
                        x[a] = 1 - x_old
                        field += q.W[:, a] * (x[a] - x_old)
                        e += d
                        if e < best_e - 1e-12:
                            best_e, best_x = e, x.copy()
                T *= sa.cool
        else:
            perm = rng.permutation(k)
            def to_x(pm):
                v = np.zeros(n)
                for p, i in enumerate(pm):
                    v[i * k + p] = 1.0
                return v
            x = to_x(perm)
            e = q.energy(x)
            probe = []
            for _ in range(20):
                a, b = rng.choice(k, 2, replace=False)
                c = perm.copy(); c[a], c[b] = c[b], c[a]
                probe.append(q.energy(to_x(c)) - e)
            T = _t0(probe, sa.p_accept0)
            if e < best_e - 1e-12:
                best_e, best_x = e, x.copy()
            for _s in range(sa.sweeps):
                for _m in range(k):
                    a, b = rng.choice(k, 2, replace=False)
                    c = perm.copy(); c[a], c[b] = c[b], c[a]
                    x2 = to_x(c); e2 = q.energy(x2); n_eval += 1
                    d = e2 - e
                    if d <= 0 or rng.random() < math.exp(-d / T):
                        perm, x, e = c, x2, e2
                        if e < best_e - 1e-12:
                            best_e, best_x = e, x.copy()
                T *= sa.cool
    return best_x, best_e, n_eval
