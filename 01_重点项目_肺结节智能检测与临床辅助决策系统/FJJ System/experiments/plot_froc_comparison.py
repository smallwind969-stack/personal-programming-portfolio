import argparse
import csv
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt


FP_RATES = [0.125, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0]


mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"],
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
    "axes.spines.right": False,
    "axes.spines.top": False,
    "legend.frameon": False,
})


def read_summary(path):
    data = {}
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            data[row["metric"]] = float(row["value"])
    return data


def paired_sensitivities(left, right, rates=FP_RATES):
    rows = []
    for rate in rates:
        key = f"sensitivity_at_{rate}_fp_per_scan"
        rows.append({"fp_per_scan": rate, "left": left[key], "right": right[key]})
    return rows


def plot_comparison(sampled, full, out, left_label, right_label):
    rows = paired_sensitivities(sampled, full)
    rates = [row["fp_per_scan"] for row in rows]
    left = [row["left"] for row in rows]
    right = [row["right"] for row in rows]

    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.plot(rates, left, marker="o", linewidth=2, color="#9ecae1", label=f"{left_label} CPM={sampled['cpm']:.4f}")
    ax.plot(rates, right, marker="o", linewidth=2, color="#de6e56", label=f"{right_label} CPM={full['cpm']:.4f}")
    ax.set_xscale("log", base=2)
    ax.set_xticks(rates)
    ax.set_xticklabels([str(rate) for rate in rates])
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("False positives per scan")
    ax.set_ylabel("Sensitivity")
    ax.set_title("FPRED FROC bridge: sampled vs full candidates_V2")
    ax.grid(axis="y", color="#eeeeee")
    ax.legend(loc="lower right")

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        fig.savefig(out.with_suffix(f".{ext}"), dpi=600 if ext == "png" else None, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Compare two FROC summary CSV files.")
    parser.add_argument("--sampled-summary", required=True)
    parser.add_argument("--full-summary", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--sampled-label", default="sampled candidates")
    parser.add_argument("--full-label", default="full candidates_V2")
    args = parser.parse_args()

    sampled = read_summary(args.sampled_summary)
    full = read_summary(args.full_summary)
    plot_comparison(sampled, full, args.out, args.sampled_label, args.full_label)
    print(Path(args.out).with_suffix(".png"))


if __name__ == "__main__":
    main()
