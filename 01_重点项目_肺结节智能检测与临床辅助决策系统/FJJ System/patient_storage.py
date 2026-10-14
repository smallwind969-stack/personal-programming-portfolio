import os
import shutil


MANAGED_DIRS = ("uploads", os.path.join("static", "processed"), "case_context")


def safe_patient_id(value):
    raw = os.path.basename(str(value)).strip()
    return "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in raw)[:80]


def patient_paths(base_dir, patient_id):
    pid = safe_patient_id(patient_id)
    return [os.path.join(base_dir, rel, pid) for rel in MANAGED_DIRS]


def existing_patient_paths(base_dir, patient_id):
    return [path for path in patient_paths(base_dir, patient_id) if os.path.exists(path)]


def list_patients(base_dir):
    patient_ids = set()
    for rel in MANAGED_DIRS:
        root = os.path.join(base_dir, rel)
        if not os.path.isdir(root):
            continue
        for name in os.listdir(root):
            path = os.path.join(root, name)
            if os.path.isdir(path):
                patient_ids.add(name)
    return sorted(patient_ids)


def delete_patients(base_dir, patient_ids):
    deleted = []
    missing = []
    for patient_id in patient_ids:
        pid = safe_patient_id(patient_id)
        paths = existing_patient_paths(base_dir, pid)
        if not paths:
            missing.append(pid)
            continue
        for path in paths:
            shutil.rmtree(path)
        deleted.append(pid)
    return {"deleted": deleted, "missing": missing}


def unique_patient_id(base_dir, desired_id):
    base = safe_patient_id(desired_id) or "patient"
    candidate = base
    suffix = 2
    while any(os.path.exists(path) for path in patient_paths(base_dir, candidate)):
        candidate = f"{base}_{suffix}"
        suffix += 1
    return candidate


def move_patients(base_dir, patient_ids, target_name):
    target = safe_patient_id(target_name)
    if not target:
        raise ValueError("目标名称不能为空")

    moved = []
    missing = []
    multi = len(patient_ids) > 1
    for patient_id in patient_ids:
        pid = safe_patient_id(patient_id)
        paths = existing_patient_paths(base_dir, pid)
        if not paths:
            missing.append(pid)
            continue

        desired = f"{target}_{pid}" if multi else target
        new_pid = unique_patient_id(base_dir, desired)
        for old_path in paths:
            parent = os.path.dirname(old_path)
            os.makedirs(parent, exist_ok=True)
            shutil.move(old_path, os.path.join(parent, new_pid))
        moved.append({"from": pid, "to": new_pid})
    return {"moved": moved, "missing": missing}
