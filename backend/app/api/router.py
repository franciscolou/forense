"""Top-level API router aggregating all versioned route modules."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    auth,
    availability,
    booking_configuration,
    bookings,
    directory,
    registration,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(registration.router)
api_router.include_router(directory.router)
api_router.include_router(booking_configuration.router)
api_router.include_router(availability.router)
api_router.include_router(bookings.router)
