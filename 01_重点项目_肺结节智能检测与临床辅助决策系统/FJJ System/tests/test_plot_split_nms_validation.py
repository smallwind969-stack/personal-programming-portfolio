import unittest

from experiments.plot_split_nms_validation import selected_radius


class PlotSplitNmsValidationTests(unittest.TestCase):
    def test_selected_radius_uses_calibration_max_cpm(self):
        rows = [
            {"radius_mm": 0.0, "cpm": 0.4},
            {"radius_mm": 10.0, "cpm": 0.6},
            {"radius_mm": 20.0, "cpm": 0.5},
        ]

        self.assertEqual(selected_radius(rows), 10.0)


if __name__ == "__main__":
    unittest.main()
