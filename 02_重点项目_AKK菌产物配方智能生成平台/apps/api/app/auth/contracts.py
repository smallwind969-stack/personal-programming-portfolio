from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class UserRole(str, Enum):
    platform_admin = "platform_admin"
    tenant_admin = "tenant_admin"
    experiment_engineer = "experiment_engineer"
    approver = "approver"
    viewer = "viewer"


class AuthIdentity(BaseModel):
    userId: str
    username: str
    displayName: str
    tenantId: str | None
    role: UserRole


class AuthSession(BaseModel):
    accessToken: str
    tokenType: str = "bearer"
    expiresAt: str
    identity: AuthIdentity


class LoginRequest(BaseModel):
    username: str
    password: str
