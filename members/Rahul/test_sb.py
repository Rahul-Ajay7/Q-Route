"""Mathematical and routing checks, independent of benchmark outcomes."""
import copy
import itertools
import unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np
import run_sb as sb


class SolverTests(unittest.TestCase):
    def setUp(self):
        self.data = sb.load_case((sb.CASES / "TC03.json"))

    def test_weighted_qubo_matches_full_route_and_fuel_model(self):
        data = self.data
        data["_objective"] = "weighted"
        data["_weights"] = {"distance": .4, "travel_time": .4, "fuel": .2}
        data["_fuel_model"] = {"km_per_unit": 2., "liters_per_100km": 8.,
                               "price_per_liter": 90., "currency": "INR"}
        block = [c["id"] for c in data["customers"][:3]]
        depot = data["depot"]["id"]
        q, offset = sb.route_qubo(data, block, depot, depot, 0)
        for order in itertools.permutations(range(3)):
            bits = np.zeros((3, 3))
            for position, customer in enumerate(order):
                bits[customer, position] = 1
            detail = sb.evaluate_route(data, data["vehicles"][0], [block[i] for i in order])
            self.assertAlmostEqual(bits.reshape(-1) @ q @ bits.reshape(-1) + offset, detail["cost"])
            self.assertAlmostEqual(detail["estimated_fuel_cost"], detail["distance"] * 2 * .08 * 90)
            self.assertAlmostEqual(detail["cost"], .4 * detail["distance"] + .4 * detail["travel_minutes"] + .2 * detail["estimated_fuel_cost"])

    def test_traffic_changes_time_but_not_distance_or_constant_fuel(self):
        route = [c["id"] for c in self.data["customers"]]
        before = sb.evaluate_route(self.data, self.data["vehicles"][0], route)
        self.data["traffic_events"] = [{"from": self.data["depot"]["id"], "to": route[0],
                                       "time": 0, "end_time": 10000, "multiplier": 2}]
        after = sb.evaluate_route(self.data, self.data["vehicles"][0], route)
        self.assertGreater(after["travel_minutes"], before["travel_minutes"])
        self.assertEqual(after["distance"], before["distance"])
        self.assertEqual(after["estimated_fuel_cost"], before["estimated_fuel_cost"])
        empty = sb.evaluate_route(self.data, self.data["vehicles"][0], [])
        self.assertEqual(empty["estimated_fuel_cost"], 0)

    def test_qubo_equals_route_cost_for_every_three_customer_permutation(self):
        block = [c["id"] for c in self.data["customers"][:3]]
        depot = self.data["depot"]["id"]
        q, offset = sb.route_qubo(self.data, block, depot, depot, 0)
        for order in itertools.permutations(range(3)):
            bits = np.zeros((3, 3))
            for position, customer in enumerate(order):
                bits[customer, position] = 1
            flat = bits.reshape(-1)
            route = [block[i] for i in order]
            cost = sb.evaluate_route(self.data, self.data["vehicles"][0], route)["cost"]
            self.assertAlmostEqual(flat @ q @ flat + offset, cost)

    def test_assignment_penalty_excludes_invalid_global_minima(self):
        block = [c["id"] for c in self.data["customers"][:2]]
        depot = self.data["depot"]["id"]
        q, offset = sb.route_qubo(self.data, block, depot, depot, 0)
        valid, invalid = [], []
        for binary in itertools.product((0, 1), repeat=4):
            bits = np.array(binary)
            (valid if sb.decode(bits, 2) is not None else invalid).append(
                bits @ q @ bits + offset)
        self.assertLess(min(valid), min(invalid))

    def test_ising_and_auxiliary_spin_match_all_binary_energies(self):
        q = np.array([[2., -1., 3.], [-1., 4., 0.5], [3., 0.5, -2.]])
        k, h, constant = sb.qubo_to_ising(q)
        for binary in itertools.product((0, 1), repeat=3):
            bits = np.array(binary)
            spins = 2 * bits - 1
            original = bits @ q @ bits
            self.assertAlmostEqual(original, constant + h @ spins + 0.5 * spins @ k @ spins)
            j = np.zeros((4, 4))
            j[:3, :3], j[:3, 3], j[3, :3] = -k, -h, -h
            for auxiliary in (-1, 1):
                z = np.append(spins * auxiliary, auxiliary)
                self.assertAlmostEqual(original, constant - 0.5 * z @ j @ z)

    def test_projection_maximizes_assignment_scores(self):
        scores = np.array([[1., 8., 4.], [5., 2., 9.], [7., 6., 3.]])
        order = sb.project(scores, 3)
        value = sum(scores[i, p] for p, i in enumerate(order))
        optimum = max(sum(scores[i, p] for p, i in enumerate(perm))
                      for perm in itertools.permutations(range(3)))
        self.assertEqual(value, optimum)
        self.assertEqual(len(set(order)), 3)
        self.assertIsNone(sb.decode(np.zeros(9), 3))

    def test_traffic_direction_expiry_and_closure(self):
        data = copy.deepcopy(self.data)
        data["traffic_events"] = [
            {"time": 10, "end_time": 20, "from": 1, "to": 2, "multiplier": 2},
            {"time": 30, "from": 1, "to": 2, "multiplier": None}]
        base = sb.travel(data, 1, 2, 0)
        self.assertEqual(sb.travel(data, 1, 2, 10), base * 2)
        self.assertEqual(sb.travel(data, 1, 2, 20), base)
        self.assertEqual(sb.travel(data, 2, 1, 10), sb.travel(data, 2, 1, 0))
        self.assertTrue(np.isinf(sb.travel(data, 1, 2, 30)))

    def test_release_time_waiting_and_service_start_window(self):
        data = copy.deepcopy(self.data)
        customer = data["customers"][0]["id"]
        data["_nodes"][customer].update(ready_time=50, due_time=50, service_time=5)
        result = sb.evaluate_route(data, data["vehicles"][0], [customer])
        self.assertTrue(result["feasible"])
        self.assertEqual(result["starts"], [50])
        data["_nodes"][customer]["release_time"] = 51
        self.assertFalse(sb.evaluate_route(data, data["vehicles"][0], [customer])["feasible"])

    def test_partial_and_duplicate_routes_are_not_feasible(self):
        routes = sb.greedy(self.data)
        self.assertTrue(sb.evaluate_solution(self.data, routes)["feasible"])
        partial = [r[:-1] for r in routes]
        self.assertFalse(sb.evaluate_solution(self.data, partial)["feasible"])
        duplicate = [r + r[:1] for r in routes]
        self.assertFalse(sb.evaluate_solution(self.data, duplicate)["feasible"])

    def test_expected_infeasible_inputs_and_colocated_ids(self):
        for name in ("TC15.json", "TC16.json", "TC25.json"):
            data = sb.load_case((sb.CASES / name))
            result = sb.evaluate_solution(data, sb.greedy(data))
            self.assertFalse(result["feasible"], name)
            self.assertTrue(result["unserved"], name)
        data = sb.load_case((sb.CASES / "TC10.json"))
        result = sb.evaluate_solution(data, sb.greedy(data))
        self.assertTrue(result["feasible"])
        self.assertFalse(result["unserved"])

    def test_sb_and_sa_repeatable_and_preserve_feasible_routes(self):
        baseline = sb.greedy(self.data)
        models = sb.prepare_models(self.data, baseline, 3)
        initial = sb.evaluate_solution(self.data, baseline)
        for method in ("SB", "SA"):
            routes, stats = sb.optimize(self.data, baseline, models, method, 4, 30, 123)
            repeated, repeated_stats = sb.optimize(
                self.data, baseline, models, method, 4, 30, 123)
            result = sb.evaluate_solution(self.data, routes)
            self.assertEqual(routes, repeated)
            self.assertEqual(stats, repeated_stats)
            self.assertTrue(result["feasible"])
            self.assertLessEqual(result["cost"], initial["cost"])
            self.assertEqual(stats["raw_valid_samples"] + stats["projected_samples"],
                             len(models) * 4)

    def test_paths_cannot_escape_folder(self):
        with self.assertRaises(ValueError):
            sb.local_path("../outside.csv")

    def test_overlapping_windows_cover_original_boundaries_and_tail(self):
        starts = sb.block_starts(11, 5, 2)
        self.assertEqual(starts, [0, 2, 4, 6])
        self.assertTrue(any(start <= 4 and start + 5 > 5 for start in starts))
        self.assertEqual(sb.block_starts(1, 5, 2), [])
        self.assertEqual(sb.block_starts(3, 5, 2), [0])

    def test_adaptive_search_preserves_ids_feasibility_and_reference_quality(self):
        data = sb.load_case((sb.CASES / "TC11.json"))
        baseline = sb.greedy(data)
        models = sb.prepare_models(data, baseline, 5)
        for method in ("SB", "SA"):
            options = dict(chunk_size=5, stride=2, passes=2, restarts=2)
            routes, stats = sb.optimize(data, baseline, models, method, 4, 30, 123, **options)
            again, again_stats = sb.optimize(data, baseline, models, method, 4, 30, 123, **options)
            self.assertEqual(routes, again)
            self.assertEqual(stats, again_stats)
            for old, new in zip(baseline, routes):
                self.assertCountEqual(old, new)
            result = sb.evaluate_solution(data, routes)
            self.assertTrue(result["feasible"])
            self.assertLessEqual(result["cost"], stats["reference_travel_minutes"] + 1e-9)
            self.assertEqual(stats["raw_valid_samples"] + stats["projected_samples"],
                             stats["solver_calls"] * 4)

    def test_rebuilt_model_uses_changed_order_boundary_and_departure(self):
        data = copy.deepcopy(self.data)
        route = [c["id"] for c in data["customers"]]
        route[0], route[1] = route[1], route[0]
        detail = sb.evaluate_route(data, data["vehicles"][0], route)
        with patch.object(sb, 'route_qubo', wraps=sb.route_qubo) as builder:
            model = sb.build_model(data, route, 0, 2, 3)
        args = builder.call_args.args
        self.assertEqual(model[2], route[2:5])
        self.assertEqual(args[2], route[1])
        self.assertEqual(args[4], detail['starts'][1] + data['_nodes'][route[1]]['service_time'])

    def test_parameter_bounds_and_penalty_energy(self):
        block = [c['id'] for c in self.data['customers'][:2]]
        depot = self.data['depot']['id']
        q, offset = sb.route_qubo(self.data, block, depot, depot, 0, 2.0)
        bits = np.eye(2).reshape(-1)
        expected = sb.evaluate_route(self.data, self.data['vehicles'][0], block)['cost']
        self.assertAlmostEqual(bits @ q @ bits + offset, expected)
        with self.assertRaises(ValueError):
            sb.route_qubo(self.data, block, depot, depot, 0, 0.5)
        for dt, coupling in [(0, 1), (float('nan'), 1), (.2, 3)]:
            with self.assertRaises(ValueError):
                sb.solve_sb(q, 2, 10, np.random.default_rng(1), bits, dt, coupling)


if __name__ == "__main__":
    unittest.main()
