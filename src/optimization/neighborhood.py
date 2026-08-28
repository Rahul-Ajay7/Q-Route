"""
src/optimization/neighborhood.py

Local search neighborhood operators for CVRPTW solutions. A solution here
is represented as a list of routes, each route a plain list of node
indices (1..N, depot=0 implicit at start/end, NOT included in the list).

Operators:
- swap_within_route: swap two customers in the same route
- relocate_within_route: move a customer to a different position in same route
- two_opt_within_route: reverse a segment (classic 2-opt)
- relocate_between_routes: move a customer from one route to another
- swap_between_routes: swap customers between two different routes

random_neighbor() picks a random move type and applies it, returning a
new solution (deep-copied) -- used by SimulatedAnnealing each iteration.
"""

import copy
import random
from typing import List


class NeighborhoodOperators:

    def __init__(self, seed: int = None):
        self.rng = random.Random(seed)

    def swap_within_route(self, route: List[int], i: int, j: int) -> List[int]:
        new_route = route[:]
        new_route[i], new_route[j] = new_route[j], new_route[i]
        return new_route

    def relocate_within_route(self, route: List[int], i: int, j: int) -> List[int]:
        new_route = route[:]
        node = new_route.pop(i)
        new_route.insert(j, node)
        return new_route

    def two_opt_within_route(self, route: List[int], i: int, j: int) -> List[int]:
        if i > j:
            i, j = j, i
        new_route = route[:i] + route[i:j + 1][::-1] + route[j + 1:]
        return new_route

    def relocate_between_routes(self, routes: List[List[int]], r1: int, i: int,
                                 r2: int, j: int) -> List[List[int]]:
        new_routes = copy.deepcopy(routes)
        node = new_routes[r1].pop(i)
        new_routes[r2].insert(j, node)
        return new_routes

    def swap_between_routes(self, routes: List[List[int]], r1: int, i: int,
                             r2: int, j: int) -> List[List[int]]:
        new_routes = copy.deepcopy(routes)
        new_routes[r1][i], new_routes[r2][j] = new_routes[r2][j], new_routes[r1][i]
        return new_routes

    def random_neighbor(self, routes: List[List[int]]) -> List[List[int]]:
        """
        Applies one random move to a copy of routes. Automatically picks
        a move type that's structurally valid given current route lengths
        (e.g. won't attempt 2-opt on a route with <2 customers).
        Returns a NEW routes list -- original is untouched.
        """
        routes = copy.deepcopy(routes)
        non_empty = [idx for idx, r in enumerate(routes) if len(r) >= 1]
        multi = [idx for idx, r in enumerate(routes) if len(r) >= 2]

        possible_moves = []
        if multi:
            possible_moves += ["swap_within", "relocate_within", "two_opt_within"]
        if len(non_empty) >= 2:
            possible_moves += ["relocate_between", "swap_between"]

        if not possible_moves:
            return routes  # nothing to mutate (e.g. all routes empty/singleton)

        move = self.rng.choice(possible_moves)

        if move == "swap_within":
            r = self.rng.choice(multi)
            i, j = self.rng.sample(range(len(routes[r])), 2)
            routes[r] = self.swap_within_route(routes[r], i, j)

        elif move == "relocate_within":
            r = self.rng.choice(multi)
            i, j = self.rng.sample(range(len(routes[r])), 2)
            routes[r] = self.relocate_within_route(routes[r], i, j)

        elif move == "two_opt_within":
            r = self.rng.choice(multi)
            i, j = self.rng.sample(range(len(routes[r])), 2)
            routes[r] = self.two_opt_within_route(routes[r], i, j)

        elif move == "relocate_between":
            r1, r2 = self.rng.sample(non_empty, 2) if len(non_empty) >= 2 else (non_empty[0], non_empty[0])
            if len(routes[r1]) == 0:
                return routes
            i = self.rng.randrange(len(routes[r1]))
            j = self.rng.randrange(len(routes[r2]) + 1)
            routes = self.relocate_between_routes(routes, r1, i, r2, j)

        elif move == "swap_between":
            candidates = [idx for idx in non_empty if len(routes[idx]) >= 1]
            if len(candidates) < 2:
                return routes
            r1, r2 = self.rng.sample(candidates, 2)
            i = self.rng.randrange(len(routes[r1]))
            j = self.rng.randrange(len(routes[r2]))
            routes = self.swap_between_routes(routes, r1, i, r2, j)

        return routes
