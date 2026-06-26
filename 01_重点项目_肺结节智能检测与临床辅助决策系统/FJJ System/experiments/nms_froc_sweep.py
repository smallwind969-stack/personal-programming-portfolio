import argparse
import csv
from pathlib import Path

try:
    from froc_eval import evaluate_froc, filter_to_seriesuids, read_annotations, read_predictions as read_froc_predictions, read_seriesuids, write_points, write_summary
    from luna_prediction_nms import nms_predictions, read_predictions as read_nms_predictions, write_predictions as write_nms_predictions
except ImportError:
    from experiments.froc_eval import evaluate_froc, filter_to_seriesuids, read_annotations, read_predictions as read_froc_predictions, read_seriesuids, write_points, write_summary
    from experiments.luna_prediction_nms import nms_predictions, read_predictions as read_nms_predictions, write_predictions as write_nms_predictions


FP_RATES = [0.125, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0]


def parse_radii(value):
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def count_rows_for_series(rows, seriesuid_set):
    return sum(1 for row in rows if row.seriesuid in seriesuid_set)


def filter_rows_for_series(rows, seriesuid_set):
    return [row for row in rows if row.seriesuid in seriesuid_set]


def write_sweep_summary(path, rows):
    fieldnames = ["radius_mm", "prediction_count", "suppressed_count"] + [f"sensitivity_at_{rate}_fp_per_scan" for rate in FP_RATES] + ["cpm"]
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_sweep(predictions_path, annotations_path, seriesuids_path, out_dir, radii):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    original_rows = read_nms_predictions(predictions_path)
    annotations = read_annotations(annotations_path)
    original_froc_predictions = read_froc_predictions(predictions_path)
    seriesuids = read_seriesuids(seriesuids_path, annotations, original_froc_predictions)
    seriesuid_set = set(seriesuids)
    split_original_count = count_rows_for_series(original_rows, seriesuid_set)
    filtered_annotations, _ = filter_to_seriesuids(annotations, original_froc_predictions, seriesuids)
    summary_rows = []

    for radius in radii:
        radius_dir = out_dir / f"radius_{radius:g}"
        radius_dir.mkdir(parents=True, exist_ok=True)
        if radius <= 0:
            kept = original_rows
        else:
            kept = nms_predictions(original_rows, radius)
        kept_for_split = filter_rows_for_series(kept, seriesuid_set)
        pred_path = radius_dir / "predictions.csv"
        write_nms_predictions(pred_path, kept_for_split)
        froc_predictions = read_froc_predictions(pred_path)
        _filtered_annotations, filtered_predictions = filter_to_seriesuids(annotations, froc_predictions, seriesuids)
        points, sensitivities, cpm = evaluate_froc(filtered_annotations, filtered_predictions, seriesuids)
        write_points(radius_dir / "froc_points.csv", points)
        write_summary(radius_dir / "froc_summary.csv", seriesuids, filtered_annotations, filtered_predictions, sensitivities, cpm)
        row = {
            "radius_mm": radius,
            "prediction_count": len(kept_for_split),
            "suppressed_count": split_original_count - len(kept_for_split),
            "cpm": cpm,
        }
        for rate in FP_RATES:
            row[f"sensitivity_at_{rate}_fp_per_scan"] = sensitivities[rate]
        summary_rows.append(row)
    write_sweep_summary(out_dir / "nms_froc_sweep_summary.csv", summary_rows)
    return summary_rows


def main():
    parser = argparse.ArgumentParser(description="Run NMS radius sweep and FROC evaluation for LUNA-style predictions.")
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--annotations", required=True)
    parser.add_argument("--seriesuids", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--radii", default="0,5,10,15,20,30")
    args = parser.parse_args()

    rows = run_sweep(args.predictions, args.annotations, args.seriesuids, args.out_dir, parse_radii(args.radii))
    for row in rows:
        print(f"radius={row['radius_mm']} cpm={row['cpm']:.6f} predictions={row['prediction_count']}")


if __name__ == "__main__":
    main()
