import unittest

from robot_b3.coverage_risk import uncovered_fraction, miss_risk
from robot_b3.geometry import seven_points


class CoverageRiskTests(unittest.TestCase):
    def test_certified_seven_points_have_zero_risk(self):
        points = seven_points(1123.0)
        self.assertEqual(uncovered_fraction(points), 0.0)
        self.assertEqual(miss_risk(points, 9, 11), 0.0)

    def test_one_omitted_ring_station_has_explicit_nonzero_risk(self):
        fraction = uncovered_fraction(seven_points(1123.0)[:-1])
        self.assertGreater(fraction, .04)
        self.assertLess(fraction, .07)
        self.assertGreater(miss_risk(seven_points(1123.0)[:-1], 9, 11), .20)

    def test_sixteen_found_sources_leave_no_missing_source_risk(self):
        self.assertEqual(miss_risk([(0, 0)], 4, 16), 0.0)


if __name__ == '__main__': unittest.main()
