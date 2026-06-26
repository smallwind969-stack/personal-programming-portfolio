import csv
import json
import tempfile
import unittest
from pathlib import Path

from experiments.plot_pooled_external_validation import plot_pooled_validation


def write_froc_summary(path, cpm, sens):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        for rate, value in sens.items():
            writer.writerow([f"sensitivity_at_{rate}_fp_per_scan", value])
        writer.writerow(["cpm", cpm])


def write_bootstrap(path, cpm, lower, upper):
    point = {"cpm": cpm}
    ci = {"cpm": {"lower": lower, "upper": upper}}
    for rate in [0.125, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0]:
        key = f"sensitivity_at_{rate}_fp_per_scan"
        point[key] = 0.5
        ci[key] = {"lower": 0.4, "upper": 0.6}
    Path(path).write_text(json.dumps({"point": point, "ci95": ci}), encoding="utf-8")


class PlotPooledExternalValidationTests(unittest.TestCase):
    def test_plot_pooled_validation_writes_all_exports(self):
        sens = {0.125: 0.2, 0.25: 0.3, 0.5: 0.4, 1.0: 0.5, 2.0: 0.6, 4.0: 0.7, 8.0: 0.8}
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            base_froc = tmp / "base.csv"
            hard_froc = tmp / "hard.csv"
            base_boot = tmp / "base.json"
            hard_boot = tmp / "hard.json"
            out = tmp / "figure"
            write_froc_summary(base_froc, 0.5, sens)
            write_froc_summary(hard_froc, 0.6, sens)
            write_bootstrap(base_boot, 0.5, 0.4, 0.6)
            write_bootstrap(hard_boot, 0.6, 0.5, 0.7)

            png = plot_pooled_validation(base_froc, hard_froc, base_boot, hard_boot, out)

            self.assertTrue(png.exists())
            self.assertTrue(out.with_suffix(".pdf").exists())
            self.assertTrue(out.with_suffix(".svg").exists())


if __name__ == "__main__":
    unittest.main()
