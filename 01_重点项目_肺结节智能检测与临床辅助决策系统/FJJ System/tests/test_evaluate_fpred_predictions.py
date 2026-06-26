import unittest

from experiments.evaluate_fpred_predictions import auc_trapezoid, confusion, roc_points


class EvaluateFpredPredictionsTests(unittest.TestCase):
    def test_confusion_metrics(self):
        rows = [
            {"label": 1, "probability": 0.9},
            {"label": 1, "probability": 0.4},
            {"label": 0, "probability": 0.7},
            {"label": 0, "probability": 0.1},
        ]

        result = confusion(rows, 0.5)

        self.assertEqual(result["tp"], 1)
        self.assertEqual(result["fp"], 1)
        self.assertEqual(result["tn"], 1)
        self.assertEqual(result["fn"], 1)
        self.assertEqual(result["precision"], 0.5)

    def test_auc_perfect_ranking(self):
        rows = [
            {"label": 1, "probability": 0.9},
            {"label": 1, "probability": 0.8},
            {"label": 0, "probability": 0.2},
            {"label": 0, "probability": 0.1},
        ]

        auc = auc_trapezoid(roc_points(rows))

        self.assertAlmostEqual(auc, 1.0)


if __name__ == "__main__":
    unittest.main()
