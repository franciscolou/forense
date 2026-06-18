"""Domain-level exceptions.

The service layer raises these provider-agnostic exceptions so it never needs to
import FastAPI / HTTP concerns. A single exception handler at the API boundary
translates them into HTTP responses (see ``app.main``).
"""
from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain errors. Carries an HTTP status hint."""

    status_code: int = 400
    message: str = "Domain error"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message


class NotFoundError(DomainError):
    status_code = 404
    message = "Resource not found"


class ConflictError(DomainError):
    status_code = 409
    message = "Resource already exists"


class ValidationError(DomainError):
    status_code = 422
    message = "Validation failed"


class AuthenticationError(DomainError):
    status_code = 401
    message = "Invalid credentials"


class AuthorizationError(DomainError):
    status_code = 403
    message = "Not authorized"
