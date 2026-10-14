from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json

from app.enterprise_knowledge.contracts import EnterpriseKnowledgeEntry


class EnterpriseKnowledgeService:
    RECORD_TYPE = "enterprise_knowledge_entry"
    CATEGORY_MAP = {
        "fact": "verifiedFact",
        "limitation": "applicabilityBoundary",
        "recommendation": "validationPlan",
    }

    def __init__(self, *, store, report_source, workspace_source) -> None:
        self.store = store
        self.reportSource = report_source
        self.workspaceSource = workspace_source

    def deposit(self, experiment_id: str, report_id: str) -> list[EnterpriseKnowledgeEntry]:
        report = self.reportSource.get(experiment_id, report_id)
        if report.status != "reviewed":
            raise ValueError("research report must be reviewed before knowledge deposit")
        approved = set(report.approvedKnowledgeStatementIds)
        workspace = self.workspaceSource.get_workspace_overview(experiment_id)
        experiment_name = getattr(workspace, "name", experiment_id) if workspace else experiment_id
        existing = {
            (item.sourceReportId, item.sourceStatementId): item
            for item in self.list(experiment_id=experiment_id)
        }
        result: list[EnterpriseKnowledgeEntry] = []
        for section in report.sections:
            for statement in section.statements:
                if statement.statementId not in approved or statement.kind == "prediction":
                    continue
                category = self.CATEGORY_MAP.get(statement.kind)
                if category is None:
                    continue
                key = (report.reportId, statement.statementId)
                if key in existing:
                    result.append(existing[key])
                    continue
                source_payload = {
                    "reportId": report.reportId,
                    "reportVersion": report.reportVersion,
                    "statementId": statement.statementId,
                    "kind": statement.kind,
                    "title": statement.title,
                    "content": statement.text,
                    "evidenceRefs": statement.evidenceRefs,
                }
                content_hash = "sha256:" + sha256(
                    json.dumps(source_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest()
                knowledge_id = f"knowledge-{content_hash.removeprefix('sha256:')[:16]}"
                entry = EnterpriseKnowledgeEntry(
                    knowledgeId=knowledge_id,
                    experimentId=experiment_id,
                    experimentName=experiment_name,
                    category=category,
                    title=statement.title,
                    content=statement.text,
                    evidenceRefs=statement.evidenceRefs,
                    sourceReportId=report.reportId,
                    sourceReportVersion=report.reportVersion,
                    sourceStatementId=statement.statementId,
                    sourceInputFingerprint=report.inputFingerprint,
                    contentHash=content_hash,
                    reviewedBy=report.reviewedBy or "unknown",
                    reviewReason=report.reviewReason or "",
                    reviewedAt=report.reviewedAt or report.generatedAt,
                    depositedAt=datetime.now(timezone.utc).isoformat(),
                )
                self.store.save(self.RECORD_TYPE, entry.knowledgeId, experiment_id, entry.model_dump(mode="json"))
                existing[key] = entry
                result.append(entry)
        return result

    def list(self, *, experiment_id: str | None = None) -> list[EnterpriseKnowledgeEntry]:
        entries = [
            EnterpriseKnowledgeEntry.model_validate(item)
            for item in self.store.list(self.RECORD_TYPE, experiment_id)
        ]
        entries.sort(key=lambda item: item.depositedAt, reverse=True)
        return entries
