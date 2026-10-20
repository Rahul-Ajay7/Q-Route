"""Exhaustive validation oracle for tiny single-depot instances only."""
import itertools
import math


def exact_small(problem):
    n, m = len(problem.ids), len(problem.vehicles)
    if n > 7 or m > 3:
        raise ValueError("Exact oracle limited to <=7 customers and <=3 vehicles")
    best, best_cost = None, math.inf
    for order in itertools.permutations(problem.ids):
        for cuts in itertools.combinations_with_replacement(range(n+1), m-1):
            ends = (0,) + cuts + (n,)
            routes = [list(order[ends[i]:ends[i+1]]) for i in range(m)]
            score = problem.evaluate(routes)
            if score["feasible"] and score["cost"] < best_cost:
                best, best_cost = routes, score["cost"]
    return dict(routes=best, cost=best_cost, proven_optimal=best is not None,
                proven_infeasible=best is None)
