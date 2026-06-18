from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.models.lawyer import Lawyer
from app.models.practice_area import PracticeArea
from app.models.user import User
from app.repositories.base import BaseRepository


class LawyerRepository(BaseRepository[Lawyer]):
    model = Lawyer

    # Eager-loads applied wherever a lawyer is returned to the API so that the
    # read schemas (which touch ``user`` and the collections) never trigger
    # lazy I/O outside the async context.
    _LOADS = (
        selectinload(Lawyer.user),
        selectinload(Lawyer.practice_areas),
        selectinload(Lawyer.educations),
        selectinload(Lawyer.languages),
    )

    async def get_with_relations(self, lawyer_id: int) -> Lawyer | None:
        result = await self.session.execute(
            select(Lawyer).where(Lawyer.id == lawyer_id).options(*self._LOADS)
        )
        return result.scalar_one_or_none()

    async def get_by_oab(self, uf: str, number: str) -> Lawyer | None:
        result = await self.session.execute(
            select(Lawyer).where(Lawyer.oab_uf == uf, Lawyer.oab_number == number)
        )
        return result.scalar_one_or_none()

    async def get_many_by_ids(self, ids: list[int]) -> list[Lawyer]:
        if not ids:
            return []
        result = await self.session.execute(
            select(Lawyer).where(Lawyer.id.in_(ids)).options(*self._LOADS)
        )
        return list(result.scalars().all())

    def _search_stmt(self, *, practice_area_id: int | None, query: str | None):
        stmt = select(Lawyer).join(User, Lawyer.user_id == User.id)
        if practice_area_id is not None:
            stmt = stmt.join(Lawyer.practice_areas).where(
                PracticeArea.id == practice_area_id
            )
        if query:
            like = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(User.full_name.ilike(like), Lawyer.bio.ilike(like), Lawyer.city.ilike(like))
            )
        return stmt

    async def search(
        self,
        *,
        practice_area_id: int | None = None,
        query: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Lawyer], int]:
        """Return a page of lawyers plus the total match count."""
        base = self._search_stmt(practice_area_id=practice_area_id, query=query)

        count_stmt = select(func.count()).select_from(base.distinct().subquery())
        total = int((await self.session.execute(count_stmt)).scalar_one())

        page_stmt = (
            base.options(*self._LOADS)
            .order_by(Lawyer.id)
            .distinct()
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(page_stmt)
        return list(result.scalars().unique().all()), total
