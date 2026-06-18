from __future__ import annotations

from pydantic import BaseModel, EmailStr

from app.models.user import UserRole
from app.schemas.common import ORMModel


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool


class AuthResponse(BaseModel):
    """Returned by registration & login endpoints: the token plus the user."""

    token: Token
    user: UserRead
