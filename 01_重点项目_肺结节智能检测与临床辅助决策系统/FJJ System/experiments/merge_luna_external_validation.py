import argparse
import csv
import json
from pathlib import Path


PREDICTION_FIELDS = ["seriesuid", "coordX", "coordY", "coordZ", "probability"]


def read_seriesuids(path):
    with Path(path).open("r", encoding="utf-8-sig") as f:
        return [line.strip() for line in f if line.strip()]


def read_predictions(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = sorted(set(PREDICTION_FIELDS) - set(reader.fieldnames or []))
        if missing:
            raise ValueError(f"{path} missing columns: {missing}")
        return [{field: row[field] for field in PREDICTION_FIELDS} for row in reader]


def read_annotation_counts(path, seriesuids):
    wanted = set(seriesuids)
    count = 0
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("seriesuid") in wanted:
                count += 1
    return count


def write_seriesuids(path, seriesuids):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(seriesuids) + "\n", encoding="utf-8")


def write_predictions(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PREDICTION_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def merge_inputs(inputs):
    seen_series = set()
    pooled_seriesuids = []
    pooled_predictions = []
    subset_reports = []

    for item in inputs:
        label = item["label"]
        seriesuids = read_seriesuids(item["seriesuids"])
        overlap = sorted(seen_series & set(seriesuids))
        if overlap:
            raise ValueError(f"Series overlap detected for {label}: {overlap[:5]}")
        seen_series.update(seriesuids)
        pooled_seriesuids.extend(seriesuids)

        rows = read_predictions(item["predictions"])
        unknown = sorted({row["seriesuid"] for row in rows} - set(seriesuids))
        if unknown:
            raise ValueError(f"Predictions for {label} include series not in seriesuid file: {unknown[:5]}")
        pooled_predictions.extend(rows)
        subset_reports.append({
            "label": label,
            "series_count": len(seriesuids),
            "prediction_count": len(rows),
            "seriesuids": str(item["seriesuids"]),
            "predictions": str(item["predictions"]),
        })

    return pooled_seriesuids, pooled_predictions, subset_reports


def build_report(inputs, pooled_seriesuids, pooled_predictions, annotations=None):
    report = {
        "subset_count": len(inputs),
        "series_count": len(pooled_seriesuids),
        "prediction_count": len(pooled_predictions),
        "subsets": inputs,
    }
    if annotations:
        report["annotation_count"] = read_annotation_counts(annotations, pooled_seriesuids)
        report["annotations"] = str(annotations)
    return report


def parse_input(value):
    parts = value.split("|")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("Expected LABEL|SERIESUIDS_TXT|PREDICTIONS_CSV")
    label, seriesuids, predictions = parts
    return {"label": label, "seriesuids": Path(seriesuids), "predictions": Path(predictions)}


def main():
    parser = argparse.ArgumentParser(description="Merge non-overlapping LUNA16 external validation subsets.")
    parser.add_argument(
        "--input",
        action="append",
        type=parse_input,
        required=True,
        help="LABEL|SERIESUIDS_TXT|PREDICTIONS_CSV. May be repeated.",
    )
    parser.add_argument("--annotations", help="Optional global LUNA16 annotations.csv for pooled annotation count.")
    parser.add_argument("--out-seriesuids", required=True)
    parser.add_argument("--out-predictions", required=True)
    parser.add_argument("--out-report", required=True)
    args = parser.parse_args()

    pooled_seriesuids, pooled_predictions, subset_reports = merge_inputs(args.input)
    write_seriesuids(args.out_seriesuids, pooled_seriesuids)
    write_predictions(args.out_predictions, pooled_predictions)
    report = build_report(subset_reports, pooled_seriesuids, pooled_predictions, Path(args.annotations) if args.annotations else None)
    Path(args.out_report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
