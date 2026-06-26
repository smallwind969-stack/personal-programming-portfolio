import argparse
import csv
import json
from pathlib import Path

try:
    from metaimage_utils import MetaImageVolume
except ImportError:
    from experiments.metaimage_utils import MetaImageVolume


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "luna16"
OUT = ROOT / "docs" / "world_frontier" / "luna16"


def find_mhd_files(data_root):
    return sorted(Path(data_root).glob("subset*/**/*.mhd"))


def image_summary(path):
    return MetaImageVolume(path).summary()


def write_csv(path, rows):
    fieldnames = [
        "seriesuid",
        "path",
        "size_x",
        "size_y",
        "size_z",
        "spacing_x",
        "spacing_y",
        "spacing_z",
        "origin_x",
        "origin_y",
        "origin_z",
    ]
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Index extracted LUNA16 .mhd CT volumes.")
    parser.add_argument("--data-root", default=str(DATA_ROOT))
    parser.add_argument("--out", default=str(OUT / "luna16_ct_index.csv"))
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    files = find_mhd_files(args.data_root)
    if args.limit:
        files = files[:args.limit]
    rows = [image_summary(path) for path in files]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    write_csv(args.out, rows)
    report = {
        "data_root": str(Path(args.data_root)),
        "ct_count": len(rows),
        "out": args.out,
        "first": rows[0] if rows else None,
    }
    (Path(args.out).with_suffix(".json")).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
