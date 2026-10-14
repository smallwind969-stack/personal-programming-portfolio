import unittest

from robot_b3.geometry import seven_points
from robot_b3.offline import OfflineSimulator
from robot_b3.residual_strategy import ResidualStrategy


class ResidualStrategyTests(unittest.TestCase):
    def test_opportunistic_measurement_removes_one_channel_fallback(self):
        sim = OfflineSimulator({})
        strategy = ResidualStrategy(sim, route_budget_s=.01)
        strategy.unknown = {1}
        strategy.channel_stations = {1: [(0.0, 0.0)]}
        before = strategy.channel_completion(1)
        strategy.position = seven_points(1123.0)[1]

        measured = strategy.opportunistic_unknown_scan()
        after = strategy.channel_completion(1)

        self.assertEqual(measured, [1])
        self.assertEqual(len(before), 6)
        self.assertEqual(len(after), 5)
        self.assertEqual(sim.measures, 1)

    def test_empty_scene_finishes_with_certified_channel_histories(self):
        sim = OfflineSimulator({})
        strategy = ResidualStrategy(sim, route_budget_s=.01)
        result = strategy.run()
        self.assertTrue(result['discovery_complete'])
        self.assertEqual(result['cleared'], 0)
        self.assertEqual(result['certified_empty_channels'], 20)


if __name__ == '__main__':
    unittest.main()
