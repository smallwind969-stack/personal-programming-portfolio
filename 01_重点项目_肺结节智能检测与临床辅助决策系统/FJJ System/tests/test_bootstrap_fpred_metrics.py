import unittest

from experiments.bootstrap_fpred_metrics import bootstrap_metrics, percentile_interval


class BootstrapFpredMetricsTests(unittest.TestCase):
    def test_percentile_interval_returns_requested_bounds(self):
        lower, upper = percentile_interval([5, 1, 9, 3, 7], alpha=0.5)

        self.assertEqual(lower, 3)
        self.assertEqual(upper, 7)

    def test_bootstrap_metrics_is_reproducible(self):
        rows = [
            {"seriesuid": "a", "label": 1, "probability": 0.91},
            {"seriesuid": "a", "label": 0, "probability": 0.12},
            {"seriesuid": "b", "label": 1, "probability": 0.82},
            {"seriesuid": "b", "label": 0, "probability": 0.33},
            {"seriesuid": "c", "label": 0, "probability": 0.21},
            {"seriesuid": "c", "label": 0, "probability": 0.04},
        ]

        first = bootstrap_metrics(rows, threshold=0.5, n_boot=30, seed=7, group_by_series=True)
        second = bootstrap_metrics(rows, threshold=0.5, n_boot=30, seed=7, group_by_series=True)

        self.assertEqual(first, second)
        self.assertEqual(first["resampling_unit"], "seriesuid")
        self.assertEqual(first["point"]["auc"], 1.0)
        self.assertIn("auc", first["ci95"])
        self.assertIn("sensitivity", first["ci95"])


if __name__ == "__main__":
    unittest.main()
