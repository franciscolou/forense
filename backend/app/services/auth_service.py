"""Authentication use-cases."""
from __future__ import annotations

from app.core.exceptions import AuthenticationError
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import AuthResponse, Token, UserRead


class AuthService:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def authenticate(self, email: str, password: str) -> User:
        user = await self._users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Email ou senha inválidos")
        if not user.is_active:
            raise AuthenticationError("Conta inativa")
        return user

    def issue_token(self, user: User) -> AuthResponse:
        token = Token(access_token=create_access_token(user.id))
        return AuthResponse(token=token, user=UserRead.model_validate(user))

    async def login(self, email: str, password: str) -> AuthResponse:
        user = await self.authenticate(email, password)
        return self.issue_token(user)
