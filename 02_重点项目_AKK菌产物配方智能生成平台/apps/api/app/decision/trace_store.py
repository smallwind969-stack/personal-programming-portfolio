from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.auth.contracts import AuthIdentity
from app.auth.service import AuthError, SqliteAuthService


class ConfirmationRecord(BaseModel):
    planId: str
    approverUserId: str
    approverName: str
    tenantId: str
    note: str | None = None
    confirmedAt: str


class DecisionTrace(BaseModel):
    runId: str
    tenantId: str
    userId: str
    rawRequirement: str
    requirement: dict[str, Any]
    supplementalConstraints: dict[str, Any] = Field(default_factory=dict)
    knowledgeVersion: str
    knowledgeIds: list[str]
    dataVersions: list[str] = Field(default_factory=list)
    modelVersions: dict[str, str]
    search: dict[str, Any]
    plans: list[dict[str, Any]]
    risks: list[str] = Field(default_factory=list)
    applicability: list[str] = Field(default_factory=list)
    generatedAt: str
    replayOfRunId: str | None = None
    confirmationStatus: Literal["pending", "confirmed"] = "pending"
    confirmation: ConfirmationRecord | None = None


class SqliteDecisionTraceStore:
    def __init__(
        self, path: str | Path, auth_service: SqliteAuthService
    ) -> None:
        self.auth_service = auth_service
        self._connection = sqlite3.connect(str(path), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS decision_traces (
                run_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def create(
        self, identity: AuthIdentity, trace: DecisionTrace
    ) -> DecisionTrace:
        self.auth_service.assert_tenant_access(identity, trace.tenantId)
        if identity.userId != trace.userId:
            raise AuthError("TENANT_ACCESS_DENIED", "运行发起人与当前身份不一致。")
        self._connection.execute(
            "INSERT INTO decision_traces (run_id, tenant_id, generated_at, payload_json) VALUES (?, ?, ?, ?)",
            (
                trace.runId,
                trace.tenantId,
                trace.generatedAt,
                json.dumps(trace.model_dump(mode="json"), ensure_ascii=False, sort_keys=True),
            ),
        )
        self._connection.commit()
        return trace

    def get(self, run_id: str, identity: AuthIdentity) -> DecisionTrace:
        row = self._connection.execute(
            "SELECT tenant_id, payload_json FROM decision_traces WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            raise LookupError("decision run not found")
        self.auth_service.assert_tenant_access(identity, row["tenant_id"])
        return DecisionTrace.model_validate_json(row["payload_json"])

    def list_for_identity(
        self, identity: AuthIdentity, limit: int = 50
    ) -> list[DecisionTrace]:
        if identity.tenantId is None:
            rows = self._connection.execute(
                "SELECT payload_json FROM decision_traces ORDER BY generated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = self._connection.execute(
                "SELECT payload_json FROM decision_traces WHERE tenant_id = ? ORDER BY generated_at DESC LIMIT ?",
                (identity.tenantId, limit),
            ).fetchall()
        return [
            DecisionTrace.model_validate_json(row["payload_json"]) for row in rows
        ]

    def confirm(
        self,
        run_id: str,
        identity: AuthIdentity,
        plan_id: str,
        note: str | None = None,
    ) -> DecisionTrace:
        trace = self.get(run_id, identity)
        self.auth_service.require_confirmation_permission(identity)
        if not any(plan.get("planId") == plan_id for plan in trace.plans):
            raise ValueError("selected plan does not belong to this decision run")
        trace.confirmationStatus = "confirmed"
        trace.confirmation = ConfirmationRecord(
            planId=plan_id,
            approverUserId=identity.userId,
            approverName=identity.displayName,
            tenantId=trace.tenantId,
            note=note,
            confirmedAt=datetime.now(timezone.utc).isoformat(),
        )
        self._connection.execute(
            "UPDATE decision_traces SET payload_json = ? WHERE run_id = ?",
            (
                json.dumps(trace.model_dump(mode="json"), ensure_ascii=False, sort_keys=True),
                run_id,
            ),
        )
        self._connection.commit()
        return trace
