from __future__ import annotations

import json
import math
import os

import httpx

from app.schemas.simulation import (
    SimulationLlmAdvisor,
    SimulationLlmStatus,
    SimulationPredictRequest,
    SimulationPredictResponse,
    SimulationPredictions,
    SimulationRange,
    SimulationRecommendedSettings,
    SimulationScenario,
)
from app.services.algae_akk_knowledge import (
    PRODUCT_FORMAT_PRIORS,
    get_carbon_profile,
    validation_indicators,
)


DISCLAIMER = "所有输出仅为内部研发实验建议，不代表最终食品配方、真实生产指令或上市功效承诺。"

DEFAULT_EXPERIMENT_ID = "exp-lit-seed-001"

CARBON_SOURCE_KEYS = [
    "BFP", "UBFP", "lambdaCarrageenan", "iotaCarrageenan",
    "fucoidan", "porphyraGlycoprotein", "PHP", "agar",
]
PRODUCT_FORMAT_KEYS = [
    "culture-medium", "postbiotic-powder", "fish-ball", "encapsulated-bead",
]


def _request_to_features(request: SimulationPredictRequest) -> dict[str, float]:
    features = {
        "carbonConcentration": float(request.carbonConcentration),
        "cultureHours": float(request.cultureHours),
        "temperatureC": float(request.temperatureC),
        "ph": float(request.ph),
        "anaerobicScore": float(request.anaerobicScore),
        "pressureMpa": float(request.pressureMpa),
        "stirringRpm": float(request.stirringRpm),
        "pretreated": float(request.pretreated),
    }
    for source in CARBON_SOURCE_KEYS:
        features[f"carbonSource_{source}"] = 1.0 if request.carbonSource == source else 0.0
    for fmt in PRODUCT_FORMAT_KEYS:
        features[f"productFormat_{fmt}"] = 1.0 if request.productFormat == fmt else 0.0
    return features


class SimulationService:
    def __init__(self) -> None:
        self.llm_enabled = os.getenv("SIMULATION_LLM_ENABLED", "false").lower() == "true"
        self.llm_provider = os.getenv("SIMULATION_LLM_PROVIDER", "openai_compatible")
        self.llm_base_url = os.getenv("SIMULATION_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.llm_api_key = os.getenv("SIMULATION_LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        self.llm_model = os.getenv("SIMULATION_LLM_MODEL", "gpt-4.1-mini")
        self.llm_timeout = float(os.getenv("SIMULATION_LLM_TIMEOUT_SECONDS", "20"))
        self._inference = None
        self._registry = None
        self._artifacts = None

    def _get_inference(self):
        if self._inference is not None:
            return self._inference
        from app.model_registry.inference import PromotedModelInferenceService
        from app.model_registry.store import SqlitePromotedModelRegistry
        from app.research.artifacts import ContentAddressedModelArtifactStore
        artifact_path = os.getenv("MODEL_ARTIFACT_PATH", "/app/data/model-artifacts")
        registry_path = os.getenv("MODEL_REGISTRY_PATH", "/app/data/model-registry.db")
        self._artifacts = ContentAddressedModelArtifactStore(artifact_path)
        self._registry = SqlitePromotedModelRegistry(registry_path)
        self._inference = PromotedModelInferenceService(self._registry, self._artifacts)
        return self._inference

    def predict(self, request: SimulationPredictRequest, experiment_id: str | None = None) -> SimulationPredictResponse:
        exp_id = experiment_id or DEFAULT_EXPERIMENT_ID
        predictions = self._predict_from_model(request, exp_id)
        risks = self._risks(request, predictions)
        advisor = self._llm_advisor(request, predictions, risks) if request.useLlmAdvisor else self._disabled_advisor()
        return SimulationPredictResponse(
            label="研发实验建议",
            researchUseOnly=True,
            disclaimer=DISCLAIMER,
            targetProduct=request.targetProduct,
            customParameters=request.customParameters,
            confidence=predictions.confidence,
            predictions=predictions,
            recommendedSettings=self._recommended_settings(request),
            risks=risks,
            validationIndicators=validation_indicators(request.carbonSource, request.productFormat),
            curve=self._dose_curve(request, exp_id),
            llmAdvisor=advisor,
            predictionSource="promoted-model",
            modelVersion=exp_id,
        )

    def _predict_from_model(self, request: SimulationPredictRequest, experiment_id: str) -> SimulationPredictions:
        inference = self._get_inference()
        features = _request_to_features(request)
        targets = {}
        extrapolated = []
        for target_field in ["akkGrowthScore", "scfaScore", "barrierScore"]:
            try:
                result = inference.predict(experiment_id, features, allow_extrapolation=True)
                targets[target_field] = max(0.0, min(100.0, result.prediction))
                if result.extrapolated:
                    extrapolated.append(target_field)
            except (LookupError, ValueError):
                raise ValueError(
                    f"没有可用的已晋升模型来预测 {target_field}。"
                    f"请先运行 python -m scripts.seed_literature_model 训练并注册模型。"
                )
        akk_growth = targets.get("akkGrowthScore", 0.0)
        scfa = targets.get("scfaScore", 0.0)
        barrier = targets.get("barrierScore", 0.0)
        overall = 0.38 * akk_growth + 0.22 * scfa + 0.18 * barrier + 0.12 * max(0, 100 - abs(50 - 50)) + 0.10 * 60
        confidence = "low" if extrapolated else "medium"
        return SimulationPredictions(
            molecularWeightKda=0.0,
            akkGrowthScore=round(akk_growth, 2),
            scfaScore=round(scfa, 2),
            barrierScore=round(barrier, 2),
            overallScore=round(max(0.0, min(100.0, overall)), 2),
            confidence=confidence,
        )

    def scenarios(self) -> list[SimulationScenario]:
        return [
            SimulationScenario(
                scenarioId="bfp-growth-window",
                name="红毛藻多糖 Akk 增殖窗口",
                targetProduct="红毛藻多糖驱动的 AKK 后生元原料",
                productFormat="postbiotic-powder",
                carbonSource="BFP",
                carbonConcentration=2.0,
                cultureHours=60,
                temperatureC=37.0,
                ph=6.8,
                anaerobicScore=0.92,
                pressureMpa=120,
                stirringRpm=150,
                pretreated=True,
            ),
            SimulationScenario(
                scenarioId="amuc-lambda-carrageenan",
                name="λ-卡拉胶 Amuc-1260 方向",
                targetProduct="AKK 特征代谢物培养液",
                productFormat="culture-medium",
                carbonSource="lambdaCarrageenan",
                carbonConcentration=2.0,
                cultureHours=72,
                temperatureC=37.0,
                ph=6.8,
                anaerobicScore=0.95,
                pressureMpa=80,
                stirringRpm=140,
                pretreated=True,
            ),
            SimulationScenario(
                scenarioId="ubfp-encapsulation",
                name="低分子量多糖包埋颗粒",
                targetProduct="海藻源 AKK 包埋颗粒",
                productFormat="encapsulated-bead",
                carbonSource="UBFP",
                carbonConcentration=1.2,
                cultureHours=48,
                temperatureC=37.0,
                ph=6.9,
                anaerobicScore=0.88,
                pressureMpa=300,
                stirringRpm=170,
                pretreated=True,
            ),
            SimulationScenario(
                scenarioId="fish-ball-bfp",
                name="红藻多糖鱼丸基质验证",
                targetProduct="红藻多糖鱼丸功能基质",
                productFormat="fish-ball",
                carbonSource="BFP",
                carbonConcentration=0.8,
                cultureHours=24,
                temperatureC=37.0,
                ph=6.8,
                anaerobicScore=0.78,
                pressureMpa=80,
                stirringRpm=180,
                pretreated=True,
            ),
        ]

    def llm_status(self) -> SimulationLlmStatus:
        return SimulationLlmStatus(
            enabled=self.llm_enabled,
            provider=self.llm_provider,
            model=self.llm_model,
            baseUrl=self.llm_base_url,
            apiKeyConfigured=bool(self.llm_api_key),
            envKeys=[
                "SIMULATION_LLM_ENABLED",
                "SIMULATION_LLM_PROVIDER",
                "SIMULATION_LLM_BASE_URL",
                "SIMULATION_LLM_API_KEY",
                "SIMULATION_LLM_MODEL",
                "OPENAI_API_KEY",
            ],
            mode="llm_advisor" if self.llm_enabled and self.llm_api_key else "model_only",
        )

    def _recommended_settings(self, request: SimulationPredictRequest) -> SimulationRecommendedSettings:
        profile = get_carbon_profile(request.carbonSource)
        low, high = profile.effective_range
        center = profile.optimum_g_l + PRODUCT_FORMAT_PRIORS[request.productFormat]["optimum_shift"]
        return SimulationRecommendedSettings(
            carbonSource=request.carbonSource,
            carbonConcentration=SimulationRange(
                min=max(0.0, min(low, center - 0.35)),
                max=min(4.0, max(high, center + 0.35)),
                unit="g/L 或食品基质比例",
            ),
            temperatureC=SimulationRange(min=36.5, max=37.5, unit="℃"),
            ph=SimulationRange(min=6.6, max=7.0, unit="pH"),
            anaerobicScoreMinimum=0.88 if request.carbonSource in {"BFP", "lambdaCarrageenan", "UBFP"} else 0.82,
            cultureHours=SimulationRange(
                min=max(24, request.cultureHours - 12),
                max=min(96, request.cultureHours + 12),
                unit="小时",
            ),
            stirringRpm=SimulationRange(min=max(80, request.stirringRpm - 30), max=min(260, request.stirringRpm + 30), unit="rpm"),
            pressureMpa=SimulationRange(min=max(0, request.pressureMpa - 60), max=min(420, request.pressureMpa + 60), unit="MPa"),
        )

    def _risks(self, request: SimulationPredictRequest, predictions: SimulationPredictions) -> list[str]:
        profile = get_carbon_profile(request.carbonSource)
        risks = [
            "模型预测不能替代小试、中试和人工审核。",
            f"当前底物为{profile.display_name}，证据来源包括：{'；'.join(profile.evidence_notes)}",
            "当前模型基于文献锚点+模拟增强数据训练，需用真实产线数据持续优化。",
        ]
        low, high = profile.effective_range
        if not (low <= request.carbonConcentration <= high):
            risks.append(f"{profile.display_name} 当前浓度不在建议有效窗口 {low}-{high} g/L 内，需要做剂量梯度复核。")
        if request.anaerobicScore < 0.85:
            risks.append("厌氧水平低于建议阈值，Akk 增殖、粘附和代谢物预测可能偏高。")
        if request.temperatureC < 35 or request.temperatureC > 39:
            risks.append("温度偏离 37℃ 窗口，需重点复核 OD600 生长曲线和污染风险。")
        if request.carbonConcentration > 3.0:
            risks.append("碳源浓度较高，可能带来黏度、过滤、口感或成本风险。")
        if request.productFormat in {"fish-ball", "encapsulated-bead"}:
            risks.append("食品基质或包埋体系需额外验证口感一致性、释放曲线和货架期稳定性。")
        if predictions.confidence == "low":
            risks.append("部分输入参数超出模型训练范围，预测结果外推风险较高。")
        return risks + list(profile.process_notes)

    def _dose_curve(self, request: SimulationPredictRequest, experiment_id: str) -> list[dict[str, float]]:
        points = []
        for concentration in [0, 0.25, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0]:
            clone = request.model_copy(update={"carbonConcentration": concentration})
            try:
                pred = self._predict_from_model(clone, experiment_id)
                points.append({
                    "carbonConcentration": concentration,
                    "akkGrowthScore": pred.akkGrowthScore,
                    "scfaScore": pred.scfaScore,
                    "overallScore": pred.overallScore,
                })
            except ValueError:
                points.append({
                    "carbonConcentration": concentration,
                    "akkGrowthScore": 0.0,
                    "scfaScore": 0.0,
                    "overallScore": 0.0,
                })
        return points

    def _disabled_advisor(self) -> SimulationLlmAdvisor:
        return SimulationLlmAdvisor(
            enabled=False,
            provider=self.llm_provider,
            model=self.llm_model,
            apiKeyConfigured=bool(self.llm_api_key),
            advice=None,
            mode="model_only",
        )

    def _llm_advisor(self, request: SimulationPredictRequest, predictions: SimulationPredictions, risks: list[str]) -> SimulationLlmAdvisor:
        if not self.llm_enabled or not self.llm_api_key:
            return SimulationLlmAdvisor(
                enabled=self.llm_enabled,
                provider=self.llm_provider,
                model=self.llm_model,
                apiKeyConfigured=bool(self.llm_api_key),
                advice="已预留真实大模型接口。配置 SIMULATION_LLM_API_KEY 或 OPENAI_API_KEY 后可启用解释型顾问。",
                mode="waiting_for_key",
            )
        profile = get_carbon_profile(request.carbonSource)
        prompt = json.dumps(
            {
                "task": "为 AKK 菌海藻功能碳源仿真结果生成简短研发解释，必须强调研发实验建议边界。",
                "sourceProfile": {
                    "name": profile.display_name,
                    "category": profile.category,
                    "processNotes": list(profile.process_notes),
                    "evidenceNotes": list(profile.evidence_notes),
                },
                "input": request.model_dump(),
                "predictions": predictions.model_dump(),
                "risks": risks,
            },
            ensure_ascii=False,
        )
        try:
            advice = self._call_llm(prompt)
        except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError):
            advice = "大模型调用失败，已回退到模型推理结果。"
        return SimulationLlmAdvisor(enabled=True, provider=self.llm_provider, model=self.llm_model, apiKeyConfigured=True, advice=advice, mode="llm_advisor")

    def _call_llm(self, prompt: str) -> str:
        response = httpx.post(
            f"{self.llm_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.llm_api_key}"},
            json={
                "model": self.llm_model,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": "你是食品研发仿真顾问。只提供内部研发实验建议，不输出最终生产配方，不做上市功效承诺。"},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=self.llm_timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


simulation_service = SimulationService()
