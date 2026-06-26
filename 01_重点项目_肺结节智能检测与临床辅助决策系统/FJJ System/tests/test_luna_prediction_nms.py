import unittest

from experiments.luna_prediction_nms import PredictionRow, nms_predictions


class LunaPredictionNmsTests(unittest.TestCase):
    def test_nms_suppresses_lower_probability_nearby_prediction(self):
        rows = [
            PredictionRow("scan-a", 0.0, 0.0, 0.0, 0.9),
            PredictionRow("scan-a", 3.0, 0.0, 0.0, 0.8),
            PredictionRow("scan-a", 20.0, 0.0, 0.0, 0.7),
        ]

        kept = nms_predictions(rows, radius_mm=5.0)

        self.assertEqual(len(kept), 2)
        self.assertEqual([row.probability for row in kept], [0.9, 0.7])

    def test_nms_does_not_suppress_across_series(self):
        rows = [
            PredictionRow("scan-a", 0.0, 0.0, 0.0, 0.9),
            PredictionRow("scan-b", 0.0, 0.0, 0.0, 0.8),
        ]

        kept = nms_predictions(rows, radius_mm=5.0)

        self.assertEqual(len(kept), 2)


if __name__ == "__main__":
    unittest.main()
