"""Shared schema building blocks."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    """Base schema for objects read from the ORM."""

    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    """A simple paginated envelope used by list/search endpoints."""

    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        if self.page_size == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size
