from types import SimpleNamespace

from app.enterprise_knowledge.service import EnterpriseKnowledgeService
from app.research_reports.contracts import ResearchReport, ResearchReportSection, ResearchReportStatement


class Store:
    def __init__(self):
        self.items = []

    def list(self, record_type, experiment_id=None):
        return [item["payload"] for item in self.items if item["recordType"] == record_type and (experiment_id is None or item["payload"]["experimentId"] == experiment_id)]

    def save(self, record_type, record_key, experiment_id, payload):
        self.items = [item for item in self.items if not (item["recordType"] == record_type and item["recordKey"] == record_key)]
        self.items.append({"recordType": record_type, "recordKey": record_key, "payload": payload})


def _report(status="reviewed"):
    statements = [
        ResearchReportStatement(statementId="fact-1", kind="fact", title="稳定区间", text="温度 36-38℃ 内结果稳定。", evidenceRefs=["dataset://v3"]),
        ResearchReportStatement(statementId="limit-1", kind="limitation", title="适用边界", text="尚未覆盖放大批次。", evidenceRefs=["evaluation://v2"]),
        ResearchReportStatement(statementId="plan-1", kind="recommendation", title="验证计划", text="完成三个独立批次复测。", evidenceRefs=["simulation://v2"]),
        ResearchReportStatement(statementId="prediction-1", kind="prediction", title="模型预测", text="预计得率提高 8%。", evidenceRefs=["simulation://v2"]),
    ]
    return ResearchReport(
        reportId="report-1", experimentId="exp-1", reportVersion=2, commandId="command-1",
        title="研发报告", status=status, inputFingerprint="sha256:input",
        sourceVersions={"dataset": "v3"},
        sections=[ResearchReportSection(sectionKey="results", title="结果", statements=statements)],
        unresolvedItems=[], generatedAt="2026-07-21T12:00:00+00:00",
        reviewedBy="负责人" if status == "reviewed" else None,
        reviewReason="逐条核验" if status == "reviewed" else None,
        reviewedAt="2026-07-21T13:00:00+00:00" if status == "reviewed" else None,
        approvedKnowledgeStatementIds=["fact-1", "limit-1", "plan-1"] if status == "reviewed" else [],
    )


def test_only_reviewed_and_explicitly_approved_statements_are_deposited():
    store = Store()
    service = EnterpriseKnowledgeService(
        store=store,
        report_source=SimpleNamespace(get=lambda *_: _report()),
        workspace_source=SimpleNamespace(get_workspace_overview=lambda _: SimpleNamespace(name="菌藻培养条件筛选")),
    )
    entries = service.deposit("exp-1", "report-1")

    assert [item.category for item in entries] == ["verifiedFact", "applicabilityBoundary", "validationPlan"]
    assert {item.sourceStatementId for item in entries} == {"fact-1", "limit-1", "plan-1"}
    assert all(item.sourceReportId == "report-1" and item.sourceReportVersion == 2 for item in entries)
    assert all(item.contentHash.startswith("sha256:") for item in entries)
    assert all(item.reviewedBy == "负责人" for item in entries)
    assert not any(item.sourceStatementId == "prediction-1" for item in entries)


def test_deposit_is_idempotent_and_draft_report_is_rejected():
    store = Store()
    report_source = SimpleNamespace(get=lambda *_: _report())
    service = EnterpriseKnowledgeService(
        store=store, report_source=report_source,
        workspace_source=SimpleNamespace(get_workspace_overview=lambda _: SimpleNamespace(name="实验一")),
    )
    first = service.deposit("exp-1", "report-1")
    second = service.deposit("exp-1", "report-1")
    assert [item.knowledgeId for item in first] == [item.knowledgeId for item in second]
    assert len(service.list(experiment_id="exp-1")) == 3

    service.reportSource = SimpleNamespace(get=lambda *_: _report(status="draft"))
    try:
        service.deposit("exp-1", "report-1")
        assert False, "draft report must not enter enterprise knowledge"
    except ValueError as exc:
        assert "reviewed" in str(exc)
