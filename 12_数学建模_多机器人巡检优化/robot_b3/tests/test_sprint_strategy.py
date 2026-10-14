import unittest

from robot_b3.offline import OfflineSimulator
from robot_b3.sprint_strategy import SprintStrategy


class SprintStrategyTests(unittest.TestCase):
    def test_zero_risk_budget_retains_strict_seven_station_cover(self):
        strategy = SprintStrategy(OfflineSimulator({}), route_budget_s=.01, risk_budget=0)
        result = strategy.run()
        self.assertEqual(result['coverage_stations'], 7)
        self.assertEqual(result['estimated_miss_risk'], 0.0)

    def test_explicit_risk_budget_can_skip_last_ring_station(self):
        scene = {c: ((0, 0), 1000) for c in range(1, 12)}
        strategy = SprintStrategy(OfflineSimulator(scene), route_budget_s=.01, risk_budget=.30)
        result = strategy.run()
        self.assertEqual(result['coverage_stations'], 6)
        self.assertGreater(result['estimated_miss_risk'], 0)
        self.assertLessEqual(result['estimated_miss_risk'], .30)


if __name__ == '__main__': unittest.main()
