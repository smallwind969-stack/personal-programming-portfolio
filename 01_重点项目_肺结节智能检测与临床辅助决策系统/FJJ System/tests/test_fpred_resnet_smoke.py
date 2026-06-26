import unittest

from experiments.run_fpred_resnet_smoke import confusion_at_threshold


class FpredResnetSmokeTests(unittest.TestCase):
    def test_confusion_at_threshold(self):
        rows = [
            {"class": "1", "probability": 0.9},
            {"class": "1", "probability": 0.2},
            {"class": "0", "probability": 0.8},
            {"class": "0", "probability": 0.1},
        ]

        summary = confusion_at_threshold(rows, 0.5)

        self.assertEqual(summary["tp"], 1)
        self.assertEqual(summary["fn"], 1)
        self.assertEqual(summary["fp"], 1)
        self.assertEqual(summary["tn"], 1)


if __name__ == "__main__":
    unittest.main()
