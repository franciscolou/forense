from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMModel
from app.schemas.practice_area import PracticeAreaRead

# Valid Brazilian state abbreviations used to validate the OAB UF field.
BR_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}


# --- Nested professional records ----------------------------------------
class EducationInput(BaseModel):
    degree: str
    institution: str
    field_of_study: str | None = None
    year: int | None = None


class EducationRead(ORMModel):
    id: int
    degree: str
    institution: str
    field_of_study: str | None
    year: int | None


class LanguageInput(BaseModel):
    language: str
    proficiency: str | None = None


class LanguageRead(ORMModel):
    id: int
    language: str
    proficiency: str | None


# --- OAB ----------------------------------------------------------------
class OABIdentifier(BaseModel):
    """The OAB id, collected as two separate fields by the UI."""

    oab_uf: str = Field(..., min_length=2, max_length=2, description="UF de inscrição, ex: SP")
    oab_number: str = Field(..., min_length=1, max_length=20, description="Número de inscrição")

    @field_validator("oab_uf")
    @classmethod
    def _validate_uf(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in BR_STATES:
            raise ValueError(f"UF inválida: {v}")
        return v

    @field_validator("oab_number")
    @classmethod
    def _validate_number(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit():
            raise ValueError("O número da OAB deve conter apenas dígitos")
        return v


# --- Registration / profile ---------------------------------------------
class LawyerProfileInput(BaseModel):
    """Profile fields shared by registration and profile updates."""

    bio: str | None = None
    years_of_experience: int | None = Field(default=None, ge=0)
    city: str | None = None
    state: str | None = None
    photo_url: str | None = None
    practice_area_ids: list[int] = Field(default_factory=list)
    educations: list[EducationInput] = Field(default_factory=list)
    languages: list[LanguageInput] = Field(default_factory=list)


class LawyerRegisterRequest(OABIdentifier, LawyerProfileInput):
    """Full payload to self-register as a lawyer."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str


class LawyerRead(ORMModel):
    """Detailed lawyer view (profile page)."""

    id: int
    user_id: int
    full_name: str
    email: EmailStr
    oab_uf: str
    oab_number: str
    oab_verified: bool
    bio: str | None
    years_of_experience: int | None
    city: str | None
    state: str | None
    photo_url: str | None
    practice_areas: list[PracticeAreaRead]
    educations: list[EducationRead]
    languages: list[LanguageRead]


class LawyerSummary(ORMModel):
    """Lightweight lawyer view used in search result lists."""

    id: int
    user_id: int
    full_name: str
    oab_uf: str
    oab_number: str
    years_of_experience: int | None
    city: str | None
    state: str | None
    photo_url: str | None
    practice_areas: list[PracticeAreaRead]
