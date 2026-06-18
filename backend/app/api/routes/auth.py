from __future__ import annotations

from fastapi import APIRouter

from app.api.dependencies import AuthServiceDep, CurrentUser
from app.schemas.auth import AuthResponse, LoginRequest, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, auth_service: AuthServiceDep) -> AuthResponse:
    return await auth_service.login(payload.email, payload.password)


@router.get("/me", response_model=UserRead)
async def me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)
