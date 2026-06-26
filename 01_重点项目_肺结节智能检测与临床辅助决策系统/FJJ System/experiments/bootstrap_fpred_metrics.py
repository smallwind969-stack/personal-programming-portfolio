import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

try:
    from evaluate_fpred_predictions import auc_trapezoid, confusion, read_predictions, roc_points
except ImportError:
    from experiments.evaluate_fpred_predictions import auc_trapezoid, confusion, read_predictions, roc_points


METRIC_NAMES = ["auc", "accuracy", "precision", "sensitivity", "specificity", "f1"]


def percentile_interval(values, alpha=0.05):
    if not values:
        return None, None
    ordered = sorted(values)
    lower_index = int((alpha / 2.0) * (len(ordered) - 1))
    upper_index = int((1.0 - alpha / 2.0) * (len(ordered) - 1))
    return ordered[lower_index], ordered[upper_index]


def metric_point(rows, threshold):
    metrics = confusion(rows, threshold)
    labels = {row["label"] for row in rows}
    metrics["auc"] = auc_trapezoid(roc_points(rows)) if labels == {0, 1} else None
    return {name: metrics.get(name) for name in METRIC_NAMES}


def _series_groups(rows):
    groups = defaultdict(list)
    for index, row in enumerate(rows):
        seriesuid = row.get("seriesuid") or f"candidate-{index}"
        groups[seriesuid].append(row)
    return list(groups.values())


def _resample_rows(rows, rng, group_by_series):
    if group_by_series:
        groups = _series_groups(rows)
        sample = []
        for _ in range(len(groups)):
            sample.extend(rng.choice(groups))
        return sample
    return [rng.choice(rows) for _ in range(len(rows))]


def bootstrap_metrics(rows, threshold, n_boot=2000, seed=20260614, group_by_series=True):
    if not rows:
        raise ValueError("bootstrap requires at least one prediction row")

    use_series = group_by_series and any(row.get("seriesuid") for row in rows)
    rng = random.Random(seed)
    point = metric_point(rows, threshold)
    samples = {name: [] for name in METRIC_NAMES}
    accepted = 0

    for _ in range(n_boot):
        sample = _resample_rows(rows, rng, use_series)
        labels = {row["label"] for row in sample}
        if labels != {0, 1}:
            continue
        sample_metrics = metric_point(sample, threshold)
        for name in METRIC_NAMES:
            value = sample_metrics[name]
            if value is not None:
                samples[name].append(value)
        accepted += 1

    ci95 = {}
    for name in METRIC_NAMES:
        lower, upper = percentile_interval(samples[name], alpha=0.05)
        ci95[name] = {"lower": lower, "upper": upper}

    return {
        "threshold": threshold,
        "n_boot_requested": n_boot,
        "n_boot_accepted": accepted,
        "seed": seed,
        "resampling_unit": "seriesuid" if use_series else "candidate",
        "prediction_count": len(rows),
        "positive_count": sum(1 for row in rows if row["label"] == 1),
        "negative_count": sum(1 for row in rows if row["label"] == 0),
        "point": point,
        "ci95": ci95,
    }


def write_ci_csv(path, summary):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "point", "ci95_lower", "ci95_upper"])
        writer.writeheader()
        for name in METRIC_NAMES:
            ci = summary["ci95"][name]
            writer.writerow({
                "metric": name,
                "point": summary["point"][name],
                "ci95_lower": ci["lower"],
                "ci95_upper": ci["upper"],
            })


def main():
    parser = argparse.ArgumentParser(description="Bootstrap FPRED metrics with fixed-threshold confidence intervals.")
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--threshold", type=float, default=0.3)
    parser.add_argument("--n-boot", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260614)
    parser.add_argument("--candidate-level", action="store_true", help="Disable seriesuid-level resampling.")
    args = parser.parse_args()

    rows = read_predictions(args.predictions)
    summary = bootstrap_metrics(
        rows,
        threshold=args.threshold,
        n_boot=args.n_boot,
        seed=args.seed,
        group_by_series=not args.candidate_level,
    )
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "bootstrap_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_ci_csv(out_dir / "bootstrap_ci95.csv", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
