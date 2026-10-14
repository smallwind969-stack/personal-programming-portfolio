from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from app.auth.contracts import AuthIdentity, AuthSession, LoginRequest
from app.auth.dependencies import auth_service, current_identity, current_token
from app.auth.service import AuthError


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthSession)
def login(payload: LoginRequest) -> AuthSession:
    try:
        return auth_service.login(payload.username, payload.password)
    except AuthError as exc:
        status = 423 if exc.code == "ACCOUNT_LOCKED" else 401
        raise HTTPException(status_code=status, detail=exc.code) from exc


@router.post("/logout", status_code=204)
def logout(token: str = Depends(current_token)) -> Response:
    auth_service.logout(token)
    return Response(status_code=204)


@router.get("/me", response_model=AuthIdentity)
def me(identity: AuthIdentity = Depends(current_identity)) -> AuthIdentity:
    return identity
