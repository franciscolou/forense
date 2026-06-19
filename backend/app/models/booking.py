"""The booking / service request entity.

A booking captures a *snapshot* of the provider's four settings at creation time
so that in-flight bookings are unaffected if the provider later changes their
configuration. The flow engine derives the ordered pipeline of steps from this
snapshot; ``current_step`` records where in that pipeline the booking sits and
``status`` records its lifecycle state.
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.booking_configuration import (
    AgendaVisibility,
    ApprovalMode,
    PaymentMode,
    TriageMode,
)
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.availability import AvailabilitySlot
    from app.models.triage import TriageResponse
    from app.models.user import User


class BookingStatus(str, enum.Enum):
    PENDING = "pending"                      # cliente ainda tem etapa a cumprir
    AWAITING_APPROVAL = "awaiting_approval"  # aguardando provider aprovar
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class PaymentState(str, enum.Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    PAID = "paid"


class StepKey(str, enum.Enum):
    """Identifies which pipeline step a booking is currently waiting on.

    Acts as the discriminator that explains *why* a booking is PENDING (e.g.
    waiting on triage vs. slot selection vs. payment).
    """

    TRIAGE = "triage"
    AGENDA = "agenda"
    APPROVAL = "approval"
    PAYMENT = "payment"


class Booking(Base, TimestampMixin):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[BookingStatus] = mapped_column(
        SAEnum(BookingStatus), default=BookingStatus.PENDING, nullable=False, index=True
    )
    current_step: Mapped[StepKey | None] = mapped_column(SAEnum(StepKey), nullable=True)

    # --- Snapshot of the provider configuration at creation time ---------
    triage_mode: Mapped[TriageMode] = mapped_column(SAEnum(TriageMode), nullable=False)
    agenda_visibility: Mapped[AgendaVisibility] = mapped_column(
        SAEnum(AgendaVisibility), nullable=False
    )
    approval_mode: Mapped[ApprovalMode] = mapped_column(SAEnum(ApprovalMode), nullable=False)
    payment_mode: Mapped[PaymentMode] = mapped_column(SAEnum(PaymentMode), nullable=False)

    # --- Outcomes of the steps ------------------------------------------
    slot_id: Mapped[int | None] = mapped_column(
        ForeignKey("availability_slots.id", ondelete="SET NULL"), nullable=True
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_state: Mapped[PaymentState] = mapped_column(
        SAEnum(PaymentState), default=PaymentState.NOT_REQUIRED, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Set when rejected/cancelled, for a human-readable reason.
    resolution_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    provider: Mapped["User"] = relationship(foreign_keys=[provider_user_id])
    client: Mapped["User"] = relationship(foreign_keys=[client_user_id])
    slot: Mapped["AvailabilitySlot | None"] = relationship(back_populates="booking")
    triage_response: Mapped["TriageResponse | None"] = relationship(
        back_populates="booking", cascade="all, delete-orphan", uselist=False
    )
