from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

from app.repositories.mock_repository import MockRepository
from app.repositories.sqlite_repository import SqliteRepository
from app.schemas.formula import FormulaGenerationRequest, FormulaResult
from app.services.experiment_service import experiment_service
from app.services.knowledge_service import knowledge_service
from app.services.llm_service import local_llm_service


APPLICATION_NAMES = {
    "yogurt": "功能酸奶",
    "nutrition_powder": "益生元营养粉",
    "functional_beverage": "即饮功能饮料",
    "meal_replacement": "代餐奶昔",
    "custom": "自定义商品",
}

PRODUCT_DISPLAY_CATEGORIES = {
    "postbiotic": "后生元原料",
    "metabolite_blend": "代谢物组合",
    "fiber_complex": "纤维复配物",
}

BASE_RATIO_PROFILES = {
    "yogurt": {
        "akk-postbiotic-powder": 58,
        "akk-metabolite-blend": 14,
        "akk-fiber-complex": 28,
    },
    "functional_beverage": {
        "akk-postbiotic-powder": 35,
        "akk-metabolite-blend": 45,
        "akk-fiber-complex": 20,
    },
    "nutrition_powder": {
        "akk-postbiotic-powder": 42,
        "akk-metabolite-blend": 8,
        "akk-fiber-complex": 50,
    },
    "meal_replacement": {
        "akk-postbiotic-powder": 35,
        "akk-metabolite-blend": 8,
        "akk-fiber-complex": 57,
    },
}


class FormulaService:
    def __init__(self, repository: MockRepository | None = None) -> None:
        self.repository = repository or MockRepository()
        self.sqlite_repository = SqliteRepository()
        self._generated_results: dict[str, dict] = {}

    def generate_formula(self, request: FormulaGenerationRequest) -> FormulaResult:
        custom_application = self._parse_constraint_value(request.constraints, "custom_application")
        customer_demand = self._parse_constraint_value(request.constraints, "customer_demand") or request.notes or ""
        project_name = self._parse_project_name(request.constraints)
        application_key = self._resolve_application_key(request, custom_application, customer_demand)
        application_name = custom_application or APPLICATION_NAMES.get(request.applicationTargetId, request.applicationTargetId)
        products = self._select_products(request, application_key)
        composition = self._build_composition(products, request.constraints, application_key, customer_demand)

        retrieval_query = self._build_retrieval_query(application_name, customer_demand, request.targetProperties, composition)
        knowledge_references = self._select_knowledge_references(application_key, retrieval_query)
        companion_ingredients = self._build_companion_ingredients(application_key, customer_demand)
        risk_items = self._build_risk_items(products, knowledge_references, application_key, customer_demand)
        validation_metrics = self._build_validation_metrics(products, knowledge_references, application_key)
        predictions = self._build_predictions(application_name, composition, risk_items, knowledge_references)
        product_advantages = self._build_product_advantages(
            application_name, request.targetProperties, products, composition, knowledge_references
        )
        upgrade_suggestions = self._build_upgrade_suggestions(application_key, customer_demand)
        experiment_suggestions = self._build_experiment_suggestions(application_key, validation_metrics)

        llm_enrichment = self._maybe_enrich_with_llm(
            llm_requested=any(constraint.startswith("llm_agent_mode:") for constraint in request.constraints),
            application_name=application_name,
            customer_demand=customer_demand,
            target_properties=request.targetProperties,
            products=products,
            composition=composition,
            knowledge_references=knowledge_references,
            companion_ingredients=companion_ingredients,
        )
        llm_used = bool(llm_enrichment)
        reasoning_summary = self._rule_reasoning_summary(application_name, composition, knowledge_references)
        if llm_enrichment:
            product_advantages = self._list_or_fallback(llm_enrichment.get("productAdvantages"), product_advantages)
            upgrade_suggestions = self._list_or_fallback(llm_enrichment.get("upgradeSuggestions"), upgrade_suggestions)
            companion_ingredients = self._companion_or_fallback(llm_enrichment.get("companionIngredients"), companion_ingredients)
            reasoning_summary = str(llm_enrichment.get("reasoningSummary") or reasoning_summary)

        result = {
            "resultId": f"generated-{uuid4().hex[:8]}",
            "recommendationType": "rd_experiment_suggestion",
            "researchUseOnly": True,
            "research_use_only": True,
            "disclaimer": "内部研发实验建议。本方案用于商品概念、打样沟通和验证计划生成，不作为可直接上市的最终食品配方。",
            "applicationName": application_name,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "sourceType": "mock",
            "candidates": [
                {
                    "candidateId": "generated-candidate-001",
                    "candidateName": project_name or self._name_formula(application_name, composition, customer_demand),
                    "composition": composition,
                    "companionIngredients": companion_ingredients,
                    "predictions": predictions,
                    "confidenceScore": self._confidence_score(knowledge_references),
                    "confidenceLevel": "medium",
                    "riskItems": risk_items,
                    "validationMetrics": validation_metrics,
                    "experimentSuggestions": experiment_suggestions,
                    "productAdvantages": product_advantages,
                    "upgradeSuggestions": upgrade_suggestions,
                    "knowledgeReferences": knowledge_references,
                    "agentTrace": self._build_agent_trace(
                        application_name=application_name,
                        target_properties=request.targetProperties,
                        knowledge_count=len(knowledge_references),
                        risk_count=len(risk_items),
                        validation_count=len(validation_metrics),
                        llm_used=llm_used,
                        llm_summary=reasoning_summary,
                    ),
                    "approvalStatus": "pending_research_review",
                }
            ],
        }
        self._generated_results[result["resultId"]] = deepcopy(result)
        self.sqlite_repository.save_formula_result(result)
        experiment_service.create_synthetic_records_for_result(result)
        return FormulaResult.model_validate(result)

    def get_result(self, result_id: str) -> FormulaResult | None:
        stored = self.sqlite_repository.get_formula_result(result_id)
        if stored is not None:
            return FormulaResult.model_validate(stored)
        if result_id in self._generated_results:
            return FormulaResult.model_validate(self._generated_results[result_id])
        for result in self.repository.get_formula_results():
            if result["resultId"] == result_id:
                return FormulaResult.model_validate(result)
        return None

    def list_results(self) -> list[FormulaResult]:
        sqlite_results = [FormulaResult.model_validate(result) for result in self.sqlite_repository.list_formula_results()]
        generated_results = [FormulaResult.model_validate(result) for result in self._generated_results.values()]
        stored_results = [FormulaResult.model_validate(result) for result in self.repository.get_formula_results()]
        known_ids = {result.resultId for result in sqlite_results}
        merged = sqlite_results + [result for result in generated_results if result.resultId not in known_ids]
        known_ids.update(result.resultId for result in merged)
        merged.extend(result for result in stored_results if result.resultId not in known_ids)
        return merged

    def _resolve_application_key(
        self,
        request: FormulaGenerationRequest,
        custom_application: str | None,
        customer_demand: str,
    ) -> str:
        if request.applicationTargetId != "custom":
            return request.applicationTargetId
        text = f"{custom_application or ''} {customer_demand} {' '.join(request.targetProperties)}".lower()
        if any(keyword in text for keyword in ["酸奶", "发酵乳", "乳", "yogurt", "milk"]):
            return "yogurt"
        if any(keyword in text for keyword in ["饮料", "即饮", "水", "beverage", "drink"]):
            return "functional_beverage"
        if any(keyword in text for keyword in ["代餐", "奶昔", "体重", "meal"]):
            return "meal_replacement"
        return "nutrition_powder"

    def _select_products(self, request: FormulaGenerationRequest, application_key: str) -> list[dict]:
        products = [
            product
            for product in self.repository.get_products()
            if product["productId"] not in request.excludedProductIds
        ]
        if request.preferredProductIds:
            preferred = [product for product in products if product["productId"] in request.preferredProductIds]
            products = preferred or products
        else:
            preferred_order = BASE_RATIO_PROFILES.get(application_key, BASE_RATIO_PROFILES["nutrition_powder"])
            products.sort(key=lambda product: preferred_order.get(product["productId"], 0), reverse=True)
        return products[: request.maxIngredientCount]

    def _build_composition(self, products: list[dict], constraints: list[str], application_key: str, demand: str) -> list[dict]:
        custom_ratios = self._parse_custom_ratios(constraints)
        selected_total = sum(custom_ratios.get(product["productId"], 0) for product in products)
        if selected_total <= 0:
            base = BASE_RATIO_PROFILES.get(application_key, BASE_RATIO_PROFILES["nutrition_powder"])
            selected_total = sum(base.get(product["productId"], 0) for product in products)
            custom_ratios = {
                product["productId"]: base.get(product["productId"], 100 / max(len(products), 1))
                for product in products
            }
        if "儿童" in demand:
            custom_ratios = self._rebalance(custom_ratios, "akk-postbiotic-powder", 6)
        if any(keyword in demand for keyword in ["低糖", "饱腹", "银发", "代餐"]):
            custom_ratios = self._rebalance(custom_ratios, "akk-fiber-complex", 8)
        if any(keyword in demand for keyword in ["清爽", "饮料", "即饮"]):
            custom_ratios = self._rebalance(custom_ratios, "akk-metabolite-blend", 8)
        selected_total = sum(custom_ratios.get(product["productId"], 0) for product in products)

        return [
            {
                "productId": product["productId"],
                "productName": product["productName"],
                "ratioPercent": round(custom_ratios.get(product["productId"], 0) / selected_total * 100, 2),
                "role": self._product_role(product, application_key),
            }
            for product in products
        ]

    def _rebalance(self, ratios: dict[str, float], target: str, delta: float) -> dict[str, float]:
        if target not in ratios:
            return ratios
        updated = dict(ratios)
        updated[target] += delta
        others = [key for key in updated if key != target and updated[key] > 0]
        if not others:
            return updated
        cut = delta / len(others)
        for key in others:
            updated[key] = max(1, updated[key] - cut)
        return updated

    def _select_knowledge_references(self, application_key: str, query: str) -> list[dict]:
        topic_map = {
            "yogurt": ["postbiotic", "food_application", "dairy_matrix", "safety", "regulatory"],
            "nutrition_powder": ["fiber_polysaccharide", "postbiotic", "clinical", "safety"],
            "functional_beverage": ["metabolite", "postbiotic", "food_application", "safety"],
            "meal_replacement": ["fiber_polysaccharide", "clinical", "safety"],
        }
        items = knowledge_service.search_items(query=query, topics=topic_map.get(application_key, ["food_application", "safety"]))
        references = []
        for item in items[:6]:
            reason_parts = item.matchReasons[:3] or item.usableInsights[:1]
            boundary = item.riskNotes[0] if item.riskNotes else "需要结合目标食品基质和小试验证使用。"
            passages = item.keyPassages[:2] or ([item.summary] if item.summary else [])
            references.append(
                {
                    "knowledgeId": item.knowledgeId,
                    "title": item.title,
                    "evidenceLevel": item.evidenceLevel,
                    "sourceUrl": item.sourceUrl,
                    "retrievalScore": item.retrievalScore,
                    "keyPassages": passages[:2],
                    "relevanceReason": f"{'；'.join(reason_parts)}。引用原因：该材料用于支撑配方的科学性、适用基质或安全边界判断。边界：{boundary}",
                }
            )
        return references

    def _build_retrieval_query(
        self,
        application_name: str,
        customer_demand: str,
        target_properties: list[str],
        composition: list[dict],
    ) -> str:
        product_text = " ".join(item["productName"] for item in composition)
        return f"{application_name} {customer_demand} {' '.join(target_properties)} {product_text} AKK 后生元 安全 稳定性 食品应用"

    def _maybe_enrich_with_llm(
        self,
        llm_requested: bool,
        application_name: str,
        customer_demand: str,
        target_properties: list[str],
        products: list[dict],
        composition: list[dict],
        knowledge_references: list[dict],
        companion_ingredients: list[dict],
    ) -> dict | None:
        if not llm_requested:
            return None
        return local_llm_service.enrich_formula(
            {
                "applicationName": application_name,
                "customerDemand": customer_demand,
                "targetProperties": target_properties,
                "akkProducts": [
                    {
                        "productId": product["productId"],
                        "productName": product["productName"],
                        "productCategory": PRODUCT_DISPLAY_CATEGORIES.get(product["productCategory"], product["productCategory"]),
                        "riskLevel": product["riskLevel"],
                        "evidenceLevel": product["evidenceLevel"],
                    }
                    for product in products
                ],
                "composition": composition,
                "companionIngredients": companion_ingredients,
                "knowledgeReferences": knowledge_references,
            }
        )

    def _build_predictions(self, application_name: str, composition: list[dict], risks: list[dict], references: list[dict]) -> list[dict]:
        high_risk = sum(1 for risk in risks if risk["riskLevel"] == "high")
        confidence = self._confidence_score(references)
        return [
            {
                "predictionId": "pred-market-fit",
                "targetName": "商品概念匹配度",
                "predictedValue": "较高" if confidence >= 0.68 else "需要优化",
                "confidenceScore": confidence,
                "explanation": f"目标商品为{application_name}，AKK 原料组合与检索到的食品基质、后生元或安全证据存在匹配，可作为首轮打样起点。",
            },
            {
                "predictionId": "pred-sensory-risk",
                "targetName": "感官风险",
                "predictedValue": "中",
                "confidenceScore": 0.62,
                "explanation": "AKK 后生元、代谢物或纤维原料可能影响底味、酸甜平衡、浊度或黏度，需要感官小试验证。",
            },
            {
                "predictionId": "pred-stability-risk",
                "targetName": "加工稳定性",
                "predictedValue": "中高" if high_risk else "中",
                "confidenceScore": 0.66,
                "explanation": "需要重点验证酸性体系、热处理、复水分散或货架期稳定性，确认关键标志物保留表现。",
            },
        ]

    def _build_risk_items(self, products: list[dict], references: list[dict], application_key: str, demand: str) -> list[dict]:
        risks = [risk for product in products for risk in product["riskItems"]]
        risks.append(
            {
                "riskId": "knowledge-boundary",
                "riskName": "知识库外推边界",
                "riskLevel": "medium",
                "description": "论文证据与目标商品基质、工艺和人群并不完全等同，不能直接外推为最终产品功效。",
                "mitigationSuggestion": "保留引用材料、配比假设和实验记录，使用 A/B/C 小试验证稳定性、感官和关键标志物。",
            }
        )
        if application_key in {"yogurt", "functional_beverage"}:
            risks.append(
                {
                    "riskId": "acid-system",
                    "riskName": "酸性体系稳定性",
                    "riskLevel": "high",
                    "description": "酸奶或饮料体系可能影响 AKK 相关标志物、浊度、沉淀和风味表现。",
                    "mitigationSuggestion": "设置 pH、热处理、货架期和离心沉淀观察实验。",
                }
            )
        if any(keyword in demand for keyword in ["儿童", "孕", "老人", "银发"]):
            risks.append(
                {
                    "riskId": "sensitive-population",
                    "riskName": "目标人群边界",
                    "riskLevel": "high",
                    "description": "敏感人群相关产品需要更严格的安全性、法规和标签审查。",
                    "mitigationSuggestion": "优先复核 EFSA/FDA 等法规资料，并增加安全性资料审查节点。",
                }
            )
        if references:
            risks.append(
                {
                    "riskId": "claim-compliance",
                    "riskName": "宣称与法规边界",
                    "riskLevel": "medium",
                    "description": "安全、临床或法规资料只能作为研发依据，不能直接转化为疾病治疗或功效承诺。",
                    "mitigationSuggestion": "商业化前需要目标市场法规复核和标签宣称审查。",
                }
            )
        return risks[:6]

    def _build_validation_metrics(self, products: list[dict], references: list[dict], application_key: str) -> list[dict]:
        metrics = [metric for product in products for metric in product["validationMetrics"]]
        metric_names = {metric["metricName"] for metric in metrics}
        extra_metrics = [
            {
                "metricId": "sensory-acceptance",
                "metricName": "感官接受度",
                "methodSuggestion": "开展 3-5 个比例梯度的小试感官评价，记录底味、酸甜、口感和外观。",
                "expectedRange": "内部小试评分 >= 7/10",
                "priority": "required",
            },
            {
                "metricId": "literature-marker-retention",
                "metricName": "文献关联标志物保留",
                "methodSuggestion": "围绕引用材料中的后生元、代谢物或结构相关指标设置检测。",
                "expectedRange": "首轮记录基线，不做上市承诺",
                "priority": "recommended",
            },
        ]
        if application_key in {"yogurt", "functional_beverage"}:
            extra_metrics.append(
                {
                    "metricId": "acid-stability-screening",
                    "metricName": "酸性体系稳定性",
                    "methodSuggestion": "在目标 pH 和加速条件下观察浊度、沉淀、风味和关键指标变化。",
                    "expectedRange": "<= 10% change",
                    "priority": "required",
                }
            )
        if references:
            extra_metrics.append(
                {
                    "metricId": "evidence-review",
                    "metricName": "证据与合规复核",
                    "methodSuggestion": "复核知识库引用材料，确认适用基质、人群、剂量和法规边界。",
                    "expectedRange": "研发评审通过",
                    "priority": "required",
                }
            )
        for metric in extra_metrics:
            if metric["metricName"] not in metric_names:
                metrics.append(metric)
                metric_names.add(metric["metricName"])
        return metrics[:8]

    def _build_companion_ingredients(self, application_key: str, demand: str) -> list[dict]:
        templates = {
            "yogurt": [
                ("inulin", "菊粉", "膳食纤维/益生元", "0.5%-2.0%", "提升低糖酸奶厚度和肠道健康概念表达", "高添加量可能带来胀气感"),
                ("citrus-fiber", "柑橘纤维", "结构稳定剂", "0.1%-0.4%", "改善乳基体系悬浮、稠厚感和清洁标签表达", "需验证酸性体系黏度变化"),
                ("berry-flavor", "天然莓果风味", "风味修饰", "按风味体系调整", "遮盖 AKK 原料可能带来的底味", "需做三角感官测试"),
            ],
            "nutrition_powder": [
                ("fos", "低聚果糖", "益生元", "1%-5%", "强化益生元与清洁标签表达", "甜度和胃肠耐受性需验证"),
                ("oat-beta-glucan", "燕麦β-葡聚糖", "膳食纤维", "0.5%-3.0%", "支持饱腹感和粉体营养结构", "可能影响复水速度"),
                ("whey-protein", "乳清蛋白", "蛋白基底", "10%-25%", "提升营养粉蛋白含量和口感主体", "酸性体系下需验证稳定性"),
            ],
            "functional_beverage": [
                ("pectin", "果胶", "水相稳定剂", "0.05%-0.25%", "改善悬浮稳定性和轻稠口感", "过量可能导致口感黏腻"),
                ("erythritol", "赤藓糖醇", "低糖甜味体系", "1%-4%", "支持低糖和清爽口感", "需验证酸甜协调性"),
                ("citrate-buffer", "柠檬酸/柠檬酸钠缓冲体系", "酸度调节", "按目标 pH 调整", "控制酸度和风味平衡", "pH 过低可能提高稳定性风险"),
            ],
            "meal_replacement": [
                ("pea-protein", "豌豆蛋白", "植物蛋白", "8%-18%", "支持代餐营养结构和植物基卖点", "豆腥味需遮盖"),
                ("konjac", "魔芋葡甘聚糖", "饱腹纤维", "0.2%-1.0%", "强化饱腹感和稠厚口感", "黏度过高会影响饮用体验"),
                ("mct", "MCT 粉", "脂质能量基底", "2%-8%", "改善能量结构和顺滑感", "需验证氧化稳定性"),
            ],
        }
        selected = templates.get(application_key, templates["nutrition_powder"])
        return [
            {
                "ingredientId": ingredient_id,
                "ingredientName": name,
                "category": category,
                "suggestedUsage": usage,
                "purpose": purpose,
                "riskNote": risk,
            }
            for ingredient_id, name, category, usage, purpose, risk in selected
        ]

    def _build_product_advantages(
        self,
        application_name: str,
        target_properties: list[str],
        products: list[dict],
        composition: list[dict],
        references: list[dict],
    ) -> list[str]:
        target_text = self._join_targets(target_properties)
        product_names = "、".join(product["productName"] for product in products)
        evidence_count = len([reference for reference in references if reference["evidenceLevel"] in {"A", "B"}])
        top_ratio = max(composition, key=lambda item: item["ratioPercent"]) if composition else None
        top_ratio_text = f"首轮以 {top_ratio['productName']} 为主线，占比 {top_ratio['ratioPercent']}%" if top_ratio else "已形成首轮配比"
        return [
            f"围绕{application_name}形成 AKK 商品概念，适合与下游品牌进行首轮打样沟通。",
            f"核心原料组合为{product_names}，{top_ratio_text}，便于验证后生元、代谢物或纤维协同。",
            f"目标卖点覆盖{target_text}，可生成 A/B/C 梯度样品和验证计划。",
            f"知识库检索到 {evidence_count} 条 A/B 级优先证据，可辅助说明研发依据和风险边界。",
        ]

    def _build_upgrade_suggestions(self, application_key: str, demand: str) -> list[str]:
        suggestions = {
            "yogurt": [
                "若口感偏涩，优先调整天然风味、柑橘纤维和甜味体系比例。",
                "若酸稳定性不足，降低代谢物组合比例，并提高结构稳定剂筛选密度。",
                "若成本偏高，保留后生元粉末主线，减少高成本风味遮蔽体系。",
            ],
            "nutrition_powder": [
                "若复水较慢，降低高黏度纤维并优化粉体粒径。",
                "若饱腹感不足，提高燕麦β-葡聚糖或魔芋纤维梯度。",
                "若配料表过长，优先合并甜味和纤维体系。",
            ],
            "functional_beverage": [
                "若出现沉淀，提高果胶稳定体系并控制 pH。",
                "若底味明显，调整酸甜比和天然香气。",
                "若热处理损失较高，考虑低温后添加或无菌冷灌路径。",
            ],
            "meal_replacement": [
                "若粉感重，优化蛋白基底和脂质粉比例。",
                "若黏度过高，降低魔芋胶并提升复水剪切条件。",
                "若成本偏高，调整蛋白和 MCT 粉用量。",
            ],
        }
        return suggestions.get(application_key, suggestions["nutrition_powder"])

    def _build_experiment_suggestions(self, application_key: str, metrics: list[dict]) -> list[str]:
        required = [metric["metricName"] for metric in metrics if metric.get("priority") == "required"][:3]
        suggestions = [
            "按当前比例制作 A/B/C 小试样品，记录混合均匀性、外观、气味和口感。",
            f"优先验证：{'、'.join(required) if required else '稳定性、感官接受度和关键标志物保留'}。",
            "将知识库引用材料、配比假设、实验批次和异常观察同步归档，作为后续方案升级依据。",
        ]
        if application_key in {"yogurt", "functional_beverage"}:
            suggestions.append("增加 pH 梯度、热处理和加速稳定性观察，重点关注沉淀、浊度和风味变化。")
        return suggestions

    def _build_agent_trace(
        self,
        application_name: str,
        target_properties: list[str],
        knowledge_count: int,
        risk_count: int,
        validation_count: int,
        llm_used: bool,
        llm_summary: str,
    ) -> list[dict]:
        return [
            {
                "agentName": "需求理解 Agent",
                "status": "completed",
                "outputSummary": f"识别目标商品为{application_name}，核心目标包括{self._join_targets(target_properties)}。",
            },
            {
                "agentName": "知识库检索 Agent",
                "status": "completed",
                "outputSummary": f"从论文和法规知识库召回 {knowledge_count} 条证据，结合食品基质、主题、证据等级和正文片段排序。",
            },
            {
                "agentName": "配方生成 Agent",
                "status": "completed",
                "outputSummary": "生成 AKK 核心原料组合、协同食品原料和首轮小试配比。",
            },
            {
                "agentName": "风险预测 Agent",
                "status": "completed",
                "outputSummary": f"识别 {risk_count} 项风险和 {validation_count} 项验证指标。",
            },
            {
                "agentName": "本地 Ollama RAG Agent",
                "status": "completed" if llm_used else "fallback",
                "outputSummary": llm_summary,
            },
        ]

    def _parse_custom_ratios(self, constraints: list[str]) -> dict[str, float]:
        ratios: dict[str, float] = {}
        for constraint in constraints:
            if not constraint.startswith("custom_ratio:"):
                continue
            _, product_id, raw_ratio = constraint.split(":", 2)
            try:
                ratios[product_id] = max(float(raw_ratio), 0)
            except ValueError:
                continue
        return ratios

    def _parse_project_name(self, constraints: list[str]) -> str | None:
        return self._parse_constraint_value(constraints, "project_name")

    def _parse_constraint_value(self, constraints: list[str], key: str) -> str | None:
        prefix = f"{key}:"
        for constraint in constraints:
            if constraint.startswith(prefix):
                return constraint.split(":", 1)[1].strip() or None
        return None

    def _list_or_fallback(self, value: object, fallback: list[str]) -> list[str]:
        if not isinstance(value, list):
            return fallback
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        return cleaned[:5] or fallback

    def _companion_or_fallback(self, value: object, fallback: list[dict]) -> list[dict]:
        if not isinstance(value, list):
            return fallback
        cleaned = []
        for index, item in enumerate(value[:5]):
            if not isinstance(item, dict):
                continue
            name = str(item.get("ingredientName", "")).strip()
            if not name:
                continue
            cleaned.append(
                {
                    "ingredientId": str(item.get("ingredientId") or f"llm-ingredient-{index + 1}"),
                    "ingredientName": name,
                    "category": str(item.get("category") or "协同食品原料"),
                    "suggestedUsage": str(item.get("suggestedUsage") or "按小试梯度确认"),
                    "purpose": str(item.get("purpose") or "改善商品结构、口感或卖点表达"),
                    "riskNote": str(item.get("riskNote") or "需要小试验证稳定性和感官影响"),
                }
            )
        return cleaned or fallback

    def _join_targets(self, targets: list[str]) -> str:
        clean_targets = [target for target in targets if target.strip()]
        if not clean_targets:
            return "肠道健康、稳定性和低风险打样"
        return "、".join(clean_targets[:4])

    def _product_role(self, product: dict, application_key: str) -> str:
        category = PRODUCT_DISPLAY_CATEGORIES.get(product.get("productCategory"), "AKK 原料")
        if product["productId"] == "akk-postbiotic-powder":
            return f"{category}，用于后生元概念、热稳定性和 AKK 核心识别"
        if product["productId"] == "akk-metabolite-blend":
            return f"{category}，用于风味协同、水相表达和代谢物概念"
        return f"{category}，用于质构、饱腹感、复水或乳基稳定支撑"

    def _name_formula(self, application_name: str, composition: list[dict], demand: str) -> str:
        if "儿童" in demand:
            prefix = "儿童友好型"
        elif "银发" in demand or "老人" in demand:
            prefix = "银发营养型"
        elif "低糖" in demand:
            prefix = "低糖轻负担"
        else:
            prefix = "AKK 共创"
        return f"{prefix}{application_name}方案"

    def _rule_reasoning_summary(self, application_name: str, composition: list[dict], references: list[dict]) -> str:
        ratio_text = "、".join(f"{item['productName']} {item['ratioPercent']}%" for item in composition)
        evidence_text = "、".join(reference["title"] for reference in references[:2]) if references else "知识库未命中强证据"
        return f"规则引擎已根据{application_name}的食品基质、目标性质和知识库证据生成首轮配比：{ratio_text}。重点引用：{evidence_text}。"

    def _confidence_score(self, references: list[dict]) -> float:
        if not references:
            return 0.56
        high = sum(1 for reference in references if reference["evidenceLevel"] in {"A", "B"})
        score = 0.58 + min(high * 0.045, 0.18)
        top_score = max((reference.get("retrievalScore") or 0 for reference in references), default=0)
        if top_score > 80:
            score += 0.04
        return round(min(score, 0.82), 2)


formula_service = FormulaService()
