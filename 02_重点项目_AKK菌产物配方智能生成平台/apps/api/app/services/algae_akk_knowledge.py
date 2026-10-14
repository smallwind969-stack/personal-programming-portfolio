from __future__ import annotations

from dataclasses import dataclass
from math import exp


@dataclass(frozen=True)
class CarbonSourceProfile:
    source_id: str
    display_name: str
    category: str
    optimum_g_l: float
    effective_range: tuple[float, float]
    growth_factor: float
    scfa_factor: float
    adhesion_factor: float
    barrier_factor: float
    molecular_weight_shift: float
    process_notes: tuple[str, ...]
    evidence_notes: tuple[str, ...]
    validation_focus: tuple[str, ...]


CARBON_SOURCE_PROFILES: dict[str, CarbonSourceProfile] = {
    "BFP": CarbonSourceProfile(
        source_id="BFP",
        display_name="红毛藻多糖",
        category="红藻功能多糖",
        optimum_g_l=2.0,
        effective_range=(0.5, 2.0),
        growth_factor=1.18,
        scfa_factor=1.12,
        adhesion_factor=1.14,
        barrier_factor=1.10,
        molecular_weight_shift=-4.0,
        process_notes=(
            "适合作为海藻来源优质功能碳源，第一轮建议重点围绕 0.5-2.0 g/L 做剂量梯度。",
            "附件专利与论文材料提示 2.0 g/L 附近对 Akk 增殖、粘附和短链脂肪酸表现更优。",
            "进入食品基质前应复核颜色、腥味、黏度和口感遮蔽需求。",
        ),
        evidence_notes=(
            "红毛藻多糖促进 Akk 生长与定植相关论文和专利。",
            "红毛藻多糖-DSS 与体内 Akk 富集材料。",
        ),
        validation_focus=("OD600 生长曲线", "Akk qPCR/CFU", "Caco-2 粘附", "乙酸/丙酸/丁酸", "产品基质稳定性"),
    ),
    "UBFP": CarbonSourceProfile(
        source_id="UBFP",
        display_name="超高压改性红毛藻多糖",
        category="改性低分子量海藻多糖",
        optimum_g_l=1.2,
        effective_range=(0.6, 2.0),
        growth_factor=1.24,
        scfa_factor=1.16,
        adhesion_factor=1.10,
        barrier_factor=1.12,
        molecular_weight_shift=-16.0,
        process_notes=(
            "适合需要低分子量、较好分散性和后生元粉体稳定性的方向。",
            "超高压或适度降解会降低分子量，但过强处理可能牺牲结构完整性和成本友好性。",
            "适合与冻干、包埋或粉体复配工艺联动评估。",
        ),
        evidence_notes=(
            "海藻源低分子量活性多糖益生菌包埋颗粒相关专利。",
            "基于机器学习的卡拉胶分子量预测材料可迁移到分子量窗口管理。",
        ),
        validation_focus=("分子量分布", "包埋率", "复水分散性", "活性保留", "加速稳定性"),
    ),
    "lambdaCarrageenan": CarbonSourceProfile(
        source_id="lambdaCarrageenan",
        display_name="λ-卡拉胶",
        category="硫酸化红藻多糖",
        optimum_g_l=2.0,
        effective_range=(0.5, 2.0),
        growth_factor=1.21,
        scfa_factor=1.18,
        adhesion_factor=1.08,
        barrier_factor=1.06,
        molecular_weight_shift=12.0,
        process_notes=(
            "适合特征代谢物与 Amuc-1260 激活方向的研发验证。",
            "高黏度或分子量偏高时要关注传质、过滤和口感风险。",
            "建议与分子量预测和适度降解策略联动。",
        ),
        evidence_notes=(
            "λ-卡拉胶为碳源培养激活 Amuc-1260 的培养基相关专利。",
            "促进 Akk 特征代谢物生成方法相关专利。",
        ),
        validation_focus=("Amuc-1260", "特征代谢物", "短链脂肪酸", "黏度", "分子量分布"),
    ),
    "iotaCarrageenan": CarbonSourceProfile(
        source_id="iotaCarrageenan",
        display_name="ι-卡拉胶",
        category="凝胶型红藻多糖",
        optimum_g_l=1.1,
        effective_range=(0.4, 1.5),
        growth_factor=0.92,
        scfa_factor=0.95,
        adhesion_factor=0.96,
        barrier_factor=1.02,
        molecular_weight_shift=10.0,
        process_notes=(
            "更适合凝胶、果冻、软糖等基质适配，不宜只按增殖效果排序。",
            "需要重点管理分子量、凝胶强度和热加工稳定性。",
            "可结合机器学习分子量预测方法建立质构窗口。",
        ),
        evidence_notes=("基于机器学习的 ι-型卡拉胶分子量预测相关材料。",),
        validation_focus=("分子量预测", "凝胶强度", "热稳定性", "释放曲线", "口感一致性"),
    ),
    "fucoidan": CarbonSourceProfile(
        source_id="fucoidan",
        display_name="岩藻聚糖",
        category="褐藻硫酸化多糖",
        optimum_g_l=1.5,
        effective_range=(0.5, 2.5),
        growth_factor=1.08,
        scfa_factor=1.05,
        adhesion_factor=1.06,
        barrier_factor=1.10,
        molecular_weight_shift=4.0,
        process_notes=(
            "适合作为差异化海藻功能碳源储备，建议先做体外筛选再进入产品基质。",
            "需关注来源批次、硫酸基含量和成本。",
        ),
        evidence_notes=("创新点材料将岩藻聚糖列为海藻功能碳源数据库候选底物。",),
        validation_focus=("硫酸基含量", "Akk 增殖响应", "短链脂肪酸", "批次稳定性"),
    ),
    "porphyraGlycoprotein": CarbonSourceProfile(
        source_id="porphyraGlycoprotein",
        display_name="紫菜糖蛋白",
        category="紫菜来源糖蛋白",
        optimum_g_l=1.0,
        effective_range=(0.3, 1.8),
        growth_factor=1.02,
        scfa_factor=1.04,
        adhesion_factor=1.08,
        barrier_factor=1.08,
        molecular_weight_shift=-1.0,
        process_notes=(
            "适合作为前沿储备方向，现阶段应降低置信度并加强验证指标。",
            "建议优先用于机制探索和差异化产品叙事，不直接作为中试默认方案。",
        ),
        evidence_notes=("创新点材料将坛紫菜糖蛋白作为原创性和差异化升级方向。",),
        validation_focus=("糖蛋白结构", "Akk 响应", "粘附能力", "安全性边界"),
    ),
    "PHP": CarbonSourceProfile(
        source_id="PHP",
        display_name="桔梗多糖",
        category="植物多糖对照底物",
        optimum_g_l=1.5,
        effective_range=(0.5, 2.5),
        growth_factor=0.96,
        scfa_factor=1.0,
        adhesion_factor=0.96,
        barrier_factor=0.98,
        molecular_weight_shift=-2.0,
        process_notes=("可作为非海藻多糖对照，不应作为本项目海藻-AKK 创新主线的首选底物。",),
        evidence_notes=("既有 AKK 与多糖关系资料可作为对照参考。",),
        validation_focus=("Akk 增殖响应", "SCFA", "成本", "与海藻底物对照"),
    ),
    "agar": CarbonSourceProfile(
        source_id="agar",
        display_name="琼胶",
        category="红藻多糖对照底物",
        optimum_g_l=1.0,
        effective_range=(0.2, 1.5),
        growth_factor=0.70,
        scfa_factor=0.76,
        adhesion_factor=0.88,
        barrier_factor=0.90,
        molecular_weight_shift=18.0,
        process_notes=("更适合作为凝胶基质或对照底物，直接作为高效 Akk 碳源的优先级较低。",),
        evidence_notes=("作为海藻多糖对照项，用于避免模型过度偏向单一底物。",),
        validation_focus=("凝胶适配", "Akk 增殖响应", "黏度", "过滤风险"),
    ),
}


PRODUCT_FORMAT_PRIORS = {
    "culture-medium": {"growth": 1.06, "stability": 0.96, "cost": 0.96, "optimum_shift": 0.0},
    "postbiotic-powder": {"growth": 1.00, "stability": 1.12, "cost": 0.92, "optimum_shift": 0.0},
    "fish-ball": {"growth": 0.86, "stability": 0.98, "cost": 1.03, "optimum_shift": -1.1},
    "encapsulated-bead": {"growth": 0.94, "stability": 1.18, "cost": 0.86, "optimum_shift": -0.4},
}


def get_carbon_profile(source_id: str) -> CarbonSourceProfile:
    return CARBON_SOURCE_PROFILES[source_id]


def carbon_source_options() -> list[CarbonSourceProfile]:
    return list(CARBON_SOURCE_PROFILES.values())


def dose_response(concentration: float, profile: CarbonSourceProfile, product_format: str) -> float:
    prior = PRODUCT_FORMAT_PRIORS[product_format]
    optimum = max(0.15, profile.optimum_g_l + prior["optimum_shift"])
    sigma = 0.72 if product_format == "fish-ball" else 0.86
    return exp(-((concentration - optimum) ** 2) / (2 * sigma**2))


def substrate_confidence(profile: CarbonSourceProfile, concentration: float) -> int:
    low, high = profile.effective_range
    if low <= concentration <= high:
        return 84
    if 0 < concentration < low or high < concentration <= high + 1.5:
        return 68
    return 52


def pretreatment_effect(pretreated: bool, pressure_mpa: float, stirring_rpm: float, profile: CarbonSourceProfile) -> tuple[float, list[str]]:
    notes: list[str] = []
    effect = 0.0
    if pretreated:
        effect += 7.0
        notes.append("已启用预处理，可提高海藻多糖可利用性和基质适配性。")
    if pressure_mpa >= 180:
        effect += 4.0
        notes.append("较高压力处理有利于降低分子量，但需复核活性保留和成本。")
    if pressure_mpa > 360:
        effect -= 6.0
        notes.append("压力过高可能导致结构过度破坏，建议降低处理强度。")
    if stirring_rpm > 260:
        effect -= 4.0
        notes.append("搅拌偏高可能增加剪切损伤和泡沫风险。")
    if profile.source_id in {"lambdaCarrageenan", "iotaCarrageenan", "agar"} and not pretreated:
        effect -= 3.0
        notes.append("卡拉胶/琼胶类底物建议评估适度降解或分子量窗口。")
    return effect, notes


def molecular_weight_prediction(source_id: str, pressure_mpa: float, stirring_rpm: float, pretreated: bool) -> float:
    profile = get_carbon_profile(source_id)
    base = 76.0 + profile.molecular_weight_shift
    value = base - 0.058 * pressure_mpa - 0.055 * max(0, stirring_rpm - 140)
    if pretreated:
        value -= 8.5
    return max(6.0, min(140.0, value))


def validation_indicators(source_id: str, product_format: str) -> list[str]:
    profile = get_carbon_profile(source_id)
    indicators = list(profile.validation_focus)
    if product_format in {"fish-ball", "encapsulated-bead"}:
        indicators.extend(["口感一致性", "基质释放曲线", "货架期稳定性"])
    if source_id == "lambdaCarrageenan":
        indicators.extend(["Amuc-1260 表达", "特征代谢物 LC-MS/GC-MS"])
    return list(dict.fromkeys(indicators))
