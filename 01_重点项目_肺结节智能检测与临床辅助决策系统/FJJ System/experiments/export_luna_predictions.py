import argparse
import csv
import json
from pathlib import Path

import SimpleITK as sitk


ROOT = Path(__file__).resolve().parents[1]
UPLOADS = ROOT / "uploads"
CASE_CONTEXT = ROOT / "case_context"
OUT = ROOT / "docs" / "world_frontier"


def load_itk(path):
    if path.is_file() and path.suffix.lower() == ".mhd":
        return sitk.ReadImage(str(path))
    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(str(path))
    if not dicom_names:
        raise FileNotFoundError(f"No DICOM series found under {path}")
    reader.SetFileNames(list(dicom_names)[::-1])
    return reader.Execute()


def safe_float(value, default=0.0):
    try:
        if value in ("", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def patient_ids(selected):
    if selected:
        return selected
    return sorted(p.name for p in CASE_CONTEXT.iterdir() if p.is_dir())


def load_review(patient_id):
    path = CASE_CONTEXT / patient_id / "doctor_review.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def finding_to_physical(itk_img, finding):
    if all(k in finding for k in ("coordX", "coordY", "coordZ")):
        return (
            safe_float(finding["coordX"]),
            safe_float(finding["coordY"]),
            safe_float(finding["coordZ"]),
        )

    x = safe_float(finding.get("x"))
    y = safe_float(finding.get("y"))
    z = safe_float(finding.get("slice_idx"))
    try:
        coord = itk_img.TransformContinuousIndexToPhysicalPoint((x, y, z))
    except RuntimeError:
        # Keep the row exportable while making the coordinate uncertainty visible.
        coord = (x, y, z)
    return tuple(float(v) for v in coord)


def collect_rows(selected_patients, include_doctor_added):
    rows = []
    for patient_id in patient_ids(selected_patients):
        review = load_review(patient_id)
        image_path = UPLOADS / patient_id
        if not review or not image_path.exists():
            continue
        itk_img = load_itk(image_path)
        findings = list(review.get("model_findings", []))
        if include_doctor_added:
            findings.extend(review.get("doctor_nodules", []))
        for idx, finding in enumerate(findings, start=1):
            status = finding.get("status")
            if status in {"deleted", "rejected"}:
                continue
            coord_x, coord_y, coord_z = finding_to_physical(itk_img, finding)
            prob = safe_float(finding.get("prob", finding.get("detection_prob")), 0.5)
            if finding.get("source") == "doctor" and prob == 0.5:
                prob = 0.99
            rows.append({
                "seriesuid": patient_id,
                "coordX": round(coord_x, 4),
                "coordY": round(coord_y, 4),
                "coordZ": round(coord_z, 4),
                "probability": round(prob, 6),
                "source": finding.get("source", "model"),
                "nodule_id": finding.get("nodule_id", f"{patient_id}_{idx}"),
            })
    return rows


def write_predictions(path, rows, include_metadata):
    fieldnames = ["seriesuid", "coordX", "coordY", "coordZ", "probability"]
    if include_metadata:
        fieldnames += ["source", "nodule_id"]
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fieldnames})


def main():
    parser = argparse.ArgumentParser(description="Export local findings to LUNA16-style prediction CSV.")
    parser.add_argument("--patient", action="append", help="Patient id to export. Repeat for multiple.")
    parser.add_argument("--include-doctor-added", action="store_true")
    parser.add_argument("--include-metadata", action="store_true")
    parser.add_argument("--out", default=str(OUT / "local_luna_predictions.csv"))
    args = parser.parse_args()

    rows = collect_rows(args.patient, args.include_doctor_added)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_predictions(out, rows, args.include_metadata)
    print(f"rows={len(rows)}")
    print(out)


if __name__ == "__main__":
    main()
