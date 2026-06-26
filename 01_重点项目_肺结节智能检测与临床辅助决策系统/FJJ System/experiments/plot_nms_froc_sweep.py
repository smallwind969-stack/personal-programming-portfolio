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


def best_radius(rows):
    return max(rows, key=lambda row: row["cpm"])


def plot_sweep(rows, out):
    best = best_radius(rows)
    radii = [row["radius_mm"] for row in rows]
    cpm = [row["cpm"] for row in rows]
    predictions = [row["prediction_count"] for row in rows]
    low_fp = [row["sensitivity_at_0.25_fp_per_scan"] for row in rows]
    mid_fp = [row["sensitivity_at_1.0_fp_per_scan"] for row in rows]

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.3), constrained_layout=True)
    axes[0].plot(radii, cpm, marker="o", color="#de6e56", label="CPM")
    axes[0].plot(radii, low_fp, marker="o", color="#9ecae1", label="Sens @0.25 FP/scan")
    axes[0].plot(radii, mid_fp, marker="o", color="#74c476", label="Sens @1.0 FP/scan")
    axes[0].axvline(best["radius_mm"], color="#444444", linestyle="--", linewidth=1)
    axes[0].set_xlabel("NMS radius (mm)")
    axes[0].set_ylabel("Metric")
    axes[0].set_ylim(0, 1.02)
    axes[0].set_title("a  FROC sensitivity and CPM")
    axes[0].grid(axis="y", color="#eeeeee")
    axes[0].legend(loc="lower right")

    axes[1].plot(radii, predictions, marker="o", color="#756bb1")
    axes[1].axvline(best["radius_mm"], color="#444444", linestyle="--", linewidth=1)
    axes[1].set_xlabel("NMS radius (mm)")
    axes[1].set_ylabel("Prediction count")
    axes[1].set_title("b  Candidate suppression")
    axes[1].grid(axis="y", color="#eeeeee")
    axes[1].text(
        0.98,
        0.88,
        f"Best radius = {best['radius_mm']:.1f} mm\nCPM = {best['cpm']:.4f}",
        ha="right",
        va="top",
        transform=axes[1].transAxes,
        fontsize=9,
        color="#333333",
    )
    fig.suptitle("Subset0 candidates_V2 NMS sweep", x=0.02, y=1.04, ha="left", fontsize=12, fontweight="bold")

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        fig.savefig(out.with_suffix(f".{ext}"), dpi=600 if ext == "png" else None, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Plot NMS-FROC sweep summary.")
    parser.add_argument("--summary", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    plot_sweep(read_rows(args.summary), args.out)
    print(Path(args.out).with_suffix(".png"))


if __name__ == "__main__":
    main()
