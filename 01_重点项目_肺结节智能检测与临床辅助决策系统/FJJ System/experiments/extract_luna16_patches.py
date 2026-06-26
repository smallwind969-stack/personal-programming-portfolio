import argparse
import csv
import json
from pathlib import Path

import numpy as np
try:
    from metaimage_utils import MetaImageVolume
except ImportError:
    from experiments.metaimage_utils import MetaImageVolume


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "luna16"
OUT = ROOT / "docs" / "world_frontier" / "luna16" / "patch_smoke"


def load_candidates(path, split=None):
    rows = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if split and row.get("split") != split:
                continue
            rows.append(row)
    return rows


def find_volume(data_root, seriesuid):
    matches = list(Path(data_root).glob(f"subset*/**/{seriesuid}.mhd"))
    return matches[0] if matches else None


def crop_patch(array_zyx, center_xyz, patch_size):
    cx, cy, cz = [int(round(v)) for v in center_xyz]
    half = patch_size // 2
    patch = np.zeros((patch_size, patch_size, patch_size), dtype=np.float32)

    z0, z1 = cz - half, cz + half
    y0, y1 = cy - half, cy + half
    x0, x1 = cx - half, cx + half

    src_z0, src_z1 = max(0, z0), min(array_zyx.shape[0], z1)
    src_y0, src_y1 = max(0, y0), min(array_zyx.shape[1], y1)
    src_x0, src_x1 = max(0, x0), min(array_zyx.shape[2], x1)

    dst_z0, dst_y0, dst_x0 = src_z0 - z0, src_y0 - y0, src_x0 - x0
    patch[
        dst_z0:dst_z0 + (src_z1 - src_z0),
        dst_y0:dst_y0 + (src_y1 - src_y0),
        dst_x0:dst_x0 + (src_x1 - src_x0),
    ] = array_zyx[src_z0:src_z1, src_y0:src_y1, src_x0:src_x1]
    return patch


def normalize_hu(array):
    return ((np.clip(array, -1200, 600) + 1200) / 1800.0).astype(np.float32)


def extract_patch_for_candidate(image, row, patch_size):
    point = (float(row["coordX"]), float(row["coordY"]), float(row["coordZ"]))
    center = image.physical_to_continuous_index(point)
    array = normalize_hu(image.array.astype(np.float32))
    patch = crop_patch(array, center, patch_size)
    return patch, center


def main():
    parser = argparse.ArgumentParser(description="Extract 3D patches from LUNA16 candidates.")
    parser.add_argument("--data-root", default=str(DATA_ROOT))
    parser.add_argument("--candidates", default=str(OUT.parent / "fpred_candidates_balanced.csv"))
    parser.add_argument("--split", default="val")
    parser.add_argument("--limit", type=int, default=16)
    parser.add_argument("--patch-size", type=int, default=32)
    parser.add_argument("--out-dir", default=str(OUT))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = load_candidates(args.candidates, split=args.split)
    images = {}
    manifest = []
    for idx, row in enumerate(rows):
        seriesuid = row["seriesuid"]
        volume_path = find_volume(args.data_root, seriesuid)
        if volume_path is None:
            manifest.append({"seriesuid": seriesuid, "status": "missing_volume"})
            continue
        if seriesuid not in images:
            images[seriesuid] = MetaImageVolume(volume_path)
        patch, center = extract_patch_for_candidate(images[seriesuid], row, args.patch_size)
        patch_path = out_dir / f"{idx:04d}_{seriesuid}_{row.get('class', 'x')}.npy"
        np.save(patch_path, patch)
        manifest.append({
            "seriesuid": seriesuid,
            "class": row.get("class"),
            "split": row.get("split"),
            "patch": str(patch_path),
            "center_x": center[0],
            "center_y": center[1],
            "center_z": center[2],
            "status": "ok",
        })
        if args.limit and sum(1 for item in manifest if item["status"] == "ok") >= args.limit:
            break

    manifest_path = out_dir / "patch_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"requested": len(rows), "ok": sum(1 for x in manifest if x["status"] == "ok"), "manifest": str(manifest_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
