"""The authentication root entity.

``User`` holds credentials and a role discriminator. Each role has a dedicated
profile table (``Client`` / ``Lawyer`` / ``Firm``) linked 1:1, keeping the auth
concern cleanly separated from profile data.
"""
from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.firm import Firm
    from app.models.lawyer import Lawyer


class UserRole(str, enum.Enum):
    CLIENT = "client"
    LAWYER = "lawyer"
    FIRM = "firm"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    client: Mapped[Optional["Client"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    lawyer: Mapped[Optional["Lawyer"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    firm: Mapped[Optional["Firm"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
