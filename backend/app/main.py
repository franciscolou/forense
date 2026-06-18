"""Application factory and ASGI entrypoint.

Run with:  uvicorn app.main:app --reload
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.database import init_db
from app.core.exceptions import DomainError
from app.seed import seed

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # For local/dev convenience we create tables and seed on startup.
    # In production these are replaced by Alembic migrations + a seed command.
    await init_db()
    await seed()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Translate domain errors into HTTP responses at the boundary, so the
    # service layer stays free of HTTP concerns.
    @app.exception_handler(DomainError)
    async def _domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    return app


app = create_app()
