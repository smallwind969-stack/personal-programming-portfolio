import unittest

from experiments.plot_froc_bootstrap_ci import metric_rows


class PlotFrocBootstrapCiTests(unittest.TestCase):
    def test_metric_rows_extracts_point_and_ci(self):
        summary = {
            "point": {"cpm": 0.7},
            "ci95": {"cpm": {"lower": 0.6, "upper": 0.8}},
        }

        rows = metric_rows(summary, ["cpm"])

        self.assertEqual(rows, [{"metric": "cpm", "point": 0.7, "lower": 0.6, "upper": 0.8}])


if __name__ == "__main__":
    unittest.main()
