import unittest

from experiments.train_fpred_resnet import class_counts


class DummyDataset:
    rows = [{"class": "1"}, {"class": "0"}, {"class": "0"}]

    def __len__(self):
        return len(self.rows)


class TrainFpredResnetTests(unittest.TestCase):
    def test_class_counts(self):
        neg, pos = class_counts(DummyDataset())
        self.assertEqual(neg, 2)
        self.assertEqual(pos, 1)


if __name__ == "__main__":
    unittest.main()
