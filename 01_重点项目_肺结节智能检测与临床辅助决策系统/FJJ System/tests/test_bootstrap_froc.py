import unittest

from experiments.bootstrap_froc import bootstrap_froc, percentile_interval
from experiments.froc_eval import Annotation, Prediction


class BootstrapFrocTests(unittest.TestCase):
    def test_percentile_interval(self):
        self.assertEqual(percentile_interval([5, 1, 3, 7, 9], alpha=0.5), (3, 7))

    def test_bootstrap_froc_is_reproducible(self):
        annotations = [
            Annotation("scan-a", 0, 0, 0, 10),
            Annotation("scan-b", 0, 0, 0, 10),
        ]
        predictions = [
            Prediction("scan-a", 1, 0, 0, 0.9),
            Prediction("scan-b", 1, 0, 0, 0.8),
            Prediction("scan-b", 100, 0, 0, 0.1),
        ]

        first = bootstrap_froc(annotations, predictions, ["scan-a", "scan-b"], n_boot=20, seed=42)
        second = bootstrap_froc(annotations, predictions, ["scan-a", "scan-b"], n_boot=20, seed=42)

        self.assertEqual(first, second)
        self.assertIn("cpm", first["point"])
        self.assertIn("cpm", first["ci95"])
        self.assertEqual(first["n_boot_requested"], 20)


if __name__ == "__main__":
    unittest.main()
