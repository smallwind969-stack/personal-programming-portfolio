from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import uuid4

from app.research_reports.contracts import ResearchReport, ResearchReportSection, ResearchReportStatement


class _MemoryStore:
    def __init__(self) -> None:
        self.records: list[dict] = []

    def list(self, record_type: str, experiment_id: str | None = None) -> list[dict]:
        return [item for item in self.records if experiment_id is None or item["experimentId"] == experiment_id]

    def save(self, record_type: str, record_key: str, experiment_id: str, payload: dict) -> None:
        self.records = [item for item in self.records if item["reportId"] != record_key]
        self.records.append(payload)


class ResearchReportService:
    def __init__(
        self, *, store, workspace_source, dataset_source, model_registry,
        evaluation_source, simulation_source, optimization_source,
    ) -> None:
        self.store = store or _MemoryStore()
        self.workspaceSource = workspace_source
        self.datasetSource = dataset_source
        self.modelRegistry = model_registry
        self.evaluationSource = evaluation_source
        self.simulationSource = simulation_source
        self.optimizationSource = optimization_source

    def create(self, experiment_id: str, command_id: str) -> ResearchReport:
        prior = next((item for item in self.list(experiment_id) if item.commandId == command_id), None)
        if prior is not None:
            return prior
        workspace = self.workspaceSource.get_workspace_overview(experiment_id)
        if workspace is None:
            raise LookupError("experiment workspace was not found")
        snapshot = self._safe(lambda: self.datasetSource.get_latest_dataset_snapshot(experiment_id))
        model = self._safe(lambda: self.modelRegistry.latest(experiment_id))
        evaluation = self._safe(lambda: self.evaluationSource.latest_report(experiment_id))
        simulation = self._safe(lambda: self.simulationSource.peek_latest(experiment_id))
        optimization = self._safe(lambda: self.optimizationSource.peek_latest(experiment_id))
        existing = self.list(experiment_id)
        version = max((item.reportVersion for item in existing), default=0) + 1
        source_versions = {
            "workspace": getattr(workspace, "updatedAt", "unknown"),
            "dataset": getattr(snapshot, "snapshotId", "not_available") if snapshot else "not_available",
            "model": getattr(model, "modelVersion", "not_available") if model else "not_available",
            "evaluation": getattr(evaluation, "reportId", "not_available") if evaluation else "not_available",
            "simulation": getattr(simulation, "runId", "not_available") if simulation else "not_available",
            "optimization": getattr(optimization, "runId", "not_available") if optimization else "not_available",
        }
        fingerprint = self._hash(source_versions)
        sections, unresolved = self._assemble(workspace, snapshot, model, evaluation, simulation, optimization)
        report = ResearchReport(
            reportId=f"research-report-{uuid4().hex[:12]}", experimentId=experiment_id,
            reportVersion=version, commandId=command_id,
            title=f"{workspace.name}研发报告（版本 {version}）",
            inputFingerprint=fingerprint, sourceVersions=source_versions,
            sections=sections, unresolvedItems=unresolved,
            generatedAt=datetime.now(timezone.utc).isoformat(),
        )
        self.store.save("research_report", report.reportId, experiment_id, report.model_dump(mode="json"))
        return report

    def list(self, experiment_id: str) -> list[ResearchReport]:
        reports = [ResearchReport.model_validate(item) for item in self.store.list("research_report", experiment_id)]
        reports.sort(key=lambda item: (item.reportVersion, item.generatedAt), reverse=True)
        return reports

    def get(self, experiment_id: str, report_id: str) -> ResearchReport:
        report = next((item for item in self.list(experiment_id) if item.reportId == report_id), None)
        if report is None:
            raise LookupError("research report was not found")
        return report

    def latest(self, experiment_id: str) -> ResearchReport | None:
        reports = self.list(experiment_id)
        return reports[0] if reports else None

    def review(
        self, experiment_id: str, report_id: str, *, operator: str, reason: str,
        approved_statement_ids: list[str],
    ) -> ResearchReport:
        report = self.get(experiment_id, report_id)
        if report.status == "reviewed":
            raise ValueError("research report is already reviewed")
        statements = {
            item.statementId: item
            for section in report.sections for item in section.statements
        }
        unknown = sorted(set(approved_statement_ids) - set(statements))
        if unknown:
            raise ValueError(f"unknown report statement: {', '.join(unknown)}")
        predictions = [
            statement_id for statement_id in approved_statement_ids
            if statements[statement_id].kind == "prediction"
        ]
        if predictions:
            raise ValueError("prediction statements cannot enter formal knowledge")
        reviewed = report.model_copy(update={
            "status": "reviewed",
            "reviewedBy": operator.strip(),
            "reviewReason": reason.strip(),
            "reviewedAt": datetime.now(timezone.utc).isoformat(),
            "approvedKnowledgeStatementIds": list(dict.fromkeys(approved_statement_ids)),
        })
        self.store.save(
            "research_report", reviewed.reportId, experiment_id,
            reviewed.model_dump(mode="json"),
        )
        return reviewed

    @staticmethod
    def render_markdown(report: ResearchReport) -> str:
        labels = {"fact": "事实", "prediction": "模型预测", "recommendation": "研发建议", "limitation": "限制条件"}
        lines = [f"# {report.title}", "", f"报告编号：{report.reportId}", f"输入指纹：{report.inputFingerprint}", ""]
        for section in report.sections:
            lines.extend([f"## {section.title}", ""])
            for item in section.statements:
                lines.extend([f"### [{labels[item.kind]}] {item.title}", "", item.text, "", f"证据：{', '.join(item.evidenceRefs)}", ""])
        if report.unresolvedItems:
            lines.extend(["## 待确认事项", "", *[f"- {item}" for item in report.unresolvedItems], ""])
        lines.extend(["## 使用边界", "", report.disclaimer, ""])
        return "\n".join(lines)

    def _assemble(self, workspace, snapshot, model, evaluation, simulation, optimization):
        groups: dict[str, list[ResearchReportStatement]] = {"overview": [], "data": [], "model": [], "simulation": [], "optimization": []}
        unresolved: list[str] = []
        self._add(groups["overview"], "fact", "实验目标", f"目标产品：{workspace.targetProduct or '未填写'}；研发目标：{workspace.objective}。", [f"experiment://{workspace.experimentId}"])
        if snapshot:
            self._add(groups["data"], "fact", "数据资产规模", f"数据快照 {snapshot.snapshotId} 汇总 {snapshot.assetCount} 份文件、{snapshot.alignedRowCount} 条对齐记录。", [f"dataset://{snapshot.snapshotId}"])
            if snapshot.anomalyCount:
                self._add(groups["data"], "limitation", "数据异常提示", f"当前快照包含 {snapshot.anomalyCount} 项异常提示，解释模型结果前应逐项复核。", [f"dataset://{snapshot.snapshotId}"])
        else:
            unresolved.append("尚未形成可引用的数据快照。")
        if model:
            metrics = "，".join(f"{key}={value:.4g}" for key, value in model.metrics.items())
            self._add(groups["model"], "fact", "已晋升数学模型", f"模型 {model.modelVersion}（{model.modelType}）以 {model.targetField} 为目标；记录指标：{metrics}。", [f"model://{model.modelVersion}", f"dataset://{model.datasetSnapshotId}"])
        else:
            unresolved.append("尚无经人工晋升的正式模型版本。")
        if evaluation:
            self._add(groups["model"], "fact", "可靠性评估", f"评估报告 {evaluation.reportId} 的可靠性评分为 {evaluation.reliabilityScore * 100:.1f}%，状态为 {evaluation.status}，仿真准入{'已批准' if evaluation.admissionAllowed else '未批准'}。", [f"model-evaluation://{evaluation.reportId}"])
            for reason in evaluation.admissionReasons:
                self._add(groups["model"], "limitation", "模型适用限制", reason, [f"model-evaluation://{evaluation.reportId}"])
        elif model:
            unresolved.append("正式模型尚无独立可靠性评估报告。")
        if simulation and simulation.officialResult:
            predictions = simulation.officialResult.predictions.model_dump(mode="json")
            prediction_text = "，".join(f"{key}={value}" for key, value in predictions.items())
            self._add(groups["simulation"], "prediction", "仿真预测结果", f"仿真运行 {simulation.runId} 输出：{prediction_text}。", [f"simulation://{simulation.runId}", f"simulation-snapshot://{simulation.officialResult.snapshotId}"])
            for risk in simulation.officialResult.risks:
                self._add(groups["simulation"], "limitation", "仿真风险", risk, [f"simulation://{simulation.runId}"])
            for item in simulation.officialResult.validationIndicators:
                self._add(groups["simulation"], "recommendation", "仿真验证建议", item, [f"simulation://{simulation.runId}"])
        else:
            unresolved.append("尚无完成并形成正式快照的仿真运行。")
        if optimization and optimization.resultSummary:
            for outcome in optimization.resultSummary.predictedOutcomes:
                self._add(groups["optimization"], "prediction", "候选工艺预期", outcome, [f"optimization://{optimization.runId}"])
            for risk in optimization.resultSummary.riskItems:
                self._add(groups["optimization"], "limitation", "工艺放大风险", risk, [f"optimization://{optimization.runId}"])
            for item in optimization.resultSummary.validationItems:
                self._add(groups["optimization"], "recommendation", "下一轮实验", item, [f"optimization://{optimization.runId}"])
        else:
            unresolved.append("工艺优化尚未形成可引用的结果摘要。")
        titles = {"overview": "实验概况", "data": "数据基础", "model": "数学建模", "simulation": "仿真结果", "optimization": "工艺优化与下一步"}
        return [ResearchReportSection(sectionKey=key, title=titles[key], statements=items) for key, items in groups.items() if items], unresolved

    @staticmethod
    def _add(items, kind, title, text, evidence):
        digest = sha256(f"{kind}|{title}|{text}|{'|'.join(evidence)}".encode("utf-8")).hexdigest()[:12]
        items.append(ResearchReportStatement(statementId=f"statement-{digest}", kind=kind, title=title, text=text, evidenceRefs=evidence))

    @staticmethod
    def _safe(factory):
        try: return factory()
        except (LookupError, ValueError): return None

    @staticmethod
    def _hash(payload):
        return "sha256:" + sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
