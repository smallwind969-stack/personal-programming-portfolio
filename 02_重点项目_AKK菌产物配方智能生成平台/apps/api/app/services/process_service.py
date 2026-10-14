from __future__ import annotations

from math import exp
from uuid import uuid4

from app.schemas.process import (
    CandidatePlan,
    ExperimentFeedback,
    ExperimentFeedbackRequest,
    GeneratedProcessTask,
    NumericRange,
    ProcessTaskRequest,
    ProductionLineProfile,
    RecommendationReport,
    RecommendedParameters,
    ResponseSurface,
    ScoreBreakdown,
    SurfacePoint,
)


DISCLAIMER = "内部研发实验建议：所有预测和参数窗口仅用于小试/中试设计，不作为最终生产配方或真实生产指令。"


PRODUCTION_LINES = [
    ProductionLineProfile(
        lineId="lab-anaerobic-a",
        lineName="小试厌氧发酵平台 A",
        equipmentType="厌氧小试发酵系统",
        workingVolume="2-10 L",
        temperatureRange=NumericRange(min=25, max=42, unit="℃"),
        phRange=NumericRange(min=5.5, max=8.0, unit="pH"),
        agitationRange=NumericRange(min=80, max=500, unit="rpm"),
        anaerobicCapability="支持氮气置换与厌氧维持",
        aerationCapability="支持氮气、二氧化碳和微量空气切换",
        sensors=["温度", "pH", "ORP", "搅拌转速"],
        downstreamCapabilities=["离心", "过滤", "低温保存"],
        feasibilityScore=88,
        dataCompleteness="中",
        limitations=["在线目标产物浓度检测不足", "放大验证能力有限"],
    ),
    ProductionLineProfile(
        lineId="pilot-anaerobic-b",
        lineName="中试厌氧发酵罐 B",
        equipmentType="中试发酵罐",
        workingVolume="50-200 L",
        temperatureRange=NumericRange(min=28, max=40, unit="℃"),
        phRange=NumericRange(min=6.0, max=7.6, unit="pH"),
        agitationRange=NumericRange(min=60, max=420, unit="rpm"),
        anaerobicCapability="支持稳定厌氧控制和批次记录",
        aerationCapability="支持氮气、二氧化碳、空气比例控制",
        sensors=["温度", "pH", "ORP", "DO", "搅拌转速", "通气流量"],
        downstreamCapabilities=["离心", "膜过滤", "浓缩", "冻干"],
        feasibilityScore=84,
        dataCompleteness="中",
        limitations=["pH 窄窗口控制需复核", "共培养比例需要小试验证"],
    ),
    ProductionLineProfile(
        lineId="coculture-reactor-c",
        lineName="菌藻共培养反应器 C",
        equipmentType="共培养反应器",
        workingVolume="5-50 L",
        temperatureRange=NumericRange(min=20, max=38, unit="℃"),
        phRange=NumericRange(min=6.2, max=8.2, unit="pH"),
        agitationRange=NumericRange(min=40, max=300, unit="rpm"),
        anaerobicCapability="支持分阶段厌氧和微氧切换",
        aerationCapability="支持二氧化碳补充和低通气培养",
        sensors=["温度", "pH", "ORP", "光照", "通气流量"],
        downstreamCapabilities=["离心", "过滤", "避光保存"],
        feasibilityScore=76,
        dataCompleteness="低",
        limitations=["共培养历史数据较少", "放大风险较高", "在线活性检测不足"],
    ),
]


def list_production_lines() -> list[ProductionLineProfile]:
    return PRODUCTION_LINES


def generate_process_task(payload: ProcessTaskRequest) -> GeneratedProcessTask:
    line = _find_line(payload.productionLineId)
    plans = _build_candidate_plans(payload, line)
    selected_plan = max(plans, key=lambda plan: plan.scoreBreakdown.overallScore)
    return GeneratedProcessTask(
        taskId=f"process-{uuid4().hex[:8]}",
        targetSummary=(
            f"{payload.targetProductName}，{payload.targetProductForm}，需要 {payload.akkProductType}；"
            f"目标含量：{payload.targetContent}；活性：{payload.activityTarget}；"
            f"稳定性：{payload.stabilityTarget}"
        ),
        selectedLine=line,
        candidatePlans=plans,
        surface=_build_surface(payload, line),
        report=_build_report(payload, line, selected_plan),
        disclaimer="内部研发实验建议",
    )


def create_feedback(payload: ExperimentFeedbackRequest) -> ExperimentFeedback:
    return ExperimentFeedback(feedbackId=f"feedback-{uuid4().hex[:8]}", **payload.model_dump())


def _find_line(line_id: str) -> ProductionLineProfile:
    for line in PRODUCTION_LINES:
        if line.lineId == line_id:
            return line
    return PRODUCTION_LINES[0]


def _build_candidate_plans(payload: ProcessTaskRequest, line: ProductionLineProfile) -> list[CandidatePlan]:
    current_temp = payload.currentTemperature or 36.0
    current_ph = payload.currentPh or 6.8
    current_rpm = payload.currentAgitationRpm or 160
    line_fit = _line_fit(line, current_temp, current_ph, current_rpm)
    co_note = "共培养比例先从低比例窗口验证。" if payload.allowCoCulture else "本轮不启用共培养比例。"

    specs = [
        {
            "planId": "plan-conservative",
            "planType": "conservativeValidation",
            "displayName": "保守验证方案",
            "summary": "优先降低失败概率，适合首轮小试或产线数据不足时使用。",
            "temp": (35.8, 36.8),
            "ph": (6.8, 7.1),
            "hours": (36, 44),
            "rpm": (150, 190),
            "inoculation": "3.0%-4.5%",
            "coCulture": "1.0%-2.0%" if payload.allowCoCulture else None,
            "yield": 78,
            "activity": 86,
            "stability": 88,
            "cost": 86,
            "risk": 90,
            "riskItems": ["目标产物上限偏保守", "需要补充目标产物含量检测"],
            "explanation": ["参数窗口较宽，便于确认产线稳定性。", "优先避开 pH 窄窗口。", co_note],
        },
        {
            "planId": "plan-output",
            "planType": "outputEnhancement",
            "displayName": "强化产出方案",
            "summary": "优先提高目标产物表现，适合已有基础数据后做产出强化验证。",
            "temp": (37.0, 37.8),
            "ph": (6.6, 6.9),
            "hours": (46, 54),
            "rpm": (210, 260),
            "inoculation": "4.5%-6.5%",
            "coCulture": "2.0%-5.0%" if payload.allowCoCulture else None,
            "yield": 92,
            "activity": 80,
            "stability": 76,
            "cost": 68,
            "risk": 72,
            "riskItems": ["控制窗口较窄", "培养周期更长", "成本和污染风险上升"],
            "explanation": ["更偏向目标产物得分。", "需要更严格复核 pH、ORP 和污染指标。", co_note],
        },
        {
            "planId": "plan-balance",
            "planType": "processBalance",
            "displayName": "工艺平衡方案",
            "summary": "兼顾产物、活性、稳定性、成本和放大风险，适合作为默认中试窗口。",
            "temp": (36.4, 37.2),
            "ph": (6.75, 7.05),
            "hours": (42, 48),
            "rpm": (180, 220),
            "inoculation": "3.8%-5.5%",
            "coCulture": "1.5%-4.0%" if payload.allowCoCulture else None,
            "yield": 86,
            "activity": 84,
            "stability": 86,
            "cost": 80,
            "risk": 82,
            "riskItems": ["共培养兼容性需小试确认" if payload.allowCoCulture else "仍需复核批次稳定性"],
            "explanation": ["综合评分更均衡，适合作为建议书默认方案。", "参数窗口兼顾放大可执行性。", co_note],
        },
    ]

    plans: list[CandidatePlan] = []
    for spec in specs:
        score = _score(
            line=line,
            line_fit=line_fit,
            yield_score=spec["yield"],
            activity_score=spec["activity"],
            stability_score=spec["stability"],
            cost_score=spec["cost"],
            risk_score=spec["risk"],
        )
        validation = [
            "目标产物含量",
            "活性保留率",
            "污染检测",
            "pH 与 ORP 波动",
            "产品基质稳定性",
            "成本记录",
        ]
        if payload.akkProductType == "AKK 活菌体":
            validation.insert(1, "Akk qPCR 或 CFU")
        plans.append(
            CandidatePlan(
                planId=spec["planId"],
                planType=spec["planType"],
                displayName=spec["displayName"],
                summary=spec["summary"],
                recommendedParameters=RecommendedParameters(
                    temperature=NumericRange(min=spec["temp"][0], max=spec["temp"][1], unit="℃"),
                    ph=NumericRange(min=spec["ph"][0], max=spec["ph"][1], unit="pH"),
                    cultureTimeHours=NumericRange(min=spec["hours"][0], max=spec["hours"][1], unit="小时"),
                    agitationRpm=NumericRange(min=spec["rpm"][0], max=spec["rpm"][1], unit="rpm"),
                    aerationMode="稳定厌氧，保留阶段性取样复核",
                    inoculationRatio=spec["inoculation"],
                    coCultureRatio=spec["coCulture"],
                ),
                scoreBreakdown=score,
                riskItems=[*spec["riskItems"], *line.limitations[:1]],
                validationMetrics=validation,
                explanation=spec["explanation"],
            )
        )
    return plans


def _line_fit(line: ProductionLineProfile, temperature: float, ph: float, agitation: float) -> int:
    temp_ok = line.temperatureRange.min <= temperature <= line.temperatureRange.max
    ph_ok = line.phRange.min <= ph <= line.phRange.max
    rpm_ok = line.agitationRange.min <= agitation <= line.agitationRange.max
    score = line.feasibilityScore
    score += 4 if temp_ok else -14
    score += 4 if ph_ok else -14
    score += 3 if rpm_ok else -10
    return max(30, min(100, score))


def _score(
    line: ProductionLineProfile,
    line_fit: int,
    yield_score: int,
    activity_score: int,
    stability_score: int,
    cost_score: int,
    risk_score: int,
) -> ScoreBreakdown:
    feasibility = round((line.feasibilityScore * 0.55) + (line_fit * 0.45))
    overall = round(
        yield_score * 0.25
        + activity_score * 0.20
        + stability_score * 0.18
        + cost_score * 0.12
        + feasibility * 0.15
        + risk_score * 0.10
    )
    confidence = round((feasibility + stability_score + risk_score) / 3)
    return ScoreBreakdown(
        overallScore=overall,
        yieldScore=yield_score,
        activityScore=activity_score,
        stabilityScore=stability_score,
        costScore=cost_score,
        riskScore=risk_score,
        feasibilityScore=feasibility,
        confidenceScore=confidence,
    )


def _build_surface(payload: ProcessTaskRequest, line: ProductionLineProfile) -> ResponseSurface:
    points: list[SurfacePoint] = []
    temp_values = [34.0, 35.0, 36.0, 36.5, 37.0, 37.5, 38.5, 39.5]
    ph_values = [6.2, 6.4, 6.6, 6.8, 7.0, 7.2, 7.4, 7.6]
    target_bonus = 5 if "后生元" in payload.akkProductType else 0
    for temperature in temp_values:
        for ph in ph_values:
            temp_fit = exp(-((temperature - 37.0) ** 2) / 3.2)
            ph_fit = exp(-((ph - 6.85) ** 2) / 0.16)
            in_range = line.temperatureRange.min <= temperature <= line.temperatureRange.max and line.phRange.min <= ph <= line.phRange.max
            score = round(44 + 44 * temp_fit * ph_fit + target_bonus + (4 if in_range else -20))
            risk_level = "高" if not in_range or score < 58 else "中" if score < 76 else "低"
            points.append(SurfacePoint(temperature=temperature, ph=ph, score=max(0, min(100, score)), riskLevel=risk_level))
    return ResponseSurface(xAxisLabel="温度", yAxisLabel="pH", zAxisLabel="综合评分", points=points)


def _build_report(payload: ProcessTaskRequest, line: ProductionLineProfile, selected_plan: CandidatePlan) -> RecommendationReport:
    params = selected_plan.recommendedParameters
    return RecommendationReport(
        title=f"{payload.targetProductName}工艺状态建议书",
        parameterWindows=[
            f"推荐温度：{params.temperature.min}-{params.temperature.max}{params.temperature.unit}",
            f"推荐 pH：{params.ph.min}-{params.ph.max}",
            f"培养时间：{params.cultureTimeHours.min}-{params.cultureTimeHours.max}小时",
            f"搅拌范围：{params.agitationRpm.min}-{params.agitationRpm.max} rpm",
            f"通气/厌氧策略：{params.aerationMode}",
            f"接种比例：{params.inoculationRatio}",
            f"共培养比例：{params.coCultureRatio or '本轮不启用'}",
        ],
        predictedOutcomes=[
            f"综合评分预计为 {selected_plan.scoreBreakdown.overallScore}/100。",
            f"{payload.akkProductType}在{payload.targetProductForm}中的表现处于可验证区间。",
            f"目标含量：{payload.targetContent}；活性目标：{payload.activityTarget}。",
            f"所选产线“{line.lineName}”当前可执行性评分为 {selected_plan.scoreBreakdown.feasibilityScore}/100。",
        ],
        riskControls=[
            DISCLAIMER,
            "进入中试前需复核污染检测、pH 波动、ORP 和关键活性指标。",
            "所有模型结果来自论文锚点、模拟增强数据和规则模板，需用实验回填修正。",
            *selected_plan.riskItems,
        ],
        validationPlan=selected_plan.validationMetrics,
        nextStepSuggestion="建议按工艺平衡方案完成一轮小试或中试验证，回填目标产物含量、活性、稳定性和失败原因后再修正模型权重。",
    )
