import argparse
import csv
import json
from pathlib import Path


REQUIRED_COLUMNS = ["seriesuid", "coordX", "coordY", "coordZ", "probability"]


def read_series(path):
    if not path:
        return None
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if "seriesuid" in (reader.fieldnames or []):
            return {row["seriesuid"] for row in reader if row.get("seriesuid")}
    with Path(path).open("r", encoding="utf-8-sig") as f:
        return {line.strip() for line in f if line.strip()}


def validate_submission(path, known_series=None):
    path = Path(path)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    columns = reader.fieldnames or []
    errors = []
    warnings = []
    missing = [col for col in REQUIRED_COLUMNS if col not in columns]
    if missing:
        errors.append(f"missing required columns: {missing}")

    unknown_series = set()
    probability_out_of_range = 0
    coordinate_errors = 0
    series_counts = {}

    for idx, row in enumerate(rows, start=2):
        sid = row.get("seriesuid", "")
        if not sid:
            errors.append(f"row {idx}: empty seriesuid")
        else:
            series_counts[sid] = series_counts.get(sid, 0) + 1
            if known_series is not None and sid not in known_series:
                unknown_series.add(sid)
        for col in ("coordX", "coordY", "coordZ"):
            try:
                float(row.get(col, ""))
            except ValueError:
                coordinate_errors += 1
        try:
            prob = float(row.get("probability", ""))
            if prob < 0 or prob > 1:
                probability_out_of_range += 1
        except ValueError:
            probability_out_of_range += 1

    if coordinate_errors:
        errors.append(f"invalid coordinate values: {coordinate_errors}")
    if probability_out_of_range:
        errors.append(f"probability outside [0,1] or invalid: {probability_out_of_range}")
    if unknown_series:
        warnings.append(f"unknown seriesuid count: {len(unknown_series)}")

    empty = len(rows) == 0
    if empty:
        warnings.append("submission has no prediction rows")

    return {
        "path": str(path),
        "row_count": len(rows),
        "series_count": len(series_counts),
        "required_columns": REQUIRED_COLUMNS,
        "columns": columns,
        "errors": errors,
        "warnings": warnings,
        "valid": not errors,
        "max_predictions_per_series": max(series_counts.values()) if series_counts else 0,
    }


def main():
    parser = argparse.ArgumentParser(description="Validate LUNA16-style submission CSV.")
    parser.add_argument("--submission", required=True)
    parser.add_argument("--known-series")
    parser.add_argument("--out", default="docs/world_frontier/luna16/submission_validation.json")
    args = parser.parse_args()

    report = validate_submission(args.submission, read_series(args.known_series))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
