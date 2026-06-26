import unittest

from experiments.froc_eval import Annotation, Prediction, evaluate_froc, evaluate_froc_slow, filter_to_seriesuids


class FrocEvaluationTests(unittest.TestCase):
    def test_duplicate_detection_counts_as_one_tp_and_one_fp(self):
        annotations = [Annotation("scan-a", 0.0, 0.0, 0.0, 10.0)]
        predictions = [
            Prediction("scan-a", 1.0, 1.0, 1.0, 0.9),
            Prediction("scan-a", 2.0, 0.0, 0.0, 0.8),
        ]

        points, sensitivities, cpm = evaluate_froc(annotations, predictions, ["scan-a"])

        duplicate_active_point = next(p for p in points if p["threshold"] == 0.8)

        self.assertEqual(duplicate_active_point["tp"], 1)
        self.assertEqual(duplicate_active_point["fp"], 1)
        self.assertEqual(duplicate_active_point["fn"], 0)
        self.assertEqual(sensitivities[8.0], 1.0)
        self.assertGreater(cpm, 0.0)

    def test_low_confidence_false_positive_does_not_hurt_strict_fp_rates(self):
        annotations = [Annotation("scan-a", 0.0, 0.0, 0.0, 10.0)]
        predictions = [
            Prediction("scan-a", 1.0, 1.0, 1.0, 0.9),
            Prediction("scan-a", 100.0, 100.0, 100.0, 0.1),
        ]

        _points, sensitivities, cpm = evaluate_froc(annotations, predictions, ["scan-a"])

        self.assertEqual(sensitivities[0.125], 1.0)
        self.assertEqual(cpm, 1.0)

    def test_seriesuid_subset_filters_annotations_and_predictions(self):
        annotations = [
            Annotation("scan-a", 0.0, 0.0, 0.0, 10.0),
            Annotation("scan-b", 0.0, 0.0, 0.0, 10.0),
        ]
        predictions = [
            Prediction("scan-a", 1.0, 1.0, 1.0, 0.9),
            Prediction("scan-b", 1.0, 1.0, 1.0, 0.9),
        ]

        points, sensitivities, cpm = evaluate_froc(annotations, predictions, ["scan-a"])

        first_active = next(p for p in points if p["threshold"] == 0.9)
        self.assertEqual(first_active["tp"], 1)
        self.assertEqual(first_active["fn"], 0)
        self.assertEqual(sensitivities[0.125], 1.0)
        self.assertEqual(cpm, 1.0)

    def test_filter_to_seriesuids_returns_consistent_summary_inputs(self):
        annotations = [
            Annotation("scan-a", 0.0, 0.0, 0.0, 10.0),
            Annotation("scan-b", 0.0, 0.0, 0.0, 10.0),
        ]
        predictions = [
            Prediction("scan-a", 1.0, 1.0, 1.0, 0.9),
            Prediction("scan-b", 1.0, 1.0, 1.0, 0.9),
        ]

        filtered_annotations, filtered_predictions = filter_to_seriesuids(annotations, predictions, ["scan-a"])

        self.assertEqual(len(filtered_annotations), 1)
        self.assertEqual(len(filtered_predictions), 1)
        self.assertEqual(filtered_annotations[0].seriesuid, "scan-a")

    def test_fast_froc_matches_slow_reference(self):
        annotations = [
            Annotation("scan-a", 0.0, 0.0, 0.0, 10.0),
            Annotation("scan-a", 20.0, 0.0, 0.0, 8.0),
        ]
        predictions = [
            Prediction("scan-a", 1.0, 0.0, 0.0, 0.9),
            Prediction("scan-a", 21.0, 0.0, 0.0, 0.7),
            Prediction("scan-a", 100.0, 0.0, 0.0, 0.6),
            Prediction("scan-a", 101.0, 0.0, 0.0, 0.1),
        ]

        fast_points, fast_sensitivities, fast_cpm = evaluate_froc(annotations, predictions, ["scan-a"])
        slow_points, slow_sensitivities, slow_cpm = evaluate_froc_slow(annotations, predictions, ["scan-a"])

        self.assertEqual(fast_points, slow_points)
        self.assertEqual(fast_sensitivities, slow_sensitivities)
        self.assertEqual(fast_cpm, slow_cpm)


if __name__ == "__main__":
    unittest.main()
