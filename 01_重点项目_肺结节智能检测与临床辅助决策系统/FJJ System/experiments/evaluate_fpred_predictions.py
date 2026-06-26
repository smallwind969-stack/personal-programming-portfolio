import argparse
import csv
import json
from pathlib import Path


def read_predictions(path):
    rows = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rows.append({
                "seriesuid": row.get("seriesuid", ""),
                "label": int(row["class"]),
                "probability": float(row["probability"]),
            })
    return rows


def confusion(rows, threshold):
    tp = fp = tn = fn = 0
    for row in rows:
        pred = 1 if row["probability"] >= threshold else 0
        label = row["label"]
        if label == 1 and pred == 1:
            tp += 1
        elif label == 0 and pred == 1:
            fp += 1
        elif label == 0 and pred == 0:
            tn += 1
        else:
            fn += 1
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "threshold": threshold,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "accuracy": (tp + tn) / len(rows) if rows else 0.0,
        "precision": precision,
        "sensitivity": recall,
        "specificity": specificity,
        "f1": f1,
    }


def roc_points(rows):
    thresholds = sorted({row["probability"] for row in rows}, reverse=True)
    thresholds = [float("inf")] + thresholds + [float("-inf")]
    points = []
    positives = sum(1 for row in rows if row["label"] == 1)
    negatives = sum(1 for row in rows if row["label"] == 0)
    for threshold in thresholds:
        item = confusion(rows, threshold)
        tpr = item["tp"] / positives if positives else 0.0
        fpr = item["fp"] / negatives if negatives else 0.0
        points.append({"threshold": threshold, "tpr": tpr, "fpr": fpr})
    return sorted(points, key=lambda row: row["fpr"])


def auc_trapezoid(points):
    auc = 0.0
    for left, right in zip(points, points[1:]):
        width = right["fpr"] - left["fpr"]
        height = (right["tpr"] + left["tpr"]) / 2.0
        auc += width * height
    return auc


def write_csv(path, rows, fieldnames):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Evaluate FPRED candidate classification predictions.")
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--out-dir", default="docs/world_frontier/luna16/fpred_eval")
    parser.add_argument("--thresholds", default="0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9")
    args = parser.parse_args()

    rows = read_predictions(args.predictions)
    thresholds = [float(x) for x in args.thresholds.split(",") if x.strip()]
    threshold_rows = [confusion(rows, threshold) for threshold in thresholds]
    points = roc_points(rows)
    auc = auc_trapezoid(points)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(
        out / "threshold_metrics.csv",
        threshold_rows,
        ["threshold", "tp", "fp", "tn", "fn", "accuracy", "precision", "sensitivity", "specificity", "f1"],
    )
    write_csv(out / "roc_points.csv", points, ["threshold", "tpr", "fpr"])
    summary = {
        "prediction_count": len(rows),
        "positive_count": sum(1 for row in rows if row["label"] == 1),
        "negative_count": sum(1 for row in rows if row["label"] == 0),
        "auc": auc,
        "best_f1": max(threshold_rows, key=lambda row: row["f1"]) if threshold_rows else None,
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
