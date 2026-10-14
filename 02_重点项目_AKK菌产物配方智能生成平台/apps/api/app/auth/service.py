from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from pathlib import Path
import secrets
import sqlite3
import uuid

from .contracts import AuthIdentity, AuthSession, UserRole


class AuthError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class SqliteAuthService:
    _CONFIRM_ROLES = {
        UserRole.platform_admin,
        UserRole.tenant_admin,
        UserRole.approver,
    }

    def __init__(
        self,
        path: str | Path,
        *,
        session_hours: int = 12,
        max_failed_attempts: int = 5,
    ) -> None:
        self.path = str(path)
        self.session_hours = session_hours
        self.max_failed_attempts = max_failed_attempts
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._initialize()

    def seed_user(
        self,
        *,
        username: str,
        password: str,
        display_name: str,
        tenant_id: str | None,
        role: UserRole,
    ) -> AuthIdentity:
        user_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"jzqy:{tenant_id}:{username}"))
        salt = secrets.token_bytes(16)
        password_hash = self._password_hash(password, salt)
        self._connection.execute(
            """
            INSERT INTO auth_users (
                user_id, username, display_name, tenant_id, role, password_hash,
                salt_hex, enabled, failed_attempts, locked
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0, 0)
            ON CONFLICT(username) DO NOTHING
            """,
            (
                user_id,
                username,
                display_name,
                tenant_id,
                role.value,
                password_hash,
                salt.hex(),
            ),
        )
        self._connection.commit()
        row = self._user_by_username(username)
        return self._identity(row)

    def login(self, username: str, password: str) -> AuthSession:
        row = self._user_by_username(username)
        if row is None or not row["enabled"]:
            raise AuthError("INVALID_CREDENTIALS", "账号或密码错误。")
        if row["locked"]:
            raise AuthError("ACCOUNT_LOCKED", "账号已锁定。")
        actual = self._password_hash(password, bytes.fromhex(row["salt_hex"]))
        if not hmac.compare_digest(actual, row["password_hash"]):
            failed_attempts = int(row["failed_attempts"]) + 1
            locked = failed_attempts >= self.max_failed_attempts
            self._connection.execute(
                "UPDATE auth_users SET failed_attempts = ?, locked = ? WHERE user_id = ?",
                (failed_attempts, int(locked), row["user_id"]),
            )
            self._connection.commit()
            if locked:
                raise AuthError("ACCOUNT_LOCKED", "登录失败次数过多，账号已锁定。")
            raise AuthError("INVALID_CREDENTIALS", "账号或密码错误。")

        self._connection.execute(
            "UPDATE auth_users SET failed_attempts = 0 WHERE user_id = ?",
            (row["user_id"],),
        )
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=self.session_hours)
        self._connection.execute(
            "INSERT INTO auth_sessions (token_hash, user_id, expires_at, revoked) VALUES (?, ?, ?, 0)",
            (self._token_hash(token), row["user_id"], expires_at.isoformat()),
        )
        self._connection.commit()
        return AuthSession(
            accessToken=token,
            expiresAt=expires_at.isoformat(),
            identity=self._identity(row),
        )

    def resolve_token(self, token: str) -> AuthIdentity:
        row = self._connection.execute(
            """
            SELECT u.* FROM auth_sessions s
            JOIN auth_users u ON u.user_id = s.user_id
            WHERE s.token_hash = ? AND s.revoked = 0 AND u.enabled = 1
            """,
            (self._token_hash(token),),
        ).fetchone()
        if row is None:
            raise AuthError("AUTHENTICATION_REQUIRED", "访问令牌无效。")
        session = self._connection.execute(
            "SELECT expires_at FROM auth_sessions WHERE token_hash = ?",
            (self._token_hash(token),),
        ).fetchone()
        if datetime.fromisoformat(session["expires_at"]) <= datetime.now(timezone.utc):
            raise AuthError("AUTHENTICATION_REQUIRED", "访问令牌已过期。")
        return self._identity(row)

    def logout(self, token: str) -> None:
        self._connection.execute(
            "UPDATE auth_sessions SET revoked = 1 WHERE token_hash = ?",
            (self._token_hash(token),),
        )
        self._connection.commit()

    def assert_tenant_access(self, identity: AuthIdentity, tenant_id: str) -> None:
        if identity.role == UserRole.platform_admin:
            return
        if identity.tenantId != tenant_id:
            raise AuthError("TENANT_ACCESS_DENIED", "无权访问该企业资源。")

    def require_confirmation_permission(self, identity: AuthIdentity) -> None:
        if identity.role not in self._CONFIRM_ROLES:
            raise AuthError("CONFIRMATION_FORBIDDEN", "当前角色没有方案确认权限。")

    def _initialize(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS auth_users (
                user_id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                tenant_id TEXT,
                role TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                salt_hex TEXT NOT NULL,
                enabled INTEGER NOT NULL,
                failed_attempts INTEGER NOT NULL,
                locked INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS auth_sessions (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES auth_users(user_id)
            );
            """
        )
        self._connection.commit()

    def _user_by_username(self, username: str):
        return self._connection.execute(
            "SELECT * FROM auth_users WHERE username = ?", (username,)
        ).fetchone()

    @staticmethod
    def _password_hash(password: str, salt: bytes) -> str:
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, 310_000
        ).hex()

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _identity(row) -> AuthIdentity:
        return AuthIdentity(
            userId=row["user_id"],
            username=row["username"],
            displayName=row["display_name"],
            tenantId=row["tenant_id"],
            role=UserRole(row["role"]),
        )
