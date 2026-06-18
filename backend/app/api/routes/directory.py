"""Public directory endpoints — the client view (search & profiles)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import DirectoryServiceDep
from app.schemas.common import Page
from app.schemas.firm import FirmRead, FirmSummary
from app.schemas.lawyer import LawyerRead, LawyerSummary
from app.schemas.practice_area import PracticeAreaRead

router = APIRouter(tags=["directory"])

PageParam = Annotated[int, Query(ge=1)]
PageSizeParam = Annotated[int, Query(ge=1, le=100)]


@router.get("/practice-areas", response_model=list[PracticeAreaRead])
async def list_practice_areas(service: DirectoryServiceDep) -> list[PracticeAreaRead]:
    return await service.list_practice_areas()


@router.get("/lawyers", response_model=Page[LawyerSummary])
async def search_lawyers(
    service: DirectoryServiceDep,
    practice_area_id: Annotated[int | None, Query()] = None,
    q: Annotated[str | None, Query(description="Busca textual")] = None,
    page: PageParam = 1,
    page_size: PageSizeParam = 20,
) -> Page[LawyerSummary]:
    return await service.search_lawyers(
        practice_area_id=practice_area_id, query=q, page=page, page_size=page_size
    )


@router.get("/lawyers/{lawyer_id}", response_model=LawyerRead)
async def get_lawyer(lawyer_id: int, service: DirectoryServiceDep) -> LawyerRead:
    return await service.get_lawyer(lawyer_id)


@router.get("/firms", response_model=Page[FirmSummary])
async def search_firms(
    service: DirectoryServiceDep,
    practice_area_id: Annotated[int | None, Query()] = None,
    q: Annotated[str | None, Query(description="Busca textual")] = None,
    page: PageParam = 1,
    page_size: PageSizeParam = 20,
) -> Page[FirmSummary]:
    return await service.search_firms(
        practice_area_id=practice_area_id, query=q, page=page, page_size=page_size
    )


@router.get("/firms/{firm_id}", response_model=FirmRead)
async def get_firm(firm_id: int, service: DirectoryServiceDep) -> FirmRead:
    return await service.get_firm(firm_id)
