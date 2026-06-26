import unittest

from experiments.luna_prediction_nms import PredictionRow
from experiments.nms_froc_sweep import count_rows_for_series, filter_rows_for_series, parse_radii


class NmsFrocSweepTests(unittest.TestCase):
    def test_parse_radii(self):
        self.assertEqual(parse_radii("0,5,10.5"), [0.0, 5.0, 10.5])

    def test_count_rows_for_series(self):
        rows = [
            PredictionRow("scan-a", 0, 0, 0, 0.9),
            PredictionRow("scan-b", 0, 0, 0, 0.8),
        ]

        self.assertEqual(count_rows_for_series(rows, {"scan-a"}), 1)

    def test_filter_rows_for_series(self):
        rows = [
            PredictionRow("scan-a", 0, 0, 0, 0.9),
            PredictionRow("scan-b", 0, 0, 0, 0.8),
        ]

        filtered = filter_rows_for_series(rows, {"scan-b"})

        self.assertEqual(filtered, [rows[1]])


if __name__ == "__main__":
    unittest.main()
