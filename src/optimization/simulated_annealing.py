"""
src/optimization/simulated_annealing.py

Simulated Annealing metaheuristic for CVRPTW. Takes a starting solution
(e.g. from GreedySolver) and improves it via random neighborhood moves,
accepting worse solutions probabilistically (classic SA) to escape local
optima. Uses soft penalties for capacity/time-window/overtime violations
so SA can explore through infeasible territory rather than getting stuck.

Solution format used internally: list of routes, each route a plain list
of node indices (1..N), depot=0 implicit. Convert to/from GreedySolver's
richer dict format at the boundary (see routes_from_greedy / to_greedy_format).
"""

import math
import random
import copy
from typing import Dict, List, Tuple

from src.cost.distance_cost import DistanceCost
from src.cost.late_penalty import LatePenalty
from src.cost.operating_cost import OperatingCost
from src.constraints.capacity import CapacityConstraint
from src.constraints.vehicle_availability import VehicleAvailabilityConstraint
from src.optimization.neighborhood import NeighborhoodOperators


class SolutionEvaluator:
    """Simulates a fixed route order and computes total weighted cost,
    including soft penalties for constraint violations."""

    def __init__(self, instance: Dict, distance_km_matrix: List[List[float]],
                 travel_time_s_matrix: List[List[float]],
                 weights: Dict[str, float] = None):
        self.instance = instance
        self.distance_km_matrix = distance_km_matrix
        self.travel_time_s_matrix = travel_time_s_matrix
        self.customers = instance["customers"]
        self.idx_to_customer = {i + 1: c for i, c in enumerate(self.customers)}

        default_weights = {
            "distance": 1.0,
            "late_penalty": 2.0,
            "operating": 1.0,
            "capacity_violation": 50.0,
            "overtime_violation": 20.0,
            "unrouted_penalty": 500.0,
        }
        self.weights = {**default_weights, **(weights or {})}

        self.distance_cost = DistanceCost()
        self.late_penalty = LatePenalty()
        self.operating_cost = OperatingCost()
        self.capacity = CapacityConstraint()
        self.availability = VehicleAvailabilityConstraint()

    def simulate_route(self, vehicle: Dict, node_sequence: List[int]) -> Dict:
        """Forward-simulate a fixed customer order for one vehicle.
        Returns timing/load info needed for cost + feasibility checks."""
        shift_start, shift_end = vehicle["shift_window"]
        current_node = 0
        current_time = shift_start
        load = 0.0
        arrival_times = []
        due_times = []
        distance_km = 0.0

        for node_idx in node_sequence:
            customer = self.idx_to_customer[node_idx]
            travel_min = self.travel_time_s_matrix[current_node][node_idx] / 60.0
            distance_km += self.distance_km_matrix[current_node][node_idx]
            raw_arrival = current_time + travel_min
            arrival = max(raw_arrival, customer["ready_time"])
            arrival_times.append(arrival)
            due_times.append(customer["due_time"])
            current_time = arrival + customer["service_time"]
            load += customer["demand"]
            current_node = node_idx

        # return to depot
        return_min = self.travel_time_s_matrix[current_node][0] / 60.0
        distance_km += self.distance_km_matrix[current_node][0]
        route_end = current_time + return_min

        return {
            "arrival_times_min": arrival_times,
            "due_times_min": due_times,
            "load": load,
            "route_end_min": route_end,
            "distance_km": distance_km,
        }

    def route_cost(self, vehicle: Dict, node_sequence: List[int]) -> float:
        if not node_sequence:
            return 0.0
        sim = self.simulate_route(vehicle, node_sequence)

        c_distance = self.distance_cost.cost(sim["distance_km"])
        c_late = self.late_penalty.route_penalty(sim["arrival_times_min"], sim["due_times_min"])
        route_duration_hours = (sim["route_end_min"] - vehicle["shift_window"][0]) / 60.0
        c_operating = self.operating_cost.vehicle_cost(route_duration_hours)

        demands = [self.idx_to_customer[n]["demand"] for n in node_sequence]
        c_capacity_violation = self.capacity.violation_amount(demands, vehicle["capacity"])
        c_overtime = self.availability.overtime_amount(sim["route_end_min"], vehicle["shift_window"])

        total = (self.weights["distance"] * c_distance
                 + self.weights["late_penalty"] * c_late
                 + self.weights["operating"] * c_operating
                 + self.weights["capacity_violation"] * c_capacity_violation
                 + self.weights["overtime_violation"] * c_overtime)
        return total

    def solution_cost(self, routes: List[List[int]]) -> float:
        vehicles = self.instance["vehicles"]
        total = 0.0
        routed_ids = set()
        for vehicle, node_seq in zip(vehicles, routes):
            total += self.route_cost(vehicle, node_seq)
            routed_ids.update(node_seq)

        all_ids = set(self.idx_to_customer.keys())
        num_unrouted = len(all_ids - routed_ids)
        total += num_unrouted * self.weights["unrouted_penalty"]
        return total


class SimulatedAnnealing:

    def __init__(self, evaluator: SolutionEvaluator,
                 initial_temp: float = 1000.0, cooling_rate: float = 0.995,
                 min_temp: float = 1.0, max_iterations: int = 5000,
                 seed: int = None):
        self.evaluator = evaluator
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.min_temp = min_temp
        self.max_iterations = max_iterations
        self.ops = NeighborhoodOperators(seed=seed)
        self.rng = random.Random(seed)

    def solve(self, initial_routes: List[List[int]]) -> Dict:
        """
        initial_routes: list of node-index lists, one per vehicle (from
        GreedySolver output, converted via routes_from_greedy()).

        Returns dict: {best_routes, best_cost, cost_history}
        """
        current_routes = copy.deepcopy(initial_routes)
        current_cost = self.evaluator.solution_cost(current_routes)

        best_routes = copy.deepcopy(current_routes)
        best_cost = current_cost

        temp = self.initial_temp
        cost_history = [current_cost]

        iteration = 0
        while temp > self.min_temp and iteration < self.max_iterations:
            candidate_routes = self.ops.random_neighbor(current_routes)
            candidate_cost = self.evaluator.solution_cost(candidate_routes)

            delta = candidate_cost - current_cost
            if delta < 0 or self.rng.random() < math.exp(-delta / temp):
                current_routes = candidate_routes
                current_cost = candidate_cost

                if current_cost < best_cost:
                    best_routes = copy.deepcopy(current_routes)
                    best_cost = current_cost

            cost_history.append(current_cost)
            temp *= self.cooling_rate
            iteration += 1

        return {
            "best_routes": best_routes,
            "best_cost": best_cost,
            "cost_history": cost_history,
            "iterations_run": iteration,
        }


def routes_from_greedy(greedy_solution: Dict, num_vehicles: int) -> List[List[int]]:
    """
    Converts GreedySolver output (list of route dicts, one per USED vehicle)
    into a fixed-length list of node-index lists, one per vehicle slot
    (empty list if that vehicle was unused by greedy).
    """
    routes = [[] for _ in range(num_vehicles)]
    for i, route in enumerate(greedy_solution["routes"]):
        if i < num_vehicles:
            routes[i] = route["node_indices"][:]
    return routes
