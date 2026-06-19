from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.booking_configuration import BookingConfiguration
from app.repositories.base import BaseRepository


class BookingConfigurationRepository(BaseRepository[BookingConfiguration]):
    model = BookingConfiguration

    async def get_by_user(self, user_id: int) -> BookingConfiguration | None:
        result = await self.session.execute(
            select(BookingConfiguration)
            .where(BookingConfiguration.user_id == user_id)
            .options(selectinload(BookingConfiguration.questions))
        )
        return result.scalar_one_or_none()
