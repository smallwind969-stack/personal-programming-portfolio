import math
import unittest


class ExactOpenRouteTests(unittest.TestCase):
    def test_milp_finds_exact_open_route_on_small_instance(self):
        from robot_b3.q4_oracle import exact_open_route_milp

        points = {
            "a": (1.0, 0.0),
            "b": (2.0, 0.0),
            "c": (2.0, 1.0),
        }
        result = exact_open_route_milp((0.0, 0.0), points, time_limit_s=5.0)

        self.assertEqual(set(result.order), set(points))
        self.assertAlmostEqual(result.distance_m, 3.0, places=7)
        self.assertLessEqual(result.lower_bound_m, result.distance_m + 1e-7)
        self.assertLess(result.relative_gap, 1e-7)
        self.assertTrue(result.proven_optimal)


class OracleRegretTests(unittest.TestCase):
    def test_omniscient_clear_oracle_uses_true_open_route_and_one_clear_each(self):
        from robot_b3.q4_oracle import omniscient_clear_oracle

        sources = {
            1: ((3.0, 0.0), 1000.0),
            7: ((3.0, 4.0), 1400.0, 90.0),
        }
        result = omniscient_clear_oracle(sources, time_limit_s=5.0)

        self.assertAlmostEqual(result.move_distance_m, 7.0)
        self.assertAlmostEqual(result.move_s, 1.4)
        self.assertAlmostEqual(result.clear_s, 10.0)
        self.assertAlmostEqual(result.total_lower_bound_s, 11.4)
        self.assertTrue(result.route.proven_optimal)

    def test_regret_components_reconstruct_total_time(self):
        from robot_b3.q4_oracle import OracleClearResult, ExactRouteResult
        from robot_b3.q4_oracle import decompose_oracle_regret

        route = ExactRouteResult((1,), 100.0, 100.0, 0.0, True, "ok")
        oracle = OracleClearResult(route, 100.0, 20.0, 10.0, 30.0)
        actual = {
            "move_s": 50.0,
            "measure_s": 40.0,
            "switch_s": 6.0,
            "clear_s": 16.0,
            "total_s": 112.0,
        }
        result = decompose_oracle_regret(actual, oracle)

        self.assertEqual(result["excess_move_s"], 30.0)
        self.assertEqual(result["measurement_regret_s"], 40.0)
        self.assertEqual(result["switch_regret_s"], 6.0)
        self.assertEqual(result["clear_regret_s"], 6.0)
        self.assertEqual(result["total_regret_s"], 82.0)
        self.assertAlmostEqual(
            oracle.total_lower_bound_s + result["total_regret_s"],
            actual["total_s"],
        )

    def test_offline_metrics_split_search_from_post_discovery_localization(self):
        from robot_b3.offline import OfflineSimulator

        sim = OfflineSimulator({1: ((500.0, 0.0), 1000.0)}, error_mode='zero')
        sim.measure((0.0, 0.0), 2)
        sim.measure((0.0, 0.0), 1)
        sim.measure((100.0, 0.0), 1)
        costs = sim.cost_breakdown()

        self.assertEqual(costs['search_measures'], 2)
        self.assertEqual(costs['localization_measures'], 1)
        self.assertEqual(costs['no_signal_measures'], 1)
        self.assertEqual(costs['direction_measures'], 2)

    def test_empty_route_is_zero_and_optimal(self):
        from robot_b3.q4_oracle import exact_open_route_milp

        result = exact_open_route_milp((0.0, 0.0), {}, time_limit_s=1.0)
        self.assertEqual(result.order, ())
        self.assertEqual(result.distance_m, 0.0)
        self.assertEqual(result.lower_bound_m, 0.0)
        self.assertTrue(result.proven_optimal)


if __name__ == "__main__":
    unittest.main()
