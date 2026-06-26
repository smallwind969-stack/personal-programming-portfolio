import csv
import tempfile
import unittest
from pathlib import Path

from experiments.merge_luna_external_validation import merge_inputs, read_predictions, read_seriesuids


def write_series(path, values):
    Path(path).write_text("\n".join(values) + "\n", encoding="utf-8")


def write_predictions(path, rows):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["seriesuid", "coordX", "coordY", "coordZ", "probability"])
        writer.writeheader()
        writer.writerows(rows)


class MergeLunaExternalValidationTests(unittest.TestCase):
    def test_merges_non_overlapping_series_and_predictions(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            s1 = tmp / "s1.txt"
            s2 = tmp / "s2.txt"
            p1 = tmp / "p1.csv"
            p2 = tmp / "p2.csv"
            write_series(s1, ["scan-a"])
            write_series(s2, ["scan-b"])
            write_predictions(p1, [{"seriesuid": "scan-a", "coordX": 1, "coordY": 2, "coordZ": 3, "probability": 0.9}])
            write_predictions(p2, [{"seriesuid": "scan-b", "coordX": 4, "coordY": 5, "coordZ": 6, "probability": 0.8}])

            seriesuids, predictions, reports = merge_inputs([
                {"label": "subset-a", "seriesuids": s1, "predictions": p1},
                {"label": "subset-b", "seriesuids": s2, "predictions": p2},
            ])

        self.assertEqual(seriesuids, ["scan-a", "scan-b"])
        self.assertEqual([row["seriesuid"] for row in predictions], ["scan-a", "scan-b"])
        self.assertEqual([row["series_count"] for row in reports], [1, 1])

    def test_rejects_overlapping_seriesuids(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            s1 = tmp / "s1.txt"
            s2 = tmp / "s2.txt"
            p1 = tmp / "p1.csv"
            p2 = tmp / "p2.csv"
            write_series(s1, ["scan-a"])
            write_series(s2, ["scan-a"])
            write_predictions(p1, [{"seriesuid": "scan-a", "coordX": 1, "coordY": 2, "coordZ": 3, "probability": 0.9}])
            write_predictions(p2, [{"seriesuid": "scan-a", "coordX": 4, "coordY": 5, "coordZ": 6, "probability": 0.8}])

            with self.assertRaisesRegex(ValueError, "Series overlap"):
                merge_inputs([
                    {"label": "subset-a", "seriesuids": s1, "predictions": p1},
                    {"label": "subset-b", "seriesuids": s2, "predictions": p2},
                ])

    def test_rejects_predictions_outside_declared_seriesuids(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            s1 = tmp / "s1.txt"
            p1 = tmp / "p1.csv"
            write_series(s1, ["scan-a"])
            write_predictions(p1, [{"seriesuid": "scan-x", "coordX": 1, "coordY": 2, "coordZ": 3, "probability": 0.9}])

            with self.assertRaisesRegex(ValueError, "include series not in seriesuid file"):
                merge_inputs([{"label": "subset-a", "seriesuids": s1, "predictions": p1}])

    def test_read_helpers_use_expected_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            series = tmp / "series.txt"
            preds = tmp / "predictions.csv"
            write_series(series, ["scan-a", "", "scan-b"])
            write_predictions(preds, [{"seriesuid": "scan-a", "coordX": 1, "coordY": 2, "coordZ": 3, "probability": 0.9}])

            self.assertEqual(read_seriesuids(series), ["scan-a", "scan-b"])
            self.assertEqual(read_predictions(preds)[0]["probability"], "0.9")


if __name__ == "__main__":
    unittest.main()
