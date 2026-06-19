"""Provider availability.

Availability is expressed declaratively, not slot-by-slot:

* :class:`AvailabilityRule` — a *recurring weekly* window (e.g. "every Tuesday
  09:00–18:00"). This is how a provider covers weeks/months in a few clicks.
* :class:`AvailabilityException` — a concrete interval that is *blocked* (a
  holiday, a vacation, a busy afternoon), subtracted from the recurring rules.

Concrete bookable slots are **derived** from rules minus exceptions minus
already-booked times (see ``AvailabilityService``); an :class:`AvailabilitySlot`
row is materialised only when a client actually books one. Granularity is one
hour.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.user import User


class AvailabilityRule(Base, TimestampMixin):
    """A recurring weekly availability window, at hour granularity.

    ``weekday`` follows ``datetime.weekday()`` (Monday=0 … Sunday=6). The window
    spans ``[start_hour, end_hour)`` and is expanded into one-hour slots.
    """

    __tablename__ = "availability_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Mon … 6=Sun
    start_hour: Mapped[int] = mapped_column(Integer, nullable=False)  # 0–23
    end_hour: Mapped[int] = mapped_column(Integer, nullable=False)  # 1–24, exclusive

    provider: Mapped["User"] = relationship()


class AvailabilityException(Base, TimestampMixin):
    """A concrete interval during which the provider is unavailable."""

    __tablename__ = "availability_exceptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)

    provider: Mapped["User"] = relationship()


class AvailabilitySlot(Base, TimestampMixin):
    """A concrete one-hour slot.

    Materialised on demand when a client books a derived availability window, so
    every row here is (or was) an actual reservation referenced by a booking.
    """

    __tablename__ = "availability_slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_booked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    provider: Mapped["User"] = relationship()
    booking: Mapped["Booking | None"] = relationship(back_populates="slot", uselist=False)
