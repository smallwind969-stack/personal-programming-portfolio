import argparse
import csv
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "luna16"
OUT = ROOT / "docs" / "world_frontier" / "luna16"


def available_series(data_root):
    return {path.stem for path in Path(data_root).glob("subset*/**/*.mhd")}


def read_candidates(path, series_filter=None, split=None):
    rows = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if split and row.get("split") != split:
                continue
            if series_filter is not None and row["seriesuid"] not in series_filter:
                continue
            rows.append(row)
    return rows


def balanced_sample(rows, positives, negatives, seed):
    rng = random.Random(seed)
    pos_rows = [row for row in rows if row.get("class") == "1"]
    neg_rows = [row for row in rows if row.get("class") == "0"]
    selected = []
    selected.extend(rng.sample(pos_rows, min(positives, len(pos_rows))))
    selected.extend(rng.sample(neg_rows, min(negatives, len(neg_rows))))
    rng.shuffle(selected)
    return selected


def write_csv(path, rows):
    fieldnames = ["seriesuid", "coordX", "coordY", "coordZ", "class", "split"]
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([{key: row.get(key, "") for key in fieldnames} for row in rows])


def main():
    parser = argparse.ArgumentParser(description="Create a subset-aware balanced candidate list for patch extraction.")
    parser.add_argument("--data-root", default=str(DATA_ROOT))
    parser.add_argument("--candidates", default=str(OUT / "fpred_candidates_balanced.csv"))
    parser.add_argument("--split", default="val")
    parser.add_argument("--positives", type=int, default=32)
    parser.add_argument("--negatives", type=int, default=96)
    parser.add_argument("--seed", type=int, default=20260614)
    parser.add_argument("--out", default=str(OUT / "subset0_val_patch_candidates.csv"))
    args = parser.parse_args()

    series = available_series(args.data_root)
    rows = read_candidates(args.candidates, series_filter=series, split=args.split)
    selected = balanced_sample(rows, args.positives, args.negatives, args.seed)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    write_csv(args.out, selected)
    print({
        "available_series": len(series),
        "candidate_rows": len(rows),
        "selected": len(selected),
        "positive": sum(1 for row in selected if row["class"] == "1"),
        "negative": sum(1 for row in selected if row["class"] == "0"),
        "out": args.out,
    })


if __name__ == "__main__":
    main()
