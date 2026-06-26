import unittest

from experiments.export_fpred_luna_predictions import align_predictions_to_candidates


class ExportFpredLunaPredictionsTests(unittest.TestCase):
    def test_align_predictions_to_candidates_exports_world_coordinates(self):
        candidates = [
            {"seriesuid": "scan-a", "coordX": "1", "coordY": "2", "coordZ": "3", "class": "1", "split": "test"},
            {"seriesuid": "scan-b", "coordX": "4", "coordY": "5", "coordZ": "6", "class": "0", "split": "test"},
        ]
        manifest = [
            {"seriesuid": "scan-a", "class": "1", "patch": "a.npy", "status": "ok"},
            {"seriesuid": "scan-b", "class": "0", "patch": "b.npy", "status": "ok"},
        ]
        predictions = [
            {"seriesuid": "scan-a", "class": "1", "probability": "0.8", "patch": "a.npy"},
            {"seriesuid": "scan-b", "class": "0", "probability": "0.2", "patch": "b.npy"},
        ]

        rows = align_predictions_to_candidates(candidates, manifest, predictions)

        self.assertEqual(rows[0]["seriesuid"], "scan-a")
        self.assertEqual(rows[0]["coordX"], 1.0)
        self.assertEqual(rows[0]["coordY"], 2.0)
        self.assertEqual(rows[0]["coordZ"], 3.0)
        self.assertEqual(rows[0]["probability"], 0.8)

    def test_alignment_rejects_series_mismatch(self):
        candidates = [{"seriesuid": "scan-a", "coordX": "1", "coordY": "2", "coordZ": "3", "class": "1"}]
        manifest = [{"seriesuid": "scan-b", "class": "1", "patch": "a.npy", "status": "ok"}]
        predictions = [{"seriesuid": "scan-a", "class": "1", "probability": "0.8", "patch": "a.npy"}]

        with self.assertRaises(ValueError):
            align_predictions_to_candidates(candidates, manifest, predictions)


if __name__ == "__main__":
    unittest.main()
