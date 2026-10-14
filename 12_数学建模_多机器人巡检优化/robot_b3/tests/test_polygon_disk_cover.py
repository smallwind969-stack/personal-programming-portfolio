import math
import unittest


def inside_convex(point, polygon):
    signs = []
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        cross = ((b[0] - a[0]) * (point[1] - a[1])
                 - (b[1] - a[1]) * (point[0] - a[0]))
        if abs(cross) > 1e-8:
            signs.append(cross > 0)
    return not signs or all(signs) or not any(signs)


class PolygonDiskCoverTests(unittest.TestCase):
    def test_dense_polygon_samples_are_covered(self):
        from robot_b3.polygon_disk_cover import certified_polygon_disk_cover

        polygon = [(-70.0, 0.0), (0.0, -18.0), (75.0, 3.0), (0.0, 19.0)]
        plan = certified_polygon_disk_cover(polygon, start=(0.0, 0.0))
        for ix in range(-70, 76, 2):
            for iy in range(-20, 21, 2):
                p = (float(ix), float(iy))
                if inside_convex(p, polygon):
                    self.assertLessEqual(
                        min(math.dist(p, q) for q in plan.points),
                        20.0 + 1e-7,
                    )

    def test_rotated_thin_polygon_does_not_cover_whole_bounding_box(self):
        from robot_b3.polygon_disk_cover import certified_polygon_disk_cover

        polygon = [(-100.0, -80.0), (-90.0, -90.0),
                   (100.0, 80.0), (90.0, 90.0)]
        plan = certified_polygon_disk_cover(polygon, start=(0.0, 0.0))
        spacing = 20.0 * math.sqrt(2.0) * (1.0 - 1e-10)
        bbox_cells = math.ceil(200.0 / spacing) * math.ceil(180.0 / spacing)
        self.assertLess(len(plan.points), bbox_cells * 0.6)

    def test_plan_has_finite_worst_case_time(self):
        from robot_b3.polygon_disk_cover import certified_polygon_disk_cover

        plan = certified_polygon_disk_cover(
            [(-10.0, -10.0), (10.0, -10.0),
             (10.0, 10.0), (-10.0, 10.0)],
            start=(100.0, 0.0), destination=(120.0, 0.0),
        )
        self.assertGreaterEqual(len(plan.points), 1)
        self.assertGreater(plan.upper_time_s, 0.0)
        self.assertTrue(math.isfinite(plan.upper_time_s))


if __name__ == '__main__':
    unittest.main()
