from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.booking import Booking
from app.models.triage import TriageResponse
from app.repositories.base import BaseRepository


class BookingRepository(BaseRepository[Booking]):
    model = Booking

    _LOADS = (
        selectinload(Booking.provider),
        selectinload(Booking.client),
        selectinload(Booking.slot),
        selectinload(Booking.triage_response).selectinload(TriageResponse.answers),
    )

    async def get_with_relations(self, booking_id: int) -> Booking | None:
        result = await self.session.execute(
            select(Booking).where(Booking.id == booking_id).options(*self._LOADS)
        )
        return result.scalar_one_or_none()

    async def list_for_client(self, client_user_id: int) -> list[Booking]:
        result = await self.session.execute(
            select(Booking)
            .where(Booking.client_user_id == client_user_id)
            .options(*self._LOADS)
            .order_by(Booking.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_for_provider(self, provider_user_id: int) -> list[Booking]:
        result = await self.session.execute(
            select(Booking)
            .where(Booking.provider_user_id == provider_user_id)
            .options(*self._LOADS)
            .order_by(Booking.created_at.desc())
        )
        return list(result.scalars().all())
