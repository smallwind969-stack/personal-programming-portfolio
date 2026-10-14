from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ResearchReportStatement(BaseModel):
    statementId: str
    kind: Literal["fact", "prediction", "recommendation", "limitation"]
    title: str
    text: str
    evidenceRefs: list[str] = Field(min_length=1)


class ResearchReportSection(BaseModel):
    sectionKey: str
    title: str
    statements: list[ResearchReportStatement]


class ResearchReport(BaseModel):
    reportId: str
    experimentId: str
    reportVersion: int = Field(ge=1)
    commandId: str
    title: str
    status: Literal["draft", "reviewed"] = "draft"
    inputFingerprint: str
    sourceVersions: dict[str, str]
    sections: list[ResearchReportSection]
    unresolvedItems: list[str]
    generatedBy: str = "ResearchReportAgent"
    generatedAt: str
    reviewedBy: str | None = None
    reviewReason: str | None = None
    reviewedAt: str | None = None
    approvedKnowledgeStatementIds: list[str] = Field(default_factory=list)
    disclaimer: str = "本报告区分已记录事实、模型预测、研发建议和限制条件；模型预测不等于真实实验结果，工艺建议须经人工审核与现实实验验证。"


class ResearchReportCreateRequest(BaseModel):
    commandId: str = Field(min_length=1, max_length=128)


class ResearchReportReviewRequest(BaseModel):
    operator: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=2, max_length=1000)
    approvedStatementIds: list[str] = Field(default_factory=list, max_length=200)
