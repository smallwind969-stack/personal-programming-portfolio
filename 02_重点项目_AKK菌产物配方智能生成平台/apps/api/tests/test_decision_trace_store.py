import pytest

from app.auth.contracts import UserRole
from app.auth.service import AuthError, SqliteAuthService
from app.decision.trace_store import DecisionTrace, SqliteDecisionTraceStore


def _identity(auth, username, tenant, role):
    auth.seed_user(
        username=username,
        password="Strong-password-2026!",
        display_name=username,
        tenant_id=tenant,
        role=role,
    )
    return auth.resolve_token(
        auth.login(username, "Strong-password-2026!").accessToken
    )


def test_trace_is_tenant_scoped_and_confirmation_is_audited(tmp_path):
    auth = SqliteAuthService(tmp_path / "auth.db")
    engineer = _identity(
        auth, "engineer-a", "tenant-a", UserRole.experiment_engineer
    )
    approver = _identity(auth, "approver-a", "tenant-a", UserRole.approver)
    outsider = _identity(auth, "admin-b", "tenant-b", UserRole.tenant_admin)
    store = SqliteDecisionTraceStore(tmp_path / "traces.db", auth)
    trace = store.create(
        engineer,
        DecisionTrace(
            runId="run-fixed",
            tenantId="tenant-a",
            userId=engineer.userId,
            rawRequirement="低糖高弹性菌藻果冻",
            requirement={"productType": "功能性果冻"},
            knowledgeVersion="knowledge-v1",
            knowledgeIds=["jelly-evidence"],
            modelVersions={"target_product_output": "model-v1"},
            search={"scoringVersion": "deterministic-grid-v1"},
            plans=[{"planId": "balanced:candidate-0001"}],
            generatedAt="2026-07-25T10:00:00+00:00",
            replayOfRunId="run-original",
        ),
    )
    assert store.get("run-fixed", engineer).runId == trace.runId
    assert store.get("run-fixed", engineer).replayOfRunId == "run-original"

    with pytest.raises(AuthError, match="TENANT_ACCESS_DENIED"):
        store.get("run-fixed", outsider)
    with pytest.raises(AuthError, match="CONFIRMATION_FORBIDDEN"):
        store.confirm(
            "run-fixed", engineer, "balanced:candidate-0001", "工程师无审批权"
        )

    confirmed = store.confirm(
        "run-fixed", approver, "balanced:candidate-0001", "批准进入小试验证"
    )
    assert confirmed.confirmationStatus == "confirmed"
    assert confirmed.confirmation.approverUserId == approver.userId
    assert confirmed.confirmation.tenantId == "tenant-a"
