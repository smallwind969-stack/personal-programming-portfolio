import unittest

from experiments.plot_nms_froc_sweep import best_radius


class PlotNmsFrocSweepTests(unittest.TestCase):
    def test_best_radius_uses_max_cpm(self):
        rows = [
            {"radius_mm": 0.0, "cpm": 0.5},
            {"radius_mm": 10.0, "cpm": 0.7},
            {"radius_mm": 20.0, "cpm": 0.6},
        ]

        self.assertEqual(best_radius(rows), rows[1])


if __name__ == "__main__":
    unittest.main()
