import unittest

from experiments.make_luna16_fpred_splits import assign_splits, balanced_rows, split_series, summarize


class Luna16FpredSplitTests(unittest.TestCase):
    def test_balanced_rows_keeps_all_positives_and_limits_negatives(self):
        rows = [
            {"seriesuid": "a", "class": "1"},
            {"seriesuid": "b", "class": "1"},
            {"seriesuid": "c", "class": "0"},
            {"seriesuid": "d", "class": "0"},
            {"seriesuid": "e", "class": "0"},
            {"seriesuid": "f", "class": "0"},
        ]

        selected = balanced_rows(rows, max_neg_per_pos=1, seed=1)

        self.assertEqual(sum(1 for row in selected if row["class"] == "1"), 2)
        self.assertEqual(sum(1 for row in selected if row["class"] == "0"), 2)

    def test_assign_splits_and_summary(self):
        train, val, test = split_series(["a", "b", "c", "d"], 0.5, 0.25, seed=1)
        rows = assign_splits(
            [
                {"seriesuid": next(iter(train)), "class": "1"},
                {"seriesuid": next(iter(val)), "class": "0"},
                {"seriesuid": next(iter(test)), "class": "0"},
            ],
            train,
            val,
        )
        summary = summarize(rows)

        self.assertIn("train", summary)
        self.assertIn("val", summary)
        self.assertIn("test", summary)


if __name__ == "__main__":
    unittest.main()
