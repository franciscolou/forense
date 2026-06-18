from __future__ import annotations

from fastapi import APIRouter, status

from app.api.dependencies import RegistrationServiceDep
from app.schemas.auth import AuthResponse
from app.schemas.client import ClientRegisterRequest
from app.schemas.firm import FirmRegisterRequest
from app.schemas.lawyer import LawyerRegisterRequest

router = APIRouter(prefix="/register", tags=["registration"])


@router.post("/client", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_client(
    payload: ClientRegisterRequest, service: RegistrationServiceDep
) -> AuthResponse:
    return await service.register_client(payload)


@router.post("/lawyer", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_lawyer(
    payload: LawyerRegisterRequest, service: RegistrationServiceDep
) -> AuthResponse:
    return await service.register_lawyer(payload)


@router.post("/firm", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register_firm(
    payload: FirmRegisterRequest, service: RegistrationServiceDep
) -> AuthResponse:
    return await service.register_firm(payload)
