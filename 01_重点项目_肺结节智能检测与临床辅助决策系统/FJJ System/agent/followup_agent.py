from .llm_client import generate_with_local_qwen
from .guideline_rules import SAFETY_NOTE, guideline_hint_for_finding


def _to_float(value, default=0.0):
    try:
        if value in ("", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _has_text(value):
    return isinstance(value, str) and value.strip()


def _risk_from_finding(finding):
    malignancy_prob = _to_float(finding.get("malignancy_prob"))
    detection_prob = _to_float(finding.get("prob", finding.get("detection_prob")))
    status = finding.get("status")

    if status == "malignant" or malignancy_prob >= 0.7:
        return "high"
    if finding.get("source") == "doctor" and finding.get("doctor_confirmed"):
        return "medium"
    if malignancy_prob >= 0.4 or detection_prob >= 0.75:
        return "medium"
    return "low"


def _risk_label(risk_level):
    return {
        "high": "高风险",
        "medium": "中等风险",
        "low": "低风险",
    }.get(risk_level, "待评估")


def _rule_suggestion(risk_level, doctor_confirmed=False):
    prefix = "医生已复核该结节，" if doctor_confirmed else ""
    if risk_level == "high":
        return prefix + "建议优先结合薄层CT、既往影像对比和临床资料，由医生评估是否需要短期复查或进一步检查。"
    if risk_level == "medium":
        return prefix + "建议补充结节最大径、类型和既往CT对比信息，并由医生确定随访间隔。"
    return prefix + "当前结构化信息提示风险较低，但仍需结合结节大小、类型、危险因素和既往影像决定是否常规随访。"


def _format_feature_notes(features):
    if not isinstance(features, dict):
        return []
    labels = {
        "spiculation": "毛刺",
        "lobulation": "分叶",
        "pleural_indentation": "胸膜牵拉",
        "calcification": "钙化",
        "cavitation": "空洞/空泡",
        "solid_type": "结节类型",
    }
    notes = []
    for key, label in labels.items():
        value = features.get(key)
        if value not in ("", None, False):
            notes.append(f"{label}: {value}")
    return notes


def _rank_findings(findings, clinical_context=None):
    clinical_context = clinical_context or {}
    ranked = []
    for idx, finding in enumerate(findings or [], start=1):
        risk_level = _risk_from_finding(finding)
        doctor_notes = finding.get("doctor_assessment", "")
        basis = []

        if finding.get("source") == "doctor":
            basis.append("该结节由医生人工新增或确认，应优先纳入最终复核列表。")
        elif finding.get("doctor_confirmed"):
            basis.append("该模型候选结节已进入医生复核后的最终列表。")
        else:
            basis.append("该结节来自模型候选结果，仍需医生复核。")

        detection_prob = finding.get("prob", finding.get("detection_prob"))
        malignancy_prob = finding.get("malignancy_prob")
        if detection_prob not in ("", None):
            basis.append(f"检测置信度: {detection_prob}")
        if malignancy_prob not in ("", None):
            basis.append(f"恶性概率: {malignancy_prob}")
        if finding.get("diameter_mm"):
            basis.append(f"最大径: {finding.get('diameter_mm')} mm")
        if _has_text(doctor_notes):
            basis.append(f"医生意见: {doctor_notes}")

        feature_notes = _format_feature_notes(finding.get("imaging_features"))
        if feature_notes:
            basis.extend(feature_notes)
        else:
            basis.append("毛刺、分叶、胸膜牵拉、结节类型等细粒度影像征象仍依赖医生补充或后续模型扩展。")

        ranked.append({
            "nodule_id": finding.get("nodule_id") or f"N{idx}",
            "source": finding.get("source", "model"),
            "doctor_confirmed": bool(finding.get("doctor_confirmed")),
            "slice_idx": finding.get("slice_idx", finding.get("slice_index")),
            "x": finding.get("x"),
            "y": finding.get("y"),
            "bbox_3d": finding.get("bbox_3d", {}),
            "area": finding.get("area"),
            "diameter_mm": finding.get("diameter_mm"),
            "detection_prob": detection_prob,
            "malignancy_prob": malignancy_prob,
            "status": finding.get("status", "pending"),
            "doctor_assessment": doctor_notes,
            "imaging_features": finding.get("imaging_features", {}),
            "risk_level": risk_level,
            "risk_label": _risk_label(risk_level),
            "suggestion": _rule_suggestion(risk_level, bool(finding.get("doctor_confirmed"))),
            "guideline_hint": guideline_hint_for_finding(finding, clinical_context),
            "basis": basis,
        })

    return sorted(
        ranked,
        key=lambda item: (
            {"high": 3, "medium": 2, "low": 1}.get(item["risk_level"], 0),
            1 if item.get("source") == "doctor" else 0,
            _to_float(item.get("malignancy_prob")),
            _to_float(item.get("detection_prob")),
        ),
        reverse=True,
    )


def _risk_sections(ranked):
    sections = {"high": [], "medium": [], "low": []}
    for item in ranked:
        sections.setdefault(item["risk_level"], []).append(item)
    return sections


def _overall_risk(ranked):
    if any(item["risk_level"] == "high" for item in ranked):
        return "high"
    if any(item["risk_level"] == "medium" for item in ranked):
        return "medium"
    return "low"


def _clinical_missing(clinical_context):
    clinical_context = clinical_context or {}
    checks = [
        ("age", "患者年龄"),
        ("sex", "患者性别"),
        ("smoking_history", "吸烟史"),
        ("previous_ct", "既往CT对比"),
        ("tumor_history", "既往肿瘤史"),
        ("symptoms", "当前症状"),
    ]
    return [label for key, label in checks if not _has_text(str(clinical_context.get(key, "")).strip())]


def _statistics(ranked):
    return {
        "total_nodules": len(ranked),
        "model_count": sum(1 for item in ranked if item.get("source") != "doctor"),
        "doctor_added_count": sum(1 for item in ranked if item.get("source") == "doctor"),
        "doctor_confirmed_count": sum(1 for item in ranked if item.get("doctor_confirmed")),
        "high_count": sum(1 for item in ranked if item["risk_level"] == "high"),
        "medium_count": sum(1 for item in ranked if item["risk_level"] == "medium"),
        "low_count": sum(1 for item in ranked if item["risk_level"] == "low"),
    }


def _case_summary(patient_id, stats, overall_risk):
    return (
        f"病例 {patient_id} 最终纳入 {stats['total_nodules']} 个结节，"
        f"其中模型候选 {stats['model_count']} 个、医生新增 {stats['doctor_added_count']} 个、"
        f"医生确认 {stats['doctor_confirmed_count']} 个；总体风险分层为{_risk_label(overall_risk)}。"
    )


def _presentation_highlight(stats, overall_risk):
    return (
        "本阶段完成了AI检测-医生复核-临床补充-Agent建议的闭环升级。"
        f"系统可自动汇总 {stats['total_nodules']} 个结节并进行风险分层，"
        f"其中高风险 {stats['high_count']} 个、中等风险 {stats['medium_count']} 个、低风险 {stats['low_count']} 个，"
        f"当前病例总体判断为{_risk_label(overall_risk)}，可作为大创汇报中的智能辅助诊断流程亮点。"
    )


def _missing_information(ranked, clinical_context):
    missing = _clinical_missing(clinical_context)
    if ranked and not any(item.get("diameter_mm") for item in ranked):
        missing.append("结节最大径")
    if ranked and not any((item.get("imaging_features") or {}).get("solid_type") for item in ranked):
        missing.append("结节类型：实性、磨玻璃或部分实性")
    missing.extend([
        "毛刺、分叶、胸膜牵拉、空泡征、钙化等影像征象",
        "既往CT对比及结节增长情况",
        "医生对原始薄层CT的人工复核结论",
    ])
    return list(dict.fromkeys(missing))


def _build_prompt(patient_id, ranked, overall_risk, clinical_context):
    return f"""
你是肺结节CT辅助诊断系统中的随访建议助手。请根据结构化病例上下文生成简洁、谨慎、面向医生复核的中文说明。
硬性要求：
1. 不得使用“确诊”“一定是癌”“无需就医”等绝对化表达。
2. 医生复核、医生新增结节和医生补充病史的优先级高于模型原始判断。
3. 如果医生没有补充毛刺、分叶、胸膜牵拉、结节类型、最大径等信息，不要自行编造。
4. 建议必须是辅助参考，最终由医生结合临床资料决定。

病例ID：{patient_id}
总体风险：{_risk_label(overall_risk)}
临床信息：{clinical_context}
复核后结节列表：{ranked}

请输出三段：
- 病例概述
- 随访建议
- 仍需补充的信息
""".strip()


def build_followup_recommendation(patient_id, findings=None, case_context=None):
    case_context = case_context or {}
    clinical_context = case_context.get("clinical_context") or {}
    final_findings = case_context.get("final_nodules") if case_context else None
    final_findings = final_findings if final_findings is not None else (findings or [])
    ranked = _rank_findings(final_findings, clinical_context)

    if not ranked:
        missing = _clinical_missing(clinical_context) + [
            "医生对原始影像的人工复核结论",
            "结节最大径、类型和既往CT对比",
        ]
        stats = _statistics([])
        return {
            "patient_id": patient_id,
            "case_summary": f"病例 {patient_id} 当前最终上下文中未发现需要纳入随访建议的结节。",
            "risk_level": "low",
            "risk_label": "低风险",
            "statistics": stats,
            "risk_sections": {"high": [], "medium": [], "low": []},
            "followup_suggestion": "若临床仍有疑问，建议医生结合原始CT、症状和既往影像进行复核。",
            "recommendations": [],
            "clinical_context": clinical_context,
            "missing_information": list(dict.fromkeys(missing)),
            "presentation_highlight": "系统已具备AI检测-医生复核-临床补充-Agent建议的闭环框架，当前病例需先补充有效结节或人工复核结果。",
            "llm_summary": "",
            "llm_metadata": {"available": False, "reason": "no_findings"},
            "safety_note": SAFETY_NOTE,
        }

    overall_risk = _overall_risk(ranked)
    stats = _statistics(ranked)
    risk_sections = _risk_sections(ranked)

    if overall_risk == "high":
        followup_suggestion = "建议优先复核高风险结节，并结合医生补充信息、薄层CT、既往影像对比和指南化提示决定是否短期复查或进一步检查。"
    elif overall_risk == "medium":
        followup_suggestion = "建议结合医生复核意见，补充结节最大径、结节类型和既往影像变化后，再参照 Fleischner/Lung-RADS 场景确定随访间隔。"
    else:
        followup_suggestion = "整体风险较低，但仍建议以医生确认后的结节列表为准，结合患者危险因素决定是否常规随访。"

    prompt = _build_prompt(patient_id, ranked, overall_risk, clinical_context)
    llm_summary, llm_metadata = generate_with_local_qwen(prompt)

    return {
        "patient_id": patient_id,
        "case_summary": _case_summary(patient_id, stats, overall_risk),
        "risk_level": overall_risk,
        "risk_label": _risk_label(overall_risk),
        "statistics": stats,
        "risk_sections": risk_sections,
        "followup_suggestion": followup_suggestion,
        "recommendations": ranked,
        "clinical_context": clinical_context,
        "missing_information": _missing_information(ranked, clinical_context),
        "presentation_highlight": _presentation_highlight(stats, overall_risk),
        "llm_summary": llm_summary,
        "llm_metadata": llm_metadata,
        "safety_note": SAFETY_NOTE,
    }
