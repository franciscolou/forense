"""Area of legal practice (e.g. Trabalhista, Tributário, Penal)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.associations import firm_practice_areas, lawyer_practice_areas

if TYPE_CHECKING:
    from app.models.firm import Firm
    from app.models.lawyer import Lawyer


class PracticeArea(Base):
    __tablename__ = "practice_areas"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)

    lawyers: Mapped[list["Lawyer"]] = relationship(
        secondary=lawyer_practice_areas, back_populates="practice_areas"
    )
    firms: Mapped[list["Firm"]] = relationship(
        secondary=firm_practice_areas, back_populates="practice_areas"
    )
