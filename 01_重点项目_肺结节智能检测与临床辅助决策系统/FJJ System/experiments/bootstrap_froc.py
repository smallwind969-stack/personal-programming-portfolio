import argparse
import csv
import json
import random
from pathlib import Path

try:
    from froc_eval import FP_RATES, Annotation, Prediction, evaluate_froc, read_annotations, read_predictions, read_seriesuids
except ImportError:
    from experiments.froc_eval import FP_RATES, Annotation, Prediction, evaluate_froc, read_annotations, read_predictions, read_seriesuids


def percentile_interval(values, alpha=0.05):
    ordered = sorted(values)
    if not ordered:
        return None, None
    lower_index = int((alpha / 2.0) * (len(ordered) - 1))
    upper_index = int((1.0 - alpha / 2.0) * (len(ordered) - 1))
    return ordered[lower_index], ordered[upper_index]


def group_by_series(rows):
    groups = {}
    for row in rows:
        groups.setdefault(row.seriesuid, []).append(row)
    return groups


def clone_annotation(annotation, seriesuid):
    return Annotation(seriesuid, annotation.x, annotation.y, annotation.z, annotation.diameter_mm)


def clone_prediction(prediction, seriesuid):
    return Prediction(seriesuid, prediction.x, prediction.y, prediction.z, prediction.probability)


def resample_series(annotations, predictions, seriesuids, rng):
    ann_by_series = group_by_series(annotations)
    pred_by_series = group_by_series(predictions)
    sampled_annotations = []
    sampled_predictions = []
    sampled_seriesuids = []
    for index in range(len(seriesuids)):
        source = rng.choice(seriesuids)
        sampled_id = f"{source}__boot{index}"
        sampled_seriesuids.append(sampled_id)
        sampled_annotations.extend(clone_annotation(item, sampled_id) for item in ann_by_series.get(source, []))
        sampled_predictions.extend(clone_prediction(item, sampled_id) for item in pred_by_series.get(source, []))
    return sampled_annotations, sampled_predictions, sampled_seriesuids


def summarize_froc(annotations, predictions, seriesuids):
    _points, sensitivities, cpm = evaluate_froc(annotations, predictions, seriesuids)
    values = {"cpm": cpm}
    for rate in FP_RATES:
        values[f"sensitivity_at_{rate}_fp_per_scan"] = sensitivities[rate]
    return values


def bootstrap_froc(annotations, predictions, seriesuids, n_boot=1000, seed=20260615):
    rng = random.Random(seed)
    point = summarize_froc(annotations, predictions, seriesuids)
    samples = {key: [] for key in point}
    accepted = 0
    for _ in range(n_boot):
        sample_annotations, sample_predictions, sample_seriesuids = resample_series(annotations, predictions, seriesuids, rng)
        if not sample_annotations:
            continue
        values = summarize_froc(sample_annotations, sample_predictions, sample_seriesuids)
        for key, value in values.items():
            samples[key].append(value)
        accepted += 1

    ci95 = {}
    for key, values in samples.items():
        lower, upper = percentile_interval(values, alpha=0.05)
        ci95[key] = {"lower": lower, "upper": upper}
    return {
        "n_boot_requested": n_boot,
        "n_boot_accepted": accepted,
        "seed": seed,
        "series_count": len(seriesuids),
        "annotation_count": len(annotations),
        "prediction_count": len(predictions),
        "point": point,
        "ci95": ci95,
    }


def write_ci_csv(path, summary):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "point", "ci95_lower", "ci95_upper"])
        writer.writeheader()
        for metric, point in summary["point"].items():
            ci = summary["ci95"][metric]
            writer.writerow({"metric": metric, "point": point, "ci95_lower": ci["lower"], "ci95_upper": ci["upper"]})


def main():
    parser = argparse.ArgumentParser(description="Series-level bootstrap confidence intervals for LUNA16-style FROC/CPM.")
    parser.add_argument("--annotations", required=True)
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--seriesuids", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--n-boot", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260615)
    args = parser.parse_args()

    annotations = read_annotations(args.annotations)
    predictions = read_predictions(args.predictions)
    seriesuids = read_seriesuids(args.seriesuids, annotations, predictions)
    seriesuid_set = set(seriesuids)
    annotations = [item for item in annotations if item.seriesuid in seriesuid_set]
    predictions = [item for item in predictions if item.seriesuid in seriesuid_set]
    summary = bootstrap_froc(annotations, predictions, seriesuids, n_boot=args.n_boot, seed=args.seed)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "bootstrap_froc_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_ci_csv(out_dir / "bootstrap_froc_ci95.csv", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
