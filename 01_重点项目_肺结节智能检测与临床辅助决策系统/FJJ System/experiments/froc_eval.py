import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path


FP_RATES = [0.125, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0]


@dataclass
class Annotation:
    seriesuid: str
    x: float
    y: float
    z: float
    diameter_mm: float


@dataclass
class Prediction:
    seriesuid: str
    x: float
    y: float
    z: float
    probability: float


def _float(row, key):
    return float(row[key])


def read_annotations(path):
    annotations = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            annotations.append(
                Annotation(
                    row["seriesuid"],
                    _float(row, "coordX"),
                    _float(row, "coordY"),
                    _float(row, "coordZ"),
                    _float(row, "diameter_mm"),
                )
            )
    return annotations


def read_predictions(path):
    predictions = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            predictions.append(
                Prediction(
                    row["seriesuid"],
                    _float(row, "coordX"),
                    _float(row, "coordY"),
                    _float(row, "coordZ"),
                    _float(row, "probability"),
                )
            )
    return predictions


def read_seriesuids(path, annotations, predictions):
    if path:
        with Path(path).open("r", encoding="utf-8-sig") as f:
            return sorted({line.strip() for line in f if line.strip()})
    return sorted({a.seriesuid for a in annotations} | {p.seriesuid for p in predictions})


def distance(a, p):
    return math.sqrt((a.x - p.x) ** 2 + (a.y - p.y) ** 2 + (a.z - p.z) ** 2)


def evaluate_at_threshold(annotations, predictions, seriesuids, threshold):
    active_predictions = [p for p in predictions if p.probability >= threshold]
    by_series = {}
    for ann in annotations:
        by_series.setdefault(ann.seriesuid, []).append(ann)

    matched = set()
    tp = 0
    fp = 0
    # High-confidence predictions claim nodules first, which mirrors detector use.
    for pred in sorted(active_predictions, key=lambda p: p.probability, reverse=True):
        candidates = []
        for idx, ann in enumerate(by_series.get(pred.seriesuid, [])):
            ann_key = (pred.seriesuid, idx)
            if ann_key in matched:
                continue
            radius = max(ann.diameter_mm / 2.0, 1e-6)
            d = distance(ann, pred)
            if d <= radius:
                candidates.append((d, ann_key))
        if candidates:
            _d, key = min(candidates, key=lambda item: item[0])
            matched.add(key)
            tp += 1
        else:
            fp += 1

    n_ann = len(annotations)
    n_scans = max(len(seriesuids), 1)
    sensitivity = tp / n_ann if n_ann else 0.0
    fp_per_scan = fp / n_scans
    return {
        "threshold": threshold,
        "tp": tp,
        "fp": fp,
        "fn": n_ann - tp,
        "sensitivity": sensitivity,
        "fp_per_scan": fp_per_scan,
        "prediction_count": len(active_predictions),
    }


def interpolate_sensitivity(points, fp_rate):
    eligible = [p for p in points if p["fp_per_scan"] <= fp_rate]
    if not eligible:
        return 0.0
    return max(p["sensitivity"] for p in eligible)


def filter_to_seriesuids(annotations, predictions, seriesuids):
    seriesuid_set = set(seriesuids)
    return (
        [a for a in annotations if a.seriesuid in seriesuid_set],
        [p for p in predictions if p.seriesuid in seriesuid_set],
    )


def evaluate_froc(annotations, predictions, seriesuids):
    annotations, predictions = filter_to_seriesuids(annotations, predictions, seriesuids)
    by_series = {}
    for ann in annotations:
        by_series.setdefault(ann.seriesuid, []).append(ann)
    matched = set()
    tp = fp = 0
    points = []
    n_ann = len(annotations)
    n_scans = max(len(seriesuids), 1)
    ordered = sorted(predictions, key=lambda p: p.probability, reverse=True)
    index = 0
    while index < len(ordered):
        threshold = ordered[index].probability
        while index < len(ordered) and ordered[index].probability == threshold:
            pred = ordered[index]
            candidates = []
            for ann_idx, ann in enumerate(by_series.get(pred.seriesuid, [])):
                ann_key = (pred.seriesuid, ann_idx)
                if ann_key in matched:
                    continue
                radius = max(ann.diameter_mm / 2.0, 1e-6)
                d = distance(ann, pred)
                if d <= radius:
                    candidates.append((d, ann_key))
            if candidates:
                _d, key = min(candidates, key=lambda item: item[0])
                matched.add(key)
                tp += 1
            else:
                fp += 1
            index += 1
        points.append({
            "threshold": threshold,
            "tp": tp,
            "fp": fp,
            "fn": n_ann - tp,
            "sensitivity": tp / n_ann if n_ann else 0.0,
            "fp_per_scan": fp / n_scans,
            "prediction_count": tp + fp,
        })
    if not points or points[-1]["threshold"] != 0.0:
        points.append({
            "threshold": 0.0,
            "tp": tp,
            "fp": fp,
            "fn": n_ann - tp,
            "sensitivity": tp / n_ann if n_ann else 0.0,
            "fp_per_scan": fp / n_scans,
            "prediction_count": tp + fp,
        })
    sensitivities = {rate: interpolate_sensitivity(points, rate) for rate in FP_RATES}
    cpm = sum(sensitivities.values()) / len(FP_RATES)
    return points, sensitivities, cpm


def evaluate_froc_slow(annotations, predictions, seriesuids):
    annotations, predictions = filter_to_seriesuids(annotations, predictions, seriesuids)
    thresholds = sorted({p.probability for p in predictions}, reverse=True)
    if 0.0 not in thresholds:
        thresholds.append(0.0)
    points = [evaluate_at_threshold(annotations, predictions, seriesuids, t) for t in thresholds]
    sensitivities = {rate: interpolate_sensitivity(points, rate) for rate in FP_RATES}
    cpm = sum(sensitivities.values()) / len(FP_RATES)
    return points, sensitivities, cpm


def write_points(path, rows):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["threshold", "tp", "fp", "fn", "sensitivity", "fp_per_scan", "prediction_count"],
        )
        writer.writeheader()
        writer.writerows(rows)


def write_summary(path, seriesuids, annotations, predictions, sensitivities, cpm):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        writer.writerow(["scan_count", len(seriesuids)])
        writer.writerow(["annotation_count", len(annotations)])
        writer.writerow(["prediction_count", len(predictions)])
        for rate in FP_RATES:
            writer.writerow([f"sensitivity_at_{rate}_fp_per_scan", round(sensitivities[rate], 6)])
        writer.writerow(["cpm", round(cpm, 6)])


def main():
    parser = argparse.ArgumentParser(description="Evaluate lung nodule detections with LUNA16-style FROC/CPM.")
    parser.add_argument("--annotations", required=True, help="CSV with seriesuid,coordX,coordY,coordZ,diameter_mm")
    parser.add_argument("--predictions", required=True, help="CSV with seriesuid,coordX,coordY,coordZ,probability")
    parser.add_argument("--seriesuids", help="Optional text file with one scan id per line")
    parser.add_argument("--out-dir", default="docs/world_frontier/froc_eval")
    args = parser.parse_args()

    annotations = read_annotations(args.annotations)
    predictions = read_predictions(args.predictions)
    seriesuids = read_seriesuids(args.seriesuids, annotations, predictions)
    filtered_annotations, filtered_predictions = filter_to_seriesuids(annotations, predictions, seriesuids)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    points, sensitivities, cpm = evaluate_froc(filtered_annotations, filtered_predictions, seriesuids)
    write_points(out_dir / "froc_points.csv", points)
    write_summary(out_dir / "froc_summary.csv", seriesuids, filtered_annotations, filtered_predictions, sensitivities, cpm)
    print(f"CPM={cpm:.6f}")
    print(out_dir)


if __name__ == "__main__":
    main()
