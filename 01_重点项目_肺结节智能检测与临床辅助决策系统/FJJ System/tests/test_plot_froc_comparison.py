import unittest

from experiments.plot_froc_comparison import paired_sensitivities


class PlotFrocComparisonTests(unittest.TestCase):
    def test_paired_sensitivities_reads_rates_in_order(self):
        left = {"sensitivity_at_0.125_fp_per_scan": 0.5, "sensitivity_at_0.25_fp_per_scan": 0.75}
        right = {"sensitivity_at_0.125_fp_per_scan": 0.25, "sensitivity_at_0.25_fp_per_scan": 0.5}

        rows = paired_sensitivities(left, right, [0.125, 0.25])

        self.assertEqual(rows[0], {"fp_per_scan": 0.125, "left": 0.5, "right": 0.25})
        self.assertEqual(rows[1]["right"], 0.5)


if __name__ == "__main__":
    unittest.main()
