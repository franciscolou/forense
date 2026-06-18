from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class ClientRegisterRequest(BaseModel):
    """Basic account registration for a client."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str
    phone: str | None = None
    city: str | None = None
    state: str | None = None


class ClientRead(ORMModel):
    id: int
    phone: str | None
    city: str | None
    state: str | None
