from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.research_reports.contracts import ResearchReport, ResearchReportSection, ResearchReportStatement
import app.routers.experiments as experiments_router


client = TestClient(app)


def _report():
    return ResearchReport(
        reportId="report-1", experimentId="exp-1", reportVersion=1, commandId="command-1",
        title="实验研发报告", inputFingerprint="sha256:input", sourceVersions={"dataset": "dataset-1"},
        sections=[ResearchReportSection(sectionKey="data", title="数据基础", statements=[
            ResearchReportStatement(statementId="statement-1", kind="fact", title="数据量", text="共 10 条记录", evidenceRefs=["dataset://dataset-1"]),
        ])], unresolvedItems=[], generatedAt="2026-07-21T12:00:00+00:00",
    )


def test_research_report_api_create_list_detail_and_markdown(monkeypatch):
    report = _report()
    service = SimpleNamespace(
        create=lambda experiment_id, command_id: report,
        list=lambda experiment_id: [report],
        get=lambda experiment_id, report_id: report,
        render_markdown=lambda item: "# 实验研发报告\n\n[事实] 数据量",
    )
    monkeypatch.setattr(experiments_router, "research_report_service", service, raising=False)

    created = client.post("/experiments/exp-1/research-reports", json={"commandId": "command-1"})
    listed = client.get("/experiments/exp-1/research-reports")
    detail = client.get("/experiments/exp-1/research-reports/report-1")
    markdown = client.get("/experiments/exp-1/research-reports/report-1/markdown")
    data_package = client.get("/experiments/exp-1/research-reports/report-1/json")

    assert created.status_code == 200
    assert listed.json()[0]["reportVersion"] == 1
    assert detail.json()["sections"][0]["statements"][0]["kind"] == "fact"
    assert markdown.headers["content-type"].startswith("text/markdown")
    assert data_package.status_code == 200
    assert data_package.headers["content-type"].startswith("application/json")
    assert data_package.json()["inputFingerprint"] == "sha256:input"
    assert "[事实]" in markdown.text


def test_unknown_research_report_returns_404(monkeypatch):
    def missing(*_): raise LookupError("research report was not found")
    monkeypatch.setattr(experiments_router, "research_report_service", SimpleNamespace(get=missing), raising=False)
    assert client.get("/experiments/exp-1/research-reports/missing").status_code == 404


def test_report_review_and_knowledge_deposit_api(monkeypatch):
    report = _report().model_copy(update={
        "status": "reviewed", "reviewedBy": "研发负责人", "reviewReason": "逐条复核",
        "reviewedAt": "2026-07-21T13:00:00+00:00", "approvedKnowledgeStatementIds": ["statement-1"],
    })
    entry = {
        "knowledgeId": "knowledge-1", "experimentId": "exp-1", "experimentName": "实验一",
        "category": "verifiedFact", "title": "数据量", "content": "共 10 条记录",
        "evidenceRefs": ["dataset://dataset-1"], "sourceReportId": "report-1",
        "sourceReportVersion": 1, "sourceStatementId": "statement-1",
        "sourceInputFingerprint": "sha256:input", "contentHash": "sha256:" + "a" * 64,
        "reviewedBy": "研发负责人", "reviewReason": "逐条复核",
        "reviewedAt": "2026-07-21T13:00:00+00:00", "depositedAt": "2026-07-21T13:01:00+00:00",
        "status": "active",
    }
    report_service = SimpleNamespace(review=lambda *args, **kwargs: report)
    knowledge_service = SimpleNamespace(deposit=lambda *args: [entry], list=lambda **kwargs: [entry])
    monkeypatch.setattr(experiments_router, "research_report_service", report_service, raising=False)
    monkeypatch.setattr(experiments_router, "enterprise_knowledge_service", knowledge_service, raising=False)

    reviewed = client.post("/experiments/exp-1/research-reports/report-1/review", json={
        "operator": "研发负责人", "reason": "逐条复核", "approvedStatementIds": ["statement-1"],
    })
    deposited = client.post("/experiments/exp-1/research-reports/report-1/knowledge-deposit")
    listed = client.get("/experiments/enterprise-knowledge", params={"experimentId": "exp-1"})

    assert reviewed.status_code == 200
    assert reviewed.json()["approvedKnowledgeStatementIds"] == ["statement-1"]
    assert deposited.status_code == 200
    assert deposited.json()[0]["category"] == "verifiedFact"
    assert listed.status_code == 200
    assert listed.json()[0]["sourceReportId"] == "report-1"


def test_knowledge_usage_register_and_list_api(monkeypatch):
    usage = {
        "usageId": "usage-1", "experimentId": "exp-1", "knowledgeIds": ["knowledge-1"],
        "sourceEntries": [{"knowledgeId": "knowledge-1", "experimentId": "source-exp", "experimentName": "来源实验", "category": "verifiedFact", "title": "稳定区间", "content": "温度范围稳定", "evidenceRefs": ["dataset://v1"], "sourceReportId": "report-1", "sourceReportVersion": 1, "sourceStatementId": "statement-1", "sourceInputFingerprint": "sha256:input", "contentHash": "sha256:" + "a" * 64, "reviewedBy": "负责人", "reviewReason": "核验", "reviewedAt": "2026-07-21T01:00:00+00:00", "depositedAt": "2026-07-21T01:01:00+00:00", "status": "active"}], "purpose": "modeling", "targetVersion": "dataset-v4",
        "operator": "建模负责人", "note": "用于解释边界", "usageFingerprint": "sha256:" + "b" * 64,
        "createdAt": "2026-07-21T14:00:00+00:00",
    }
    service = SimpleNamespace(register=lambda *args, **kwargs: usage, list=lambda **kwargs: [usage])
    monkeypatch.setattr(experiments_router, "enterprise_knowledge_usage_service", service, raising=False)
    created = client.post("/experiments/exp-1/knowledge-usage", json={
        "knowledgeIds": ["knowledge-1"], "purpose": "modeling", "targetVersion": "dataset-v4",
        "operator": "建模负责人", "note": "用于解释边界",
    })
    listed = client.get("/experiments/exp-1/knowledge-usage")
    assert created.status_code == 200
    assert created.json()["usageId"] == "usage-1"
    assert listed.status_code == 200
    assert listed.json()[0]["purpose"] == "modeling"
