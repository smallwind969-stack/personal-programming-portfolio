import tempfile
import unittest
from pathlib import Path

from experiments.froc_eval import Annotation, Prediction
from experiments.paired_bootstrap_froc_gain import paired_bootstrap_gain, resumable_paired_bootstrap_gain, write_gain_csv


class PairedBootstrapFrocGainTests(unittest.TestCase):
    def test_paired_bootstrap_reports_positive_gain_for_better_predictions(self):
        annotations = [Annotation("scan-a", 0.0, 0.0, 0.0, 10.0), Annotation("scan-b", 0.0, 0.0, 0.0, 10.0)]
        baseline = [
            Prediction("scan-a", 100.0, 0.0, 0.0, 0.9),
            Prediction("scan-b", 1.0, 0.0, 0.0, 0.8),
        ]
        experimental = [
            Prediction("scan-a", 1.0, 0.0, 0.0, 0.9),
            Prediction("scan-b", 1.0, 0.0, 0.0, 0.8),
        ]

        summary = paired_bootstrap_gain(annotations, baseline, experimental, ["scan-a", "scan-b"], n_boot=20, seed=7)

        self.assertGreater(summary["gain_point"]["cpm"], 0.0)
        self.assertGreater(summary["p_gain_positive"]["cpm"], 0.0)
        self.assertEqual(summary["n_boot_accepted"], 20)

    def test_write_gain_csv(self):
        summary = {
            "gain_point": {"cpm": 0.1},
            "gain_ci95": {"cpm": {"lower": 0.01, "upper": 0.2}},
            "p_gain_positive": {"cpm": 1.0},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gain.csv"
            write_gain_csv(path, summary)

            text = path.read_text(encoding="utf-8-sig")

        self.assertIn("metric,gain,ci95_lower,ci95_upper,p_gain_positive", text)
        self.assertIn("cpm,0.1,0.01,0.2,1.0", text)

    def test_resumable_bootstrap_extends_existing_samples(self):
        annotations = [Annotation("scan-a", 0.0, 0.0, 0.0, 10.0), Annotation("scan-b", 0.0, 0.0, 0.0, 10.0)]
        baseline = [
            Prediction("scan-a", 100.0, 0.0, 0.0, 0.9),
            Prediction("scan-b", 1.0, 0.0, 0.0, 0.8),
        ]
        experimental = [
            Prediction("scan-a", 1.0, 0.0, 0.0, 0.9),
            Prediction("scan-b", 1.0, 0.0, 0.0, 0.8),
        ]

        first = resumable_paired_bootstrap_gain(
            annotations, baseline, experimental, ["scan-a", "scan-b"], n_boot=2, seed=11
        )
        resumed = resumable_paired_bootstrap_gain(
            annotations,
            baseline,
            experimental,
            ["scan-a", "scan-b"],
            n_boot=5,
            seed=11,
            existing_samples=first["samples"],
        )

        self.assertEqual(first["n_boot_accepted"], 2)
        self.assertEqual(resumed["n_boot_accepted"], 5)
        self.assertEqual(len(resumed["samples"]["cpm"]), 5)
        self.assertEqual(resumed["samples"]["cpm"][:2], first["samples"]["cpm"])


if __name__ == "__main__":
    unittest.main()
