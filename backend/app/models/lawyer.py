"""Lawyer profile and its related professional records.

The OAB identifier is intentionally stored as two columns (``oab_uf`` and
``oab_number``) so the frontend can collect them in separate fields, while a
convenience property exposes the combined registration string.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.associations import firm_lawyers, lawyer_practice_areas
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.firm import Firm
    from app.models.practice_area import PracticeArea
    from app.models.user import User


class Lawyer(Base, TimestampMixin):
    __tablename__ = "lawyers"
    # A given OAB number is unique within its issuing state.
    __table_args__ = (UniqueConstraint("oab_uf", "oab_number", name="uq_oab"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # OAB registration, split into the two fields the UI collects.
    oab_uf: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    oab_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    oab_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Professional profile.
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    years_of_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    user: Mapped["User"] = relationship(back_populates="lawyer")
    practice_areas: Mapped[list["PracticeArea"]] = relationship(
        secondary=lawyer_practice_areas, back_populates="lawyers"
    )
    educations: Mapped[list["LawyerEducation"]] = relationship(
        back_populates="lawyer", cascade="all, delete-orphan"
    )
    languages: Mapped[list["LawyerLanguage"]] = relationship(
        back_populates="lawyer", cascade="all, delete-orphan"
    )
    firms: Mapped[list["Firm"]] = relationship(
        secondary=firm_lawyers, back_populates="lawyers"
    )

    @property
    def oab_full(self) -> str:
        return f"OAB/{self.oab_uf} {self.oab_number}"

    # Convenience accessors so read schemas (``from_attributes``) can expose the
    # account's name/email without the API layer reaching into ``user``.
    # Requires ``user`` to be eager-loaded (the repositories do so).
    @property
    def full_name(self) -> str:
        return self.user.full_name

    @property
    def email(self) -> str:
        return self.user.email


class LawyerEducation(Base):
    """Formações e pós-graduações."""

    __tablename__ = "lawyer_educations"

    id: Mapped[int] = mapped_column(primary_key=True)
    lawyer_id: Mapped[int] = mapped_column(
        ForeignKey("lawyers.id", ondelete="CASCADE"), nullable=False
    )
    # e.g. "graduacao", "pos-graduacao", "mestrado", "doutorado", "certificacao"
    degree: Mapped[str] = mapped_column(String(80), nullable=False)
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    field_of_study: Mapped[str | None] = mapped_column(String(255), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    lawyer: Mapped["Lawyer"] = relationship(back_populates="educations")


class LawyerLanguage(Base):
    """Idiomas falados pelo advogado e nível de proficiência."""

    __tablename__ = "lawyer_languages"

    id: Mapped[int] = mapped_column(primary_key=True)
    lawyer_id: Mapped[int] = mapped_column(
        ForeignKey("lawyers.id", ondelete="CASCADE"), nullable=False
    )
    language: Mapped[str] = mapped_column(String(80), nullable=False)
    # e.g. "basico", "intermediario", "avancado", "fluente", "nativo"
    proficiency: Mapped[str | None] = mapped_column(String(40), nullable=True)

    lawyer: Mapped["Lawyer"] = relationship(back_populates="languages")
