import unittest

from robot_b3.coverage import farthest_uncovered
from robot_b3.geometry import seven_points
from robot_b3.residual_search import minimum_completion, optimized_completion


class ResidualSearchTests(unittest.TestCase):
    def setUp(self):
        self.points = seven_points(1123.0)

    def test_center_requires_all_six_fallback_stations(self):
        chosen = minimum_completion([self.points[0]], self.points[1:], (0, 0))
        self.assertEqual(len(chosen), 6)
        self.assertLessEqual(farthest_uncovered([self.points[0]] + chosen)[1], 1000.0)

    def test_actual_ring_visit_removes_that_future_station(self):
        chosen = minimum_completion(self.points[:2], self.points[1:], self.points[1])
        self.assertEqual(len(chosen), 5)
        self.assertNotIn(self.points[1], chosen)

    def test_result_is_deterministic_and_certified(self):
        actual = (1080.0, 80.0)
        first = minimum_completion([self.points[0], actual], self.points[1:], actual)
        second = minimum_completion([self.points[0], actual], self.points[1:], actual)
        self.assertEqual(first, second)
        self.assertLessEqual(farthest_uncovered([self.points[0], actual] + first)[1], 1000.0)

    def test_free_centers_can_replace_fixed_completion(self):
        actual = (1080.0, 80.0)
        chosen = optimized_completion([self.points[0], actual], self.points[1:], actual, .1)
        self.assertEqual(len(chosen), 5)
        self.assertLessEqual(farthest_uncovered([self.points[0], actual] + chosen)[1], 1000.0)


if __name__ == '__main__':
    unittest.main()
