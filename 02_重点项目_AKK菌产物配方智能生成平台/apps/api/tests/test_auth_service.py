import sqlite3

import pytest

from app.auth.contracts import UserRole
from app.auth.service import AuthError, SqliteAuthService


def test_password_is_hashed_and_login_resolves_server_owned_identity(tmp_path):
    database = tmp_path / "auth.db"
    service = SqliteAuthService(database)
    service.seed_user(
        username="admin",
        password="Competition-2026!",
        display_name="系统管理员",
        tenant_id="tenant-alpha",
        role=UserRole.tenant_admin,
    )

    row = sqlite3.connect(database).execute(
        "SELECT password_hash FROM auth_users WHERE username = ?", ("admin",)
    ).fetchone()
    assert row is not None
    assert "Competition-2026!" not in row[0]

    session = service.login("admin", "Competition-2026!")
    identity = service.resolve_token(session.accessToken)
    assert identity.tenantId == "tenant-alpha"
    assert identity.role == UserRole.tenant_admin


def test_disabled_account_and_repeated_failures_are_rejected(tmp_path):
    service = SqliteAuthService(tmp_path / "auth.db", max_failed_attempts=2)
    service.seed_user(
        username="engineer",
        password="correct-password",
        display_name="研发工程师",
        tenant_id="tenant-alpha",
        role=UserRole.experiment_engineer,
    )

    with pytest.raises(AuthError, match="INVALID_CREDENTIALS"):
        service.login("engineer", "wrong")
    with pytest.raises(AuthError, match="ACCOUNT_LOCKED"):
        service.login("engineer", "wrong-again")
    with pytest.raises(AuthError, match="ACCOUNT_LOCKED"):
        service.login("engineer", "correct-password")


def test_tenant_and_confirmation_permissions_are_enforced(tmp_path):
    service = SqliteAuthService(tmp_path / "auth.db")
    service.seed_user(
        username="engineer",
        password="correct-password",
        display_name="研发工程师",
        tenant_id="tenant-alpha",
        role=UserRole.experiment_engineer,
    )
    identity = service.resolve_token(
        service.login("engineer", "correct-password").accessToken
    )

    with pytest.raises(AuthError, match="TENANT_ACCESS_DENIED"):
        service.assert_tenant_access(identity, "tenant-beta")
    with pytest.raises(AuthError, match="CONFIRMATION_FORBIDDEN"):
        service.require_confirmation_permission(identity)
