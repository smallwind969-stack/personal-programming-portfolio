import csv
import tempfile
import unittest
from pathlib import Path

from experiments.validate_luna_submission import validate_submission


class LunaSubmissionValidationTests(unittest.TestCase):
    def write_csv(self, rows):
        tmp = tempfile.TemporaryDirectory()
        path = Path(tmp.name) / "submission.csv"
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["seriesuid", "coordX", "coordY", "coordZ", "probability"])
            writer.writeheader()
            writer.writerows(rows)
        self.addCleanup(tmp.cleanup)
        return path

    def test_valid_submission(self):
        path = self.write_csv([{"seriesuid": "a", "coordX": 1, "coordY": 2, "coordZ": 3, "probability": 0.8}])
        report = validate_submission(path, {"a"})
        self.assertTrue(report["valid"])
        self.assertEqual(report["row_count"], 1)

    def test_invalid_probability_fails(self):
        path = self.write_csv([{"seriesuid": "a", "coordX": 1, "coordY": 2, "coordZ": 3, "probability": 1.8}])
        report = validate_submission(path, {"a"})
        self.assertFalse(report["valid"])
        self.assertIn("probability outside [0,1] or invalid: 1", report["errors"])


if __name__ == "__main__":
    unittest.main()
