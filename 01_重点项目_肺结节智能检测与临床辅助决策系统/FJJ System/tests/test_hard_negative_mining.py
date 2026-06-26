import unittest

from experiments.mine_hard_negatives import (
    Annotation,
    Prediction,
    is_true_positive,
    select_hard_negatives,
)


class HardNegativeMiningTests(unittest.TestCase):
    def test_is_true_positive_uses_annotation_radius(self):
        annotation = Annotation("scan-a", 0.0, 0.0, 0.0, 10.0)

        self.assertTrue(is_true_positive(Prediction("scan-a", 3.0, 4.0, 0.0, 0.9), [annotation]))
        self.assertFalse(is_true_positive(Prediction("scan-a", 5.1, 0.0, 0.0, 0.9), [annotation]))

    def test_select_hard_negatives_ignores_true_positives_and_sorts_by_probability(self):
        annotations = [Annotation("scan-a", 0.0, 0.0, 0.0, 10.0)]
        predictions = [
            Prediction("scan-a", 1.0, 1.0, 1.0, 0.99),
            Prediction("scan-a", 30.0, 30.0, 30.0, 0.80),
            Prediction("scan-a", 40.0, 40.0, 40.0, 0.95),
            Prediction("scan-b", 50.0, 50.0, 50.0, 0.97),
        ]

        rows = select_hard_negatives(
            predictions,
            annotations,
            allowed_series={"scan-a"},
            min_probability=0.5,
            max_total=2,
            max_per_series=2,
        )

        self.assertEqual([row["probability"] for row in rows], [0.95, 0.8])
        self.assertTrue(all(row["class"] == "0" for row in rows))
        self.assertTrue(all(row["split"] == "train_hard_negative" for row in rows))

    def test_select_hard_negatives_applies_per_series_cap(self):
        predictions = [
            Prediction("scan-a", 10.0, 0.0, 0.0, 0.9),
            Prediction("scan-a", 20.0, 0.0, 0.0, 0.8),
            Prediction("scan-b", 10.0, 0.0, 0.0, 0.7),
        ]

        rows = select_hard_negatives(
            predictions,
            annotations=[],
            allowed_series={"scan-a", "scan-b"},
            min_probability=0.0,
            max_total=10,
            max_per_series=1,
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual([row["seriesuid"] for row in rows], ["scan-a", "scan-b"])


if __name__ == "__main__":
    unittest.main()
