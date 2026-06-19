from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.booking import BookingStatus, PaymentState, StepKey
from app.models.booking_configuration import (
    AgendaVisibility,
    ApprovalMode,
    PaymentMode,
    TriageMode,
)
from app.schemas.availability import SlotRead
from app.schemas.triage import TriageAnswerInput, TriageQuestionRead, TriageResponseRead


class ConfigSnapshot(BaseModel):
    triage_mode: TriageMode
    agenda_visibility: AgendaVisibility
    approval_mode: ApprovalMode
    payment_mode: PaymentMode


class StepDescriptor(BaseModel):
    key: str
    actor: str
    action: str
    label: str
    required: bool | None = None
    after_confirmation: bool | None = None


class PublicFlowRead(BaseModel):
    """What a client needs to render a provider's booking flow dynamically."""

    provider_user_id: int
    provider_name: str
    config: ConfigSnapshot
    steps: list[StepDescriptor]
    questions: list[TriageQuestionRead]


# --- Action payloads ----------------------------------------------------
class BookingInitiate(BaseModel):
    provider_user_id: int
    notes: str | None = None


class TriageSubmit(BaseModel):
    answers: list[TriageAnswerInput] = Field(default_factory=list)


class SlotSelect(BaseModel):
    # The client picks a derived availability window by its start time; the slot
    # row is materialised on booking.
    start_at: datetime


class PaymentSubmit(BaseModel):
    # Placeholder — payment is only modelled, not integrated.
    pass


class ResolutionInput(BaseModel):
    reason: str | None = None


# --- Read ---------------------------------------------------------------
class PartyRead(BaseModel):
    id: int
    full_name: str


class BookingRead(BaseModel):
    id: int
    status: BookingStatus
    current_step: StepKey | None
    pending_action: StepDescriptor | None
    config: ConfigSnapshot
    provider: PartyRead
    client: PartyRead
    slot: SlotRead | None
    scheduled_at: datetime | None
    payment_state: PaymentState
    notes: str | None
    resolution_reason: str | None
    triage_response: TriageResponseRead | None
    created_at: datetime
