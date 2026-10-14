import unittest
from robot_b3.offline import OfflineSimulator
from robot_b3.q4_route_service_strategy import Q4RouteServiceStrategy


class RouteServiceTests(unittest.TestCase):
    def test_probe_selection_counts_onward_travel(self):
        strategy = Q4RouteServiceStrategy(OfflineSimulator({}))
        strategy.position = (0, 0)
        strategy._circle = lambda c: ((0, 0), 100)
        strategy._probe_queue = lambda c: [(-10, 0), (11, 0)]
        self.assertEqual(strategy._target_point(1), (-10, 0))
        self.assertEqual(strategy._target_point(1, (100, 0)), (11, 0))

    def test_scheduling_retains_all_certificate_tasks(self):
        strategy = Q4RouteServiceStrategy(OfflineSimulator({}))
        coverage = {('certificate', 0): (20, 0), ('certificate', 1): (40, 0)}
        tasks = dict(coverage)
        before = dict(coverage)
        selected = strategy._scheduled_key(list(reversed(tasks)), tasks, coverage)
        self.assertEqual(selected, ('certificate', 0))
        self.assertEqual(coverage, before)

    def test_empty_scene_executes_complete_21_station_certificate(self):
        sim = OfflineSimulator({})
        result = Q4RouteServiceStrategy(sim, route_budget_s=.01).run()
        self.assertTrue(result['discovery_complete'])
        self.assertEqual(result['unknown_channels'], [])
        self.assertEqual(len(result['absent_channels']), 20)
        self.assertEqual(sim.measures, 420)
        self.assertAlmostEqual(sim.moves_m, 17808.42897191402, places=5)


if __name__ == '__main__':
    unittest.main()
