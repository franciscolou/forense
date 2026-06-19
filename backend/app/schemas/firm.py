from __future__ import annotations

import re

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMModel
from app.schemas.lawyer import LawyerRegisterRequest, LawyerSummary
from app.schemas.practice_area import PracticeAreaRead

_CNPJ_RE = re.compile(r"\D")


class FirmProfileInput(BaseModel):
    legal_name: str = Field(..., description="Razão social")
    cnpj: str = Field(..., description="CNPJ do escritório")
    oab_registration: str = Field(..., description="Registro OAB do escritório")
    description: str | None = None
    city: str | None = None
    state: str | None = None
    website: str | None = None
    logo_url: str | None = None
    practice_area_ids: list[int] = Field(default_factory=list)

    @field_validator("cnpj")
    @classmethod
    def _normalize_cnpj(cls, v: str) -> str:
        digits = _CNPJ_RE.sub("", v)
        if len(digits) != 14:
            raise ValueError("CNPJ deve conter 14 dígitos")
        return digits


class FirmMemberRef(BaseModel):
    """Reference to an existing lawyer to attach to the firm."""

    lawyer_id: int


class FirmRegisterRequest(FirmProfileInput):
    """Register a firm.

    A firm must be composed of at least one lawyer. Members can be supplied as
    references to lawyers that already exist (``existing_lawyer_ids``) and/or as
    brand-new lawyers to be created on the spot (``new_lawyers``).
    """

    email: EmailStr
    password: str = Field(..., min_length=8)

    existing_lawyer_ids: list[int] = Field(default_factory=list)
    new_lawyers: list[LawyerRegisterRequest] = Field(default_factory=list)


class FirmSummary(ORMModel):
    """Lightweight firm view used in search result lists."""

    id: int
    user_id: int
    legal_name: str
    city: str | None
    state: str | None
    logo_url: str | None
    practice_areas: list[PracticeAreaRead]


class FirmRead(ORMModel):
    """Detailed firm view (profile page)."""

    id: int
    user_id: int
    legal_name: str
    cnpj: str
    oab_registration: str
    email: EmailStr
    description: str | None
    city: str | None
    state: str | None
    website: str | None
    logo_url: str | None
    practice_areas: list[PracticeAreaRead]
    lawyers: list[LawyerSummary]
