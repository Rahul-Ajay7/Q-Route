"""
src/optimization/greedy.py

Greedy construction heuristic for CVRPTW: nearest-feasible-neighbor
insertion. For each vehicle, repeatedly picks the closest unassigned
customer that doesn't violate capacity or time window, until no
feasible customer remains, then moves to the next vehicle.

Operates on plain-dict instances (as produced by SyntheticGenerator /
CVRPLibLoader) and a travel-time matrix (as produced by Preprocessor).
Node indexing convention: 0 = depot, 1..N = customers in instance["customers"]
order -- matches Preprocessor._all_coords().

This is a fast, greedy baseline -- NOT optimal. Feeds into SimulatedAnnealing
as the initial solution to improve.
"""

from typing import Dict, List
from src.constraints.feasibility import FeasibilityChecker


class GreedySolver:

    def __init__(self):
        self.feasibility = FeasibilityChecker()

    def solve(self, instance: Dict, travel_time_s: List[List[float]]) -> Dict:
        """
        instance: plain-dict from SyntheticGenerator/CVRPLibLoader.
        travel_time_s: NxN matrix (seconds) from Preprocessor, node 0=depot.

        Returns dict:
        {
            "routes": [
                {
                    "vehicle_id": int,
                    "customer_ids": [ids in visit order],
                    "node_indices": [1-based indices into travel_time_s],
                    "arrival_times_min": [...],
                    "departure_times_min": [...],
                    "load": float,
                    "route_start_min": float,
                    "route_end_min": float,
                },
                ...
            ],
            "unrouted_customer_ids": [ids that couldn't be placed -- means
                                       construction failed; not an infeasibility proof],
        }
        """
        customers = instance["customers"]
        vehicles = instance["vehicles"]
        n = len(customers)

        # index maps: node_index (1..n) <-> customer dict
        idx_to_customer = {i + 1: c for i, c in enumerate(customers)}
        unassigned = set(idx_to_customer.keys())

        routes = []

        for vehicle_index, vehicle in enumerate(vehicles):
            if not unassigned:
                break

            capacity = vehicle["capacity"]
            shift_start, shift_end = vehicle["shift_window"]

            route_nodes = []
            arrival_times = []
            departure_times = []
            current_node = 0  # depot
            current_time = shift_start
            load = 0.0

            while True:
                best_next = None
                best_dist = float("inf")

                for node_idx in unassigned:
                    customer = idx_to_customer[node_idx]
                    demand = customer["demand"]

                    if load + demand > capacity:
                        continue

                    travel_s = travel_time_s[current_node][node_idx]
                    travel_min = travel_s / 60.0
                    raw_arrival = current_time + travel_min
                    arrival = max(raw_arrival, customer["ready_time"])

                    if arrival > customer["due_time"]:
                        continue  # would be late, skip

                    service_end = arrival + customer["service_time"]
                    return_travel_min = travel_time_s[node_idx][0] / 60.0
                    if service_end + return_travel_min > shift_end:
                        continue  # can't get back to depot in time

                    if travel_s < best_dist:
                        best_dist = travel_s
                        best_next = node_idx
                        best_arrival = arrival
                        best_departure = service_end

                if best_next is None:
                    break  # no feasible customer left for this vehicle

                route_nodes.append(best_next)
                arrival_times.append(round(best_arrival, 2))
                departure_times.append(round(best_departure, 2))
                load += idx_to_customer[best_next]["demand"]
                current_node = best_next
                current_time = best_departure
                unassigned.remove(best_next)

            if route_nodes:
                return_travel_min = travel_time_s[current_node][0] / 60.0
                route_end = current_time + return_travel_min
                routes.append({
                    "vehicle_id": vehicle["id"],
                    "vehicle_index": vehicle_index,
                    "customer_ids": [idx_to_customer[i]["id"] for i in route_nodes],
                    "node_indices": route_nodes,
                    "arrival_times_min": arrival_times,
                    "departure_times_min": departure_times,
                    "load": load,
                    "route_start_min": shift_start,
                    "route_end_min": round(route_end, 2),
                })

        unrouted_ids = [idx_to_customer[i]["id"] for i in unassigned]

        return {
            "routes": routes,
            "unrouted_customer_ids": unrouted_ids,
        }
