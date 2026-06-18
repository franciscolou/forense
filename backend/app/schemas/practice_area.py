from __future__ import annotations

from app.schemas.common import ORMModel


class PracticeAreaRead(ORMModel):
    id: int
    name: str
    slug: str
