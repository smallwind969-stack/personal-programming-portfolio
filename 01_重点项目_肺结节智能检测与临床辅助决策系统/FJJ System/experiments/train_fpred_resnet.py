import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models import ResNet18_3D_CBAM
from experiments.evaluate_fpred_predictions import auc_trapezoid, confusion, roc_points


DEFAULT_WEIGHTS = ROOT / "models" / "fpr_v7_best_rec_0.9612.pth"


class PatchDataset(Dataset):
    def __init__(self, manifest):
        rows = json.loads(Path(manifest).read_text(encoding="utf-8"))
        self.rows = [row for row in rows if row.get("status") == "ok"]

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        row = self.rows[idx]
        patch = np.load(row["patch"]).astype(np.float32)
        label = int(row["class"])
        return torch.from_numpy(patch).unsqueeze(0), torch.tensor(label, dtype=torch.long)


def class_counts(dataset):
    pos = sum(1 for row in dataset.rows if int(row["class"]) == 1)
    neg = len(dataset) - pos
    return neg, pos


def load_model(weights, device):
    model = ResNet18_3D_CBAM().to(device)
    model.load_state_dict(torch.load(weights, map_location=device))
    return model


def evaluate(model, loader, device):
    model.eval()
    rows = []
    with torch.no_grad():
        for patches, labels in loader:
            patches = patches.to(device)
            logits = model(patches)
            probs = torch.softmax(logits, dim=1)[:, 1].cpu().numpy()
            for label, prob in zip(labels.numpy(), probs):
                rows.append({"label": int(label), "probability": float(prob)})
    auc = auc_trapezoid(roc_points(rows))
    metrics_05 = confusion(rows, 0.5)
    best = max((confusion(rows, t / 100.0) for t in range(1, 100)), key=lambda item: item["f1"])
    return {"auc": auc, "threshold_0_5": metrics_05, "best_f1": best, "rows": rows}


def write_predictions(path, rows):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["class", "probability"])
        writer.writeheader()
        for row in rows:
            writer.writerow({"class": row["label"], "probability": row["probability"]})


def main():
    parser = argparse.ArgumentParser(description="Fine-tune ResNet-CBAM FPRED model on extracted LUNA16 patches.")
    parser.add_argument("--train-manifest", default="docs/world_frontier/luna16/patch_train_256/patch_manifest.json")
    parser.add_argument("--val-manifest", default="docs/world_frontier/luna16/patch_val_115/patch_manifest.json")
    parser.add_argument("--weights", default=str(DEFAULT_WEIGHTS))
    parser.add_argument("--out-dir", default="docs/world_frontier/luna16/fpred_finetune_subset0")
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    device = torch.device(args.device)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    train_ds = PatchDataset(args.train_manifest)
    val_ds = PatchDataset(args.val_manifest)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)

    model = load_model(args.weights, device)
    neg, pos = class_counts(train_ds)
    weights = torch.tensor([1.0, neg / max(pos, 1)], dtype=torch.float32, device=device)
    criterion = torch.nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    history = []
    best_auc = -1.0
    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0
        total = 0
        for patches, labels in train_loader:
            patches = patches.to(device)
            labels = labels.to(device)
            optimizer.zero_grad()
            logits = model(patches)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            total_loss += float(loss.item()) * labels.shape[0]
            total += labels.shape[0]

        val = evaluate(model, val_loader, device)
        row = {
            "epoch": epoch,
            "train_loss": total_loss / max(total, 1),
            "val_auc": val["auc"],
            "val_threshold_0_5": val["threshold_0_5"],
            "val_best_f1": val["best_f1"],
        }
        history.append(row)
        print(json.dumps(row, ensure_ascii=False))
        if val["auc"] > best_auc:
            best_auc = val["auc"]
            torch.save(model.state_dict(), out_dir / "best_resnet_cbam_subset0.pth")
            write_predictions(out_dir / "best_val_predictions.csv", val["rows"])

    summary = {
        "train_count": len(train_ds),
        "val_count": len(val_ds),
        "train_class_counts": {"negative": neg, "positive": pos},
        "epochs": args.epochs,
        "best_auc": best_auc,
        "history": history,
    }
    (out_dir / "training_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
