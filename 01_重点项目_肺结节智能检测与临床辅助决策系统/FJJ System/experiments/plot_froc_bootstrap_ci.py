import argparse
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


METRICS = [
    "cpm",
    "sensitivity_at_0.125_fp_per_scan",
    "sensitivity_at_0.25_fp_per_scan",
    "sensitivity_at_0.5_fp_per_scan",
    "sensitivity_at_1.0_fp_per_scan",
    "sensitivity_at_2.0_fp_per_scan",
    "sensitivity_at_4.0_fp_per_scan",
    "sensitivity_at_8.0_fp_per_scan",
]

LABELS = {
    "cpm": "CPM",
    "sensitivity_at_0.125_fp_per_scan": "Sens @0.125 FP/scan",
    "sensitivity_at_0.25_fp_per_scan": "Sens @0.25 FP/scan",
    "sensitivity_at_0.5_fp_per_scan": "Sens @0.5 FP/scan",
    "sensitivity_at_1.0_fp_per_scan": "Sens @1 FP/scan",
    "sensitivity_at_2.0_fp_per_scan": "Sens @2 FP/scan",
    "sensitivity_at_4.0_fp_per_scan": "Sens @4 FP/scan",
    "sensitivity_at_8.0_fp_per_scan": "Sens @8 FP/scan",
}


mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"],
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
    "axes.spines.right": False,
    "axes.spines.top": False,
    "legend.frameon": False,
})


def metric_rows(summary, metrics=METRICS):
    rows = []
    for metric in metrics:
        ci = summary["ci95"][metric]
        rows.append({
            "metric": metric,
            "point": summary["point"][metric],
            "lower": ci["lower"],
            "upper": ci["upper"],
        })
    return rows


def plot_ci(summary, out):
    rows = metric_rows(summary)
    y = np.arange(len(rows))
    point = np.array([row["point"] for row in rows])
    lower = np.array([row["lower"] for row in rows])
    upper = np.array([row["upper"] for row in rows])
    xerr = np.vstack([point - lower, upper - point])

    fig, ax = plt.subplots(figsize=(6.8, 4.4), constrained_layout=True)
    colors = ["#de6e56"] + ["#3182bd"] * (len(rows) - 1)
    ax.errorbar(point, y, xerr=xerr, fmt="none", ecolor="#777777", elinewidth=1.4, capsize=3)
    ax.scatter(point, y, color=colors, s=28, zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels([LABELS[row["metric"]] for row in rows])
    ax.set_xlim(0, 1.28)
    ax.set_xlabel("Point estimate with 95% series-bootstrap CI")
    ax.set_title("Evaluation split fixed 10 mm NMS FROC uncertainty", loc="left", fontweight="bold")
    ax.grid(axis="x", color="#eeeeee")
    for row, yy in zip(rows, y):
        ax.text(1.07, yy, f"{row['point']:.3f} [{row['lower']:.3f}, {row['upper']:.3f}]", ha="left", va="center", fontsize=8)
    ax.invert_yaxis()

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        fig.savefig(out.with_suffix(f".{ext}"), dpi=600 if ext == "png" else None, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Plot series-bootstrap FROC/CPM confidence intervals.")
    parser.add_argument("--summary", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    summary = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    plot_ci(summary, args.out)
    print(Path(args.out).with_suffix(".png"))


if __name__ == "__main__":
    main()
