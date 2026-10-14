from __future__ import annotations

from app.result_interpretation.contracts import InterpretationProviderOutput, MetricInterpretationDraft, NextExperimentDraft, PatternDraft, ResultInterpretationContext, ResultInterpretationProviderFailure, RiskExplanationDraft


_PROHIBITED = ("控制产线", "下发指令", "直接上市", "治疗疾病", "批准仿真", "晋升模型", "execute code", "powershell")


class ResultInterpretationPolicy:
    def validate(self, context: ResultInterpretationContext, output: InterpretationProviderOutput) -> InterpretationProviderOutput:
        allowed_refs = context.allowed_evidence_refs()
        risk_ids = {risk.riskId for risk in context.risks}
        if {item.metricKey for item in output.metricInterpretations} != set(context.metrics): self._reject()
        if {item.riskId for item in output.riskExplanations} != risk_ids: self._reject()
        texts = [output.overallSummary, *output.unresolvedQuestions]
        for item in output.metricInterpretations:
            if item.metricKey not in context.metrics: self._reject()
            self._check_refs(item.evidenceRefs, allowed_refs)
            texts.append(item.interpretation)
        for item in output.observedPatterns:
            self._check_refs(item.evidenceRefs, allowed_refs); texts.append(item.statement)
        for item in output.riskExplanations:
            if item.riskId not in risk_ids: self._reject()
            self._check_refs(item.evidenceRefs, allowed_refs); texts.append(item.explanation)
        for item in output.nextExperimentSuggestions:
            self._check_refs(item.evidenceRefs, allowed_refs); texts.extend([item.title, item.purpose, *item.validationItems])
        if any(token in " ".join(texts).lower() for token in _PROHIBITED): self._reject()
        return output

    @staticmethod
    def fallback(context: ResultInterpretationContext) -> InterpretationProviderOutput:
        metrics = [MetricInterpretationDraft(metricKey=key, interpretation=f"该指标来自权威训练结果，需结合样本量与跨批次稳定性人工复核。", evidenceRefs=[f"metric:{key}"]) for key in context.metrics]
        risks = [RiskExplanationDraft(riskId=item.riskId, explanation=item.text, evidenceRefs=[item.riskId]) for item in context.risks]
        evidence = [context.risks[0].riskId] if context.risks else ["result:manual-review"]
        return InterpretationProviderOutput(
            overallSummary="当前结果可作为研发分析起点，不能替代独立实验验证或真实生产结论。",
            metricInterpretations=metrics, observedPatterns=[], riskExplanations=risks,
            nextExperimentSuggestions=[NextExperimentDraft(title="补充独立验证批次", purpose="验证模型在不同批次下的稳定性与误差变化。", evidenceRefs=evidence, validationItems=["MAE、RMSE、R² 的跨批次变化", "异常点复核结果"])],
            unresolvedQuestions=list(context.manualReviewItems),
        )

    @staticmethod
    def _check_refs(refs: list[str], allowed: set[str]) -> None:
        if not refs or any(ref not in allowed for ref in refs): ResultInterpretationPolicy._reject()

    @staticmethod
    def _reject() -> None:
        raise ResultInterpretationProviderFailure("policyRejected")
