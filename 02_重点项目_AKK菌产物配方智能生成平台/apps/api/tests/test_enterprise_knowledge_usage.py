from types import SimpleNamespace

from app.enterprise_knowledge.service import EnterpriseKnowledgeService
from app.enterprise_knowledge.usage import EnterpriseKnowledgeUsageService
from app.enterprise_knowledge.contracts import EnterpriseKnowledgeEntry


def _entry(knowledge_id="knowledge-1"):
    return EnterpriseKnowledgeEntry(
        knowledgeId=knowledge_id, experimentId="source-exp", experimentName="来源实验",
        category="verifiedFact", title="稳定区间", content="温度范围稳定",
        evidenceRefs=["dataset://v1"], sourceReportId="report-1", sourceReportVersion=1,
        sourceStatementId="statement-1", sourceInputFingerprint="sha256:input",
        contentHash="sha256:" + "a" * 64, reviewedBy="负责人", reviewReason="核验",
        reviewedAt="2026-07-21T01:00:00+00:00", depositedAt="2026-07-21T01:01:00+00:00",
    )


class Store:
    def __init__(self): self.items = []
    def list(self, record_type, experiment_id=None):
        return [item for item in self.items if item.get("experimentId") == experiment_id or experiment_id is None]
    def save(self, record_type, record_key, experiment_id, payload):
        self.items = [item for item in self.items if item.get("usageId") != record_key]
        self.items.append(payload)


def test_usage_requires_existing_knowledge_and_is_idempotent():
    store = Store()
    knowledge = SimpleNamespace(list=lambda **_: [_entry()])
    service = EnterpriseKnowledgeUsageService(store=store, knowledge_source=knowledge)
    first = service.register(
        "target-exp", knowledge_ids=["knowledge-1"], purpose="modeling",
        target_version="dataset-snapshot-v4", operator="建模负责人", note="作为特征解释边界",
    )
    repeated = service.register(
        "target-exp", knowledge_ids=["knowledge-1"], purpose="modeling",
        target_version="dataset-snapshot-v4", operator="建模负责人", note="作为特征解释边界",
    )
    assert first.usageId == repeated.usageId
    assert len(service.list(experiment_id="target-exp")) == 1
    assert first.knowledgeIds == ["knowledge-1"]
    assert first.sourceEntries[0].contentHash.endswith("a" * 64)

    try:
        service.register("target-exp", knowledge_ids=["missing"], purpose="simulation", target_version="run-v1", operator="负责人", note="缺失")
        assert False, "missing knowledge must be rejected"
    except ValueError as exc:
        assert "not found" in str(exc)


def test_usage_rejects_empty_selection():
    service = EnterpriseKnowledgeUsageService(store=Store(), knowledge_source=SimpleNamespace(list=lambda **_: [_entry()]))
    try:
        service.register("target-exp", knowledge_ids=[], purpose="optimization", target_version="plan-v1", operator="负责人", note="没有条目")
        assert False
    except ValueError as exc:
        assert "at least one" in str(exc)
