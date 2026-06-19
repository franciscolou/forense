"""Booking endpoints: public flow descriptor, client actions, provider actions."""
from __future__ import annotations

from fastapi import APIRouter, status

from app.api.dependencies import BookingServiceDep, CurrentUser, ProviderUser
from app.schemas.booking import (
    BookingInitiate,
    BookingRead,
    LawyerAssign,
    LawyerOption,
    LawyerSelect,
    PaymentSubmit,
    PublicFlowRead,
    ResolutionInput,
    SlotSelect,
    TriageSubmit,
)

router = APIRouter(tags=["bookings"])


# --- Public -------------------------------------------------------------
@router.get("/providers/{provider_user_id}/booking-flow", response_model=PublicFlowRead)
async def get_booking_flow(provider_user_id: int, service: BookingServiceDep) -> PublicFlowRead:
    """The resolved, ordered steps + questionnaire so the client UI can render
    the flow dynamically."""
    return await service.get_public_flow(provider_user_id)


# --- Listing ------------------------------------------------------------
@router.get("/bookings", response_model=list[BookingRead])
async def my_bookings(current_user: CurrentUser, service: BookingServiceDep) -> list[BookingRead]:
    return await service.list_my_bookings(current_user)


@router.get("/bookings/{booking_id}", response_model=BookingRead)
async def get_booking(
    booking_id: int, current_user: CurrentUser, service: BookingServiceDep
) -> BookingRead:
    return await service.get_booking(current_user, booking_id)


# --- Client: initiate + step actions -----------------------------------
@router.post("/bookings", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
async def initiate_booking(
    payload: BookingInitiate, current_user: CurrentUser, service: BookingServiceDep
) -> BookingRead:
    return await service.initiate(current_user, payload)


@router.post("/bookings/{booking_id}/lawyer", response_model=BookingRead)
async def select_lawyer(
    booking_id: int,
    payload: LawyerSelect,
    current_user: CurrentUser,
    service: BookingServiceDep,
) -> BookingRead:
    return await service.select_lawyer(current_user, booking_id, payload.lawyer_user_id)


@router.post("/bookings/{booking_id}/triage", response_model=BookingRead)
async def submit_triage(
    booking_id: int,
    payload: TriageSubmit,
    current_user: CurrentUser,
    service: BookingServiceDep,
) -> BookingRead:
    return await service.submit_triage(current_user, booking_id, payload)


@router.post("/bookings/{booking_id}/slot", response_model=BookingRead)
async def select_slot(
    booking_id: int,
    payload: SlotSelect,
    current_user: CurrentUser,
    service: BookingServiceDep,
) -> BookingRead:
    return await service.select_slot(current_user, booking_id, payload.start_at)


@router.post("/bookings/{booking_id}/payment", response_model=BookingRead)
async def submit_payment(
    booking_id: int,
    _payload: PaymentSubmit,
    current_user: CurrentUser,
    service: BookingServiceDep,
) -> BookingRead:
    return await service.submit_payment(current_user, booking_id)


# --- Provider actions ---------------------------------------------------
@router.get("/me/firm/lawyers", response_model=list[LawyerOption])
async def my_firm_lawyers(
    provider: ProviderUser, service: BookingServiceDep
) -> list[LawyerOption]:
    """Member lawyers the firm can assign to a booking."""
    return await service.list_my_lawyers(provider)


@router.post("/bookings/{booking_id}/assign-lawyer", response_model=BookingRead)
async def assign_lawyer(
    booking_id: int,
    payload: LawyerAssign,
    current_user: CurrentUser,
    service: BookingServiceDep,
) -> BookingRead:
    return await service.assign_lawyer(current_user, booking_id, payload.lawyer_user_id)


@router.post("/bookings/{booking_id}/approve", response_model=BookingRead)
async def approve_booking(
    booking_id: int, current_user: CurrentUser, service: BookingServiceDep
) -> BookingRead:
    return await service.approve(current_user, booking_id)


@router.post("/bookings/{booking_id}/reject", response_model=BookingRead)
async def reject_booking(
    booking_id: int,
    payload: ResolutionInput,
    current_user: CurrentUser,
    service: BookingServiceDep,
) -> BookingRead:
    return await service.reject(current_user, booking_id, payload.reason)


@router.post("/bookings/{booking_id}/complete", response_model=BookingRead)
async def complete_booking(
    booking_id: int, current_user: CurrentUser, service: BookingServiceDep
) -> BookingRead:
    return await service.complete(current_user, booking_id)


# --- Either party -------------------------------------------------------
@router.post("/bookings/{booking_id}/cancel", response_model=BookingRead)
async def cancel_booking(
    booking_id: int,
    payload: ResolutionInput,
    current_user: CurrentUser,
    service: BookingServiceDep,
) -> BookingRead:
    return await service.cancel(current_user, booking_id, payload.reason)
