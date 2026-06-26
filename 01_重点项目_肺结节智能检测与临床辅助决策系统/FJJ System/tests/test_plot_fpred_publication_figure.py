import unittest

from experiments.plot_fpred_publication_figure import metric_rows_from_bootstrap


class PlotFpredPublicationFigureTests(unittest.TestCase):
    def test_metric_rows_from_bootstrap_flattens_ci(self):
        summary = {
            "point": {"auc": 0.9, "sensitivity": 0.8},
            "ci95": {
                "auc": {"lower": 0.7, "upper": 1.0},
                "sensitivity": {"lower": 0.5, "upper": 0.95},
            },
        }

        rows = metric_rows_from_bootstrap(summary, ["auc", "sensitivity"])

        self.assertEqual(rows[0]["metric"], "auc")
        self.assertEqual(rows[0]["point"], 0.9)
        self.assertEqual(rows[0]["lower"], 0.7)
        self.assertEqual(rows[1]["upper"], 0.95)


if __name__ == "__main__":
    unittest.main()
