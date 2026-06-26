import argparse
import csv
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


FP_RATES = [0.125, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0]


mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"],
    "font.size": 8,
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
    "axes.spines.right": False,
    "axes.spines.top": False,
    "axes.linewidth": 0.8,
    "legend.frameon": False,
})


def read_froc_summary(path):
    data = {}
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            data[row["metric"]] = float(row["value"])
    return data


def read_bootstrap_summary(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sensitivity_vector(summary):
    return [summary[f"sensitivity_at_{rate}_fp_per_scan"] for rate in FP_RATES]


def cpm_ci(summary):
    point = summary["point"]["cpm"]
    ci = summary["ci95"]["cpm"]
    return point, ci["lower"], ci["upper"]


def plot_pooled_validation(baseline_froc, hardneg_froc, baseline_bootstrap, hardneg_bootstrap, out):
    base = read_froc_summary(baseline_froc)
    hard = read_froc_summary(hardneg_froc)
    base_boot = read_bootstrap_summary(baseline_bootstrap)
    hard_boot = read_bootstrap_summary(hardneg_bootstrap)

    fig = plt.figure(figsize=(7.2, 3.8), constrained_layout=True)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.5, 1.0])
    ax = fig.add_subplot(gs[0, 0])
    ax_ci = fig.add_subplot(gs[0, 1])

    ax.plot(FP_RATES, sensitivity_vector(base), marker="o", linewidth=2.0, color="#6b7280",
            label=f"Baseline CPM={base['cpm']:.3f}")
    ax.plot(FP_RATES, sensitivity_vector(hard), marker="o", linewidth=2.2, color="#2563eb",
            label=f"Hard-negative agent CPM={hard['cpm']:.3f}")
    ax.set_xscale("log", base=2)
    ax.set_xticks(FP_RATES)
    ax.set_xticklabels([str(rate).rstrip("0").rstrip(".") for rate in FP_RATES])
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("False positives per scan")
    ax.set_ylabel("Sensitivity")
    ax.set_title("Pooled external FROC", loc="left", fontweight="bold")
    ax.grid(axis="y", color="#eceff3", linewidth=0.8)
    ax.legend(loc="lower right")

    labels = ["Baseline", "Hard-negative\nagent"]
    points = []
    lower_err = []
    upper_err = []
    for boot in [base_boot, hard_boot]:
        point, lower, upper = cpm_ci(boot)
        points.append(point)
        lower_err.append(point - lower)
        upper_err.append(upper - point)
    x = np.arange(len(labels))
    ax_ci.errorbar(x, points, yerr=np.vstack([lower_err, upper_err]), fmt="none",
                   ecolor="#4b5563", elinewidth=1.4, capsize=4)
    ax_ci.scatter(x, points, s=42, color=["#6b7280", "#2563eb"], zorder=3)
    ax_ci.set_xlim(-0.55, 1.55)
    ax_ci.set_xticks(x)
    ax_ci.set_xticklabels(labels)
    ax_ci.set_ylim(0.35, 0.78)
    ax_ci.set_ylabel("CPM with 95% CI")
    ax_ci.set_title("Series bootstrap", loc="left", fontweight="bold")
    ax_ci.grid(axis="y", color="#eceff3", linewidth=0.8)
    for xx, point, lo, hi in zip(x, points, lower_err, upper_err):
        ax_ci.text(xx, point + hi + 0.015, f"{point:.3f}", ha="center", va="bottom", fontsize=8)

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        fig.savefig(out.with_suffix(f".{ext}"), dpi=600 if ext == "png" else None, bbox_inches="tight")
    plt.close(fig)
    return out.with_suffix(".png")


def main():
    parser = argparse.ArgumentParser(description="Plot pooled subset external validation FROC and CPM CI.")
    parser.add_argument("--baseline-froc", required=True)
    parser.add_argument("--hardneg-froc", required=True)
    parser.add_argument("--baseline-bootstrap", required=True)
    parser.add_argument("--hardneg-bootstrap", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    png = plot_pooled_validation(
        args.baseline_froc,
        args.hardneg_froc,
        args.baseline_bootstrap,
        args.hardneg_bootstrap,
        args.out,
    )
    print(png)


if __name__ == "__main__":
    main()
