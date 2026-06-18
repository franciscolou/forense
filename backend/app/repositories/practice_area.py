from __future__ import annotations

from sqlalchemy import select

from app.models.practice_area import PracticeArea
from app.repositories.base import BaseRepository


class PracticeAreaRepository(BaseRepository[PracticeArea]):
    model = PracticeArea

    async def get_by_ids(self, ids: list[int]) -> list[PracticeArea]:
        if not ids:
            return []
        result = await self.session.execute(
            select(PracticeArea).where(PracticeArea.id.in_(ids))
        )
        return list(result.scalars().all())

    async def get_by_slug(self, slug: str) -> PracticeArea | None:
        result = await self.session.execute(
            select(PracticeArea).where(PracticeArea.slug == slug)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[PracticeArea]:
        result = await self.session.execute(
            select(PracticeArea).order_by(PracticeArea.name)
        )
        return list(result.scalars().all())
