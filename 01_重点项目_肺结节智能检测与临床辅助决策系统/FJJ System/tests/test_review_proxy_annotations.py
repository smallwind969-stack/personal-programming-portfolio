import unittest

from experiments.export_review_proxy_annotations import estimate_diameter_mm


class ReviewProxyAnnotationTests(unittest.TestCase):
    def test_estimates_diameter_from_area(self):
        value = estimate_diameter_mm({"area": 78.5398}, default_diameter_mm=8.0)
        self.assertAlmostEqual(value, 10.0, places=3)

    def test_uses_bbox_when_area_missing(self):
        value = estimate_diameter_mm({"bbox_3d": {"x1": 10, "x2": 20, "y1": 4, "y2": 12}}, 8.0)
        self.assertEqual(value, 9.0)

    def test_uses_default_when_size_missing(self):
        self.assertEqual(estimate_diameter_mm({}, 8.0), 8.0)


if __name__ == "__main__":
    unittest.main()
