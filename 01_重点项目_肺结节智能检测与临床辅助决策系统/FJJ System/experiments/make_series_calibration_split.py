import argparse
import csv
import json
from pathlib import Path


def read_seriesuids(path):
    return [line.strip() for line in Path(path).read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def annotation_counts(annotations_path, seriesuids):
    counts = {seriesuid: 0 for seriesuid in seriesuids}
    with Path(annotations_path).open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            seriesuid = row["seriesuid"]
            if seriesuid in counts:
                counts[seriesuid] += 1
    return counts


def split_series_balanced(counts):
    calibration = []
    evaluation = []
    cal_total = 0
    eval_total = 0
    for seriesuid, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        if cal_total <= eval_total:
            calibration.append(seriesuid)
            cal_total += count
        else:
            evaluation.append(seriesuid)
            eval_total += count
    return sorted(calibration), sorted(evaluation)


def write_series(path, seriesuids):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(seriesuids) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Create balanced calibration/evaluation series splits by annotation count.")
    parser.add_argument("--seriesuids", required=True)
    parser.add_argument("--annotations", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    seriesuids = read_seriesuids(args.seriesuids)
    counts = annotation_counts(args.annotations, seriesuids)
    calibration, evaluation = split_series_balanced(counts)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_series(out_dir / "calibration_seriesuids.txt", calibration)
    write_series(out_dir / "evaluation_seriesuids.txt", evaluation)
    summary = {
        "series_count": len(seriesuids),
        "calibration_series_count": len(calibration),
        "evaluation_series_count": len(evaluation),
        "annotation_count": sum(counts.values()),
        "calibration_annotation_count": sum(counts[item] for item in calibration),
        "evaluation_annotation_count": sum(counts[item] for item in evaluation),
        "counts_by_series": counts,
    }
    (out_dir / "series_split_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
