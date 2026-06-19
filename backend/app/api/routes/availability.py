"""Availability: providers declare a recurring weekly schedule + exception
blocks; clients read the derived open slots."""
from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.dependencies import AvailabilityServiceDep, ProviderUser
from app.schemas.availability import (
    ExceptionInput,
    ExceptionRead,
    OpenSlotRead,
    RulesUpdate,
    ScheduleRead,
)

router = APIRouter(tags=["availability"])


# --- Public -------------------------------------------------------------
@router.get("/providers/{provider_user_id}/slots", response_model=list[OpenSlotRead])
async def list_open_slots(
    provider_user_id: int, service: AvailabilityServiceDep
) -> list[OpenSlotRead]:
    """Derived, bookable one-hour windows for the rolling horizon."""
    slots = await service.open_slots(provider_user_id)
    return [OpenSlotRead(start_at=s.start_at, end_at=s.end_at) for s in slots]


# --- Provider schedule --------------------------------------------------
@router.get("/me/availability", response_model=ScheduleRead)
async def get_my_schedule(
    provider: ProviderUser, service: AvailabilityServiceDep
) -> ScheduleRead:
    rules, exceptions = await service.get_schedule(provider.id)
    return ScheduleRead(rules=rules, exceptions=exceptions)


@router.put("/me/availability/rules", response_model=ScheduleRead)
async def replace_rules(
    payload: RulesUpdate, provider: ProviderUser, service: AvailabilityServiceDep
) -> ScheduleRead:
    await service.replace_rules(provider.id, payload.rules)
    rules, exceptions = await service.get_schedule(provider.id)
    return ScheduleRead(rules=rules, exceptions=exceptions)


@router.post(
    "/me/availability/exceptions",
    response_model=ExceptionRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_exception(
    payload: ExceptionInput, provider: ProviderUser, service: AvailabilityServiceDep
) -> ExceptionRead:
    return await service.add_exception(provider.id, payload)


@router.delete(
    "/me/availability/exceptions/{exception_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_exception(
    exception_id: int, provider: ProviderUser, service: AvailabilityServiceDep
) -> Response:
    await service.delete_exception(provider.id, exception_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
