import csv
import tempfile
import unittest
from pathlib import Path

from experiments.summarize_luna16_resources import describe_candidates


class SummarizeLuna16ResourcesTests(unittest.TestCase):
    def test_describe_candidates_counts_classes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.csv"
            with path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["seriesuid", "coordX", "coordY", "coordZ", "class"])
                writer.writeheader()
                writer.writerow({"seriesuid": "a", "coordX": 1, "coordY": 2, "coordZ": 3, "class": 1})
                writer.writerow({"seriesuid": "a", "coordX": 4, "coordY": 5, "coordZ": 6, "class": 0})

            summary = describe_candidates(path)

        self.assertEqual(summary["row_count"], 2)
        self.assertEqual(summary["series_count"], 1)
        self.assertEqual(summary["positive_count"], 1)
        self.assertEqual(summary["negative_count"], 1)


if __name__ == "__main__":
    unittest.main()
