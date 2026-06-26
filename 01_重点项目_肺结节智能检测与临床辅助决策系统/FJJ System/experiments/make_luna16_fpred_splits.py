import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "luna16"
OUT = ROOT / "docs" / "world_frontier" / "luna16"


def read_candidates(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def split_series(seriesuids, train_ratio, val_ratio, seed):
    rng = random.Random(seed)
    seriesuids = list(seriesuids)
    rng.shuffle(seriesuids)
    n = len(seriesuids)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)
    train = set(seriesuids[:n_train])
    val = set(seriesuids[n_train:n_train + n_val])
    test = set(seriesuids[n_train + n_val:])
    return train, val, test


def balanced_rows(rows, max_neg_per_pos, seed):
    positives = [row for row in rows if str(row.get("class")) == "1"]
    negatives = [row for row in rows if str(row.get("class")) == "0"]
    rng = random.Random(seed)
    target_neg = min(len(negatives), len(positives) * max_neg_per_pos)
    sampled_negatives = rng.sample(negatives, target_neg) if target_neg < len(negatives) else negatives
    out = positives + sampled_negatives
    rng.shuffle(out)
    return out


def assign_splits(rows, train_series, val_series):
    assigned = []
    for row in rows:
        sid = row["seriesuid"]
        split = "test"
        if sid in train_series:
            split = "train"
        elif sid in val_series:
            split = "val"
        new_row = dict(row)
        new_row["split"] = split
        assigned.append(new_row)
    return assigned


def summarize(rows):
    by_split = defaultdict(lambda: {"total": 0, "positive": 0, "negative": 0, "series": set()})
    for row in rows:
        item = by_split[row["split"]]
        item["total"] += 1
        item["series"].add(row["seriesuid"])
        if str(row.get("class")) == "1":
            item["positive"] += 1
        else:
            item["negative"] += 1
    return {
        split: {
            "total": values["total"],
            "positive": values["positive"],
            "negative": values["negative"],
            "series_count": len(values["series"]),
        }
        for split, values in sorted(by_split.items())
    }


def write_csv(path, rows):
    fieldnames = ["seriesuid", "coordX", "coordY", "coordZ", "class", "split"]
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([{key: row.get(key, "") for key in fieldnames} for row in rows])


def write_summary(path, summary):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["split", "total", "positive", "negative", "series_count"])
        for split, values in summary.items():
            writer.writerow([split, values["total"], values["positive"], values["negative"], values["series_count"]])


def main():
    parser = argparse.ArgumentParser(description="Create balanced LUNA16 false-positive reduction candidate splits.")
    parser.add_argument("--candidates", default=str(DATA_ROOT / "candidates_V2" / "candidates_V2.csv"))
    parser.add_argument("--out", default=str(OUT / "fpred_candidates_balanced.csv"))
    parser.add_argument("--summary", default=str(OUT / "fpred_candidates_balanced_summary.csv"))
    parser.add_argument("--max-neg-per-pos", type=int, default=5)
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=20260614)
    args = parser.parse_args()

    rows = read_candidates(args.candidates)
    seriesuids = sorted({row["seriesuid"] for row in rows})
    train_series, val_series, _test_series = split_series(seriesuids, args.train_ratio, args.val_ratio, args.seed)
    selected = balanced_rows(rows, args.max_neg_per_pos, args.seed)
    assigned = assign_splits(selected, train_series, val_series)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    write_csv(args.out, assigned)
    split_summary = summarize(assigned)
    write_summary(args.summary, split_summary)
    print(f"rows={len(assigned)}")
    print(split_summary)
    print(args.out)


if __name__ == "__main__":
    main()
