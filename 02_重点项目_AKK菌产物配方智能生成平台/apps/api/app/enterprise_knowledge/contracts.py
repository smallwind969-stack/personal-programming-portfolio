from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class EnterpriseKnowledgeEntry(BaseModel):
    knowledgeId: str
    experimentId: str
    experimentName: str
    category: Literal["verifiedFact", "applicabilityBoundary", "validationPlan"]
    title: str
    content: str
    evidenceRefs: list[str] = Field(min_length=1)
    sourceReportId: str
    sourceReportVersion: int = Field(ge=1)
    sourceStatementId: str
    sourceInputFingerprint: str
    contentHash: str
    reviewedBy: str
    reviewReason: str
    reviewedAt: str
    depositedAt: str
    status: Literal["active"] = "active"


class EnterpriseKnowledgeDepositResult(BaseModel):
    reportId: str
    createdCount: int
    reusedCount: int
    entries: list[EnterpriseKnowledgeEntry]
