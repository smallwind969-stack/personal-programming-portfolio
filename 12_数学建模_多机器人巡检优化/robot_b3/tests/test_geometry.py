import math
import unittest

from robot_b3.geometry import arena_polygon, bearing_clip, diameter, enclosing_circle, seven_points


class GeometryTests(unittest.TestCase):
    def test_seven_points_cover_arena_with_1000_radius(self):
        points = seven_points(1123.0)
        for k in range(720):
            a = 2 * math.pi * k / 720
            for r in (0, 300, 600, 900, 1200, 1500, 1800):
                p = (r * math.cos(a), r * math.sin(a))
                self.assertLessEqual(min(math.dist(p, q) for q in points), 1000.0 + 1e-7)

    def test_two_crossing_bearings_shrink_region(self):
        poly = arena_polygon(1800, 360)
        p1 = bearing_clip(poly, (-500, 0), 0.0, 1.0)
        p2 = bearing_clip(p1, (0, -500), 90.0, 1.0)
        self.assertLess(diameter(p2), diameter(p1))

    def test_enclosing_circle_of_right_triangle(self):
        center, radius = enclosing_circle([(0, 0), (40, 0), (0, 30)])
        self.assertAlmostEqual(center[0], 20.0, places=6)
        self.assertAlmostEqual(center[1], 15.0, places=6)
        self.assertAlmostEqual(radius, 25.0, places=6)


if __name__ == '__main__':
    unittest.main()
