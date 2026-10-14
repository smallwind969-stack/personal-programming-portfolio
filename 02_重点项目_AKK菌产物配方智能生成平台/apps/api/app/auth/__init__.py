"""Authentication and tenant authorization for the decision terminal."""

from .contracts import AuthIdentity, AuthSession, UserRole
from .service import AuthError, SqliteAuthService

__all__ = [
    "AuthError",
    "AuthIdentity",
    "AuthSession",
    "SqliteAuthService",
    "UserRole",
]
