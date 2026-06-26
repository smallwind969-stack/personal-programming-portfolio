import argparse
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


METRICS = ["auc", "accuracy", "precision", "sensitivity", "specificity", "f1"]
METRIC_LABELS = {
    "auc": "AUC",
    "accuracy": "Accuracy",
    "precision": "Precision",
    "sensitivity": "Sensitivity",
    "specificity": "Specificity",
    "f1": "F1",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def metric_rows_from_bootstrap(summary, metrics=METRICS):
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


def save_publication_figure(fig, out_base):
    out_base = Path(out_base)
    out_base.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_base.with_suffix(".png"), dpi=450, bbox_inches="tight")
    fig.savefig(out_base.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(out_base.with_suffix(".svg"), bbox_inches="tight")


def _configure_matplotlib():
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 8,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.8,
        "legend.frameon": False,
    })


def _plot_ci_panel(ax, rows, title, color):
    y = np.arange(len(rows))
    points = np.array([row["point"] for row in rows])
    lower = np.array([row["lower"] for row in rows])
    upper = np.array([row["upper"] for row in rows])
    xerr = np.vstack([points - lower, upper - points])
    ax.errorbar(points, y, xerr=xerr, fmt="o", color=color, ecolor="#7a7a7a", capsize=2.5, markersize=4)
    ax.set_yticks(y)
    ax.set_yticklabels([METRIC_LABELS[row["metric"]] for row in rows])
    ax.set_xlim(0, 1.18)
    ax.set_xlabel("Point estimate with 95% bootstrap CI")
    ax.set_title(title, loc="left", fontweight="bold")
    ax.grid(axis="x", color="#e8e8e8", linewidth=0.8)
    for row, yy in zip(rows, y):
        ax.text(
            1.035,
            yy,
            f"{row['point']:.3f} [{row['lower']:.3f}, {row['upper']:.3f}]",
            va="center",
            ha="left",
            fontsize=7,
            color="#333333",
        )
    ax.invert_yaxis()


def _plot_delta_panel(ax, val_rows, test_rows):
    metrics = [row["metric"] for row in val_rows]
    val = np.array([row["point"] for row in val_rows])
    test = np.array([row["point"] for row in test_rows])
    x = np.arange(len(metrics))
    width = 0.34
    ax.bar(x - width / 2, val, width=width, color="#9ecae1", label="Validation")
    ax.bar(x + width / 2, test, width=width, color="#fdae6b", label="Independent test")
    ax.set_xticks(x)
    ax.set_xticklabels([METRIC_LABELS[m] for m in metrics], rotation=35, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Metric value")
    ax.set_title("b  Fixed-threshold transfer from validation to test", loc="left", fontweight="bold")
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 1.03), ncol=2)
    ax.grid(axis="y", color="#eeeeee", linewidth=0.8)


def _plot_confusion_panel(ax, test_threshold):
    matrix = np.array([
        [test_threshold["tp"], test_threshold["fn"]],
        [test_threshold["fp"], test_threshold["tn"]],
    ])
    im = ax.imshow(matrix, cmap="Blues", vmin=0, vmax=max(1, matrix.max()))
    labels = [["TP", "FN"], ["FP", "TN"]]
    for i in range(2):
        for j in range(2):
            color = "white" if matrix[i, j] > matrix.max() * 0.55 else "#1f1f1f"
            ax.text(j, i, f"{labels[i][j]}\n{matrix[i, j]}", ha="center", va="center", color=color, fontweight="bold")
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Pred +", "Pred -"])
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["True +", "True -"])
    ax.set_title("c  Test confusion matrix at threshold 0.30", loc="left", fontweight="bold")
    ax.tick_params(length=0)
    return im


def build_figure(val_bootstrap, test_bootstrap, test_threshold, out_base):
    _configure_matplotlib()
    val_rows = metric_rows_from_bootstrap(val_bootstrap)
    test_rows = metric_rows_from_bootstrap(test_bootstrap)

    fig = plt.figure(figsize=(7.8, 6.3), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, height_ratios=[1.15, 1.0], width_ratios=[1.35, 1.0])
    ax_ci = fig.add_subplot(grid[0, :])
    ax_delta = fig.add_subplot(grid[1, 0])
    ax_conf = fig.add_subplot(grid[1, 1])

    _plot_ci_panel(ax_ci, test_rows, "a  Independent LUNA16 subset test performance", "#de6e56")
    _plot_delta_panel(ax_delta, val_rows, test_rows)
    _plot_confusion_panel(ax_conf, test_threshold)
    fig.suptitle("FPRED branch validation on LUNA16 subset candidates", x=0.02, y=1.02, ha="left", fontweight="bold", fontsize=11)
    save_publication_figure(fig, out_base)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Create a publication-style FPRED validation figure.")
    parser.add_argument("--val-bootstrap", required=True)
    parser.add_argument("--test-bootstrap", required=True)
    parser.add_argument("--test-threshold-metrics", required=True)
    parser.add_argument("--threshold", type=float, default=0.3)
    parser.add_argument("--out-base", required=True)
    args = parser.parse_args()

    val_bootstrap = load_json(args.val_bootstrap)
    test_bootstrap = load_json(args.test_bootstrap)
    with Path(args.test_threshold_metrics).open("r", encoding="utf-8-sig") as f:
        import csv

        rows = list(csv.DictReader(f))
    threshold_rows = [row for row in rows if abs(float(row["threshold"]) - args.threshold) < 1e-9]
    if not threshold_rows:
        raise ValueError(f"threshold {args.threshold} not found in {args.test_threshold_metrics}")
    test_threshold = {key: int(float(value)) if key in {"tp", "fp", "tn", "fn"} else float(value) for key, value in threshold_rows[0].items()}
    build_figure(val_bootstrap, test_bootstrap, test_threshold, args.out_base)


if __name__ == "__main__":
    main()
