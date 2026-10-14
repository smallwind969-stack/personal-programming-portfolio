import os
import uuid
import time
import csv
from datetime import datetime

import torch
import numpy as np
import SimpleITK as sitk
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from PIL import Image
from engine import DiagnosisEngine
from agent.llm_client import LLMClientError
from agent.followup_agent import build_followup_recommendation
from doctor_review import load_review, merge_case_context, save_review
from model_run_evidence import EvidenceError, fetch_verified_run
from patient_storage import delete_patients, list_patients, move_patients

base_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(base_dir, 'templates'),
    static_folder=os.path.join(base_dir, 'static')
)
app.config['JSON_AS_ASCII'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
CORS(app)

# 路径配置
UPLOAD_FOLDER = os.path.join(base_dir, 'uploads')
PROCESSED_FOLDER = os.path.join(base_dir, 'static', 'processed')
TIMING_CSV = os.path.join(base_dir, 'timing_results.csv')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# 模型权重路径
VNET_W = os.path.join(base_dir, 'models', 'vnet_v6_7_sprint_recall_0.9648_epoch_41.pth')
RESNET_W = os.path.join(base_dir, 'models', 'fpr_v7_best_rec_0.9612.pth')
MALIG_W = os.path.join(base_dir, 'models', 'GOLDEN_Ep58_A0.923.pth')

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 初始化引擎
engine = DiagnosisEngine(VNET_W, RESNET_W, MALIG_W, DEVICE)

# 用于缓存一次完整测试过程中的时间信息
TIMING_CACHE = {}


def flatten_dict(d, parent_key="", sep="."):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def safe_patient_id(value):
    raw = os.path.basename(str(value)).strip() or str(uuid.uuid4())[:8]
    return "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in raw)[:80]


def split_upload_path(filename):
    parts = str(filename or "").replace("\\", "/").split("/")
    return [part for part in parts if part and part not in (".", "..")]


def group_uploaded_files(files):
    paths = [(f, split_upload_path(f.filename)) for f in files]
    roots = {parts[0] for _, parts in paths if parts}
    second_level = {parts[1] for _, parts in paths if len(parts) >= 3}
    has_root_files = any(len(parts) <= 2 for _, parts in paths)

    use_second_level = len(roots) == 1 and len(second_level) > 1 and not has_root_files
    groups = {}
    fallback_pid = str(uuid.uuid4())[:8]
    for file_storage, parts in paths:
        if not parts:
            pid = fallback_pid
        elif len(parts) == 1:
            pid = fallback_pid
        elif use_second_level:
            pid = parts[1]
        else:
            pid = parts[0]
        groups.setdefault(safe_patient_id(pid), []).append(file_storage)
    return groups


def process_patient_upload(pid, files, api_start=None):
    api_start = api_start if api_start is not None else time.perf_counter()
    raw_path = os.path.join(UPLOAD_FOLDER, pid)
    static_path = os.path.join(PROCESSED_FOLDER, pid)
    os.makedirs(raw_path, exist_ok=True)
    os.makedirs(static_path, exist_ok=True)

    t0 = time.perf_counter()
    saved_count = 0
    for idx, f in enumerate(files):
        filename = os.path.basename(f.filename) or f"slice_{idx:04d}.dcm"
        f.save(os.path.join(raw_path, filename))
        saved_count += 1
    t1 = time.perf_counter()

    itk_img = engine.load_itk(raw_path)
    vol = sitk.GetArrayFromImage(itk_img)
    t2 = time.perf_counter()

    disp = (np.clip(vol, -1200, 600) + 1200) / 1800.0 * 255
    for i in range(disp.shape[0]):
        Image.fromarray(disp[i].astype('uint8')).save(
            os.path.join(static_path, f'slice_{i:03d}.png')
        )
    t3 = time.perf_counter()

    timing = {
        "file_count": saved_count,
        "save_files_sec": round(t1 - t0, 4),
        "load_dicom_sec": round(t2 - t1, 4),
        "generate_preview_sec": round(t3 - t2, 4),
        "total_upload_sec": round(t3 - api_start, 4)
    }
    TIMING_CACHE[pid] = {"upload": timing}
    print(f"[UPLOAD TIMING] patient={pid} | {timing}", flush=True)
    return {
        "patient_id": pid,
        "file_count": saved_count,
        "timing": timing,
    }


def save_complete_test_to_csv(patient_id):
    """
    只有在 upload + detect + identify 都完成后，才写入一条完整记录
    """
    if patient_id not in TIMING_CACHE:
        return

    cache = TIMING_CACHE[patient_id]

    # 三步都齐了才写
    if not all(k in cache for k in ["upload", "detect", "identify"]):
        return

    row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "patient_id": patient_id
    }

    # 总响应时间
    upload_total = cache["upload"].get("total_upload_sec", 0.0)
    detect_total = cache["detect"].get("total_detect_sec", 0.0)
    identify_total = cache["identify"].get("total_identify_sec", 0.0)

    row["upload_total_sec"] = upload_total
    row["detect_total_sec"] = detect_total
    row["identify_total_sec"] = identify_total
    row["whole_pipeline_total_sec"] = round(upload_total + detect_total + identify_total, 4)

    # 上传阶段
    row.update({f"upload.{k}": v for k, v in flatten_dict(cache["upload"]).items()})

    # 检测阶段
    row.update({f"detect.{k}": v for k, v in flatten_dict(cache["detect"]).items()})

    # 识别阶段
    row.update({f"identify.{k}": v for k, v in flatten_dict(cache["identify"]).items()})

    file_exists = os.path.exists(TIMING_CSV)

    if not file_exists:
        with open(TIMING_CSV, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(row.keys()))
            writer.writeheader()
            writer.writerow(row)
    else:
        with open(TIMING_CSV, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            old_rows = list(reader)
            old_fields = reader.fieldnames if reader.fieldnames else []

        all_fields = list(dict.fromkeys(old_fields + list(row.keys())))

        with open(TIMING_CSV, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=all_fields)
            writer.writeheader()
            for old_row in old_rows:
                writer.writerow(old_row)
            writer.writerow(row)

    print(f">>> 已保存完整测试结果到 CSV: {TIMING_CSV}", flush=True)

    # 写完就清掉当前病例缓存，避免重复叠加
    del TIMING_CACHE[patient_id]


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/get_patients')
def get_patients():
    return jsonify({"patients": list_patients(base_dir)})


@app.route('/get_patient_detail/<pid>')
def get_detail(pid):
    path = os.path.join(PROCESSED_FOLDER, pid)
    if not os.path.isdir(path):
        return jsonify({"images": [], "status": "no_processed_images"})
    imgs = sorted([f for f in os.listdir(path) if f.endswith('.png')])
    return jsonify({"images": imgs})


@app.route('/patients/delete', methods=['POST'])
def delete_patient_records():
    data = request.json or {}
    patient_ids = data.get('patient_ids') or data.get('patients') or []
    if isinstance(patient_ids, str):
        patient_ids = [patient_ids]
    if not patient_ids:
        return jsonify({"status": "error", "message": "缺少 patient_ids"}), 400

    result = delete_patients(base_dir, patient_ids)
    for pid in result["deleted"]:
        TIMING_CACHE.pop(pid, None)
    return jsonify({"status": "success", **result})


@app.route('/patients/move', methods=['POST'])
def move_patient_records():
    data = request.json or {}
    patient_ids = data.get('patient_ids') or data.get('patients') or []
    if isinstance(patient_ids, str):
        patient_ids = [patient_ids]
    target_name = data.get('target_name') or data.get('target') or ""
    if not patient_ids:
        return jsonify({"status": "error", "message": "缺少 patient_ids"}), 400
    try:
        result = move_patients(base_dir, patient_ids, target_name)
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400

    for item in result["moved"]:
        cached = TIMING_CACHE.pop(item["from"], None)
        if cached is not None:
            TIMING_CACHE[item["to"]] = cached
    return jsonify({"status": "success", **result})


@app.route('/upload', methods=['POST'])
def upload():
    api_start = time.perf_counter()

    files = request.files.getlist('files')
    if not files:
        return jsonify({"status": "error", "message": "未接收到上传文件"}), 400

    results = []
    errors = []
    for pid, patient_files in group_uploaded_files(files).items():
        try:
            results.append(process_patient_upload(pid, patient_files, api_start=api_start))
        except Exception as exc:
            errors.append({
                "patient_id": pid,
                "message": str(exc),
            })

    if not results:
        return jsonify({
            "status": "error",
            "message": "未能成功解析上传的 DICOM 病例",
            "errors": errors,
        }), 400

    return jsonify({
        "status": "partial_success" if errors else "success",
        "patient_id": results[0]["patient_id"],
        "patient_ids": [item["patient_id"] for item in results],
        "patients": results,
        "errors": errors,
        "timing": {
            "total_upload_sec": round(time.perf_counter() - api_start, 4),
            "patient_count": len(results),
        }
    })

@app.route('/detect')
def detect():
    api_start = time.perf_counter()

    pid = request.args.get('patient_id')
    if not pid:
        return jsonify({"status": "error", "message": "缺少 patient_id"}), 400

    try:
        prob_threshold = float(request.args.get('prob_threshold', 0.15))
        resnet_threshold = float(request.args.get('resnet_threshold', 0.4))
        patch_size = int(request.args.get('patch_size', 64))
        stride = int(request.args.get('stride', 32))
        return_all_candidates = str(request.args.get('return_all_candidates', 'false')).lower() in ('1', 'true', 'yes')
    except ValueError:
        return jsonify({"status": "error", "message": "检测参数格式错误"}), 400

    t0 = time.perf_counter()
    itk_img = engine.load_itk(os.path.join(UPLOAD_FOLDER, pid))
    t1 = time.perf_counter()

    findings, engine_timing = engine.run_inference(
        itk_img,
        prob_threshold=prob_threshold,
        resnet_threshold=resnet_threshold,
        patch_size=patch_size,
        stride=stride,
        return_all_candidates=return_all_candidates,
    )
    t2 = time.perf_counter()

    timing = {
        "load_itk_sec": round(t1 - t0, 4),
        "engine_detect_sec": round(t2 - t1, 4),
        "total_detect_sec": round(t2 - api_start, 4),
        "engine_detail": engine_timing
    }

    if pid not in TIMING_CACHE:
        TIMING_CACHE[pid] = {}
    TIMING_CACHE[pid]["detect"] = timing

    print(f"[DETECT TIMING] patient={pid} | findings={len(findings)} | {timing}", flush=True)

    return jsonify({
        "findings": findings,
        "timing": timing
    })


@app.route('/identify', methods=['POST'])
def identify():
    api_start = time.perf_counter()

    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "缺少 JSON 数据"}), 400

    pid = data.get('patient_id')
    findings = data.get('findings', [])

    if not pid:
        return jsonify({"status": "error", "message": "缺少 patient_id"}), 400

    t0 = time.perf_counter()
    itk_img = engine.load_itk(os.path.join(UPLOAD_FOLDER, pid))
    t1 = time.perf_counter()

    real_findings, engine_timing = engine.identify_malignancy(itk_img, findings)
    t2 = time.perf_counter()

    timing = {
        "load_itk_sec": round(t1 - t0, 4),
        "engine_identify_sec": round(t2 - t1, 4),
        "total_identify_sec": round(t2 - api_start, 4),
        "engine_detail": engine_timing
    }

    if pid not in TIMING_CACHE:
        TIMING_CACHE[pid] = {}
    TIMING_CACHE[pid]["identify"] = timing

    print(f"[IDENTIFY TIMING] patient={pid} | nodules={len(real_findings)} | {timing}", flush=True)

    # 到这一步，三步都齐了，保存一次完整测试结果
    save_complete_test_to_csv(pid)

    return jsonify({
        "findings": real_findings,
        "timing": timing
    })


@app.route('/agent/followup', methods=['POST'])
def agent_followup():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "缺少 JSON 数据"}), 400

    pid = data.get('patient_id')
    if not pid:
        return jsonify({"status": "error", "message": "缺少 patient_id"}), 400

    # 随访只读取服务端已保存的医生复核；浏览器传来的模型发现/复核 JSON 不作证据。
    review = load_review(base_dir, pid)

    case_context = merge_case_context(
        pid,
        findings=[],
        review=review,
        clinical_context={},
    )
    try:
        result = build_followup_recommendation(pid, [], case_context=case_context)
    except LLMClientError as exc:
        return jsonify({
            "status": "error",
            "message": str(exc),
            "case_context": case_context,
        }), 502

    return jsonify({
        "status": "success",
        "case_context": case_context,
        "followup": result
    })


@app.route('/agent/verify-run', methods=['POST'])
def verify_model_run():
    origin = request.headers.get('Origin')
    if origin and origin.rstrip('/') != request.host_url.rstrip('/'):
        return jsonify({"status": "error", "message": "只允许当前工作台核验运行记录"}), 403
    data = request.get_json(silent=True) or {}
    case_id = data.get('case_id', '')
    run_id = data.get('run_id', '')
    if case_id not in list_patients(base_dir):
        return jsonify({"status": "error", "message": "请先选择已导入的演示病例"}), 404
    try:
        evidence = fetch_verified_run(
            case_id, run_id,
            os.getenv('MODEL_SERVER_URL', 'http://127.0.0.1:8100'),
            os.getenv('MODEL_SERVER_TOKEN', ''),
        )
    except EvidenceError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 422
    return jsonify({"status": "success", "evidence": evidence})


@app.route('/doctor/review/<pid>', methods=['GET'])
def get_doctor_review(pid):
    return jsonify({
        "status": "success",
        "review": load_review(base_dir, pid)
    })


@app.route('/doctor/review/save', methods=['POST'])
def save_doctor_review():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "缺少 JSON 数据"}), 400

    pid = data.get('patient_id')
    if not pid:
        return jsonify({"status": "error", "message": "缺少 patient_id"}), 400

    review = save_review(
        base_dir,
        pid,
        findings=data.get('findings', []),
        doctor_nodules=data.get('doctor_nodules', []),
        clinical_context=data.get('clinical_context', {}),
    )
    return jsonify({
        "status": "success",
        "review": review
    })


if __name__ == '__main__':
    print(f">>> 当前 app2.py 路径: {os.path.abspath(__file__)}", flush=True)
    print(f">>> CSV 保存路径: {TIMING_CSV}", flush=True)
    app.run(host='127.0.0.1', port=5001, debug=False)

