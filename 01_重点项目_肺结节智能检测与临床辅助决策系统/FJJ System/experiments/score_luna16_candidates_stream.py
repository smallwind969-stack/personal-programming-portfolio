import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models import ResNet18_3D_CBAM

try:
    from extract_luna16_patches import crop_patch, find_volume
    from metaimage_utils import MetaImageVolume
except ImportError:
    from experiments.extract_luna16_patches import crop_patch, find_volume
    from experiments.metaimage_utils import MetaImageVolume


DEFAULT_WEIGHTS = ROOT / "docs" / "world_frontier" / "luna16" / "fpred_finetune_subset0" / "best_resnet_cbam_subset0.pth"


def read_seriesuids(path):
    with Path(path).open("r", encoding="utf-8-sig") as f:
        return {line.strip() for line in f if line.strip()}


def read_candidates(path, seriesuids=None, limit=None):
    rows = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if seriesuids and row["seriesuid"] not in seriesuids:
                continue
            rows.append(row)
            if limit and len(rows) >= limit:
                break
    return rows


def read_predictions(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def candidate_key(row):
    return (row["seriesuid"], float(row["coordX"]), float(row["coordY"]), float(row["coordZ"]))


def filter_already_scored(rows, scored_rows):
    scored_keys = {candidate_key(row) for row in scored_rows}
    return [row for row in rows if candidate_key(row) not in scored_keys]


def batch_items(items, batch_size):
    for start in range(0, len(items), batch_size):
        yield items[start:start + batch_size]


def load_model(weights, device):
    model = ResNet18_3D_CBAM().to(device)
    state = torch.load(weights, map_location=device)
    if isinstance(state, dict) and "state_dict" in state:
        state = state["state_dict"]
    model.load_state_dict(state)
    model.eval()
    return model


def make_patch_tensor(patches):
    array = np.stack(patches).astype(np.float32)
    return torch.from_numpy(array).unsqueeze(1)


def normalize_image_once(image):
    return ((np.clip(image.array.astype(np.float32), -1200, 600) + 1200) / 1800.0).astype(np.float32)


def extract_patch_from_normalized(image, normalized_array, row, patch_size):
    point = (float(row["coordX"]), float(row["coordY"]), float(row["coordZ"]))
    center = image.physical_to_continuous_index(point)
    return crop_patch(normalized_array, center, patch_size)


def candidate_to_prediction(row, probability):
    return {
        "seriesuid": row["seriesuid"],
        "coordX": float(row["coordX"]),
        "coordY": float(row["coordY"]),
        "coordZ": float(row["coordZ"]),
        "probability": float(probability),
    }


def write_predictions(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["seriesuid", "coordX", "coordY", "coordZ", "probability"])
        writer.writeheader()
        writer.writerows(rows)


def write_progress(path, summary):
    if not path:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def score_candidates(rows, data_root, weights, device, patch_size=32, batch_size=16, checkpoint=None, checkpoint_prefix=None, progress_summary=None):
    model = load_model(weights, device)
    predictions = []
    failures = []
    start = time.time()

    rows_by_series = {}
    for row in rows:
        rows_by_series.setdefault(row["seriesuid"], []).append(row)

    processed_series = 0
    total_series = len(rows_by_series)
    for seriesuid, series_rows in rows_by_series.items():
        volume_path = find_volume(data_root, seriesuid)
        if volume_path is None:
            failures.append({"seriesuid": seriesuid, "error": "missing_volume", "count": len(series_rows)})
            processed_series += 1
            write_progress(progress_summary, {
                "processed_series": processed_series,
                "total_series": total_series,
                "current_seriesuid": seriesuid,
                "new_prediction_count": len(predictions),
                "checkpoint_prefix_count": len(checkpoint_prefix or []),
                "total_prediction_count": len(checkpoint_prefix or []) + len(predictions),
                "failure_count": len(failures),
                "elapsed_sec": round(time.time() - start, 3),
                "checkpoint": str(checkpoint) if checkpoint else None,
            })
            continue
        image = MetaImageVolume(volume_path)
        normalized_array = normalize_image_once(image)
        for batch in batch_items(series_rows, batch_size):
            patches = []
            valid_rows = []
            for row in batch:
                try:
                    patch = extract_patch_from_normalized(image, normalized_array, row, patch_size)
                    patches.append(patch)
                    valid_rows.append(row)
                except Exception as exc:
                    failures.append({"seriesuid": seriesuid, "error": repr(exc), "coordX": row.get("coordX"), "coordY": row.get("coordY"), "coordZ": row.get("coordZ")})
            if not patches:
                continue
            tensor = make_patch_tensor(patches).to(device)
            with torch.no_grad():
                logits = model(tensor)
                probs = torch.softmax(logits, dim=1)[:, 1].detach().cpu().numpy()
            for row, prob in zip(valid_rows, probs):
                predictions.append(candidate_to_prediction(row, round(float(prob), 6)))
        if checkpoint:
            write_predictions(checkpoint, (checkpoint_prefix or []) + predictions)
        processed_series += 1
        write_progress(progress_summary, {
            "processed_series": processed_series,
            "total_series": total_series,
            "current_seriesuid": seriesuid,
            "new_prediction_count": len(predictions),
            "checkpoint_prefix_count": len(checkpoint_prefix or []),
            "total_prediction_count": len(checkpoint_prefix or []) + len(predictions),
            "failure_count": len(failures),
            "elapsed_sec": round(time.time() - start, 3),
            "checkpoint": str(checkpoint) if checkpoint else None,
        })

    summary = {
        "candidate_count": len(rows),
        "prediction_count": len(predictions),
        "series_count": len(rows_by_series),
        "failure_count": len(failures),
        "elapsed_sec": round(time.time() - start, 3),
        "weights": str(weights),
        "patch_size": patch_size,
        "batch_size": batch_size,
    }
    return predictions, summary, failures


def main():
    parser = argparse.ArgumentParser(description="Stream-score LUNA16 candidates_V2 with the FPRED ResNet-CBAM model.")
    parser.add_argument("--candidates", default=str(ROOT / "data" / "luna16" / "candidates_V2" / "candidates_V2.csv"))
    parser.add_argument("--seriesuids", required=True)
    parser.add_argument("--data-root", default=str(ROOT / "data" / "luna16"))
    parser.add_argument("--weights", default=str(DEFAULT_WEIGHTS))
    parser.add_argument("--out", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--failures", required=True)
    parser.add_argument("--patch-size", type=int, default=32)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--checkpoint", help="Optional CSV updated after each series.")
    parser.add_argument("--resume-from", help="Existing LUNA-style prediction CSV to keep and skip.")
    parser.add_argument("--progress-summary", help="Optional small JSON updated after each processed series.")
    args = parser.parse_args()

    seriesuids = read_seriesuids(args.seriesuids)
    rows = read_candidates(args.candidates, seriesuids=seriesuids, limit=args.limit or None)
    existing_predictions = read_predictions(args.resume_from) if args.resume_from else []
    rows = filter_already_scored(rows, existing_predictions)
    device = torch.device(args.device)
    predictions, summary, failures = score_candidates(
        rows,
        Path(args.data_root),
        Path(args.weights),
        device,
        patch_size=args.patch_size,
        batch_size=args.batch_size,
        checkpoint=Path(args.checkpoint) if args.checkpoint else None,
        checkpoint_prefix=existing_predictions,
        progress_summary=Path(args.progress_summary) if args.progress_summary else None,
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    combined_predictions = existing_predictions + predictions
    write_predictions(out, combined_predictions)
    summary["resumed_prediction_count"] = len(existing_predictions)
    summary["total_prediction_count"] = len(combined_predictions)
    Path(args.summary).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.failures).write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
