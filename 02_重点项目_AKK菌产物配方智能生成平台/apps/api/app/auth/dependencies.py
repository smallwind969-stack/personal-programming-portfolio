from __future__ import annotations

import os
from pathlib import Path

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .contracts import AuthIdentity, UserRole
from .service import AuthError, SqliteAuthService


_database_path = Path(os.getenv("AUTH_DB_PATH", "data/runtime/auth.db"))
_database_path.parent.mkdir(parents=True, exist_ok=True)
auth_service = SqliteAuthService(_database_path)
auth_service.seed_user(
    username=os.getenv("BOOTSTRAP_ADMIN_USERNAME", "admin"),
    password=os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "JZQY-Admin-2026!"),
    display_name="菌藻启元管理员",
    tenant_id="tenant-junzao-qiyuan",
    role=UserRole.tenant_admin,
)

bearer = HTTPBearer(auto_error=False)


def current_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> AuthIdentity:
    if credentials is None:
        raise HTTPException(status_code=401, detail="AUTHENTICATION_REQUIRED")
    try:
        return auth_service.resolve_token(credentials.credentials)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=exc.code) from exc


def current_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str:
    if credentials is None:
        raise HTTPException(status_code=401, detail="AUTHENTICATION_REQUIRED")
    return credentials.credentials
