import argparse
import csv
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt


mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"],
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
    "axes.spines.right": False,
    "axes.spines.top": False,
    "legend.frameon": False,
})


def read_rows(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        return [{key: float(value) for key, value in row.items()} for row in csv.DictReader(f)]


def selected_radius(calibration_rows):
    return max(calibration_rows, key=lambda row: row["cpm"])["radius_mm"]


def value_at_radius(rows, radius, key):
    for row in rows:
        if row["radius_mm"] == radius:
            return row[key]
    raise ValueError(f"radius {radius} not found")


def plot_split(calibration_rows, evaluation_rows, out):
    radius = selected_radius(calibration_rows)
    radii = [row["radius_mm"] for row in calibration_rows]
    cal_cpm = [row["cpm"] for row in calibration_rows]
    eval_cpm = [row["cpm"] for row in evaluation_rows]
    cal_low = [row["sensitivity_at_0.25_fp_per_scan"] for row in calibration_rows]
    eval_low = [row["sensitivity_at_0.25_fp_per_scan"] for row in evaluation_rows]

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), constrained_layout=True)
    axes[0].plot(radii, cal_cpm, marker="o", color="#3182bd", label="Calibration CPM")
    axes[0].plot(radii, eval_cpm, marker="o", color="#de6e56", label="Evaluation CPM")
    axes[0].axvline(radius, color="#444444", linestyle="--", linewidth=1)
    axes[0].set_xlabel("NMS radius (mm)")
    axes[0].set_ylabel("CPM")
    axes[0].set_ylim(0, 0.8)
    axes[0].set_title("a  Radius selection")
    axes[0].grid(axis="y", color="#eeeeee")
    axes[0].legend(loc="lower right")

    axes[1].plot(radii, cal_low, marker="o", color="#9ecae1", label="Calibration")
    axes[1].plot(radii, eval_low, marker="o", color="#fdae6b", label="Evaluation")
    axes[1].axvline(radius, color="#444444", linestyle="--", linewidth=1)
    axes[1].set_xlabel("NMS radius (mm)")
    axes[1].set_ylabel("Sensitivity @0.25 FP/scan")
    axes[1].set_ylim(0, 0.65)
    axes[1].set_title("b  Low-FP sensitivity")
    axes[1].grid(axis="y", color="#eeeeee")
    axes[1].legend(loc="lower right")

    fig.suptitle(
        f"Split-valid NMS: selected {radius:.0f} mm, evaluation CPM {value_at_radius(evaluation_rows, radius, 'cpm'):.4f}",
        x=0.02,
        y=1.04,
        ha="left",
        fontsize=11,
        fontweight="bold",
    )
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        fig.savefig(out.with_suffix(f".{ext}"), dpi=600 if ext == "png" else None, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Plot calibration/evaluation NMS validation curves.")
    parser.add_argument("--calibration-summary", required=True)
    parser.add_argument("--evaluation-summary", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    plot_split(read_rows(args.calibration_summary), read_rows(args.evaluation_summary), args.out)
    print(Path(args.out).with_suffix(".png"))


if __name__ == "__main__":
    main()
