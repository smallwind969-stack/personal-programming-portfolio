import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models import ResNet18_3D_CBAM


DEFAULT_WEIGHTS = ROOT / "models" / "fpr_v7_best_rec_0.9612.pth"


def load_manifest(path):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    return [row for row in rows if row.get("status") == "ok"]


def confusion_at_threshold(rows, threshold):
    tp = fp = tn = fn = 0
    for row in rows:
        label = int(row["class"])
        pred = 1 if float(row["probability"]) >= threshold else 0
        if label == 1 and pred == 1:
            tp += 1
        elif label == 0 and pred == 1:
            fp += 1
        elif label == 0 and pred == 0:
            tn += 1
        elif label == 1 and pred == 0:
            fn += 1
    return {
        "threshold": threshold,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "accuracy": (tp + tn) / len(rows) if rows else 0.0,
        "sensitivity": tp / (tp + fn) if (tp + fn) else 0.0,
        "specificity": tn / (tn + fp) if (tn + fp) else 0.0,
    }


def load_model(weights, device):
    model = ResNet18_3D_CBAM().to(device)
    state = torch.load(weights, map_location=device)
    if isinstance(state, dict) and "state_dict" in state:
        state = state["state_dict"]
    model.load_state_dict(state)
    model.eval()
    return model


def predict_patch(model, patch_path, device):
    patch = np.load(patch_path).astype(np.float32)
    tensor = torch.from_numpy(patch).unsqueeze(0).unsqueeze(0).to(device)
    with torch.no_grad():
        logits = model(tensor)
        prob = torch.softmax(logits, dim=1)[0, 1].item()
    return prob


def write_csv(path, rows):
    fieldnames = ["seriesuid", "class", "probability", "patch", "split"]
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([{key: row.get(key, "") for key in fieldnames} for row in rows])


def main():
    parser = argparse.ArgumentParser(description="Run current ResNet-CBAM FP filter on extracted LUNA16 patches.")
    parser.add_argument("--manifest", default="docs/world_frontier/luna16/patch_smoke/patch_manifest.json")
    parser.add_argument("--weights", default=str(DEFAULT_WEIGHTS))
    parser.add_argument("--out", default="docs/world_frontier/luna16/patch_smoke/fpred_resnet_smoke_predictions.csv")
    parser.add_argument("--summary", default="docs/world_frontier/luna16/patch_smoke/fpred_resnet_smoke_summary.json")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    device = torch.device(args.device)
    model = load_model(args.weights, device)
    rows = []
    for item in load_manifest(args.manifest):
        row = dict(item)
        row["probability"] = round(predict_patch(model, item["patch"], device), 6)
        rows.append(row)

    write_csv(args.out, rows)
    summary = confusion_at_threshold(rows, args.threshold)
    summary.update({"row_count": len(rows), "weights": args.weights, "manifest": args.manifest})
    Path(args.summary).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
