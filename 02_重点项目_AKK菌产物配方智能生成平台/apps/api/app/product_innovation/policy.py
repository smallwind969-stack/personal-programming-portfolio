from __future__ import annotations

import re

from app.product_innovation.contracts import InnovationMaterialRoleDraft, InnovationMetricDraft, InnovationProviderFailure, InnovationProviderOutput, InnovationSuggestionDraft, ProductInnovationContext, ProductInnovationInput


FIXED_BOUNDARIES = ["仅作为研发实验建议，不是可直接上市的最终产品方案", "不得替代法规、安全和现实实验验证", "不得生成或下发真实产线控制指令"]
_FORBIDDEN = ("治疗疾病", "预防疾病", "直接上市", "保证上市", "控制产线", "下发指令", "最终配方", "模型晋升", "execute code", "powershell")
_RATIO = re.compile(r"(?:原料|成分|配方).{0,8}(?:比例|\d+(?:\.\d+)?\s*%)")


class ProductInnovationPolicy:
    def build_context(self, experiment_id: str, request: ProductInnovationInput, evidence) -> ProductInnovationContext:
        return ProductInnovationContext(experimentId=experiment_id, request=request, evidence=evidence, fixedBoundaries=FIXED_BOUNDARIES)

    def validate(self, context: ProductInnovationContext, output: InnovationProviderOutput) -> InnovationProviderOutput:
        allowed = context.allowed_evidence_refs()
        refs = list(output.evidenceRefs)
        texts = [output.workingName, output.category, output.problemStatement, *output.targetUserTags, *output.usageScenarios, *output.valuePropositions, *output.costAssumptions, *output.processConstraints, *output.regulatoryConstraints, *output.risks, *output.unresolvedQuestions]
        for item in output.targetMetrics: refs.extend(item.evidenceRefs); texts.extend([item.metricName, item.targetDescription])
        for item in output.materialRoles: refs.extend(item.evidenceRefs); texts.extend([item.role, item.purpose, *item.constraints])
        for item in output.validationPlan: refs.extend(item.evidenceRefs); texts.extend([item.title, item.purpose, *item.validationItems])
        joined = " ".join(texts).lower()
        if any(ref not in allowed for ref in refs) or any(token in joined for token in _FORBIDDEN) or _RATIO.search(joined):
            raise InnovationProviderFailure("policyRejected")
        return output

    @staticmethod
    def fallback(context: ProductInnovationContext) -> InnovationProviderOutput:
        request = context.request
        category = request.industry or "待确认行业"
        return InnovationProviderOutput(
            workingName="产品概念验证项目", category=category,
            problemStatement=f"围绕“{request.brief[:160]}”建立可测试的产品需求与研发边界。",
            targetUserTags=request.targetUsers or ["目标用户待确认"], usageScenarios=["使用场景待访谈确认"],
            valuePropositions=["把自然语言构想转化为可验证研发目标"],
            targetMetrics=[InnovationMetricDraft(metricName="核心性能指标", direction="target", targetDescription="由研发人员补充基线、目标区间和测量方法", evidenceRefs=["input:brief"])],
            materialRoles=[InnovationMaterialRoleDraft(role="功能角色待筛选", purpose="根据目标性能筛选候选原材料功能角色，不在本阶段确定配比", constraints=["来源可追溯", "安全与法规适用性待确认"], evidenceRefs=["input:brief"])],
            costAssumptions=["成本为待验证假设，必须以供应商报价和小试消耗核算为准"],
            processConstraints=["具体工艺窗口必须由后续数据建模和小试确定"], regulatoryConstraints=list(FIXED_BOUNDARIES),
            risks=["需求仍包含未验证假设", "性能、成本与工艺可行性需要联合验证"],
            unresolvedQuestions=["目标用户、场景和验收阈值是否明确", "适用法规与安全边界是什么"],
            validationPlan=[InnovationSuggestionDraft(title="产品概念小试", purpose="验证核心性能、感官/使用体验、稳定性与成本假设", evidenceRefs=["input:brief"], validationItems=["核心性能指标", "稳定性", "安全与法规", "单位成本假设"])],
            evidenceRefs=["input:brief", "boundary:research-only"],
        )
