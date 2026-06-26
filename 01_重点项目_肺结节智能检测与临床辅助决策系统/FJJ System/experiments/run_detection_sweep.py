import argparse
import csv
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "research_loop"


def request_json(url, timeout=900):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_one(base_url, patient_id, prob_threshold, resnet_threshold, patch_size, stride, return_all_candidates):
    params = {
        "patient_id": patient_id,
        "prob_threshold": prob_threshold,
        "resnet_threshold": resnet_threshold,
        "patch_size": patch_size,
        "stride": stride,
        "return_all_candidates": str(return_all_candidates).lower(),
    }
    url = f"{base_url.rstrip('/')}/detect?{urllib.parse.urlencode(params)}"
    t0 = time.perf_counter()
    data = request_json(url)
    elapsed = round(time.perf_counter() - t0, 4)
    findings = data.get("findings", [])
    timing = data.get("timing", {})
    engine_detail = timing.get("engine_detail", {})
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "patient_id": patient_id,
        "prob_threshold": prob_threshold,
        "resnet_threshold": resnet_threshold,
        "patch_size": patch_size,
        "stride": stride,
        "return_all_candidates": return_all_candidates,
        "finding_count": len(findings),
        "candidate_count_before_filter": engine_detail.get("candidate_count_before_filter"),
        "candidate_count_after_filter": engine_detail.get("candidate_count_after_filter"),
        "http_elapsed_sec": elapsed,
        "load_itk_sec": timing.get("load_itk_sec"),
        "engine_detect_sec": timing.get("engine_detect_sec"),
        "total_detect_sec": timing.get("total_detect_sec"),
    }


def write_rows(path, rows):
    if not rows:
        return
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Run detection threshold sweeps against the local Flask service.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5001")
    parser.add_argument("--patient", required=True)
    parser.add_argument("--prob-thresholds", default="0.15")
    parser.add_argument("--resnet-thresholds", default="0.4")
    parser.add_argument("--patch-size", type=int, default=64)
    parser.add_argument("--stride", type=int, default=32)
    parser.add_argument("--return-all-candidates", action="store_true")
    parser.add_argument("--out", default=str(OUT / "detection_sweep_runs.csv"))
    args = parser.parse_args()

    prob_thresholds = [float(x) for x in args.prob_thresholds.split(",") if x.strip()]
    resnet_thresholds = [float(x) for x in args.resnet_thresholds.split(",") if x.strip()]

    rows = []
    for prob in prob_thresholds:
        for resnet in resnet_thresholds:
            row = run_one(
                args.base_url,
                args.patient,
                prob,
                resnet,
                args.patch_size,
                args.stride,
                args.return_all_candidates,
            )
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False))

    write_rows(Path(args.out), rows)


if __name__ == "__main__":
    main()
