from types import SimpleNamespace

from app.research_reports.service import ResearchReportService


class Store:
    def __init__(self): self.items = []
    def list(self, record_type, experiment_id=None): return [item for item in self.items if experiment_id is None or item["experimentId"] == experiment_id]
    def save(self, record_type, record_key, experiment_id, payload):
        self.items = [item for item in self.items if item["reportId"] != record_key]
        self.items.append(payload)


def _service(store=None):
    store = store or Store()
    workspace = SimpleNamespace(
        experimentId="exp-1", name="菌藻培养优化", objective="提高目标产物得率", targetProduct="菌藻培养产物",
        targetMetrics=["得率", "稳定性"], sourceType="enterprise", updatedAt="2026-07-21T08:00:00+00:00",
    )
    snapshot = SimpleNamespace(snapshotId="dataset-v3", datasetFingerprint="sha256:data", assetCount=3, alignedRowCount=120, anomalyCount=2, status="modeling_ready")
    model = SimpleNamespace(modelVersion="model-v2", modelType="random_forest", targetField="yield", metrics={"r2": .91, "mae": .08}, datasetSnapshotId="dataset-v3", datasetFingerprint="sha256:data", artifactFingerprint="sha256:model", approvedBy="负责人", approvedAt="2026-07-21T09:00:00+00:00")
    evaluation = SimpleNamespace(reportId="evaluation-v2", modelVersion="model-v2", status="confirmed", reliabilityScore=.88, admissionAllowed=True, admissionReasons=["仍需独立批次验证"])
    simulation = SimpleNamespace(runId="simulation-v2", version=2, status="completed", modelVersion="model-v2", reliabilityScore=.88, bindingVersions=["binding-v2"], officialResult=SimpleNamespace(snapshotId="snapshot-v2", predictions=SimpleNamespace(model_dump=lambda mode=None: {"yield": 2.4}), risks=["外推风险"], validationIndicators=["复测得率"]), updatedAt="2026-07-21T10:00:00+00:00")
    optimization = SimpleNamespace(runId="optimization-v2", version=2, status="needsReview", selectedPlanId="plan-1", submittedParameters=SimpleNamespace(model_dump=lambda mode=None: {"temperatureC": 37.0, "ph": 6.8}), resultSummary=SimpleNamespace(confidenceScore=.84, predictedOutcomes=["预测得率提高 8%"], riskItems=["放大效应未知"], validationItems=["三批次复验"]), updatedAt="2026-07-21T11:00:00+00:00")
    return ResearchReportService(
        store=store, workspace_source=SimpleNamespace(get_workspace_overview=lambda _: workspace),
        dataset_source=SimpleNamespace(get_latest_dataset_snapshot=lambda _: snapshot),
        model_registry=SimpleNamespace(latest=lambda _: model),
        evaluation_source=SimpleNamespace(latest_report=lambda _: evaluation),
        simulation_source=SimpleNamespace(peek_latest=lambda _: simulation),
        optimization_source=SimpleNamespace(peek_latest=lambda _: optimization),
    ), store


def test_report_separates_facts_predictions_recommendations_and_limitations():
    service, _ = _service()
    report = service.create("exp-1", "command-1")

    kinds = {statement.kind for section in report.sections for statement in section.statements}
    assert kinds == {"fact", "prediction", "recommendation", "limitation"}
    assert any("120" in item.text and item.kind == "fact" for section in report.sections for item in section.statements)
    assert any("预测得率提高" in item.text and item.kind == "prediction" for section in report.sections for item in section.statements)
    assert all(item.evidenceRefs for section in report.sections for item in section.statements)
    assert report.sourceVersions["model"] == "model-v2"
    assert report.status == "draft"


def test_report_versions_are_immutable_and_command_is_idempotent():
    service, store = _service()
    first = service.create("exp-1", "command-1")
    repeated = service.create("exp-1", "command-1")
    second = service.create("exp-1", "command-2")

    assert repeated.reportId == first.reportId
    assert second.reportVersion == 2
    assert len(store.items) == 2
    assert [item.reportVersion for item in service.list("exp-1")] == [2, 1]


def test_markdown_keeps_evidence_type_labels_and_disclaimer():
    service, _ = _service()
    report = service.create("exp-1", "command-1")
    markdown = service.render_markdown(report)

    assert "[事实]" in markdown
    assert "[模型预测]" in markdown
    assert "[研发建议]" in markdown
    assert "[限制条件]" in markdown
    assert report.disclaimer in markdown


def test_review_requires_explicit_human_selection_and_rejects_predictions():
    service, _ = _service()
    report = service.create("exp-1", "command-review")
    statements = [item for section in report.sections for item in section.statements]
    fact = next(item for item in statements if item.kind == "fact")
    prediction = next(item for item in statements if item.kind == "prediction")

    try:
        service.review(
            "exp-1", report.reportId,
            operator="研发负责人", reason="证据与边界已逐条复核",
            approved_statement_ids=[fact.statementId, prediction.statementId],
        )
        assert False, "prediction must never be approved for formal knowledge"
    except ValueError as exc:
        assert "prediction" in str(exc)

    reviewed = service.review(
        "exp-1", report.reportId,
        operator="研发负责人", reason="证据与边界已逐条复核",
        approved_statement_ids=[fact.statementId],
    )
    assert reviewed.status == "reviewed"
    assert reviewed.reviewedBy == "研发负责人"
    assert reviewed.reviewReason == "证据与边界已逐条复核"
    assert reviewed.approvedKnowledgeStatementIds == [fact.statementId]
    assert reviewed.reviewedAt


def test_review_is_one_way_and_unknown_statement_is_rejected():
    service, _ = _service()
    report = service.create("exp-1", "command-review-once")
    try:
        service.review(
            "exp-1", report.reportId, operator="负责人", reason="完成复核",
            approved_statement_ids=["statement-missing"],
        )
        assert False, "unknown statement must be rejected"
    except ValueError as exc:
        assert "unknown" in str(exc)

    reviewed = service.review(
        "exp-1", report.reportId, operator="负责人", reason="完成复核",
        approved_statement_ids=[],
    )
    try:
        service.review(
            "exp-1", reviewed.reportId, operator="其他人", reason="重复复核",
            approved_statement_ids=[],
        )
        assert False, "reviewed report must stay immutable"
    except ValueError as exc:
        assert "already reviewed" in str(exc)
