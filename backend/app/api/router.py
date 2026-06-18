"""Top-level API router aggregating all versioned route modules."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import auth, directory, registration

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(registration.router)
api_router.include_router(directory.router)
