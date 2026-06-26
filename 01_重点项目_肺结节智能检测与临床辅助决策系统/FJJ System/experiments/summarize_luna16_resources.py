import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "luna16"
OUT = ROOT / "docs" / "world_frontier" / "luna16"


def count_csv(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return reader.fieldnames or [], rows


def describe_annotations(path):
    columns, rows = count_csv(path)
    series = {row["seriesuid"] for row in rows if row.get("seriesuid")}
    diameters = [float(row["diameter_mm"]) for row in rows if row.get("diameter_mm")]
    return {
        "path": str(path),
        "columns": columns,
        "row_count": len(rows),
        "series_count": len(series),
        "diameter_min_mm": min(diameters) if diameters else None,
        "diameter_max_mm": max(diameters) if diameters else None,
    }


def describe_seriesuids(path):
    with Path(path).open("r", encoding="utf-8-sig") as f:
        series = [line.strip() for line in f if line.strip()]
    return {"path": str(path), "series_count": len(series), "first_seriesuid": series[0] if series else None}


def describe_candidates(path):
    columns, rows = count_csv(path)
    series = set()
    positive = 0
    negative = 0
    for row in rows:
        if row.get("seriesuid"):
            series.add(row["seriesuid"])
        klass = str(row.get("class", "")).strip()
        if klass == "1":
            positive += 1
        elif klass == "0":
            negative += 1
    return {
        "path": str(path),
        "columns": columns,
        "row_count": len(rows),
        "series_count": len(series),
        "positive_count": positive,
        "negative_count": negative,
    }


def main():
    parser = argparse.ArgumentParser(description="Summarize downloaded LUNA16 resources.")
    parser.add_argument("--data-root", default=str(DATA_ROOT))
    parser.add_argument("--out", default=str(OUT / "luna16_resource_summary.json"))
    args = parser.parse_args()

    data_root = Path(args.data_root)
    eval_root = data_root / "evaluationScript" / "evaluationScript"
    candidates_path = data_root / "candidates_V2" / "candidates_V2.csv"
    summary = {
        "annotations": describe_annotations(data_root / "annotations.csv"),
        "sample_submission": {"path": str(data_root / "sampleSubmission.csv"), "size": (data_root / "sampleSubmission.csv").stat().st_size},
        "official_seriesuids": describe_seriesuids(eval_root / "annotations" / "seriesuids.csv"),
        "official_annotations": describe_annotations(eval_root / "annotations" / "annotations.csv"),
        "official_annotations_excluded": describe_annotations(eval_root / "annotations" / "annotations_excluded.csv"),
        "candidates_v2": describe_candidates(candidates_path),
        "evaluation_script": {
            "path": str(eval_root / "noduleCADEvaluationLUNA16.py"),
            "exists": (eval_root / "noduleCADEvaluationLUNA16.py").exists(),
        },
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
