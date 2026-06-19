from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.booking import BookingStatus, PaymentState, StepKey
from app.models.booking_configuration import (
    AgendaVisibility,
    ApprovalMode,
    LawyerSelectionMode,
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
    lawyer_selection_mode: LawyerSelectionMode


class LawyerOption(BaseModel):
    """A firm member offered to the client in the lawyer-selection step, or shown
    as the responsible lawyer in the firm's bookings calendar."""

    user_id: int
    full_name: str
    photo_url: str | None = None


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
    # Firm members the client can pick from when the lawyer-selection step is
    # present; empty for non-firm providers.
    lawyers: list[LawyerOption] = Field(default_factory=list)


# --- Action payloads ----------------------------------------------------
class BookingInitiate(BaseModel):
    provider_user_id: int
    notes: str | None = None


class TriageSubmit(BaseModel):
    answers: list[TriageAnswerInput] = Field(default_factory=list)


class LawyerSelect(BaseModel):
    # The client picks a firm member by their user id. ``None`` defers the choice
    # to the firm (only allowed in HYBRID mode).
    lawyer_user_id: int | None = None


class LawyerAssign(BaseModel):
    # The firm assigns the responsible lawyer to a booking.
    lawyer_user_id: int


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
    email: str | None = None
    # Populated for the client party (from their Client profile) so the provider
    # can see who booked; absent for the provider party.
    phone: str | None = None
    city: str | None = None
    state: str | None = None


class BookingRead(BaseModel):
    id: int
    status: BookingStatus
    current_step: StepKey | None
    pending_action: StepDescriptor | None
    config: ConfigSnapshot
    provider: PartyRead
    client: PartyRead
    # The responsible lawyer, when one has been chosen/assigned.
    lawyer: PartyRead | None = None
    lawyer_user_id: int | None = None
    # Whose availability the agenda runs against (lawyer if chosen, else provider).
    scheduling_user_id: int
    slot: SlotRead | None
    scheduled_at: datetime | None
    payment_state: PaymentState
    notes: str | None
    resolution_reason: str | None
    triage_response: TriageResponseRead | None
    created_at: datetime
