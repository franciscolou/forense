"""Law firm profile.

Beyond the basic account data, a firm carries its legal identity (razão social,
CNPJ, OAB registration) and is composed of one or more lawyers.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.associations import firm_lawyers, firm_practice_areas
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.lawyer import Lawyer
    from app.models.practice_area import PracticeArea
    from app.models.user import User


class Firm(Base, TimestampMixin):
    __tablename__ = "firms"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)  # razão social
    cnpj: Mapped[str] = mapped_column(String(18), unique=True, index=True, nullable=False)
    oab_registration: Mapped[str] = mapped_column(String(40), nullable=False)  # OAB do escritório

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    user: Mapped["User"] = relationship(back_populates="firm")
    lawyers: Mapped[list["Lawyer"]] = relationship(
        secondary=firm_lawyers, back_populates="firms"
    )
    practice_areas: Mapped[list["PracticeArea"]] = relationship(
        secondary=firm_practice_areas, back_populates="firms"
    )

    # Convenience accessor for read schemas; requires ``user`` eager-loaded.
    @property
    def email(self) -> str:
        return self.user.email
