"""Per-run bounded route cache for an immutable offline problem.

Keys include the vehicle and the COMPLETE customer order. Changing a route
always recomputes its load, departure times and downstream traffic/windows.
Nothing is cached across changes to the problem or across solver runs.
"""
from collections import OrderedDict, Counter
import math


class CachedProblem:
    def __init__(self, problem, limit=4096):
        if limit < 1:
            raise ValueError("Cache limit must be positive")
        self.problem = problem
        self.limit = limit
        self.cache = OrderedDict()
        self.route_simulations = 0
        self.route_cache_hits = 0

    def __getattr__(self, name):
        return getattr(self.problem, name)

    def route(self, vi, route):
        key = vi, tuple(route)
        if key in self.cache:
            self.route_cache_hits += 1
            self.cache.move_to_end(key)
            return self.cache[key]
        self.route_simulations += 1
        detail = self.problem.route(vi, route)
        self.cache[key] = detail
        if len(self.cache) > self.limit:
            self.cache.popitem(last=False)
        return detail

    def evaluate(self, routes):
        counts = Counter(c for r in routes for c in r)
        issues = []
        if len(routes) != len(self.vehicles):
            issues.append("vehicle_count")
        if counts != Counter(self.ids):
            issues.append("customer_coverage")
        if set(counts)-set(self.ids) or len(routes) != len(self.vehicles):
            return dict(feasible=False, cost=math.inf, issues=issues, routes=[])
        details = [self.route(i, r) for i, r in enumerate(routes)]
        issues.extend(issue for d in details for issue in d["issues"])
        feasible = not issues
        return dict(feasible=feasible, cost=sum(d["cost"] for d in details) if feasible else math.inf,
                    issues=sorted(set(issues)), routes=details,
                    **{k: sum(d[k] for d in details) for k in
                       ("distance", "travel_minutes", "duration_minutes", "fuel_liters", "lateness_minutes")})
