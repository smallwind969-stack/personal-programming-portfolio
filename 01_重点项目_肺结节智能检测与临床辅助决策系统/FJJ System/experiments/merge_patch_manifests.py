import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_manifest(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def merge_manifests(items):
    merged = []
    for path, label in items:
        for row in read_manifest(path):
            if row.get("status") != "ok":
                continue
            item = dict(row)
            item["source_manifest"] = label
            merged.append(item)
    return merged


def class_counts(rows):
    pos = sum(1 for row in rows if int(row["class"]) == 1)
    neg = len(rows) - pos
    return {"negative": neg, "positive": pos}


def main():
    parser = argparse.ArgumentParser(description="Merge extracted patch manifests for FPRED training.")
    parser.add_argument("--manifest", action="append", nargs=2, metavar=("PATH", "LABEL"), required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()

    items = [(Path(path), label) for path, label in args.manifest]
    rows = merge_manifests(items)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "out": str(out),
        "count": len(rows),
        "class_counts": class_counts(rows),
        "sources": [{"path": str(path), "label": label} for path, label in items],
    }
    summary_path = Path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
