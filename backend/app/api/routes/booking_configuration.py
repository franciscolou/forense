"""Provider-only endpoints to configure the booking flow and questionnaire."""
from __future__ import annotations

from fastapi import APIRouter, status

from app.api.dependencies import BookingConfigurationServiceDep, ProviderUser
from app.schemas.booking_configuration import (
    BookingConfigurationRead,
    BookingConfigurationUpdate,
)
from app.schemas.triage import TriageQuestionInput

router = APIRouter(prefix="/me/booking-configuration", tags=["booking-configuration"])


@router.get("", response_model=BookingConfigurationRead)
async def get_configuration(
    provider: ProviderUser, service: BookingConfigurationServiceDep
) -> BookingConfigurationRead:
    config = await service.get_or_create(provider.id)
    return BookingConfigurationRead.model_validate(config)


@router.put("", response_model=BookingConfigurationRead)
async def update_configuration(
    payload: BookingConfigurationUpdate,
    provider: ProviderUser,
    service: BookingConfigurationServiceDep,
) -> BookingConfigurationRead:
    config = await service.update(provider.id, payload)
    return BookingConfigurationRead.model_validate(config)


@router.post("/questions", response_model=BookingConfigurationRead, status_code=status.HTTP_201_CREATED)
async def add_question(
    payload: TriageQuestionInput,
    provider: ProviderUser,
    service: BookingConfigurationServiceDep,
) -> BookingConfigurationRead:
    config = await service.add_question(provider.id, payload)
    return BookingConfigurationRead.model_validate(config)


@router.put("/questions/{question_id}", response_model=BookingConfigurationRead)
async def update_question(
    question_id: int,
    payload: TriageQuestionInput,
    provider: ProviderUser,
    service: BookingConfigurationServiceDep,
) -> BookingConfigurationRead:
    config = await service.update_question(provider.id, question_id, payload)
    return BookingConfigurationRead.model_validate(config)


@router.delete("/questions/{question_id}", response_model=BookingConfigurationRead)
async def delete_question(
    question_id: int,
    provider: ProviderUser,
    service: BookingConfigurationServiceDep,
) -> BookingConfigurationRead:
    config = await service.delete_question(provider.id, question_id)
    return BookingConfigurationRead.model_validate(config)
