import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from experiments.score_luna16_candidates_stream import (
    batch_items,
    candidate_key,
    candidate_to_prediction,
    filter_already_scored,
    make_patch_tensor,
    normalize_image_once,
    write_predictions,
)


class ScoreLuna16CandidatesStreamTests(unittest.TestCase):
    def test_batch_items_splits_rows(self):
        batches = list(batch_items([1, 2, 3, 4, 5], 2))

        self.assertEqual(batches, [[1, 2], [3, 4], [5]])

    def test_candidate_to_prediction_preserves_coordinates(self):
        row = {
            "seriesuid": "scan-a",
            "coordX": "1.5",
            "coordY": "2.5",
            "coordZ": "3.5",
            "class": "1",
        }

        prediction = candidate_to_prediction(row, 0.75)

        self.assertEqual(prediction["seriesuid"], "scan-a")
        self.assertEqual(prediction["coordX"], 1.5)
        self.assertEqual(prediction["coordY"], 2.5)
        self.assertEqual(prediction["coordZ"], 3.5)
        self.assertEqual(prediction["probability"], 0.75)

    def test_make_patch_tensor_returns_ncdhw_tensor(self):
        patches = [np.zeros((4, 4, 4), dtype=np.float32), np.ones((4, 4, 4), dtype=np.float32)]

        tensor = make_patch_tensor(patches)

        self.assertEqual(tuple(tensor.shape), (2, 1, 4, 4, 4))

    def test_normalize_image_once_clips_hu_range(self):
        image = type("Image", (), {"array": np.array([[[-1300.0, -1200.0, 600.0, 1000.0]]], dtype=np.float32)})()

        normalized = normalize_image_once(image)

        self.assertEqual(normalized.dtype, np.float32)
        self.assertAlmostEqual(float(normalized.min()), 0.0)
        self.assertAlmostEqual(float(normalized.max()), 1.0)

    def test_filter_already_scored_uses_coordinate_key(self):
        rows = [
            {"seriesuid": "scan-a", "coordX": "1.0", "coordY": "2.0", "coordZ": "3.0"},
            {"seriesuid": "scan-a", "coordX": "4.0", "coordY": "5.0", "coordZ": "6.0"},
        ]
        scored = [{"seriesuid": "scan-a", "coordX": "1", "coordY": "2", "coordZ": "3", "probability": "0.9"}]

        remaining = filter_already_scored(rows, scored)

        self.assertEqual(len(remaining), 1)
        self.assertEqual(candidate_key(remaining[0]), ("scan-a", 4.0, 5.0, 6.0))

    def test_write_predictions_creates_parent_directory(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "predictions.csv"
            write_predictions(path, [{"seriesuid": "scan-a", "coordX": 1, "coordY": 2, "coordZ": 3, "probability": 0.4}])

            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
