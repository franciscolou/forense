"""Directory / search use-cases — the client-facing read side.

This powers the client view: browsing and filtering lawyers and firms by area of
practice (or free-text), and viewing individual profiles.
"""
from __future__ import annotations

from app.core.exceptions import NotFoundError
from app.repositories.firm import FirmRepository
from app.repositories.lawyer import LawyerRepository
from app.repositories.practice_area import PracticeAreaRepository
from app.schemas.common import Page
from app.schemas.firm import FirmRead, FirmSummary
from app.schemas.lawyer import LawyerRead, LawyerSummary
from app.schemas.practice_area import PracticeAreaRead


class DirectoryService:
    def __init__(
        self,
        lawyers: LawyerRepository,
        firms: FirmRepository,
        practice_areas: PracticeAreaRepository,
    ) -> None:
        self._lawyers = lawyers
        self._firms = firms
        self._practice_areas = practice_areas

    async def list_practice_areas(self) -> list[PracticeAreaRead]:
        areas = await self._practice_areas.list_all()
        return [PracticeAreaRead.model_validate(a) for a in areas]

    async def search_lawyers(
        self,
        *,
        practice_area_id: int | None,
        query: str | None,
        page: int,
        page_size: int,
    ) -> Page[LawyerSummary]:
        items, total = await self._lawyers.search(
            practice_area_id=practice_area_id,
            query=query,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        return Page[LawyerSummary](
            items=[LawyerSummary.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def search_firms(
        self,
        *,
        practice_area_id: int | None,
        query: str | None,
        page: int,
        page_size: int,
    ) -> Page[FirmSummary]:
        items, total = await self._firms.search(
            practice_area_id=practice_area_id,
            query=query,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        return Page[FirmSummary](
            items=[FirmSummary.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_lawyer(self, lawyer_id: int) -> LawyerRead:
        lawyer = await self._lawyers.get_with_relations(lawyer_id)
        if lawyer is None:
            raise NotFoundError("Advogado não encontrado")
        return LawyerRead.model_validate(lawyer)

    async def get_firm(self, firm_id: int) -> FirmRead:
        firm = await self._firms.get_with_relations(firm_id)
        if firm is None:
            raise NotFoundError("Escritório não encontrado")
        return FirmRead.model_validate(firm)
