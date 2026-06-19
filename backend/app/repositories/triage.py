from __future__ import annotations

from sqlalchemy import select

from app.models.triage import TriageQuestion
from app.repositories.base import BaseRepository


class TriageQuestionRepository(BaseRepository[TriageQuestion]):
    model = TriageQuestion

    async def list_for_configuration(
        self, configuration_id: int, *, active_only: bool = False
    ) -> list[TriageQuestion]:
        stmt = select(TriageQuestion).where(
            TriageQuestion.configuration_id == configuration_id
        )
        if active_only:
            stmt = stmt.where(TriageQuestion.is_active.is_(True))
        stmt = stmt.order_by(TriageQuestion.order, TriageQuestion.id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_many_by_ids(self, ids: list[int]) -> list[TriageQuestion]:
        if not ids:
            return []
        result = await self.session.execute(
            select(TriageQuestion).where(TriageQuestion.id.in_(ids))
        )
        return list(result.scalars().all())
