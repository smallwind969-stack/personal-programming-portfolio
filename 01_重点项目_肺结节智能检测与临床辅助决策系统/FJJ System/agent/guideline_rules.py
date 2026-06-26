SAFETY_NOTE = (
    "本建议为AI辅助分析结果，不能替代影像科、呼吸科或胸外科医生的诊断和管理决策。"
)


def to_float(value, default=0.0):
    try:
        if value in ("", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def has_text(value):
    return isinstance(value, str) and value.strip()


def normalize_nodule_type(value):
    text = str(value or "").strip().lower()
    if any(key in text for key in ("部分实性", "part", "part-solid", "mixed")):
        return "part_solid"
    if any(key in text for key in ("磨玻璃", "ground", "ggn", "subsolid", "亚实性")):
        return "ground_glass"
    if any(key in text for key in ("实性", "solid")):
        return "solid"
    return "unknown"


def patient_risk_level(clinical_context):
    clinical_context = clinical_context or {}
    age = to_float(clinical_context.get("age"))
    smoking = str(clinical_context.get("smoking_history", "")).strip().lower()
    tumor = str(clinical_context.get("tumor_history", "")).strip().lower()
    if age >= 50:
        return "high"
    if any(signal in smoking for signal in ("有", "吸烟", "长期", "重度", "yes", "current", "former")):
        return "high"
    if any(signal in tumor for signal in ("有", "恶性", "肿瘤", "癌", "yes")):
        return "high"
    return "low"


def guideline_applicability(clinical_context):
    scenario = str((clinical_context or {}).get("scenario", "")).strip().lower()
    if "screen" in scenario or "筛查" in scenario:
        return {
            "primary_framework": "Lung-RADS/NCCN",
            "applicability": "可能属于肺癌筛查场景，应优先使用 Lung-RADS/NCCN，并由医生确认筛查资格。",
        }
    return {
        "primary_framework": "Fleischner 2017",
        "applicability": "按偶发肺结节辅助提示处理；若实际为筛查、已知肿瘤或免疫抑制人群，应改用相应临床路径。",
    }


def suspicious_features(finding):
    features = finding.get("imaging_features") or {}
    signals = []
    for key, label in (
        ("spiculation", "毛刺"),
        ("lobulation", "分叶"),
        ("pleural_indentation", "胸膜牵拉"),
        ("cavitation", "空泡/空洞"),
    ):
        value = str(features.get(key, "")).strip()
        if value and value not in {"未见", "无", "否", "false", "False"}:
            signals.append(label)
    return signals


def guideline_missing_inputs(finding, clinical_context):
    missing = []
    if to_float(finding.get("diameter_mm")) <= 0:
        missing.append("结节最大径")
    if normalize_nodule_type((finding.get("imaging_features") or {}).get("solid_type")) == "unknown":
        missing.append("结节类型：实性、磨玻璃或部分实性")
    if not has_text(str((clinical_context or {}).get("previous_ct", "")).strip()):
        missing.append("既往CT对比或增长情况")
    if not has_text(str((clinical_context or {}).get("smoking_history", "")).strip()):
        missing.append("吸烟史/高危因素")
    return missing


def fleischner_hint(finding, clinical_context):
    diameter = to_float(finding.get("diameter_mm"))
    nodule_type = normalize_nodule_type((finding.get("imaging_features") or {}).get("solid_type"))
    patient_risk = patient_risk_level(clinical_context)
    suspicious = suspicious_features(finding)
    missing = guideline_missing_inputs(finding, clinical_context)

    if diameter <= 0 or nodule_type == "unknown":
        recommendation = "指南化随访建议暂不能精确生成；需先补充结节最大径和结节类型。"
    elif nodule_type == "solid":
        if diameter < 6:
            recommendation = "通常不需要常规随访；若存在高危因素或可疑形态，可由医生考虑约12个月CT复查。"
        elif diameter <= 8:
            recommendation = "通常建议6-12个月CT复查；高危患者或可疑形态可考虑18-24个月再次复查。"
        else:
            recommendation = "建议医生评估约3个月CT复查、PET/CT、组织取样或其他进一步检查的必要性。"
    elif nodule_type == "ground_glass":
        if diameter < 6:
            recommendation = "通常不需要常规随访；仍需结合医生对形态和病史的判断。"
        else:
            recommendation = "通常建议6-12个月CT确认是否持续存在；若稳定，可考虑每2年随访至5年。"
    else:
        if diameter < 6:
            recommendation = "需医生确认是否为真正部分实性结节；小结节一般以复核形态和既往对比为先。"
        else:
            recommendation = "通常建议3-6个月CT确认持续存在；若稳定且实性成分小于6 mm，可考虑年度随访至5年。"

    if suspicious:
        recommendation += " 因存在可疑影像征象，应提高医生复核优先级。"

    return {
        "framework": "Fleischner 2017",
        "patient_risk": patient_risk,
        "nodule_type": nodule_type,
        "diameter_mm": diameter or None,
        "recommendation": recommendation,
        "basis": "辅助提示依据 Fleischner 2017 的大小、密度和风险分层原则改写，不能替代医生决策。",
        "missing_inputs": missing,
        "suspicious_features": suspicious,
    }


def guideline_hint_for_finding(finding, clinical_context):
    hint = fleischner_hint(finding, clinical_context)
    hint.update(guideline_applicability(clinical_context))
    return hint


BANNED_PHRASES = [
    "确诊为癌",
    "一定是癌",
    "无需就医",
    "不用复查",
    "可以替代医生",
    "替代医生诊断",
    "保证治愈",
    "保证无风险",
]


def audit_agent_text(text):
    text = text or ""
    violations = [phrase for phrase in BANNED_PHRASES if phrase in text]
    return {
        "passed": not violations and SAFETY_NOTE in text,
        "violations": violations,
        "has_safety_note": SAFETY_NOTE in text,
    }
