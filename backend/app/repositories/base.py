"""Generic async repository.

The Repository pattern isolates persistence concerns from the service layer.
Services depend on these classes (never on raw SQLAlchemy sessions in business
logic), which keeps the data-access strategy swappable and the services easy to
test with fakes.
"""
from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id_: int) -> ModelT | None:
        return await self.session.get(self.model, id_)

    async def list(self, *, limit: int | None = None, offset: int | None = None) -> list[ModelT]:
        stmt = select(self.model)
        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(self.model))
        return int(result.scalar_one())

    def add(self, entity: ModelT) -> ModelT:
        """Stage a new entity. The unit-of-work (session) is flushed/committed
        by the service layer."""
        self.session.add(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)
