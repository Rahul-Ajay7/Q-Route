import numpy as np
from scipy.optimize import linear_sum_assignment
from .qubo import LocalQubo


def decode(x: np.ndarray, q: LocalQubo) -> tuple[tuple, bool]:
    """Binary vector -> ordering of customer ids. Returns (order, repaired).
    If x is not a permutation matrix it is repaired by Hungarian assignment (max overlap with x)."""
    k = q.k
    X = np.round(x).reshape(k, k)                       # rows = customers, cols = slots
    if (X.sum(axis=0) == 1).all() and (X.sum(axis=1) == 1).all():
        return tuple(q.customers[int(X[:, p].argmax())] for p in range(k)), False
    rows, cols = linear_sum_assignment(-X)
    order = [None] * k
    for r, c in zip(rows, cols):
        order[c] = q.customers[r]
    return tuple(order), True
