from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select

from app.models.availability import (
    AvailabilityException,
    AvailabilityRule,
    AvailabilitySlot,
)
from app.repositories.base import BaseRepository


class AvailabilityRuleRepository(BaseRepository[AvailabilityRule]):
    model = AvailabilityRule

    async def list_for_provider(self, provider_user_id: int) -> list[AvailabilityRule]:
        result = await self.session.execute(
            select(AvailabilityRule)
            .where(AvailabilityRule.provider_user_id == provider_user_id)
            .order_by(AvailabilityRule.weekday, AvailabilityRule.start_hour)
        )
        return list(result.scalars().all())

    async def delete_for_provider(self, provider_user_id: int) -> None:
        """Wipe a provider's recurring rules (the weekly grid is replace-all)."""
        await self.session.execute(
            delete(AvailabilityRule).where(
                AvailabilityRule.provider_user_id == provider_user_id
            )
        )


class AvailabilityExceptionRepository(BaseRepository[AvailabilityException]):
    model = AvailabilityException

    async def list_for_provider(
        self, provider_user_id: int, *, upcoming_only: bool = False
    ) -> list[AvailabilityException]:
        stmt = select(AvailabilityException).where(
            AvailabilityException.provider_user_id == provider_user_id
        )
        if upcoming_only:
            stmt = stmt.where(AvailabilityException.end_at >= datetime.now(timezone.utc))
        stmt = stmt.order_by(AvailabilityException.start_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class AvailabilityRepository(BaseRepository[AvailabilitySlot]):
    model = AvailabilitySlot

    async def booked_starts(
        self, provider_user_id: int, since: datetime
    ) -> set[datetime]:
        """Start times already taken by a materialised (booked) slot."""
        result = await self.session.execute(
            select(AvailabilitySlot.start_at).where(
                AvailabilitySlot.provider_user_id == provider_user_id,
                AvailabilitySlot.is_booked.is_(True),
                AvailabilitySlot.start_at >= since,
            )
        )
        return set(result.scalars().all())

    async def get_booked_at(
        self, provider_user_id: int, start_at: datetime
    ) -> AvailabilitySlot | None:
        result = await self.session.execute(
            select(AvailabilitySlot).where(
                AvailabilitySlot.provider_user_id == provider_user_id,
                AvailabilitySlot.start_at == start_at,
                AvailabilitySlot.is_booked.is_(True),
            )
        )
        return result.scalar_one_or_none()
