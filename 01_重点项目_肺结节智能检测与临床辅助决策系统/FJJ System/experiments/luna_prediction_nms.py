import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PredictionRow:
    seriesuid: str
    x: float
    y: float
    z: float
    probability: float


def distance(left, right):
    return math.sqrt((left.x - right.x) ** 2 + (left.y - right.y) ** 2 + (left.z - right.z) ** 2)


def nms_predictions(rows, radius_mm):
    by_series = {}
    for row in rows:
        by_series.setdefault(row.seriesuid, []).append(row)

    kept = []
    for seriesuid in sorted(by_series):
        series_rows = sorted(by_series[seriesuid], key=lambda row: row.probability, reverse=True)
        series_kept = []
        for row in series_rows:
            if all(distance(row, selected) > radius_mm for selected in series_kept):
                series_kept.append(row)
        kept.extend(series_kept)
    return sorted(kept, key=lambda row: row.probability, reverse=True)


def read_predictions(path):
    rows = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(
                PredictionRow(
                    row["seriesuid"],
                    float(row["coordX"]),
                    float(row["coordY"]),
                    float(row["coordZ"]),
                    float(row["probability"]),
                )
            )
    return rows


def write_predictions(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["seriesuid", "coordX", "coordY", "coordZ", "probability"])
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "seriesuid": row.seriesuid,
                "coordX": row.x,
                "coordY": row.y,
                "coordZ": row.z,
                "probability": row.probability,
            })


def main():
    parser = argparse.ArgumentParser(description="Apply per-series 3D NMS to LUNA-style prediction CSV.")
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--radius-mm", type=float, required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()

    rows = read_predictions(args.predictions)
    kept = nms_predictions(rows, args.radius_mm)
    write_predictions(args.out, kept)
    summary = {
        "input_count": len(rows),
        "kept_count": len(kept),
        "suppressed_count": len(rows) - len(kept),
        "series_count": len({row.seriesuid for row in rows}),
        "radius_mm": args.radius_mm,
        "out": args.out,
    }
    Path(args.summary).parent.mkdir(parents=True, exist_ok=True)
    Path(args.summary).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
