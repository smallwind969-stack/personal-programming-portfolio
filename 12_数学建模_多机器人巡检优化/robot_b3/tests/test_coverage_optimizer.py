import math
import unittest

from robot_b3.coverage import farthest_uncovered


class CoverageOptimizerTests(unittest.TestCase):
    def test_target_near_ring_station_replaces_it(self):
        from robot_b3.coverage_optimizer import complete_coverage
        existing=[(0,0),(1123,0)]
        planned=complete_coverage(existing,5,budget_s=.2)
        self.assertIsNotNone(planned)
        self.assertEqual(len(planned),5)
        self.assertLessEqual(farthest_uncovered(existing+planned)[1],1000.0)

    def test_result_is_deterministic(self):
        from robot_b3.coverage_optimizer import complete_coverage
        existing=[(0,0),(1080,80)]
        self.assertEqual(complete_coverage(existing,5,.1),complete_coverage(existing,5,.1))

    def test_too_few_centers_returns_none(self):
        from robot_b3.coverage_optimizer import complete_coverage
        self.assertIsNone(complete_coverage([(0,0)],4,.1))


if __name__=='__main__':unittest.main()
