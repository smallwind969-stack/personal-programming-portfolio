"""
肺结节检测分类模型推理服务（FastAPI）

把原有的 FJJ System / DiagnosisEngine 封装成一个独立的、无前端的 ML 微服务，
对外提供两个推理接口和一个只读运行证据接口：

  GET  /health    健康检查
  POST /detect    结节检测（VNet 滑窗 -> ResNet 精筛）
  POST /identify  良恶性分类（DualBranchResNet）
  GET  /runs/{case_id}/{run_id}  读取服务端保存的该批次候选

启动：
  python app.py
默认监听 http://127.0.0.1:8100
"""

import os
import time
from copy import deepcopy
from hmac import compare_digest
from pathlib import Path
from typing import List
from uuid import uuid4

import torch
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from case_registry import CaseLookupError, resolve_case
from engine import DiagnosisEngine

BASE_DIR = Path(os.path.abspath(__file__)).parent

# ---------------------------------------------------------------------------
# 权重路径配置：默认复用同级的 FJJ System/models，可通过环境变量覆盖
# ---------------------------------------------------------------------------
def _weight(name, fallback):
    return os.getenv(name, str(fallback))


VNET_W = _weight(
    "VNET_W",
    BASE_DIR / ".." / ".." / "FJJ System" / "models" / "vnet_v6_7_sprint_recall_0.9648_epoch_41.pth",
)
RESNET_W = _weight(
    "RESNET_W",
    BASE_DIR / ".." / ".." / "FJJ System" / "models" / "fpr_v7_best_rec_0.9612.pth",
)
MALIG_W = _weight(
    "MALIG_W",
    BASE_DIR / ".." / ".." / "FJJ System" / "models" / "GOLDEN_Ep58_A0.923.pth",
)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

app = FastAPI(
    title="肺结节检测分类模型服务",
    description="Nexent 升级版模型推理微服务，供 MCP 工具调用",
    version="2.0.0",
)

# 懒加载引擎（首次调用时才加载权重，避免启动阻塞）
_engine = None
CANDIDATE_CACHE = {}


def get_engine() -> DiagnosisEngine:
    global _engine
    if _engine is None:
        for p in (VNET_W, RESNET_W, MALIG_W):
            if not Path(p).exists():
                raise RuntimeError(f"模型权重不存在: {p}")
        _engine = DiagnosisEngine(VNET_W, RESNET_W, MALIG_W, DEVICE)
    return _engine


# ---------------------------------------------------------------------------
# 请求/响应模型
# ---------------------------------------------------------------------------
class DetectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str = Field(..., pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


class IdentifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str = Field(..., pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    run_id: str = Field(..., min_length=1)
    candidate_ids: List[str] = Field(..., min_length=1)


def _require_token(authorization):
    expected = os.getenv("MODEL_SERVER_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="模型服务令牌尚未配置")
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    if not authorization or not authorization.startswith("Bearer ") or not compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="未授权的模型服务请求")


def _case_path(case_id):
    try:
        return resolve_case(case_id, os.getenv("DICOM_ROOT"), os.getenv("CASE_CATALOG_JSON"))
    except CaseLookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _public_finding(finding):
    allowed = {
        "candidate_id", "z_idx", "y_idx", "x_idx", "coordX", "coordY", "coordZ",
        "slice_idx", "x", "y", "area", "passed_filter",
    }
    out = {key: value for key, value in finding.items() if key in allowed}
    if "prob" in finding:
        out["detection_score"] = finding["prob"]
    out["review_status"] = "pending"
    return out


# ---------------------------------------------------------------------------
# 接口
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "device": str(DEVICE),
        "cuda_available": torch.cuda.is_available(),
        "weights": {
            "vnet": os.path.basename(VNET_W),
            "resnet": os.path.basename(RESNET_W),
            "malignancy": os.path.basename(MALIG_W),
        },
    }


@app.post("/detect")
def detect(req: DetectRequest, authorization: str = Header(default="")):
    _require_token(authorization)
    dicom_dir = _case_path(req.case_id)

    t0 = time.perf_counter()
    try:
        engine = get_engine()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    itk_img = engine.load_itk(dicom_dir)
    findings, timing = engine.run_inference(
        itk_img,
        prob_threshold=float(os.getenv("DETECT_PROB_THRESHOLD", "0.15")),
        resnet_threshold=float(os.getenv("DETECT_RESNET_THRESHOLD", "0.4")),
        patch_size=64,
        stride=32,
        return_all_candidates=False,
    )
    timing["api_total_sec"] = round(time.perf_counter() - t0, 4)
    cached = {}
    for index, finding in enumerate(findings, start=1):
        candidate_id = f"c{index:03d}"
        cached[candidate_id] = {**finding, "candidate_id": candidate_id}
    run_id = uuid4().hex
    public = {candidate_id: _public_finding(item) for candidate_id, item in cached.items()}
    CANDIDATE_CACHE[req.case_id] = {
        "run_id": run_id,
        "dicom_dir": dicom_dir,
        "candidates": cached,
        "public_findings": public,
    }
    return {"case_id": req.case_id, "run_id": run_id, "findings": list(public.values()), "timing": timing}


@app.post("/identify")
def identify(req: IdentifyRequest, authorization: str = Header(default="")):
    _require_token(authorization)
    dicom_dir = _case_path(req.case_id)
    detected = CANDIDATE_CACHE.get(req.case_id)
    if not detected or detected["run_id"] != req.run_id or detected["dicom_dir"] != dicom_dir:
        raise HTTPException(status_code=409, detail="检测批次已失效；请先重新检测")
    cached = detected["candidates"]
    if len(set(req.candidate_ids)) != len(req.candidate_ids) or any(item not in cached for item in req.candidate_ids):
        raise HTTPException(status_code=400, detail="候选 ID 不存在或重复；请先重新检测")

    t0 = time.perf_counter()
    try:
        engine = get_engine()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    itk_img = engine.load_itk(dicom_dir)
    findings, timing = engine.identify_malignancy(itk_img, [deepcopy(cached[item]) for item in req.candidate_ids])
    timing["api_total_sec"] = round(time.perf_counter() - t0, 4)
    public = []
    for finding in findings:
        item = _public_finding(finding)
        item["model_score"] = finding.get("malignancy_prob")
        public.append(item)
        detected["public_findings"][item["candidate_id"]] = item
    return {"case_id": req.case_id, "run_id": req.run_id, "findings": public, "timing": timing}


@app.get("/runs/{case_id}/{run_id}")
def get_run_evidence(case_id: str, run_id: str, authorization: str = Header(default="")):
    _require_token(authorization)
    dicom_dir = _case_path(case_id)
    detected = CANDIDATE_CACHE.get(case_id)
    if not detected or detected["run_id"] != run_id or detected["dicom_dir"] != dicom_dir:
        raise HTTPException(status_code=404, detail="未找到该病例的有效运行批次")
    return {
        "case_id": case_id,
        "run_id": run_id,
        "findings": deepcopy(list(detected["public_findings"].values())),
    }


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("MODEL_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MODEL_SERVER_PORT", "8100"))
    print(f">>> 模型推理服务启动: http://{host}:{port}  (device={DEVICE})")
    uvicorn.run(app, host=host, port=port)
