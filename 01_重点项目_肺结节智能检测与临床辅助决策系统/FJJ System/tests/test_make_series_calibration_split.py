import unittest

from experiments.make_series_calibration_split import split_series_balanced


class MakeSeriesCalibrationSplitTests(unittest.TestCase):
    def test_split_series_balanced_keeps_annotation_totals_close(self):
        counts = {
            "a": 5,
            "b": 4,
            "c": 3,
            "d": 2,
            "e": 1,
            "f": 1,
        }

        calibration, evaluation = split_series_balanced(counts)

        self.assertTrue(calibration)
        self.assertTrue(evaluation)
        cal_total = sum(counts[key] for key in calibration)
        eval_total = sum(counts[key] for key in evaluation)
        self.assertLessEqual(abs(cal_total - eval_total), 1)
        self.assertEqual(set(calibration) | set(evaluation), set(counts))
        self.assertFalse(set(calibration) & set(evaluation))


if __name__ == "__main__":
    unittest.main()
