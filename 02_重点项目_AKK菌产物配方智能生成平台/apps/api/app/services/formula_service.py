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
    "nutrition_powder": "营养粉",
    "functional_beverage": "即饮功能饮品",
    "meal_replacement": "代餐奶昔",
    "custom": "自定义产品",
}

PRODUCT_CATEGORY_LABELS = {
    "postbiotic": "AKK 后生元原料",
    "metabolite_blend": "AKK 代谢物组合",
    "fiber_complex": "AKK 纤维复配物",
    "algae_polysaccharide": "海藻多糖底物",
    "modified_algae_polysaccharide": "改性海藻多糖",
    "carrageenan_substrate": "卡拉胶底物",
    "algae_glycoprotein": "海藻糖蛋白",
    "fermented_fiber": "发酵膳食纤维",
    "encapsulation": "包埋颗粒",
    "food_matrix": "食品基质",
    "prototype_product": "产品原型",
    "polysaccharide_control": "对照多糖",
}

BASE_RATIO_PROFILES = {
    "yogurt": {
        "akk-postbiotic-powder": 44,
        "bfp-polysaccharide": 24,
        "akk-fiber-complex": 20,
        "akk-metabolite-blend": 12,
    },
    "functional_beverage": {
        "akk-metabolite-blend": 34,
        "akk-postbiotic-powder": 28,
        "bfp-polysaccharide": 22,
        "akk-fiber-complex": 16,
    },
    "nutrition_powder": {
        "akk-fiber-complex": 38,
        "akk-postbiotic-powder": 30,
        "bfp-polysaccharide": 20,
        "akk-metabolite-blend": 12,
    },
    "meal_replacement": {
        "akk-fiber-complex": 42,
        "akk-postbiotic-powder": 28,
        "bfp-polysaccharide": 18,
        "akk-metabolite-blend": 12,
    },
}


class FormulaService:
    def __init__(self, repository: MockRepository | None = None) -> None:
        self.repository = repository or MockRepository()
        self.sqlite_repository = SqliteRepository()
        self._generated_results: dict[str, dict] = {}

    def generate_formula(self, request: FormulaGenerationRequest) -> FormulaResult:
        customer_demand = self._parse_constraint_value(request.constraints, "customer_demand") or request.notes or ""
        custom_application = self._parse_constraint_value(request.constraints, "custom_application")
        project_name = self._parse_constraint_value(request.constraints, "project_name")
        application_key = self._resolve_application_key(request, custom_application, customer_demand)
        application_name = custom_application or APPLICATION_NAMES.get(request.applicationTargetId, request.applicationTargetId)

        products = self._select_products(request, application_key)
        composition = self._build_composition(products, request.constraints, application_key, customer_demand)
        references = self._select_knowledge_references(application_key, application_name, customer_demand, request.targetProperties, composition)
        risk_items = self._build_risk_items(products, references, application_key, customer_demand)
        validation_metrics = self._build_validation_metrics(products, references, application_key)
        predictions = self._build_predictions(application_name, composition, risk_items, references)
        companion_ingredients = self._build_companion_ingredients(application_key, customer_demand)
        product_advantages = self._build_product_advantages(application_name, request.targetProperties, products, composition, references)
        upgrade_suggestions = self._build_upgrade_suggestions(application_key, products, risk_items)
        experiment_suggestions = self._build_experiment_suggestions(application_key, validation_metrics)
        reasoning_summary = self._rule_reasoning_summary(application_name, composition, references)

        llm_used = False
        if any(constraint.startswith("llm_agent_mode:") for constraint in request.constraints):
            enrichment = local_llm_service.enrich_formula(
                {
                    "applicationName": application_name,
                    "customerDemand": customer_demand,
                    "targetProperties": request.targetProperties,
                    "products": [
                        {
                            "productId": product["productId"],
                            "productName": product["productName"],
                            "productCategory": PRODUCT_CATEGORY_LABELS.get(product["productCategory"], product["productCategory"]),
                            "riskLevel": product["riskLevel"],
                            "evidenceLevel": product["evidenceLevel"],
                            "description": product.get("description", ""),
                        }
                        for product in products
                    ],
                    "composition": composition,
                    "riskItems": risk_items,
                    "validationMetrics": validation_metrics,
                    "knowledgeReferences": references,
                }
            )
            if enrichment:
                llm_used = True
                product_advantages = self._list_or_fallback(enrichment.get("productAdvantages"), product_advantages)
                upgrade_suggestions = self._list_or_fallback(enrichment.get("upgradeSuggestions"), upgrade_suggestions)
                companion_ingredients = self._companion_or_fallback(enrichment.get("companionIngredients"), companion_ingredients)
                reasoning_summary = str(enrichment.get("reasoningSummary") or reasoning_summary)

        result = {
            "resultId": f"generated-{uuid4().hex[:8]}",
            "recommendationType": "rd_experiment_suggestion",
            "researchUseOnly": True,
            "research_use_only": True,
            "disclaimer": "内部研发实验建议。本方案用于概念探索、打样沟通和验证计划生成，不作为可直接上市的最终食品配方或真实生产指令。",
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
                    "confidenceScore": self._confidence_score(references, products),
                    "confidenceLevel": "medium",
                    "riskItems": risk_items,
                    "validationMetrics": validation_metrics,
                    "experimentSuggestions": experiment_suggestions,
                    "productAdvantages": product_advantages,
                    "upgradeSuggestions": upgrade_suggestions,
                    "knowledgeReferences": references,
                    "agentTrace": self._build_agent_trace(
                        application_name,
                        request.targetProperties,
                        len(references),
                        len(risk_items),
                        len(validation_metrics),
                        llm_used,
                        reasoning_summary,
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

    def _resolve_application_key(self, request: FormulaGenerationRequest, custom_application: str | None, customer_demand: str) -> str:
        if request.applicationTargetId != "custom":
            return request.applicationTargetId
        text = f"{custom_application or ''} {customer_demand} {' '.join(request.targetProperties)}".lower()
        if any(keyword in text for keyword in ["酸奶", "乳", "yogurt", "milk"]):
            return "yogurt"
        if any(keyword in text for keyword in ["饮料", "即饮", "饮品", "beverage", "drink"]):
            return "functional_beverage"
        if any(keyword in text for keyword in ["代餐", "奶昔", "体重", "meal"]):
            return "meal_replacement"
        return "nutrition_powder"

    def _select_products(self, request: FormulaGenerationRequest, application_key: str) -> list[dict]:
        products = [product for product in self.repository.get_products() if product["productId"] not in request.excludedProductIds]
        if request.preferredProductIds:
            preferred = [product for product in products if product["productId"] in request.preferredProductIds]
            return preferred[: request.maxIngredientCount] or products[: request.maxIngredientCount]
        profile = BASE_RATIO_PROFILES.get(application_key, BASE_RATIO_PROFILES["nutrition_powder"])
        products.sort(key=lambda product: profile.get(product["productId"], 0), reverse=True)
        return products[: request.maxIngredientCount]

    def _build_composition(self, products: list[dict], constraints: list[str], application_key: str, demand: str) -> list[dict]:
        ratios = self._parse_custom_ratios(constraints)
        if not any(ratios.get(product["productId"], 0) > 0 for product in products):
            profile = BASE_RATIO_PROFILES.get(application_key, BASE_RATIO_PROFILES["nutrition_powder"])
            ratios = {product["productId"]: profile.get(product["productId"], 100 / max(len(products), 1)) for product in products}
        total = sum(max(ratios.get(product["productId"], 0), 0) for product in products) or 1
        return [
            {
                "productId": product["productId"],
                "productName": product["productName"],
                "ratioPercent": round(max(ratios.get(product["productId"], 0), 0) / total * 100, 2),
                "role": self._product_role(product),
            }
            for product in products
        ]

    def _select_knowledge_references(
        self,
        application_key: str,
        application_name: str,
        customer_demand: str,
        target_properties: list[str],
        composition: list[dict],
    ) -> list[dict]:
        topic_map = {
            "yogurt": ["postbiotic", "food_application", "dairy_matrix", "safety", "regulatory"],
            "nutrition_powder": ["fiber_polysaccharide", "postbiotic", "clinical", "safety"],
            "functional_beverage": ["metabolite", "postbiotic", "food_application", "safety"],
            "meal_replacement": ["fiber_polysaccharide", "clinical", "safety"],
        }
        product_text = " ".join(item["productName"] for item in composition)
        query = f"{application_name} {customer_demand} {' '.join(target_properties)} {product_text} AKK 红毛藻多糖 后生元 食品基质 安全 稳定性"
        items = knowledge_service.search_items(query=query, topics=topic_map.get(application_key, ["food_application", "safety"]))
        references = []
        for item in items[:6]:
            reason_parts = item.matchReasons[:2] or item.usableInsights[:1]
            boundary = item.riskNotes[0] if item.riskNotes else "需要结合目标食品基质、小试条件和检测结果验证。"
            references.append(
                {
                    "knowledgeId": item.knowledgeId,
                    "title": item.title,
                    "evidenceLevel": item.evidenceLevel,
                    "sourceUrl": item.sourceUrl,
                    "retrievalScore": item.retrievalScore,
                    "keyPassages": (item.keyPassages[:2] or ([item.summary] if item.summary else [])),
                    "relevanceReason": f"{'；'.join(reason_parts)}。引用用途：支撑研发假设、适用场景或风险边界判断。边界：{boundary}",
                }
            )
        return references

    def _build_predictions(self, application_name: str, composition: list[dict], risks: list[dict], references: list[dict]) -> list[dict]:
        high_risk = sum(1 for risk in risks if risk["riskLevel"] == "high")
        confidence = self._confidence_score(references, [])
        return [
            {
                "predictionId": "pred-product-fit",
                "targetName": "产品概念匹配",
                "predictedValue": "较高" if confidence >= 0.68 else "需要补充验证",
                "confidenceScore": confidence,
                "explanation": f"当前目标为{application_name}，已选 AKK 相关对象与知识库中的后生元、海藻多糖或食品基质证据存在匹配，可作为首轮小试起点。",
            },
            {
                "predictionId": "pred-validation-pressure",
                "targetName": "验证压力",
                "predictedValue": "偏高" if high_risk else "中等",
                "confidenceScore": 0.64,
                "explanation": "风险压力来自高风险对象、食品基质外推和加工稳定性不确定性，需要用小试数据回填后再提高置信度。",
            },
            {
                "predictionId": "pred-process-stability",
                "targetName": "加工稳定性",
                "predictedValue": "待验证",
                "confidenceScore": 0.62,
                "explanation": "需要重点验证 pH、热处理、剪切、复水、析水、浊度和标志物保留，不应直接外推为生产结论。",
            },
        ]

    def _build_risk_items(self, products: list[dict], references: list[dict], application_key: str, demand: str) -> list[dict]:
        risks = [risk for product in products for risk in product["riskItems"]]
        risks.append(
            {
                "riskId": "research-boundary",
                "riskName": "研发外推边界",
                "riskLevel": "medium",
                "description": "论文或专利证据不能直接等同于目标产品中的最终功效，也不能替代食品基质和工艺条件下的小试验证。",
                "mitigationSuggestion": "保留配比假设、引用证据、批次记录和验证数据，进入下一轮前由研发负责人复核。",
            }
        )
        if application_key in {"yogurt", "functional_beverage"}:
            risks.append(
                {
                    "riskId": "acid-system",
                    "riskName": "酸性体系稳定性",
                    "riskLevel": "high",
                    "description": "酸奶或饮品体系可能影响 AKK 相关标志物、浊度、沉淀和风味表现。",
                    "mitigationSuggestion": "设置 pH、热处理、货架期和离心沉淀观察实验。",
                }
            )
        if any(keyword in demand for keyword in ["儿童", "孩子", "老人", "银发"]):
            risks.append(
                {
                    "riskId": "sensitive-population",
                    "riskName": "敏感人群边界",
                    "riskLevel": "high",
                    "description": "面向儿童或银发人群时，需要更严格的安全性、法规和标签审核。",
                    "mitigationSuggestion": "商业化前进行法规复核、标签审核和目标人群适用性评估。",
                }
            )
        return risks[:7]

    def _build_validation_metrics(self, products: list[dict], references: list[dict], application_key: str) -> list[dict]:
        metrics = [metric for product in products for metric in product["validationMetrics"]]
        names = {metric["metricName"] for metric in metrics}
        extras = [
            {
                "metricId": "sensory-acceptance",
                "metricName": "感官接受度",
                "methodSuggestion": "开展 3-5 个比例梯度的小试感官评价，记录底味、酸甜、口感和外观。",
                "expectedRange": "内部小试评分 >= 7/10",
                "priority": "required",
            },
            {
                "metricId": "evidence-review",
                "metricName": "证据与合规复核",
                "methodSuggestion": "复核知识库引用材料，确认适用基质、人群、剂量和法规边界。",
                "expectedRange": "研发评审通过",
                "priority": "required",
            },
            {
                "metricId": "marker-retention",
                "metricName": "关键标志物保留",
                "methodSuggestion": "围绕后生元、代谢物或结构指标设置检测方法，记录加工前后变化。",
                "expectedRange": "建立首轮内部基线",
                "priority": "recommended",
            },
        ]
        if application_key in {"yogurt", "functional_beverage"}:
            extras.append(
                {
                    "metricId": "acid-stability",
                    "metricName": "酸性体系稳定性",
                    "methodSuggestion": "在目标 pH 和加速条件下观察浊度、沉淀、风味和关键指标变化。",
                    "expectedRange": "变化幅度 <= 10%",
                    "priority": "required",
                }
            )
        for metric in extras:
            if metric["metricName"] not in names:
                metrics.append(metric)
                names.add(metric["metricName"])
        return metrics[:9]

    def _build_companion_ingredients(self, application_key: str, demand: str) -> list[dict]:
        templates = {
            "yogurt": [
                ("inulin", "菊粉", "膳食纤维/益生元", "0.5%-2.0%", "提升低糖酸奶厚度和肠道健康概念表达", "高添加量可能带来胀气感"),
                ("citrus-fiber", "柑橘纤维", "结构稳定剂", "0.1%-0.4%", "改善乳基体系悬浮和稠厚感", "需要验证酸性体系黏度变化"),
            ],
            "nutrition_powder": [
                ("fos", "低聚果糖", "益生元", "1%-5%", "强化益生元与清洁标签表达", "甜度和胃肠耐受性需验证"),
                ("oat-beta-glucan", "燕麦β-葡聚糖", "膳食纤维", "0.5%-3.0%", "支持饱腹感和粉体营养结构", "可能影响复水速度"),
            ],
            "functional_beverage": [
                ("pectin", "果胶", "水相稳定剂", "0.05%-0.25%", "改善悬浮稳定性和轻稠口感", "过量可能导致口感黏腻"),
                ("erythritol", "赤藓糖醇", "低糖甜味体系", "1%-4%", "支持低糖和清爽口感", "需要验证酸甜协调性"),
            ],
            "meal_replacement": [
                ("pea-protein", "豌豆蛋白", "植物蛋白", "8%-18%", "支持代餐营养结构和植物基卖点", "豆腥味需要遮蔽"),
                ("konjac", "魔芋葡甘聚糖", "饱腹纤维", "0.2%-1.0%", "强化饱腹感和稠厚口感", "黏度过高会影响饮用体验"),
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

    def _build_product_advantages(self, application_name: str, target_properties: list[str], products: list[dict], composition: list[dict], references: list[dict]) -> list[str]:
        product_names = "、".join(product["productName"] for product in products)
        target_text = "、".join([target for target in target_properties if target.strip()][:4]) or "肠道健康、稳定性和低风险打样"
        evidence_count = len([reference for reference in references if reference["evidenceLevel"] in {"A", "B"}])
        top = max(composition, key=lambda item: item["ratioPercent"]) if composition else None
        return [
            f"围绕{application_name}形成内部研发方案，适合用于客户沟通、首轮打样和实验计划制定。",
            f"核心研发对象为{product_names}，其中{top['productName']}占比最高，可作为首轮验证主线。" if top else "已形成首轮组合。",
            f"目标标签覆盖{target_text}，可生成多个比例梯度并回填实验结果。",
            f"知识库检索到 {evidence_count} 条 A/B 级优先证据，可辅助说明研发依据和风险边界。",
        ]

    def _build_upgrade_suggestions(self, application_key: str, products: list[dict], risks: list[dict]) -> list[str]:
        suggestions = [
            "下一轮建议设置 3 个比例梯度，并把感官、稳定性、标志物保留和成本同步记录。",
            "高风险对象不要直接放大，应先完成边界验证和批次一致性检查。",
            "真实实验数据回填后，可把当前规则评分升级为监督学习模型或贝叶斯优化模型。",
        ]
        if any(product["productCategory"] in {"algae_polysaccharide", "carrageenan_substrate"} for product in products):
            suggestions.append("海藻多糖方向建议补充分子量、硫酸基、总糖、糖醛酸和黏度数据。")
        if any(risk["riskLevel"] == "high" for risk in risks):
            suggestions.append("存在高风险项，建议先输出为小试验证任务，不进入生产参数下发。")
        return suggestions[:5]

    def _build_experiment_suggestions(self, application_key: str, metrics: list[dict]) -> list[str]:
        required = [metric["metricName"] for metric in metrics if metric.get("priority") == "required"][:4]
        suggestions = [
            "按当前配比制作 A/B/C 小试样品，记录混合均匀性、外观、气味和口感。",
            f"优先验证：{'、'.join(required) if required else '稳定性、感官接受度和关键标志物保留'}。",
            "把知识库引用、配比假设、实验批次和异常观察同步归档，作为下一轮模型升级依据。",
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
        reasoning_summary: str,
    ) -> list[dict]:
        target_text = "、".join(target_properties[:4]) or "内部研发目标"
        return [
            {"agentName": "需求理解模块", "status": "completed", "outputSummary": f"识别目标产品为{application_name}，核心目标包括{target_text}。"},
            {"agentName": "产物匹配模块", "status": "completed", "outputSummary": "根据前端选择的 AKK 产物、底物和食品基质生成配比。"},
            {"agentName": "知识库检索模块", "status": "completed", "outputSummary": f"检索到 {knowledge_count} 条知识库证据，用于解释研发依据和边界。"},
            {"agentName": "风险验证模块", "status": "completed", "outputSummary": f"识别 {risk_count} 项风险和 {validation_count} 项验证指标。"},
            {
                "agentName": "大模型增强模块",
                "status": "completed" if llm_used else "fallback",
                "outputSummary": reasoning_summary if llm_used else "大模型未返回可用结构化结果，已使用规则模型生成内部研发建议。",
            },
            {"agentName": "建议书生成模块", "status": "completed", "outputSummary": "输出内部研发实验建议，不作为最终生产配方。"},
        ]

    def _rule_reasoning_summary(self, application_name: str, composition: list[dict], references: list[dict]) -> str:
        ratio_text = "、".join(f"{item['productName']} {item['ratioPercent']}%" for item in composition)
        evidence_text = "、".join(reference["title"] for reference in references[:2]) if references else "未命中强证据"
        return f"规则模型已根据{application_name}、已选研发对象和知识库证据生成首轮配比：{ratio_text}。重点引用：{evidence_text}。"

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
                    "purpose": str(item.get("purpose") or "改善产品结构、口感或验证表达"),
                    "riskNote": str(item.get("riskNote") or "需要小试验证稳定性和感官影响"),
                }
            )
        return cleaned or fallback

    def _product_role(self, product: dict) -> str:
        category = PRODUCT_CATEGORY_LABELS.get(product.get("productCategory"), "AKK 相关对象")
        if product["riskLevel"] == "high":
            return f"{category}，用于高价值方向验证，必须先做风险边界检查"
        if product["evidenceLevel"] in {"A", "B"}:
            return f"{category}，用于支撑首轮小试和模型假设"
        return f"{category}，用于探索性对照或产品原型验证"

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

    def _parse_constraint_value(self, constraints: list[str], key: str) -> str | None:
        prefix = f"{key}:"
        for constraint in constraints:
            if constraint.startswith(prefix):
                return constraint.split(":", 1)[1].strip() or None
        return None

    def _name_formula(self, application_name: str, composition: list[dict], demand: str) -> str:
        if "儿童" in demand:
            prefix = "儿童友好型"
        elif "银发" in demand or "老人" in demand:
            prefix = "银发营养型"
        elif "低糖" in demand:
            prefix = "低糖轻负担"
        else:
            prefix = "AKK 内部研发"
        return f"{prefix}{application_name}方案"

    def _confidence_score(self, references: list[dict], products: list[dict]) -> float:
        high_evidence = sum(1 for reference in references if reference["evidenceLevel"] in {"A", "B"})
        product_bonus = sum(1 for product in products if product.get("evidenceLevel") in {"A", "B"}) * 0.015
        score = 0.58 + min(high_evidence * 0.04, 0.18) + min(product_bonus, 0.06)
        return round(min(score, 0.84), 2)


formula_service = FormulaService()
