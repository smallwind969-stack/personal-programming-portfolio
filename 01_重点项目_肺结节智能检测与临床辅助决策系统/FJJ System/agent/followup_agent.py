from .llm_client import generate_with_llm_api
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


def _valid_diameter(value):
    diameter = _to_float(value, default=-1)
    return diameter if diameter > 0 else None


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
        diameter = _valid_diameter(finding.get("diameter_mm"))
        if diameter is not None:
            basis.append(f"最大径: {diameter:g} mm")
        elif finding.get("diameter_mm") not in ("", None):
            basis.append("最大径数值无效，需重新测量")
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
            "diameter_mm": diameter,
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


def _finding_feature_summary(item):
    features = item.get("imaging_features") or {}
    labels = []
    solid_type = features.get("solid_type")
    if solid_type:
        labels.append(f"类型{solid_type}")
    if features.get("spiculation") in ("可疑", "明确"):
        labels.append(f"毛刺{features.get('spiculation')}")
    if features.get("lobulation") in ("可疑", "明确"):
        labels.append(f"分叶{features.get('lobulation')}")
    if features.get("pleural_indentation") in ("可疑", "明确"):
        labels.append(f"胸膜牵拉{features.get('pleural_indentation')}")
    if item.get("diameter_mm"):
        labels.append(f"最大径{item.get('diameter_mm'):g}mm")
    if item.get("malignancy_prob") not in ("", None):
        labels.append(f"恶性概率{item.get('malignancy_prob')}")
    elif item.get("detection_prob") not in ("", None):
        labels.append(f"检测置信度{item.get('detection_prob')}")
    return "，".join(labels) if labels else "关键影像征象/最大径未补齐"


def _prompt_case_digest(patient_id, ranked, overall_risk, clinical_context):
    stats = _statistics(ranked)
    missing = _missing_information(ranked, clinical_context)[:6]
    priority = []
    for idx, item in enumerate(ranked[:5], start=1):
        source = "医生新增/确认" if item.get("source") == "doctor" else "AI候选已复核"
        priority.append(
            f"{idx}. {source}，层面{item.get('slice_idx', 'N/A')}，"
            f"{item.get('risk_label', '待评估')}，{_finding_feature_summary(item)}"
        )
    if not priority:
        priority.append("当前无有效结节进入复核列表。")

    return {
        "patient_id": patient_id,
        "overall_risk": _risk_label(overall_risk),
        "statistics": {
            "total": stats["total_nodules"],
            "high": stats["high_count"],
            "medium": stats["medium_count"],
            "low": stats["low_count"],
            "doctor_added": stats["doctor_added_count"],
            "doctor_confirmed": stats["doctor_confirmed_count"],
        },
        "clinical_context": clinical_context,
        "priority_findings": priority,
        "missing_information": missing,
    }


def _build_prompt(patient_id, ranked, overall_risk, clinical_context):
    digest = _prompt_case_digest(patient_id, ranked, overall_risk, clinical_context)
    return f"""
你是肺结节 CT 医生复核工作台里的 Agent。请输出“给医生看的复核建议”，不是病例字段转述。

输入摘要：
{digest}

硬性要求：
1. 必须用中文，控制在 350-550 字。
2. 不要逐条罗列所有结节，不要输出内部 nodule_id，不要复述坐标清单。
3. 只挑 2-4 个最值得优先复核的影像问题，说明为什么优先。
4. 负数、0 或缺失的最大径必须视为“测量无效/待补测”，不能当作真实直径。
5. 不要生成“确诊肺癌”“必须手术”等诊断或治疗结论，只能给辅助复核路径。
6. 不要重复输出“仍需补充的信息”清单，系统界面会单独显示。
7. 如果临床信息缺失，要说“当前无法形成最终随访间隔”，但要给出下一步工作顺序。

请严格按以下三段输出：
### 复核判断
用 2-3 句话概括当前风险和主要限制。
### 优先处理
列 2-4 条医生下一步最应该先看的内容。
### 建议路径
给出短期工作流建议：薄层 CT/MPR 复核、统一测量、去重合并、补临床背景、再套用指南。
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
        pending_count = sum(
            1 for item in case_context.get("model_findings", [])
            if item.get("status") != "dismissed" and not item.get("doctor_confirmed")
        )
        return {
            "patient_id": patient_id,
            "case_summary": f"病例 {patient_id} 尚无医生确认的结节；{pending_count} 个模型候选待复核。",
            "risk_level": "not_assessed",
            "risk_label": "待复核",
            "statistics": stats,
            "risk_sections": {"high": [], "medium": [], "low": []},
            "followup_suggestion": "请医生先复核模型候选和原始影像，再决定是否形成随访建议。",
            "recommendations": [],
            "clinical_context": clinical_context,
            "missing_information": list(dict.fromkeys(missing)),
            "presentation_highlight": "当前病例尚未完成医生复核，不能依据模型候选给出风险结论。",
            "llm_summary": "尚无医生确认的结节，暂不生成大模型随访建议。",
            "llm_metadata": {"available": False, "reason": "review_required"},
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
    llm_summary, llm_metadata = generate_with_llm_api(prompt)

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
