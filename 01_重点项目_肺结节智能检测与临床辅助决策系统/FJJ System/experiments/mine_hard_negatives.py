import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Annotation:
    seriesuid: str
    x: float
    y: float
    z: float
    diameter_mm: float


@dataclass(frozen=True)
class Prediction:
    seriesuid: str
    x: float
    y: float
    z: float
    probability: float


def read_seriesuids(path):
    with Path(path).open("r", encoding="utf-8-sig") as f:
        return {line.strip() for line in f if line.strip()}


def read_annotations(path):
    rows = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(
                Annotation(
                    row["seriesuid"],
                    float(row["coordX"]),
                    float(row["coordY"]),
                    float(row["coordZ"]),
                    float(row["diameter_mm"]),
                )
            )
    return rows


def read_predictions(path):
    rows = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(
                Prediction(
                    row["seriesuid"],
                    float(row["coordX"]),
                    float(row["coordY"]),
                    float(row["coordZ"]),
                    float(row["probability"]),
                )
            )
    return rows


def distance(annotation, prediction):
    return math.sqrt(
        (annotation.x - prediction.x) ** 2
        + (annotation.y - prediction.y) ** 2
        + (annotation.z - prediction.z) ** 2
    )


def is_true_positive(prediction, annotations):
    for annotation in annotations:
        if annotation.seriesuid != prediction.seriesuid:
            continue
        if distance(annotation, prediction) <= annotation.diameter_mm / 2.0:
            return True
    return False


def select_hard_negatives(predictions, annotations, allowed_series, min_probability, max_total, max_per_series):
    by_series_count = {}
    selected = []
    candidates = sorted(
        (row for row in predictions if row.seriesuid in allowed_series and row.probability >= min_probability),
        key=lambda row: row.probability,
        reverse=True,
    )
    for row in candidates:
        if len(selected) >= max_total:
            break
        if by_series_count.get(row.seriesuid, 0) >= max_per_series:
            continue
        if is_true_positive(row, annotations):
            continue
        selected.append(
            {
                "seriesuid": row.seriesuid,
                "coordX": row.x,
                "coordY": row.y,
                "coordZ": row.z,
                "class": "0",
                "split": "train_hard_negative",
                "probability": row.probability,
            }
        )
        by_series_count[row.seriesuid] = by_series_count.get(row.seriesuid, 0) + 1
    return selected


def write_candidates(path, rows):
    fieldnames = ["seriesuid", "coordX", "coordY", "coordZ", "class", "split", "probability"]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([{key: row.get(key, "") for key in fieldnames} for row in rows])


def summarize(selected, predictions, annotations, allowed_series, min_probability, max_total, max_per_series, out):
    return {
        "allowed_series_count": len(allowed_series),
        "input_prediction_count": len(predictions),
        "annotation_count": len([row for row in annotations if row.seriesuid in allowed_series]),
        "min_probability": min_probability,
        "max_total": max_total,
        "max_per_series": max_per_series,
        "selected_count": len(selected),
        "selected_series_count": len({row["seriesuid"] for row in selected}),
        "max_selected_probability": max((row["probability"] for row in selected), default=None),
        "min_selected_probability": min((row["probability"] for row in selected), default=None),
        "out": str(out),
    }


def main():
    parser = argparse.ArgumentParser(description="Mine high-score false positives for FPRED hard-negative retraining.")
    parser.add_argument("--predictions", default=str(ROOT / "docs/world_frontier/luna16/subset0_full_candidates_stream/fpred_candidates_v2_predictions.csv"))
    parser.add_argument("--annotations", default=str(ROOT / "data/luna16/annotations.csv"))
    parser.add_argument("--seriesuids", default=str(ROOT / "docs/world_frontier/luna16/subset0_full_candidates_stream/calibration_split/calibration_seriesuids.txt"))
    parser.add_argument("--out", default=str(ROOT / "docs/world_frontier/luna16/hard_negative_mining/subset0_calibration_hard_negatives.csv"))
    parser.add_argument("--summary", default=str(ROOT / "docs/world_frontier/luna16/hard_negative_mining/hard_negative_summary.json"))
    parser.add_argument("--min-probability", type=float, default=0.5)
    parser.add_argument("--max-total", type=int, default=512)
    parser.add_argument("--max-per-series", type=int, default=16)
    args = parser.parse_args()

    allowed_series = read_seriesuids(args.seriesuids)
    predictions = read_predictions(args.predictions)
    annotations = read_annotations(args.annotations)
    selected = select_hard_negatives(
        predictions,
        annotations,
        allowed_series,
        args.min_probability,
        args.max_total,
        args.max_per_series,
    )
    out = Path(args.out)
    write_candidates(out, selected)
    summary = summarize(
        selected,
        predictions,
        annotations,
        allowed_series,
        args.min_probability,
        args.max_total,
        args.max_per_series,
        out,
    )
    summary_path = Path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
