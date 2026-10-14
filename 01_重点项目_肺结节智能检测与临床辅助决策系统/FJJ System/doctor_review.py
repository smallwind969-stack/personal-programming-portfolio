import json
import os
from datetime import datetime


def _case_dir(base_dir, patient_id):
    safe_patient_id = os.path.basename(str(patient_id))
    path = os.path.join(base_dir, "case_context", safe_patient_id)
    os.makedirs(path, exist_ok=True)
    return path


def _read_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_nodule(item, index=0):
    source = item.get("source") or "doctor"
    nodule_id = item.get("nodule_id") or item.get("id") or f"{source}_{index + 1:03d}"
    return {
        "nodule_id": str(nodule_id),
        "source": source,
        "doctor_confirmed": bool(item.get("doctor_confirmed", source == "doctor")),
        "slice_idx": item.get("slice_idx", item.get("slice_index")),
        "x": item.get("x"),
        "y": item.get("y"),
        "bbox_3d": item.get("bbox_3d", {}),
        "area": item.get("area"),
        "diameter_mm": item.get("diameter_mm"),
        "prob": item.get("prob", item.get("detection_prob")),
        "malignancy_prob": item.get("malignancy_prob"),
        "status": item.get("status", "confirmed" if source == "doctor" else "pending"),
        "doctor_assessment": item.get("doctor_assessment", ""),
        "imaging_features": item.get("imaging_features", {}),
    }


def save_review(base_dir, patient_id, findings=None, doctor_nodules=None, clinical_context=None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    findings = findings or []
    doctor_nodules = doctor_nodules or []
    clinical_context = clinical_context or {}

    normalized_model = []
    for idx, finding in enumerate(findings):
        item = dict(finding)
        item.setdefault("source", "model")
        item.setdefault("doctor_confirmed", False)
        normalized_model.append(normalize_nodule(item, idx))

    normalized_doctor = []
    for idx, nodule in enumerate(doctor_nodules):
        item = dict(nodule)
        item.setdefault("source", "doctor")
        item.setdefault("doctor_confirmed", True)
        normalized_doctor.append(normalize_nodule(item, idx))

    context = {
        "patient_id": patient_id,
        "updated_at": now,
        "model_findings": normalized_model,
        "doctor_nodules": normalized_doctor,
        "clinical_context": clinical_context,
    }

    path = os.path.join(_case_dir(base_dir, patient_id), "doctor_review.json")
    _write_json(path, context)
    return context


def load_review(base_dir, patient_id):
    path = os.path.join(_case_dir(base_dir, patient_id), "doctor_review.json")
    return _read_json(path, {
        "patient_id": patient_id,
        "model_findings": [],
        "doctor_nodules": [],
        "clinical_context": {},
    })


def merge_case_context(patient_id, findings=None, review=None, clinical_context=None):
    findings = findings or []
    review = review or {}
    merged_clinical = {}
    merged_clinical.update(review.get("clinical_context") or {})
    merged_clinical.update(clinical_context or {})

    reviewed_model = review.get("model_findings") or []
    doctor_nodules = review.get("doctor_nodules") or []

    if review.get("updated_at") is not None or reviewed_model:
        base_nodules = reviewed_model
    else:
        base_nodules = [
            normalize_nodule({**finding, "source": "model", "doctor_confirmed": False}, idx)
            for idx, finding in enumerate(findings)
        ]

    final_nodules = [
        nodule for nodule in base_nodules + doctor_nodules
        if nodule.get("doctor_confirmed") and nodule.get("status") != "dismissed"
    ]

    return {
        "patient_id": patient_id,
        "final_nodules": final_nodules,
        "model_findings": base_nodules,
        "doctor_nodules": doctor_nodules,
        "clinical_context": merged_clinical,
        "review_updated_at": review.get("updated_at"),
    }
