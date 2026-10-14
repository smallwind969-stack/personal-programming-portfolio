"""Export the original VNet -> ResNet NDET chain on a LUNA16 subset.

This deliberately preserves the original engine's window and threshold choices.
Each scan is saved separately, so a long benchmark can resume after interruption.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

import SimpleITK as sitk
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import DiagnosisEngine  # noqa: E402


CSV_FIELDS = ("seriesuid", "coordX", "coordY", "coordZ", "probability", "passed_filter")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    pending = path.with_suffix(".csv.tmp")
    with pending.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    pending.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path(r"E:\LUNA16"))
    parser.add_argument("--subset", type=int, default=7)
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "benchmarks" / "legacy_subset7")
    parser.add_argument("--limit", type=int, default=0, help="Run only first N scans; 0 means all")
    args = parser.parse_args()

    scan_dir = args.data_root / f"subset{args.subset}" / f"subset{args.subset}"
    scans = sorted(scan_dir.glob("*.mhd"))
    if args.limit:
        scans = scans[: args.limit]
    if not scans:
        raise FileNotFoundError(f"No MHD scans in {scan_dir}")
    args.out.mkdir(parents=True, exist_ok=True)

    vnet = ROOT / "models" / "vnet_v6_7_sprint_recall_0.9648_epoch_41.pth"
    resnet = ROOT / "models" / "fpr_v7_best_rec_0.9612.pth"
    dual = ROOT / "models" / "GOLDEN_Ep58_A0.923.pth"
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    engine = DiagnosisEngine(str(vnet), str(resnet), str(dual), device)
    settings = {
        "chain": "original VNet + ResNet, no source modifications",
        "subset": args.subset,
        "scans_selected": len(scans),
        "device": str(device),
        "python_version": sys.version.split()[0],
        "torch_version": torch.__version__,
        "simpleitk_version": sitk.Version_VersionString(),
        "gpu_name": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
        "prob_threshold": 0.15,
        "resnet_threshold": 0.4,
        "patch_size": 64,
        "stride": 32,
        "return_all_candidates": True,
        "vnet_sha256": sha256(vnet),
        "resnet_sha256": sha256(resnet),
        "known_limitations": [
            "Legacy sliding windows do not cover trailing image borders.",
            "Candidate generation is fixed at VNet threshold 0.15.",
            "ResNet score is not a calibrated nodule probability.",
            "Training-data provenance of old weights is not established.",
        ],
    }
    (args.out / "settings.json").write_text(json.dumps(settings, indent=2), encoding="utf-8")

    for index, scan in enumerate(scans, 1):
        target = args.out / f"{scan.stem}.csv"
        if target.exists():
            print(f"{index}/{len(scans)} skip {scan.stem}", flush=True)
            continue
        start = time.perf_counter()
        image = sitk.ReadImage(str(scan))
        findings, timing = engine.run_inference(
            image,
            prob_threshold=0.15,
            resnet_threshold=0.4,
            patch_size=64,
            stride=32,
            return_all_candidates=True,
        )
        rows = [
            {
                "seriesuid": scan.stem,
                "coordX": finding["coordX"],
                "coordY": finding["coordY"],
                "coordZ": finding["coordZ"],
                "probability": finding["resnet_prob"],
                "passed_filter": int(finding["passed_filter"]),
            }
            for finding in findings
        ]
        write_csv(target, rows)
        summary = {"scan": scan.stem, "total_sec": time.perf_counter() - start, **timing}
        (args.out / f"{scan.stem}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"{index}/{len(scans)} {scan.stem} candidates={len(rows)} sec={summary['total_sec']:.1f}", flush=True)

    if len(list(args.out.glob("*.csv"))) >= len(scans):
        all_rows = []
        for scan in scans:
            with (args.out / f"{scan.stem}.csv").open(newline="", encoding="utf-8") as handle:
                all_rows.extend(csv.DictReader(handle))
        write_csv(args.out / "all_candidates.csv", all_rows)
        write_csv(args.out / "default_filtered.csv", [r for r in all_rows if r["passed_filter"] == "1"])
        print(json.dumps({"scans": len(scans), "all": len(all_rows), "filtered": sum(r["passed_filter"] == "1" for r in all_rows)}))


if __name__ == "__main__":
    main()
