from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.models.firm import Firm
from app.models.lawyer import Lawyer
from app.models.practice_area import PracticeArea
from app.repositories.base import BaseRepository


class FirmRepository(BaseRepository[Firm]):
    model = Firm

    _LOADS = (
        selectinload(Firm.user),
        selectinload(Firm.practice_areas),
        selectinload(Firm.lawyers).selectinload(Lawyer.user),
        selectinload(Firm.lawyers).selectinload(Lawyer.practice_areas),
    )

    async def get_with_relations(self, firm_id: int) -> Firm | None:
        result = await self.session.execute(
            select(Firm).where(Firm.id == firm_id).options(*self._LOADS)
        )
        return result.scalar_one_or_none()

    async def get_by_cnpj(self, cnpj: str) -> Firm | None:
        result = await self.session.execute(select(Firm).where(Firm.cnpj == cnpj))
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: int) -> Firm | None:
        """Resolve a firm from its account ``user_id``, with member lawyers (and
        their users) eager-loaded — used to list/validate selectable lawyers."""
        result = await self.session.execute(
            select(Firm)
            .where(Firm.user_id == user_id)
            .options(
                selectinload(Firm.lawyers).selectinload(Lawyer.user),
            )
        )
        return result.scalar_one_or_none()

    def _search_stmt(self, *, practice_area_id: int | None, query: str | None):
        stmt = select(Firm)
        if practice_area_id is not None:
            stmt = stmt.join(Firm.practice_areas).where(PracticeArea.id == practice_area_id)
        if query:
            like = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(Firm.legal_name.ilike(like), Firm.description.ilike(like), Firm.city.ilike(like))
            )
        return stmt

    async def search(
        self,
        *,
        practice_area_id: int | None = None,
        query: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Firm], int]:
        base = self._search_stmt(practice_area_id=practice_area_id, query=query)

        count_stmt = select(func.count()).select_from(base.distinct().subquery())
        total = int((await self.session.execute(count_stmt)).scalar_one())

        page_stmt = (
            base.options(*self._LOADS).order_by(Firm.id).distinct().limit(limit).offset(offset)
        )
        result = await self.session.execute(page_stmt)
        return list(result.scalars().unique().all()), total
