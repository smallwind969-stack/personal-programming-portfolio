import unittest

from experiments.make_subset_patch_manifest import balanced_sample


class SubsetPatchManifestTests(unittest.TestCase):
    def test_balanced_sample_limits_each_class(self):
        rows = [{"class": "1", "seriesuid": str(i)} for i in range(3)]
        rows += [{"class": "0", "seriesuid": str(i)} for i in range(10)]

        selected = balanced_sample(rows, positives=2, negatives=4, seed=1)

        self.assertEqual(sum(1 for row in selected if row["class"] == "1"), 2)
        self.assertEqual(sum(1 for row in selected if row["class"] == "0"), 4)


if __name__ == "__main__":
    unittest.main()
