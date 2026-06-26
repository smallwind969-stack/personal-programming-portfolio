import argparse
import csv
import math
from pathlib import Path

try:
    from export_luna_predictions import OUT, UPLOADS, finding_to_physical, load_itk, load_review, patient_ids, safe_float
except ImportError:
    from experiments.export_luna_predictions import OUT, UPLOADS, finding_to_physical, load_itk, load_review, patient_ids, safe_float


def estimate_diameter_mm(finding, default_diameter_mm):
    explicit = safe_float(finding.get("diameter_mm"), 0.0)
    if explicit > 0:
        return explicit
    area = safe_float(finding.get("area"), 0.0)
    if area > 0:
        return max(3.0, 2.0 * math.sqrt(area / math.pi))
    bbox = finding.get("bbox_3d")
    if isinstance(bbox, dict):
        width = abs(safe_float(bbox.get("x2")) - safe_float(bbox.get("x1")))
        height = abs(safe_float(bbox.get("y2")) - safe_float(bbox.get("y1")))
        if width > 0 and height > 0:
            return max(3.0, (width + height) / 2.0)
    return default_diameter_mm


def collect_rows(selected_patients, default_diameter_mm):
    rows = []
    for patient_id in patient_ids(selected_patients):
        review = load_review(patient_id)
        image_path = UPLOADS / patient_id
        if not review or not image_path.exists():
            continue
        itk_img = load_itk(image_path)
        findings = list(review.get("model_findings", [])) + list(review.get("doctor_nodules", []))
        for finding in findings:
            if finding.get("status") in {"deleted", "rejected"}:
                continue
            coord_x, coord_y, coord_z = finding_to_physical(itk_img, finding)
            rows.append({
                "seriesuid": patient_id,
                "coordX": round(coord_x, 4),
                "coordY": round(coord_y, 4),
                "coordZ": round(coord_z, 4),
                "diameter_mm": round(estimate_diameter_mm(finding, default_diameter_mm), 4),
            })
    return rows


def write_annotations(path, rows):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["seriesuid", "coordX", "coordY", "coordZ", "diameter_mm"])
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Export local review records as LUNA-style proxy annotations.")
    parser.add_argument("--patient", action="append", help="Patient id to export. Repeat for multiple.")
    parser.add_argument("--default-diameter-mm", type=float, default=8.0)
    parser.add_argument("--out", default=str(OUT / "local_review_proxy_annotations.csv"))
    args = parser.parse_args()

    rows = collect_rows(args.patient, args.default_diameter_mm)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_annotations(out, rows)
    print(f"rows={len(rows)}")
    print(out)


if __name__ == "__main__":
    main()
